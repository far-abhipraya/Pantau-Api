import os
import subprocess
from pathlib import Path
from typing import List, Tuple
from app.config import settings

def hadoop_env() -> dict:
    env = os.environ.copy()
    env["HADOOP_USER_NAME"] = settings.HADOOP_USER_NAME
    return env

def run_hdfs(args: List[str], timeout: int = 600) -> Tuple[int, str, str]:
    """Menjalankan perintah hdfs dfs dengan timeout dan env HADOOP_USER_NAME."""
    cmd = ["hdfs", "dfs"] + args
    try:
        p = subprocess.run(
            cmd,
            env=hadoop_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "HDFS command timed out"
    except Exception as e:
        return 1, "", str(e)

def hdfs_put(local_path: Path, hdfs_path: str) -> Tuple[bool, str]:
    """Upload file dari lokal ke HDFS (-f overwrite)."""
    code, stdout, stderr = run_hdfs(["-put", "-f", str(local_path), hdfs_path])
    if code == 0:
        return True, ""
    return False, stderr or stdout

def hdfs_du(hdfs_path: str) -> int:
    """Mengembalikan ukuran file/folder di HDFS dalam byte menggunakan -du -s."""
    code, stdout, stderr = run_hdfs(["-du", "-s", hdfs_path])
    if code == 0 and stdout:
        parts = stdout.split()
        if parts:
            try:
                return int(parts[0])
            except ValueError:
                pass
    return -1

def hdfs_count(hdfs_path: str) -> Tuple[int, int, int]:
    """Mengembalikan (dir_count, file_count, byte_size) via -count."""
    code, stdout, stderr = run_hdfs(["-count", hdfs_path])
    if code == 0 and stdout:
        parts = stdout.split()
        if len(parts) >= 3:
            try:
                return int(parts[0]), int(parts[1]), int(parts[2])
            except ValueError:
                pass
    return (0, 0, 0)

def hdfs_ls(hdfs_path: str) -> List[dict]:
    """List isi direktori HDFS."""
    code, stdout, stderr = run_hdfs(["-ls", hdfs_path])
    items = []
    if code == 0 and stdout:
        for line in stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("Found"):
                continue
            parts = line.split(maxsplit=7)
            if len(parts) >= 8:
                items.append({
                    "permissions": parts[0],
                    "replication": parts[1],
                    "owner": parts[2],
                    "group": parts[3],
                    "size": int(parts[4]) if parts[4].isdigit() else 0,
                    "date": f"{parts[5]} {parts[6]}",
                    "path": parts[7]
                })
    return items

def hdfs_rm(hdfs_path: str) -> Tuple[bool, str]:
    """Menghapus file di HDFS. Hanya diperbolehkan di bawah /karhutla."""
    norm_path = hdfs_path.replace("\\", "/")
    if ".." in norm_path or not norm_path.startswith("/karhutla/"):
        return False, "Operasi hapus hanya diizinkan di dalam path /karhutla/"
    code, stdout, stderr = run_hdfs(["-rm", "-r", "-skipTrash", norm_path])
    if code == 0:
        return True, ""
    return False, stderr or stdout

