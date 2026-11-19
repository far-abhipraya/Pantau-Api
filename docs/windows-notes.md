# Catatan Windows (PantauApi)

Dokumen ini mencatat hal-hal spesifik untuk menjalankan PantauApi pada Windows 11
menurut spesifikasi PRD Bagian 4 dan 18.

## Spesifikasi Mesin Target

| Item | Spesifikasi |
|------|-------------|
| Perangkat | Lenovo Yoga 7, Ryzen 7 8840HS |
| RAM | 16 GB (sekitar 13,8 GB usable) |
| OS | Windows 11 |
| Username | Mengandung spasi (hindari path di folder home pengguna) |
| Java | 17 (Temurin) |
| Hadoop | 3.5.0 (single-node, `C:\hadoop-3.5.0`) |
| Spark | 4.2.0 (`local[4]`, `C:\spark-4.2.0-bin-hadoop3`) |
| NiFi | 1.28.1 (HTTP :8080) |
| Python | 3.14 |

## Aturan Path (Penting!)

Semua kode, data, dan temp harus berada di path **TANPA spasi**:

- Repo: `C:\projects\karhutla-watch`
- Data: `C:\karhutla-data` (serving, staging, spark-tmp, inbox, downloads, logs)
- HDFS project data: `/karhutla/` saja

Jangan taruh apa pun di folder home pengguna (`C:\Users\<nama>\...`) karena username mengandung spesa.

## Skrip Start/Stop

| Skrip | Fungsi |
|-------|--------|
| `scripts\start_hdfs.bat` | Start HDFS (CMD Administrator) |
| `scripts\stop_hdfs.bat` | Stop HDFS |
| `scripts\start_nifi.bat` | Start NiFi (hanya bila perlu, ~1,5 GB RAM) |
| `scripts\check_env.py` | Verifikasi lingkungan sebelum menulis fitur |

## Jalankan Backend

```powershell
cd C:\projects\karhutla-watch\backend
$env:HADOOP_USER_NAME="hadoop"
python -m uvicorn app.main:app --port 8000 --reload
```

## Jalankan Frontend

```powershell
cd C:\projects\karhutla-watch\frontend
npm run dev
```

Buka: `http://localhost:3000`

## Jalankan Job Spark (Satu Sekali)

```powershell
cd C:\projects\karhutla-watch
$env:HADOOP_USER_NAME="hadoop"
spark-submit --master local[4] --driver-memory 4g backend\spark_jobs\<job>.py
```

Contoh: `features.py`, `train.py`, `predict.py`, `compact_nrt.py`, `aggregate.py`

## Aturan Mutlak (AGENTS.md)

1. Jangan `hdfs namenode -format`.
2. Jangan ubah/hapus path HDFS lama: `/hr-data`, `/warehouse`, `/user/alfarel`, `/test`, `/testupload`.
3. Jangan ubah `core-site.xml`, `hdfs-site.xml`, `yarn-site.xml`, `mapred-site.xml`, `hadoop-env.cmd` tanpa persetujuan.
4. Setiap proses Hadoop/Spark memakai env `HADOOP_USER_NAME=hadoop`.
5. Jangan `hdfs dfs -stat` dengan format `%`; pakai `-ls`, `-du`, `-count`.
6. Upload/ingest ke HDFS = staging lokal lalu `hdfs dfs -put`.
7. Satu job Spark pada satu waktu (`local[4]`, driver 4g).
8. Tanpa autentikasi dan tanpa streaming sungguhan.
9. Jangan commit kredensial; gunakan `.env`.

## Environment Variable (`.env` di root, `.env.local` di frontend)

Buat file `.env` di root repo berdasarkan `.env.example`. Isi kredensial (FIRMS_MAP_KEY, dll.) di `.env` dan `frontend/.env.local` — **jangan commit**.

## Masalah Umum

| Masalah | Penyelesaian |
|---------|--------------|
| RAM bebas kurang (< 2 GB) | Spark driver memory diturunkan otomatis (min 2g) |
| NiFi tidak running (port 8080) | Jalankan `scripts\start_nifi.bat` bila diperlukan |
| Stale cache frontend 500 | Hapus `frontend\.next` lalu restart dev server |
| Backend reload misbehave | Restart backend manual |
| `hdfs dfs -test -e` tidak andal | Pakai `hdfs dfs -ls` sebagai pengganti |

## Verifikasi Akhir

```powershell
# Backend API
python -m pytest backend\tests -q

# Frontend build
cd frontend && npm run build

# TypeScript + ESLint
npx tsc --noEmit
npx eslint .

# Environment
python scripts\check_env.py
```
