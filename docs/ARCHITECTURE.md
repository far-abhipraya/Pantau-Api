# Arsitektur Sistem PantauApi

## Diagram Alur Data (Arsitektur Tinggi)

```text
+---------------------+      +---------------------+      +---------------------+
|   Sumber Data       |      |   Akuisisi          |      |   Penyimpanan       |
|                     |      |                     |      |                     |
|  NASA FIRMS API     |----->|  NiFi (karhutla-nrt)|----->|  HDFS /karhutla/    |
|  (VIIRS/MODIS NRT)  |      |  timer 3 jam        |      |   raw/              |
|  FIRMS Arsip        |      |  Impor folder       |      |   clean/            |
|  CHIRPS / ERA5      |      |  Upload manual      |      |   features/         |
|  SiPongi+ / BNPB    |      |                     |      |   models/           |
+---------------------+      +---------------------+      +---------------------+
                                                      |
                                                      v
+---------------------+      +---------------------+      +---------------------+
|   Pre-processing    |      |   Serving Layer     |      |   API (FastAPI)     |
|                     |      |                     |      |                     |
|  Spark 4.2.0        |----->|  DuckDB + Parquet   |----->|  /api/map/*         |
|  (clean, aggregate) |      |  (agg_daily_*,      |      |  /api/analytics/*   |
|  MLlib (train/pred) |      |   risk_prediction)  |      |  /api/ingest/*      |
|                     |      |                     |      |  /api/validation/*  |
+---------------------+      +---------------------+      +---------------------+
                                                      |
                                                      v
+---------------------+      +---------------------+      +---------------------+
|   Frontend          |      |   Tampilan          |      |   Validasi          |
|                     |      |                     |      |                     |
|  Next.js 16         |----->|  Peta (/)           |      |  SiPongi+/BNPB      |
|  (TypeScript,       |      |  Data (/data)       |      |  (referensi eksternal)|
|  Tailwind, ECharts) |      |  Analitik (/analytics) |   |                     |
+---------------------+      +---------------------+      +---------------------+
```

## Komponen Sistem

| Komponen | Teknologi | Port | Tujuan |
|----------|-----------|------|--------|
| HDFS | Hadoop 3.5.0 | 9000 (Namenode), 9870 (UI) | Penyimpanan data mentah dan bersih |
| Spark | Spark 4.2.0 | local[4] | Pre-processing, agregasi, ML training/prediksi |
| NiFi | NiFi 1.28.1 | 8080 | Akuisisi NRT FIRMS tiap 3 jam |
| FastAPI | Python 3.14, FastAPI | 8000 | REST API untuk frontend |
| Frontend | Next.js 16.4.5, Turbopack | 3000 | Tiga halaman: Peta, Data, Analitik |
| Serving | DuckDB + Parquet | Lokal | Layer layanan data agregat |
| Metadata | SQLite | Lokal | Job, ingest, karantina, dataset, validasi |

## Alur Data (End-to-End)

1. **Akuisisi**: FIRMS API (NRT) via NiFi atau impor folder/manual → `/karhutla/raw/`
2. **Pre-processing**: Spark membersihkan data → `/karhutla/clean/hotspot` (Parquet)
3. **Agregasi**: Spark menghasilkan tabel serving → `C:\karhutla-data\serving\`
4. **ML**: Spark MLlib melatih model risiko → `/karhutla/models/`, prediksi → `risk_prediction`
5. **API**: FastAPI baca dari DuckDB + Parquet serving layer
6. **Frontend**: Next.js menampilkan tiga halaman dengan data dari API

## Path Penting

| Path | Deskripsi |
|------|-----------|
| `/karhutla/raw/firms_hist` | Data FIRMS historis |
| `/karhutla/raw/firms_nrt/date=YYYY-MM-DD/` | Data FIRMS NRT (NiFi) |
| `/karhutla/raw/weather` | Data cuaca ERA5/CHIRPS |
| `/karhutla/clean/hotspot` | Data bersih (Parquet, partisi tahun/bulan) |
| `/karhutla/features/grid_daily` | Fitur ML (grid-day panel) |
| `/karhutla/models/<versi>` | Model ML terlatih |
| `/karhutla/raw/firms_nrt_compacted` | Hasil kompak file kecil NRT |
| `C:\karhutla-data\serving\` | Tabel serving (DuckDB + Parquet) |
| `C:\karhutla-data\serving\meta.db` | Metadata SQLite |
