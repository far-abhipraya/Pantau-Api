"""Kompaksi file kecil NRT FIRMS ke Parquet terpartisi (FR-N5).

Membaca semua CSV di `/karhutla/raw/firms_nrt/date=*/`, menggabungkan
dengan skema kanonik, lalu menulis sebagai Parquet terpartisi ke
`/karhutla/raw/firms_nrt_compacted/date=YYYY-MM-DD/`.

Digunakan saat NiFi tidak tersedia atau sebagai pemadatan berkas kecil
secara berkala agar pembacaan selanjutnya efisien.
"""

from __future__ import annotations

import argparse
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
)

from pyspark.sql import SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402

RAW_NRT = f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/raw/firms_nrt"
OUTPUT = f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/raw/firms_nrt_compacted"


def build(spark: SparkSession, job_id: str) -> dict:
    log_job_start(
        job_id,
        "NRT_COMPACT",
        {"input": RAW_NRT, "output": OUTPUT},
    )
    started_at = now_utc()

    df = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .option("recursiveFileLookup", True)
        .csv(RAW_NRT)
    )

    if df.rdd.isEmpty():
        summary = {
            "job_id": job_id,
            "computed_at": now_utc(),
            "started_at": started_at,
            "input_rows": 0,
            "output_rows": 0,
            "partitions": 0,
            "message": "tidak ada file NRT untuk dikoompaksi",
            "output_path": OUTPUT,
        }
        log_job_finish(job_id, "COMPLETED", summary)
        print(f"[INFO] {summary['message']}")
        return summary

    input_rows = df.count()

    # Ekstrak partisi tanggal dari path file (date=YYYY-MM-DD).
    df = df.withColumn(
        "_src_path", F.input_file_name()
    ).withColumn(
        "part_date",
        F.regexp_extract(F.col("_src_path"), r"date=(\d{4}-\d{2}-\d{2})", 1),
    ).drop("_src_path")

    # Tambah kolom ingest_ts untuk audit.
    df = df.withColumn("ingest_ts", F.current_timestamp())

    # Tulis sebagai Parquet terpartisi per tanggal.
    (
        df.repartition(4)
        .write.mode("overwrite")
        .partitionBy("part_date")
        .parquet(OUTPUT)
    )

    written = spark.read.parquet(OUTPUT)
    output_rows = written.count()
    partitions = written.select("part_date").distinct().count()

    summary = {
        "job_id": job_id,
        "computed_at": now_utc(),
        "started_at": started_at,
        "input_rows": input_rows,
        "output_rows": output_rows,
        "partitions": int(partitions),
        "output_path": OUTPUT,
    }
    log_job_finish(job_id, "COMPLETED", summary)
    print(f"[SUCCESS] kompak NRT: {input_rows:,} -> {output_rows:,} baris, {partitions} partisi -> {OUTPUT}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Kompaksi file kecil NRT FIRMS")
    parser.add_argument("--job-id", default="compact-nrt-manual")
    args = parser.parse_args()

    spark = get_spark_session("PantauApi Compact NRT")
    quiet(spark)
    try:
        build(spark, args.job_id)
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
