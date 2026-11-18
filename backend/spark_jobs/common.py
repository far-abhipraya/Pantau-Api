"""Utilitas bersama untuk job Spark PantauApi."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402

CANONICAL_HOTSPOT_COLUMNS = [
    "latitude",
    "longitude",
    "acq_ts_utc",
    "acq_ts_wib",
    "year",
    "month",
    "day",
    "dayofyear",
    "hour",
    "satellite",
    "instrument",
    "confidence_level",
    "confidence_score",
    "brightness",
    "brightness_2",
    "frp",
    "daynight",
    "type",
    "grid_lat",
    "grid_lon",
    "grid_id",
    "province",
    "frp_norm",
    "brightness_norm",
    "source_file",
    "ingest_path",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def spark_ts_to_utc_iso(value: Any) -> str | None:
    """Ubah timestamp PySpark (naif, zona lokal mesin) menjadi ISO UTC.

    PySpark mengembalikan `datetime` tanpa tzinfo yang sudah dikonversi ke zona
    lokal mesin; tanpa koreksi ini meta serving akan salah 7 jam (WIB vs UTC).
    """
    if value is None:
        return None
    if getattr(value, "tzinfo", None) is None:
        value = value.astimezone()
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def get_spark_session(app_name: str):
    from pyspark.sql import SparkSession

    os.environ.setdefault("HADOOP_USER_NAME", settings.HADOOP_USER_NAME)
    builder = (
        SparkSession.builder.appName(app_name)
        .master(settings.SPARK_MASTER)
        .config("spark.driver.memory", settings.SPARK_DRIVER_MEMORY)
        .config("spark.sql.shuffle.partitions", str(settings.SPARK_SHUFFLE_PARTITIONS))
        .config("spark.local.dir", str(settings.SPARK_TMP_DIR))
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.parquet.compression.codec", "snappy")
        .config("spark.pyspark.python", sys.executable)
        .config("spark.pyspark.driver.python", sys.executable)
    )
    return builder.getOrCreate()


def quiet(spark) -> None:
    """Kurangi log INFO Spark agar keluaran job mudah dibaca."""
    spark.sparkContext.setLogLevel("WARN")


def _connect():
    path = Path(settings.SQLITE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(path))


def init_db() -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            config_json TEXT,
            report_json TEXT,
            log_tail TEXT,
            started_at TEXT,
            finished_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS job_history (
            job_id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            input_rows INTEGER DEFAULT 0,
            output_rows INTEGER DEFAULT 0,
            log_message TEXT,
            details_json TEXT
        )
        """
    )
    # Migrasi baris lama job_history -> jobs (tanpa menghapus data lama).
    cur.execute(
        """
        INSERT OR IGNORE INTO jobs (id, job_type, status, config_json, report_json, log_tail, started_at, finished_at)
        SELECT job_id, job_type, status, NULL, details_json, log_message, start_time, end_time
        FROM job_history
        """
    )
    conn.commit()
    conn.close()


def log_job_start(job_id: str, job_type: str, config: dict[str, Any] | None = None) -> None:
    init_db()
    conn = _connect()
    conn.execute(
        """
        INSERT INTO jobs (id, job_type, status, config_json, started_at)
        VALUES (?, ?, 'running', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            job_type=excluded.job_type,
            status='running',
            config_json=excluded.config_json,
            started_at=excluded.started_at,
            finished_at=NULL
        """,
        (job_id, job_type, json.dumps(config or {}), now_utc()),
    )
    conn.commit()
    conn.close()


def log_job_finish(
    job_id: str,
    status: str,
    report: dict[str, Any] | None = None,
    log_tail: str = "",
) -> None:
    init_db()
    conn = _connect()
    conn.execute(
        """
        UPDATE jobs
        SET status=?, report_json=?, log_tail=?, finished_at=?
        WHERE id=?
        """,
        (status, json.dumps(report or {}), log_tail[-8000:], now_utc(), job_id),
    )
    conn.commit()
    conn.close()


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return target


def expand_paths(spark, paths: list[str]) -> list[str]:
    """Kembangkan glob HDFS menjadi daftar file agar header tiap file dibaca terpisah.

    Spark CSV memakai satu header untuk seluruh glob; FIRMS VIIRS dan MODIS
    punya header berbeda, sehingga file harus dibaca satu per satu.
    """
    jvm = spark._jvm
    conf = spark._jsc.hadoopConfiguration()
    expanded: list[str] = []
    for raw in paths:
        candidate = raw
        if len(candidate) > 1 and candidate[1] == ":" and not candidate.startswith("file:"):
            candidate = Path(candidate).resolve().as_uri()
        hadoop_path = jvm.org.apache.hadoop.fs.Path(candidate)
        fs = hadoop_path.getFileSystem(conf)
        statuses = fs.globStatus(hadoop_path)
        if statuses:
            files = [s.getPath().toString() for s in statuses if s.isFile()]
            expanded.extend(sorted(files))
        else:
            expanded.append(candidate)
    return expanded
