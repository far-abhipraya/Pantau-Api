r"""Skrip pengunduhan data cuaca historis ERA5 (ECMWF) via Open-Meteo Archive API.

Mengunduh parameter cuaca harian:
- Suhu (maks, min, rerata 2m)
- Presipitasi / Curah hujan harian (mm)
- Kecepatan angin maksimum (km/h)
Data disimpan dalam format CSV di C:\karhutla-data\downloads\weather_era5_daily.csv.
"""
import os
import sys
import csv
import argparse
from pathlib import Path
import requests

DEFAULT_DOWNLOAD_DIR = Path(os.environ.get("DOWNLOADS_DIR", "C:/karhutla-data/downloads"))

# Titik-titik sentral provinsi rawan karhutla di Indonesia
PRIORITY_STATIONS = [
    {"name": "Riau_Pekanbaru", "lat": 0.53, "lon": 101.45},
    {"name": "Riau_Dumai", "lat": 1.68, "lon": 101.45},
    {"name": "Sumsel_Palembang", "lat": -2.99, "lon": 104.76},
    {"name": "Sumsel_Oki", "lat": -3.39, "lon": 105.15},
    {"name": "Jambi_MuaroJambi", "lat": -1.59, "lon": 103.62},
    {"name": "Kalbar_Pontianak", "lat": -0.02, "lon": 109.34},
    {"name": "Kalbar_Ketapang", "lat": -1.84, "lon": 109.97},
    {"name": "Kalteng_Palangkaraya", "lat": -2.21, "lon": 113.92},
    {"name": "Kalteng_Kotawaringin", "lat": -2.53, "lon": 111.75},
    {"name": "Kalsel_Banjarmasin", "lat": -3.32, "lon": 114.59},
]

def download_era5_weather(start_year: int = 2022, end_year: int = 2024, target_dir: Path = DEFAULT_DOWNLOAD_DIR):
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / f"weather_era5_daily_{start_year}_{end_year}.csv"
    print(f"[INFO] Mengunduh data cuaca ERA5 untuk rentang {start_year}-{end_year} ke {out_file}...")

    api_url = "https://archive-api.open-meteo.com/v1/archive"
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"

    all_records = []

    for station in PRIORITY_STATIONS:
        print(f"[DOWNLOAD] Mengambil data ERA5 untuk {station['name']} (lat: {station['lat']}, lon: {station['lon']})...")
        params = {
            "latitude": station["lat"],
            "longitude": station["lon"],
            "start_date": start_date,
            "end_date": end_date,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "precipitation_sum",
                "wind_speed_10m_max"
            ],
            "timezone": "UTC"
        }
        try:
            r = requests.get(api_url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            daily = data.get("daily", {})
            times = daily.get("time", [])

            for i in range(len(times)):
                all_records.append({
                    "date": times[i],
                    "station_name": station["name"],
                    "latitude": station["lat"],
                    "longitude": station["lon"],
                    "temp_max": daily["temperature_2m_max"][i],
                    "temp_min": daily["temperature_2m_min"][i],
                    "temp_mean": daily["temperature_2m_mean"][i],
                    "precipitation": daily["precipitation_sum"][i],
                    "wind_speed_max": daily["wind_speed_10m_max"][i]
                })
        except Exception as e:
            print(f"[ERROR] Gagal mengunduh {station['name']}: {e}")

    if all_records:
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_records[0].keys()))
            writer.writeheader()
            writer.writerows(all_records)
        print(f"[SELESAI] Berhasil menyimpan {len(all_records):,} baris data ERA5 ke {out_file.name}")
    else:
        print("[WARN] Tidak ada data yang berhasil diunduh.")

def main():
    parser = argparse.ArgumentParser(description="ERA5 Weather Downloader")
    parser.add_argument("--start", type=int, default=2022, help="Tahun mulai (default: 2022)")
    parser.add_argument("--end", type=int, default=2024, help="Tahun selesai (default: 2024)")
    parser.add_argument("--dir", type=str, default=str(DEFAULT_DOWNLOAD_DIR), help="Direktori tujuan")
    args = parser.parse_args()

    download_era5_weather(args.start, args.end, Path(args.dir))

if __name__ == "__main__":
    main()
