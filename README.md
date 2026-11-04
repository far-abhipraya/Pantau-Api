# KarhutlaWatch

Platform big data (Hadoop HDFS, Spark, NiFi) untuk memantau hotspot karhutla Indonesia dan memprediksi risikonya.

## Dokumen
- `AGENTS.md`: aturan untuk agent (selalu aktif)
- `.agents/rules/`: aturan terperinci (Windows/Hadoop, data/ML, frontend/backend)
- `.agents/workflows/start-phase.md`: workflow `/start-phase <nomor>`
- `docs/PRD.md`: kebutuhan produk (v1.1)
- `docs/ENVIRONMENT.md`, `docs/TASKS.md`, `docs/DATA_SOURCES.md`

## Mulai Cepat
1. Salin `.env.example` menjadi `.env` dan isi.
2. CMD Administrator: `scripts\start_hdfs.bat`
3. `python scripts\check_env.py`
4. Mulai Fase 0 di `docs/TASKS.md`.
