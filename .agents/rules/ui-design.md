# Aturan: UI dan Design System

- Sumber kebenaran: `docs/DESIGN.md` (token), `docs/UI_SPEC.md` (layout), `docs/design/` (ekspor Stitch/Figma bila ada). Bila bertentangan, tanyakan pengguna, jangan memilih sendiri.
- Buat `frontend/styles/tokens.css` (CSS variables) dari token DESIGN.md dan petakan ke `tailwind.config`. Dilarang hardcode hex di komponen.
- Warna api hanya untuk data (hotspot/risiko), aksi utama, dan state aktif. Teal untuk cuaca. Bagian gelap "ember" hanya: hero KPI Analitik, header section Prediksi ML, popup peta, footer.
- Top bar melayang: kapsul, tinggi 52-56 px, idle di halaman Peta turun ke opasitas sekitar 0,65 setelah sekitar 3 detik, kembali solid saat hover/fokus/sentuh.
- Tombol "Tambah data" harus tombol sekunder kecil (outline), bukan CTA utama.
- Animasi: transisi 150-200 ms saja; nonaktifkan animasi masuk ECharts; satu efek blur saja (top bar); hormati `prefers-reduced-motion`.
- Status job selalu ikon + teks. Skala risiko selalu disertai label.
- Semua kartu grafik/peta punya state loading, kosong, dan error.
- Tablet (768-1024 px): panel melayang menjadi bottom sheet/drawer; tabel dapat digeser.
- Format angka dan tanggal Indonesia (1.234.567; "16 Nov 2026"; "14:05 WIB").
- Aksesibilitas: kontras >= 4,5:1, target sentuh >= 40 px, fokus terlihat.
