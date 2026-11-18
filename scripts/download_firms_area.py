"""Tarik NRT FIRMS per area (bbox Indonesia) memakai FIRMS_MAP_KEY dari `.env`.

Fallback NiFi sesuai PRD FR-N5. API area membatasi rentang 1-5 hari per
permintaan, jadi rentang lebih panjang dipecah menjadi beberapa chunk.
File disimpan di `DOWNLOADS_DIR`, lalu diunggah ke HDFS oleh pipeline.

Contoh:
    python scripts/download_firms_area.py --days 12
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings  # noqa: E402

SOURCES = [
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "MODIS_NRT",
]
API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
MAX_DAYS_PER_REQUEST = 5


def count_rows(path: Path) -> int:
    with path.open("rb") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def fetch_chunk(source: str, start: dt.date, days: int, out_dir: Path) -> tuple[Path | None, int]:
    if not settings.FIRMS_MAP_KEY:
        raise RuntimeError("FIRMS_MAP_KEY kosong di .env")
    url = (
        f"{API}/{settings.FIRMS_MAP_KEY}/{source}/"
        f"{settings.FIRMS_BBOX}/{days}/{start.isoformat()}"
    )
    response = requests.get(url, timeout=120)
    if response.status_code != 200:
        # Jangan pernah mencetak URL (mengandung MAP_KEY).
        print(
            f"[FAIL] {source} {start} ({days}h): HTTP {response.status_code} "
            f"{response.text[:120].strip()!r}"
        )
        return None, 0
    text = response.text.strip()
    if not text or "latitude" not in text:
        print(f"[WARN] {source} {start}: tidak ada data")
        return None, 0

    dest = out_dir / f"fire_nrt_api_{source.lower()}_{start.isoformat()}_{days}d.csv"
    dest.write_text(text + "\n", encoding="utf-8")
    rows = count_rows(dest)
    print(f"[OK] {source} {start} ({days}h): {rows:,} baris -> {dest.name}")
    return dest, rows


def fetch(source: str, days: int, out_dir: Path) -> int:
    today = dt.date.today()
    first = today - dt.timedelta(days=days - 1)
    total = 0
    offset = 0
    while offset < days:
        chunk = min(MAX_DAYS_PER_REQUEST, days - offset)
        start = first + dt.timedelta(days=offset)
        _, rows = fetch_chunk(source, start, chunk, out_dir)
        total += rows
        offset += chunk
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=12, help="jumlah hari terakhir (1-31)")
    parser.add_argument("--dir", type=Path, default=Path(settings.DOWNLOADS_DIR))
    args = parser.parse_args()
    if not 1 <= args.days <= 31:
        parser.error("--days harus 1-31")

    args.dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for source in SOURCES:
        try:
            total += fetch(source, args.days, args.dir)
        except Exception as exc:
            # Hindari kebocoran MAP_KEY lewat pesan exception requests.
            message = str(exc).replace(settings.FIRMS_MAP_KEY, "***")
            print(f"[FAIL] {source}: {type(exc).__name__}: {message}")
    print(f"[DONE] Total baris NRT terunduh: {total:,}")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
