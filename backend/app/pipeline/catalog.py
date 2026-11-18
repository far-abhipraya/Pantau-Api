"""Katalog file HDFS raw: sumber kebenaran daftar dataset di halaman Data."""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.pipeline import hdfs
from app.services import serving

RAW_DIRS = {
    "firms_hist": "FIRMS (historis)",
    "firms_nrt": "FIRMS (NRT)",
    "weather": "Cuaca (CHIRPS/ERA5)",
}
DATA_SUFFIXES = (".csv", ".json", ".parquet")
CACHE_KEY = "raw_hdfs_files"


def raw_files(ttl: int = 30) -> list[dict[str, Any]]:
    """Daftar file di `/karhutla/raw/*` (di-cache singkat agar UI tidak lambat)."""

    def produce() -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for folder, label in RAW_DIRS.items():
            path = f"{settings.HDFS_BASE_PATH}/raw/{folder}"
            for entry in hdfs.list_dir(path):
                if entry["type"] != "file":
                    continue
                if not str(entry["name"]).lower().endswith(DATA_SUFFIXES):
                    continue
                items.append(
                    {
                        "hdfs_path": entry["path"],
                        "name": entry["name"],
                        "folder": folder,
                        "origin": label,
                        "size_bytes": entry["size_bytes"],
                        "modified": entry["modified"],
                    }
                )
        return items

    return serving.cached((CACHE_KEY,), produce, ttl=ttl)


def raw_summary() -> dict[str, Any]:
    files = raw_files()
    by_folder: dict[str, dict[str, int]] = {}
    for item in files:
        bucket = by_folder.setdefault(item["folder"], {"files": 0, "bytes": 0})
        bucket["files"] += 1
        bucket["bytes"] += int(item["size_bytes"] or 0)
    return {
        "files": len(files),
        "bytes": sum(int(item["size_bytes"] or 0) for item in files),
        "by_folder": by_folder,
    }


def invalidate() -> None:
    serving.invalidate(CACHE_KEY)
