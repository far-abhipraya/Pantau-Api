# Aturan: Frontend dan Backend

## Backend (FastAPI)
- Prefix `/api`. Dokumentasi OpenAPI aktif di `/docs`.
- Operasi Spark asinkron: balas `job_id`, klien polling `/api/jobs/{id}`. Antrian job tunggal.
- Upload: chunk -> staging `C:\karhutla-data\staging\<upload_id>` -> gabung streaming -> `hdfs dfs -put -f` -> verifikasi ukuran dengan `-du` -> hapus staging -> simpan metadata.
- Operasi hapus HDFS hanya boleh di bawah `/karhutla/`. Tolak path lain dan path dengan `..`.
- Validasi nama file, ekstensi `.csv`, ukuran, dan tipe dataset.
- CORS hanya `http://localhost:3000`.
- Dashboard membaca serving layer (DuckDB atas Parquet di `C:\karhutla-data\serving`), bukan HDFS langsung.
- Konfigurasi dari `.env` (pydantic-settings). Jangan hardcode path.

## Frontend (Next.js)
- Tiga halaman: `/` (Upload), `/preprocessing`, `/dashboard`. Semua panggilan API lewat `lib/api.ts`.
- Upload chunk 8-16 MB dengan progress bar. Tampilkan total baris dan indikator >= 1.000.000.
- Peta: react-leaflet + clustering, batasi jumlah titik. Grafik: ECharts.
- Tampilkan kondisi loading, kosong, dan error. Tampilkan waktu pembaruan data terakhir.
- Footer atribusi sumber data.
