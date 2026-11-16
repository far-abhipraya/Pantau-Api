---
name: PantauApi
version: 1.0
colorMode: light
---

# DESIGN.md: PantauApi Design System

Berkas ini dapat diimpor ke Google Stitch sebagai konteks desain dan dipakai agent untuk membangun `styles/tokens.css` dan konfigurasi Tailwind.

## 1. Overview
PantauApi adalah dasbor pemantauan hotspot karhutla Indonesia. Karakter: serius, jernih, tepercaya, dengan aksen api yang hangat. Dasar terang dan bersih, aksen oranye gelap menuju merah untuk data hotspot, aksi utama, dan sorotan. Bagian gelap "ember" dipakai terbatas. Modern, datar dengan bayangan lembut, tanpa dekorasi berlebihan, tanpa animasi berat.

## 2. Color Tokens

```yaml
color:
  # Dasar terang
  bg: "#FBF8F5"            # latar halaman (putih hangat)
  surface: "#FFFFFF"       # kartu, panel
  surface-muted: "#F5EFE9" # latar sekunder, header tabel
  border: "#E8DFD6"
  text: "#1F1A17"
  text-muted: "#6B5F57"
  text-subtle: "#8F8279"

  # Aksen api
  fire-orange: "#F76707"   # oranye utama
  fire-deep-orange: "#D9480F"   # oranye gelap (tombol utama, tautan, item aktif)
  fire-red: "#C92A2A"      # merah api
  fire-crimson: "#9F1D1D"  # merah tua (hover/active)
  fire-gradient: "linear-gradient(135deg, #F76707 0%, #C92A2A 100%)"
  fire-tint: "#FFF1E6"     # latar lembut item aktif
  fire-tint-strong: "#FFD8BF"

  # Bagian gelap "ember" (terbatas)
  ember: "#2A1210"
  ember-2: "#3B1814"
  ember-text: "#FBEFE9"
  ember-text-muted: "#D9B8AC"

  # Skala risiko (sekuensial, aman untuk buta warna, luminans menurun)
  risk-low: "#FCC419"
  risk-medium: "#FD7E14"
  risk-high: "#E03131"
  risk-very-high: "#7A0C1E"

  # Confidence hotspot
  conf-low: "#FFC078"
  conf-nominal: "#F76707"
  conf-high: "#B71C1C"

  # Non-api
  weather-teal: "#0B7285"
  neutral-series: "#868E96"

  # Status
  success: "#2B8A3E"
  warning: "#E67700"
  danger: "#C92A2A"
  info: "#1C7ED6"
```

Aturan: warna api = hotspot/risiko/aksi utama. Teal = cuaca/hujan. Abu-abu = netral/pembanding. Status job selalu disertai ikon dan teks, bukan warna saja. Pastikan teks di atas oranye menggunakan putih hanya pada `fire-deep-orange` atau lebih gelap (kontras minimal 4,5:1); di atas `fire-orange`/kuning gunakan teks gelap.

## 3. Typography

```yaml
typography:
  headline: "DM Sans"     # judul, angka KPI besar
  body: "Inter"           # isi, tabel
  label: "DM Sans"        # label kecil, tombol
  mono: "JetBrains Mono"  # path HDFS, koordinat (fallback: monospace)
  scale:
    display: "32/40, 700"
    h1: "28/36, 700"
    h2: "22/30, 600"
    h3: "18/26, 600"
    body: "14/22, 400"
    small: "12/18, 400"
    kpi: "36/40, 700, tabular-nums"
```
Angka memakai tabular-nums. Format Indonesia (1.234.567), tanggal "16 Nov 2026", waktu "14:05 WIB".

## 4. Layout, Spacing, Shape

```yaml
spacing: [4, 8, 12, 16, 24, 32, 48]   # basis 4/8 px
radius:
  sm: 8
  md: 12     # kartu, input
  lg: 16     # panel melayang, modal
  pill: 999  # top bar, chip, badge
shadow:
  card: "0 1px 2px rgba(31,26,23,0.06), 0 1px 3px rgba(31,26,23,0.08)"
  floating: "0 8px 24px rgba(31,26,23,0.14)"
container:
  max-width: 1200   # halaman /data dan /analytics
  top-bar-max: 1120
breakpoints: { tablet: 768, laptop: 1280, desktop: 1536 }
```

## 5. Components

- **Top bar melayang**: kapsul putih (opasitas 0,92) bayangan `floating`, tinggi 52-56, logo (ikon api gradien + "PantauApi" DM Sans 700), menu 3 item; item aktif latar `fire-tint` + teks `fire-deep-orange`. Idle di halaman Peta: opasitas 0,65.
- **Tombol utama**: latar `fire-gradient` atau `fire-deep-orange`, teks putih, radius 12, tinggi 40. **Sekunder**: outline `border`, teks `text`, hover latar `surface-muted`. **Tombol "Tambah data"**: sekunder kecil (tinggi 32, ikon plus), sengaja tidak menonjol.
- **Kartu**: `surface`, border 1 px `border`, radius 12, padding 16-20, bayangan `card`. **Kartu KPI**: label kecil muted, angka `kpi`, delta kecil. **Kartu KPI gelap**: latar `ember`, teks `ember-text`.
- **Panel melayang peta**: `surface`, radius 16, bayangan `floating`, header kecil dengan tombol ciut.
- **Chip/segmented**: pil, aktif `fire-tint` + border `fire-orange`.
- **Badge**: pil kecil; "Prediksi" outline `fire-deep-orange`; status memakai ikon + teks.
- **Tabel**: header `surface-muted`, baris 44 px, hover `fire-tint` sangat tipis, angka rata kanan.
- **Tab**: garis bawah 2 px `fire-deep-orange` pada tab aktif.
- **Stepper pipeline**: kartu vertikal bernomor, nomor dalam lingkaran gradien api, state selesai = centang hijau.
- **Modal/Drawer**: radius 16, overlay gelap 40 persen, tanpa animasi selain fade 150 ms.
- **Popup peta**: latar `ember`, teks `ember-text`, radius 12, panah kecil.
- **Skeleton**: blok `surface-muted` statis (tanpa shimmer, atau shimmer sangat lambat opsional).
- **Grafik**: latar kartu putih, grid garis `border`, seri utama `fire-orange`/`fire-red`, cuaca `weather-teal`, pembanding `neutral-series`; prediksi garis putus-putus.

## 6. Peta
Basemap terang (CARTO Positron/Voyager atau setara tanpa API key), desaturasi agar titik api menonjol. Titik hotspot: lingkaran berisi warna confidence, outline putih 1 px, radius 3-9 px menurut FRP. Cluster: lingkaran `fire-deep-orange` dengan angka putih. Grid agregat: skala `risk-low` ke `risk-very-high` dengan opasitas 0,55-0,8. Batas provinsi: garis 1 px `#B8A99C` opasitas 0,7; hover menebalkan dan mengisi `fire-tint` 40 persen.

## 7. Motion
Maksimum 150-200 ms ease-out untuk hover, buka/tutup panel, ganti tab. Tidak ada animasi kontinu, parallax, atau partikel api. Efek blur hanya di top bar. Hormati `prefers-reduced-motion`.

## 8. Accessibility
Kontras teks >= 4,5:1; target sentuh >= 40 px; fokus keyboard cincin 2 px `fire-deep-orange` dengan offset 2 px; skala risiko disertai label teks dan angka; ikon pendamping untuk status.

## 9. Do dan Don't
- Do: warna api hanya untuk data/aksi utama; kartu putih bersih; ruang kosong cukup; label Indonesia, istilah teknis Inggris.
- Don't: latar gelap penuh, gradien api sebagai dekorasi besar, animasi api, lebih dari satu efek blur, warna api untuk status sukses/netral.
