r"""Skrip pengunduhan dan verifikasi data NASA FIRMS untuk Indonesia.

Mendukung:
1. Unduhan langsung NRT publik (7 hari terakhir VIIRS & MODIS) tanpa perlu MAP_KEY.
2. Unduhan NRT via FIRMS API area bbox bila FIRMS_MAP_KEY tersedia di .env.
3. Penghitungan dan validasi baris seluruh file di C:\karhutla-data\downloads.
"""
import os
import sys
import argparse
from pathlib import Path
import requests

DEFAULT_DOWNLOAD_DIR = Path(os.environ.get("DOWNLOADS_DIR", "C:/karhutla-data/downloads"))
INDONESIA_BBOX = os.environ.get("FIRMS_BBOX", "95,-11,141,6")

OPEN_NRT_FEEDS = {
    "viirs_snpp_7d": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_SouthEast_Asia_7d.csv",
    "viirs_noaa20_7d": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_SouthEast_Asia_7d.csv",
    "modis_7d": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_SouthEast_Asia_7d.csv"
}

def count_file_rows(file_path: Path) -> int:
    """Hitung baris CSV secara streaming."""
    count = 0
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for _ in f:
            count += 1
    return count

def download_open_nrt(target_dir: Path, filter_indonesia: bool = True):
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Mengunduh open NRT feeds ke {target_dir}...")
    
    # Bbox Indonesia
    min_lon, min_lat, max_lon, max_lat = [float(x) for x in INDONESIA_BBOX.split(",")]

    for key, url in OPEN_NRT_FEEDS.items():
        dest = target_dir / f"firms_nrt_{key}.csv"
        print(f"[DOWNLOAD] {key} dari {url}...")
        try:
            r = requests.get(url, stream=True, timeout=30)
            r.raise_for_status()

            header = None
            total_read = 0
            filtered_count = 0

            with open(dest, "w", encoding="utf-8", newline="") as out:
                for line in r.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode("utf-8")
                    if header is None:
                        header = line_str
                        out.write(header + "\n")
                        continue

                    total_read += 1
                    if filter_indonesia:
                        parts = line_str.split(",")
                        try:
                            lat = float(parts[0])
                            lon = float(parts[1])
                            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                                out.write(line_str + "\n")
                                filtered_count += 1
                        except (ValueError, IndexError):
                            continue
                    else:
                        out.write(line_str + "\n")
                        filtered_count += 1

            print(f"[SELESAI] {dest.name}: {filtered_count} baris Indonesia (dari total {total_read} SE Asia).")
        except Exception as e:
            print(f"[ERROR] Gagal mengunduh {key}: {e}")

def check_download_summary(target_dir: Path):
    """Menghitung total baris seluruh CSV di target_dir."""
    print(f"\n================ SUMMARY DATASET DI {target_dir} ================")
    csv_files = sorted(set(target_dir.glob("*.csv")).union(target_dir.glob("**/*.csv")))
    if not csv_files:
        print("[WARN] Belum ada file CSV di folder downloads.")
        return 0

    total_rows = 0
    print(f"{'Nama File':<45} | {'Ukuran (MB)':<12} | {'Jumlah Baris':<12}")
    print("-" * 75)
    for f in csv_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        rows = count_file_rows(f) - 1 # kurangi header
        total_rows += max(0, rows)
        print(f"{f.name:<45} | {size_mb:<12.2f} | {rows:<12,}")
    print("-" * 75)
    print(f"Total Baris Data Mentah: {total_rows:,}")
    if total_rows >= 1_000_000:
        print("[STATUS: MEMENUHI] Target minimal >= 1.000.000 baris tercapai!")
    else:
        print(f"[STATUS: BELUM] Kurang {1_000_000 - total_rows:,} baris untuk mencapai target minimal 1.000.000.")
    print("=================================================================\n")
    return total_rows

def main():
    parser = argparse.ArgumentParser(description="NASA FIRMS Downloader & Inspector")
    parser.add_argument("--open-nrt", action="store_true", help="Unduh NRT 7 hari gratis langsung dari server FIRMS")
    parser.add_argument("--count", action="store_true", help="Hitung rekap baris dataset di downloads")
    parser.add_argument("--dir", type=str, default=str(DEFAULT_DOWNLOAD_DIR), help="Direktori target unduhan")
    args = parser.parse_args()

    target_dir = Path(args.dir)

    if args.open_nrt:
        download_open_nrt(target_dir)

    if args.count or not args.open_nrt:
        check_download_summary(target_dir)

if __name__ == "__main__":
    main()
