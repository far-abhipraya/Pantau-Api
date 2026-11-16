# DATA_SOURCES

| Sumber | Peran | Akses | Catatan |
|---|---|---|---|
| NASA FIRMS Archive Download | Hotspot historis VIIRS/MODIS (CSV) | https://firms.modaps.eosdis.nasa.gov/download/ | Perlu login Earthdata/email |
| NASA FIRMS API | NRT (layanan `area`, CSV) | https://firms2.modaps.eosdis.nasa.gov/api/ | Perlu MAP_KEY; gunakan `area` dengan bbox |
| FIRMS Fire Map | Pemantauan visual, unduhan 24/48 jam dan 7 hari | https://firms.modaps.eosdis.nasa.gov/ | Pengecekan manual |
| CHIRPS | Curah hujan harian | https://www.chc.ucsb.edu/data/chirps , https://data.chc.ucsb.edu/products/CHIRPS-2.0/ | v2 berhenti diproduksi setelah Desember 2026; v3 tersedia |
| ERA5 / ERA5-Land | Suhu, kelembapan, angin | https://cds.climate.copernicus.eu/ | Perlu akun CDS dan CDS API |
| SiPongi+ | Validasi hotspot dan luas kebakaran | https://sipongi.gakkum.kehutanan.go.id/ , https://sipongi.gakkum.kehutanan.go.id/indikasi-luas-kebakaran | Cantumkan "SIPONGI KEMENHUT" |
| Dashboard BNPB Karhutla | Validasi ringkasan harian | https://data.bnpb.go.id/data/karhutla2026 | Ada tombol unduh |
| BMKG Hotspot | Citra pembanding | https://www.bmkg.go.id/cuaca/satelit/polar-hotspot | Visual saja |

## Kandidat GeoJSON Batas Provinsi (BELUM diverifikasi: periksa lisensi, akurasi, jumlah provinsi 38, nama/kode)
- https://github.com/AlfianAliM/Indonesia-GeoJSON (`provinsi.geojson`, 38 provinsi; raw: https://raw.githubusercontent.com/AlfianAliM/Indonesia-GeoJSON/master/provinsi.geojson)
- https://github.com/chmdznr/indonesia-geojson (38 provinsi, batas administrasi 2022/2023)
- https://github.com/ardian28/GeoJson-Indonesia-38-Provinsi
- https://github.com/achmadrmdhn/geojson-wilayah-indonesia (kode dan nama BPS/Kemendagri)
- https://github.com/mahendrayudha/indonesia-geojson (GADM v4.0)
- https://github.com/ans-4175/peta-indonesia-geojson (kode provinsi; kemungkinan hanya 34 provinsi, periksa)

Langkah: pilih satu, verifikasi jumlah dan nama provinsi, sederhanakan geometri (simplify) agar ringan di web (target < 2 MB), simpan di `backend/app/static/geo/provinces.geojson`, dan buat lookup grid -> provinsi saat pre-processing. Bila tidak ada yang layak, peta tetap berfungsi tanpa lapisan batas.

## Basemap
CARTO Positron/Voyager (terang, tanpa API key) atau OpenStreetMap standar. Periksa syarat penggunaan dan tampilkan atribusi yang diwajibkan.

## Langkah pengguna (bukan agent)
1. Buat akun NASA Earthdata dan minta MAP_KEY FIRMS; isi `FIRMS_MAP_KEY` di `.env`.
2. Buat akun Copernicus CDS dan siapkan kredensial CDS API (di luar repo).
3. Izinkan agent mengunduh data lewat skrip di `scripts/`, atau taruh file di `C:\karhutla-data\inbox`.

## Aturan data
- Bbox Indonesia (perkiraan, verifikasi): lat -11 sampai 6, lon 95 sampai 141.
- Data standar untuk training; NRT untuk tampilan terkini. Latensi sekitar 3 jam: sebut "near real-time".
- Tutupan awan dapat menyembunyikan hotspot; hotspot bukan kepastian kebakaran.
- Hitung baris sebelum finalisasi rentang tahun (target >= 1.000.000).
- Belum dicari: peta gambut dan tutupan lahan (opsional).
