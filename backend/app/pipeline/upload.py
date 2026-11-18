"""Upload manual bertahap (chunk) -> staging -> `hdfs dfs -put` -> pipeline sama.

Jalur ini adalah jalur tambahan (AGENTS.md): akuisisi otomatis tetap utama,
tetapi file manual memakai deteksi format, karantina, dan pipeline yang identik.

Sesi upload disimpan di `settings.UPLOAD_DIR/<upload_id>/`:
- `meta.json`   : nama file, ukuran, waktu dibuat
- `part_000001` : potongan biner sesuai urutan
- `<nama file>` : hasil gabungan (dipakai deteksi dan upload ke HDFS)
"""
from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.adapters.detector import detect_format
from app.core.config import settings
from app.pipeline import catalog, hdfs
from app.pipeline.ingest import count_rows, target_path  # dipakai ulang agar konsisten
from app.pipeline.job_manager import (
    add_dataset,
    add_ingest_log,
    add_quarantine,
    log_job_finish,
    log_job_start,
)

UPLOAD_ID_RE = re.compile(r"^[0-9a-f]{32}$")
ALLOWED_SUFFIXES = {".csv", ".json"}
PART_RE = re.compile(r"^part_(\d{6})$")
CHUNK_MAX_BYTES = 32 * 1024 * 1024

# Kolom mentah yang benar-benar dibaca `preprocess.py`/`data_profile.py`.
RAW_KNOWN_COLUMNS = {
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "frp",
    "brightness",
    "bright_ti4",
    "bright_ti5",
    "bright_t31",
    "daynight",
    "type",
    "scan",
    "track",
    "version",
}


class UploadError(ValueError):
    """Permintaan upload tidak valid."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _session_dir(upload_id: str) -> Path:
    if not UPLOAD_ID_RE.match(upload_id or ""):
        raise UploadError("upload_id tidak valid")
    return Path(settings.UPLOAD_DIR) / upload_id


def _write_meta(session: Path, meta: dict[str, Any]) -> None:
    (session / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def read_meta(upload_id: str) -> dict[str, Any]:
    session = _session_dir(upload_id)
    meta_file = session / "meta.json"
    if not meta_file.exists():
        raise UploadError("Sesi upload tidak ditemukan (mungkin sudah dibersihkan)")
    return json.loads(meta_file.read_text(encoding="utf-8"))


def _parts(session: Path) -> list[Path]:
    return sorted(
        (p for p in session.glob("part_*") if PART_RE.match(p.name)),
        key=lambda p: int(PART_RE.match(p.name).group(1)),  # type: ignore[union-attr]
    )


def _received_bytes(session: Path) -> int:
    return sum(p.stat().st_size for p in _parts(session))


def init(filename: str, size_bytes: int) -> dict[str, Any]:
    settings.ensure_dirs()
    safe_name = Path(filename or "").name
    suffix = Path(safe_name).suffix.lower()
    if not safe_name:
        raise UploadError("Nama file kosong")
    if suffix not in ALLOWED_SUFFIXES:
        raise UploadError("Hanya file .csv atau .json yang didukung jalur manual")
    if size_bytes <= 0:
        raise UploadError("Ukuran file tidak diketahui atau kosong")
    if size_bytes > settings.MAX_UPLOAD_BYTES:
        raise UploadError(
            f"Ukuran melebihi batas {settings.MAX_UPLOAD_BYTES // 1_000_000} MB"
        )

    upload_id = uuid.uuid4().hex
    session = _session_dir(upload_id)
    session.mkdir(parents=True, exist_ok=True)
    meta = {
        "upload_id": upload_id,
        "filename": safe_name,
        "size_bytes": int(size_bytes),
        "created_at": _now(),
        "completed": False,
        "hdfs_path": None,
    }
    _write_meta(session, meta)
    return {
        "upload_id": upload_id,
        "filename": safe_name,
        "chunk_size": settings.UPLOAD_CHUNK_SIZE,
        "max_bytes": settings.MAX_UPLOAD_BYTES,
        "received_bytes": 0,
    }


def append_chunk(upload_id: str, index: int, payload: bytes) -> dict[str, Any]:
    if index < 0:
        raise UploadError("Indeks potongan tidak valid")
    if not payload:
        raise UploadError("Potongan kosong")
    if len(payload) > CHUNK_MAX_BYTES:
        raise UploadError("Potongan terlalu besar")

    meta = read_meta(upload_id)
    session = _session_dir(upload_id)
    (session / f"part_{index:06d}").write_bytes(payload)

    received = _received_bytes(session)
    if received > meta["size_bytes"]:
        (session / f"part_{index:06d}").unlink(missing_ok=True)
        raise UploadError("Data melebihi ukuran file yang dideklarasikan")

    # Gabungan lama tidak berlaku lagi setelah potongan baru ditulis.
    (session / meta["filename"]).unlink(missing_ok=True)
    return {
        "upload_id": upload_id,
        "received_bytes": received,
        "size_bytes": meta["size_bytes"],
        "parts": len(_parts(session)),
    }


def assemble(upload_id: str) -> Path:
    meta = read_meta(upload_id)
    session = _session_dir(upload_id)
    parts = _parts(session)
    if not parts:
        raise UploadError("Belum ada potongan yang diunggah")
    assembled = session / meta["filename"]
    with assembled.open("wb") as out:
        for part in parts:
            out.write(part.read_bytes())
    return assembled


def _assemble_if_needed(upload_id: str) -> Path:
    meta = read_meta(upload_id)
    session = _session_dir(upload_id)
    assembled = session / meta["filename"]
    if assembled.exists():
        return assembled
    return assemble(upload_id)


def estimate_rows(path: Path, sample_lines: int = 200) -> int:
    """Perkiraan baris: hitung cepat untuk file kecil, ekstrapolasi untuk besar."""
    if path.suffix.lower() == ".json":
        return 0  # pratinjau JSON tidak dihitung per baris
    with path.open("rb") as handle:
        sample = b""
        for _ in range(sample_lines):
            line = handle.readline()
            if not line:
                break
            sample += line
        if not sample:
            return 0
        sample_count = sample.count(b"\n")
        total = path.stat().st_size
        if sample_count >= sample_lines or total <= len(sample):
            with path.open("rb") as full:
                return max(0, sum(1 for _ in full) - 1)
        avg = len(sample) / max(sample_count, 1)
        return max(0, int(total / avg) - 1)


def _read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return [c.strip() for c in (handle.readline().strip().split(","))]


def detect(upload_id: str) -> dict[str, Any]:
    """Deteksi format dari sesi upload (tanpa memindahkan apa pun ke HDFS)."""
    meta = read_meta(upload_id)
    path = _assemble_if_needed(upload_id)
    if not path.exists():  # pragma: no cover - penjagaan
        raise UploadError("File gabungan tidak ditemukan")

    adapter, source_type, sample_rows = detect_format(path)
    header = _read_header(path) if path.suffix.lower() == ".csv" else []
    recognized = [c for c in header if c.lower() in RAW_KNOWN_COLUMNS]
    unknown = [c for c in header if c.lower() not in RAW_KNOWN_COLUMNS]
    row_estimate = estimate_rows(path)

    validation: dict[str, Any] | None = None
    if adapter is not None and sample_rows:
        import pandas as pd

        sample_df = pd.DataFrame(sample_rows)
        try:
            validation = adapter.validate(adapter.normalize(sample_df))
        except Exception as exc:  # noqa: BLE001 - laporkan, jangan gagalkan deteksi
            validation = {"valid_count": 0, "invalid_count": 0, "errors": [repr(exc)]}

    return {
        "upload_id": upload_id,
        "filename": meta["filename"],
        "size_bytes": path.stat().st_size,
        "detected_format": source_type,
        "adapter": adapter.__class__.__name__ if adapter else None,
        "estimated_rows": row_estimate,
        "columns": {
            "total": len(header),
            "recognized": recognized,
            "unknown": unknown,
        },
        "sample_validation": validation,
        "procesable": adapter is not None,
    }


def preview(upload_id: str, limit: int = 20) -> dict[str, Any]:
    meta = read_meta(upload_id)
    path = _assemble_if_needed(upload_id)
    lines = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for index, line in enumerate(handle):
            if index >= limit:
                break
            lines.append(line.rstrip("\r\n"))
    return {"filename": meta["filename"], "lines": lines}


def complete(upload_id: str, run_pipeline: bool = True) -> dict[str, Any]:
    """Gabungkan -> deteksi -> `hdfs dfs -put` -> catat dataset -> jalankan pipeline."""
    meta = read_meta(upload_id)
    session = _session_dir(upload_id)
    path = _assemble_if_needed(upload_id)
    filename = meta["filename"]
    job_id = f"ingest-manual-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    log_job_start(job_id, "INGEST_MANUAL", {"file": filename, "upload_id": upload_id})

    adapter, source_type, sample_rows = detect_format(path)
    if adapter is None:
        failed_dir = Path(settings.INBOX_FAILED_DIR)
        failed_dir.mkdir(parents=True, exist_ok=True)
        rejected_rows = estimate_rows(path)
        shutil.move(str(path), str(failed_dir / filename))
        add_quarantine(filename, "Format file tidak dikenali", rejected_rows)
        report = {
            "file": filename,
            "status": "quarantined",
            "detected_format": source_type,
            "message": "Format file tidak dikenali; file dipindahkan ke inbox/failed",
        }
        add_ingest_log("unknown", "quarantined", details=report)
        log_job_finish(job_id, "FAILED", report)
        return {**report, "job_id": job_id, "upload_id": upload_id, "quarantined": True}

    import pandas as pd

    sample_df = pd.DataFrame(sample_rows)
    validation = adapter.validate(adapter.normalize(sample_df))
    row_count = count_rows(path)
    if validation["invalid_count"] > 0 and validation["valid_count"] == 0:
        failed_dir = Path(settings.INBOX_FAILED_DIR)
        failed_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(failed_dir / filename))
        reason = "Validasi gagal: " + "; ".join(validation["errors"])
        add_quarantine(filename, reason, row_count)
        report = {
            "file": filename,
            "status": "quarantined",
            "detected_format": source_type,
            "message": reason,
        }
        add_ingest_log(
            source_type, "quarantined", rows_in=row_count, rows_quarantined=row_count, details=report
        )
        log_job_finish(job_id, "FAILED", report)
        return {**report, "job_id": job_id, "upload_id": upload_id, "quarantined": True}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    staging_file = Path(settings.STAGING_DIR) / f"{source_type}_{timestamp}_{filename}"
    staging_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(str(path), str(staging_file))
    size_bytes = staging_file.stat().st_size
    hdfs_target = target_path(source_type, staging_file.name)

    try:
        hdfs.put(staging_file, hdfs_target)
    except hdfs.HdfsError as exc:
        report = {
            "file": filename,
            "status": "failed",
            "detected_format": source_type,
            "message": f"HDFS put gagal: {exc}",
        }
        add_ingest_log(source_type, "failed", rows_in=row_count, details=report)
        log_job_finish(job_id, "FAILED", report)
        return {**report, "job_id": job_id, "upload_id": upload_id}

    staging_file.unlink(missing_ok=True)
    add_dataset(
        name=filename,
        hdfs_path=hdfs_target,
        source=source_type,
        size_bytes=size_bytes,
        row_count=row_count,
        column_count=len(_read_header(path)),
        detected_format=source_type,
        ingest_path="manual",
    )
    report = {
        "file": filename,
        "status": "ingested",
        "detected_format": source_type,
        "hdfs_path": hdfs_target,
        "size_bytes": size_bytes,
        "rows": {"input": row_count},
        "message": "Berhasil diunggah ke HDFS raw",
    }
    add_ingest_log(source_type, "success", rows_in=row_count, details=report)

    catalog.invalidate()

    pipeline_job = None
    if run_pipeline:
        pipeline_job = trigger_pipeline(report)
        report["pipeline_job_id"] = pipeline_job["job_id"] if pipeline_job else None

    log_job_finish(job_id, "COMPLETED", report)
    shutil.rmtree(session, ignore_errors=True)
    return {**report, "job_id": job_id, "upload_id": upload_id, "quarantined": False}


def trigger_pipeline(ingest_report: dict[str, Any]) -> dict[str, Any] | None:
    """Jalankan pre-processing setelah ingest manual (pipeline yang sama)."""
    from app.pipeline.spark_runner import queue

    job_id = f"preprocess-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    summary_path = Path(settings.SERVING_DIR) / "runs" / f"{job_id}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return queue.submit(
            job_id,
            "PREPROCESSING",
            "preprocess.py",
            ["--summary", str(summary_path), "--job-id", job_id],
            {"trigger": "manual-upload", "file": ingest_report.get("file")},
        )
    except Exception:  # pragma: no cover - pipeline opsional
        return None


def cancel(upload_id: str) -> bool:
    session = _session_dir(upload_id)
    if not session.exists():
        return False
    shutil.rmtree(session, ignore_errors=True)
    return True
