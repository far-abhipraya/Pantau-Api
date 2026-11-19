# PantauApi

Platform Big Data (Hadoop HDFS + Spark + NiFi + FastAPI + Next.js) untuk memantau dan memprediksi risiko kebakaran hutan dan lahan (karhutla) di Indonesia menggunakan data hotspot NASA FIRMS.

Tiga halaman:
- **Peta** (`/`) — titik hotspot, agregasi grid, dan lapisan risiko prediksi.
- **Data & Pre-processing** (`/data`) — sumber data, impor folder, upload manual, profil, dan riwayat job Spark.
- **Analitik** (`/analytics`) — KPI, tren, ranking provinsi, musiman, faktor pengaruh, cuaca, prediksi ML, dan validasi referensi.

Stack: Next.js 16 (TypeScript, Tailwind, react-leaflet, ECharts) | FastAPI + SQLAlchemy + SQLite | PySpark/Spark SQL/MLlib | HDFS 3.5.0 | NiFi 1.28.1 | DuckDB + Parquet lokal.

---

## Syarat Sistem (Windows)

| Komponen | Versi | Catatan |
|----------|-------|---------|
| Java | 17 | Sudah terpasang native di Windows |
| Hadoop | 3.5.0 | `C:\hadoop-3.5.0`, hanya HDFS (tanpa YARN) |
| Spark | 4.2.0 | `C:\spark-4.2.0-bin-hadoop3` |
| Python | 3.14 | Native di Windows |
| Node.js / npm | Terbaru | Untuk frontend Next.js 16 |
| RAM | Minimal 8 GB disarankan | Spark driver diberi batas agar tidak OOM |

**Peringatan penting (AGENTS.md):**
- Jangan pernah menjalankan `hdfs namenode -format`.
- Jangan mengubah/hapus path HDFS lama: `/hr-data`, `/warehouse`, `/user/alfarel`, `/test`, `/testupload`. Data proyek hanya di `/karhutla/`.
- Jangan mengedit `core-site.xml`, `hdfs-site.xml`, `yarn-site.xml`, `mapred-site.xml`, atau `hadoop-env.cmd` tanpa persetujuan.
- Setiap proses Hadoop/Spark perlu `HADOOP_USER_NAME=hadoop`.
- Satu job Spark pada satu waktu (`local[4]`, driver 4 GB).
- Kode, data, dan temp harus di path **tanpa spasi**: `C:\projects\karhutla-watch` dan `C:\karhutla-data`.
- Tidak ada autentikasi dan tidak ada streaming sungguhan. Data tidak boleh dikarang.

---

## Langkah Awal (Dari Nol)

### 1. Clone repositori

```powershell
git clone https://github.com/far-abhipraya/Pantau-Api.git
cd Pantau-Api
```

### 2. Siapkan environment variabel

Salin contoh dan isi nilai rahasia (contoh: `FIRMS_MAP_KEY` dari NASA FIRMS):

```powershell
copy .env.example .env
```

Edit `.env` sesuai environment lokal. Path penting sudah diatur default ke:
- `HDFS_BASE_PATH=/karhutla`
- `DATA_DIR=C:/karhutla-data`
- `INBOX_DIR=C:/karhutla-data/inbox`
- `SERVING_DIR=C:/karhutla-data/serving`

### 3. Verifikasi lingkungan

```powershell
python scripts\check_env.py
```

Pastikan semua pemeriksaan lulus (Java, Hadoop, Spark, Python, Node, HDFS, port).

### 4. Nyalakan HDFS

Jalankan **CMD sebagai Administrator**:

```bat
scripts\start_hdfs.bat
```

Verifikasi NameNode: `http://localhost:9870`

> Jika DataNode tidak aktif (semua blok "missing"), periksa log di `C:\hadoop-3.5.0\logs` dan pastikan tidak ada proses Java lain yang memegang port 9000/9870/50010/50075. Jangan jalankan `hdfs namenode -format`.

### 5. Nyalakan Backend (FastAPI)

```powershell
cd backend
$env:HADOOP_USER_NAME="hadoop"
python -m uvicorn app.main:app --reload --port 8000
```

Verifikasi: `http://localhost:8000/api/health` harus mengembalikan `status: ok` dan `hdfs.reachable: true`.

OpenAPI dokumentasi: `http://localhost:8000/docs`

### 6. Nyalakan Frontend (Next.js)

```powershell
cd frontend
npm run dev
```

Verifikasi: `http://localhost:3000` (Peta) dapat dimuat.

---

## Alur Data (Pipeline)

```
1. Akuisisi
   ├─ Impor folder manual: C:\karhutla-data\inbox  -> POST /api/ingest/inbox
   ├─ Upload manual bertahap: POST /api/datasets/upload/*
   └─ NRT FIRMS (fallback NiFi): POST /api/ingest/firms-nrt
2. Pre-processing (Spark job: preprocess.py)
   └─ Output: /karhutla/clean/hotspot (Parquet di HDFS)
3. Serving layer (Spark job: aggregate.py)
   └─ Output: C:\karhutla-data\serving\ (Parquet + DuckDB + SQLite meta.db)
4. API baca dari serving layer (tidak hit Spark secara langsung)
```

### Menjalankan pre-processing + agregasi

```powershell
cd backend
# Pre-processing (satu job pada satu waktu)
python -m uvicorn app.main:app --reload --port 8000 &  # backend harus sudah nyala
Invoke-RestMethod -Uri "http://localhost:8000/api/preprocessing/run" -Method Post -Body (@{ config = @{} } | ConvertTo-Json) -ContentType "application/json"

# Setelah pre-processing selesai, jalankan agregasi serving layer
Invoke-RestMethod -Uri "http://localhost:8000/api/analytics/refresh" -Method Post
```

Pantau status job di `http://localhost:8000/api/jobs` atau halaman `/data` -> **Riwayat Job**.

Hasil serving layer tersimpan di `C:\karhutla-data\serving\` dan metadata di `C:\karhutla-data\serving\meta.db`.

---

## Endpoint API Utama

| Metode | Path | Deskripsi |
|--------|------|-----------|
| GET | `/api/health` | Status backend, HDFS, Spark, dan serving layer |
| GET | `/api/sources` | Status sumber data, total baris, dan freshness |
| POST | `/api/ingest/inbox` | Impor folder inbox sekarang |
| POST | `/api/ingest/firms-nrt` | Unduh NRT FIRMS manual (fallback NiFi) |
| POST | `/api/ingest/compact-nrt` | Kompaksi file kecil NRT (Spark) |
| POST | `/api/preprocessing/run` | Jalankan pre-processing (job Spark asinkron) |
| GET | `/api/preprocessing/latest` | Laporan pre-processing terakhir |
| POST | `/api/analytics/refresh` | Jalankan ulang agregasi serving layer |
| GET | `/api/analytics/kpi` | KPI hero peta dan analitik |
| GET | `/api/map/risk?min_score=0.75` | Grid risiko prediksi 7 hari |
| GET | `/api/jobs` | Riwayat dan status job Spark |

---

## Akuisisi NRT FIRMS (Tanpa NiFi)

Karena NiFi membutuhkan RAM besar (~1,5 GB) dan belum dijalankan di mesin development, endpoint fallback tersedia:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/ingest/firms-nrt" -Method Post -Body (@{ days = 2 } | ConvertTo-Json) -ContentType "application/json"
```

Unduh data FIRMS NRT via API NASA langsung dan unggah ke `/karhutla/raw/firms_nrt/date=YYYY-MM-DD/` di HDFS.

Lalu jalankan pre-processing dan agregasi agar data terbaru muncul di UI.

---

## NiFi (Opsional, Fase 7)

NiFi belum dijalankan di mesin development karena keterbatasan RAM (~1,5 GB diperlukan, hanya ~0.6–2.4 GB tersedia). Flow sudah tersedia di `nifi/flow.json` dengan panduan di `nifi/README.md`.

Jika ingin mencoba NiFi:
1. Jalankan NiFi: `scripts\start_nifi.bat` (port 8080).
2. Buka `http://localhost:8080/nifi`.
3. Buat Process Group `karhutla-nrt`, impor `nifi/flow.json`.
4. Konfiguri `FIRMS_MAP_KEY`, `FIRMS_BBOX`, dan Hadoop Configuration Resources.
5. Mulai semua processor.

Endpoint `/api/ingest/firms-nrt` dan `/api/ingest/compact-nrt` tetap berfungsi sebagai fallback saat NiFi tidak nyala.

---

## Troubleshooting

### HDFS / DataNode tidak aktif (semua blok "missing")

Gejala: `/api/health` mengembalikan `hdfs.reachable: false`, atau Spark gagal membaca blok dengan `BlockMissingException: No live nodes contain current block`.

Penyebab umum: NameNode nyala tetapi DataNode tidak terdaftar (hampir semua proses Java dimatikan saat restart).

Coba langkah berikut:

1. Matikan semua proses Java terkait Hadoop/Spark:
   ```powershell
   Get-Process java | Stop-Process -Force
   ```
2. Nyalakan HDFS lagi (CMD Administrator):
   ```bat
   scripts\start_hdfs.bat
   ```
3. Tunggu NameNode siap (~15 detik), lalu periksa:
   ```bat
   hdfs dfsadmin -report
   ```
   Pastikan bagian **Datanodes** menunjukkan **Live Nodes: 1** dan **Dead Nodes: 0**.
4. Jika masih ada missing blocks, periksa log di `C:\hadoop-3.5.0\logs\hadoop-*-datanode-*.log`.

> Jangan jalankan `hdfs namenode -format` (dilarang oleh AGENTS.md).

### Spark job gagal / OOM

- Pastikan RAM bebas cukup (minimal ~2 GB untuk driver).
- Memori driver diturunkan otomatis bila RAM bebas kurang (lihat `backend/app/pipeline/spark_runner.py`).
- Satu job Spark pada satu waktu; job lain akan menunggu dalam antrean.

### Frontend crash saat kembali ke halaman Peta

Sudah diperbaiki di commit terbaru (`SafeMapContainer`). Pastikan frontend di-build ulang atau di-restart setelah `npm install` jika ada perubahan dependensi.

### Data masih "Data tertunda"

Berarti serving layer belum diperbarui dengan data terbaru. Jalankan:
1. `POST /api/ingest/firms-nrt` (atau tambahkan file ke `C:\karhutla-data\inbox` lalu `POST /api/ingest/inbox`).
2. `POST /api/preprocessing/run`.
3. `POST /api/analytics/refresh`.

Lalu periksa `http://localhost:8000/api/health` -> `serving.freshness.label` harus `Data terkini`.

---

## Verifikasi Kriteria Terima (AC-1 s/d AC-9)

| Kriteria | Status | Keterangan |
|----------|--------|------------|
| AC-1: Dataset mentah >= 1.000.000 baris di HDFS | ✅ Terpenuhi | clean/hotspot: 2.134.784 baris |
| AC-2: Format FIRMS (VIIRS/MODIS/arsip/API) terbaca otomatis | ✅ Terpenuhi | Adapter deteksi format + karantina |
| AC-3: Pre-processing Parquet di `/karhutla/clean` + laporan | ✅ Terpenuhi | Spark pre-processing, laporan funnel |
| AC-4: Peta <= 3 detik (jendela 24 jam), max 20.000 titik | ✅ Terpenuhi | KPI ~190 ms, grid ~51 ms, hotspot maks 246 ms |
| AC-5: Dashboard Analitik <= 5 detik | ✅ Terpenuhi | Semua endpoint <= 744 ms |
| AC-6: NiFi NRT tiap 3 jam ke `/karhutla/raw/firms_nrt` | ⚠️ Siap | `nifi/flow.json` tersedia; fallback endpoint aktif |
| AC-7: Model metrik + split waktu + baseline persistensi | ✅ Terpenuhi | RF: AUC-ROC 0,886 / AUC-PR 0,686; baseline: 0,752 / 0,501 |
| AC-8: Upload manual melewati pipeline yang sama | ✅ Terpenuhi | `POST /api/datasets/*`, `ingest.py` |
| AC-9: README memungkinkan jalan dari nol | 🔄 Dalam proses | Dokumen ini |

---

## Struktur Direktori Penting

```
C:\projects\karhutla-watch\          # Repositori kode
  backend\                           # FastAPI + pipeline + Spark jobs
  frontend\                          # Next.js UI
  docs\                              # PRD, UI_SPEC, DESIGN, TASKS, dll
  scripts\                           # start_hdfs.bat, stop_hdfs.bat, check_env.py
  nifi\                              # flow.json + README (Fase 7)

C:\karhutla-data\                    # Data, serving, log (tanpa spasi)
  inbox\                             # Folder impor manual
  serving\                           # Parquet + DuckDB + meta.db + logs/jobs
  spark-tmp\                         # Temp Spark
  staging\                           # Staging sebelum unggah ke HDFS
```

---

## Lisensi dan Catatan Pengembangan

- Dokumentasi teknis lengkap ada di `docs/`: PRD, UI_SPEC, DESIGN, ENVIRONMENT, TASKS, DATA_SOURCES, MODEL, ARCHITECTURE, DEMO, windows-notes.
- Aturan agent aktif ada di `AGENTS.md` dan `.agents/rules/`.
- Data proyek **tidak di-commit ke Git** (terlalu besar). Hanya artefak sampel kecil di `artifacts/` dan `data_samples/`.
- Tidak ada data, kolom, versi, atau metrik yang dikarang dalam dokumen dan kode.
