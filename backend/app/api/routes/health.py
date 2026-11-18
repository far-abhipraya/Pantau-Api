"""Endpoint kesehatan: backend, serving layer, HDFS, dan status job Spark."""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter

from app.core.config import settings
from app.pipeline import hdfs
from app.pipeline import job_manager as jm
from app.services import serving

router = APIRouter(tags=["sistem"])

_hdfs_cache: tuple[float, bool] | None = None
HDFS_TTL = 30.0


def _hdfs_reachable() -> bool:
    global _hdfs_cache
    now = time.monotonic()
    if _hdfs_cache and now - _hdfs_cache[0] < HDFS_TTL:
        return _hdfs_cache[1]
    ok = hdfs.exists(settings.HDFS_BASE_PATH, timeout=10)
    _hdfs_cache = (now, ok)
    return ok


@router.get("/health", summary="Status backend, HDFS, Spark, dan serving layer")
def health() -> dict[str, Any]:
    tables = serving.available_tables()
    meta = serving.read_meta()
    running = [job for job in jm.get_jobs(limit=10) if job["status"] == "running"]
    hdfs_ok = _hdfs_reachable()
    serving_ok = bool(tables.get("hotspot_latest"))
    return {
        "status": "ok" if hdfs_ok and serving_ok else "degraded",
        "time": serving.freshness().get("max_acq_ts"),
        "hdfs": {"reachable": hdfs_ok, "uri": settings.HDFS_URI},
        "spark": {
            "status": "running" if running else "idle",
            "active_job": running[0]["id"] if running else None,
        },
        "serving": {
            "available": serving_ok,
            "tables": tables,
            "computed_at": meta.get("computed_at"),
            "max_acq_ts": meta.get("max_acq_ts"),
            "freshness": serving.freshness(),
        },
    }
