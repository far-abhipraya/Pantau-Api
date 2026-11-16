# Aturan: Akuisisi, Adapter Format, dan Karantina

- Tiga jalur masuk (NiFi, impor folder `C:\karhutla-data\inbox`, tombol "Tambah data") wajib bermuara ke `/karhutla/raw/...` dan melewati pipeline yang sama (adapter -> validasi -> dedup -> clean).
- Satu adapter per sumber di `spark_jobs/adapters/` (viirs_csv, modis_csv, firms_archive, firms_api, chirps, era5). Setiap adapter memetakan ke skema kanonik PRD 11.1.
- Deteksi format berdasarkan header/skema (fungsi `detect_format` dipakai bersama oleh endpoint `/datasets/detect` dan job Spark). Jangan menebak dari nama file saja.
- Format tak dikenal atau baris gagal parse -> `/karhutla/quarantine/` dengan alasan; jangan dibuang diam-diam. Catat ke tabel `quarantine` dan `ingest_log`.
- Dedup lintas jalur memakai kunci (latitude, longitude, acq_date, acq_time, satellite); laporan job mencantumkan jumlah duplikat.
- Impor folder: pindahkan file ke `inbox\processed` setelah sukses atau `inbox\failed` bila gagal. Jangan hapus file asli.
- Kompaksi harian file kecil NRT oleh Spark.
- Tulis tes unit dengan sampel kecil dari `data_samples/` untuk tiap adapter.
