"""Profiling dataset hotspot mentah di HDFS (historis + NRT).

Menghasilkan ringkasan kualitas data ke `C:/karhutla-data/serving/profiling_report.json`.
Semua angka dihitung dari data nyata; tidak ada nilai contoh.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from common import (  # noqa: E402
    expand_paths,
    get_spark_session,
    log_job_finish,
    log_job_start,
    now_utc,
    quiet,
    settings,
    write_json,
)

from pyspark.sql import DataFrame, SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402

DEFAULT_INPUTS = [
    f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/raw/firms_hist/*.csv",
    f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/raw/firms_nrt/*.csv",
]
REPORT_PATH = Path(settings.SERVING_DIR) / "profiling_report.json"


def read_one(spark: SparkSession, path: str) -> DataFrame | None:
    try:
        df = (
            spark.read.option("header", "true")
            .option("inferSchema", "false")
            .option("mode", "PERMISSIVE")
            .csv(path)
        )
    except Exception as exc:
        print(f"[WARN] Lewati {path}: {exc}")
        return None
    if not df.columns:
        return None
    return df.toDF(*[c.strip().lower() for c in df.columns])


def read_raw(spark: SparkSession, paths: list[str]) -> DataFrame:
    files = expand_paths(spark, paths)
    print(f"[INFO] {len(files)} file input ditemukan")
    frames = [df for df in (read_one(spark, p) for p in files) if df is not None]
    if not frames:
        raise RuntimeError("Tidak ada file input yang bisa dibaca")
    combined = frames[0]
    for frame in frames[1:]:
        combined = combined.unionByName(frame, allowMissingColumns=True)
    return combined


def profile(
    spark: SparkSession,
    input_paths: list[str],
    output_path: str | Path,
    job_id: str,
) -> dict:
    log_job_start(job_id, "PROFILING", {"inputs": input_paths})
    raw = read_raw(spark, input_paths)
    total_rows = raw.count()
    print(f"[INFO] Total baris mentah: {total_rows:,}")

    has = set(raw.columns)

    def col(name: str):
        return F.col(name) if name in has else F.lit(None)

    latitude = col("latitude").try_cast("double")
    longitude = col("longitude").try_cast("double")
    df = (
        raw.withColumn("latitude", latitude)
        .withColumn("longitude", longitude)
        .withColumn("frp", col("frp").try_cast("double"))
        .withColumn("brightness", col("brightness").try_cast("double"))
        .withColumn(
            "brightness",
            F.coalesce(F.col("brightness"), col("bright_ti4").try_cast("double")),
        )
    )

    valid_coords = df.filter(
        F.col("latitude").isNotNull() & F.col("longitude").isNotNull()
    ).count()

    stats = df.select(
        F.min("acq_date").alias("min_date"),
        F.max("acq_date").alias("max_date"),
        F.min("frp").alias("min_frp"),
        F.max("frp").alias("max_frp"),
        F.avg("frp").alias("avg_frp"),
        F.stddev("frp").alias("std_frp"),
        F.min("brightness").alias("min_brightness"),
        F.max("brightness").alias("max_brightness"),
        F.avg("brightness").alias("avg_brightness"),
    ).collect()[0]

    satellites = [
        {"satellite": str(row["satellite"]), "count": int(row["count"])}
        for row in df.groupBy("satellite").count().orderBy(F.desc("count")).collect()
    ]
    confidence = [
        {"confidence": str(row["confidence"]), "count": int(row["count"])}
        for row in df.groupBy("confidence").count().orderBy(F.desc("count")).collect()
    ]

    # Statistik kolom (satu kali agregasi untuk null + perkiraan nilai unik).
    columns = df.columns
    agg_exprs = []
    for name in columns:
        agg_exprs.append(F.sum(F.col(name).isNull().cast("int")).alias(f"null__{name}"))
        agg_exprs.append(F.approx_count_distinct(F.col(name)).alias(f"dist__{name}"))
    column_row = df.agg(*agg_exprs).first()
    column_stats = []
    for name, dtype in df.dtypes:
        null_count = int(column_row[f"null__{name}"] or 0)
        column_stats.append(
            {
                "name": name,
                "dtype": dtype,
                "null_count": null_count,
                "null_percent": round(null_count / total_rows * 100, 2) if total_rows else 0.0,
                "distinct": int(column_row[f"dist__{name}"] or 0),
            }
        )

    # Duplikat pada kunci kanonik (PRD FR-N4).
    key = ["latitude", "longitude", "acq_date", "acq_time", "satellite"]
    duplicate_rows = 0
    if all(name in df.columns for name in key):
        duplicate_rows = int(
            df.groupBy(*key)
            .count()
            .filter(F.col("count") > 1)
            .agg(F.sum(F.col("count") - 1))
            .first()[0]
            or 0
        )

    # Distribusi ringkas (desil) untuk kolom metrik.
    distribution: dict[str, list[float]] = {}
    quantiles = [i / 10 for i in range(11)]
    for metric in ("frp", "brightness"):
        if metric in df.columns:
            values = df.select(metric).where(F.col(metric).isNotNull()).approxQuantile(
                metric, quantiles, 0.01
            )
            distribution[metric] = [round(float(v), 3) for v in (values or [])]

    report = {
        "timestamp": now_utc(),
        "job_id": job_id,
        "source_paths": input_paths,
        "total_rows": total_rows,
        "valid_coords_rows": valid_coords,
        "missing_coords": total_rows - valid_coords,
        "date_range": {
            "start": str(stats["min_date"]),
            "end": str(stats["max_date"]),
        },
        "frp_metrics": {
            "min": round(float(stats["min_frp"] or 0), 2),
            "max": round(float(stats["max_frp"] or 0), 2),
            "avg": round(float(stats["avg_frp"] or 0), 2),
            "std": round(float(stats["std_frp"] or 0), 2),
        },
        "brightness_metrics": {
            "min": round(float(stats["min_brightness"] or 0), 2),
            "max": round(float(stats["max_brightness"] or 0), 2),
            "avg": round(float(stats["avg_brightness"] or 0), 2),
        },
        "satellite_distribution": satellites,
        "confidence_distribution": confidence,
        "columns": column_stats,
        "duplicate_rows_on_key": duplicate_rows,
        "duplicate_key": key,
        "distribution_deciles": distribution,
    }
    write_json(output_path, report)
    log_job_finish(job_id, "COMPLETED", report)
    print(f"[SUCCESS] {output_path}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="*", default=DEFAULT_INPUTS)
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--job-id", default=None)
    args = parser.parse_args()
    job_id = args.job_id or f"profile-{now_utc().replace(':', '').replace('-', '')[:15]}"

    spark = None
    try:
        spark = get_spark_session("PantauApi-DataProfiling")
        quiet(spark)
        profile(spark, args.inputs or DEFAULT_INPUTS, args.output, job_id)
        return 0
    except Exception as exc:
        log_job_finish(job_id, "FAILED", {"error": repr(exc)})
        raise
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
