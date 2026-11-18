"""Endpoint status sumber data untuk strip status dan tab Sumber Data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.core.config import settings
from app.pipeline import catalog
from app.pipeline import job_manager as jm
from app.pipeline.scheduler import scheduler
from app.services import serving

router = APIRouter(tags=["sumber"])

TARGET_ROWS = 1_000_000
SOURCE_META = {
    "SNPP": {"id": "firms_viirs_snpp", "name": "FIRMS VIIRS SNPP", "hdfs": "raw/firms_hist"},
    "NOAA-20": {"id": "firms_viirs_noaa20", "name": "FIRMS VIIRS NOAA-20", "hdfs": "raw/firms_nrt"},
    "NOAA-21": {"id": "firms_viirs_noaa21", "name": "FIRMS VIIRS NOAA-21", "hdfs": "raw/firms_nrt"},
    "Terra": {"id": "firms_modis_terra", "name": "FIRMS MODIS Terra", "hdfs": "raw/firms_hist"},
    "Aqua": {"id": "firms_modis_aqua", "name": "FIRMS MODIS Aqua", "hdfs": "raw/firms_hist"},
}
WEATHER_SOURCES = [
    {"id": "chirps", "name": "CHIRPS (hujan)", "hdfs": "raw/weather"},
    {"id": "era5", "name": "ERA5 (cuaca)", "hdfs": "raw/weather"},
]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


@router.get("/sources", summary="Status sumber data otomatis dan total baris")
def sources() -> dict[str, Any]:
    summary = _read_json(Path(settings.SERVING_DIR) / "pipeline_run_summary.json")
    profiling = _read_json(Path(settings.SERVING_DIR) / "profiling_report.json")
    meta = serving.read_meta()
    datasets_summary = jm.datasets_summary()
    raw = catalog.raw_summary()
    active = jm.active_job()
    ingest_log = jm.list_ingest_log(limit=20)
    last_ingest = ingest_log[0] if ingest_log else None

    sensor_counts = {
        item["satellite"]: int(item["count"]) for item in summary.get("sensors", [])
    }
    date_range = profiling.get("date_range", {})
    raw_rows = int(profiling.get("total_rows") or summary.get("rows", {}).get("input") or 0)
    clean_rows = int(summary.get("rows", {}).get("clean") or 0)

    cards = []
    for satellite, info in SOURCE_META.items():
        rows = sensor_counts.get(satellite, 0)
        cards.append(
            {
                "id": info["id"],
                "name": info["name"],
                "satellite": satellite,
                "kind": "firms",
                "automatic": True,
                "status": "aktif" if rows else "kosong",
                "last_update": meta.get("max_acq_ts"),
                "rows": rows,
                "date_range": date_range,
                "hdfs_path": f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/{info['hdfs']}",
            }
        )
    for info in WEATHER_SOURCES:
        folder = raw["by_folder"].get(info["hdfs"].split("/")[-1], {"files": 0, "bytes": 0})
        cards.append(
            {
                "id": info["id"],
                "name": info["name"],
                "satellite": None,
                "kind": "weather",
                "automatic": True,
                "status": "aktif" if folder["files"] else "kosong",
                "last_update": None,
                "rows": None,
                "date_range": date_range,
                "hdfs_path": f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/{info['hdfs']}",
                "files": folder["files"],
                "size_bytes": folder["bytes"],
            }
        )

    return {
        "generated_at": meta.get("computed_at"),
        "freshness": serving.freshness(),
        "target_rows": TARGET_ROWS,
        "total_raw_rows": raw_rows,
        "clean_rows": clean_rows,
        "indicator": {
            "met": raw_rows >= TARGET_ROWS,
            "progress_percent": round(min(raw_rows / TARGET_ROWS, 1.0) * 100, 1),
        },
        "strip": {
            "hdfs_raw": {"files": raw["files"], "bytes": raw["bytes"]},
            "total_raw_rows": raw_rows,
            "target_rows": TARGET_ROWS,
            "indicator_met": raw_rows >= TARGET_ROWS,
            "last_ingest": {
                "at": (last_ingest or {}).get("started_at"),
                "source": (last_ingest or {}).get("source"),
                "rows": (last_ingest or {}).get("rows_in"),
                "status": (last_ingest or {}).get("status"),
            },
            "spark": {
                "status": "running" if active else "idle",
                "active_job": active["id"] if active else None,
                "active_type": active["job_type"] if active else None,
            },
            "quarantine_count": datasets_summary["quarantine_count"],
            "catalog": datasets_summary,
        },
        "sources": cards,
        "schedule": {
            "nifi": {
                "enabled": True,
                "interval_hours": 3,
                "url": settings.NIFI_URL,
                "next_run": None,
                "note": "Process group karhutla-nrt (Fase 7); NiFi belum berjalan di mesin ini.",
            },
            "folder_import": {
                "enabled": scheduler.status()["enabled"],
                "inbox": str(settings.INBOX_DIR),
                "interval_seconds": settings.INBOX_SCAN_INTERVAL_SEC,
                "next_run": scheduler.status()["next_run"],
                "last_run": scheduler.status()["last_run"],
                "note": "Penjadwal backend memindai inbox; tombol manual juga tersedia.",
            },
        },
        "datasets": jm.list_datasets(limit=200),
        "ingest_log": ingest_log,
    }
