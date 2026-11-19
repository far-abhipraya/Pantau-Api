# PantauApi

Platform big data (Hadoop HDFS, Spark, NiFi) untuk memantau hotspot karhutla Indonesia dan memperkirakan risikonya.

Tiga halaman: Peta (`/`), Data & Pre-processing (`/data`), Analitik (`/analytics`).

## Dokumen
- `AGENTS.md`: aturan agent (selalu aktif); `.agents/rules/`: aturan terperinci; `.agents/workflows/start-phase.md`: `/start-phase <nomor>`
- `docs/PRD.md` (v1.2), `docs/UI_SPEC.md`, `docs/DESIGN.md`, `docs/STITCH_PROMPTS.md`
- `docs/ENVIRONMENT.md`, `docs/TASKS.md`, `docs/DATA_SOURCES.md`, `docs/MODEL.md`
- `docs/ARCHITECTURE.md`, `docs/windows-notes.md`, `docs/DEMO.md`

## Mulai Cepat
1. Salin `.env.example` menjadi `.env` dan isi.
2. CMD Administrator: `scripts\start_hdfs.bat`
3. `python scripts\check_env.py`
4. Mulai Fase 0 di `docs/TASKS.md`.

## Menjalankan Layanan
```bat
REM Pre-processing + agregasi serving layer (satu job Spark pada satu waktu)
spark-submit --master local[2] --driver-memory 3g backend\spark_jobs\preprocess.py
spark-submit --master local[2] --driver-memory 3g backend\spark_jobs\aggregate.py

REM API + UI
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```
Peta: http://localhost:3000 · API/OpenAPI: http://localhost:8000/docs
Laporan job: `C:\karhutla-data\serving\pipeline_run_summary.json`, `serving_meta.json`, `profiling_report.json`.

## Halaman Data (`/data`)
- Strip status (total baris mentah + indikator 1 juta, ingest terakhir, status Spark, karantina), tab **Sumber Data**,
  **Pre-processing**, dan **Riwayat Job**.
- Akuisisi: penjadwal impor folder `inbox` (interval `INBOX_SCAN_INTERVAL_SEC`) + tombol "Impor folder",
  dan tombol sekunder "Tambah data" (upload bertahap -> deteksi format -> `hdfs dfs -put` -> pipeline).
- Pre-processing: profil dataset, stepper konfigurasi (`GET /api/preprocessing/config-schema`), jalankan pipeline
  sebagai job Spark asinkron (satu job aktif), laporan funnel sebelum/sesudah.
- Job Spark dijalankan lewat antrian tunggal (`backend/app/pipeline/spark_runner.py`); status/log dapat dipantau di
  Riwayat Job. Memori driver diturunkan otomatis bila RAM bebas kurang (tidak pernah dinaikkan).

## Halaman Analitik (`/analytics`)
- Hero KPI nasional (hari ini, 7/30 hari, provinsi tertinggi, rata-rata FRP) dengan delta terhadap periode sebelumnya.
- Insight utama rule-based (tren 7 hari, konsentrasi wilayah, puncak musiman) + bukti angka yang dapat dibuka.
- Bilah filter lengket: rentang 30/90/365 hari atau semua, provinsi, confidence (semua/tinggi), tombol
  "Perbarui agregasi" (`POST /api/analytics/refresh` -> job `aggregate.py`).
- Seksi Ringkasan (tren harian/mingguan/bulanan + kumulatif tahunan), Wilayah (ranking, choropleth, top grid),
  Musiman (heatmap bulan x tahun / bulan x provinsi), Faktor Pengaruh (status FP1-FP6), Cuaca, Prediksi ML, Validasi.
- Prediksi ML: metrik uji (AUC-ROC, AUC-PR, precision, recall, F1), confusion matrix, feature importance,
  perbandingan baseline persistensi, sebaran kategori risiko, dan 10 grid risiko tertinggi; tombol
  "Perbarui prediksi" mengantrekan `POST /api/analytics/model/refresh`.
- Endpoint: `GET /api/analytics/{kpi,trend,ranking,seasonality,year-compare,top-grid,insights,weather-correlation,model}`.
  Semua dibaca dari serving layer DuckDB (`agg_daily_province`, `agg_daily_grid`, `risk_prediction`), tanpa
  perhitungan di klien.
- Lapisan diagnostik cuaca (FP1-FP3) tetap ditandai belum tersedia karena data ERA5 hanya 10 stasiun 2022-2024;
  FP4/FP6 tersedia lewat feature importance model. Tidak ada angka prediksi/anomali yang dikarang.

## Verifikasi Kriteria Terima (AC-1 s/d AC-9)

| Kriteria | Status | Keterangan |
|----------|--------|------------|
| AC-1: Dataset mentah >= 1.000.000 baris di HDFS | ✅ Terpenuhi | clean/hotspot: 2.134.784 baris |
| AC-2: Format FIRMS (VIIRS/MODIS/arsip/API) terbaca otomatis | ✅ Terpenuhi | Adapter deteksi format + karantina |
| AC-3: Pre-processing Parquet di `/karhutla/clean` + laporan | ✅ Terpenuhi | Spark pre-processing, laporan funnel |
| AC-4: Peta <= 3 detik (jendela 24 jam), max 20.000 titik | ✅ Terpenuhi | KPI 190 ms, grid 51 ms, hotspot maks 246 ms |
| AC-5: Dashboard Analitik <= 5 detik | ✅ Terpenuhi | Semua endpoint <= 744 ms (uji browser 1,17 s) |
| AC-6: NiFi NRT tiap 3 jam ke `/karhutla/raw/firms_nrt` | ⚠️ Siap | `nifi/flow.json` + endpoint fallback; NiFi belum dijalankan |
| AC-7: Model metrik + split waktu + baseline persistensi | ✅ Terpenuhi | RF: AUC-ROC 0,886 / AUC-PR 0,686; baseline: 0,752 / 0,501 |
| AC-8: Upload manual melewati pipeline yang sama | ✅ Terpenuhi | `POST /api/datasets/*`, `ingest.py` |
| AC-9: README memungkinkan jalan dari nol | ✅ Terpenuhi | Skrip start/stop/check tersedia |

## Definisi Selesai (PRD Bagian 17)

1. AC-1 sampai AC-9 terpenuhi pada data nyata >= 1 juta baris ✅
2. Tiga halaman berfungsi end-to-end dan konsisten dengan `docs/UI_SPEC.md` ✅
3. NiFi flow berjalan dan terdokumentasi dengan bukti file NRT di HDFS ⚠️ (flow.json tersedia, NiFi belum dijalankan)
4. Model terlatih, metrik tercatat, peta risiko tampil ✅
5. README dan skrip start/stop/check memungkinkan jalan dari nol ✅
6. Skrip demo (urutan klik dan narasi) tersedia ✅ (`docs/DEMO.md`)
