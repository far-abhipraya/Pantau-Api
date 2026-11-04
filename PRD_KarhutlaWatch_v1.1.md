# PRD: KarhutlaWatch, Platform Big Data Pemantauan dan Prediksi Risiko Karhutla Indonesia

| Item | Isi |
|---|---|
| Mata kuliah | Big Data & Analitik (proyek akhir) |
| Tim | 2 orang (Dev A: data/backend, Dev B: frontend/ML), waktu fleksibel |
| Versi | 1.1 (revisi: Hadoop/Spark/NiFi native Windows, tanpa Docker/WSL/VM) |
| Bahasa dokumen | Indonesia, istilah teknis Inggris |

---

## 1. Ringkasan

Aplikasi web dengan tiga halaman: (1) Upload dataset ke HDFS, (2) Pre-processing data di HDFS memakai Spark, (3) Dashboard analitik hotspot karhutla dan prediksi risiko. Data utama adalah hotspot satelit NASA FIRMS (VIIRS/MODIS) untuk Indonesia, diperkaya data cuaca CHIRPS/ERA5. Data terbaru ditarik berkala oleh Apache NiFi (near real-time). SiPongi+ dan BNPB dipakai sebagai validasi.

## 2. Tujuan dan Kriteria Penerimaan

### 2.1 Tujuan
1. Memenuhi ketentuan mata kuliah: upload dataset >= 1.000.000 baris, tersimpan di HDFS, ada fitur pre-processing, ada halaman dashboard.
2. Menampilkan sebaran hotspot terkini (near real-time).
3. Memprediksi risiko hotspot per sel grid 0,25 derajat untuk 7 hari ke depan.
4. Memakai Hadoop (HDFS) dan Spark sebagai inti, NiFi sebagai jalur akuisisi.

### 2.2 Kriteria Penerimaan
- AC-1: Dataset gabungan di HDFS >= 1.000.000 baris, dibuktikan dengan hitungan di UI.
- AC-2: Upload CSV >= 200 MB berhasil tanpa backend kehabisan memori.
- AC-3: Pre-processing menghasilkan Parquet di `/karhutla/clean` beserta laporan sebelum/sesudah.
- AC-4: Dashboard memuat <= 5 detik dari data agregat (peta, tren, peta risiko).
- AC-5: NiFi menarik data FIRMS terbaru minimal tiap 3 jam ke `/karhutla/raw/firms_nrt`.
- AC-6: Model punya metrik (AUC-ROC, AUC-PR, precision, recall, F1) dengan split berbasis waktu.
- AC-7: README memungkinkan menjalankan sistem di laptop target.

## 3. Lingkup

**Dalam lingkup**: upload CSV ke HDFS; profiling, cleaning, normalisasi, feature engineering via Spark; integrasi cuaca grid-hari; agregasi dan dashboard; model prediksi MLlib; ingest NRT via NiFi; validasi agregat terhadap SiPongi+/BNPB.

**Di luar lingkup**: autentikasi dan peran pengguna; streaming sungguhan (Kafka/Structured Streaming); cluster multi-node; prediksi luas area terbakar; data gambut dan tutupan lahan (opsional lanjutan).

## 4. Lingkungan Eksekusi (Native Windows, SUDAH TERPASANG)

Ini bukan tugas instalasi. Agent dilarang menginstal ulang, memformat ulang NameNode, memindahkan instalasi, atau memperkenalkan Docker/WSL/VM. Konfigurasi di bawah adalah fakta yang harus dihormati.

### 4.1 Perangkat
- Lenovo Yoga 7 (LENOVO-YOGA-7), AMD Ryzen 7 8840HS (8 core/16 thread), RAM 16 GB (sekitar 13,8 GB usable), tanpa GPU NVIDIA (MLlib berbasis CPU), Windows 11 (10.0.26200).
- Disk: sisa sekitar 240 GB dari 954 GB. Pantau ruang.
- Username Windows mengandung spasi (`Alfarel Abhipraya`, short name `ALFARE~1`). Ini sumber error path.

### 4.2 Perangkat Lunak Terpasang

| Komponen | Versi | Lokasi/Catatan |
|---|---|---|
| Java | Eclipse Adoptium JDK 17.0.12.7 | `C:\Program Files\Eclipse Adoptium\jdk-17.0.12.7-hotspot` |
| Hadoop | 3.5.0, single-node pseudo-distributed (NameNode, DataNode, ResourceManager, NodeManager) | `C:\hadoop-3.5.0`, `winutils.exe` dan `hadoop.dll` di `bin` |
| Spark | 4.2.0 (Scala 2.13.18), mode `local[*]` | `C:\spark-4.2.0-bin-hadoop3`; `SPARK_HOME` dan `SPARK_DIST_CLASSPATH` (dari `hadoop classpath`) sudah di-set |
| NiFi | 1.28.1, HTTP port 8080 | `C:\nifi-1.28.1`; alur GetFile -> PutHDFS memakai core-site.xml dan hdfs-site.xml |
| Python | 3.14 | `C:\Python314` |

### 4.3 Konfigurasi Hadoop yang Harus Dipertahankan
- Env System: `JAVA_HOME`, `HADOOP_HOME=C:\hadoop-3.5.0`; PATH memuat `%JAVA_HOME%\bin`, `%HADOOP_HOME%\bin`, `%HADOOP_HOME%\sbin`.
- Env User: `HADOOP_USER_NAME=hadoop`.
- `core-site.xml`: `fs.defaultFS=hdfs://localhost:9000`, `hadoop.tmp.dir=C:/hadoop-3.5.0/tmp`.
- `hdfs-site.xml`: `dfs.replication=1`, `dfs.namenode.name.dir=file:///C:/hadoop-3.5.0/data/namenode`, `dfs.datanode.data.dir=file:///C:/hadoop-3.5.0/data/datanode` (forward slash wajib).
- `mapred-site.xml`: `mapreduce.framework.name=yarn`. `yarn-site.xml`: `mapreduce_shuffle` dengan `org.apache.hadoop.mapred.ShuffleHandler`.
- `hadoop-env.cmd`: `JAVA_HOME=C:\PROGRA~1\ECLIPS~1\jdk-17.0.12.7-hotspot` (short path), `HADOOP_IDENT_STRING=hadoop`.
- NameNode sudah diformat (2026-09-01). **Jangan jalankan `hdfs namenode -format` lagi**, karena akan menghapus seluruh data HDFS.
- Start: `start-all.cmd` dari CMD Administrator (peringatan deprecated normal). Stop: `stop-all.cmd`. UI: NameNode `http://localhost:9870`, YARN `http://localhost:8088`.
- Status terverifikasi: NameNode active, Safemode off, 1 node YARN (8 GB, 8 vcores), job MapReduce 2.000.000 record SUKSES.
- Isi HDFS saat ini: `/hr-data`, `/warehouse/dataset1-3` (via NiFi), `/user/alfarel`, `/test`, `/testupload`. **Jangan mengubah atau menghapus path ini.** Semua data proyek ditaruh di `/karhutla/...`.

### 4.4 Aturan Khusus Windows (Wajib Dipatuhi)
1. `HADOOP_IDENT_STRING=hadoop` dan `HADOOP_USER_NAME=hadoop` harus tetap ada. Setiap proses yang dijalankan backend (spark-submit, hdfs dfs) wajib mewarisi `HADOOP_USER_NAME=hadoop`. Set eksplisit di environment subprocess.
2. Path di XML dan konfigurasi memakai forward slash.
3. **Jangan memakai `hdfs dfs -stat` dengan format `%`** (rusak di CMD). Gunakan `-ls`, `-du`, atau `-count`.
4. **Upload lewat NameNode Web UI gagal** (redirect ke hostname DataNode). Karena itu backend tidak boleh mengandalkan alur WebHDFS dengan redirect ke DataNode tanpa pengujian. Jalur upload yang diwajibkan: simpan file ke staging lokal, lalu `hdfs dfs -put` lewat subprocess (lihat 6.1). WebHDFS hanya opsi cadangan setelah terbukti jalan.
5. **Proyek ditaruh di path tanpa spasi**, misalnya `C:\projects\karhutla-watch`. Staging dan temp: `C:\karhutla-data\staging`, `C:\karhutla-data\spark-tmp`, `C:\karhutla-data\serving`. Jangan memakai folder home pengguna (mengandung spasi).
6. Semua perintah dijalankan dari CMD/PowerShell dengan quoting path yang benar. Gunakan `pathlib` dan hindari concatenation string manual.
7. Spark di Windows butuh `HADOOP_HOME` + winutils (sudah ada). Set `spark.local.dir=C:/karhutla-data/spark-tmp`.

### 4.5 Risiko Kompatibilitas yang Harus Diverifikasi Agent di Awal (Fase 0)
- **PySpark vs Python 3.14**: periksa apakah PySpark bawaan Spark 4.2.0 mendukung Python 3.14. Bila gagal, buat virtual environment dengan Python 3.12 atau 3.13 (instal berdampingan, jangan menghapus 3.14) dan arahkan `PYSPARK_PYTHON`/`PYSPARK_DRIVER_PYTHON` ke sana. Laporkan keputusan ke pengguna.
- **Spark 4.2.0 `hadoop3` vs Hadoop 3.5.0**: Spark membawa klien Hadoop 3.x sendiri dan `SPARK_DIST_CLASSPATH` menambahkan jar Hadoop 3.5.0. Uji baca/tulis `hdfs://localhost:9000` dari PySpark (CSV dan Parquet). Bila ada konflik jar, laporkan sebelum mengubah apa pun.
- **Java 17** kompatibel dengan Spark 4.x. Pastikan opsi JVM tambahan (misalnya `--add-opens`) hanya ditambahkan bila ada error.
- **Dependensi Python di 3.14**: periksa ketersediaan wheel (fastapi, pydantic-core, pyarrow, duckdb, pandas). Bila tidak ada, pakai Python 3.12/3.13 untuk venv backend.

### 4.6 Anggaran Memori (RAM usable sekitar 13,8 GB)

| Komponen | Target |
|---|---|
| Windows + browser + IDE | sekitar 4 GB |
| NameNode + DataNode (set `HADOOP_HEAPSIZE` kecil, sekitar 512 MB-1 GB tiap daemon) | sekitar 2 GB |
| YARN RM + NM | **Tidak dibutuhkan** oleh proyek (Spark berjalan `local[*]`). Jalankan hanya HDFS (`start-dfs.cmd`) saat pengembangan agar hemat RAM. `start-all.cmd` hanya bila ingin demo MapReduce |
| Spark job (`local[4]`, `--driver-memory 4g`) | 4 GB |
| NiFi (heap 1 GB di `bootstrap.conf`) | sekitar 1,5 GB, dijalankan saat dibutuhkan |
| FastAPI | sekitar 0,5 GB |
| Next.js dev | sekitar 0,5 GB |

Aturan: jalankan satu job Spark pada satu waktu (antrian di backend). Gunakan Parquet dan partisi. Untuk pengujian volume, naikkan data bertahap.

## 5. Arsitektur

```
[Browser: Next.js :3000] <--> [FastAPI :8000] <--> [Serving layer: DuckDB + Parquet lokal, SQLite metadata]
                                  |   \
                                  |    \--> subprocess: spark-submit (PySpark, local[4]) <--> HDFS
                                  +--> subprocess: hdfs dfs -put/-ls/-du/-count  --> HDFS (hdfs://localhost:9000)

[FIRMS API] --> [NiFi :8080: InvokeHTTP -> ... -> PutHDFS] --> HDFS /karhutla/raw/firms_nrt
```

Alur data:
1. Raw (upload web dan NiFi) masuk `/karhutla/raw/...`.
2. Spark pre-processing: raw -> `/karhutla/clean/...` (Parquet).
3. Spark feature engineering: clean -> `/karhutla/features/grid_daily` (Parquet).
4. Spark train/predict: -> `/karhutla/models`, `/karhutla/predictions`.
5. Spark agregasi: -> `/karhutla/analytics/...`, lalu **ekspor ringkasan kecil** (puluhan ribu baris) ke `C:\karhutla-data\serving\*.parquet` (via `hdfs dfs -get` atau `toPandas` pada data agregat kecil). Backend membaca serving layer dengan DuckDB sehingga dashboard cepat tanpa memuat jutaan baris.
6. Frontend hanya memanggil API agregat.

Catatan desain: serving layer lokal (DuckDB + Parquet + SQLite) dipilih menggantikan PostgreSQL agar tidak menambah instalasi dan RAM. PostgreSQL native Windows boleh dipakai bila pengguna meminta, dengan skema Bagian 11 yang tetap sama.

### 5.1 Tata Letak HDFS

```
/karhutla/
  raw/ firms_hist/  firms_nrt/ (date=YYYY-MM-DD)  weather/
  clean/ hotspot/ (year=/month=)  weather/
  features/ grid_daily/
  models/ risk_gbt_v1/
  predictions/ latest/
  analytics/ daily_province/  monthly_grid/  summary/
  logs/ jobs/
```
Pembuatan awal: `hdfs dfs -mkdir -p /karhutla/raw/firms_hist ...` (jangan menyentuh path lama).

## 6. Tech Stack

| Lapisan | Teknologi |
|---|---|
| Frontend | Next.js (App Router, TypeScript), Tailwind CSS, Node.js (runtime Next.js saja) |
| Peta | Leaflet + react-leaflet (opsi deck.gl untuk titik banyak), marker clustering |
| Grafik | Apache ECharts |
| Backend | FastAPI, Uvicorn, Pydantic, SQLAlchemy |
| Penyimpanan besar | HDFS 3.5.0 (terpasang) |
| Pemrosesan | Spark 4.2.0 (PySpark, Spark SQL, MLlib) (terpasang) |
| Akuisisi | NiFi 1.28.1 (terpasang) |
| Serving/metadata | DuckDB + Parquet lokal, SQLite (alternatif: PostgreSQL native) |
| Eksekusi job | `subprocess` memanggil `spark-submit`, dengan antrian job tunggal |
| Format | CSV (raw), Parquet (clean, features, analytics) |

### 6.1 Strategi Upload ke HDFS (Wajib)
1. Frontend mengirim file dengan upload chunk (misalnya 8-16 MB/chunk) ke `/api/datasets/upload/chunk`.
2. Backend menulis chunk ke `C:\karhutla-data\staging\<upload_id>\` dan menyusun file akhir secara streaming (tidak memuat seluruh file di memori).
3. Setelah lengkap, backend menjalankan `hdfs dfs -put -f <staging_file> /karhutla/raw/<tipe>/<nama>` dengan environment `HADOOP_USER_NAME=hadoop`, lalu memverifikasi ukuran via `hdfs dfs -du`.
4. Hapus file staging setelah sukses. Catat metadata ke SQLite.
5. Hitung jumlah baris dengan job Spark ringan (atau penghitungan streaming di backend saat chunk digabung, lalu verifikasi Spark) dan simpan.
6. Jangan memakai `hdfs dfs -stat` dengan `%`.

## 7. Sumber Data

| Dataset | Peran | Akses |
|---|---|---|
| NASA FIRMS Archive | Hotspot historis VIIRS/MODIS (CSV) | https://firms.modaps.eosdis.nasa.gov/download/ |
| NASA FIRMS API | NRT, layanan `area` (CSV), perlu MAP_KEY | https://firms2.modaps.eosdis.nasa.gov/api/ |
| CHIRPS | Curah hujan harian | https://www.chc.ucsb.edu/data/chirps , https://data.chc.ucsb.edu/products/CHIRPS-2.0/ |
| ERA5 / ERA5-Land (CDS API) | Suhu, kelembapan, angin | https://cds.climate.copernicus.eu/ |
| SiPongi+ | Validasi | https://sipongi.gakkum.kehutanan.go.id/ |
| BNPB Karhutla | Validasi | https://data.bnpb.go.id/data/karhutla2026 |

Aturan: bounding box Indonesia (perkiraan, verifikasi) lat -11 sampai 6, lon 95 sampai 141. Data kualitas standar untuk training, NRT untuk tampilan terkini. Cantumkan sumber "SIPONGI KEMENHUT" bila memakai SiPongi+. Simpan MAP_KEY dan kredensial di `.env` (jangan commit). Hitung baris sebelum finalisasi rentang tahun (target total >= 1 juta).

Skema raw FIRMS (verifikasi terhadap file nyata): VIIRS umumnya `latitude, longitude, bright_ti4, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_ti5, frp, daynight`; MODIS umumnya `brightness`, `bright_t31`. `confidence` VIIRS kategori (l/n/h), MODIS angka 0-100: normalisasi ke `confidence_level` (low/nominal/high).

## 8. Persyaratan Fungsional

### 8.1 Halaman 1: Upload (`/`)
- FR-U1: Pilih satu/banyak file CSV (drag and drop).
- FR-U2: Pilih tipe dataset: `firms_hist`, `weather`, `generic`.
- FR-U3: Upload chunk dan penyimpanan ke HDFS sesuai 6.1, progress bar.
- FR-U4: Setelah upload: jumlah baris, kolom, ukuran, pratinjau 20 baris.
- FR-U5: Validasi ekstensi, header, kolom wajib per tipe (peringatan bila tidak cocok).
- FR-U6: Total baris seluruh dataset mentah di HDFS dan indikator "memenuhi >= 1.000.000 baris".
- FR-U7: Daftar file di HDFS (nama, ukuran, tanggal) dengan opsi hapus (hanya di bawah `/karhutla`).
- FR-U8: Panel status ingest NiFi terakhir (waktu, jumlah baris).

### 8.2 Halaman 2: Pre-processing (`/preprocessing`)
- FR-P1: Pilih dataset sumber dari HDFS.
- FR-P2: Profiling: jumlah baris, tipe kolom, null, duplikat, statistik deskriptif.
- FR-P3: Cleaning (opsi dicentang): hapus duplikat (kunci lat, lon, acq_date, acq_time, satellite); penanganan null (drop, mean, median, modus, konstan); filter koordinat di luar bounding box; filter confidence rendah; filter outlier (IQR atau Z-score) pada `frp`/`brightness`.
- FR-P4: Transformasi: gabung `acq_date`+`acq_time` menjadi timestamp (UTC dan WIB), ekstrak year/month/day/dayofyear/hour, standardisasi `confidence_level`, cast tipe, snake_case.
- FR-P5: Normalisasi Min-Max atau Z-score pada kolom numerik terpilih, parameter disimpan untuk inferensi.
- FR-P6: Encoding StringIndexer/OneHot untuk kolom kategori.
- FR-P7: Spatial enrichment: `grid_id` (0,25 derajat) dan pemetaan provinsi (join spasial atau lookup grid->provinsi dari GeoJSON batas provinsi; sumber GeoJSON dicari dan diverifikasi lisensinya).
- FR-P8: Perbandingan statistik sebelum/sesudah dan jumlah baris yang dihapus per langkah.
- FR-P9: Job asinkron, output Parquet partisi year/month ke `/karhutla/clean/...`.
- FR-P10: Status job (queued, running, success, failed), durasi, log ringkas, laporan baris input/output.
- FR-P11: Konfigurasi pipeline disimpan sebagai JSON dan dapat dijalankan ulang.
- FR-P12: Integrasi cuaca: join pada (`grid_id`, `date`).
- FR-P13: Feature engineering ke `features/grid_daily` (lihat Bagian 10).

### 8.3 Halaman 3: Dashboard (`/dashboard`)
- FR-D1: KPI: hotspot hari ini, 7 hari, 30 hari; provinsi tertinggi; hotspot confidence tinggi; waktu pembaruan terakhir.
- FR-D2: Peta hotspot terkini (24 jam/48 jam/7 hari), warna berdasar confidence/FRP, popup detail, clustering, batas jumlah titik.
- FR-D3: Tren harian/bulanan dan perbandingan tahun ke tahun.
- FR-D4: Ranking provinsi dan grid teratas.
- FR-D5: Heatmap musiman (bulan x tahun atau bulan x provinsi).
- FR-D6: Korelasi cuaca vs jumlah hotspot.
- FR-D7: Peta risiko prediksi 7 hari (heatmap/choropleth grid) dengan legenda 4 kategori.
- FR-D8: Panel performa model (AUC, precision, recall, F1, confusion matrix, feature importance, tanggal training).
- FR-D9: Panel validasi terhadap rekap SiPongi+/BNPB (input unggah CSV atau manual).
- FR-D10: Filter global: rentang tanggal, provinsi, sensor, confidence minimum.
- FR-D11: Tombol "Perbarui agregasi/prediksi" yang memicu job Spark.
- FR-D12: Atribusi sumber data di footer.

### 8.4 Akuisisi NiFi (NiFi 1.28.1 terpasang, HTTP :8080)
- FR-N1: Flow: scheduler (`GenerateFlowFile` atau timer driven) -> `InvokeHTTP` (FIRMS API `area`, bbox Indonesia, 1-2 hari terakhir, VIIRS dan MODIS NRT) -> `RouteOnAttribute` (cek status) -> `UpdateAttribute` (nama file memuat timestamp) -> `PutHDFS` ke `/karhutla/raw/firms_nrt/date=YYYY-MM-DD/`.
- FR-N2: Jadwal tiap 3 jam. FR-N3: retry dan route failure. FR-N4: ekspor flow ke `nifi/flow.json` dan dokumentasikan. FR-N5: job backend memproses file NRT baru (dedup dengan data historis, bersihkan, tulis ke `clean/hotspot`) dan kompaksi file kecil harian. FR-N6: fallback endpoint `/api/ingest/firms-nrt` bila NiFi tidak jalan.
- `PutHDFS` memakai `core-site.xml` dan `hdfs-site.xml` seperti alur yang sudah ada. Jangan mengubah alur lama (GetFile -> PutHDFS), buat process group baru "karhutla-nrt".

## 9. API (FastAPI, prefix `/api`)

| Metode | Endpoint | Fungsi |
|---|---|---|
| GET | `/health` | Status backend, HDFS, Spark, serving layer |
| POST | `/datasets/upload/init`, `/upload/chunk`, `/upload/complete` | Upload chunk ke staging lalu `hdfs dfs -put` |
| GET | `/datasets`, `/datasets/summary`, `/datasets/{id}/preview` | Daftar, total baris/ukuran, pratinjau |
| DELETE | `/datasets/{id}` | Hapus (hanya di bawah `/karhutla`) |
| POST | `/preprocessing/profile`, `/preprocessing/run` | Job profiling dan pipeline |
| GET | `/jobs`, `/jobs/{id}` | Status, log, laporan |
| POST | `/analytics/refresh` | Agregasi dan ekspor serving layer |
| GET | `/analytics/kpi`, `/hotspots/latest`, `/trend`, `/ranking`, `/seasonality`, `/weather-correlation` | Data dashboard |
| POST | `/ml/train`, `/ml/predict` | Job ML |
| GET | `/ml/risk-map`, `/ml/metrics` | Hasil model |
| POST | `/ingest/firms-nrt` | Tarik NRT manual (fallback) |
| POST/GET | `/validation/reference`, `/validation/compare` | Data pembanding dan perbandingan |

Aturan: operasi Spark asinkron (`job_id` + polling), satu job aktif pada satu waktu, endpoint titik wajib ada batas jumlah dan filter bbox, OpenAPI di `/docs`, CORS hanya untuk `http://localhost:3000`.

## 10. Spesifikasi Machine Learning

| Aspek | Spesifikasi |
|---|---|
| Unit sampel | (grid_id, tanggal t) |
| Label | `y=1` bila ada hotspot confidence nominal/tinggi di grid pada t+1 sampai t+7 |
| Fitur hotspot | jumlah hotspot 1/3/7/14/30 hari terakhir; rata-rata FRP 7 hari; hari sejak hotspot terakhir; hotspot 8 sel tetangga 7 hari |
| Fitur cuaca | hujan total 7/14/30 hari; hari kering berturut-turut; suhu dan kelembapan rata-rata 7 hari; angin (ERA5) |
| Fitur waktu | bulan, dayofyear (sin/cos) |
| Fitur lokasi | lat, lon, provinsi (indexed) |
| Model | `RandomForestClassifier` (baseline) dan `GBTClassifier` (pembanding) |
| Ketidakseimbangan | `weightCol` atau undersampling negatif |
| Split | berbasis waktu (misalnya train sampai 2022, validasi 2023, test 2024+); dilarang split acak |
| Metrik | AUC-ROC, AUC-PR, precision, recall, F1, confusion matrix, feature importance |
| Baseline | persistensi (ada hotspot 7 hari terakhir -> prediksi ada) |
| Keluaran | `risk_score` 0-1, kategori (rendah <0,25; sedang <0,5; tinggi <0,75; sangat tinggi >=0,75), `model_version`, `predicted_at`, `horizon_days` |

"Kapan": kurva risiko mingguan dan pola musiman. "Di mana": peta risiko grid. UI wajib menyatakan bahwa ini estimasi risiko, bukan kepastian. Karena 8 core dan RAM terbatas, batasi ukuran tabel latih (misalnya grid dan rentang tahun terpilih) dan lakukan `repartition` moderat.

## 11. Skema Serving/Metadata (SQLite + DuckDB/Parquet)

Tabel metadata (SQLite): `datasets(id, name, dataset_type, hdfs_path, size_bytes, row_count, column_count, uploaded_at)`, `jobs(id, job_type, status, config_json, report_json, log_tail, started_at, finished_at)`, `model_metrics(model_version, auc_roc, auc_pr, precision, recall, f1, confusion_json, feature_importance_json, trained_at)`, `reference_validation(date, province, source, hotspot_count, burned_area_ha)`.

File serving (Parquet di `C:\karhutla-data\serving\`, dibaca DuckDB): `agg_daily_province(date, province, hotspot_count, high_conf_count, avg_frp)`, `agg_monthly_grid(year, month, grid_id, lat, lon, hotspot_count)`, `hotspot_latest(lat, lon, acq_ts, satellite, confidence_level, frp, province)`, `risk_prediction(grid_id, lat, lon, target_date, horizon_days, risk_score, risk_category, model_version, predicted_at)`.

### 11.1 Skema Kanonik `clean/hotspot`
`latitude, longitude, acq_ts_utc, acq_ts_wib, year, month, day, dayofyear, hour, satellite, instrument, confidence_level, brightness, brightness_2, frp, daynight, grid_id, province, frp_norm, brightness_norm, source_file`.

## 12. Persyaratan Non-Fungsional
- NFR-1: Dashboard membaca data agregat, bukan scan data mentah.
- NFR-2: Pipeline mampu memproses >= 5 juta baris di mesin target tanpa OOM (uji bertahap 100 ribu, 1 juta, 5 juta).
- NFR-3: Job idempoten (overwrite per partisi), gagal tercatat dengan pesan jelas.
- NFR-4: Reproducibility: skrip `scripts\start_all.bat`, `stop_all.bat`, `check_env.bat`/`check_env.py` untuk memeriksa HDFS, Spark, NiFi, port, dan env var.
- NFR-5: Secrets di `.env`; validasi tipe dan ukuran file; operasi hapus dibatasi di `/karhutla`.
- NFR-6: Log terstruktur dan endpoint `/health`.
- NFR-7: Lint dan format (ruff, eslint, tsc).
- NFR-8: Dokumentasi: README, diagram arsitektur, catatan Windows, skrip demo.
- NFR-9: Atribusi data di UI.

## 13. Struktur Repositori (`C:\projects\karhutla-watch`)

```
karhutla-watch/
  README.md  .env.example
  docs/ (architecture.md, windows-notes.md, data-dictionary.md)
  scripts/ (start_all.bat, stop_all.bat, check_env.py, download_firms.py, download_chirps.py, download_era5.py)
  nifi/ (flow.json, README.md)
  backend/
    app/ (main.py, routers/, services/hdfs_cli.py, services/jobs.py, services/serving.py, schemas/)
    spark_jobs/ (common.py, profile.py, preprocess.py, features.py, aggregate.py, train.py, predict.py)
    tests/  requirements.txt
  frontend/ (app/page.tsx, app/preprocessing/page.tsx, app/dashboard/page.tsx, components/, lib/api.ts)
  data_samples/
```
`services/hdfs_cli.py` membungkus `hdfs dfs` (put, ls, du, count, mkdir, rm) dengan environment `HADOOP_USER_NAME=hadoop`, timeout, dan parsing output yang tidak memakai format `%`.

## 14. Rencana Pengerjaan

| Fase | Isi | Pemilik | Estimasi |
|---|---|---|---|
| 0 | Verifikasi lingkungan (4.5): PySpark baca/tulis HDFS, versi Python, `check_env.py`, buat `/karhutla/...` | A | 3-5 hari |
| 1 | Unduh FIRMS/CHIRPS/ERA5, hitung baris, kunci rentang tahun | A | 1 minggu |
| 2 | Backend upload (chunk -> staging -> `hdfs dfs -put`) + halaman Upload | A, B | 1-2 minggu |
| 3 | Spark profiling/pre-processing + halaman Preprocessing | A (job), B (UI) | 2 minggu |
| 4 | Agregasi, serving layer, Dashboard (KPI, peta, tren, ranking) | A, B | 2 minggu |
| 5 | Feature engineering, model, peta risiko, panel metrik | B (ML), A | 2 minggu |
| 6 | Flow NiFi NRT + job ingest NRT | A | 1 minggu |
| 7 | Validasi SiPongi+/BNPB, pengujian, optimasi, dokumentasi, rehearsal | A, B | 1-2 minggu |

Prioritas bila waktu mepet: Fase 0-4, lalu 6, lalu 5, lalu 7.

## 15. Pengujian
- Unit: fungsi cleaning/normalisasi (data kecil), `grid_id`, pembuatan label.
- Integrasi: upload -> HDFS -> preview; job Spark -> Parquet -> serving layer.
- Skala: 100 ribu, 1 juta, 5 juta baris dengan catatan waktu dan memori puncak.
- Kualitas data: tidak ada koordinat di luar Indonesia, tidak ada duplikat kunci, jumlah baris per langkah konsisten.
- ML: tidak ada kebocoran waktu, metrik melampaui baseline persistensi.
- UI: alur 3 halaman end-to-end, filter, kondisi kosong dan error.
- Resiliensi: NiFi/FIRMS gagal, CSV rusak, job gagal, HDFS mati (pesan jelas).
- Validasi: korelasi tren bulanan hotspot dengan rekap SiPongi+/BNPB.

## 16. Risiko dan Mitigasi

| Risiko | Mitigasi |
|---|---|
| RAM 16 GB terbatas | Jalankan hanya HDFS tanpa YARN, Spark 4 GB, NiFi sesuai kebutuhan, Parquet, partisi, satu job pada satu waktu |
| Path dengan spasi pada username | Semua kerja di `C:\projects` dan `C:\karhutla-data`, `HADOOP_USER_NAME=hadoop` di setiap subprocess |
| Ketidakcocokan PySpark/Python 3.14 atau jar Hadoop | Verifikasi Fase 0, fallback venv Python 3.12/3.13 |
| Upload via WebHDFS/UI gagal (redirect hostname) | Gunakan `hdfs dfs -put` dari staging lokal |
| Format ulang NameNode tidak sengaja | Larangan eksplisit di PRD |
| File kecil banyak di HDFS (NRT) | Kompaksi harian oleh Spark atau MergeContent di NiFi |
| Awan menutupi hotspot, hotspot bukan kepastian kebakaran | Cantumkan keterbatasan di UI dan laporan |
| Latensi satelit sekitar 3 jam | Sebut "near real-time" dan tampilkan waktu pembaruan terakhir |
| Batas permintaan FIRMS API | Unduh historis per potongan, polling NRT tiap 3 jam |
| CHIRPS v2 berhenti diproduksi setelah Desember 2026 | Pertimbangkan CHIRPS v3 atau ERA5, cek ketersediaan |
| Ketidakseimbangan kelas | Class weight/undersampling, evaluasi AUC-PR |
| Skema VIIRS vs MODIS berbeda | Skema kanonik di tahap clean |
| Batas provinsi butuh GeoJSON | Cari sumber resmi/terbuka dan verifikasi lisensi |

## 17. Definisi Selesai
1. Semua AC (2.2) terpenuhi pada data nyata >= 1 juta baris.
2. Tiga halaman berfungsi end-to-end.
3. Flow NiFi berjalan, terdokumentasi, dengan bukti file NRT di HDFS.
4. Model terlatih, metrik tercatat, peta risiko tampil.
5. README dan skrip start/stop/check memungkinkan menjalankan dari nol di mesin ini.
6. Skrip demo (urutan klik dan narasi) tersedia.

## 18. Instruksi untuk Agent Pelaksana
- Lingkungan sudah terpasang dan stabil. Jangan instal ulang, format ulang, ubah konfigurasi inti, atau menambah Docker/WSL/VM.
- Mulai dari Fase 0 dan laporkan hasil verifikasi kompatibilitas (4.5) sebelum menulis kode fitur.
- Jangan mengubah atau menghapus path HDFS lama (`/hr-data`, `/warehouse`, `/user/alfarel`, `/test`, `/testupload`) maupun alur NiFi yang sudah ada.
- Patuhi 4.4: `HADOOP_USER_NAME=hadoop`, forward slash, tanpa `-stat` dengan `%`, upload via `hdfs dfs -put`, path tanpa spasi.
- Jangan berasumsi nama kolom atau versi. Periksa data dan versi nyata. Tandai hal yang tidak dapat diverifikasi sebagai TODO, jangan mengarang data atau metrik.
- Hormati anggaran memori (4.6). Satu job Spark pada satu waktu.
- Semua job Spark idempoten dan melaporkan jumlah baris input/output.
- Jangan menaruh data besar di repositori.
- Jangan mengubah lingkup (misalnya menambah autentikasi atau streaming) tanpa persetujuan pengguna.
