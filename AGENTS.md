# AGENTS.md: KarhutlaWatch

Platform big data pemantauan dan prediksi risiko karhutla Indonesia (tugas akhir Big Data & Analitik). Rujukan utama: `docs/PRD.md` (v1.1). Fakta lingkungan: `docs/ENVIRONMENT.md`. Daftar tugas: `docs/TASKS.md`. Sumber data: `docs/DATA_SOURCES.md`.

Aturan terperinci ada di `.agents/rules/`. Ringkasan di bawah ini selalu berlaku.

## Aturan Mutlak (jangan dilanggar)
1. Hadoop 3.5.0, Spark 4.2.0, NiFi 1.28.1, Java 17 dan Python sudah terpasang NATIVE di Windows (tanpa Docker/WSL/VM). Jangan instal ulang, pindahkan, atau tambahkan Docker/WSL/VM.
2. Jangan pernah menjalankan `hdfs namenode -format`.
3. Jangan mengubah atau menghapus path HDFS lama: `/hr-data`, `/warehouse`, `/user/alfarel`, `/test`, `/testupload`. Semua data proyek di bawah `/karhutla/`.
4. Jangan mengubah `core-site.xml`, `hdfs-site.xml`, `yarn-site.xml`, `mapred-site.xml`, `hadoop-env.cmd`, atau alur NiFi lama tanpa persetujuan eksplisit pengguna.
5. Setiap proses yang memanggil Hadoop/Spark harus memakai env `HADOOP_USER_NAME=hadoop`.
6. Jangan memakai `hdfs dfs -stat` dengan format `%`. Pakai `-ls`, `-du`, `-count`.
7. Upload ke HDFS lewat staging lokal lalu `hdfs dfs -put`. Jangan mengandalkan WebHDFS atau Web UI upload (redirect ke hostname DataNode gagal).
8. Kode, data, dan temp berada di path TANPA spasi: `C:\projects\karhutla-watch` dan `C:\karhutla-data`. Username Windows mengandung spasi, jangan taruh apa pun di folder home.
9. Satu job Spark pada satu waktu. Spark `local[4]`, driver 4g. Jangan menaikkan memori tanpa bukti terukur.
10. Tanpa autentikasi, tanpa Kafka/streaming sungguhan. Jangan ubah lingkup tanpa persetujuan.
11. Jangan karang data, nama kolom, versi, atau metrik. Periksa file/perintah nyata. Tandai yang tidak terverifikasi dengan `TODO(verify)` dan laporkan.
12. Jangan menulis kredensial ke repo. Gunakan `.env` (lihat `.env.example`).

## Stack
Next.js (TypeScript, Tailwind, react-leaflet, ECharts) | FastAPI + Pydantic + SQLAlchemy | PySpark/Spark SQL/MLlib | HDFS | NiFi | DuckDB + Parquet lokal + SQLite (serving/metadata).

## Cara Bekerja
- Kerjakan satu fase pada satu waktu sesuai `docs/TASKS.md`, mulai Fase 0. Jangan lompat fase.
- Sebelum menulis fitur: jalankan `python scripts/check_env.py` dan laporkan hasilnya.
- Akhiri setiap fase dengan: ringkasan perubahan, bukti pengujian (perintah dan keluaran), masalah terbuka. Tunggu persetujuan pengguna sebelum fase berikutnya.
- Centang tugas yang selesai di `docs/TASKS.md`.
- Bila ragu pada hal yang berisiko (hapus data, ubah konfigurasi inti), tanyakan dulu.

## Perintah Umum (Windows, CMD/PowerShell)
- Cek lingkungan: `python scripts\check_env.py`
- Start HDFS: `scripts\start_hdfs.bat` (CMD Administrator). Stop: `scripts\stop_hdfs.bat`
- Backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev` (port 3000)
- Job Spark: `spark-submit --master local[4] --driver-memory 4g backend\spark_jobs\<job>.py`
- NiFi UI: http://localhost:8080/nifi | NameNode UI: http://localhost:9870

## Konvensi
- Python: type hints, `ruff`, `pathlib` (hindari concat string untuk path), logging terstruktur.
- TypeScript: strict, `eslint`, komponen kecil, panggilan API terpusat di `frontend/lib/api.ts`.
- Job Spark idempoten (overwrite per partisi) dan melaporkan jumlah baris input/output.
- Endpoint titik/peta wajib punya batas jumlah dan filter bbox.
- Atribusi sumber data wajib tampil di UI (NASA FIRMS, Copernicus/ECMWF, CHIRPS, SIPONGI KEMENHUT, BNPB).
