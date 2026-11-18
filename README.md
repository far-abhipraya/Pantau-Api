# PantauApi

Platform big data (Hadoop HDFS, Spark, NiFi) untuk memantau hotspot karhutla Indonesia dan memperkirakan risikonya.

Tiga halaman: Peta (`/`), Data & Pre-processing (`/data`), Analitik (`/analytics`).

## Dokumen
- `AGENTS.md`: aturan agent (selalu aktif); `.agents/rules/`: aturan terperinci; `.agents/workflows/start-phase.md`: `/start-phase <nomor>`
- `docs/PRD.md` (v1.2), `docs/UI_SPEC.md`, `docs/DESIGN.md`, `docs/STITCH_PROMPTS.md`
- `docs/ENVIRONMENT.md`, `docs/TASKS.md`, `docs/DATA_SOURCES.md`

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
