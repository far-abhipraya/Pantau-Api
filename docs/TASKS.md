# TASKS: Checklist per Fase

Kerjakan berurutan. Akhiri tiap fase dengan laporan dan tunggu persetujuan pengguna.
Pemilik: A = data/backend, B = frontend/ML.

## Fase 0: Verifikasi Lingkungan (A)
- [x] Buat `C:\projects\karhutla-watch` dan `C:\karhutla-data\{staging,spark-tmp,serving,downloads}`; inisialisasi git dan `.gitignore`.
- [x] Jalankan `scripts\check_env.py`; semua cek HDFS/Spark/Java lulus.
- [x] Verifikasi PySpark vs Python 3.14; putuskan venv (3.12/3.13 bila perlu); laporkan.
- [x] Smoke test PySpark: tulis dan baca CSV dan Parquet ke `hdfs://localhost:9000/karhutla/_smoke_test`, lalu hapus.
- [x] `hdfs dfs -mkdir -p` struktur `/karhutla/{raw/firms_hist,raw/firms_nrt,raw/weather,clean/hotspot,clean/weather,features/grid_daily,models,predictions,analytics,logs/jobs}`.
- [x] Verifikasi paket Python terpasang (fastapi, uvicorn, pydantic, sqlalchemy, duckdb, pyarrow, pandas).
- Selesai bila: laporan kompatibilitas dan smoke test sukses terlampir.

## Fase 1: Pengumpulan Data (A)
- [ ] Pengguna menyediakan MAP_KEY FIRMS dan akun Earthdata/CDS (agent tidak membuat akun).
- [ ] `scripts/download_firms.py`: unduh arsip VIIRS (dan MODIS) per tahun untuk bbox Indonesia ke `C:\karhutla-data\downloads`.
- [ ] Hitung jumlah baris per tahun/sensor; tentukan rentang tahun agar total >= 1.000.000 baris (target nyaman 3-5 juta).
- [ ] `scripts/download_chirps.py` dan `download_era5.py` untuk rentang yang sama.
- [x] Simpan 50-100 baris tiap sumber ke `data_samples/`; catat header aktual di `docs/data-dictionary.md`.
- Selesai bila: tabel jumlah baris per file terlampir.

## Fase 2: Upload ke HDFS (A backend, B frontend)
- [ ] Backend: `services/hdfs_cli.py`, endpoint upload init/chunk/complete, `datasets`, `summary`, `preview`, `delete`.
- [ ] Frontend halaman `/`: drag and drop, progress, pratinjau, total baris, indikator >= 1 juta, daftar file.
- [ ] Uji: upload CSV >= 200 MB; ukuran di HDFS sama dengan lokal; memori backend stabil.
- Selesai bila: AC-1 dan AC-2 terpenuhi.

## Fase 3: Pre-processing (A job, B UI)
- [ ] `spark_jobs`: `common.py`, `profile.py`, `preprocess.py` (cleaning, transformasi, normalisasi, encoding, grid_id, provinsi).
- [ ] Cari GeoJSON batas provinsi (sumber resmi/terbuka), verifikasi lisensi, buat lookup grid->provinsi.
- [ ] Sistem job: antrian tunggal, status, log, laporan baris per langkah.
- [ ] Frontend `/preprocessing`: opsi pipeline, jalankan, status, perbandingan sebelum/sesudah.
- [ ] Uji skala 100 ribu, 1 juta, 5 juta baris (catat waktu dan memori).
- Selesai bila: AC-3 terpenuhi.

## Fase 4: Agregasi dan Dashboard (A, B)
- [ ] `aggregate.py` menulis ke `/karhutla/analytics/...` dan mengekspor Parquet kecil ke `C:\karhutla-data\serving`.
- [ ] Endpoint analytics (kpi, hotspots/latest, trend, ranking, seasonality, weather-correlation).
- [ ] Frontend `/dashboard`: KPI, peta, tren, ranking, heatmap musiman, korelasi cuaca, filter global, atribusi.
- Selesai bila: AC-4 terpenuhi.

## Fase 5: Prediksi Risiko (B ML, A pipeline)
- [ ] `features.py` (fitur dan label sesuai PRD Bagian 10).
- [ ] `train.py` (RandomForest, GBT; split waktu; class weight), `predict.py`.
- [ ] Simpan metrik dan feature importance; bandingkan dengan baseline persistensi.
- [ ] Dashboard: peta risiko 7 hari dan panel performa model.
- Selesai bila: AC-6 terpenuhi.

## Fase 6: NiFi NRT (A)
- [ ] Process group baru "karhutla-nrt" (jangan ubah alur lama): timer -> InvokeHTTP FIRMS `area` -> RouteOnAttribute -> UpdateAttribute -> PutHDFS `/karhutla/raw/firms_nrt/date=YYYY-MM-DD/`.
- [ ] Jadwal tiap 3 jam, retry, route failure. Ekspor `nifi/flow.json` dan `nifi/README.md`.
- [ ] Job ingest NRT: dedup, clean, tulis ke `clean/hotspot`, kompaksi harian. Fallback `/api/ingest/firms-nrt`.
- Selesai bila: AC-5 terpenuhi.

## Fase 7: Validasi dan Finalisasi (A, B)
- [ ] Unggah rekap SiPongi+/BNPB; panel validasi (korelasi tren bulanan).
- [ ] Pengujian menyeluruh (PRD Bagian 15), optimasi.
- [ ] README, diagram arsitektur, `docs/windows-notes.md`, skrip demo.
- [ ] Cek AC-1 sampai AC-7 dan Definisi Selesai (PRD Bagian 17).
