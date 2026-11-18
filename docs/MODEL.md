# Model Risiko 7 Hari (Fase 6)

Dokumen ini mencatat implementasi nyata model risiko karhutla PantauApi. Semua
angka berasal dari job Spark pada data `clean/hotspot` yang tersedia; tidak ada
metrik yang dikarang.

## Tujuan dan unit

- Unit prediksi: grid 0,25 derajat x tanggal `t`.
- Label `y=1`: ada hotspot confidence nominal/tinggi pada `t+1..t+7`.
  Hotspot `low` tidak dipakai (konsisten dengan agregat confidence tinggi).
- Keluaran: `risk_score` 0–1 dan kategori `rendah <0,25`, `sedang <0,5`,
  `tinggi <0,75`, `sangat tinggi >=0,75`, plus `model_version`,
  `predicted_at`, `horizon_days=7`, `target_date`.

## Fitur (`backend/spark_jobs/features.py`)

| Kelompok | Fitur |
|---|---|
| Hotspot | jumlah 1/3/7/14/30 hari, rata-rata FRP 7 hari, hari sejak hotspot terakhir, hotspot 8 sel tetangga 7 hari |
| Cuaca | hujan 7/14/30 hari, hari kering berturut-turut, suhu rata-rata 7 hari, angin rata-rata 7 hari, indikator `weather_missing` |
| Waktu/lokasi | bulan, sin/cos day-of-year, lintang, bujur, indeks provinsi |

Panel dibangun padat untuk 3.336 grid yang pernah memiliki hotspot
(2019-01-01 s/d 2026-11-16): **9.597.672 baris**, **9.574.320 berlabel**;
7 hari terakhir sengaja berlabel null karena horizon belum lengkap.

### Cakupan cuaca

Sumber: `raw/weather/weather_era5_daily_2022_2024.csv` (10 stasiun
Sumatera/Kalimantan, 2022–2024). Stasiun dipetakan ke provinsi terdekat;
di luar cakupan/tanggal, fitur cuaca diimputasi `-1` dan `weather_missing=1`.
Spark 4.2 menolak NaN di `VectorAssembler`, sehingga imputasi eksplisit ini
menggantikan NaN. Keterbatasan ini juga ditampilkan di UI.

## Pelatihan (`backend/spark_jobs/train.py`)

- Split berbasis waktu, tanpa split acak: latih <= 2022-12-31, validasi 2023,
  uji >= 2024-01-01.
- `RandomForestClassifier` (baseline model) dan `GBTClassifier` (pembanding),
  `weightCol` menyeimbangkan kelas positif (rasio negatif/positif, dibatasi 50).
- Metrik uji: AUC-ROC, AUC-PR, precision, recall, F1 (ambang 0,5), confusion
  matrix, feature importance.
- Pembanding: baseline persistensi (ada hotspot 7 hari terakhir → prediksi ada).
- Metrik + manifest disimpan di `serving/model_metrics.json` dan
  `serving/model_manifest.json`; model Spark ML di HDFS `/karhutla/models/<versi>`.

## Prediksi (`backend/spark_jobs/predict.py`)

- Memuat model terakhir dari manifest, memakai fitur tanggal terakhir
  (2026-11-16), dan menulis `serving/risk_prediction` (Parquet lokal).
- Hanya grid yang pernah memiliki hotspot historis yang diprediksi; grid tanpa
  histori tidak diklaim aman.
- Ringkasan sebaran kategori di `serving/risk_summary.json`.

## Orkestrasi

`POST /api/analytics/model/refresh` mengantrekan `model_refresh.py` yang
menjalankan fitur → latih → prediksi dalam satu antrean Spark tunggal.
Setiap langkah dapat juga dijalankan manual:

```powershell
spark-submit --master local[4] --driver-memory 4g backend\spark_jobs\features.py
spark-submit --master local[4] --driver-memory 4g backend\spark_jobs\train.py
spark-submit --master local[4] --driver-memory 4g backend\spark_jobs\predict.py
```

## Keterbatasan

- Estimasi statistik, bukan kepastian kebakaran.
- Fitur cuaca hanya 10 stasiun dan 2022–2024; provinsi lain memakai indikator
  cuaca hilang.
- Grid belum pernah aktif tidak diprediksi.
- Metrik uji mencampur periode dengan dan tanpa cakupan cuaca; lihat
  `weather_features_available` pada metrik.
