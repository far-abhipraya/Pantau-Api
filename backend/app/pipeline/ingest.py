"""Impor folder: `C:/karhutla-data/inbox` -> deteksi -> HDFS raw -> metadata.

Aturan (AGENTS.md / ingestion-adapters.md):
- Jangan menebak format dari nama file; pakai `detect_format` berbasis header.
- File tidak dikenal / gagal validasi dipindahkan ke `inbox/failed` dan dicatat
  di tabel `quarantine` serta `ingest_log` (tidak dibuang diam-diam).
- Upload ke HDFS memakai staging lokal + `hdfs dfs -put`, dengan
  `HADOOP_USER_NAME` dari konfigurasi.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.adapters.detector import detect_format
from app.core.config import settings
from app.pipeline.job_manager import add_dataset, add_ingest_log, add_quarantine


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _count_rows(path: Path) -> int:
    with path.open("rb") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _hdfs_put(local_path: Path, hdfs_path: str) -> tuple[bool, str]:
    env = os.environ.copy()
    env["HADOOP_USER_NAME"] = settings.HADOOP_USER_NAME
    cmd = f'hdfs dfs -put -f "{local_path}" "{hdfs_path}"'
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()


def _target_path(source_type: str, filename: str) -> str:
    root = settings.HDFS_BASE_PATH
    if "VIIRS" in source_type or "MODIS" in source_type:
        return f"{root}/raw/firms_hist/{filename}"
    if "WEATHER" in source_type:
        return f"{root}/raw/weather/{filename}"
    return f"{root}/raw/{filename}"


def count_rows(path: Path) -> int:
    """Jumlah baris data (tanpa header) untuk CSV."""
    return _count_rows(path)


def target_path(source_type: str, filename: str) -> str:
    """Path HDFS raw sesuai jenis sumber."""
    return _target_path(source_type, filename)


def ingest_inbox() -> list[dict[str, Any]]:
    settings.ensure_dirs()
    inbox = Path(settings.INBOX_DIR)
    processed_dir = Path(settings.INBOX_PROCESSED_DIR)
    failed_dir = Path(settings.INBOX_FAILED_DIR)
    staging_dir = Path(settings.STAGING_DIR)

    results: list[dict[str, Any]] = []
    candidates = [
        p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in {".csv", ".json"}
    ]

    for file_path in sorted(candidates):
        filename = file_path.name
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        started_at = _now()
        result: dict[str, Any] = {
            "filename": filename,
            "status": "pending",
            "source_type": "unknown",
            "row_count": 0,
            "hdfs_path": None,
            "message": "",
        }

        try:
            adapter, source_type, _ = detect_format(file_path)
            result["source_type"] = source_type

            if adapter is None or source_type == "unknown":
                dest = failed_dir / f"{ts}_{filename}"
                shutil.move(str(file_path), str(dest))
                result["status"] = "quarantined"
                result["message"] = "Format file tidak dikenali"
                add_quarantine(filename, result["message"], 0)
                add_ingest_log(
                    source_type,
                    "quarantined",
                    details={"file": filename, "reason": result["message"]},
                    started_at=started_at,
                )
                results.append(result)
                continue

            sample = pd.read_csv(file_path, nrows=500)
            validation = adapter.validate(adapter.normalize(sample))
            row_count = _count_rows(file_path)
            result["row_count"] = row_count

            if validation["invalid_count"] > 0 and validation["valid_count"] == 0:
                dest = failed_dir / f"{ts}_{filename}"
                shutil.move(str(file_path), str(dest))
                result["status"] = "quarantined"
                result["message"] = "Validasi gagal: " + "; ".join(validation["errors"])
                add_quarantine(filename, result["message"], row_count)
                add_ingest_log(
                    source_type,
                    "quarantined",
                    rows_in=row_count,
                    rows_quarantined=row_count,
                    details={"file": filename, "reason": result["message"]},
                    started_at=started_at,
                )
                results.append(result)
                continue

            staging_file = staging_dir / f"{source_type}_{ts}_{filename}"
            shutil.copy(str(file_path), str(staging_file))
            hdfs_target = _target_path(source_type, staging_file.name)
            ok, message = _hdfs_put(staging_file, hdfs_target)

            if ok:
                size_bytes = staging_file.stat().st_size if staging_file.exists() else 0
                result.update(
                    status="ingested",
                    hdfs_path=hdfs_target,
                    message="Berhasil diunggah ke HDFS raw",
                )
                shutil.move(str(file_path), str(processed_dir / f"{ts}_{filename}"))
                staging_file.unlink(missing_ok=True)
                add_dataset(
                    name=filename,
                    hdfs_path=hdfs_target,
                    source=source_type,
                    size_bytes=size_bytes,
                    row_count=row_count,
                    detected_format=source_type,
                    ingest_path="auto",
                )
                add_ingest_log(
                    source_type,
                    "success",
                    rows_in=row_count,
                    details={"file": filename, "hdfs_path": hdfs_target},
                    started_at=started_at,
                )
            else:
                result.update(status="failed", message=f"HDFS put error: {message}")
                shutil.move(str(file_path), str(failed_dir / f"{ts}_{filename}"))
                staging_file.unlink(missing_ok=True)
                add_ingest_log(
                    source_type,
                    "failed",
                    rows_in=row_count,
                    details={"file": filename, "error": message},
                    started_at=started_at,
                )
        except Exception as exc:  # noqa: BLE001
            result["status"] = "error"
            result["message"] = str(exc)
            if file_path.exists():
                shutil.move(str(file_path), str(failed_dir / f"{ts}_{filename}"))
            add_ingest_log(
                "unknown",
                "error",
                details={"file": filename, "error": repr(exc)},
                started_at=started_at,
            )

        results.append(result)

    return results


if __name__ == "__main__":
    print(ingest_inbox())
