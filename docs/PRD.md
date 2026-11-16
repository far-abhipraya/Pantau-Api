# PRD: PantauApi, Platform Big Data Pemantauan dan Prediksi Risiko Karhutla Indonesia

| Item | Isi |
|---|---|
| Nama produk | **PantauApi** |
| Mata kuliah | Big Data & Analitik (proyek akhir) |
| Tim | 2 orang (A: data/backend, B: frontend/ML), waktu fleksibel |
| Versi | 1.2 (struktur 3 halaman baru; upload dijadikan tombol sekunder; UI light-first bernuansa api) |
| Bahasa | Dokumen dan UI: Indonesia, istilah teknis tetap Inggris (Hotspot, Confidence, FRP, Pipeline, Job) |
| Dokumen terkait | `docs/UI_SPEC.md`, `docs/DESIGN.md`, `docs/STITCH_PROMPTS.md`, `docs/ENVIRONMENT.md`, `docs/TASKS.md`, `docs/DATA_SOURCES.md` |

---

## 1. Ringkasan Produk

PantauApi adalah aplikasi web untuk memantau titik panas (hotspot) kebakaran hutan dan lahan (karhutla) di Indonesia secara near real-time dan memperkirakan risikonya. Data satelit NASA FIRMS (VIIRS/MODIS) diakuisisi **otomatis di backend** (NiFi dan impor terjadwal), disimpan di HDFS, diproses dengan Spark, lalu disajikan lewat tiga halaman:

1. **Peta** (halaman utama): peta interaktif Indonesia dengan titik hotspot, zoom/pan, filter, dan lapisan prediksi risiko.
2. **Data & Pre-processing**: status akuisisi otomatis, profiling, pipeline cleaning/normalisasi, riwayat job, serta tombol sederhana "Tambah data" untuk upload manual.
3. **Analitik**: dashboard statistik, tren, musiman, korelasi cuaca, machine learning, dan validasi terhadap SiPongi+/BNPB.

Pengguna: dosen/penilai, mahasiswa, dan pembaca umum yang ingin melihat kondisi hotspot terkini. Tanpa autentikasi.

## 2. Tujuan dan Kriteria Penerimaan

### 2.1 Tujuan
1. Memenuhi ketentuan mata kuliah: dataset >= 1.000.000 baris tersimpan di HDFS (dikonfirmasi dosen: halaman upload khusus tidak wajib), ada pre-processing, ada dashboard analitik; Hadoop dan Spark wajib, NiFi disarankan.
2. Peta hotspot terkini yang responsif walau data historis berjuta baris.
3. Prediksi risiko hotspot per grid 0,25 derajat untuk 7 hari ke depan.
4. Akuisisi data otomatis sebagai jalur utama; upload manual sebagai jalur tambahan.

### 2.2 Kriteria Penerimaan
- AC-1: Total baris dataset mentah di HDFS >= 1.000.000 (tampil di halaman 2 beserta indikatornya).
- AC-2: Data dari beragam format FIRMS (VIIRS, MODIS, arsip, API) terbaca otomatis ke skema kanonik; baris gagal parse masuk karantina dengan alasan.
- AC-3: Pre-processing menghasilkan Parquet di `/karhutla/clean` dan laporan baris input/output per langkah.
- AC-4: Peta awal tampil <= 3 detik pada jendela 24 jam; zoom/pan tetap lancar (tidak pernah memuat lebih dari 20.000 titik sekali waktu).
- AC-5: Dashboard Analitik memuat <= 5 detik dari serving layer.
- AC-6: NiFi menarik data FIRMS terbaru minimal tiap 3 jam ke `/karhutla/raw/firms_nrt`.
- AC-7: Model punya metrik (AUC-ROC, AUC-PR, precision, recall, F1) dengan split berbasis waktu dan dibandingkan dengan baseline persistensi.
- AC-8: Upload manual lewat tombol "Tambah data" melewati pipeline yang sama dengan jalur otomatis.
- AC-9: README memungkinkan menjalankan sistem di laptop target.

## 3. Lingkup

**Dalam lingkup**: akuisisi otomatis (NiFi + impor folder terjadwal), deteksi format dan adapter, upload manual sederhana, pre-processing Spark, integrasi cuaca (CHIRPS/ERA5), agregasi dan serving layer, peta interaktif, dashboard analitik, ML (Spark MLlib), validasi SiPongi+/BNPB (perbandingan agregat).

**Di luar lingkup**: autentikasi/peran, streaming sungguhan (Kafka/Structured Streaming), cluster multi-node, prediksi luas area terbakar, data gambut/tutupan lahan (opsional lanjutan), aplikasi mobile native.

## 4. Lingkungan Eksekusi (Native Windows, SUDAH TERPASANG)

Detail lengkap di `docs/ENVIRONMENT.md`. Agent dilarang menginstal ulang atau memperkenalkan Docker/WSL/VM.

- Perangkat: Lenovo Yoga 7, Ryzen 7 8840HS, RAM 16 GB (sekitar 13,8 GB usable), Windows 11, username Windows mengandung spasi.
- Terpasang: Java 17 (Temurin), Hadoop 3.5.0 (single-node, `C:\hadoop-3.5.0`), Spark 4.2.0 (`local[*]`, `C:\spark-4.2.0-bin-hadoop3`), NiFi 1.28.1 (HTTP :8080), Python 3.14.
- Aturan wajib:
  1. Jangan `hdfs namenode -format`. Jangan ubah/hapus `/hr-data`, `/warehouse`, `/user/alfarel`, `/test`, `/testupload`. Data proyek di `/karhutla/`.
  2. `HADOOP_USER_NAME=hadoop` pada setiap subprocess Hadoop/Spark.
  3. Path konfigurasi memakai forward slash; jangan `hdfs dfs -stat` dengan `%`.
  4. Upload ke HDFS = staging lokal + `hdfs dfs -put` (WebHDFS/Web UI upload gagal karena redirect hostname DataNode).
  5. Kode/data/temp di path tanpa spasi: `C:\projects\karhutla-watch`, `C:\karhutla-data`.
  6. YARN tidak dipakai; cukup `start-dfs.cmd`. Satu job Spark pada satu waktu (`local[4]`, driver 4g).
  7. Verifikasi di Fase 0: kompatibilitas PySpark dengan Python 3.14 (fallback venv 3.12/3.13), baca/tulis HDFS dari PySpark, wheel paket.
- Anggaran memori (RAM usable sekitar 13,8 GB): OS+browser+IDE sekitar 4 GB; HDFS sekitar 2 GB; Spark 4 GB; NiFi sekitar 1,5 GB (saat perlu); FastAPI sekitar 0,5 GB; Next.js dev sekitar 0,5 GB.

## 5. Arsitektur

```
[Browser: Next.js :3000] <--> [FastAPI :8000] <--> [Serving layer: DuckDB + Parquet lokal; SQLite metadata]
                                  |   \
                                  |    \--> subprocess spark-submit (PySpark local[4]) <--> HDFS
                                  +--> subprocess hdfs dfs -put/-ls/-du/-count --> HDFS (hdfs://localhost:9000)

Jalur akuisisi (semua bermuara ke raw, lalu pipeline yang sama):
 1. NiFi: FIRMS API (area) -> PutHDFS /karhutla/raw/firms_nrt   [utama, real-time]
 2. Impor folder terjadwal: C:\karhutla-data\inbox -> deteksi format -> hdfs put -> /karhutla/raw/firms_hist  [utama, historis]
 3. Tombol "Tambah data" (halaman 2) -> staging -> deteksi format -> hdfs put  [tambahan]
```

Alur data: raw -> adapter format + validasi (karantina bila gagal) -> dedup -> clean (Parquet) -> features -> model/prediksi -> agregasi -> ekspor ringkasan kecil ke serving layer (`C:\karhutla-data\serving`) -> API -> UI. Browser tidak pernah menarik data mentah.

### 5.1 Tata Letak HDFS
```
/karhutla/
  raw/ firms_hist/  firms_nrt/ (date=YYYY-MM-DD)  weather/
  quarantine/ (file/baris gagal parse beserta alasan)
  clean/ hotspot/ (year=/month=)  weather/
  features/ grid_daily/
  models/ risk_gbt_v1/
  predictions/ latest/
  analytics/ daily_province/  daily_grid/  monthly_grid/  summary/
  logs/ jobs/
```

## 6. Tech Stack

| Lapisan | Teknologi |
|---|---|
| Frontend | Next.js (App Router, TypeScript), Tailwind CSS, Node.js runtime |
| Peta | Leaflet + react-leaflet, marker clustering, basemap light (CARTO Positron/Voyager, tanpa API key; verifikasi syarat atribusi/penggunaan) |
| Grafik | Apache ECharts |
| Backend | FastAPI, Uvicorn, Pydantic, SQLAlchemy |
| Penyimpanan | HDFS 3.5.0 (terpasang) |
| Pemrosesan | Spark 4.2.0 (PySpark, Spark SQL, MLlib) (terpasang) |
| Akuisisi | NiFi 1.28.1 (terpasang) + impor folder terjadwal |
| Serving/metadata | DuckDB + Parquet lokal, SQLite (alternatif: PostgreSQL native) |
| Eksekusi job | `subprocess` memanggil `spark-submit`, antrian job tunggal |
| Format | CSV/JSON (raw), Parquet (clean, features, analytics) |

## 7. Sumber Data

| Dataset | Peran | Akses |
|---|---|---|
| NASA FIRMS Archive | Hotspot historis VIIRS/MODIS | https://firms.modaps.eosdis.nasa.gov/download/ |
| NASA FIRMS API | NRT (layanan `area`, perlu MAP_KEY) | https://firms2.modaps.eosdis.nasa.gov/api/ |
| CHIRPS | Curah hujan harian | https://www.chc.ucsb.edu/data/chirps |
| ERA5 / ERA5-Land | Suhu, kelembapan, angin | https://cds.climate.copernicus.eu/ |
| SiPongi+ | Validasi | https://sipongi.gakkum.kehutanan.go.id/ |
| BNPB Karhutla | Validasi | https://data.bnpb.go.id/data/karhutla2026 |
| GeoJSON batas provinsi | Peta dan pemetaan provinsi | Kandidat di `docs/DATA_SOURCES.md` (lisensi harus diverifikasi) |

Aturan: bbox Indonesia (perkiraan, verifikasi) lat -11 sampai 6, lon 95 sampai 141; data standar untuk training, NRT untuk tampilan terkini; cantumkan "SIPONGI KEMENHUT" bila memakai SiPongi+; kredensial di `.env`; hitung baris sebelum finalisasi rentang tahun (target >= 1 juta).

## 8. Persyaratan Fungsional

### 8.0 Layout Global
- FR-G1: Top bar melayang (floating), ramping (tinggi sekitar 56 px), memuat logo "PantauApi" (ikon api + teks), 3 menu (Peta, Data & Pre-processing, Analitik), dan indikator "Data diperbarui: <waktu>" dengan titik status (hijau = segar, kuning = tertunda, merah = gagal).
- FR-G2: Di halaman Peta, top bar menjadi semi-transparan setelah idle sekitar 3 detik dan kembali solid saat hover/fokus/sentuh. Di halaman lain bersifat sticky normal.
- FR-G3: Footer ringkas dengan atribusi data: NASA FIRMS, Copernicus/ECMWF, CHIRPS, SIPONGI KEMENHUT, BNPB, kontributor basemap.
- FR-G4: Tema terang sebagai dasar; aksen api gelap hanya pada bagian terpilih (lihat `docs/UI_SPEC.md`). Animasi minimal (transisi 150-200 ms, hormati `prefers-reduced-motion`).
- FR-G5: Layout responsif: desktop dan laptop (1280-1920 px) utama; tablet (768-1024 px) tetap rapi dengan panel menjadi bottom sheet/drawer.

### 8.1 Halaman 1: Peta (`/`)
- FR-M1: Peta interaktif Indonesia memenuhi layar (full-bleed), pusat awal sekitar Indonesia, zoom/pan/scroll, tombol zoom, tombol "Reset tampilan".
- FR-M2: Lapisan Hotspot: titik sesuai jendela waktu (24 jam default, 48 jam, 7 hari). Warna menurut `confidence_level` (low/nominal/high), ukuran menurut FRP (batas min-maks).
- FR-M3: Strategi zoom: zoom rendah menampilkan agregasi grid (bukan titik); zoom tinggi menampilkan titik individual per bbox yang terlihat, maksimum 20.000 titik per permintaan. Titik padat memakai clustering.
- FR-M4: Popup titik: koordinat, waktu (WIB), satelit/sensor, confidence, FRP, provinsi.
- FR-M5: Lapisan "Prediksi risiko 7 hari" (heatmap/choropleth grid) yang bisa dinyalakan; legenda 4 kategori; label jelas "estimasi risiko, bukan kepastian".
- FR-M6: Lapisan "Batas provinsi" (bila GeoJSON tersedia; bila tidak, peta tetap berfungsi tanpa lapisan ini). Klik provinsi membuka drawer ringkasan (hotspot 24 jam/7 hari, tren mini, tombol "Lihat analitik provinsi" yang membawa filter ke halaman 3).
- FR-M7: Panel filter melayang: jendela waktu, sensor (VIIRS/MODIS/semua), confidence minimum, toggle lapisan (Hotspot, Densitas grid, Prediksi risiko, Batas provinsi).
- FR-M8: 3 KPI mini melayang: total hotspot (jendela terpilih), provinsi tertinggi, jumlah confidence tinggi. Indikator waktu pembaruan terakhir.
- FR-M9: Slider waktu historis (opsional fase lanjut): memilih tanggal dan menampilkan agregasi harian.
- FR-M10: Legenda (warna confidence, ukuran FRP, skala risiko), tombol pergantian basemap sederhana (Terang/Satelit bila tersedia tanpa API key).
- FR-M11: Kondisi UI: loading (skeleton ringan), data kosong ("Tidak ada hotspot pada filter ini"), error (pesan dan tombol coba lagi), data tertunda (banner kuning).

### 8.2 Halaman 2: Data & Pre-processing (`/data`)
Struktur: strip status di atas + tiga tab: **Sumber Data**, **Pre-processing**, **Riwayat Job**.

**Strip status (selalu tampil)**: total baris mentah di HDFS dengan indikator ">= 1.000.000", ukuran data, ingest NiFi terakhir (waktu, baris), status Spark (idle/running), jumlah file karantina (badge).

**Tab Sumber Data**
- FR-D1: Kartu per sumber (FIRMS VIIRS, FIRMS MODIS, CHIRPS, ERA5): status otomatis (aktif/tertunda/gagal), pembaruan terakhir, jumlah baris, rentang tanggal, path HDFS.
- FR-D2: Panel jadwal akuisisi otomatis (NiFi tiap 3 jam, impor folder) dengan waktu eksekusi berikutnya.
- FR-D3: Tombol sekunder sederhana **"Tambah data"** (tidak menonjol) di header panel. Membuka modal: pilih satu/banyak file (CSV/JSON), backend mendeteksi format otomatis dan menampilkan ringkasan (format terdeteksi, perkiraan baris, kolom dikenali/tidak dikenali), pengguna menekan "Proses". File melalui staging -> `hdfs dfs -put` -> pipeline yang sama. Modal ditutup dan progres muncul sebagai satu baris di Riwayat Job. Upload chunk di belakang layar untuk file besar.
- FR-D4: Daftar file di HDFS (nama, sumber, ukuran, baris, tanggal), dengan filter sumber, hapus hanya di bawah `/karhutla`.
- FR-D5: Panel karantina: daftar file/baris gagal parse beserta alasan dan jumlah.

**Tab Pre-processing**
- FR-P1: Pilih dataset sumber. Profiling: jumlah baris, tipe kolom, null, duplikat, statistik, distribusi ringkas.
- FR-P2: Pipeline berbentuk stepper opsi (centang): Cleaning (hapus duplikat; null: drop/mean/median/modus/konstan; filter bbox Indonesia; filter confidence rendah; outlier IQR/Z-score pada `frp`/`brightness`), Transformasi (timestamp UTC/WIB, year/month/day/dayofyear/hour, standardisasi `confidence_level`, cast tipe, snake_case), Normalisasi (Min-Max/Z-score; parameter disimpan), Encoding (StringIndexer/OneHot), Spatial enrichment (`grid_id`, provinsi), Integrasi cuaca, Feature engineering.
- FR-P3: Tombol "Jalankan pipeline" memicu job asinkron; konfigurasi dapat disimpan sebagai JSON dan dijalankan ulang.
- FR-P4: Laporan sebelum/sesudah: funnel jumlah baris per langkah, statistik kolom, durasi.

**Tab Riwayat Job**
- FR-J1: Tabel job (jenis, status badge queued/running/success/failed dengan ikon, waktu, durasi, baris in/out), drawer detail berisi log ringkas dan laporan. Auto-refresh polling.

### 8.3 Halaman 3: Analitik (`/analytics`)
Bilah filter global lengket (rentang tanggal, provinsi, sensor, confidence minimum) dan navigasi section (Ringkasan, Wilayah, Musiman, Cuaca, Prediksi ML, Validasi).
- FR-A1 **Ringkasan**: KPI (hotspot hari ini/7/30 hari, provinsi tertinggi, confidence tinggi, rata-rata FRP), tren harian/bulanan, perbandingan tahun ke tahun.
- FR-A2 **Wilayah**: ranking provinsi (bar), choropleth provinsi (bila GeoJSON ada), top grid.
- FR-A3 **Musiman**: heatmap bulan x tahun dan bulan x provinsi.
- FR-A4 **Cuaca**: korelasi curah hujan/suhu vs hotspot (dua sumbu, scatter), hari kering berturut-turut.
- FR-A5 **Prediksi ML**: peta risiko 7 hari, tabel grid risiko tertinggi, kurva risiko mingguan, panel performa model (AUC-ROC, AUC-PR, precision, recall, F1, confusion matrix, feature importance), perbandingan dengan baseline persistensi, tanggal training, catatan keterbatasan.
- FR-A6 **Validasi**: perbandingan tren pipeline dengan rekap SiPongi+/BNPB (unggah CSV rekap atau input manual), korelasi dan selisih relatif.
- FR-A7: Tombol "Perbarui agregasi/prediksi" memicu job; indikator waktu pembaruan.
- FR-A8: Kondisi loading/kosong/error pada setiap kartu grafik; ekspor gambar/CSV ringkas per grafik (opsional).

### 8.4 Akuisisi Otomatis
- FR-N1 NiFi: process group baru "karhutla-nrt" (jangan ubah alur lama): timer 3 jam -> InvokeHTTP FIRMS `area` (bbox Indonesia, 1-2 hari, VIIRS dan MODIS NRT) -> RouteOnAttribute -> UpdateAttribute (nama memuat timestamp) -> PutHDFS `/karhutla/raw/firms_nrt/date=YYYY-MM-DD/`. Ekspor `nifi/flow.json`.
- FR-N2 Impor folder: backend memantau `C:\karhutla-data\inbox` (jadwal tiap beberapa menit atau tombol), mendeteksi format, `hdfs dfs -put`, memindahkan file ke `inbox\processed` atau `inbox\failed`.
- FR-N3 Adapter format: satu adapter per sumber (VIIRS CSV, MODIS CSV, arsip, FIRMS API CSV/JSON, CHIRPS, ERA5) memetakan ke skema kanonik. Deteksi berdasarkan header/skema. Format tak dikenal -> karantina.
- FR-N4 Dedup lintas jalur (kunci lat, lon, acq_date, acq_time, satellite) sebelum masuk `clean`; laporan menyebut jumlah duplikat.
- FR-N5 Kompaksi harian file kecil NRT oleh Spark. Fallback `/api/ingest/firms-nrt` bila NiFi tidak berjalan.

## 9. API (FastAPI, prefix `/api`)

| Metode | Endpoint | Fungsi |
|---|---|---|
| GET | `/health` | Status backend, HDFS, Spark, serving layer |
| GET | `/map/hotspots` | Titik per bbox. Parameter: `bbox`, `hours` (24/48/168), `sensor`, `min_conf`, `limit` (maks 20000) |
| GET | `/map/grid` | Agregasi grid per `zoom` (resolusi 1,0/0,5/0,25 derajat) dan jendela waktu |
| GET | `/map/risk` | Grid risiko prediksi 7 hari |
| GET | `/map/provinces` | Ringkasan per provinsi (hotspot 24 jam/7 hari, tren mini) |
| GET | `/map/kpi` | KPI untuk panel peta |
| GET | `/geo/provinces` | GeoJSON batas provinsi (disederhanakan) bila tersedia |
| GET | `/sources` | Status sumber data otomatis, jadwal, total baris, indikator 1 juta |
| POST | `/datasets/detect` | Deteksi format file yang diunggah (tanpa memproses) |
| POST | `/datasets/upload/init`, `/upload/chunk`, `/upload/complete` | Upload chunk -> staging -> `hdfs dfs -put` -> memicu pipeline |
| GET | `/datasets`, `/datasets/{id}/preview` | Daftar file di HDFS dan pratinjau |
| DELETE | `/datasets/{id}` | Hapus (hanya di bawah `/karhutla`) |
| GET | `/quarantine` | Daftar karantina dan alasan |
| POST | `/preprocessing/profile`, `/preprocessing/run` | Profiling dan pipeline |
| GET | `/jobs`, `/jobs/{id}` | Riwayat, status, log, laporan |
| POST | `/analytics/refresh` | Agregasi + ekspor serving layer |
| GET | `/analytics/kpi`, `/trend`, `/ranking`, `/seasonality`, `/weather-correlation` | Data analitik |
| POST | `/ml/train`, `/ml/predict` | Job ML |
| GET | `/ml/risk-map`, `/ml/metrics` | Hasil model |
| POST | `/ingest/firms-nrt` | Tarik NRT manual (fallback NiFi) |
| POST/GET | `/validation/reference`, `/validation/compare` | Data pembanding dan perbandingan |

Aturan: operasi Spark asinkron (`job_id` + polling), satu job aktif; endpoint titik wajib bbox dan batas jumlah; respons agregat diberi header cache singkat; OpenAPI di `/docs`; CORS hanya `http://localhost:3000`.

### 9.1 Serving Layer untuk Peta
Spark menghasilkan tabel kecil di `C:\karhutla-data\serving`: `hotspot_latest` (7 hari terakhir, titik), `grid_latest_{1.0,0.5,0.25}` (agregasi per jendela 24 jam/48 jam/7 hari), `agg_daily_grid`, `agg_daily_province`, `risk_prediction`. DuckDB melayani query bbox dan agregasi.

## 10. Spesifikasi Machine Learning

| Aspek | Spesifikasi |
|---|---|
| Unit | (grid_id 0,25 derajat, tanggal t) |
| Label | `y=1` bila ada hotspot confidence nominal/tinggi di grid pada t+1..t+7 |
| Fitur hotspot | jumlah 1/3/7/14/30 hari; rata-rata FRP 7 hari; hari sejak hotspot terakhir; hotspot 8 sel tetangga 7 hari |
| Fitur cuaca | hujan total 7/14/30 hari; hari kering berturut-turut; suhu dan kelembapan rata-rata 7 hari; angin (ERA5) |
| Fitur waktu/lokasi | bulan, dayofyear (sin/cos), lat, lon, provinsi (indexed) |
| Model | `RandomForestClassifier` (baseline model) dan `GBTClassifier` (pembanding) |
| Ketidakseimbangan | `weightCol` atau undersampling negatif |
| Split | berbasis waktu (misalnya train sampai 2022, validasi 2023, test 2024+); dilarang split acak |
| Metrik | AUC-ROC, AUC-PR, precision, recall, F1, confusion matrix, feature importance |
| Baseline | persistensi (ada hotspot 7 hari terakhir -> prediksi ada) |
| Keluaran | `risk_score` 0-1; kategori: Rendah <0,25; Sedang <0,5; Tinggi <0,75; Sangat tinggi >=0,75; `model_version`, `predicted_at`, `horizon_days` |

"Kapan" = kurva risiko mingguan + pola musiman. "Di mana" = peta risiko grid. UI wajib menyatakan bahwa ini estimasi risiko.

## 11. Model Data

Metadata (SQLite): `datasets(id, name, source, hdfs_path, size_bytes, row_count, column_count, detected_format, ingest_path[auto|nifi|manual], created_at)`, `jobs(id, job_type, status, config_json, report_json, log_tail, started_at, finished_at)`, `quarantine(id, file_name, reason, row_count, created_at)`, `ingest_log(id, source, started_at, finished_at, rows_in, rows_dup, rows_quarantined, status)`, `model_metrics(...)`, `reference_validation(date, province, source, hotspot_count, burned_area_ha)`.

Serving (Parquet): lihat 9.1. Kolom `risk_prediction(grid_id, lat, lon, target_date, horizon_days, risk_score, risk_category, model_version, predicted_at)`.

### 11.1 Skema Kanonik `clean/hotspot`
`latitude, longitude, acq_ts_utc, acq_ts_wib, year, month, day, dayofyear, hour, satellite, instrument, confidence_level (low|nominal|high), brightness, brightness_2, frp, daynight, grid_id, province, frp_norm, brightness_norm, source_file, ingest_path`.

Skema raw (verifikasi terhadap file nyata): VIIRS umumnya `latitude, longitude, bright_ti4, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_ti5, frp, daynight`; MODIS umumnya `brightness`, `bright_t31`. `confidence` VIIRS kategori (l/n/h), MODIS angka 0-100.

## 12. Persyaratan Non-Fungsional
- NFR-1 Performa: peta dan dashboard membaca serving layer; payload titik <= 20.000; respons peta <= 1 detik pada bbox tipikal.
- NFR-2 Skala: pipeline mampu >= 5 juta baris (uji 100 ribu, 1 juta, 5 juta).
- NFR-3 Keandalan: job idempoten (overwrite per partisi), error tercatat jelas.
- NFR-4 Reproducibility: `scripts\check_env.py`, `start_hdfs.bat`, `stop_hdfs.bat`, `start_nifi.bat`.
- NFR-5 Keamanan dasar: `.env` untuk secrets, validasi file, hapus HDFS dibatasi `/karhutla`, CORS terbatas.
- NFR-6 Aksesibilitas: kontras teks >= 4,5:1, skala risiko tidak bergantung warna saja (label/ikon/pola), fokus keyboard terlihat, ukuran target sentuh >= 40 px di tablet.
- NFR-7 Ringan: tanpa animasi kontinu, maksimal satu efek blur/transparansi (top bar), tanpa library animasi berat.
- NFR-8 Kualitas kode: ruff, eslint, tsc strict.
- NFR-9 Atribusi data tampil di footer.

## 13. Struktur Repositori (`C:\projects\karhutla-watch`)
```
karhutla-watch/
  AGENTS.md  README.md  .env.example  .gitignore
  .agents/ rules/ (windows-hadoop.md, data-and-ml.md, ingestion-adapters.md, frontend-backend.md, ui-design.md)  workflows/start-phase.md
  docs/ (PRD.md, UI_SPEC.md, DESIGN.md, STITCH_PROMPTS.md, ENVIRONMENT.md, TASKS.md, DATA_SOURCES.md, data-dictionary.md)
  scripts/ (check_env.py, start_hdfs.bat, stop_hdfs.bat, start_nifi.bat, download_*.py)
  nifi/ (flow.json, README.md)
  backend/ app/ (main.py, routers/, services/hdfs_cli.py, services/jobs.py, services/serving.py, services/detect.py) spark_jobs/ (common.py, adapters/, profile.py, preprocess.py, features.py, aggregate.py, train.py, predict.py) tests/
  frontend/ app/ (page.tsx [Peta], data/page.tsx, analytics/page.tsx) components/ lib/api.ts styles/tokens.css
  data_samples/
```
Folder repo tidak harus diganti nama meski produk bernama PantauApi.

## 14. Rencana Pengerjaan
Lihat `docs/TASKS.md`. Ringkas: Fase 0 verifikasi lingkungan; 1 pengumpulan data dan sampel; 2 adapter format + akuisisi otomatis + pre-processing inti; 3 serving layer + halaman Peta; 4 halaman Data & Pre-processing (termasuk "Tambah data"); 5 halaman Analitik; 6 ML; 7 NiFi NRT; 8 validasi, pengujian, dokumentasi. Desain UI (Stitch -> Figma) dikerjakan pengguna sebelum Fase 3.

## 15. Pengujian
Unit (adapter, cleaning, `grid_id`, label), integrasi (inbox/NiFi/manual -> HDFS -> clean -> serving), skala (100 ribu/1 juta/5 juta), kualitas data (bbox, duplikat, konsistensi baris), ML (tanpa kebocoran waktu, melampaui baseline), UI (tiga halaman end-to-end, filter, state kosong/error/loading, tablet), performa peta (zoom/pan pada jendela 7 hari), resiliensi (NiFi/FIRMS gagal, file rusak, HDFS mati), validasi (korelasi dengan SiPongi+/BNPB).

## 16. Risiko dan Mitigasi

| Risiko | Mitigasi |
|---|---|
| RAM 16 GB terbatas | HDFS saja tanpa YARN, Spark 4 GB, NiFi saat perlu, Parquet, satu job pada satu waktu |
| Path dengan spasi pada username | Kerja di `C:\projects` dan `C:\karhutla-data`; `HADOOP_USER_NAME=hadoop` pada subprocess |
| PySpark vs Python 3.14 / konflik jar Hadoop | Verifikasi Fase 0; fallback venv 3.12/3.13 |
| Upload via WebHDFS gagal | Staging lokal + `hdfs dfs -put` |
| Format FIRMS beragam | Adapter + deteksi header + karantina |
| Peta lambat dengan data besar | Agregasi per zoom, bbox, batas 20.000 titik, clustering |
| File kecil banyak (NRT) | Kompaksi harian |
| Awan menutupi hotspot; hotspot bukan kepastian kebakaran | Catatan keterbatasan di UI |
| Latensi satelit sekitar 3 jam | Sebut "near real-time", tampilkan waktu pembaruan |
| Batas permintaan FIRMS API | Unduh historis per potongan, polling NRT tiap 3 jam |
| CHIRPS v2 berhenti diproduksi setelah Desember 2026 | Pertimbangkan CHIRPS v3/ERA5 |
| Lisensi/akurasi GeoJSON provinsi | Verifikasi sebelum dipakai; peta tetap berfungsi tanpanya |
| Ketidakseimbangan kelas | Class weight/undersampling, AUC-PR |
| Hasil Stitch tidak konsisten | Gunakan `DESIGN.md`, satu layar per prompt, ekstrak token lalu terapkan ke seluruh layar |

## 17. Definisi Selesai
1. AC-1 sampai AC-9 terpenuhi pada data nyata >= 1 juta baris.
2. Tiga halaman berfungsi end-to-end dan konsisten dengan `docs/UI_SPEC.md`.
3. NiFi flow berjalan dan terdokumentasi dengan bukti file NRT di HDFS.
4. Model terlatih, metrik tercatat, peta risiko tampil.
5. README dan skrip start/stop/check memungkinkan menjalankan dari nol di mesin ini.
6. Skrip demo (urutan klik dan narasi) tersedia.

## 18. Instruksi untuk Agent Pelaksana
- Lingkungan sudah terpasang. Jangan instal ulang, format ulang, ubah konfigurasi inti, atau menambah Docker/WSL/VM.
- Mulai dari Fase 0; laporkan hasil verifikasi kompatibilitas sebelum menulis fitur.
- Jangan sentuh path HDFS lama dan alur NiFi lama.
- Patuhi aturan Windows di Bagian 4 dan `.agents/rules/windows-hadoop.md`.
- UI mengikuti `docs/UI_SPEC.md` dan `docs/DESIGN.md` (token di `styles/tokens.css` dan konfigurasi Tailwind). Jangan menambah animasi berat atau efek di luar spesifikasi.
- Jangan berasumsi nama kolom atau versi. Periksa data nyata. Tandai `TODO(verify)` untuk hal yang tak terverifikasi, jangan mengarang data atau metrik.
- Satu fase pada satu waktu; laporkan dan tunggu persetujuan pengguna.
- Jangan mengubah lingkup (autentikasi, streaming) tanpa persetujuan.
