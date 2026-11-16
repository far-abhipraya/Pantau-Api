# STITCH_PROMPTS_ANALYTICS: Pengganti Prompt 3 dan Lanjutan

Gantikan Prompt 3 di `docs/STITCH_PROMPTS.md` dengan versi di bawah. Impor `docs/DESIGN.md` terlebih dahulu. Gunakan satu prompt pada satu waktu dan evaluasi hasilnya sebelum lanjut.

## Prompt 3A: Halaman Analitik (struktur utama)
```
Design the "Analitik" page (desktop, 1440x1600 scrollable) for PantauApi, an Indonesian wildfire hotspot monitoring app, using the existing design system and floating top bar ("Analitik" active, solid).
Primary goal: help the user understand current wildfire hotspot conditions, which past factors relate to them, and what is predicted next.
Layout, top to bottom:
1) Dark ember (#2A1210) hero band with 5 KPI cards in light text: "Hotspot hari ini", "7 hari", "30 hari", "Provinsi tertinggi", "Rata-rata FRP".
2) Section "Insight utama" on warm off-white (#FBF8F5): a small caption "Dihitung dari data 1 Jan - 16 Nov 2026 · diperbarui 14:05 WIB" and a grid of 6 insight cards. One featured card spans two columns with a dark ember background and light text; the others are white cards with a 4px colored left stripe by type (Tren orange, Wilayah dark red, Faktor teal, Musiman amber, Prediksi deep orange with a "Prediksi" outline badge, Validasi gray). Each card: small icon, short title, large key figure (e.g. "+42%"), a one- or two-line insight sentence in Indonesian, a confidence badge ("Keyakinan: Tinggi/Sedang/Rendah"), a "Lihat detail" link and an info icon for "Lihat bukti".
3) Sticky white filter bar (date range, province, sensor, confidence) with section tabs: Ringkasan, Wilayah, Musiman, Faktor Pengaruh, Prediksi ML, Validasi.
4) Show only the Ringkasan section below: a daily trend line chart with Harian/Bulanan toggle and a year-over-year bar chart, in white cards.
Style: light-first, warm off-white background, white cards, accent deep orange to red (#D9480F to #C92A2A), weather data in teal (#0B7285), neutral gray for comparisons, DM Sans headings, Inter body, radius 12px, soft shadows, flat, no heavy animation.
Use realistic sample content in Indonesian (technical terms in English). Insight wording must be associative ("berkaitan dengan"), never causal.
Constraints: every card has loading/empty/error states; tablet: insight grid 2 columns then 1.
```

## Prompt 3B: Section Faktor Pengaruh
```
On the same Analitik page, add the section "Faktor Pengaruh" below Musiman, with subtitle "Faktor di masa lalu yang berkaitan dengan kejadian hari ini" and a small info note "Hubungan bersifat asosiasi, bukan bukti sebab-akibat."
Header row: segmented selector "Nasional | Pulau | Provinsi" plus a dropdown.
Row 1: a line chart "Korelasi dengan jeda waktu" (x = lag 0-8 minggu, y = korelasi Spearman) with rainfall in teal, temperature in amber, humidity in gray, the best lag marked with a dot and label, next to a card "Jeda paling berpengaruh" with the lag, correlation value, number of weeks and a confidence badge.
Row 2: two side-by-side charts "Peluang hotspot 7 hari ke depan" by consecutive dry days (0, 1-3, 4-7, 8-14, 15-21, 22-30, >30) and by 30-day cumulative rainfall quantile; bars in orange-to-red, sample size n shown under each bar, a dashed baseline line.
Row 3: four horizontal anomaly cards (Hujan 30 hari, Suhu 7 hari, Kelembapan 7 hari, Hari tanpa hujan berturut-turut), each with current value, historical normal, percentile bar, and a badge such as "Lebih kering dari normal".
Row 4: left "Penjelas wilayah": region picker, current risk score with a category badge, and a horizontal bar list of the top 5 driving factors (Indonesian feature names, current value, percentile, up/down arrow), labeled "Perkiraan faktor pendorong (heuristik)"; right: "Faktor terpenting model" bar chart of top 8 features.
Row 5: full-width line chart "Pembanding antar tahun": cumulative hotspots by day of year, one highlighted year in orange-red, historical average gray dashed, with a thin teal strip for yearly rainfall anomaly below.
Keep the same style, white cards, no animation, tablet-friendly (single column, anomaly cards 2x2).
```

## Prompt 3C: Prediksi ML dan Validasi (lanjutan)
```
Add the sections "Prediksi ML" and "Validasi" below Faktor Pengaruh. "Prediksi ML" starts with a dark ember header band titled "Prediksi Risiko 7 Hari" with an outline badge "Prediksi" and the note "Estimasi risiko, bukan kepastian". Below: a risk map card (grid cells yellow to dark maroon with a 4-step legend Rendah, Sedang, Tinggi, Sangat tinggi), a top-10 risk grid table, a weekly risk curve with a dashed line, metric cards (AUC-ROC, AUC-PR, Precision, Recall, F1) each with a small comparison to a persistence baseline, a confusion matrix, and a small card "Cara membaca peta risiko" with a button "Lihat faktor pendorong wilayah ini". "Validasi" has a two-line chart (pipeline vs SiPongi+/BNPB), a correlation card, and a quiet secondary button "Unggah rekap". Finish with a methodology note and the dark ember footer with data attribution.
```

## Prompt Perbaikan Cepat (satu per kali)
- `Make the featured insight card taller with a larger key figure, keep other cards unchanged.`
- `Reduce visual density in the Faktor Pengaruh section: fewer gridlines, more whitespace, keep all components.`
- `Show the "Lihat bukti" popover on an insight card with value, sample size, time window and calculation date.`
- `Show the empty state of the insight grid: "Belum cukup data untuk membuat insight pada filter ini" with a reset filter button.`
- `Create the tablet version (834x1112) of the Insight utama section with a 2-column grid.`
