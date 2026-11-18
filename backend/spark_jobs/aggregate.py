"""Agregasi clean/hotspot -> tabel serving layer untuk halaman peta.

Keluaran (Parquet lokal di `settings.SERVING_DIR`, dibaca DuckDB):

- `hotspot_latest`            titik 7 hari terakhir (jendela maksimum peta)
- `grid_latest_1_0`           agregasi 1,0 derajat x jendela 24/48/168 jam
- `grid_latest_0_5`           agregasi 0,5 derajat x jendela 24/48/168 jam
- `grid_latest_0_25`          agregasi 0,25 derajat x jendela 24/48/168 jam
- `agg_daily_grid`            harian x grid 0,5 derajat (seluruh riwayat)
- `agg_daily_province`        harian x provinsi (seluruh riwayat)
- `serving_meta.json`         max acq_ts, jumlah baris, waktu hitung

Tabel `risk_prediction` baru diisi pada Fase 6 (ML); selama belum ada,
endpoint `/api/map/risk` mengembalikan `available: false`.
"""
from __future__ import annotations

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
    spark_ts_to_utc_iso,
    write_json,
)

from pyspark.sql import DataFrame, SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402

CLEAN_PATH = f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/clean/hotspot"
SERVING_DIR = Path(settings.SERVING_DIR)
WINDOWS = (24, 48, 168)
RESOLUTIONS = (("1_0", 1.0), ("0_5", 0.5), ("0_25", 0.25))
DAILY_GRID_STEP = 0.5

POINT_COLUMNS = [
    "latitude",
    "longitude",
    "acq_ts_utc",
    "acq_ts_wib",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence_level",
    "confidence_score",
    "frp",
    "brightness",
    "daynight",
    "grid_id",
    "province",
]


def _local_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _write(df: DataFrame, name: str, partitions: int = 1) -> dict:
    target = SERVING_DIR / name
    (df.coalesce(partitions).write.mode("overwrite").parquet(_local_uri(target)))
    rows = df.count()
    print(f"[INFO] {name}: {rows:,} baris -> {target}")
    return {"rows": rows, "path": str(target)}


def _daily_agg(df: DataFrame, group_cols: list[str]) -> DataFrame:
    return df.groupBy(*group_cols).agg(
        F.count(F.lit(1)).alias("hotspot_count"),
        F.sum(F.when(F.col("confidence_level") == "high", 1).otherwise(0)).alias(
            "high_count"
        ),
        F.sum(F.when(F.col("confidence_level") == "nominal", 1).otherwise(0)).alias(
            "nominal_count"
        ),
        F.sum(F.when(F.col("confidence_level") == "low", 1).otherwise(0)).alias(
            "low_count"
        ),
        F.round(F.sum("frp"), 2).alias("frp_sum"),
        F.round(F.max("frp"), 2).alias("frp_max"),
        F.round(F.avg("frp"), 2).alias("frp_avg"),
    )


def build(spark: SparkSession, job_id: str) -> dict:
    log_job_start(job_id, "AGGREGATION", {"input": CLEAN_PATH, "output": str(SERVING_DIR)})
    started_at = now_utc()
    SERVING_DIR.mkdir(parents=True, exist_ok=True)

    clean = spark.read.parquet(CLEAN_PATH)
    max_ts = clean.agg(F.max("acq_ts_utc")).collect()[0][0]
    if max_ts is None:
        raise RuntimeError("clean/hotspot kosong")
    total_rows = clean.count()
    print(f"[INFO] clean/hotspot: {total_rows:,} baris, max acq_ts {max_ts}")

    latest = clean.filter(
        F.col("acq_ts_utc") >= F.lit(max_ts) - F.expr("INTERVAL 168 HOURS")
    ).select(*[c for c in POINT_COLUMNS if c in clean.columns])
    # Titik dipakai endpoint bbox sehingga dipartisi menurut grid 0,5 derajat.
    latest = latest.withColumn("cell_lat", F.floor(F.col("latitude") / 0.5).cast("int"))
    outputs: dict[str, dict] = {}
    outputs["hotspot_latest"] = _write(latest, "hotspot_latest", partitions=4)

    windowed: dict[int, DataFrame] = {
        hours: clean.filter(
            F.col("acq_ts_utc") >= F.lit(max_ts) - F.expr(f"INTERVAL {hours} HOURS")
        )
        for hours in WINDOWS
    }

    for suffix, step in RESOLUTIONS:
        frames = []
        for hours, source in windowed.items():
            cells = (
                source.withColumn(
                    "grid_lat", F.round(F.floor(F.col("latitude") / step) * step, 4)
                )
                .withColumn(
                    "grid_lon", F.round(F.floor(F.col("longitude") / step) * step, 4)
                )
                .groupBy("grid_lat", "grid_lon")
                .agg(
                    F.count(F.lit(1)).alias("hotspot_count"),
                    F.sum(
                        F.when(F.col("confidence_level") == "high", 1).otherwise(0)
                    ).alias("high_count"),
                    F.sum(
                        F.when(F.col("confidence_level") == "nominal", 1).otherwise(0)
                    ).alias("nominal_count"),
                    F.sum(
                        F.when(F.col("confidence_level") == "low", 1).otherwise(0)
                    ).alias("low_count"),
                    F.round(F.sum("frp"), 2).alias("frp_sum"),
                    F.round(F.max("frp"), 2).alias("frp_max"),
                    F.round(F.avg("frp"), 2).alias("frp_avg"),
                    F.max("province").alias("province"),
                )
                .withColumn("window_hours", F.lit(hours))
                .withColumn("cell_lat", F.col("grid_lat") + F.lit(step / 2))
                .withColumn("cell_lon", F.col("grid_lon") + F.lit(step / 2))
            )
            frames.append(cells)
        grid = frames[0]
        for frame in frames[1:]:
            grid = grid.unionByName(frame)
        grid = grid.withColumn("resolution", F.lit(step)).withColumn(
            "updated_at", F.lit(max_ts)
        )
        outputs[f"grid_latest_{suffix}"] = _write(
            grid, f"grid_latest_{suffix}", partitions=1
        )

    daily_grid = (
        clean.withColumn(
            "grid_lat",
            F.round(F.floor(F.col("latitude") / DAILY_GRID_STEP) * DAILY_GRID_STEP, 4),
        )
        .withColumn(
            "grid_lon",
            F.round(F.floor(F.col("longitude") / DAILY_GRID_STEP) * DAILY_GRID_STEP, 4),
        )
        .withColumn("date", F.to_date("acq_ts_utc"))
        .transform(lambda df: _daily_agg(df, ["date", "grid_lat", "grid_lon"]))
        .withColumn("province", F.lit(None).cast("string"))
    )
    # Provinsi per grid (modus) diambil dari clean agar tetap akurat.
    province_join = (
        clean.withColumn(
            "grid_lat",
            F.round(F.floor(F.col("latitude") / DAILY_GRID_STEP) * DAILY_GRID_STEP, 4),
        )
        .withColumn(
            "grid_lon",
            F.round(F.floor(F.col("longitude") / DAILY_GRID_STEP) * DAILY_GRID_STEP, 4),
        )
        .groupBy("grid_lat", "grid_lon")
        .agg(F.max("province").alias("province"))
    )
    daily_grid = daily_grid.drop("province").join(
        province_join, on=["grid_lat", "grid_lon"], how="left"
    )
    outputs["agg_daily_grid"] = _write(daily_grid, "agg_daily_grid", partitions=4)

    daily_province = (
        clean.withColumn("date", F.to_date("acq_ts_utc"))
        .transform(lambda df: _daily_agg(df, ["date", "province"]))
        .orderBy("date", "province")
    )
    outputs["agg_daily_province"] = _write(
        daily_province, "agg_daily_province", partitions=1
    )

    meta = {
        "job_id": job_id,
        "computed_at": now_utc(),
        "started_at": started_at,
        "source_rows": total_rows,
        "max_acq_ts": spark_ts_to_utc_iso(max_ts),
        "windows_hours": list(WINDOWS),
        "resolutions": [step for _, step in RESOLUTIONS],
        "tables": outputs,
    }
    write_json(SERVING_DIR / "serving_meta.json", meta)
    log_job_finish(job_id, "COMPLETED", meta)
    print(f"[SUCCESS] {SERVING_DIR / 'serving_meta.json'}")
    return meta


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", default=None)
    args = parser.parse_args()
    job_id = args.job_id or f"aggregate-{now_utc().replace(':', '').replace('-', '')[:15]}"

    spark = None
    try:
        spark = get_spark_session("PantauApi-Aggregate")
        quiet(spark)
        build(spark, job_id)
        return 0
    except Exception as exc:
        log_job_finish(job_id, "FAILED", {"error": repr(exc)})
        print(f"[FAIL] {exc!r}")
        raise
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
