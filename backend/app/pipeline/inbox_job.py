"""Job impor folder `inbox` (FR-N2), dipakai tombol manual dan penjadwal."""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.pipeline import catalog
from app.pipeline.ingest import ingest_inbox
from app.pipeline.job_manager import log_job_finish, log_job_start


def run_inbox_job(job_id: str, run_pipeline: bool = True) -> dict[str, Any]:
    """Deteksi -> HDFS raw -> metadata -> (opsional) pre-processing."""
    log_job_start(job_id, "INGEST_FOLDER", {"inbox": str(settings.INBOX_DIR)})
    try:
        results = ingest_inbox()
        ingested = [item for item in results if item["status"] == "ingested"]
        quarantined = [item for item in results if item["status"] == "quarantined"]
        report: dict[str, Any] = {
            "files": len(results),
            "ingested": len(ingested),
            "quarantined": len(quarantined),
            "rows_in": sum(int(item.get("row_count") or 0) for item in ingested),
            "results": results,
        }
        if run_pipeline and ingested:
            from app.pipeline.upload import trigger_pipeline

            submission = trigger_pipeline({"file": f"{len(ingested)} file"})
            report["pipeline_job_id"] = submission["job_id"] if submission else None
        log_job_finish(job_id, "COMPLETED", report)
        return report
    except Exception as exc:  # noqa: BLE001 - laporkan ke riwayat job
        log_job_finish(job_id, "FAILED", {"error": repr(exc)})
        return {"error": repr(exc)}
    finally:
        catalog.invalidate()


def inbox_has_files() -> bool:
    inbox = settings.INBOX_DIR
    if not inbox.exists():
        return False
    return any(
        p.is_file() and p.suffix.lower() in {".csv", ".json"}
        for p in inbox.iterdir()
    )
