# STITCH_PROMPTS: Panduan dan Prompt Google Stitch untuk PantauApi

Panduan Stitch menyarankan: mulai dari konsep luas lalu rinci per layar, satu layar atau komponen per prompt, dan perubahan kecil (satu atau dua) per prompt lanjutan. Template yang disarankan: platform, tujuan halaman, layout, komponen, data, gaya, batasan.

## Langkah 0: Siapkan Konteks Desain
1. Buat proyek Stitch bertipe **Web** (desktop). 
2. Impor/tempel isi `docs/DESIGN.md` sebagai design system proyek. Bila impor tidak tersedia, tempel Bagian "Overview", "Color Tokens", "Typography", dan "Components" pada prompt pertama.
3. Hasilkan satu layar dulu (Prompt 1), nilai arah visual, perbaiki, baru lanjut layar berikutnya agar konsisten. Bila perlu hasilkan 2-3 varian layout Peta lalu pilih.

## Prompt 1: Halaman Peta (home)
```
Design a web dashboard home page (desktop, 1440x900) for "PantauApi", an Indonesian wildfire hotspot monitoring app. Language: Indonesian, technical terms in English (Hotspot, Confidence, FRP).
Primary goal: let the user see where active wildfire hotspots are in Indonesia right now and toggle a 7-day risk prediction layer.
Layout: full-bleed interactive map of Indonesia (light, desaturated basemap) filling the whole screen. A slim floating pill-shaped top bar (about 56px high, white, soft shadow, centered, max width 1120px) with a flame icon logo and text "PantauApi", three menu items: "Peta" (active), "Data & Pre-processing", "Analitik", and on the right a badge "Diperbarui 14:05 WIB" with a green status dot.
Components, by priority: (1) top-left floating filter card (288px, rounded 16px): time window chips "24 jam | 48 jam | 7 hari", sensor dropdown, confidence segmented control, layer toggles "Hotspot", "Densitas grid", "Prediksi risiko 7 hari", "Batas provinsi". (2) top-right three small KPI cards: "Hotspot (24 jam)" 7.491, "Provinsi tertinggi" Sumatera Selatan, "Confidence tinggi" 2.318. (3) hotspot points as small circles in orange to dark red with white outline and numbered cluster bubbles. (4) bottom-left compact legend for confidence colors, point size = FRP, and a 4-step risk scale (Rendah, Sedang, Tinggi, Sangat tinggi). (5) bottom-right zoom controls, reset view button, basemap switch.
Data: thousands of points across Sumatra and Kalimantan; show loading skeleton, empty ("Tidak ada hotspot pada filter ini") and error states.
Style: light-first, warm off-white (#FBF8F5) and white cards, primary accent deep orange to red (#D9480F to #C92A2A), dark ember (#2A1210) only for popups. Fonts DM Sans (headings) and Inter (body). Radius 12-16px, soft shadows, flat, minimal, no heavy animation.
Constraints: tablet-friendly (panels become bottom sheets), high contrast, risk scale not reliant on color alone.
```

Prompt lanjutan (satu per kali):
- `Add a popup card for a clicked hotspot point with dark ember background (#2A1210) and light text, showing time WIB, coordinates, sensor, confidence badge, FRP, and province.`
- `Add a right-side drawer (360px) for a selected province with name, hotspot 24h and 7d counts, a small sparkline, national rank, and a primary button "Lihat analitik provinsi".`
- `Show the top bar in its idle state: 65% opacity with subtle blur, keep everything else unchanged.`
- `Show the risk prediction layer turned on: grid cells colored yellow to dark maroon with a "Prediksi" outline badge and the note "Estimasi risiko 7 hari ke depan, bukan kepastian".`

## Prompt 2: Halaman Data & Pre-processing
```
Design the "Data & Pre-processing" page (desktop, 1440x900) for PantauApi using the same design system and top bar (menu item "Data & Pre-processing" active, solid top bar).
Primary goal: let the user confirm that automatic data acquisition is healthy and run the pre-processing pipeline.
Layout: centered container (max 1200px) on warm off-white background. Below the top bar, a status strip of 4 cards: "Total baris mentah di HDFS" 3.482.116 with a progress bar toward 1.000.000 and a green badge "Terpenuhi"; "Ingest terakhir" 14:05 WIB, 12.480 baris; "Status Spark" Idle; "Karantina" 3 file. Under it, tabs: "Sumber Data" (active), "Pre-processing", "Riwayat Job".
Tab "Sumber Data": grid of 4 source cards (FIRMS VIIRS, FIRMS MODIS, CHIRPS, ERA5) each with status badge, last update, row count, date range, and a small monospace HDFS path. A panel "Jadwal Akuisisi Otomatis" (NiFi every 3 hours, next run 17:00). A table "Dataset di HDFS" (name, source, entry path Otomatis/NiFi/Manual, size, rows, date, delete icon) whose header has a small, low-emphasis secondary outline button "Tambah data" with a plus icon on the right.
Style: same as Home; primary buttons use the orange-red gradient, but "Tambah data" must stay a quiet secondary button. Tables with 44px rows, tabular numbers.
Constraints: tablet-friendly (status cards 2x2, table scrolls horizontally).
```
Prompt lanjutan:
- `Add a modal "Tambah data": simple drop area, list of selected files with auto-detected format badges (VIIRS, MODIS, Tidak dikenal), estimated rows, recognized vs unrecognized columns, buttons "Proses" and "Batal", and one helper sentence: "Data akan diproses otomatis dan muncul di peta setelah job selesai."`
- `Show the "Pre-processing" tab: left dataset picker with profiling cards (rows, columns, null %, duplicates %), a vertical numbered stepper of collapsible cards (Cleaning, Transformasi, Normalisasi, Encoding, Spatial enrichment, Cuaca & fitur) with checkboxes and dropdowns, and a primary button "Jalankan pipeline" plus secondary "Simpan konfigurasi".`
- `Show the before/after report after a run: a horizontal funnel of row counts per step and a column statistics table.`
- `Show the "Riwayat Job" tab: table with status badges (Queued gray, Running blue, Success green, Failed red, each with icon), duration, rows in/out, and a right drawer with log and report.`
- `Add the quarantine panel listing files that failed to parse with reasons.`

## Prompt 3: Halaman Analitik
```
Design the "Analitik" dashboard page (desktop, 1440x1200 scrollable) for PantauApi with the same design system and top bar ("Analitik" active).
Primary goal: help the user understand wildfire hotspot trends, regions, seasonality, weather relation, and ML risk prediction quality.
Layout: a dark ember (#2A1210) hero band under the top bar with 5 KPI cards (Hotspot hari ini, 7 hari, 30 hari, Provinsi tertinggi, Rata-rata FRP) in light text. Below, a sticky white filter bar (date range, province, sensor, confidence) with section tabs: Ringkasan, Wilayah, Musiman, Cuaca, Prediksi ML, Validasi. Then sections on a warm off-white background with white chart cards: line chart of daily hotspots with Harian/Bulanan toggle and a year-over-year bar chart; horizontal bar ranking of provinces next to a province choropleth map; month-by-year heatmap (yellow to dark red); dual-axis chart hotspots vs rainfall (rainfall in teal #0B7285) and a scatter; a "Prediksi Risiko 7 Hari" section with a dark ember header, badge "Prediksi" and note "Estimasi risiko, bukan kepastian", containing a risk map card, top-10 risk grid table, weekly risk curve, metric cards (AUC-ROC, AUC-PR, Precision, Recall, F1) compared with a persistence baseline, a confusion matrix and a feature importance bar chart; a "Validasi" section with a two-line chart (pipeline vs SiPongi+/BNPB), correlation card, and a quiet secondary button "Unggah rekap".
Style: light-first, chart series orange to red, neutral gray comparison, dashed lines for predictions, Indonesian labels and number format (1.234.567), no animated charts.
Constraints: each card has loading, empty and error states; tablet: single column.
```
Prompt lanjutan:
- `Make the KPI hero more compact (height 140px) and add small delta indicators vs previous period.`
- `Increase chart card whitespace and reduce the number of gridlines.`
- `Show the empty and error states for a chart card.`

## Prompt 4: Konsistensi dan Tablet
- `Apply the same top bar, footer (dark ember, small attribution text), and card style across all three screens. Do not change content.`
- `Create the tablet (834x1112) versions of the Home screen with the filter as a bottom sheet and KPIs as a horizontal row.`
- `Create the tablet version of the Data page with 2x2 status cards.`

## Setelah Desain Selesai
1. Periksa konsistensi token: warna, radius, tipografi, jarak. Ekstrak dan perbarui `docs/DESIGN.md` bila ada perubahan yang Anda sukai.
2. Ekspor layar (Figma/kode/gambar) ke `docs/design/` agar agent merujuknya. Anda punya konektor Figma yang dapat dipakai untuk pengaturan lanjutan.
3. Perbarui `docs/UI_SPEC.md` bila desain final menyimpang dari spesifikasi, supaya dokumen dan desain sinkron.
4. Beri tahu agent: "Implementasikan UI mengikuti `docs/design/` dan `docs/DESIGN.md`; token ada di `styles/tokens.css`."

## Tips
- Jaga data contoh realistis (angka dan nama provinsi Indonesia) supaya desain terasa nyata.
- Bila hasil terlalu ramai, tambahkan: `Reduce visual density, remove decorative elements, keep only listed components.`
- Bila warna api terlalu dominan: `Use the fire colors only for data, primary buttons, and active states; keep all other surfaces white or warm off-white.`
