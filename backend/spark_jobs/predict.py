"""Prediksi risiko 7 hari untuk grid terakhir (PRD Bagian 10).

Memuat model dari `model_manifest.json`, membangun fitur tanggal terakhir dari
HDFS, lalu menulis tabel serving `risk_prediction` (Parquet lokal) yang dibaca
endpoint `/api/map/risk` dan panel Prediksi ML.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

JOB_DIR = Path(__file__).resolve().parent
if str(JOB_DIR) not in sys.path:
    sys.path.insert(0, str(JOB_DIR))

from common import (  # noqa: E402
    get_spark_session,
    log_job_finish,
    log_job_start,
    now_utc,
    quiet,
    settings,
    write_json,
)

from pyspark.ml import PipelineModel  # noqa: E402
from pyspark.ml.functions import vector_to_array  # noqa: E402
from pyspark.sql import SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402

FEATURES_PATH = f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/features/grid_daily"
SERVING_DIR = Path(settings.SERVING_DIR)
RISK_DIR = SERVING_DIR / "risk_prediction"
HORIZON_DAYS = 7


def _category(score_column: str):
    return (
        F.when(F.col(score_column) >= 0.75, F.lit("sangat tinggi"))
        .when(F.col(score_column) >= 0.5, F.lit("tinggi"))
        .when(F.col(score_column) >= 0.25, F.lit("sedang"))
        .otherwise(F.lit("rendah"))
    )


def build(spark: SparkSession, job_id: str, model_path: str | None = None) -> dict:
    manifest_path = SERVING_DIR / "model_manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("model_manifest.json tidak ada; jalankan train.py lebih dulu")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    model_path = model_path or manifest["model_path"]
    version = manifest["version"]

    log_job_start(job_id, "ML_PREDICT", {"model": model_path, "output": str(RISK_DIR)})
    started_at = now_utc()

    model = PipelineModel.load(model_path)
    latest_date = (
        spark.read.parquet(FEATURES_PATH).agg(F.max("date")).collect()[0][0]
    )
    if latest_date is None:
        raise RuntimeError("features/grid_daily kosong")
    latest = spark.read.parquet(FEATURES_PATH).filter(F.col("date") == F.lit(latest_date))
    predicted = model.transform(latest)

    risk = (
        predicted.withColumn("risk_score", F.round(vector_to_array("probability")[1], 6))
        .withColumn("risk_category", _category("risk_score"))
        .withColumn(
            "grid_id",
            F.concat_ws(
                "_",
                F.format_number(F.col("grid_lat"), 2),
                F.format_number(F.col("grid_lon"), 2),
            ),
        )
        .withColumn("lat", F.col("grid_lat") + F.lit(0.125))
        .withColumn("lon", F.col("grid_lon") + F.lit(0.125))
        .withColumn("target_date", F.date_add(F.col("date"), HORIZON_DAYS))
        .withColumn("horizon_days", F.lit(HORIZON_DAYS))
        .withColumn("model_version", F.lit(version))
        .withColumn("predicted_at", F.lit(now_utc()))
        .select(
            "grid_id",
            "lat",
            "lon",
            "target_date",
            "horizon_days",
            "risk_score",
            "risk_category",
            "model_version",
            "predicted_at",
            "province",
            "cnt_7d",
        )
    )

    RISK_DIR.mkdir(parents=True, exist_ok=True)
    (
        risk.coalesce(4)
        .write.mode("overwrite")
        .parquet(RISK_DIR.resolve().as_uri())
    )

    rows = risk.count()
    counts = {
        row["risk_category"]: int(row["count"])
        for row in risk.groupBy("risk_category").count().collect()
    }
    summary = {
        "job_id": job_id,
        "computed_at": now_utc(),
        "started_at": started_at,
        "model_version": version,
        "model_path": model_path,
        "feature_date": str(latest_date),
        "target_date": str(latest_date + timedelta(days=HORIZON_DAYS)),
        "horizon_days": HORIZON_DAYS,
        "rows": rows,
        "categories": counts,
        "max_score": float(risk.agg(F.max("risk_score")).collect()[0][0] or 0),
        "mean_score": round(float(risk.agg(F.avg("risk_score")).collect()[0][0] or 0), 4),
        "thresholds": {"rendah": "<0,25", "sedang": "<0,5", "tinggi": "<0,75", "sangat tinggi": ">=0,75"},
        "output": str(RISK_DIR),
    }
    write_json(SERVING_DIR / "risk_summary.json", summary)
    log_job_finish(job_id, "COMPLETED", summary)
    print(f"[SUCCESS] {rows:,} grid diprediksi -> {RISK_DIR}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Prediksi risiko 7 hari")
    parser.add_argument("--job-id", default="predict-manual")
    parser.add_argument("--model-path", default=None)
    args = parser.parse_args()

    spark = get_spark_session("PantauApi Predict")
    quiet(spark)
    try:
        build(spark, args.job_id, args.model_path)
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
