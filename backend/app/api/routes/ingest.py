"""Endpoint ingest: impor folder `inbox` (FR-N2) dan tarik NRT FIRMS (FR-N5 fallback)."""
from __future__ import annotations

import datetime as dt
import os
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.pipeline import hdfs
from app.pipeline.inbox_job import run_inbox_job
from app.pipeline.job_manager import (
    add_ingest_log,
    log_job_finish,
    log_job_start,
)

router = APIRouter(prefix="/ingest", tags=["ingest"])


class InboxRequest(BaseModel):
    run_pipeline: bool = True


class FirmsNrtRequest(BaseModel):
    days: int = 2


def _firms_chunk(source: str, start: dt.date, days: int, out_dir: Path) -> tuple[Path | None, int]:
    """Unduh satu chunk FIRMS area API ke file lokal."""
    if not settings.FIRMS_MAP_KEY:
        raise RuntimeError("FIRMS_MAP_KEY kosong di .env")
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{settings.FIRMS_MAP_KEY}/{source}/"
        f"{settings.FIRMS_BBOX}/{days}/{start.isoformat()}"
    )
    try:
        response = requests.get(url, timeout=120)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {source} {start}: {type(exc).__name__}")
        return None, 0
    if response.status_code != 200:
        print(
            f"[FAIL] {source} {start} ({days}h): HTTP {response.status_code} "
            f"{response.text[:120].strip()!r}"
        )
        return None, 0
    text = response.text.strip()
    if not text or "latitude" not in text:
        print(f"[WARN] {source} {start}: tidak ada data")
        return None, 0

    dest = out_dir / f"firms_nrt_{source.lower()}_{start.isoformat()}_{days}d.csv"
    dest.write_text(text + "\n", encoding="utf-8")
    row_count = max(0, sum(1 for _ in dest.open("rb")) - 1)
    print(f"[OK] {source} {start} ({days}h): {row_count:,} baris -> {dest.name}")
    return dest, row_count


def _fetch_firms_nrt(days: int, out_dir: Path) -> int:
    """Unduh NRT FIRMS untuk semua sumber, simpan di out_dir."""
    today = dt.date.today()
    first = today - dt.timedelta(days=days - 1)
    sources = [
        "VIIRS_SNPP_NRT",
        "VIIRS_NOAA20_NRT",
        "VIIRS_NOAA21_NRT",
        "MODIS_NRT",
    ]
    total = 0
    for source in sources:
        offset = 0
        while offset < days:
            chunk = min(5, days - offset)
            start = first + dt.timedelta(days=offset)
            _, rows = _firms_chunk(source, start, chunk, out_dir)
            total += rows
            offset += chunk
    return total


@router.post("/inbox", summary="Impor folder inbox sekarang (job tercatat)")
def import_inbox(request: InboxRequest | None = None) -> dict[str, Any]:
    run_pipeline = True if request is None else request.run_pipeline
    job_id = f"ingest-folder-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    log_job_start(job_id, "INGEST_FOLDER", {"folder_import": True})
    thread = threading.Thread(
        target=run_inbox_job, args=(job_id, run_pipeline), name="ingest-inbox", daemon=True
    )
    thread.start()
    return {"job_id": job_id, "job_type": "INGEST_FOLDER", "status": "queued"}


@router.post("/firms-nrt", summary="Tarik NRT FIRMS manual (fallback NiFi, FR-N5)")
def ingest_firms_nrt(request: FirmsNrtRequest | None = None) -> dict[str, Any]:
    """Unduh data NRT FIRMS via API, unggah ke HDFS, catat di job manager.

    Digunakan sebagai fallback bila NiFi tidak berjalan.
    """
    days = 2 if request is None else request.days
    if not 1 <= days <= 31:
        raise HTTPException(status_code=422, detail="days harus 1-31")
    if not settings.FIRMS_MAP_KEY:
        raise HTTPException(
            status_code=400,
            detail="FIRMS_MAP_KEY belum diatur di .env; unduhan NRT tidak dapat dijalankan",
        )

    job_id = f"ingest-firms-nrt-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    log_job_start(job_id, "NRT_INGEST", {"days": days, "source": "firms-nrt-api"})

    staging = Path(settings.STAGING_DIR) / f"firms_nrt_{job_id}"
    staging.mkdir(parents=True, exist_ok=True)

    try:
        total_rows = _fetch_firms_nrt(days, staging)

        # Unggah setiap file ke HDFS dengan partisi tanggal.
        uploaded = 0
        today_str = dt.date.today().isoformat()
        hdfs_target_dir = f"{settings.HDFS_BASE_PATH}/raw/firms_nrt/date={today_str}"
        for csv_file in sorted(staging.glob("*.csv")):
            hdfs.put(csv_file, f"{hdfs_target_dir}/{csv_file.name}")
            uploaded += 1

        add_ingest_log(
            "firms-nrt",
            "success",
            rows_in=total_rows,
            details={"job_id": job_id, "days": days, "files_uploaded": uploaded},
        )
        log_job_finish(
            job_id,
            "COMPLETED",
            {
                "rows_in": total_rows,
                "files_uploaded": uploaded,
                "hdfs_dir": hdfs_target_dir,
            },
        )

        # Bersihkan staging.
        for f in staging.iterdir():
            f.unlink(missing_ok=True)
        staging.rmdir()

        return {
            "job_id": job_id,
            "job_type": "NRT_INGEST",
            "status": "completed",
            "rows_in": total_rows,
            "files_uploaded": uploaded,
            "hdfs_dir": hdfs_target_dir,
        }
    except Exception as exc:  # noqa: BLE001
        add_ingest_log("firms-nrt", "failed", details={"job_id": job_id, "error": repr(exc)})
        log_job_finish(job_id, "FAILED", {"error": repr(exc)})
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if staging.exists():
            for f in staging.iterdir():
                f.unlink(missing_ok=True)
            staging.rmdir()


@router.post("/compact-nrt", summary="Jalankan kompak file kecil NRT (Spark job)")
def compact_nrt() -> dict[str, Any]:
    """Antrekan job Spark kompak file NRT kecil menjadi Parquet terpartisi."""
    from app.pipeline.spark_runner import queue

    job_id = f"compact-nrt-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    submission = queue.submit(
        job_id,
        "NRT_COMPACT",
        "compact_nrt.py",
        ["--job-id", job_id],
        {"trigger": "ingest-firms-nrt-fallback"},
    )
    return submission

