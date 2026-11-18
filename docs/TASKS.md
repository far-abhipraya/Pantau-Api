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
- [x] `detect_format` + adapter per sumber + tes unit dari sampel. (`pytest backend\tests` -> 3 passed)
- [x] Impor folder terjadwal (inbox -> detect -> `hdfs dfs -put` -> raw) dengan karantina dan `ingest_log`.
  (`backend/app/pipeline/ingest.py`: staging -> `hdfs dfs -put`, tabel `jobs`/`ingest_log`/`quarantine`/`datasets` di `meta.db`.)
- [x] Job Spark `profile.py`, `preprocess.py` (cleaning, transformasi, normalisasi, encoding, grid_id, provinsi), dedup lintas jalur.
  (`data_profile.py`, `preprocess.py`; dedup kunci `(latitude, longitude, acq_date, acq_time, satellite)`; provinsi via `province_grid_lookup.parquet` 403.595 sel 0,02°.)
- [x] Sistem job (antrian tunggal, status, log, laporan baris).
  (`job_manager.py` + `log_job_start`/`log_job_finish`; satu job Spark pada satu waktu.)
- [ ] Uji skala 100 ribu, 1 juta, 5 juta baris (catat waktu/memori).
  Sebagian: run penuh 2.134.784 baris selesai 1 mnt 52 dtk (`local[2]`, driver 3g, RAM bebas ~3,3 GB) - `preprocess_full2.log`.
- Selesai bila: AC-1, AC-2, AC-3.

Bukti Fase 2 (16 Nov 2026): `/karhutla/clean/hotspot` = 2.134.784 baris, rentang 2019-01-01 s.d. 2026-11-16,
0 duplikat kunci, 0 koordinat/waktu tidak valid, provinsi `UNKNOWN` 4.288 (0,2%).
Laporan: `C:\karhutla-data\serving\pipeline_run_summary.json`, `profiling_report.json`.
Catatan: nama job Spark `profile.py` di checklist diimplementasikan sebagai `data_profile.py`.

## Fase 3: Serving Layer dan Halaman Peta (A + B)
- [x] `aggregate.py` menulis `hotspot_latest`, `grid_latest_{1.0,0.5,0.25}`, `agg_daily_grid`, `agg_daily_province` ke HDFS dan serving layer.
  Parquet lokal di `C:\karhutla-data\serving` + `serving_meta.json`; `risk_prediction` menunggu Fase 6.
  Bukti: 13.451 titik 7 hari, grid 591/1.158/2.104 sel, harian grid 308.719 baris, harian provinsi 64.115 baris.
- [x] Endpoint `/map/*`, `/geo/provinces`, `/sources`, `/health`.
  `KPI 190 ms`, `grid 51 ms`, `hotspots 20.000 titik maks 246 ms`, `geo 4 ms` (gzip, ETag) - AC-4 terpenuhi.
- [x] `styles/tokens.css` + Tailwind dari `docs/DESIGN.md`; top bar melayang; footer.
  Token Tailwind v4 di `frontend/app/globals.css`; `TopBar` (idle fade 3 dtk) dan `Footer` ember.
- [x] Halaman `/`: peta, kartu filter, KPI mini, legenda, popup titik, drawer provinsi, lapisan grid/risiko (placeholder bila model belum ada), state loading/kosong/error.
  `MapExperience`/`MapCanvas`: grid < zoom 7, titik >= zoom 7 (cluster > 800 titik), drawer provinsi + sparkline, banner data tertunda, basemap Terang/Satelit.
- Selesai bila: AC-4.

## Fase 4: Halaman Data & Pre-processing (A + B)
- [x] Strip status, tab Sumber Data (kartu sumber, jadwal, tabel file, panel karantina).
  `GET /api/sources` (strip + kartu + jadwal), `GET /api/datasets` (katalog HDFS), `GET /api/quarantine`.
  Bukti: strip `2.134.784` baris mentah + badge "Terpenuhi", 17 file raw, 0 karantina, status Spark.
- [x] Tombol sekunder "Tambah data" + modal deteksi format + upload chunk -> staging -> `hdfs dfs -put` -> pipeline.
  `POST /api/datasets/upload/init|chunk|complete`, `POST /api/datasets/detect`; sesi di `staging/uploads/<id>`;
  ingest manual tercatat sebagai job `INGEST_MANUAL` dan memicu pre-processing yang sama.
  Bukti: tes `test_upload_detect_complete_preview_delete` (deteksi FIRMS_VIIRS, 3 baris, put HDFS, hapus) lulus.
- [x] Tab Pre-processing (profiling, stepper pipeline, simpan konfigurasi, laporan sebelum/sesudah).
  `GET /api/preprocessing/config-schema`, `POST /preprocessing/profile`, `POST /preprocessing/run`,
  `GET /preprocessing/latest`, `POST/GET /preprocessing/configs`; `preprocess.py --config`.
  Bukti: default tanpa config tetap **2.134.784 -> 2.134.784** (identik, 0 duplikat);
  `min_confidence=high` -> clean 159.687 (1.975.097 difilter) dengan funnel per langkah.
- [x] Tab Riwayat Job (tabel, drawer log/laporan).
  `GET /api/jobs`, `GET /api/jobs/{id}`; antrian Spark tunggal (`spark_runner.py`), log ekor disalurkan ke DB.
  Bukti: job profiling lewat API selesai 44 dtk (driver 2g karena RAM), log 5,5 KB, laporan 17 kolom.
- Selesai bila: AC-1, AC-8.

Catatan Fase 4 (17 Nov 2026):
- Langkah stepper yang belum aktif ditandai jelas di UI: Encoding (Fase 6), Integrasi cuaca (data cuaca belum lengkap),
  Feature engineering (Fase 6). Tidak ada opsi yang mengaku berjalan padahal tidak.
- Memori driver diturunkan otomatis bila RAM bebas kurang (`/api/jobs` menampilkan `requested` vs `driver_memory`);
  tidak pernah dinaikkan. `hdfs dfs -test -e` tidak dipakai (kode keluar tidak andal di Windows) - pagar memakai `-ls`.
- `pytest backend\tests` -> 20 passed (`test_phase4_api.py` menambah 7 tes: skema, jobs, katalog, upload, pagar hapus).

## Fase 5: Halaman Analitik (A + B)
- [x] Endpoint analytics (kpi, trend, ranking, seasonality, weather-correlation). Tambahan: `year-compare` (FP5),
  `top-grid`, `insights`, dan `POST /refresh` (FR-A7). Semua dari serving layer DuckDB.
- [x] Halaman `/analytics`: hero KPI, filter lengket, section Ringkasan/Wilayah/Musiman/Cuaca (+Faktor Pengaruh,
  Prediksi ML, Validasi sebagai status jujur).
- Selesai bila: AC-5.
- Bukti: `python -m pytest backend\tests -q` -> 30 passed (10 test analitik); `npm run build` sukses (route
  `/`, `/data`, `/analytics`); uji browser: KPI 578/11.960/116.245, 3 kartu insight, filter provinsi + confidence,
  heatmap 2 mode, choropleth 38 provinsi, top grid 10 baris.
- Catatan: FP1-FP4/FP6 dan Prediksi ML menunggu data cuaca + model (Fase 6); Validasi menunggu Fase 8.
  Sensor belum bisa menyaring agregat harian (hanya confidence), didokumentasikan di UI.

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
