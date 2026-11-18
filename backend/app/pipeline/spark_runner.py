"""Antrian tunggal untuk job Spark: `spark-submit` asinkron + log + status.

Aturan (AGENTS.md / PRD Bagian 9):
- Satu job Spark aktif pada satu waktu; job lain menunggu sebagai `queued`.
- Log job disimpan di `settings.JOB_LOG_DIR` dan cuplikannya di tabel `jobs`.
- Memori driver tidak dinaikkan; bila RAM bebas kurang, nilainya diturunkan
  (bukan dinaikkan) agar tidak OOM.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.pipeline import job_manager as jm

REPO_ROOT = Path(__file__).resolve().parents[3]
SPARK_JOBS_DIR = REPO_ROOT / "backend" / "spark_jobs"
TAIL_LINES = 120
RESERVE_GB = 1.0
MIN_DRIVER_GB = 2.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_memory_gb(value: str) -> float:
    text = (value or "").strip().lower()
    try:
        if text.endswith("g"):
            return float(text[:-1])
        if text.endswith("m"):
            return float(text[:-1]) / 1024
    except ValueError:
        pass
    return 4.0


def available_gb() -> float:
    try:
        import psutil

        return round(psutil.virtual_memory().available / 1024**3, 2)
    except Exception:  # pragma: no cover - psutil tidak wajib
        return 0.0


def driver_memory() -> str:
    """Turunkan memori driver bila RAM bebas tidak cukup (tidak pernah naik).

    Batas bawah `MIN_DRIVER_GB` menjaga job tetap dapat berjalan; bila hasilnya
    lebih kecil dari konfigurasi, nilainya dilaporkan lewat `/api/jobs`.
    """
    requested = parse_memory_gb(settings.SPARK_DRIVER_MEMORY)
    free = available_gb()
    if free <= 0:
        return settings.SPARK_DRIVER_MEMORY
    usable = max(MIN_DRIVER_GB, free - RESERVE_GB)
    chosen = max(MIN_DRIVER_GB, min(requested, usable))
    return f"{int(chosen)}g"


def spark_submit_binary() -> str:
    if settings.SPARK_SUBMIT:
        return settings.SPARK_SUBMIT
    found = shutil.which("spark-submit")
    if found:
        return found
    spark_home = os.environ.get("SPARK_HOME", "")
    if spark_home:
        candidate = Path(spark_home) / "bin" / "spark-submit.cmd"
        if candidate.exists():
            return str(candidate)
    raise RuntimeError("spark-submit tidak ditemukan; set SPARK_SUBMIT atau SPARK_HOME")


def build_command(script: str, args: list[str], driver: str) -> list[str]:
    return [
        spark_submit_binary(),
        "--master",
        settings.SPARK_MASTER,
        "--driver-memory",
        driver,
        str(SPARK_JOBS_DIR / script),
        *args,
    ]


def _log_path(job_id: str) -> Path:
    return Path(settings.JOB_LOG_DIR) / f"{job_id}.log"


def _read_tail(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-TAIL_LINES:])


class SparkQueue:
    """Worker tunggal: satu job berjalan, sisanya menunggu."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queue: deque[tuple[str, str, list[str], str, dict[str, Any]]] = deque()
        self._worker: threading.Thread | None = None
        self._current: str | None = None

    # --- API publik -----------------------------------------------------
    def submit(
        self,
        job_id: str,
        job_type: str,
        script: str,
        args: list[str],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        settings.ensure_dirs()
        with self._lock:
            driver = driver_memory()
            payload = {"config": config or {}, "script": script, "driver_memory": driver}
            jm.log_job_start(job_id, job_type, payload)
            jm.update_job_status(job_id, "queued")
            self._queue.append((job_id, job_type, [*args], script, payload))
            position = len(self._queue) + (1 if self._current else 0)
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._work, name="spark-queue", daemon=True)
                self._worker.start()
        return {"job_id": job_id, "job_type": job_type, "status": "queued", "queue_position": position}

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._current,
                "queued": [item[0] for item in self._queue],
            }

    # --- Worker ---------------------------------------------------------
    def _work(self) -> None:
        while True:
            with self._lock:
                if not self._queue:
                    self._worker = None
                    return
                job_id, job_type, args, script, payload = self._queue.popleft()
                self._current = job_id

            try:
                self._run(job_id, job_type, script, args, payload)
            except Exception as exc:  # pragma: no cover - pelindung worker
                jm.log_job_finish(job_id, "FAILED", {"error": repr(exc)})
            finally:
                with self._lock:
                    self._current = None

    def _run(
        self,
        job_id: str,
        job_type: str,
        script: str,
        args: list[str],
        payload: dict[str, Any],
    ) -> str:
        log_file = _log_path(job_id)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        command = build_command(script, args, payload["driver_memory"])
        jm.update_job_status(job_id, "running", started_at=_now())

        env = os.environ.copy()
        env["HADOOP_USER_NAME"] = settings.HADOOP_USER_NAME
        env.setdefault("PYSPARK_PYTHON", sys.executable)
        env.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
        env["PYTHONIOENCODING"] = "utf-8"

        with log_file.open("w", encoding="utf-8", errors="replace") as handle:
            handle.write(f"$ {' '.join(command)}\n\n")
            handle.flush()
            process = subprocess.Popen(
                command,
                stdout=handle,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=str(REPO_ROOT),
            )

        # Cuplik log ke DB selama proses berjalan (UI polling).
        while process.poll() is None:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                jm.update_job_log(job_id, _read_tail(log_file))

        exit_code = process.returncode
        jm.update_job_log(job_id, _read_tail(log_file))

        row = jm.get_job(job_id) or {}
        if row.get("status") in {"COMPLETED", "FAILED"}:
            # Job Spark sudah menulis kesimpulannya sendiri (common.log_job_finish).
            final = row["status"]
            if final == "FAILED":
                jm.log_job_finish(job_id, "FAILED", _safe_report(row), _read_tail(log_file))
            return final

        if exit_code == 0:
            jm.log_job_finish(job_id, "COMPLETED", {"exit_code": 0}, _read_tail(log_file))
            return "COMPLETED"

        jm.log_job_finish(
            job_id,
            "FAILED",
            {"exit_code": exit_code},
            _read_tail(log_file),
        )
        return "FAILED"


def _safe_report(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("report_json")
    if not raw:
        return {}
    import json

    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


queue = SparkQueue()
