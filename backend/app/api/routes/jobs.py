"""Endpoint riwayat job: daftar, status, log, dan laporan."""
from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.pipeline import job_manager as jm
from app.pipeline.spark_runner import available_gb, driver_memory, queue

router = APIRouter(prefix="/jobs", tags=["job"])


def _decode(value: Any) -> Any:
    if not value:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def _shape(row: dict[str, Any]) -> dict[str, Any]:
    report = _decode(row.get("report_json")) or {}
    rows_in = None
    rows_out = None
    if isinstance(report, dict):
        rows = report.get("rows")
        if isinstance(rows, dict):
            rows_in = rows.get("input")
            rows_out = rows.get("clean")
        if rows_in is None and "total_rows" in report:
            rows_in = report.get("total_rows")
        if rows_out is None and isinstance(report.get("files"), int):
            rows_out = report.get("files")
    return {
        "id": row["id"],
        "job_type": row["job_type"],
        "status": row["status"],
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
        "rows_in": rows_in,
        "rows_out": rows_out,
        "config": _decode(row.get("config_json")),
    }


@router.get("", summary="Riwayat job (terbaru lebih dahulu)")
def list_jobs(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    job_type: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    items = [_shape(row) for row in jm.list_jobs(limit=limit, job_type=job_type, status=status)]
    effective = driver_memory()
    requested = settings.SPARK_DRIVER_MEMORY
    return {
        "items": items,
        "meta": {
            "count": len(items),
            "queue": queue.snapshot(),
            "driver_memory": effective,
            "requested_driver_memory": requested,
            "memory_clamped": effective != requested,
            "available_gb": available_gb(),
        },
    }


@router.get("/{job_id}", summary="Detail job: log dan laporan")
def get_job(job_id: str) -> dict[str, Any]:
    row = jm.get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    detail = _shape(row)
    detail["log_tail"] = row.get("log_tail") or ""
    detail["report"] = _decode(row.get("report_json")) or {}
    return detail
