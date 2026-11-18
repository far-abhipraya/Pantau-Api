"""Metadata SQLite PantauApi: job, ingest, karantina, dan dataset.

Skema mengikuti PRD Bagian 11. Semua path berasal dari `settings` (.env).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    path = Path(settings.SQLITE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    # timeout agar penulisan dari job Spark dan API tidak saling melempar error.
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.executescript(
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
        );

        CREATE TABLE IF NOT EXISTS ingest_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            rows_in INTEGER DEFAULT 0,
            rows_dup INTEGER DEFAULT 0,
            rows_quarantined INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            details_json TEXT
        );

        CREATE TABLE IF NOT EXISTS quarantine (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            reason TEXT NOT NULL,
            row_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            source TEXT,
            hdfs_path TEXT NOT NULL,
            size_bytes INTEGER DEFAULT 0,
            row_count INTEGER DEFAULT 0,
            column_count INTEGER DEFAULT 0,
            detected_format TEXT,
            ingest_path TEXT,
            created_at TEXT NOT NULL
        );
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
        (job_id, job_type, json.dumps(config or {}), _now()),
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
        UPDATE jobs SET status=?, report_json=?, log_tail=?, finished_at=? WHERE id=?
        """,
        (status, json.dumps(report or {}), log_tail[-8000:], _now(), job_id),
    )
    conn.commit()
    conn.close()


def log_job(
    job_id: str,
    job_type: str,
    status: str,
    report: dict[str, Any] | None = None,
    log_message: str = "",
) -> None:
    """Kompatibilitas untuk pemanggil lama."""
    log_job_start(job_id, job_type)
    log_job_finish(job_id, status, report, log_message)


def get_jobs(limit: int = 20) -> list[dict[str, Any]]:
    init_db()
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM jobs ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Nama lama yang masih dipakai kode lain.
get_job_history = get_jobs


def get_job(job_id: str) -> dict[str, Any] | None:
    init_db()
    conn = _connect()
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_jobs(
    limit: int = 50, job_type: str | None = None, status: str | None = None
) -> list[dict[str, Any]]:
    init_db()
    clauses = []
    params: list[Any] = []
    if job_type:
        clauses.append("job_type = ?")
        params.append(job_type)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    conn = _connect()
    rows = conn.execute(
        f"SELECT * FROM jobs {where} ORDER BY started_at DESC LIMIT ?", params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def active_job() -> dict[str, Any] | None:
    init_db()
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM jobs WHERE status IN ('running', 'queued') ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_job_log(job_id: str, log_tail: str) -> None:
    init_db()
    conn = _connect()
    conn.execute("UPDATE jobs SET log_tail=? WHERE id=?", (log_tail[-8000:], job_id))
    conn.commit()
    conn.close()


def update_job_status(job_id: str, status: str, started_at: str | None = None) -> None:
    init_db()
    conn = _connect()
    if started_at:
        conn.execute(
            "UPDATE jobs SET status=?, started_at=? WHERE id=?", (status, started_at, job_id)
        )
    else:
        conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()
    conn.close()


def list_datasets(limit: int = 200) -> list[dict[str, Any]]:
    init_db()
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM datasets ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dataset(dataset_id: int) -> dict[str, Any] | None:
    init_db()
    conn = _connect()
    row = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_dataset(dataset_id: int) -> bool:
    init_db()
    conn = _connect()
    cursor = conn.execute("DELETE FROM datasets WHERE id=?", (dataset_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def datasets_summary() -> dict[str, Any]:
    """Ringkasan untuk strip status dan indikator 1 juta baris."""
    init_db()
    conn = _connect()
    row = conn.execute(
        """
        SELECT count(*) AS files,
               coalesce(sum(size_bytes), 0) AS total_size_bytes,
               coalesce(sum(row_count), 0) AS total_rows
        FROM datasets
        """
    ).fetchone()
    quarantine = conn.execute("SELECT count(*) AS total FROM quarantine").fetchone()
    conn.close()
    return {
        "files": int(row["files"]),
        "total_size_bytes": int(row["total_size_bytes"]),
        "total_rows": int(row["total_rows"]),
        "quarantine_count": int(quarantine["total"]),
    }


def list_ingest_log(limit: int = 20) -> list[dict[str, Any]]:
    init_db()
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM ingest_log ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_ingest_log(
    source: str,
    status: str,
    rows_in: int = 0,
    rows_dup: int = 0,
    rows_quarantined: int = 0,
    details: dict[str, Any] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> None:
    init_db()
    conn = _connect()
    conn.execute(
        """
        INSERT INTO ingest_log
            (source, started_at, finished_at, rows_in, rows_dup, rows_quarantined, status, details_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source,
            started_at or _now(),
            finished_at or _now(),
            rows_in,
            rows_dup,
            rows_quarantined,
            status,
            json.dumps(details or {}),
        ),
    )
    conn.commit()
    conn.close()


def add_quarantine(file_name: str, reason: str, row_count: int = 0) -> None:
    init_db()
    conn = _connect()
    conn.execute(
        "INSERT INTO quarantine (file_name, reason, row_count, created_at) VALUES (?, ?, ?, ?)",
        (file_name, reason, row_count, _now()),
    )
    conn.commit()
    conn.close()


def list_quarantine(limit: int = 100) -> list[dict[str, Any]]:
    init_db()
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM quarantine ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_dataset(
    name: str,
    hdfs_path: str,
    source: str = "",
    size_bytes: int = 0,
    row_count: int = 0,
    column_count: int = 0,
    detected_format: str = "",
    ingest_path: str = "auto",
) -> None:
    init_db()
    conn = _connect()
    conn.execute(
        """
        INSERT INTO datasets
            (name, source, hdfs_path, size_bytes, row_count, column_count,
             detected_format, ingest_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            source,
            hdfs_path,
            size_bytes,
            row_count,
            column_count,
            detected_format,
            ingest_path,
            _now(),
        ),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database siap: {settings.SQLITE_PATH}")
