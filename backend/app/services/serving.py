"""Akses serving layer: Parquet lokal -> view DuckDB -> query API.

Semua query memakai DuckDB agar filternya deklaratif dan cepat tanpa
memuat seluruh Parquet ke memori Python.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import duckdb

from app.core.config import settings

SERVING_DIR = Path(settings.SERVING_DIR)
META_PATH = SERVING_DIR / "serving_meta.json"

TABLE_GLOBS: dict[str, Path] = {
    "hotspot_latest": SERVING_DIR / "hotspot_latest",
    "grid_latest_1_0": SERVING_DIR / "grid_latest_1_0",
    "grid_latest_0_5": SERVING_DIR / "grid_latest_0_5",
    "grid_latest_0_25": SERVING_DIR / "grid_latest_0_25",
    "agg_daily_grid": SERVING_DIR / "agg_daily_grid",
    "agg_daily_province": SERVING_DIR / "agg_daily_province",
    "risk_prediction": SERVING_DIR / "risk_prediction",
}

_lock = threading.Lock()
_views_signature: tuple | None = None


def _parquet_glob(path: Path) -> str:
    return (path / "*.parquet").as_posix()


def _signature() -> tuple:
    stamps = []
    for name, path in TABLE_GLOBS.items():
        files = list(path.glob("*.parquet")) if path.exists() else []
        stamps.append((name, len(files), max((f.stat().st_mtime_ns for f in files), default=0)))
    return tuple(stamps)


def read_meta() -> dict[str, Any]:
    if not META_PATH.exists():
        return {}
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def ensure_views(force: bool = False) -> dict[str, bool]:
    """Buat/ganti view DuckDB sesuai file Parquet yang ada.

    View dibuat di file DuckDB agar koneksi read-only per request tetap murah.
    """
    global _views_signature
    with _lock:
        signature = _signature()
        if not force and signature == _views_signature:
            return {name: path.exists() for name, path in TABLE_GLOBS.items()}

        settings.DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(settings.DUCKDB_PATH))
        available: dict[str, bool] = {}
        try:
            for name, path in TABLE_GLOBS.items():
                if path.exists() and any(path.glob("*.parquet")):
                    conn.execute(
                        f"CREATE OR REPLACE VIEW {name} AS "
                        f"SELECT * FROM read_parquet('{_parquet_glob(path)}')"
                    )
                    available[name] = True
                else:
                    conn.execute(f"DROP VIEW IF EXISTS {name}")
                    available[name] = False
        finally:
            conn.close()
        _views_signature = signature
        return available


def connect() -> duckdb.DuckDBPyConnection:
    ensure_views()
    return duckdb.connect(str(settings.DUCKDB_PATH), read_only=True)


def query(sql: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    conn = connect()
    try:
        cursor = conn.execute(sql, list(params or []))
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
    finally:
        conn.close()


def query_one(sql: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def available_tables() -> dict[str, bool]:
    return {
        name: bool(path.exists() and any(path.glob("*.parquet")))
        for name, path in TABLE_GLOBS.items()
    }


def freshness() -> dict[str, Any]:
    meta = read_meta()
    raw = meta.get("max_acq_ts")
    if not raw:
        return {"status": "unknown", "age_hours": None, "max_acq_ts": None, "label": "Belum ada data"}
    try:
        max_ts = datetime.fromisoformat(raw)
    except ValueError:
        return {"status": "unknown", "age_hours": None, "max_acq_ts": raw, "label": "Waktu tidak valid"}
    if max_ts.tzinfo is None:
        max_ts = max_ts.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - max_ts).total_seconds() / 3600
    age = max(0.0, round(age, 2))
    if age < 4:
        status, label = "fresh", "Data terkini"
    elif age < 8:
        status, label = "delayed", "Data tertunda"
    else:
        status, label = "stale", "Data terlambat"
    return {
        "status": status,
        "age_hours": age,
        "max_acq_ts": max_ts.isoformat(),
        "label": label,
    }


def window_start(max_ts: datetime, hours: int) -> datetime:
    return max_ts - timedelta(hours=hours)


# Cache ringan untuk respons agregat yang dipanggil berulang.
_cache: dict[tuple, tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 25


def cached(key: tuple, producer, ttl: int = CACHE_TTL_SECONDS):
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    value = producer()
    _cache[key] = (now, value)
    return value


def invalidate(prefix: str | None = None) -> None:
    """Buang cache agar perubahan data (ingest/hapus) langsung terlihat."""
    if prefix is None:
        _cache.clear()
        return
    for key in [k for k in _cache if k and k[0] == prefix]:
        _cache.pop(key, None)
