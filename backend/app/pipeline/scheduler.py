"""Penjadwal impor folder `inbox` (FR-N2).

Sederhana dan aman: hanya memindai folder, hanya menjalankan job bila ada file
baru dan tidak ada job lain yang berjalan. Tidak menjalankan Spark langsung.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.pipeline import job_manager as jm
from app.pipeline.inbox_job import inbox_has_files, run_inbox_job
from app.pipeline.spark_runner import queue


class InboxScheduler:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._state: dict[str, Any] = {
            "enabled": False,
            "interval_sec": int(settings.INBOX_SCAN_INTERVAL_SEC),
            "next_run": None,
            "last_run": None,
            "last_job_id": None,
            "last_result": None,
        }

    # --- Siklus hidup ---------------------------------------------------
    def start(self) -> dict[str, Any]:
        interval = int(settings.INBOX_SCAN_INTERVAL_SEC)
        if interval <= 0 or self._thread is not None:
            self._state["enabled"] = interval > 0
            return self.status()
        self._state["enabled"] = True
        self._state["next_run"] = self._next_time(interval)
        self._thread = threading.Thread(target=self._loop, name="inbox-scheduler", daemon=True)
        self._thread.start()
        return self.status()

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> dict[str, Any]:
        return dict(self._state)

    # --- Internal -------------------------------------------------------
    @staticmethod
    def _next_time(interval: int) -> str:
        return (datetime.now(timezone.utc) + timedelta(seconds=interval)).isoformat(timespec="seconds")

    def _loop(self) -> None:
        interval = int(settings.INBOX_SCAN_INTERVAL_SEC)
        while not self._stop.wait(interval):
            try:
                self._tick()
            except Exception as exc:  # pragma: no cover - penjadwal tidak boleh mati
                self._state["last_result"] = f"error: {exc!r}"
            finally:
                self._state["next_run"] = self._next_time(interval)

    def _tick(self) -> None:
        if not inbox_has_files():
            self._state["last_result"] = "tidak ada file baru"
            return
        if queue.snapshot()["running"] or jm.active_job():
            self._state["last_result"] = "ditunda: ada job berjalan"
            return
        job_id = f"ingest-scan-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        self._state["last_job_id"] = job_id
        self._state["last_run"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        report = run_inbox_job(job_id, run_pipeline=True)
        self._state["last_result"] = report


scheduler = InboxScheduler()
