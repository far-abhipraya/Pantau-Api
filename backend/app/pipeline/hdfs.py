"""Pembungkus perintah HDFS untuk API PantauApi.

Aturan (AGENTS.md):
- Semua proses memakai env `HADOOP_USER_NAME`.
- Tidak memakai `hdfs dfs -stat` dengan format `%`; pakai `-ls`, `-du`, `-count`.
- Upload/ingest selalu staging lokal lalu `hdfs dfs -put`.
- Penghapusan hanya diizinkan di bawah `settings.HDFS_BASE_PATH`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from app.core.config import settings


class HdfsError(RuntimeError):
    """Perintah HDFS gagal."""


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["HADOOP_USER_NAME"] = settings.HADOOP_USER_NAME
    return env


def _binary() -> str:
    binary = shutil.which("hdfs")
    if not binary:
        raise HdfsError("Perintah `hdfs` tidak ditemukan di PATH")
    return binary


def run(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    command = [_binary(), "dfs", *args]
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=_env(),
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise HdfsError((proc.stderr or proc.stdout).strip() or f"gagal: {command}")
    return proc


def exists(path: str, timeout: int = 30) -> bool:
    """Cek keberadaan memakai `hdfs dfs -ls` (AGENTS.md melarang `-stat %`).

    `hdfs dfs -test -e` tidak dipakai: pada Hadoop 3.5.0 di Windows, kode
    keluarnya tidak dapat diandalkan dan pernah menggantung.
    """
    try:
        proc = subprocess.run(
            [_binary(), "dfs", "-ls", path],
            capture_output=True,
            text=True,
            env=_env(),
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    expected = path.rstrip("/")
    return expected in (proc.stdout or "")


def remove(path: str, recursive: bool = True) -> None:
    """Hapus hanya di bawah HDFS_BASE_PATH (pagarnya di sini, bukan di UI)."""
    if not is_within_base(path):
        raise HdfsError(f"Penghapusan hanya diizinkan di bawah {settings.HDFS_BASE_PATH}")
    args = ["-rm", "-f", "-skipTrash"]
    if recursive:
        args.append("-r")
    args.append(path)
    run(args)


def is_within_base(path: str) -> bool:
    normalized = path.strip().rstrip("/")
    base = settings.HDFS_BASE_PATH.rstrip("/")
    return normalized == base or normalized.startswith(base + "/")


def put(local_path: Path, hdfs_path: str) -> None:
    run(["-put", "-f", str(local_path), hdfs_path], timeout=600)


def du_bytes(path: str, timeout=60) -> int:
    """Ukuran total (byte) memakai `hdfs dfs -du -s` (kolom pertama)."""
    try:
        proc = run(["-du", "-s", path], timeout=timeout)
    except HdfsError:
        return 0
    first = (proc.stdout or "").strip().splitlines()
    if not first:
        return 0
    parts = first[0].split()
    try:
        return int(parts[0])
    except (IndexError, ValueError):
        return 0


def count_files(path: str, timeout: int = 60) -> int:
    """Jumlah file memakai `hdfs dfs -count` (kolom kedua)."""
    try:
        proc = run(["-count", path], timeout=timeout)
    except HdfsError:
        return 0
    parts = (proc.stdout or "").strip().split()
    if len(parts) < 2:
        return 0
    try:
        return int(parts[1])
    except ValueError:
        return 0


def list_dir(path: str, timeout: int = 60) -> list[dict[str, object]]:
    """Daftar isi direktori memakai `hdfs dfs -ls` (bukan `-stat` format %)."""
    try:
        proc = run(["-ls", path], timeout=timeout)
    except HdfsError:
        return []
    entries: list[dict[str, object]] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith(("d", "-", "l")):
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        entries.append(
            {
                "permission": parts[0],
                "type": "dir" if parts[0].startswith("d") else "file",
                "size_bytes": int(parts[4]) if parts[4].isdigit() else 0,
                "modified": f"{parts[5]} {parts[6]}",
                "path": parts[-1],
                "name": parts[-1].rstrip("/").split("/")[-1],
            }
        )
    return entries


def head_lines(path: str, limit: int = 50, timeout: int = 60) -> list[str]:
    """Baca awal file tanpa memuat seluruh isi (untuk pratinjau)."""
    proc = subprocess.Popen(
        [_binary(), "dfs", "-cat", path],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(),
    )
    lines: list[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line.rstrip("\r\n"))
            if len(lines) >= limit:
                break
    finally:
        proc.stdout and proc.stdout.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover - proses bandel
            proc.kill()
    return lines
