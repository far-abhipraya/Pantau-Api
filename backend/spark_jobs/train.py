"""Latih model risiko 7 hari (RandomForest + GBT) dengan split berbasis waktu.

Input : HDFS `/karhutla/features/grid_daily`
Output: model Spark ML di `/karhutla/models/<versi>`, metrik + feature
importance di serving layer (`model_metrics.json`), perbandingan baseline
persistensi. Tidak ada split acak.
"""
from __future__ import annotations

import argparse
import json
import sys
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

from pyspark.ml import Pipeline, PipelineModel  # noqa: E402
from pyspark.ml.classification import GBTClassifier, RandomForestClassifier  # noqa: E402
from pyspark.ml.evaluation import BinaryClassificationEvaluator  # noqa: E402
from pyspark.ml.feature import StringIndexer, VectorAssembler  # noqa: E402
from pyspark.ml.functions import vector_to_array  # noqa: E402
from pyspark.sql import DataFrame, SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402

FEATURES_PATH = f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/features/grid_daily"
MODELS_PATH = f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/models"
SERVING_DIR = Path(settings.SERVING_DIR)
TRAIN_END = "2022-12-31"
VAL_START = "2023-01-01"
VAL_END = "2023-12-31"
TEST_START = "2024-01-01"

HOTSPOT_FEATURES = [
    "cnt_1d",
    "cnt_3d",
    "cnt_7d",
    "cnt_14d",
    "cnt_30d",
    "frp_mean_7d",
    "days_since_last",
    "nbr_7d",
]
WEATHER_FEATURES = ["rain_7d", "rain_14d", "rain_30d", "dry_streak", "temp_7d", "wind_7d"]
TIME_FEATURES = ["month", "doy_sin", "doy_cos", "grid_lat", "grid_lon"]
EXTRA_FEATURES = ["weather_missing"]
ALL_FEATURES = (
    HOTSPOT_FEATURES + WEATHER_FEATURES + EXTRA_FEATURES + TIME_FEATURES + ["province_idx"]
)

FEATURE_LABELS = {
    "cnt_1d": "Hotspot 1 hari",
    "cnt_3d": "Hotspot 3 hari",
    "cnt_7d": "Hotspot 7 hari",
    "cnt_14d": "Hotspot 14 hari",
    "cnt_30d": "Hotspot 30 hari",
    "frp_mean_7d": "Rata-rata FRP 7 hari",
    "days_since_last": "Hari sejak hotspot terakhir",
    "nbr_7d": "Hotspot 8 sel tetangga (7 hari)",
    "rain_7d": "Hujan 7 hari (mm)",
    "rain_14d": "Hujan 14 hari (mm)",
    "rain_30d": "Hujan 30 hari (mm)",
    "dry_streak": "Hari kering berturut-turut",
    "temp_7d": "Suhu rata-rata 7 hari (C)",
    "wind_7d": "Angin rata-rata 7 hari",
    "weather_missing": "Cuaca tidak tersedia (indikator)",
    "month": "Bulan",
    "doy_sin": "Siklus tahunan (sin)",
    "doy_cos": "Siklus tahunan (cos)",
    "grid_lat": "Lintang grid",
    "grid_lon": "Bujur grid",
    "province_idx": "Provinsi (index)",
    "province_code": "Provinsi (kategori)",
}


def _metrics(pred: DataFrame, label_col: str, score_col: str) -> dict:
    scored = pred.select(
        F.col(score_col).cast("double").alias("score"),
        F.col(label_col).cast("double").alias("label"),
        F.col("prediction").cast("double").alias("prediction"),
    )
    roc_evaluator = BinaryClassificationEvaluator(
        labelCol="label", rawPredictionCol="score", metricName="areaUnderROC"
    )
    pr_evaluator = BinaryClassificationEvaluator(
        labelCol="label", rawPredictionCol="score", metricName="areaUnderPR"
    )
    auc_roc = float(roc_evaluator.evaluate(scored))
    auc_pr = float(pr_evaluator.evaluate(scored))

    row = scored.agg(
        F.sum(
            F.when((F.col("prediction") == 1.0) & (F.col("label") == 1.0), 1).otherwise(0)
        ).alias("tp"),
        F.sum(
            F.when((F.col("prediction") == 1.0) & (F.col("label") == 0.0), 1).otherwise(0)
        ).alias("fp"),
        F.sum(
            F.when((F.col("prediction") == 0.0) & (F.col("label") == 1.0), 1).otherwise(0)
        ).alias("fn"),
        F.sum(
            F.when((F.col("prediction") == 0.0) & (F.col("label") == 0.0), 1).otherwise(0)
        ).alias("tn"),
    ).collect()[0]
    tp, fp, fn, tn = (int(row[name]) for name in ("tp", "fp", "fn", "tn"))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "auc_roc": round(auc_roc, 4),
        "auc_pr": round(auc_pr, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "rows": tp + fp + fn + tn,
    }


def _add_weights(train: DataFrame) -> tuple[DataFrame, float]:
    counts = {
        int(row["label"]): int(row["count"])
        for row in train.groupBy(F.col("label").cast("int").alias("label")).count().collect()
    }
    positives = counts.get(1, 0)
    negatives = counts.get(0, 0)
    positive_weight = min(50.0, (negatives / positives) if positives else 1.0)
    weighted = train.withColumn(
        "weight",
        F.when(F.col("label") == 1.0, F.lit(positive_weight)).otherwise(F.lit(1.0)),
    )
    return weighted, positive_weight


def _build_pipeline(algorithm: str) -> Pipeline:
    indexer = StringIndexer(
        inputCol="province_idx", outputCol="province_code", handleInvalid="keep"
    )
    assembler = VectorAssembler(
        inputCols=[*HOTSPOT_FEATURES, *WEATHER_FEATURES, *EXTRA_FEATURES, *TIME_FEATURES, "province_code"],
        outputCol="features",
        handleInvalid="keep",
    )
    if algorithm == "gbt":
        classifier = GBTClassifier(
            labelCol="label",
            featuresCol="features",
            weightCol="weight",
            maxIter=40,
            maxDepth=4,
            maxBins=64,
            stepSize=0.1,
            seed=42,
        )
    else:
        classifier = RandomForestClassifier(
            labelCol="label",
            featuresCol="features",
            weightCol="weight",
            numTrees=80,
            maxDepth=7,
            minInstancesPerNode=5,
            maxBins=64,
            featureSubsetStrategy="sqrt",
            seed=42,
        )
    return Pipeline(stages=[indexer, assembler, classifier])


def _importance(model: PipelineModel) -> list[dict]:
    assembler: VectorAssembler = model.stages[1]
    classifier = model.stages[-1]
    values = list(classifier.featureImportances.toArray())
    return sorted(
        [
            {
                "feature": name,
                "label": FEATURE_LABELS.get(name, name),
                "value": round(float(value), 6),
            }
            for name, value in zip(assembler.getInputCols(), values)
        ],
        key=lambda item: item["value"],
        reverse=True,
    )


def _persistence_baseline(test: DataFrame) -> dict:
    baseline = test.withColumn(
        "score", F.when(F.col("cnt_7d") > 0, F.lit(1.0)).otherwise(F.lit(0.0))
    ).withColumn("prediction", F.col("score"))
    return _metrics(baseline, "label", "score")


def build(spark: SparkSession, job_id: str, algorithm: str = "rf") -> dict:
    log_job_start(
        job_id,
        "ML_TRAIN",
        {"input": FEATURES_PATH, "algorithm": algorithm, "models_path": MODELS_PATH},
    )
    started_at = now_utc()
    version = f"{algorithm}-{started_at.replace('-', '').replace(':', '').replace('+0000', 'Z')}"
    version = version.replace("T", "-")[:20]

    features = spark.read.parquet(FEATURES_PATH).filter(F.col("label").isNotNull())
    train = features.filter(F.col("date") <= F.lit(TRAIN_END))
    validation = features.filter(
        (F.col("date") >= F.lit(VAL_START)) & (F.col("date") <= F.lit(VAL_END))
    )
    test = features.filter(F.col("date") >= F.lit(TEST_START))
    if train.limit(1).count() == 0 or test.limit(1).count() == 0:
        raise RuntimeError("split waktu kosong; periksa rentang data fitur")

    weighted_train, positive_weight = _add_weights(train)
    pipeline = _build_pipeline(algorithm)
    model = pipeline.fit(weighted_train)

    rf_metrics = _metrics(model.transform(test).withColumn("score", vector_to_array("probability")[1]), "label", "score")
    gbt_metrics = None
    if algorithm == "rf":
        # Bandingkan GBT pada data yang sama (pembanding PRD).
        gbt_model = _build_pipeline("gbt").fit(weighted_train)
        gbt_metrics = _metrics(gbt_model.transform(test).withColumn("score", vector_to_array("probability")[1]), "label", "score")
    baseline = _persistence_baseline(test)

    model_path = f"{MODELS_PATH}/{version}"
    model.write().overwrite().save(model_path)

    rows = {
        "train": train.count(),
        "validation": validation.count(),
        "test": test.count(),
        "positive_weight": round(positive_weight, 3),
    }
    metrics = {
        "job_id": job_id,
        "version": version,
        "algorithm": algorithm,
        "trained_at": now_utc(),
        "started_at": started_at,
        "model_path": model_path,
        "split": {"train_end": TRAIN_END, "validation": "2023", "test_start": TEST_START},
        "rows": rows,
        "label_rate": {
            "train": round(float(train.agg(F.avg("label")).collect()[0][0] or 0), 4),
            "test": round(float(test.agg(F.avg("label")).collect()[0][0] or 0), 4),
        },
        "metrics": {
            "model": rf_metrics,
            "baseline_persistence": baseline,
            **({"gbt": gbt_metrics} if gbt_metrics else {}),
        },
        "feature_importance": _importance(model),
        "features": ALL_FEATURES,
        "weather_features_available": bool(
            features.filter(F.col("weather_missing") == 0.0).limit(1).count()
        ),
        "limitations": [
            "Fitur cuaca ERA5 hanya mencakup 10 stasiun Sumatera/Kalimantan pada 2022-2024; di luar cakupan diimputasi -1 dengan indikator weather_missing.",
            "Grid yang belum pernah memiliki hotspot historis tidak diprediksi.",
            "Skor risiko adalah estimasi statistik, bukan kepastian kebakaran.",
        ],
    }

    SERVING_DIR.mkdir(parents=True, exist_ok=True)
    write_json(SERVING_DIR / "model_metrics.json", metrics)
    write_json(
        SERVING_DIR / "model_manifest.json",
        {
            "version": version,
            "algorithm": algorithm,
            "model_path": model_path,
            "feature_columns": metrics["features"],
            "trained_at": metrics["trained_at"],
        },
    )
    # Salinan metrik di HDFS agar dapat diaudit bersama model.
    spark.createDataFrame([(json.dumps(metrics),)]).coalesce(1).write.mode("overwrite").text(
        f"{MODELS_PATH}/{version}_metrics"
    )

    log_job_finish(job_id, "COMPLETED", metrics)
    print(f"[SUCCESS] model {version} -> {model_path}")
    print(f"[METRICS] model={rf_metrics} baseline={baseline}")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Latih model risiko 7 hari")
    parser.add_argument("--job-id", default="train-manual")
    parser.add_argument("--algorithm", choices=("rf", "gbt"), default="rf")
    args = parser.parse_args()

    spark = get_spark_session("PantauApi Train")
    quiet(spark)
    try:
        build(spark, args.job_id, args.algorithm)
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
