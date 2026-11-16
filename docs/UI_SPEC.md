# UI_SPEC: PantauApi

Spesifikasi UI untuk dipakai sebagai dasar desain (Google Stitch/Figma) dan implementasi (Next.js + Tailwind). Pelengkap: `docs/DESIGN.md` (token dan aturan visual) dan `docs/STITCH_PROMPTS.md`.

## 1. Prinsip Desain
1. **Light-first.** Latar terang hangat, teks gelap, kartu putih. Aksen api (oranye gelap ke merah) dipakai untuk data, aksi utama, dan sorotan.
2. **Api sebagai bahasa data.** Warna oranye-merah selalu berarti hotspot/risiko. Warna non-api (teal) untuk cuaca/hujan, abu-abu untuk netral. Jangan memakai warna api untuk dekorasi biasa.
3. **Bagian gelap terbatas.** Panel gelap berwarna "ember" (merah-coklat sangat gelap) hanya untuk: KPI hero di Analitik, header section Prediksi ML, tooltip/popup peta ringkas, dan footer. Sisanya terang.
4. **Peta adalah pintu masuk.** Halaman pertama langsung peta penuh dengan panel melayang.
5. **Ringan.** Tanpa animasi kontinu. Transisi 150-200 ms untuk hover, buka/tutup panel, dan pergantian tab. Blur/transparansi hanya pada top bar. Hormati `prefers-reduced-motion`.
6. **Jujur soal prediksi.** Lapisan dan kartu prediksi selalu berlabel "Estimasi risiko 7 hari" dan visual dibedakan dari data historis (garis putus-putus, badge "Prediksi").
7. **Aksesibel.** Kontras tinggi, skala risiko tidak hanya bergantung warna, fokus keyboard jelas.

## 2. Referensi Pola (bukan untuk disalin)
Pola yang umum pada peta dan dasbor kebakaran: peta penuh dengan panel layer/filter melayang, legenda kecil di sudut, popup titik, kartu KPI ringkas, tren waktu di bawah/samping, dan badge waktu pembaruan data. NASA FIRMS Fire Map adalah acuan fungsional (hotspot MODIS/VIIRS, filter waktu). Gunakan hanya sebagai inspirasi fungsi; tata letak dan visual PantauApi dibuat sendiri.

## 3. Struktur Informasi

| Rute | Nama menu | Tujuan |
|---|---|---|
| `/` | Peta | Melihat hotspot terkini dan prediksi risiko secara spasial |
| `/data` | Data & Pre-processing | Memantau akuisisi otomatis, menjalankan pre-processing, melihat riwayat job |
| `/analytics` | Analitik | Memahami tren, wilayah, musim, cuaca, performa model, validasi |

## 4. Komponen Global

### 4.1 Top Bar Melayang
- Bentuk pil/kapsul, margin 12 px dari tepi atas, lebar maksimum 1120 px di tengah (desktop), tinggi 52-56 px, sudut membulat penuh.
- Isi (kiri ke kanan): logo (ikon api kecil gradien oranye-merah + teks "PantauApi"), menu 3 item (item aktif: pil berlatar oranye lembut + teks oranye tua), kanan: badge "Diperbarui 14:05 WIB" dengan titik status.
- Perilaku: di halaman Peta, setelah idle sekitar 3 detik opasitas turun ke sekitar 65 persen dan blur latar ringan; hover/fokus/sentuh kembali solid. Di `/data` dan `/analytics` tetap solid, bayangan tipis, sticky.
- Tablet: menu menjadi ikon + label pendek; badge pembaruan menjadi titik status saja.

### 4.2 Footer
Ringkas, latar ember gelap, teks terang kecil: atribusi sumber data dan basemap, catatan "Hotspot adalah indikasi anomali suhu satelit, bukan kepastian kebakaran". Di halaman Peta, atribusi basemap kecil di pojok kanan bawah peta, bukan footer penuh.

### 4.3 Status dan Badge
- Job: Queued (abu-abu, ikon jam), Running (biru, ikon putar statis), Success (hijau, centang), Failed (merah, silang). Selalu ikon + teks.
- Kesegaran data: hijau (<4 jam), kuning (4-8 jam), merah (>8 jam atau gagal).
- Badge "Prediksi" (outline oranye) untuk semua elemen prediksi.

## 5. Halaman 1: Peta (`/`)

**Tujuan utama**: melihat di mana hotspot sekarang dan melihat risiko 7 hari ke depan.

**Layout (desktop)**: peta penuh layar di belakang semua elemen; top bar melayang di atas.
- Kiri atas (di bawah top bar): **Kartu Filter** (lebar sekitar 288 px, dapat diciutkan): chip jendela waktu (24 jam | 48 jam | 7 hari), dropdown sensor (Semua, VIIRS, MODIS), slider/segmented confidence minimum (Semua | Nominal+ | High), daftar toggle lapisan: Hotspot, Densitas grid, Prediksi risiko 7 hari, Batas provinsi.
- Kanan atas: **3 KPI mini** (kartu putih kecil): "Hotspot (24 jam)", "Provinsi tertinggi", "Confidence tinggi". Angka besar, label kecil, delta opsional.
- Kiri bawah: **Legenda** kecil: confidence (3 lingkaran), ukuran FRP, skala risiko 4 tingkat (aktif bila lapisan risiko menyala).
- Kanan bawah: kontrol zoom +/-, "Reset tampilan", pilihan basemap (Terang/Satelit).
- Klik titik: **popup kartu** (latar ember gelap, teks terang): waktu WIB, koordinat, sensor, confidence (badge), FRP, provinsi.
- Klik provinsi (bila batas tersedia): **drawer kanan** (lebar sekitar 360 px): nama provinsi, hotspot 24 jam/7 hari, mini tren (sparkline), peringkat nasional, tombol utama "Lihat analitik provinsi".
- Perilaku zoom: zoom rendah = grid agregat (kotak berwarna per intensitas), zoom tinggi = titik + cluster bubble berangka.
- Banner kecil di atas peta (muncul bila perlu): "Data tertunda sejak 09:00 WIB".

**State**: loading (skeleton di kartu KPI, indikator tipis di atas peta), kosong ("Tidak ada hotspot pada filter ini" + tombol reset filter), error (kartu kecil + "Coba lagi").

**Tablet**: kartu filter menjadi tombol "Filter" yang membuka bottom sheet; KPI menjadi satu baris horizontal di bawah top bar; drawer provinsi menjadi bottom sheet setengah layar.

## 6. Halaman 2: Data & Pre-processing (`/data`)

**Tujuan utama**: memastikan akuisisi otomatis sehat dan menjalankan pre-processing.

**Layout**: latar terang, kontainer lebar maksimum sekitar 1200 px.
1. **Strip status** (4 kartu horizontal): Total baris mentah di HDFS (angka besar + progress menuju 1.000.000 + badge "Terpenuhi"), Ingest terakhir (waktu, baris), Status Spark (Idle/Running + job aktif), Karantina (jumlah, tautan ke panel).
2. **Tab**: Sumber Data | Pre-processing | Riwayat Job.

**Tab Sumber Data**
- Grid kartu sumber (FIRMS VIIRS, FIRMS MODIS, CHIRPS, ERA5): nama, status otomatis (badge), pembaruan terakhir, baris, rentang tanggal, path HDFS (teks kecil monospace).
- Panel "Jadwal Akuisisi Otomatis": NiFi tiap 3 jam (berikutnya pukul ...), impor folder.
- Header panel daftar file: judul "Dataset di HDFS" dan **tombol sekunder kecil "Tambah data"** (outline, ikon plus, tidak berwarna api penuh) di kanan. Tabel file: nama, sumber, jalur masuk (Otomatis/NiFi/Manual), ukuran, baris, tanggal, aksi hapus (ikon).
- **Modal "Tambah data"**: area drop file sederhana, daftar file terpilih, hasil deteksi per file (badge format: VIIRS/MODIS/Cuaca/Tidak dikenal, perkiraan baris, kolom dikenali/tidak dikenali), tombol "Proses" dan "Batal". Teks bantu satu kalimat: "Data akan diproses otomatis dan muncul di peta setelah job selesai."
- Panel Karantina (ciut/buka): daftar file/baris gagal parse + alasan.

**Tab Pre-processing**
- Kiri: pemilih dataset, ringkasan profiling (kartu: baris, kolom, null %, duplikat %).
- Tengah: **stepper pipeline** berurutan (Cleaning, Transformasi, Normalisasi, Encoding, Spatial enrichment, Cuaca & fitur) berupa kartu yang bisa dibuka; tiap kartu berisi opsi (checkbox/dropdown).
- Kanan atau bawah: ringkasan konfigurasi dan tombol utama "Jalankan pipeline" (tombol api penuh), tombol sekunder "Simpan konfigurasi".
- Setelah job: **laporan sebelum/sesudah** berupa funnel baris per langkah dan tabel statistik kolom.

**Tab Riwayat Job**: tabel (jenis, status badge, mulai, durasi, baris in/out), klik membuka drawer dengan log ringkas dan laporan.

**Tablet**: kartu status 2x2; stepper vertikal; tabel dapat digeser horizontal.

## 7. Halaman 3: Analitik (`/analytics`)

**Tujuan utama**: memahami pola dan menilai prediksi.

**Layout**
1. **Hero KPI gelap (ember)**: baris 4-5 kartu KPI di atas latar ember gelap bergradien tipis: Hotspot hari ini, 7 hari, 30 hari, Provinsi tertinggi, Rata-rata FRP. Angka besar terang, delta kecil.
2. **Bilah filter lengket** (latar putih, di bawah top bar): rentang tanggal, provinsi, sensor, confidence; navigasi section sebagai tab/anchor: Ringkasan | Wilayah | Musiman | Cuaca | Prediksi ML | Validasi.
3. **Section Ringkasan**: grafik garis tren harian (lebar penuh) dengan toggle Harian/Bulanan; grafik batang perbandingan tahun ke tahun.
4. **Section Wilayah**: bar horizontal ranking provinsi + choropleth provinsi (bila GeoJSON ada) berdampingan; tabel top grid.
5. **Section Musiman**: heatmap bulan x tahun (skala kuning ke merah tua), switch ke bulan x provinsi.
6. **Section Cuaca**: grafik dua sumbu (hotspot vs curah hujan, hujan berwarna teal), scatter korelasi, kartu "Hari kering berturut-turut".
7. **Section Prediksi ML**: header section berlatar ember gelap dengan judul "Prediksi Risiko 7 Hari" + badge "Prediksi" + catatan "Estimasi risiko, bukan kepastian". Isi: peta risiko (kartu peta), tabel 10 grid risiko tertinggi, kurva risiko mingguan; panel performa model: kartu metrik (AUC-ROC, AUC-PR, Precision, Recall, F1) dengan perbandingan terhadap baseline persistensi, confusion matrix, bar feature importance, info versi/tanggal training. Tombol "Perbarui prediksi".
8. **Section Validasi**: grafik garis ganda (hotspot pipeline vs rekap SiPongi+/BNPB), kartu korelasi dan selisih relatif, tombol sekunder "Unggah rekap".
9. Footer ember.

**Kartu grafik**: latar putih, judul + deskripsi satu baris + menu (ekspor), state loading/kosong/error di dalam kartu.

**Tablet**: grafik bertumpuk satu kolom; filter menjadi satu baris yang dapat digeser.

## 8. Aturan Grafik dan Peta
- Grafik garis hotspot: oranye-merah; pembanding: abu-abu; cuaca: teal. Garis prediksi putus-putus.
- Heatmap: skala sekuensial kuning -> oranye -> merah -> marun, dengan legenda angka.
- Titik hotspot: lingkaran dengan outline putih tipis agar terbaca di basemap terang.
- Semua grafik memiliki tooltip, label sumbu berbahasa Indonesia, angka berformat Indonesia (titik ribuan), tanggal "16 Nov 2026".
- Jangan lebih dari satu grafik animasi masuk; animasi masuk ECharts dinonaktifkan atau durasi sangat pendek.

## 9. Copy Utama (Bahasa Indonesia)
Judul peta: "Pantau titik api di seluruh Indonesia". Label: "Hotspot", "Confidence", "FRP", "Pipeline", "Job". Catatan: "Hotspot adalah indikasi anomali suhu dari satelit, bukan kepastian kebakaran." Prediksi: "Estimasi risiko 7 hari ke depan, bukan kepastian kejadian."
