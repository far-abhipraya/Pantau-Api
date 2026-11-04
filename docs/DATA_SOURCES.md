# DATA_SOURCES

| Sumber | Peran | Akses | Catatan |
|---|---|---|---|
| NASA FIRMS Archive Download | Hotspot historis VIIRS/MODIS (CSV) | https://firms.modaps.eosdis.nasa.gov/download/ | Perlu login Earthdata atau email. Unduh per negara/area dan per tahun |
| NASA FIRMS API | NRT (layanan `area`, CSV) | https://firms2.modaps.eosdis.nasa.gov/api/ | Perlu MAP_KEY. Fitur `countries` sempat ditandai tidak tersedia, gunakan `area` dengan bbox |
| FIRMS Fire Map | Pemantauan visual, unduhan 24/48 jam dan 7 hari | https://firms.modaps.eosdis.nasa.gov/ | Untuk pengecekan manual |
| CHIRPS | Curah hujan harian | https://www.chc.ucsb.edu/data/chirps , https://data.chc.ucsb.edu/products/CHIRPS-2.0/ | CHIRPS v2 berhenti diproduksi setelah Desember 2026; v3 tersedia, periksa |
| ERA5 / ERA5-Land | Suhu, kelembapan, angin | https://cds.climate.copernicus.eu/ | Perlu akun CDS dan CDS API. Statistik harian siap pakai tersedia di katalog |
| SiPongi+ (Kemenhut) | Validasi hotspot dan luas kebakaran | https://sipongi.gakkum.kehutanan.go.id/ , https://sipongi.gakkum.kehutanan.go.id/indikasi-luas-kebakaran | Wajib cantumkan "SIPONGI KEMENHUT" |
| Dashboard BNPB Karhutla | Validasi ringkasan harian | https://data.bnpb.go.id/data/karhutla2026 | Ada tombol unduh |
| BMKG Hotspot | Citra pembanding | https://www.bmkg.go.id/cuaca/satelit/polar-hotspot | Visual saja |

## Langkah yang dilakukan pengguna (bukan agent)
1. Buat akun NASA Earthdata dan minta MAP_KEY FIRMS. Isi `FIRMS_MAP_KEY` di `.env`.
2. Buat akun Copernicus CDS dan siapkan kredensial CDS API di `.env` (atau berkas konfigurasi CDS lokal di luar repo).
3. Unduh atau izinkan agent mengunduh data lewat skrip di `scripts/`.

## Aturan data
- Bbox Indonesia (perkiraan, verifikasi): lat -11 sampai 6, lon 95 sampai 141.
- Gunakan data kualitas standar untuk training; NRT untuk tampilan terkini.
- Latensi satelit sekitar 3 jam, sebut "near real-time".
- Tutupan awan dapat menyembunyikan hotspot; hotspot bukan kepastian kebakaran.
- Hitung jumlah baris sebelum finalisasi rentang tahun (target total >= 1.000.000).
- Belum dicari/diverifikasi: GeoJSON batas provinsi, peta lahan gambut, tutupan lahan (opsional).
