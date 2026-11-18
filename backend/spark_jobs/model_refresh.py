"""Orkestrator Fase 6: fitur -> latih -> prediksi dalam satu sesi Spark.

Dipakai tombol "Perbarui prediksi" di halaman Analitik. Setiap langkah menulis
keluaran ke HDFS/serving layer sehingga dapat diaudit terpisah.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

JOB_DIR = Path(__file__).resolve().parent
if str(JOB_DIR) not in sys.path:
    sys.path.insert(0, str(JOB_DIR))

import features  # noqa: E402
import predict  # noqa: E402
import train  # noqa: E402
from common import (  # noqa: E402
    get_spark_session,
    log_job_finish,
    log_job_start,
    now_utc,
    quiet,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitur + latih + prediksi")
    parser.add_argument("--job-id", default="model-refresh-manual")
    parser.add_argument("--algorithm", choices=("rf", "gbt"), default="rf")
    args = parser.parse_args()

    spark = get_spark_session("PantauApi Model Refresh")
    quiet(spark)
    started_at = now_utc()
    log_job_start(args.job_id, "ML_REFRESH", {"algorithm": args.algorithm})
    try:
        features_summary = features.build(spark, f"{args.job_id}-features")
        spark.catalog.clearCache()
        metrics = train.build(spark, f"{args.job_id}-train", args.algorithm)
        spark.catalog.clearCache()
        risk = predict.build(spark, f"{args.job_id}-predict")
        summary = {
            "job_id": args.job_id,
            "started_at": started_at,
            "finished_at": now_utc(),
            "features": {
                "rows": features_summary["rows"],
                "labeled_rows": features_summary["labeled_rows"],
                "weather_available": features_summary["weather_available"],
            },
            "model": {
                "version": metrics["version"],
                "metrics": metrics["metrics"],
            },
            "risk": {
                "rows": risk["rows"],
                "categories": risk["categories"],
                "target_date": risk["target_date"],
            },
        }
        log_job_finish(args.job_id, "COMPLETED", summary)
        print(f"[SUCCESS] model refresh: {summary}")
    except Exception as exc:  # noqa: BLE001
        log_job_finish(args.job_id, "FAILED", {"error": repr(exc)})
        raise
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
