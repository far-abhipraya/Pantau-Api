# Data Dictionary: KarhutlaWatch

Kamus data ini mendokumentasikan header dan skema aktual dari sampel data yang tersimpan di `data_samples/` untuk digunakan pada pipeline pre-processing, analitik, dan machine learning.

---

## 1. NASA FIRMS VIIRS (`data_samples/firms_viirs_sample.csv`)
Sumber: NASA LANCE FIRMS (Sensor Suomi-NPP / NOAA-20 / NOAA-21 VIIRS 375m).

| Nama Kolom | Tipe Data | Deskripsi | Contoh Nilai |
|---|---|---|---|
| `latitude` | Float (Double) | Garis lintang titik hotspot (WGS84) | `-0.0423` |
| `longitude` | Float (Double) | Garis bujur titik hotspot (WGS84) | `105.8439` |
| `bright_ti4` | Float | Suhu kecerahan I-4 channel (Kelvin) | `331.48` |
| `scan` | Float | Resolusi spasial searah scan (km) | `0.53` |
| `track` | Float | Resolusi spasial searah lintasan (km) | `0.42` |
| `acq_date` | String (YYYY-MM-DD) | Tanggal akuisisi satelit | `2024-10-27` |
| `acq_time` | String (HHMM) | Waktu akuisisi dalam UTC (4 digit) | `0657` |
| `satellite` | String | Identitas satelit (`N`=Suomi-NPP, `1`=NOAA-20, `2`=NOAA-21) | `N` |
| `confidence` | String | Tingkat keyakinan deteksi (`low`, `nominal`, `high`) | `nominal` |
| `version` | String | Versi pemrosesan produk FIRMS | `2.0NRT` |
| `bright_ti5` | Float | Suhu kecerahan I-5 channel (Kelvin) | `293.85` |
| `frp` | Float | Fire Radiative Power (Megawatt) | `4.37` |
| `daynight` | String | Waktu pengamatan (`D`=Day, `N`=Night) | `D` |

---

## 2. NASA FIRMS MODIS (`data_samples/firms_modis_sample.csv`)
Sumber: NASA LANCE FIRMS (Sensor Terra & Aqua MODIS 1km).

| Nama Kolom | Tipe Data | Deskripsi | Contoh Nilai |
|---|---|---|---|
| `latitude` | Float (Double) | Garis lintang titik hotspot (WGS84) | `-2.872` |
| `longitude` | Float (Double) | Garis bujur titik hotspot (WGS84) | `104.120` |
| `brightness` | Float | Suhu kecerahan Channel 21/22 (Kelvin) | `312.4` |
| `scan` | Float | Resolusi spasial searah scan (km) | `1.0` |
| `track` | Float | Resolusi spasial searah lintasan (km) | `1.0` |
| `acq_date` | String (YYYY-MM-DD) | Tanggal akuisisi satelit | `2024-10-27` |
| `acq_time` | String (HHMM) | Waktu akuisisi dalam UTC | `0003` |
| `satellite` | String | Identitas satelit (`T`=Terra, `A`=Aqua) | `T` |
| `confidence` | Integer | Tingkat keyakinan deteksi (0 - 100%) | `45` |
| `version` | String | Versi pemrosesan produk | `6.1NRT` |
| `bright_t31` | Float | Suhu kecerahan Channel 31 (Kelvin) | `294.24` |
| `frp` | Float | Fire Radiative Power (Megawatt) | `3.99` |
| `daynight` | String | Waktu pengamatan (`D`=Day, `N`=Night) | `D` |

---

## 3. Skema Kanonik Normalisasi Hotspot (`clean/hotspot`)
Hasil normalisasi gabungan VIIRS dan MODIS oleh Spark job pre-processing:

| Nama Kolom | Tipe Data | Keterangan Normalisasi |
|---|---|---|
| `latitude` | Double | Koordinat WGS84 |
| `longitude` | Double | Koordinat WGS84 |
| `acq_ts_utc` | Timestamp | Gabungan `acq_date` + `acq_time` zona UTC |
| `acq_ts_wib` | Timestamp | Konversi ke Waktu Indonesia Barat (UTC+7) |
| `year` | Integer | Tahun ekstraksi (partisi Parquet) |
| `month` | Integer | Bulan ekstraksi (partisi Parquet) |
| `day` | Integer | Hari |
| `dayofyear` | Integer | Hari ke-n dalam setahun (1-366) |
| `hour` | Integer | Jam (0-23) WIB |
| `satellite` | String | Nama satelit (`Suomi-NPP`, `NOAA-20`, `Terra`, `Aqua`) |
| `instrument` | String | `VIIRS` atau `MODIS` |
| `confidence_level` | String | `low`, `nominal`, `high` (MODIS: <30=low, 30-80=nominal, >80=high) |
| `brightness` | Double | Suhu kecerahan utama (`bright_ti4` VIIRS / `brightness` MODIS) |
| `brightness_2` | Double | Suhu kecerahan sekunder (`bright_ti5` VIIRS / `bright_t31` MODIS) |
| `frp` | Double | Fire Radiative Power |
| `daynight` | String | `D` atau `N` |
| `grid_id` | String | Kode grid 0,25 derajat (misal: `GRID_m025_10125`) |
| `province` | String | Nama provinsi hasil lookup spasial |
| `frp_norm` | Double | Normalisasi Min-Max FRP |
| `brightness_norm`| Double | Normalisasi Min-Max suhu kecerahan |
| `source_file` | String | Nama file asal |

---

## 4. Cuaca ERA5 (`data_samples/era5_sample.csv`)
Sumber: ECMWF ERA5 Reanalysis via Open-Meteo Historical Archive.

| Nama Kolom | Tipe Data | Satuan | Deskripsi |
|---|---|---|---|
| `latitude` | Double | derajat | Lintang grid |
| `longitude` | Double | derajat | Bujur grid |
| `date` | Date (YYYY-MM-DD) | - | Tanggal pengamatan |
| `temp_max` | Float | Celsius | Suhu udara maksimum 2 meter |
| `temp_min` | Float | Celsius | Suhu udara minimum 2 meter |
| `temp_mean` | Float | Celsius | Suhu udara rata-rata 2 meter |
| `precipitation`| Float | mm | Akumulasi curah hujan harian |
| `wind_speed_max`| Float | km/h | Kecepatan angin maksimum 10 meter |

---

## 5. Validasi Referensi SiPongi+ (`data_samples/sipongi_reference_sample.csv`)
Sumber: SiPongi+ Kementerian Kehutanan (Kemenhut) & BNPB.

| Nama Kolom | Tipe Data | Deskripsi |
|---|---|---|
| `date` | Date (YYYY-MM-DD) | Periode rekapitulasi |
| `province` | String | Nama provinsi |
| `source` | String | Sumber data (`SIPONGI KEMENHUT` / `BNPB`) |
| `hotspot_count` | Integer | Jumlah hotspot terverifikasi |
| `burned_area_ha` | Float | Estimasi luas kebakaran hutan/lahan (hektar) |
