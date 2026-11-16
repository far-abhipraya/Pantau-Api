# PantauApi

Platform big data (Hadoop HDFS, Spark, NiFi) untuk memantau hotspot karhutla Indonesia dan memperkirakan risikonya.

Tiga halaman: Peta (`/`), Data & Pre-processing (`/data`), Analitik (`/analytics`).

## Dokumen
- `AGENTS.md`: aturan agent (selalu aktif); `.agents/rules/`: aturan terperinci; `.agents/workflows/start-phase.md`: `/start-phase <nomor>`
- `docs/PRD.md` (v1.2), `docs/UI_SPEC.md`, `docs/DESIGN.md`, `docs/STITCH_PROMPTS.md`
- `docs/ENVIRONMENT.md`, `docs/TASKS.md`, `docs/DATA_SOURCES.md`

## Mulai Cepat
1. Salin `.env.example` menjadi `.env` dan isi.
2. CMD Administrator: `scripts\start_hdfs.bat`
3. `python scripts\check_env.py`
4. Mulai Fase 0 di `docs/TASKS.md`.
