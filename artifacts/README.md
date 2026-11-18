# Artefak & Sampel Data

Folder ini berisi **artefak kecil** hasil pipeline supaya isi proyek bisa diperiksa langsung dari GitHub. Dataset penuh **tidak** di-commit (ukuran ~2,1 juta baris, > 100 MB).

## Isi

| Path | Isi |
|---|---|
| `data_samples/hotspot_latest_sample.csv` | 1.000 baris sampel tabel `hotspot_latest` (data clean terbaru, kolom lengkap: koordinat, waktu akuisisi, satelit, confidence, FRP, provinsi, grid). |
| `data_samples/agg_daily_province_sample.csv` | 890 baris agregat harian per provinsi (30 hari terakhir). |
| `data_samples/agg_daily_grid_sample.csv` | 1.000 baris agregat harian per grid 0,25° (30 hari terakhir). |
| `artifacts/reports/pipeline_run_summary.json` | Ringkasan eksekusi pipeline preprocessing (input, output, funnel filter, durasi). |
| `artifacts/reports/profiling_report.json` | Laporan profiling data (statistik kolom, duplikat kunci, desil). |
| `artifacts/reports/serving_meta.json` | Metadata serving layer (jumlah baris per tabel, waktu build). |
| `artifacts/reports/run_*.json` | Ringkasan job Spark historis. |
| `artifacts/reports/manifest.json` | Manifest lokasi data penuh. |

## Lokasi Data Penuh (tidak di Git)

- HDFS: `/karhutla/raw`, `/karhutla/clean/hotspot`, `/karhutla/clean/weather`
- Serving lokal: `C:/karhutla-data/serving/` (`*.parquet`, `pantauapi.duckdb`, `meta.db`)
- Log job: `C:/karhutla-data/serving/logs/jobs/`

## Regenerasi Sampel

```bat
cd backend
set PYTHONPATH=%CD%
python ..\scripts\export_artifacts.py
```
