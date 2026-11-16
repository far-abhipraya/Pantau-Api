# PATCH v1.2.1: Penambahan Insight dan Faktor Pengaruh pada Halaman Analitik

Terapkan perubahan berikut pada dokumen v1.2. Sumber kebenaran halaman Analitik kini `docs/ANALYTICS_SPEC.md`.

## Instruksi untuk Agent
Terapkan semua perubahan di bawah ini persis seperti tertulis. Jangan mengubah bagian lain. Setelah selesai, tampilkan ringkasan perubahan per berkas. Jangan menghapus FR-A lama sebelum penggantinya terpasang.

## 1. `docs/PRD.md`
1. Header: ubah "Versi 1.2" menjadi "Versi 1.2.1 (menambah Insight Utama dan Faktor Pengaruh pada Analitik)". Tambahkan `docs/ANALYTICS_SPEC.md` ke daftar "Dokumen terkait".
2. Bagian 1 (Ringkasan), butir 3: ganti dengan: "**Analitik**: dashboard dengan Insight Utama (kartu insight otomatis), statistik deskriptif, Faktor Pengaruh (faktor masa lalu yang berkaitan dengan kejadian hari ini), prediksi risiko berbasis machine learning, dan validasi terhadap SiPongi+/BNPB."
3. Bagian 8.3: ganti seluruh isi FR-A1..FR-A8 dengan:
   - FR-A1 Hero KPI (hotspot hari ini/7/30 hari, provinsi tertinggi, rata-rata FRP).
   - FR-A2 **Insight Utama**: 5-7 kartu insight hasil perhitungan (katalog I1-I8, aturan, dan komponen di `docs/ANALYTICS_SPEC.md` Bagian 3), mengikuti filter global, dengan tingkat keyakinan dan bukti.
   - FR-A3 Ringkasan (tren harian/bulanan, tahun ke tahun), Wilayah (ranking, choropleth), Musiman (heatmap).
   - FR-A4 **Faktor Pengaruh** (menggantikan section Cuaca): FP1 korelasi lag, FP2 dosis-respons, FP3 anomali kondisi saat ini, FP4 penjelas wilayah, FP5 pembanding antar tahun, FP6 faktor terpenting model (`docs/ANALYTICS_SPEC.md` Bagian 4).
   - FR-A5 Prediksi ML (peta risiko 7 hari, tabel grid teratas, kurva risiko mingguan, metrik vs baseline persistensi, confusion matrix, feature importance, kartu "Cara membaca peta risiko", tautan ke FP4).
   - FR-A6 Validasi terhadap SiPongi+/BNPB.
   - FR-A7 Tombol "Perbarui agregasi/prediksi/insight" memicu rantai job (aggregate -> features -> train/predict -> insights).
   - FR-A8 State loading/kosong/error pada setiap kartu; catatan metodologi (asosiasi bukan sebab-akibat).
4. Bagian 2.2: tambahkan AC-10 sampai AC-14 dari `docs/ANALYTICS_SPEC.md` Bagian 8.
5. Bagian 9 (API): tambahkan endpoint `/analytics/insights`, `/analytics/drivers/lag`, `/drivers/dose-response`, `/drivers/anomaly`, `/drivers/region`, `/drivers/year-compare`, `/drivers/importance` (Bagian 7 ANALYTICS_SPEC).
6. Bagian 9.1 (Serving layer): tambahkan tabel `lag_correlation`, `dose_response`, `weather_anomaly`, `region_drivers`, `year_compare`, `insight_cards` (Bagian 6 ANALYTICS_SPEC).
7. Bagian 13 (struktur repo): tambahkan `backend/spark_jobs/insights.py`, `backend/spark_jobs/insight_config.yaml`, `docs/ANALYTICS_SPEC.md`, `docs/STITCH_PROMPTS_ANALYTICS.md`, `.agents/rules/insights.md`.
8. Bagian 12 (NFR): tambahkan "NFR-10: Seluruh angka dan klaim pada kartu insight harus dapat ditelusuri ke tabel hasil perhitungan (`evidence_json`); bahasa insight bersifat asosiasi."
9. Bagian 16 (Risiko): tambahkan baris "Insight terkesan kausal atau sampel kecil menyesatkan | Bahasa asosiasi, badge keyakinan, n sampel terlihat, kartu disembunyikan bila n < 30".

## 2. `docs/UI_SPEC.md`
- Ganti seluruh Bagian 7 (Halaman 3: Analitik) dengan rujukan: "Lihat `docs/ANALYTICS_SPEC.md` Bagian 2, 3, 4, 5, dan 9. Ringkasan: Hero KPI gelap -> Insight Utama -> filter lengket -> Ringkasan -> Wilayah -> Musiman -> Faktor Pengaruh -> Prediksi ML -> Validasi -> catatan metodologi -> footer."
- Bagian 4.3 tambahkan: "Badge keyakinan insight: Tinggi (hijau), Sedang (kuning), Rendah (abu-abu), selalu dengan teks."
- Bagian 8 tambahkan: "Grafik lag: korelasi hujan teal, suhu amber, kelembapan abu-abu. Kurva dosis-respons: batang oranye-merah dengan n sampel di bawah batang."

## 3. `docs/DESIGN.md`
Tambahkan di Bagian 2 (Color Tokens):
```yaml
  insight-trend: "#F76707"
  insight-region: "#9F1D1D"
  insight-factor: "#0B7285"
  insight-seasonal: "#F59F00"
  insight-forecast: "#D9480F"
  insight-validation: "#868E96"
  confidence-high: "#2B8A3E"
  confidence-medium: "#E67700"
  confidence-low: "#868E96"
```
Tambahkan di Bagian 5 (Components): "**Kartu insight**: kartu putih, strip kiri 4 px sesuai tipe (`insight-*`), ikon kecil, judul maks 5 kata, angka kunci (`kpi` 28-36), kalimat 1-2 baris, badge keyakinan, tautan 'Lihat detail', ikon info 'Lihat bukti'. **Kartu insight sorotan**: latar `ember`, teks `ember-text`, lebar 2 kolom. **Kartu anomali**: nilai saat ini, normal historis, bar persentil, badge. **Bar faktor pendorong**: bar horizontal dengan panah arah dan nilai persentil."

## 4. `docs/STITCH_PROMPTS.md`
Ganti seluruh "Prompt 3: Halaman Analitik" dan prompt lanjutannya dengan rujukan ke `docs/STITCH_PROMPTS_ANALYTICS.md` (Prompt 3A, 3B, 3C).

## 5. `docs/TASKS.md`
Ganti Fase 5 dengan:
```
## Fase 5: Halaman Analitik (A + B)
- [ ] Endpoint analytics dasar (kpi, trend, ranking, seasonality).
- [ ] Halaman /analytics: hero KPI, filter lengket, section Ringkasan/Wilayah/Musiman.
- [ ] Job `insights.py` (lag_correlation, dose_response, weather_anomaly, year_compare) dan `insight_config.yaml`.
- [ ] Endpoint /analytics/drivers/* dan section Faktor Pengaruh (FP1-FP3, FP5).
- [ ] Generator kartu insight rule-based (`insight_cards`) + endpoint /analytics/insights + UI kartu insight (bukti, keyakinan).
- Selesai bila: AC-5, AC-10, AC-11, AC-13, AC-14.
```
Tambahkan di akhir Fase 6 (ML):
```
- [ ] `region_drivers` (push_score heuristik) dan FP4 Penjelas wilayah; FP6 feature importance berlabel Indonesia; insight I7.
- Selesai bila: AC-7, AC-12.
```
Tambahkan di Fase 8: `- [ ] Kalibrasi ambang keyakinan insight dan tinjau seluruh kalimat insight (bahasa asosiasi).`

## 6. `AGENTS.md`
Tambahkan di bagian "UI": "Halaman Analitik mengikuti `docs/ANALYTICS_SPEC.md`. Kartu insight dibuat dari aturan dan angka hasil perhitungan (tabel `insight_cards` + `evidence_json`). Dilarang menulis angka insight secara manual atau memakai LLM untuk menghasilkan angka. Bahasa insight selalu asosiasi, bukan sebab-akibat."

## 7. `.agents/rules/insights.md` (berkas baru)
Buat berkas dengan isi berikut:
```
# Aturan: Insight dan Faktor Pengaruh
- Semua kartu insight berasal dari `insight_cards`, dihitung job `insights.py` dari data nyata; simpan `evidence_json` (nilai, n, jendela, tanggal hitung).
- Dilarang membuat angka insight secara manual, dari contoh dokumen, atau dari LLM.
- Bahasa asosiasi: "berkaitan dengan", "diikuti oleh". Dilarang "menyebabkan".
- Keyakinan dihitung dari n sampel dan kekuatan hubungan menurut `insight_config.yaml`; sembunyikan kartu bila n < 30.
- Korelasi lag memakai Spearman pada seri mingguan; baseline anomali minimal 5 tahun dan mengecualikan tahun berjalan; dosis-respons dari `features/grid_daily`.
- Penjelas wilayah memakai heuristik push_score dan wajib berlabel "Perkiraan faktor pendorong (heuristik)".
- Tulis tes unit untuk perhitungan lag, anomali, dan generator kalimat dengan data kecil yang diketahui hasilnya.
- Contoh angka di dokumen/prompt desain bukan data nyata; jangan disalin ke kode.
```
