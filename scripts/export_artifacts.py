"""Ekspor sampel data + ringkasan hasil ke folder repo (artefak kecil untuk GitHub).

Data penuh (2,1 juta baris) tetap di HDFS/serving lokal dan TIDAK masuk Git.
Jalankan: python scripts/export_artifacts.py
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "data_samples"
REPORTS = ROOT / "artifacts" / "reports"
SERVING = Path("C:/karhutla-data/serving")


def export_csv(name: str, sql: str) -> int:
    from app.services import serving

    rows = serving.query(sql)
    SAMPLES.mkdir(parents=True, exist_ok=True)
    target = SAMPLES / name
    if not rows:
        print(f"[SKIP] {name}: tidak ada baris")
        return 0
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[OK]   {name}: {len(rows):,} baris")
    return len(rows)


def main() -> None:
    export_csv(
        "hotspot_latest_sample.csv",
        "SELECT * FROM hotspot_latest USING SAMPLE 1000 ROWS",
    )
    export_csv(
        "agg_daily_province_sample.csv",
        """
        SELECT * FROM agg_daily_province
        WHERE date > (SELECT max(date) FROM agg_daily_province) - 30
        ORDER BY date DESC, hotspot_count DESC
        LIMIT 1000
        """,
    )
    export_csv(
        "agg_daily_grid_sample.csv",
        """
        SELECT * FROM agg_daily_grid
        WHERE date > (SELECT max(date) FROM agg_daily_grid) - 30
        ORDER BY date DESC, hotspot_count DESC
        LIMIT 1000
        """,
    )

    REPORTS.mkdir(parents=True, exist_ok=True)
    for name in (
        "pipeline_run_summary.json",
        "profiling_report.json",
        "serving_meta.json",
        "latest_preprocess.json",
    ):
        source = SERVING / name
        if source.exists():
            shutil.copy2(source, REPORTS / name)
            print(f"[OK]   reports/{name}")

    runs = SERVING / "runs"
    if runs.exists():
        for summary in sorted(runs.glob("*.json"))[-3:]:
            shutil.copy2(summary, REPORTS / f"run_{summary.name}")
            print(f"[OK]   reports/run_{summary.name}")

    manifest = {
        "dataset": "PantauApi - hotspot FIRMS Indonesia",
        "clean_rows": 2134784,
        "history": "2019-01-01 s/d 2026-11-16 (per pipeline_run_summary.json)",
        "full_data_location": "HDFS /karhutla/clean/hotspot + C:/karhutla-data/serving (tidak di Git)",
        "samples": sorted(p.name for p in SAMPLES.glob("*.csv")),
        "notes": "Sampel 1.000 baris per tabel, hanya untuk inspeksi cepat di GitHub.",
    }
    (REPORTS / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("[OK]   reports/manifest.json")


if __name__ == "__main__":
    main()
