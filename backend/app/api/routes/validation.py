"""Endpoint validasi terhadap rekap eksternal SiPongi+ / BNPB (FR-A6).

Menerima unggah CSV rekap, menyimpan ke SQLite (`reference_validation`),
dan membandingkan tren pipeline (`agg_daily_province`) dengan rekap
eksternal: korelasi, selisih relatif, dan RMSE.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.pipeline.job_manager import (
    _connect,
    add_ingest_log,
    init_db,
    log_job_finish,
    log_job_start,
    _now,
)
from app.services import serving

router = APIRouter(prefix="/validation", tags=["validasi"])

# Kolom yang diharapkan dalam CSV rekap SiPongi+ / BNPB.
REQUIRED_COLUMNS = {"date", "province", "hotspot_count"}
OPTIONAL_COLUMNS = {"source", "burned_area_ha"}


class ValidationCompare(BaseModel):
    date: str
    pipeline_count: int
    reference_count: int
    diff: int
    diff_percent: float | None


class ValidationSummary(BaseModel):
    reference_rows: int
    reference_provinces: list[str]
    date_start: str | None
    date_end: str | None
    correlation: float | None
    relative_difference_percent: float | None
    rmse: float | None
    comparison: list[ValidationCompare]


def _parse_csv(file_content: str) -> list[dict[str, Any]]:
    """Parse CSV rekap validasi ke daftar baris."""
    reader = csv.DictReader(io.StringIO(file_content))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV kosong atau tidak memiliki header")
    header = set(c.strip().lower() for c in reader.fieldnames)
    missing = REQUIRED_COLUMNS - header
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Kolom wajib hilang: {', '.join(sorted(missing))}",
        )
    rows: list[dict[str, Any]] = []
    for row in reader:
        try:
            rows.append(
                {
                    "date": row["date"].strip(),
                    "province": row["province"].strip(),
                    "hotspot_count": int(row["hotspot_count"]),
                    "source": (row.get("source") or "SiPongi+").strip() or "SiPongi+",
                    "burned_area_ha": float(row["burned_area_ha"])
                    if row.get("burned_area_ha")
                    else None,
                }
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=f"Baris CSV tidak valid: {exc}")
    if not rows:
        raise HTTPException(status_code=400, detail="CSV tidak mengandung baris data")
    return rows


def _validate_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Tanggal tidak valid: {value}")
    return value


@router.post("/reference", summary="Unggah CSV rekap SiPongi+ / BNPB untuk validasi")
def upload_reference(file: UploadFile = File(...)) -> dict[str, Any]:
    """Unggah CSV rekap eksternal (SiPongi+ atau BNPB) sebagai data referensi validasi.

    Kolom wajib: date, province, hotspot_count.
    Kolom opsional: source, burned_area_ha.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File harus berekstensi .csv")

    content = (file.file.read()).decode("utf-8")
    rows = _parse_csv(content)

    # Validasi semua tanggal sebelum menyimpan.
    for row in rows:
        _validate_date(row["date"])

    job_id = f"validation-ref-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    log_job_start(job_id, "VALIDATION_REFERENCE", {"file": file.filename, "rows": len(rows)})

    try:
        for row in rows:
            conn = _connect()
            try:
                conn.execute(
                    """
                    INSERT INTO reference_validation
                        (date, province, source, hotspot_count, burned_area_ha, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["date"],
                        row["province"],
                        row["source"],
                        row["hotspot_count"],
                        row["burned_area_ha"],
                        _now(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        add_ingest_log(
            "validation-reference",
            "success",
            rows_in=len(rows),
            details={"file": file.filename, "rows": len(rows)},
        )
        log_job_finish(
            job_id,
            "COMPLETED",
            {"rows_inserted": len(rows), "file": file.filename},
        )

        return {
            "status": "success",
            "rows_inserted": len(rows),
            "file": file.filename,
            "message": "Data referensi validasi tersimpan",
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        log_job_finish(job_id, "FAILED", {"error": repr(exc)})
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/compare", summary="Bandingkan tren pipeline vs rekap eksternal")
def compare() -> ValidationSummary:
    """
    Bandingkan agregat harian pipeline (`agg_daily_province`) dengan data
    referensi validasi (`reference_validation`) per tanggal.

    Mengembalikan korelasi Pearson, selisih relatif, dan RMSE untuk setiap
    tanggal yang tersedia di keduanya.
    """
    ref_rows = []
    init_db()
    conn = _connect()
    try:
        ref_rows = conn.execute(
            """
            SELECT date, province, source, hotspot_count, burned_area_ha
            FROM reference_validation
            ORDER BY date, province
            """
        ).fetchall()
    finally:
        conn.close()
    ref_rows = [dict(r) for r in ref_rows]

    if not ref_rows:
        return ValidationSummary(
            reference_rows=0,
            reference_provinces=[],
            date_start=None,
            date_end=None,
            correlation=None,
            relative_difference_percent=None,
            rmse=None,
            comparison=[],
        )

    # Ambil rentang tanggal referensi.
    dates = sorted({r["date"] for r in ref_rows})
    provinces = sorted({r["province"] for r in ref_rows})
    date_start = dates[0]
    date_end = dates[-1]

    # Ambil data pipeline untuk rentang tanggal yang sama, grouped by date.
    placeholders = ",".join(["?"] * len(dates))
    pipeline_rows = serving.query(
        f"""
        SELECT date, SUM(hotspot_count) AS pipeline_count
        FROM agg_daily_province
        WHERE date IN ({placeholders})
        GROUP BY date
        ORDER BY date
        """,
        list(dates),
    )
    pipeline_by_date = {r["date"]: int(r["pipeline_count"] or 0) for r in pipeline_rows}

    # Gabungkan per tanggal (referensi diagregasi seluruh provinsi).
    reference_by_date: dict[str, int] = {}
    for r in ref_rows:
        reference_by_date[r["date"]] = reference_by_date.get(r["date"], 0) + int(
            r["hotspot_count"] or 0
        )

    common_dates = sorted(set(pipeline_by_date.keys()) & set(reference_by_date.keys()))
    comparison: list[ValidationCompare] = []
    pipeline_vals: list[float] = []
    reference_vals: list[float] = []

    for d in common_dates:
        pc = pipeline_by_date.get(d, 0)
        rc = reference_by_date.get(d, 0)
        diff = pc - rc
        diff_pct = (diff / rc * 100.0) if rc else None
        comparison.append(
            ValidationCompare(
                date=d,
                pipeline_count=pc,
                reference_count=rc,
                diff=diff,
                diff_percent=round(diff_pct, 2) if diff_pct is not None else None,
            )
        )
        pipeline_vals.append(float(pc))
        reference_vals.append(float(rc))

    # Hitung korelasi Pearson dan RMSE jika cukup data.
    correlation: float | None = None
    rmse: float | None = None
    relative_diff: float | None = None

    if len(common_dates) >= 2:
        n = len(common_dates)
        mean_p = sum(pipeline_vals) / n
        mean_r = sum(reference_vals) / n

        cov = sum((p - mean_p) * (r - mean_r) for p, r in zip(pipeline_vals, reference_vals))
        var_p = sum((p - mean_p) ** 2 for p in pipeline_vals)
        var_r = sum((r - mean_r) ** 2 for r in reference_vals)

        if var_p > 0 and var_r > 0:
            correlation = cov / ((var_p * var_r) ** 0.5)

        rmse = (sum((p - r) ** 2 for p, r in zip(pipeline_vals, reference_vals)) / n) ** 0.5

        total_p = sum(pipeline_vals)
        total_r = sum(reference_vals)
        if total_r:
            relative_diff = (total_p - total_r) / total_r * 100.0

    return ValidationSummary(
        reference_rows=len(ref_rows),
        reference_provinces=provinces,
        date_start=date_start,
        date_end=date_end,
        correlation=round(correlation, 4) if correlation is not None else None,
        relative_difference_percent=round(relative_diff, 2) if relative_diff is not None else None,
        rmse=round(rmse, 4) if rmse is not None else None,
        comparison=comparison,
    )
