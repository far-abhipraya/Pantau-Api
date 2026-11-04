# Aturan: Data, Pre-processing, dan ML

## Data
- Jangan mengasumsikan skema FIRMS. Baca header file di `data_samples/` terlebih dahulu.
- Skema kanonik `clean/hotspot` ada di PRD Bagian 11.1. VIIRS dan MODIS dinormalisasi ke satu skema (`confidence_level` = low/nominal/high).
- Bounding box Indonesia (perkiraan, verifikasi): lat -11 sampai 6, lon 95 sampai 141.
- `grid_id` = lat/lon dibulatkan ke kelipatan 0,25 derajat (definisikan satu fungsi bersama di `spark_jobs/common.py`).
- Hotspot adalah indikasi anomali suhu, bukan kepastian kebakaran. Cantumkan di UI/laporan.
- Data bersumber SiPongi+ wajib mencantumkan "SIPONGI KEMENHUT".
- Jangan commit data besar. `data_samples/` hanya berisi sampel kecil.

## Pre-processing
- Setiap langkah mencatat jumlah baris sebelum/sesudah ke laporan job (JSON).
- Parameter normalisasi (min/max atau mean/std) disimpan agar bisa dipakai ulang saat inferensi.
- Pipeline dikonfigurasi via JSON dan dapat dijalankan ulang (idempoten).

## ML
- Split berbasis waktu. Dilarang split acak. Cegah kebocoran: fitur pada tanggal t hanya memakai data <= t.
- Bandingkan dengan baseline persistensi. Laporkan AUC-ROC, AUC-PR, precision, recall, F1, confusion matrix.
- Tangani ketidakseimbangan kelas (class weight atau undersampling).
- Jangan melaporkan metrik yang tidak benar-benar dihitung.
- UI wajib menyatakan bahwa keluaran adalah estimasi risiko, bukan kepastian.
