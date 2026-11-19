# NiFi Flow: karhutla-nrt (Fase 7)

Dokumen ini menjelaskan alur NiFi untuk akuisisi data FIRMS Near Real-Time (NRT)
secara otomatis tiap 3 jam, sesuai PRD FR-N1 dan AC-6.

## Alur Data

```
Timer 3 Jam -> InvokeHTTP FIRMS Area -> RouteOnAttribute -> UpdateAttribute -> PutHDFS
                                                     |-> LogAttribute (failure route)
```

### Langkah-langkah

| Proses | Deskripsi |
|---|---|
| **Timer 3 Jam** | `GenerateFlowFile` yang memicu alur setiap 3 jam (cron `0 0 */3 * * ?`). |
| **InvokeHTTP FIRMS Area** | Memanggil NASA FIRMS API `area` untuk bbox Indonesia, VIIRS + MODIS NRT, rentang 1-2 hari. Membutuhkan `FIRMS_MAP_KEY` di `.env`. |
| **RouteOnAttribute** | Memeriksa kode respons HTTP. `200` lanjut ke `UpdateAttribute`, non-`200` diarahkan ke `LogAttribute`. |
| **UpdateAttribute** | Menetapkan nama file dengan timestamp dan partisi tanggal (`date=YYYY-MM-DD`). |
| **PutHDFS** | Menulis file ke HDFS di `/karhutla/raw/firms_nrt/date=YYYY-MM-DD/`. |
| **LogAttribute (failure route)** | Mencatat kegagalan ke log NiFi untuk audit. |

## Path HDFS

```
# Tujuan PutHDFS (per tanggal):
/karhutla/raw/firms_nrt/date=2026-11-18/firms_nrt_VIIRS_20261118_143000.csv

# Hasil kompaknya (Spark job compact_nrt.py):
/karhutla/raw/firms_nrt_compacted/date=2026-11-18/part-*.parquet
```

## Cara Import ke NiFi

1. Jalankan NiFi: `scripts\start_nifi.bat` (port 8080).
2. Buka UI NiFi: `http://localhost:8080/nifi`.
3. Buat Process Group baru bernama `karhutla-nrt`.
4. Masuk ke Process Group, pilih **Template -> Import**, pilih berkas `flow.json`.
5. Konfigurasi properti berikut sesuai environment:
   - `FIRMS_MAP_KEY`: NASA FIRMS MAP key (isi di `.env`).
   - `FIRMS_BBOX`: `95,-11,141,6` (Indonesia).
   - Hadoop Configuration Resources: jalur `core-site.xml` dan `hdfs-site.xml`.
6. Mulai semua processor dalam Process Group.

## Fallback saat NiFi Tidak Berjalan

Jika NiFi tidak tersedia, gunakan endpoint fallback:

```bash
curl -X POST http://localhost:8000/api/ingest/firms-nrt -H "Content-Type: application/json" -d '{"days": 2}'
```

Endpoint ini mengunduh data FIRMS NRT via API langsung dan mengunggahnya ke
`/karhutla/raw/firms_nrt/date=YYYY-MM-DD/` di HDFS.

## Kompaksi File Kecil (FR-N5)

Setelah berkas NRT terkumpul, jalankan job Spark kompak:

```bash
spark-submit --master local[4] --driver-memory 4g backend\spark_jobs\compact_nrt.py --job-id compact-nrt-job
```

Job ini membaca semua CSV di `/karhutla/raw/firms_nrt/date=*/` dan menulis
Parquet terpartisi ke `/karhutla/raw/firms_nrt_compacted/date=YYYY-MM-DD/`.

## Catatan

- Alur NiFi lama tidak diubah (sesuai AGENTS.md aturan mutlak nomor 4).
- Semua proses HDFS memakai `HADOOP_USER_NAME=hadoop`.
- Penghapusan HDFS hanya diizinkan di bawah `/karhutla/`.
- Data proyek hanya di `/karhutla/`, tidak di path lama (`/hr-data`, `/warehouse`, dll).
