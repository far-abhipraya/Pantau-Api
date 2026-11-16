# ANALYTICS_SPEC: Halaman Analitik PantauApi (v1.2.1)

Dokumen ini adalah sumber kebenaran untuk halaman `/analytics`. Bila bertentangan dengan FR-A1..A8 di PRD v1.2 atau Bagian 7 di `UI_SPEC.md`, dokumen ini yang berlaku (lihat `docs/PATCH_v1.2.1.md`).

## 1. Tujuan
Memenuhi kriteria tugas: menganalisis data untuk mendapatkan insight baru, baik **memprediksi kejadian akan datang** maupun **Business Intelligence** (faktor di masa lalu yang memengaruhi kejadian hari ini).

Empat lapis analitik:

| Lapis | Pertanyaan | Komponen |
|---|---|---|
| Deskriptif | Apa yang terjadi? | KPI, tren, ranking wilayah, pola musiman |
| Diagnostik | Mengapa terjadi? Faktor apa di masa lalu yang berpengaruh? | **Faktor Pengaruh** (lag, dosis-respons, anomali, penjelas wilayah, pembanding tahun) |
| Prediktif | Apa yang akan terjadi? | Peta risiko 7 hari, performa model |
| Preskriptif ringan | Apa yang perlu diperhatikan? | **Insight Utama** (kartu insight otomatis) |

## 2. Urutan Halaman
1. Hero KPI (ember gelap)
2. **Insight Utama** (baru): 5-7 kartu insight hasil perhitungan
3. Bilah filter lengket + navigasi section: Ringkasan | Wilayah | Musiman | **Faktor Pengaruh** | Prediksi ML | Validasi
4. Section Ringkasan, Wilayah, Musiman (tetap seperti v1.2; Cuaca digabung ke Faktor Pengaruh)
5. **Faktor Pengaruh** (baru, menggantikan section Cuaca)
6. Prediksi ML
7. Validasi
8. Catatan metodologi dan footer

## 3. Insight Utama

### 3.1 Prinsip
- Insight dihasilkan oleh aturan (rule-based) dari angka yang benar-benar dihitung. **Dilarang** menulis angka atau klaim yang tidak berasal dari tabel hasil perhitungan. Tidak memakai LLM untuk membuat angka.
- Bahasa: asosiasi, bukan sebab-akibat. Gunakan "berkaitan dengan", "diikuti oleh", "lebih tinggi dari". Dilarang "menyebabkan".
- Setiap kartu menyimpan `evidence` (nilai, n sampel, jendela waktu, tanggal hitung) yang dapat dibuka lewat "Lihat bukti".
- Setiap kartu punya tingkat keyakinan (Tinggi/Sedang/Rendah) berdasarkan ukuran sampel dan kekuatan hubungan. Ambang awal (konfigurable di `insight_config.yaml`, perlu dikalibrasi): Tinggi bila n >= 500 dan |r| >= 0,40; Sedang bila n >= 100 dan |r| >= 0,25; selain itu Rendah. Kartu keyakinan Rendah tetap tampil dengan badge dan teks hati-hati, atau disembunyikan bila n < 30.
- Kartu mengikuti filter global (rentang tanggal, provinsi, sensor, confidence).

### 3.2 Katalog Insight (template Indonesia; `{...}` diisi dari hasil perhitungan)

| ID | Tipe | Template kalimat | Dihitung dari |
|---|---|---|---|
| I1 | Tren | "Hotspot {wilayah} {naik/turun} {pct}% dalam 7 hari terakhir dibanding 7 hari sebelumnya ({a} vs {b})." | `agg_daily_province` |
| I2 | Wilayah | "{provinsi_1}, {provinsi_2}, dan {provinsi_3} menyumbang {share}% hotspot pada periode ini." | ranking provinsi |
| I3 | Kekeringan | "Wilayah dengan hotspot tertinggi mengalami {n} hari tanpa hujan berturut-turut (median); curah hujan 30 hari terakhir {x}% di {bawah/atas} normal." | `weather_anomaly`, fitur hari kering |
| I4 | Faktor | "Curah hujan {lag_min}-{lag_max} minggu sebelumnya paling berkaitan dengan jumlah hotspot (korelasi {r}, n={n})." | `lag_correlation` |
| I5 | Faktor | "Peluang hotspot dalam 7 hari ke depan naik dari {p_low}% menjadi {p_high}% ketika hari tanpa hujan berturut-turut melewati {ambang} hari." | `dose_response` |
| I6 | Musiman | "Secara historis, puncak hotspot terjadi pada bulan {bulan_puncak}; saat ini {sebelum/di dalam/setelah} periode puncak." | agregasi bulanan |
| I7 | Prediksi | "{n_grid} grid diperkirakan berisiko Tinggi atau Sangat tinggi dalam 7 hari ke depan, terutama di {provinsi_teratas}. Model: AUC-PR {x} vs baseline {y}." | `risk_prediction`, `model_metrics` |
| I8 | Validasi | "Tren bulanan hotspot pipeline berkorelasi {r} dengan rekap {sumber}." | `/validation/compare` |

Aturan pemilihan: urutkan menurut skor relevansi (|perubahan|, kekuatan hubungan, keyakinan), tampilkan 5-7 kartu, minimal satu per lapis (tren, faktor, prediksi). Bila data tidak cukup untuk suatu insight, lewati; jangan menampilkan placeholder kosong.

### 3.3 Komponen UI Kartu Insight
- Kartu putih, radius 12, strip aksen 4 px di kiri menurut tipe: Tren = oranye, Wilayah = merah tua, Kekeringan/Faktor = teal, Musiman = amber, Prediksi = oranye gelap dengan badge "Prediksi", Validasi = abu-abu.
- Isi: ikon kecil, judul pendek (maks 5 kata), **angka kunci** besar (misalnya "+42%"), kalimat insight (maks 2 baris), badge keyakinan, tautan "Lihat detail" (scroll ke section terkait) dan ikon info untuk "Lihat bukti" (popover: nilai, n, jendela, tanggal hitung).
- **Kartu sorotan**: satu kartu terpenting (skor tertinggi) tampil lebih lebar dengan latar ember gelap dan teks terang. Sisanya putih. Batas penggunaan gelap tetap sesuai UI_SPEC.
- Susunan: grid 3 kolom di desktop (kartu sorotan menempati 2 kolom), 2 kolom di tablet, 1 kolom kecil. Label di atas grid: "Insight utama · dihitung dari data {rentang}" + waktu hitung.
- State: loading (skeleton), kosong ("Belum cukup data untuk membuat insight pada filter ini"), error.

## 4. Section Faktor Pengaruh

Subjudul: "Faktor di masa lalu yang berkaitan dengan kejadian hari ini". Catatan metodologi singkat selalu tampak di kepala section: "Hubungan yang ditampilkan bersifat asosiasi, bukan bukti sebab-akibat."

Selektor wilayah di kepala section: Nasional | Pulau (Sumatera, Kalimantan, dst.) | Provinsi. Berlaku untuk FP1-FP4.

### FP1: Korelasi dengan Jeda Waktu (Lag)
- Grafik garis: sumbu x = jeda 0-8 minggu, sumbu y = korelasi Spearman antara jumlah hotspot mingguan di minggu t dan variabel cuaca di minggu t-lag. Seri: curah hujan (teal), suhu, kelembapan (abu-abu/amber). Titik jeda terbaik diberi penanda dan label.
- Kartu kecil di sampingnya: "Jeda paling berpengaruh", nilai korelasi, n minggu, keyakinan.
- Perhitungan: seri mingguan per wilayah dari `clean/hotspot` dan cuaca grid-hari yang diagregasi ke wilayah (rata-rata/sum menurut variabel). Wilayah dengan < 100 minggu data: tampilkan peringatan.

### FP2: Kurva Dosis-Respons
- Dua grafik batang/garis: peluang ada hotspot dalam 7 hari ke depan (sumbu y) menurut (a) kelompok hari tanpa hujan berturut-turut: 0, 1-3, 4-7, 8-14, 15-21, 22-30, >30; (b) kelompok curah hujan kumulatif 30 hari (kuantil). Setiap batang menampilkan n sampel (teks kecil/tooltip). Garis acuan: peluang rata-rata keseluruhan.
- Sumber: `features/grid_daily` (fitur dan label), diagregasi menurut wilayah terpilih.

### FP3: Anomali Kondisi Saat Ini
- Kartu per variabel (Hujan 30 hari, Suhu 7 hari, Kelembapan 7 hari, Hari tanpa hujan berturut-turut): nilai saat ini, normal historis (rata-rata untuk jendela kalender yang sama, minimal 5 tahun, tahun berjalan dikecualikan), z-score dan persentil, mini bar posisi di distribusi, badge: "Jauh lebih kering dari normal", "Lebih kering", "Normal", "Lebih basah".
- Sumber: `weather_anomaly`.

### FP4: Penjelas Wilayah ("Mengapa risikonya tinggi?")
- Pilih provinsi atau grid (dari peta kecil atau dropdown). Tampilkan risiko saat ini (skor dan kategori) dan daftar 5 faktor pendorong teratas dalam bar horizontal, tiap baris: nama fitur berbahasa Indonesia (misalnya "Hari tanpa hujan berturut-turut"), nilai saat ini, persentil terhadap riwayat bulan yang sama, arah (mendorong naik/menekan risiko).
- Skor dorongan (heuristik, bukan SHAP): `push = importance_norm * arah * (persentil - 50) / 50`, dengan `arah` = tanda korelasi fitur dengan label pada data latih. Beri label jelas "Perkiraan faktor pendorong (heuristik berbasis feature importance)".
- Sumber: `region_drivers`.

### FP5: Pembanding Antar Tahun
- Grafik garis kumulatif hotspot menurut hari dalam tahun untuk tiap tahun (tahun terpilih disorot oranye-merah, rata-rata historis abu-abu putus-putus), dengan strip kecil anomali hujan tahunan di bawahnya (teal). Tujuan: terlihat bahwa tahun lebih kering cenderung memiliki hotspot lebih banyak.
- Opsional (fase lanjut): lapisan indeks iklim (ONI/IOD) bila datanya dibawa masuk; belum ada di PRD, jangan ditambahkan tanpa persetujuan.

### FP6: Faktor Terpenting Model
- Bar feature importance (top 8) dengan terjemahan nama fitur. Tautan ke section Prediksi ML untuk detail.

### Catatan Metodologi (tampil di bawah section)
Asosiasi bukan sebab-akibat; hotspot adalah indikasi anomali suhu dari satelit, bukan kepastian kebakaran; awan dapat menutupi deteksi; data cuaca beresolusi kasar; hasil sensitif terhadap pemilihan wilayah dan periode.

## 5. Section Prediksi ML (perubahan kecil)
Tambahkan di bawah panel performa: kartu "Cara membaca peta risiko" (3 baris), tombol "Lihat faktor pendorong wilayah ini" yang membuka FP4 dengan wilayah terpilih, dan tautan ke Insight I7.

## 6. Data dan Job

Job Spark baru `backend/spark_jobs/insights.py`, dijalankan setelah `features.py`, `train.py`/`predict.py`, dan `aggregate.py` oleh `/analytics/refresh`. Seluruh keluaran kecil (ribuan baris) ditulis ke HDFS `/karhutla/analytics/insights/` dan diekspor ke serving layer.

| Tabel (Parquet) | Kolom utama |
|---|---|
| `lag_correlation` | region_level, region_id, variable, lag_weeks, spearman_r, n_weeks, computed_at |
| `dose_response` | region_level, region_id, variable, bin_label, bin_order, n, p_hotspot_7d |
| `weather_anomaly` | region_level, region_id, variable, window_label, value, baseline_mean, baseline_std, zscore, percentile, n_years, computed_at |
| `region_drivers` | region_level, region_id, feature, feature_label_id, value, percentile, direction, importance_norm, push_score, as_of_date |
| `year_compare` | region_id, year, dayofyear, cum_hotspot, rain_anomaly |
| `insight_cards` | id, type, score, title, key_figure, sentence, confidence, evidence_json, region_id, period_start, period_end, computed_at |

Konfigurasi: `backend/spark_jobs/insight_config.yaml` (ambang keyakinan, ambang jumlah minimum, pemilihan variabel, bin hari kering).

## 7. API Tambahan (`/api/analytics`)

| Metode | Endpoint | Fungsi |
|---|---|---|
| GET | `/insights` | Daftar kartu insight (parameter filter global; maks 7) |
| GET | `/drivers/lag` | Korelasi lag (`region_level`, `region_id`, `variables`) |
| GET | `/drivers/dose-response` | Kurva dosis-respons (`variable`, region) |
| GET | `/drivers/anomaly` | Anomali kondisi saat ini (region) |
| GET | `/drivers/region` | Penjelas wilayah (`region_id`) |
| GET | `/drivers/year-compare` | Pembanding antar tahun (region, tahun) |
| GET | `/drivers/importance` | Top feature importance berlabel Indonesia |

Semua respons memuat `computed_at` dan `n` sampel.

## 8. Kriteria Penerimaan Tambahan
- AC-10: Minimal 5 kartu insight tampil, semuanya dihitung dari data (bukti dapat dibuka), mencakup tren, faktor, dan prediksi.
- AC-11: FP1 (lag) dan FP2 (dosis-respons) tampil untuk minimal tingkat Nasional dan Provinsi, dengan n sampel terlihat.
- AC-12: FP3 (anomali) dan FP4 (penjelas wilayah) berfungsi untuk wilayah terpilih.
- AC-13: Semua kalimat insight memakai bahasa asosiasi; catatan metodologi tampil.
- AC-14: Halaman Analitik memuat <= 5 detik karena semua tabel insight berasal dari serving layer.

## 9. Spesifikasi UI Ringkas (untuk Stitch dan implementasi)

**Insight Utama**: di bawah hero KPI, judul "Insight utama" + keterangan periode dan waktu hitung. Grid kartu insight (lihat 3.3). Satu kartu sorotan ember gelap.

**Faktor Pengaruh** layout (desktop):
- Baris 1: header section + selektor wilayah (segmented Nasional | Pulau | Provinsi + dropdown) + catatan metodologi (ikon info).
- Baris 2: FP1 grafik lag (2/3 lebar) + kartu "Jeda paling berpengaruh" (1/3).
- Baris 3: FP2 dua grafik dosis-respons berdampingan.
- Baris 4: FP3 empat kartu anomali horizontal.
- Baris 5: FP4 penjelas wilayah (kiri: pemilih wilayah + skor risiko; kanan: bar faktor pendorong) dan FP6 feature importance.
- Baris 6: FP5 pembanding antar tahun lebar penuh.
Tablet: satu kolom; kartu anomali 2x2.

**Warna**: hotspot/risiko = oranye-merah; cuaca = teal; pembanding = abu-abu; prediksi = garis putus-putus + badge "Prediksi". Tanpa animasi masuk grafik.

**Contoh copy (contoh tampilan saja, bukan data nyata)**: judul "Faktor di masa lalu yang berkaitan dengan kejadian hari ini"; badge "Keyakinan: Sedang"; label "Hari tanpa hujan berturut-turut".
