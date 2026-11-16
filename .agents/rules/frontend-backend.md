# Aturan: Frontend dan Backend

## Backend (FastAPI)
- Prefix `/api`; OpenAPI di `/docs`. CORS hanya `http://localhost:3000`.
- Operasi Spark asinkron: balas `job_id`, klien polling `/api/jobs/{id}`. Antrian job tunggal.
- Upload manual: chunk -> staging `C:\karhutla-data\staging\<upload_id>` -> gabung streaming -> `POST /datasets/detect` memberi ringkasan -> setelah konfirmasi `hdfs dfs -put -f` -> verifikasi `-du` -> hapus staging -> catat metadata -> memicu pipeline.
- Hapus HDFS hanya di bawah `/karhutla/`; tolak path lain dan `..`.
- Endpoint peta: bbox wajib, `limit` maks 20000, resolusi grid menurut `zoom` (1,0/0,5/0,25 derajat). Baca dari serving layer (DuckDB atas Parquet di `C:\karhutla-data\serving`), bukan HDFS.
- Konfigurasi dari `.env` (pydantic-settings); jangan hardcode path.

## Frontend (Next.js)
- Rute: `/` (Peta), `/data`, `/analytics`. Semua panggilan API lewat `lib/api.ts`.
- Peta: react-leaflet, clustering, muat data per bbox yang terlihat, debounce saat pan/zoom. Batas provinsi opsional (peta tetap berfungsi tanpa GeoJSON).
- Grafik: ECharts, tanpa animasi masuk.
- Halaman `/data`: strip status + tab; tombol "Tambah data" sekunder membuka modal deteksi format.
- Tampilkan waktu pembaruan terakhir, state loading/kosong/error, dan atribusi sumber data.
- Implementasi visual mengikuti `.agents/rules/ui-design.md`.
