# TASKS: Checklist per Fase (PRD v1.2)

Kerjakan berurutan. Akhiri tiap fase dengan laporan dan tunggu persetujuan. Pemilik: A = data/backend, B = frontend/ML.
Catatan: desain UI (Stitch -> Figma/ekspor) dikerjakan pengguna sebelum Fase 3; letakkan hasilnya di `docs/design/`.

## Fase 0: Verifikasi Lingkungan (A)
- [ ] Buat `C:\projects\karhutla-watch` dan `C:\karhutla-data\{inbox,inbox\processed,inbox\failed,staging,spark-tmp,serving,downloads}`; git init.
- [ ] `python scripts\check_env.py` lulus.
- [ ] Verifikasi PySpark vs Python 3.14 (fallback venv 3.12/3.13), laporkan.
- [ ] Smoke test PySpark baca/tulis CSV dan Parquet ke `hdfs://localhost:9000/karhutla/_smoke_test`, lalu hapus.
- [ ] Buat struktur `/karhutla/{raw/firms_hist,raw/firms_nrt,raw/weather,quarantine,clean/hotspot,clean/weather,features/grid_daily,models,predictions,analytics,logs/jobs}`.
- [ ] Verifikasi paket (fastapi, uvicorn, pydantic, sqlalchemy, duckdb, pyarrow, pandas).

## Fase 1: Pengumpulan Data (A)
- [ ] Pengguna menyiapkan MAP_KEY FIRMS, akun Earthdata/CDS.
- [ ] `scripts/download_firms.py` (VIIRS/MODIS per tahun, bbox Indonesia) ke `downloads`.
- [ ] Hitung baris per file; tentukan rentang tahun agar total >= 1.000.000 (target 3-5 juta).
- [ ] `download_chirps.py`, `download_era5.py` untuk rentang sama.
- [ ] Simpan sampel 50-100 baris tiap sumber ke `data_samples/`; catat header di `docs/data-dictionary.md`.
- [ ] Cari/verifikasi GeoJSON batas provinsi (lihat DATA_SOURCES), simpan sederhana (simplified) untuk web.

## Fase 2: Adapter, Akuisisi Otomatis, Pre-processing Inti (A)
- [ ] `detect_format` + adapter per sumber + tes unit dari sampel.
- [ ] Impor folder terjadwal (inbox -> detect -> `hdfs dfs -put` -> raw) dengan karantina dan `ingest_log`.
- [ ] Job Spark `profile.py`, `preprocess.py` (cleaning, transformasi, normalisasi, encoding, grid_id, provinsi), dedup lintas jalur.
- [ ] Sistem job (antrian tunggal, status, log, laporan baris).
- [ ] Uji skala 100 ribu, 1 juta, 5 juta baris (catat waktu/memori).
- Selesai bila: AC-1, AC-2, AC-3.

## Fase 3: Serving Layer dan Halaman Peta (A + B)
- [ ] `aggregate.py` menulis `hotspot_latest`, `grid_latest_{1.0,0.5,0.25}`, `agg_daily_grid`, `agg_daily_province` ke HDFS dan serving layer.
- [ ] Endpoint `/map/*`, `/geo/provinces`, `/sources`, `/health`.
- [ ] `styles/tokens.css` + Tailwind dari `docs/DESIGN.md`; top bar melayang; footer.
- [ ] Halaman `/`: peta, kartu filter, KPI mini, legenda, popup titik, drawer provinsi, lapisan grid/risiko (placeholder bila model belum ada), state loading/kosong/error.
- Selesai bila: AC-4.

## Fase 4: Halaman Data & Pre-processing (A + B)
- [ ] Strip status, tab Sumber Data (kartu sumber, jadwal, tabel file, panel karantina).
- [ ] Tombol sekunder "Tambah data" + modal deteksi format + upload chunk -> staging -> `hdfs dfs -put` -> pipeline.
- [ ] Tab Pre-processing (profiling, stepper pipeline, simpan konfigurasi, laporan sebelum/sesudah).
- [ ] Tab Riwayat Job (tabel, drawer log/laporan).
- Selesai bila: AC-1, AC-8.

## Fase 5: Halaman Analitik (A + B)
- [ ] Endpoint analytics (kpi, trend, ranking, seasonality, weather-correlation).
- [ ] Halaman `/analytics`: hero KPI, filter lengket, section Ringkasan/Wilayah/Musiman/Cuaca.
- Selesai bila: AC-5.

## Fase 6: Machine Learning (B ML, A pipeline)
- [ ] `features.py` (fitur dan label PRD Bagian 10), `train.py` (RF, GBT; split waktu; class weight), `predict.py`.
- [ ] Simpan metrik/feature importance; bandingkan dengan baseline persistensi.
- [ ] Section Prediksi ML dan lapisan risiko di peta.
- Selesai bila: AC-7.

## Fase 7: NiFi NRT (A)
- [ ] Process group baru "karhutla-nrt" (jangan ubah alur lama): timer 3 jam -> InvokeHTTP FIRMS `area` -> RouteOnAttribute -> UpdateAttribute -> PutHDFS `/karhutla/raw/firms_nrt/date=YYYY-MM-DD/`.
- [ ] Retry/failure route; ekspor `nifi/flow.json` + `nifi/README.md`; job ingest NRT dan kompaksi; fallback `/api/ingest/firms-nrt`.
- Selesai bila: AC-6.

## Fase 8: Validasi dan Finalisasi (A + B)
- [ ] Section Validasi (unggah rekap SiPongi+/BNPB, korelasi tren).
- [ ] Pengujian menyeluruh (PRD Bagian 15), optimasi performa peta, uji tablet.
- [ ] README, diagram arsitektur, `docs/windows-notes.md`, skrip demo.
- [ ] Cek AC-1..AC-9 dan Definisi Selesai.
