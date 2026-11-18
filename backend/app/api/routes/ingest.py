"""Endpoint ingest: impor folder `inbox` (FR-N2) sebagai job yang tercatat."""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.pipeline.inbox_job import run_inbox_job
from app.pipeline.job_manager import log_job_start

router = APIRouter(prefix="/ingest", tags=["ingest"])


class InboxRequest(BaseModel):
    run_pipeline: bool = True


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
