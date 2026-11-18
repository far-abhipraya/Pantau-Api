"""Fitur grid-day untuk model risiko karhutla (PRD Bagian 10).

Unit: (grid 0,25 derajat, tanggal). Label: ada hotspot nominal/tinggi pada
t+1..t+7. Fitur: hotspot 1/3/7/14/30 hari, rata-rata FRP 7 hari, hari sejak
hotspot terakhir, hotspot 8 sel tetangga 7 hari, waktu/lokasi, dan cuaca
(hujan 7/14/30 hari, hari kering, suhu, angin) bila tersedia.

Keluaran: HDFS `/karhutla/features/grid_daily` (semua tanggal, label null pada
7 hari terakhir karena horizon belum lengkap) dan ringkasan JSON di serving.
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
    write_json,
)

from pyspark.sql import DataFrame, Window  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402

GRID_STEP = 0.25
CLEAN_PATH = f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/clean/hotspot"
WEATHER_GLOB = f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/raw/weather"
FEATURES_PATH = f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/features/grid_daily"
SERVING_DIR = Path(settings.SERVING_DIR)

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
FEATURE_COLUMNS = (
    HOTSPOT_FEATURES + WEATHER_FEATURES + ["weather_missing"] + TIME_FEATURES + ["province_idx"]
)
NEIGHBOR_OFFSETS = [
    (dy, dx)
    for dy in (-GRID_STEP, 0.0, GRID_STEP)
    for dx in (-GRID_STEP, 0.0, GRID_STEP)
    if not (dy == 0.0 and dx == 0.0)
]


def _grid(df: DataFrame) -> DataFrame:
    return df.withColumn(
        "grid_lat", F.round(F.floor(F.col("latitude") / GRID_STEP) * GRID_STEP, 4)
    ).withColumn(
        "grid_lon", F.round(F.floor(F.col("longitude") / GRID_STEP) * GRID_STEP, 4)
    )


def _weather_features(spark, grids: DataFrame) -> DataFrame | None:
    """Cuaca harian per provinsi (stasiun terdekat).

    Dataset ERA5 lokal hanya 10 stasiun di Sumatera/Kalimantan (2022-2024);
    provinsi lain dan tanggal di luar cakupan akan bernilai null.
    """
    try:
        raw = spark.read.option("header", True).option("inferSchema", True).csv(WEATHER_GLOB)
        if "date" not in raw.columns:
            return None
    except Exception as exc:  # noqa: BLE001 - data opsional
        print(f"[WARN] cuaca tidak terbaca: {exc}")
        return None

    weather = (
        raw.select(
            F.to_date("date").alias("date"),
            F.col("station_name"),
            F.col("latitude").cast("double").alias("station_lat"),
            F.col("longitude").cast("double").alias("station_lon"),
            F.col("precipitation").cast("double").alias("precip"),
            F.col("temp_mean").cast("double").alias("temp"),
            F.col("wind_speed_max").cast("double").alias("wind"),
        )
        .filter(F.col("date").isNotNull() & F.col("station_name").isNotNull())
        .dropDuplicates(["date", "station_name"])
    )

    stations = weather.select("station_name", "station_lat", "station_lon").distinct()
    grid_prov = (
        grids.select("grid_lat", "grid_lon", "province")
        .filter(F.col("province").isNotNull() & (F.col("province") != "UNKNOWN"))
        .distinct()
    )
    if grid_prov.limit(1).count() == 0:
        print("[WARN] lookup provinsi grid kosong; fitur cuaca dilewati")
        return None

    distance = (
        stations.crossJoin(grid_prov)
        .withColumn("dlat", F.radians(F.col("grid_lat") - F.col("station_lat")))
        .withColumn("dlon", F.radians(F.col("grid_lon") - F.col("station_lon")))
        .withColumn(
            "a",
            F.pow(F.sin(F.col("dlat") / 2), 2)
            + F.cos(F.radians(F.col("station_lat")))
            * F.cos(F.radians(F.col("grid_lat")))
            * F.pow(F.sin(F.col("dlon") / 2), 2),
        )
        .withColumn("dist_km", F.lit(2 * 6371.0) * F.asin(F.sqrt(F.col("a"))))
    )
    mapping = (
        distance.groupBy("station_name")
        .agg(F.min(F.struct("dist_km", "province")).alias("nearest"))
        .select("station_name", F.col("nearest.province").alias("province"))
    )

    by_province = (
        weather.join(mapping, on="station_name", how="inner")
        .groupBy("province", "date")
        .agg(
            F.round(F.avg("precip"), 2).alias("precip"),
            F.round(F.avg("temp"), 2).alias("temp"),
            F.round(F.avg("wind"), 2).alias("wind"),
        )
    )

    window = Window.partitionBy("province").orderBy("date")
    trailing_7 = window.rowsBetween(-6, 0)
    trailing_14 = window.rowsBetween(-13, 0)
    trailing_30 = window.rowsBetween(-29, 0)
    all_past = window.rowsBetween(Window.unboundedPreceding, 0)

    by_province = (
        by_province.withColumn("rain_7d", F.round(F.sum("precip").over(trailing_7), 2))
        .withColumn("rain_14d", F.round(F.sum("precip").over(trailing_14), 2))
        .withColumn("rain_30d", F.round(F.sum("precip").over(trailing_30), 2))
        .withColumn("temp_7d", F.round(F.avg("temp").over(trailing_7), 2))
        .withColumn("wind_7d", F.round(F.avg("wind").over(trailing_7), 2))
        .withColumn(
            "last_wet_date",
            F.max(F.when(F.col("precip") >= 1.0, F.col("date"))).over(all_past),
        )
        .withColumn(
            "dry_streak",
            F.when(F.col("precip") >= 1.0, F.lit(0))
            .when(F.col("last_wet_date").isNull(), F.lit(9999))
            .otherwise(F.datediff(F.col("date"), F.col("last_wet_date")))
            .cast("double"),
        )
        .select(
            "province",
            "date",
            "rain_7d",
            "rain_14d",
            "rain_30d",
            "dry_streak",
            "temp_7d",
            "wind_7d",
        )
    )
    return by_province


def build(spark, job_id: str) -> dict:
    log_job_start(
        job_id,
        "FEATURES",
        {"input": CLEAN_PATH, "output": FEATURES_PATH, "grid_step": GRID_STEP},
    )
    started_at = now_utc()

    clean = (
        spark.read.parquet(CLEAN_PATH)
        .filter(F.col("confidence_level") != "low")
        .withColumn("date", F.to_date("acq_ts_utc"))
        .transform(_grid)
        .select("grid_lat", "grid_lon", "date", "province", F.col("frp").cast("double"))
        .filter(F.col("date").isNotNull())
    )

    daily = clean.groupBy("grid_lat", "grid_lon", "date").agg(
        F.count(F.lit(1)).cast("double").alias("hotspot_count"),
        F.sum("frp").alias("frp_sum"),
    )
    grids = clean.groupBy("grid_lat", "grid_lon").agg(
        F.max("province").alias("province")
    )
    bounds = daily.agg(F.min("date").alias("min_date"), F.max("date").alias("max_date")).collect()[0]
    if bounds["min_date"] is None:
        raise RuntimeError("clean/hotspot kosong setelah filter confidence")

    dates = spark.sql(
        "SELECT explode(sequence("
        f"to_date('{bounds['min_date']}'), to_date('{bounds['max_date']}'), interval 1 day"
        ")) AS date"
    )
    panel = (
        grids.crossJoin(dates)
        .join(daily, on=["grid_lat", "grid_lon", "date"], how="left")
        .fillna(0.0, subset=["hotspot_count", "frp_sum"])
        .withColumn("hotspot_count", F.col("hotspot_count").cast("double"))
    )

    window = Window.partitionBy("grid_lat", "grid_lon").orderBy("date")
    for days in (1, 3, 7, 14, 30):
        panel = panel.withColumn(
            f"cnt_{days}d",
            F.sum("hotspot_count").over(window.rowsBetween(-(days - 1), 0)),
        )
    panel = panel.withColumn(
        "frp_mean_7d",
        F.when(
            F.col("cnt_7d") > 0,
            F.sum("frp_sum").over(window.rowsBetween(-6, 0)) / F.col("cnt_7d"),
        ).otherwise(F.lit(0.0)),
    )
    panel = panel.withColumn(
        "last_hot_date",
        F.max(F.when(F.col("hotspot_count") > 0, F.col("date"))).over(
            window.rowsBetween(Window.unboundedPreceding, 0)
        ),
    ).withColumn(
        "days_since_last",
        F.when(F.col("last_hot_date").isNull(), F.lit(9999.0))
        .otherwise(F.datediff(F.col("date"), F.col("last_hot_date")))
        .cast("double"),
    )

    # Label horizon 7 hari (null pada 7 hari terakhir).
    future = window.rowsBetween(1, 7)
    panel = panel.withColumn(
        "future_count", F.sum("hotspot_count").over(future)
    ).withColumn(
        "label",
        F.when(F.col("date") <= F.date_sub(F.lit(bounds["max_date"]), 7), F.when(F.col("future_count") > 0, 1).otherwise(0)).cast("double"),
    )

    # Hotspot 8 sel tetangga (7 hari) - geser grid lalu agregasi.
    base7 = panel.select("grid_lat", "grid_lon", "date", "cnt_7d")
    neighbor_frames = []
    for dy, dx in NEIGHBOR_OFFSETS:
        neighbor_frames.append(
            base7.select(
                F.round(F.col("grid_lat") + F.lit(dy), 4).alias("grid_lat"),
                F.round(F.col("grid_lon") + F.lit(dx), 4).alias("grid_lon"),
                "date",
                "cnt_7d",
            )
        )
    neighbors = neighbor_frames[0]
    for frame in neighbor_frames[1:]:
        neighbors = neighbors.unionByName(frame)
    neighbors = neighbors.groupBy("grid_lat", "grid_lon", "date").agg(
        F.sum("cnt_7d").alias("nbr_7d")
    )
    panel = panel.join(neighbors, on=["grid_lat", "grid_lon", "date"], how="left").fillna(
        0.0, subset=["nbr_7d"]
    )

    panel = (
        panel.withColumn("month", F.month("date"))
        .withColumn("doy", F.dayofyear("date"))
        .withColumn("doy_sin", F.sin(2 * 3.141592653589793 * F.col("doy") / 365.25))
        .withColumn("doy_cos", F.cos(2 * 3.141592653589793 * F.col("doy") / 365.25))
    )

    weather = _weather_features(spark, grids)
    weather_available = weather is not None
    if weather is not None:
        panel = panel.join(weather, on=["province", "date"], how="left")
    else:
        for name in WEATHER_FEATURES:
            panel = panel.withColumn(name, F.lit(None).cast("double"))

    # Spark 4.2 menolak NaN di VectorAssembler; imputasi sentinel + indikator
    # cakupan cuaca agar model dapat membedakan nilai hilang.
    panel = panel.withColumn("weather_missing", F.col("rain_7d").isNull().cast("double"))
    panel = panel.fillna(-1.0, subset=WEATHER_FEATURES)

    panel = panel.withColumn(
        "province_idx", F.coalesce(F.col("province"), F.lit("UNKNOWN"))
    )

    output = panel.select(
        "grid_lat",
        "grid_lon",
        "date",
        "province",
        "province_idx",
        *HOTSPOT_FEATURES,
        *WEATHER_FEATURES,
        "weather_missing",
        "month",
        "doy",
        "doy_sin",
        "doy_cos",
        "label",
    )

    output.write.mode("overwrite").parquet(FEATURES_PATH)
    written = spark.read.parquet(FEATURES_PATH)
    total = written.count()
    labeled = written.filter(F.col("label").isNotNull()).count()
    grid_count = written.select("grid_lat", "grid_lon").distinct().count()
    weather_rows = (
        written.filter(F.col("weather_missing") == 0.0).count() if weather_available else 0
    )
    print(f"[INFO] features: {total:,} baris ({labeled:,} berlabel) -> {FEATURES_PATH}")

    summary = {
        "job_id": job_id,
        "computed_at": now_utc(),
        "started_at": started_at,
        "grid_step": GRID_STEP,
        "rows": total,
        "labeled_rows": labeled,
        "grids": grid_count,
        "date_start": str(bounds["min_date"]),
        "date_end": str(bounds["max_date"]),
        "weather_available": weather_available,
        "weather_rows": weather_rows,
        "feature_columns": FEATURE_COLUMNS,
        "weather_features": WEATHER_FEATURES,
        "output_path": FEATURES_PATH,
    }
    SERVING_DIR.mkdir(parents=True, exist_ok=True)
    write_json(SERVING_DIR / "features_summary.json", summary)
    log_job_finish(job_id, "COMPLETED", summary)
    print(f"[SUCCESS] {summary}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Bangun fitur grid-day")
    parser.add_argument("--job-id", default="features-manual")
    args = parser.parse_args()

    spark = get_spark_session("PantauApi Features")
    quiet(spark)
    try:
        build(spark, args.job_id)
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
