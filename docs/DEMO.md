# Skrip Demo PantauApi

Urutan klik dan narasi untuk demonstrasi sistem kepada dosen/penilai.

## Persiapan

Pastikan layanan berikut sudah berjalan:
- HDFS (NameNode: `http://localhost:9870`)
- Backend FastAPI: `http://localhost:8000`
- Frontend Next.js: `http://localhost:3000`

Jika belum, jalankan:
```powershell
# Backend (di terminal terpisah)
cd C:\projects\karhutla-watch\backend
$env:HADOOP_USER_NAME="hadoop"
python -m uvicorn app.main:app --port 8000 --reload

# Frontend (di terminal terpisah)
cd C:\projects\karhutla-watch\frontend
npm run dev
```

---

## Halaman 1: Peta (`/`) — ~2 menit

**Langkah 1:** Buka `http://localhost:3000/`  
**Narasi:** "Halaman utama menampilkan peta interaktif hotspot karhutla Indonesia dengan data NASA FIRMS."

**Langkah 2:** Klik tombol "Filter" di kiri atas  
**Narasi:** "Bilah filter memungkinkan pemilihan jendela waktu (24 jam/48 jam/7 hari), sensor (Semua/VIIRS/MODIS), dan confidence minimum (Semua/Nominal+/High)."

**Langkah 3:** Ganti basemap dari "Terang" ke "Satelit", lalu kembali ke "Terang"  
**Narasi:** "Basemap tersedia dalam dua mode: Terang (OpenStreetMap) dan Satelit (Esri World Imagery)."

**Langkah 4:** Aktifkan lapisan "Densitas grid" dan "Prediksi risiko 7 hari (Fase 6)"  
**Narasi:** "Lapisan densitas grid menunjukkan agregasi hotspot per sel grid. Lapisan prediksi risiko 7 hari menunjukkan estimasi risiko dari model ML (Random Forest, AUC-ROC 0,886)."

**Langkah 5:** Klik salah satu titik hotspot di peta  
**Narasi:** "Popup menampilkan detail hotspot: waktu, koordinat, sensor, confidence, FRP, dan provinsi."

**Langkah 6:** Perhatikan KPI di kanan atas: "Hotspot (24 jam): 717", "Provinsi tertinggi: Sulawesi Tenggara (89 hotspot)", "Confidence tinggi: 20 (3% dari total)"  
**Narasi:** "KPI menampilkan jumlah hotspot 24 jam terakhir, provinsi dengan hotspot terbanyak, dan jumlah confidence tinggi."

**Akibat yang diharapkan:** Peta menampilkan titik hotspot tanpa "API KEY REQUIRED"; lapisan risiko menampilkan titik berwarna sesuai kategori (rendah/sedang/tinggi/sangat tinggi).

---

## Halaman 2: Data & Pre-processing (`/data`) — ~2 menit

**Langkah 7:** Klik "Data" di navigasi atas  
**Narasi:** "Halaman Data menampilkan strip status, tab sumber data, dan pre-processing."

**Langkah 8:** Perhatikan strip status di atas  
**Narasi:** "Strip status menunjukkan total baris data mentah di HDFS (>= 1.000.000 baris), ukuran data, ingest NiFi terakhir, status Spark, dan jumlah file karantina."

**Langkah 9:** Klik tab "Sumber Data"  
**Narasi:** "Menampilkan kartu per sumber (FIRMS VIIRS, FIRMS MODIS, CHIRPS, ERA5) dengan status otomatis, pembaruan terakhir, jumlah baris, dan path HDFS."

**Langkah 10:** Klik tombol sekunder "Tambah data"  
**Narasi:** "Modal deteksi format muncul. Pilih file CSV/JSON, backend mendeteksi format otomatis, lalu proses. File melalui staging → HDFS → pipeline yang sama dengan jalur otomatis (AC-8)."

**Langkah 11:** Klik tab "Pre-processing"  
**Narasi:** "Menampilkan profiling, stepper pipeline, dan laporan sebelum/sesudah. Langkah Encoding dan Integrasi cuaca ditandai menunggu Fase 6."

**Langkah 12:** Klik tab "Riwayat Job"  
**Narasi:** "Tabel pekerjaan Spark dengan status (queued/running/COMPLETED/FAILED), durasi, dan tombol untuk melihat log/laporan."

**Akibat yang diharapkan:** Semua tab berfungsi; strip status menunjukkan indikator ">= 1.000.000 baris"; tombol "Tambah data" memakai pipeline yang sama dengan otomatis.

---

## Halaman 3: Analitik (`/analytics`) — ~3 menit

**Langkah 13:** Klik "Analitik" di navigasi atas  
**Narasi:** "Halaman Analitik menampilkan dashboard statistik: hero KPI, insight otomatis, dan berbagai visualisasi."

**Langkah 14:** Perhatikan Hero KPI di atas  
**Narasi:** "KPI nasional: hotspot hari ini, kemarin, 7 hari, 30 hari, provinsi tertinggi, dan rata-rata FRP, dengan delta terhadap periode sebelumnya."

**Langkah 15:** Perhatikan Insight Cards  
**Narasi:** "Insight otomatis (rule-based): tren 7 hari, konsentrasi wilayah, puncak musiman. Setiap kartu memiliki bukti angka yang dapat diperluas."

**Langkah 16:** Ganti filter rentang waktu (30/90/365 hari/Semua) dan provinsi  
**Narasi:** "Bilah filter lengket memungkinkan pemilihan rentang waktu, provinsi, dan confidence. Granularitas grafik berubah otomatis (hari/minggu/bulan)."

**Langkah 17:** Lihat section "Ringkasan" (tren harian + kumulatif tahunan)  
**Narasi:** "Grafik garis tren hotspot dan grafik kumulatif per tahun untuk perbandingan tahun ke tahun (FP5)."

**Langkah 18:** Lihat section "Wilayah" (ranking provinsi, choropleth, top grid)  
**Narasi:** "Ranking provinsi sebagai diagram batang, choropleth peta provinsi, dan 10 grid dengan hotspot terbanyak."

**Langkah 19:** Lihat section "Musiman" (heatmap bulan x tahun / bulan x provinsi)  
**Narasi:** "Heatmap menunjukkan pola musiman hotspot per bulan dan tahun. Terdapat 2 mode heatmap."

**Langkah 20:** Lihat section "Prediksi Risiko 7 Hari"  
**Narasi:** "Panel performa model: AUC-ROC 0,886, AUC-PR 0,686, precision 0,430, recall 0,811, F1 0,562. Dibandingkan dengan baseline persistensi (0,752 / 0,501). Feature importance ditampilkan: hari sejak hotspot terakhir (30,5%) adalah fitur terpenting. Tabel 10 grid risiko tertinggi ditampilkan dengan kategori risiko."

**Langkah 21:** Klik tombol "Perbarui prediksi"  
**Narasi:** "Mengantrekan job fitur → latih → prediksi. Hasil akan tersedia setelah job Spark selesai."

**Langkah 22:** Lihat section "Validasi terhadap rekap eksternal"  
**Narasi:** "Unggah CSV rekap SiPongi+ atau BNPB (kolom: date, province, hotspot_count). Sistem akan menampilkan korelasi, selisih relatif, RMSE, dan grafik garis ganda pipeline vs referensi."

**Langkah 23:** Lihat section "Cuaca dan hotspot"  
**Narasi:** "Status data cuaca ditampilkan. Data ERA5 mencakup 10 stasiun Sumatera/Kalimantan (2022–2024). Grafik korelasi akan muncul setelah data cuaca lengkap."

**Akibat yang diharapkan:** Tiga halaman berfungsi end-to-end; semua grafik memiliki state loading/kosong/error; estimasi risiko diformulasikan sebagai "estimasi statistik, bukan kepastian kebakaran".

---

## Verifikasi Terakhir

Sebelum demo, pastikan:
- [ ] Backend API responsif (`GET /api/health` → 200)
- [ ] Frontend muat tanpa error konsol
- [ ] Peta menampilkan titik hotspot (tidak ada "API KEY REQUIRED")
- [ ] Analitik memuat semua section (<= 5 detik)
- [ ] Model risiko tersedia (metrik ditampilkan)
- [ ] Semua tes backend lulus (`python -m pytest backend\tests -q`)

---

## Catatan Keterbatasan

- Estimasi risiko ML adalah statistik, bukan kepastian kebakaran.
- Data cuaca ERA5 hanya mencakup 10 stasiun Sumatera/Kalimantan (2022–2024).
- NiFi belum dijalankan (port 8080); fallback endpoint `/api/ingest/firms-nrt` tersedia.
- Grid yang belum pernah memiliki hotspot historis tidak diprediksi.
