# AGENTS.md: PantauApi

Platform big data pemantauan dan prediksi risiko karhutla Indonesia (proyek akhir Big Data & Analitik). Rujukan: `docs/PRD.md` (v1.2), `docs/UI_SPEC.md`, `docs/DESIGN.md`, `docs/ENVIRONMENT.md`, `docs/TASKS.md`, `docs/DATA_SOURCES.md`. Aturan terperinci di `.agents/rules/`.

## Aturan Mutlak
1. Hadoop 3.5.0, Spark 4.2.0, NiFi 1.28.1, Java 17, Python sudah terpasang NATIVE di Windows. Jangan instal ulang, pindahkan, atau menambah Docker/WSL/VM.
2. Jangan pernah `hdfs namenode -format`.
3. Jangan ubah/hapus path HDFS lama: `/hr-data`, `/warehouse`, `/user/alfarel`, `/test`, `/testupload`. Data proyek hanya di `/karhutla/`.
4. Jangan ubah `core-site.xml`, `hdfs-site.xml`, `yarn-site.xml`, `mapred-site.xml`, `hadoop-env.cmd`, atau alur NiFi lama tanpa persetujuan eksplisit.
5. Setiap proses Hadoop/Spark memakai env `HADOOP_USER_NAME=hadoop`.
6. Jangan `hdfs dfs -stat` dengan format `%`. Pakai `-ls`, `-du`, `-count`.
7. Upload/ingest ke HDFS = staging lokal lalu `hdfs dfs -put`. Jangan mengandalkan WebHDFS/Web UI upload.
8. Kode, data, temp di path TANPA spasi: `C:\projects\karhutla-watch` dan `C:\karhutla-data`. Jangan taruh apa pun di folder home pengguna.
9. Satu job Spark pada satu waktu (`local[4]`, driver 4g). Jangan naikkan memori tanpa bukti terukur.
10. Tanpa autentikasi dan tanpa streaming sungguhan. Jangan ubah lingkup tanpa persetujuan.
11. Jangan mengarang data, kolom, versi, metrik. Periksa file/perintah nyata. Tandai `TODO(verify)` dan laporkan.
12. Jangan commit kredensial. Gunakan `.env`.

## Produk dan Halaman
Nama produk: **PantauApi**. Tiga halaman: `/` (Peta), `/data` (Data & Pre-processing, termasuk tombol sekunder "Tambah data"), `/analytics` (Analitik). Tidak ada halaman upload khusus (dikonfirmasi dosen). Akuisisi otomatis (NiFi + impor folder) adalah jalur utama; upload manual hanya jalur tambahan yang memakai pipeline yang sama.

## UI
- Ikuti `docs/UI_SPEC.md` dan `docs/DESIGN.md`; token di `frontend/styles/tokens.css` dan konfigurasi Tailwind. Bila ada ekspor desain di `docs/design/`, itu menjadi acuan visual utama.
- Light-first dengan aksen api; bagian gelap "ember" hanya sesuai spesifikasi.
- Animasi minimal (transisi 150-200 ms), tanpa animasi kontinu; hormati `prefers-reduced-motion`.
- Peta tidak pernah memuat lebih dari 20.000 titik; agregasi grid pada zoom rendah.
- Bahasa UI Indonesia, istilah teknis Inggris.

## Stack
Next.js (TypeScript, Tailwind, react-leaflet, ECharts) | FastAPI + Pydantic + SQLAlchemy | PySpark/Spark SQL/MLlib | HDFS | NiFi | DuckDB + Parquet lokal + SQLite.

## Cara Bekerja
- Satu fase pada satu waktu sesuai `docs/TASKS.md`, mulai Fase 0.
- Sebelum menulis fitur: `python scripts\check_env.py`, laporkan hasilnya.
- Akhiri tiap fase dengan: ringkasan perubahan, bukti pengujian (perintah + keluaran), masalah terbuka. Tunggu persetujuan pengguna.
- Centang tugas di `docs/TASKS.md`. Tanyakan dulu untuk hal berisiko.

## Perintah Umum (Windows)
- Cek lingkungan: `python scripts\check_env.py`
- Start/stop HDFS: `scripts\start_hdfs.bat` (CMD Administrator) / `scripts\stop_hdfs.bat`
- Backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev` (port 3000)
- Spark: `spark-submit --master local[4] --driver-memory 4g backend\spark_jobs\<job>.py`
- UI: NiFi http://localhost:8080/nifi | NameNode http://localhost:9870

## Konvensi
- Python: type hints, `ruff`, `pathlib`. TypeScript strict + eslint. API terpusat di `frontend/lib/api.ts`.
- Job Spark idempoten dan melaporkan jumlah baris input/output.
- Endpoint peta wajib bbox dan batas jumlah.
- Atribusi sumber data tampil di UI.
