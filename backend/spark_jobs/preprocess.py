"""Pre-processing hotspot mentah -> Parquet clean sesuai skema kanonik PRD 11.1.

Langkah default (tanpa `--config`) identik dengan hasil yang sudah terverifikasi:
1. Baca raw FIRMS historis dan NRT (VIIRS + MODIS), satukan skema.
2. Normalisasi kolom (brightness, confidence, satelit/instrumen, waktu UTC/WIB).
3. Filter koordinat valid + bbox Indonesia.
4. Hitung grid_id 0,25 derajat; join provinsi via lookup poligon.
5. Normalisasi Min-Max frp/brightness; deduplikasi kunci
   (latitude, longitude, acq_date, acq_time, satellite).
6. Tulis Parquet berpartisi year/month ke HDFS + laporan job (funnel per langkah).

`--config <json>` menyalakan opsi stepper (cleaning/transform/normalization/spatial)
dan mencatat konfigurasi pada laporan; lihat `GET /api/preprocessing/config-schema`.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Pastikan `common` dan paket `app` bisa diimpor saat dijalankan via spark-submit.
JOB_DIR = Path(__file__).resolve().parent
if str(JOB_DIR) not in sys.path:
    sys.path.insert(0, str(JOB_DIR))

from common import (  # noqa: E402
    CANONICAL_HOTSPOT_COLUMNS,
    expand_paths,
    get_spark_session,
    log_job_finish,
    log_job_start,
    now_utc,
    quiet,
    settings,
    write_json,
)

from pyspark.sql import DataFrame, SparkSession, Window  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402
from pyspark.storagelevel import StorageLevel  # noqa: E402

DEFAULT_INPUTS = [
    f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/raw/firms_hist/*.csv",
    f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/raw/firms_nrt/*.csv",
]
CLEAN_OUTPUT = f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/clean/hotspot"
SUMMARY_PATH = Path(settings.SERVING_DIR) / "pipeline_run_summary.json"
LATEST_PATH = Path(settings.SERVING_DIR) / "latest_preprocess.json"
PROVINCE_STEP = 0.02
NUMERIC_FILL_COLUMNS = ("frp", "brightness", "confidence_score")
CONFIDENCE_RANK = {"low": 1, "nominal": 2, "high": 3}

DEFAULT_CONFIG: dict = {
    "cleaning": {
        "drop_duplicates": True,
        "filter_bbox": True,
        "min_confidence": "low",
        "null_strategy": "constant",
        "null_constant": 0.0,
        "outlier_method": "none",
        "outlier_column": "frp",
        "outlier_threshold": 1.5,
    },
    "transform": {"time_parts": True},
    "normalization": {"method": "minmax"},
    "spatial": {"grid_id": True, "province": True},
}


def load_config(path: str | Path | None) -> dict:
    """Gabung konfigurasi dari file dengan default (tanpa mengubah default)."""
    config = json.loads(json.dumps(DEFAULT_CONFIG))  # salinan dalam
    if not path:
        return config
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    incoming = payload.get("config", payload) if isinstance(payload, dict) else {}
    for section, values in (incoming or {}).items():
        if isinstance(values, dict) and isinstance(config.get(section), dict):
            config[section].update(values)
        else:
            config[section] = values
    return config


def read_one(spark: SparkSession, path: str) -> DataFrame | None:
    try:
        df = (
            spark.read.option("header", "true")
            .option("inferSchema", "false")
            .option("mode", "PERMISSIVE")
            .csv(path)
        )
    except Exception as exc:  # path kosong / tidak ada file
        print(f"[WARN] Lewati input {path}: {exc}")
        return None
    if not df.columns:
        print(f"[WARN] Lewati input {path}: tidak ada kolom")
        return None
    # Header FIRMS tidak selalu konsisten huruf besar/kecil.
    df = df.toDF(*[c.strip().lower() for c in df.columns])
    return df.withColumn("source_file", F.input_file_name())


def read_raw(spark: SparkSession, paths: list[str]) -> DataFrame:
    # Satu file per pembacaan: header VIIRS dan MODIS berbeda, sehingga glob
    # tunggal akan gagal menyatukan skema.
    files = expand_paths(spark, paths)
    print(f"[INFO] {len(files)} file input ditemukan")
    frames = [df for df in (read_one(spark, p) for p in files) if df is not None]
    if not frames:
        raise RuntimeError("Tidak ada file input yang bisa dibaca")
    combined = frames[0]
    for frame in frames[1:]:
        combined = combined.unionByName(frame, allowMissingColumns=True)
    return combined


def bbox_filter(df: DataFrame) -> DataFrame:
    bbox = settings.BBOX_INDONESIA
    return df.filter(
        F.col("latitude").between(bbox["min_lat"], bbox["max_lat"])
        & F.col("longitude").between(bbox["min_lon"], bbox["max_lon"])
    )


def normalize(df: DataFrame) -> DataFrame:
    present = set(df.columns)

    def col(name: str, typ: str = "string"):
        return F.col(name) if name in present else F.lit(None).cast(typ)

    latitude = col("latitude").try_cast("double")
    longitude = col("longitude").try_cast("double")
    frp = F.coalesce(col("frp").try_cast("double"), F.lit(0.0))
    brightness = F.coalesce(
        col("bright_ti4").try_cast("double"),
        col("brightness").try_cast("double"),
    )
    brightness_2 = F.coalesce(
        col("bright_ti5").try_cast("double"),
        col("bright_t31").try_cast("double"),
    )

    sat_raw = F.upper(F.trim(col("satellite")))
    satellite = (
        F.when(sat_raw.isin("N", "SNPP"), "SNPP")
        .when(sat_raw.isin("1", "N20", "NOAA20", "NOAA-20"), "NOAA-20")
        .when(sat_raw.isin("2", "N21", "NOAA21", "NOAA-21"), "NOAA-21")
        .when(sat_raw.isin("T", "TERRA"), "Terra")
        .when(sat_raw.isin("A", "AQUA"), "Aqua")
        .otherwise(F.upper(F.trim(sat_raw)))
    )
    is_viirs = col("bright_ti4", "double").isNotNull() | satellite.isin(
        "SNPP", "NOAA-20", "NOAA-21"
    )
    instrument = F.when(is_viirs, F.lit("VIIRS")).otherwise(F.lit("MODIS"))

    acq_date = F.try_to_date(col("acq_date"), "yyyy-MM-dd")
    digits = F.regexp_replace(col("acq_time"), "[^0-9]", "")
    # FIRMS kadang memberi jam tanpa nol depan ("56" = 00:56).
    acq_time = F.when(
        (F.length(digits) >= 1) & (F.length(digits) <= 4), F.lpad(digits, 4, "0")
    )
    acq_ts_utc = F.try_to_timestamp(
        F.concat_ws(" ", F.date_format(acq_date, "yyyy-MM-dd"), acq_time),
        F.lit("yyyy-MM-dd HHmm"),
    )
    acq_ts_wib = F.from_utc_timestamp(acq_ts_utc, "Asia/Jakarta")

    conf_str = F.lower(F.trim(col("confidence")))
    conf_num = conf_str.try_cast("double")
    confidence_level = (
        F.when(conf_str.isin("h", "high"), "high")
        .when(conf_str.isin("l", "low"), "low")
        .when(conf_str.isin("n", "nominal"), "nominal")
        .when(conf_num >= 80, "high")
        .when(conf_num >= 30, "nominal")
        .when(conf_num >= 0, "low")
        .otherwise("nominal")
    )
    confidence_score = (
        F.when(conf_num.isNotNull(), conf_num)
        .when(confidence_level == "high", F.lit(95.0))
        .when(confidence_level == "nominal", F.lit(70.0))
        .otherwise(F.lit(30.0))
    )

    grid_lat = F.round(latitude / 0.25) * 0.25 + F.lit(0.0)
    grid_lon = F.round(longitude / 0.25) * 0.25 + F.lit(0.0)
    grid_id = F.concat(
        F.lit("grid_"),
        F.format_number(grid_lat, 2),
        F.lit("_"),
        F.format_number(grid_lon, 2),
    )

    ingest_path = (
        F.when(F.col("source_file").contains("/firms_nrt/"), F.lit("nifi"))
        .otherwise(F.lit("auto"))
    )

    normalized = (
        df.withColumn("latitude", latitude)
        .withColumn("longitude", longitude)
        .withColumn("frp", frp)
        .withColumn("brightness", brightness)
        .withColumn("brightness_2", brightness_2)
        .withColumn("satellite", satellite)
        .withColumn("instrument", instrument)
        .withColumn("acq_date", acq_date)
        .withColumn("acq_time", acq_time)
        .withColumn("acq_ts_utc", acq_ts_utc)
        .withColumn("acq_ts_wib", acq_ts_wib)
        .withColumn("confidence_level", confidence_level)
        .withColumn("confidence_score", confidence_score)
        .withColumn("daynight", F.upper(F.trim(col("daynight"))))
        .withColumn("type", col("type").try_cast("int"))
        .withColumn("grid_lat", grid_lat)
        .withColumn("grid_lon", grid_lon)
        .withColumn("grid_id", grid_id)
        .withColumn("ingest_path", ingest_path)
    )
    return normalized


def apply_null_strategy(df: DataFrame, strategy: str, constant: float) -> tuple[DataFrame, dict]:
    """Isi/buang nilai kosong pada kolom metrik numerik (FR-P2)."""
    info: dict = {"strategy": strategy, "filled": {}}
    if strategy == "drop":
        before = df.count()
        df = df.dropna(subset=list(NUMERIC_FILL_COLUMNS))
        info["dropped_rows"] = before - df.count()
        return df, info

    if strategy == "constant":
        # Satu kali agregasi untuk menghitung nilai kosong per kolom.
        missing_row = df.select(
            *[F.sum(F.col(c).isNull().cast("int")).alias(c) for c in NUMERIC_FILL_COLUMNS]
        ).first()
        filled = {c: int(missing_row[c] or 0) for c in NUMERIC_FILL_COLUMNS}
        if any(filled.values()):
            df = df.fillna({c: float(constant) for c in NUMERIC_FILL_COLUMNS})
        info["filled"] = filled
        return df, info

    for column in NUMERIC_FILL_COLUMNS:
        missing = df.filter(F.col(column).isNull()).count()
        if not missing:
            info["filled"][column] = 0
            continue
        value = None
        if strategy == "mean":
            value = df.select(F.avg(column)).first()[0]
        elif strategy == "median":
            quantiles = df.approxQuantile(column, [0.5], 0.01)
            value = quantiles[0] if quantiles else None
        elif strategy == "mode":
            row = (
                df.filter(F.col(column).isNotNull())
                .groupBy(column)
                .count()
                .orderBy(F.desc("count"))
                .first()
            )
            value = row[0] if row else None
        if value is None:
            value = float(constant)
        df = df.fillna({column: float(value)})
        info["filled"][column] = missing
    return df, info


def apply_min_confidence(df: DataFrame, minimum: str) -> DataFrame:
    """Filter confidence minimum: low (semua) | nominal | high."""
    threshold = CONFIDENCE_RANK.get(minimum, 1)
    allowed = [level for level, rank in CONFIDENCE_RANK.items() if rank >= threshold]
    return df.filter(F.col("confidence_level").isin(allowed))


def filter_outliers(df: DataFrame, method: str, column: str, threshold: float) -> DataFrame:
    """Filter outlier IQR/Z-score pada kolom metrik (FR-P2)."""
    if method == "none":
        return df
    if method == "iqr":
        q1, q3 = df.approxQuantile(column, [0.25, 0.75], 0.01)
        spread = q3 - q1
        low, high = q1 - threshold * spread, q3 + threshold * spread
        df = df.filter(F.col(column).between(low, high) | F.col(column).isNull())
    else:  # zscore
        row = df.select(F.avg(column).alias("mean"), F.stddev(column).alias("sd")).first()
        mean, sd = float(row["mean"] or 0.0), float(row["sd"] or 0.0)
        if sd > 0:
            deviation = F.abs(F.col(column).cast("double") - F.lit(mean))
            df = df.filter((deviation <= threshold * sd) | F.col(column).isNull())
    return df


def enrich_province(spark: SparkSession, df: DataFrame) -> DataFrame:
    lookup_path = Path(settings.PROVINCE_GRID_LOOKUP)
    if not lookup_path.exists():
        raise FileNotFoundError(
            f"Lookup provinsi belum ada: {lookup_path}. "
            "Jalankan `python backend/spark_jobs/build_province_lookup.py`."
        )
    # Default FS adalah HDFS; path Windows lokal harus memakai file:///.
    lookup = spark.read.parquet(lookup_path.resolve().as_uri())
    df = (
        df.withColumn("cell_lat", F.floor(F.col("latitude") / PROVINCE_STEP).cast("int"))
        .withColumn("cell_lon", F.floor(F.col("longitude") / PROVINCE_STEP).cast("int"))
        .join(
            F.broadcast(lookup),
            on=["cell_lat", "cell_lon"],
            how="left",
        )
        .withColumn("province", F.coalesce(F.col("province"), F.lit("UNKNOWN")))
        .drop("cell_lat", "cell_lon")
    )
    return df


def deduplicate(df: DataFrame) -> DataFrame:
    """Dedup sesuai PRD; pertahankan FRP/confidence tertinggi."""
    key = ["latitude", "longitude", "acq_date", "acq_time", "satellite"]
    window = Window.partitionBy(*key).orderBy(
        F.desc_nulls_last("frp"),
        F.desc_nulls_last("confidence_score"),
        F.desc_nulls_last("acq_ts_utc"),
    )
    return (
        df.withColumn("_rn", F.row_number().over(window))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )


def normalize_scales(df: DataFrame, method: str) -> tuple[DataFrame, dict]:
    """Min-Max / Z-score / tanpa normalisasi; parameter disimpan di laporan."""
    stats = df.select(
        F.min("frp").alias("frp_min"),
        F.max("frp").alias("frp_max"),
        F.avg("frp").alias("frp_avg"),
        F.stddev("frp").alias("frp_sd"),
        F.min("brightness").alias("brightness_min"),
        F.max("brightness").alias("brightness_max"),
        F.avg("brightness").alias("brightness_avg"),
        F.stddev("brightness").alias("brightness_sd"),
    ).collect()[0]
    params = {key: (None if stats[key] is None else round(float(stats[key]), 6)) for key in stats.asDict()}

    if method == "none":
        return (
            df.withColumn("frp_norm", F.lit(None).cast("double")).withColumn(
                "brightness_norm", F.lit(None).cast("double")
            ),
            params,
        )

    def scale(column: str, low: float, high: float, mean: float, sd: float):
        if method == "zscore":
            if sd and sd > 0:
                return (F.col(column).cast("double") - F.lit(mean)) / F.lit(sd)
            return F.lit(0.0)
        if high <= low:
            return F.lit(0.0)
        return F.greatest(
            F.lit(0.0),
            F.least(
                F.lit(1.0),
                (F.col(column).cast("double") - F.lit(low)) / F.lit(high - low),
            ),
        )

    df = df.withColumn(
        "frp_norm",
        scale(
            "frp",
            params["frp_min"] or 0.0,
            params["frp_max"] or 0.0,
            params["frp_avg"] or 0.0,
            params["frp_sd"] or 0.0,
        ),
    ).withColumn(
        "brightness_norm",
        scale(
            "brightness",
            params["brightness_min"] or 0.0,
            params["brightness_max"] or 0.0,
            params["brightness_avg"] or 0.0,
            params["brightness_sd"] or 0.0,
        ),
    )
    return df, params


def preprocess(
    spark: SparkSession,
    input_paths: list[str],
    output_path: str,
    job_id: str,
    summary_path: str | Path | None = None,
    config: dict | None = None,
) -> dict:
    config = config or load_config(None)
    cleaning = config["cleaning"]
    transform = config["transform"]
    normalization = config["normalization"]
    spatial = config["spatial"]

    log_job_start(
        job_id,
        "PREPROCESSING",
        {"inputs": input_paths, "output": output_path, "config": config},
    )
    started_at = now_utc()
    funnel: list[dict] = []
    durations: dict[str, float] = {}

    def mark(step: str, label: str, rows: int, duration: float, note: str = "") -> None:
        funnel.append(
            {"step": step, "label": label, "rows": int(rows), "duration_ms": int(duration * 1000), "note": note}
        )

    tick = time.perf_counter()
    raw = read_raw(spark, input_paths)
    input_count = raw.count()
    mark("read", "Baca raw", input_count, time.perf_counter() - tick, f"{len(input_paths)} pola input")
    print(f"[INFO] Baris input: {input_count:,}")

    tick = time.perf_counter()
    df = normalize(raw)
    durations["normalize"] = time.perf_counter() - tick

    tick = time.perf_counter()
    df, null_info = apply_null_strategy(
        df, str(cleaning.get("null_strategy", "constant")), float(cleaning.get("null_constant", 0.0))
    )
    nulls_rows = df.count()
    mark(
        "nulls",
        "Tangani nilai kosong",
        nulls_rows,
        time.perf_counter() - tick,
        f"{null_info['strategy']}; diisi {sum(v for v in null_info['filled'].values())}",
    )

    tick = time.perf_counter()
    valid_condition = ~(
        F.col("latitude").isNull()
        | F.col("longitude").isNull()
        | F.col("acq_ts_utc").isNull()
    )
    df = df.filter(valid_condition)
    valid_count = df.count()
    invalid_coords_count = input_count - valid_count
    mark("valid", "Koordinat & waktu valid", valid_count, time.perf_counter() - tick, f"{invalid_coords_count} dibuang")

    if cleaning.get("filter_bbox", True):
        tick = time.perf_counter()
        df = bbox_filter(df)
        bbox_count = df.count()
        out_of_bbox = valid_count - bbox_count
        mark("bbox", "Filter bbox Indonesia", bbox_count, time.perf_counter() - tick, f"{out_of_bbox} di luar bbox")
    else:
        bbox_count = valid_count
        out_of_bbox = 0
        mark("bbox", "Filter bbox Indonesia", bbox_count, 0.0, "dimatikan")
    print(f"[INFO] Valid koordinat/waktu: {valid_count:,}; di bbox: {bbox_count:,}")

    tick = time.perf_counter()
    df = apply_min_confidence(df, str(cleaning.get("min_confidence", "low")))
    confidence_rows = df.count()
    confidence_removed = bbox_count - confidence_rows
    mark(
        "confidence",
        "Filter confidence minimum",
        confidence_rows,
        time.perf_counter() - tick,
        f"min={cleaning.get('min_confidence')} ({confidence_removed} dibuang)",
    )

    if spatial.get("province", True):
        tick = time.perf_counter()
        df = enrich_province(spark, df)
        durations["province"] = time.perf_counter() - tick
    else:
        df = df.withColumn("province", F.lit("UNKNOWN"))

    if not spatial.get("grid_id", True):
        df = df.withColumn("grid_id", F.lit(None).cast("string"))

    # Simpan hasil enrichment ke disk agar tidak dihitung ulang pada beberapa aksi.
    df = df.persist(StorageLevel.DISK_ONLY)

    tick = time.perf_counter()
    df = filter_outliers(
        df,
        str(cleaning.get("outlier_method", "none")),
        str(cleaning.get("outlier_column", "frp")),
        float(cleaning.get("outlier_threshold", 1.5)),
    )
    outlier_rows = df.count()
    outlier_removed = confidence_rows - outlier_rows
    mark(
        "outliers",
        "Filter outlier",
        outlier_rows,
        time.perf_counter() - tick,
        f"{cleaning.get('outlier_method')} pada {cleaning.get('outlier_column')} ({outlier_removed} dibuang)",
    )

    tick = time.perf_counter()
    df, norm_params = normalize_scales(df, str(normalization.get("method", "minmax")))
    mark(
        "normalize",
        "Normalisasi",
        outlier_rows,
        time.perf_counter() - tick,
        f"metode={normalization.get('method')}",
    )

    if cleaning.get("drop_duplicates", True):
        tick = time.perf_counter()
        before_dedup = outlier_rows
        df = deduplicate(df)
        clean_count = df.count()
        duplicates = before_dedup - clean_count
        mark("dedup", "Deduplikasi", clean_count, time.perf_counter() - tick, f"{duplicates} dibuang")
    else:
        before_dedup = outlier_rows
        clean_count = before_dedup
        duplicates = 0
        mark("dedup", "Deduplikasi", clean_count, 0.0, "dimatikan")
    print(f"[INFO] Setelah dedup: {clean_count:,} (duplikat {duplicates:,})")

    if transform.get("time_parts", True):
        df = (
            df.withColumn("year", F.year("acq_ts_utc"))
            .withColumn("month", F.month("acq_ts_utc"))
            .withColumn("day", F.dayofmonth("acq_ts_utc"))
            .withColumn("dayofyear", F.dayofyear("acq_ts_utc"))
            .withColumn("hour", F.hour("acq_ts_utc"))
        )
    else:
        for column in ("year", "month", "day", "dayofyear", "hour"):
            df = df.withColumn(column, F.lit(None).cast("int"))

    selected = [c for c in CANONICAL_HOTSPOT_COLUMNS]
    extra = [c for c in ("acq_date", "acq_time") if c in df.columns]
    df_final = df.select(*selected, *extra)

    tick = time.perf_counter()
    print(f"[INFO] Menulis Parquet ke {output_path}")
    (
        df_final.write.mode("overwrite")
        .partitionBy("year", "month")
        .parquet(output_path)
    )
    durations["write"] = time.perf_counter() - tick

    province_rows = (
        df_final.groupBy("province").count().orderBy(F.desc("count")).collect()
    )
    sensors = df_final.groupBy("instrument", "satellite").count().collect()
    df.unpersist()

    report = {
        "job_id": job_id,
        "status": "COMPLETED",
        "started_at": started_at,
        "finished_at": now_utc(),
        "inputs": input_paths,
        "output_path": output_path,
        "config": config,
        "rows": {
            "input": input_count,
            "invalid_coords_or_time": invalid_coords_count,
            "out_of_bbox": out_of_bbox,
            "in_bbox": bbox_count,
            "before_dedup": before_dedup,
            "clean": clean_count,
            "duplicates_removed": duplicates,
            "confidence_filtered": confidence_removed,
            "outliers_removed": outlier_removed,
            "clean_rate_percent": round(clean_count / input_count * 100, 2)
            if input_count
            else 0.0,
        },
        "funnel": funnel,
        "durations_ms": {key: int(value * 1000) for key, value in durations.items()},
        "null_handling": null_info,
        "normalization": {"method": normalization.get("method"), "params": norm_params},
        "provinces": {str(r["province"]): int(r["count"]) for r in province_rows},
        "sensors": [
            {
                "instrument": r["instrument"],
                "satellite": r["satellite"],
                "count": int(r["count"]),
            }
            for r in sensors
        ],
        "schema": df_final.dtypes,
    }
    write_json(summary_path or SUMMARY_PATH, report)
    if summary_path is None:
        write_json(LATEST_PATH, {"job_id": job_id, "finished_at": report["finished_at"]})
    log_job_finish(job_id, "COMPLETED", report)
    print("[SUCCESS] " + str(summary_path or SUMMARY_PATH))
    print(
        f"[SUCCESS] {clean_count:,} baris clean dari {input_count:,} baris input "
        f"({report['rows']['clean_rate_percent']}%)"
    )
    return report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="*", help="glob/path input; default hist + NRT")
    parser.add_argument("--output", default=CLEAN_OUTPUT)
    parser.add_argument("--summary", default=None)
    parser.add_argument("--config", default=None, help="JSON konfigurasi stepper")
    parser.add_argument("--job-id", default=None)
    args = parser.parse_args()

    job_id = args.job_id or (
        f"preprocess-{now_utc().replace(':', '').replace('-', '')[:15]}"
    )
    paths = args.inputs or DEFAULT_INPUTS
    config = load_config(args.config)
    spark = None
    try:
        spark = get_spark_session("PantauApi-Preprocess")
        quiet(spark)
        preprocess(
            spark,
            paths,
            args.output,
            job_id,
            summary_path=args.summary,
            config=config,
        )
        return 0
    except Exception as exc:
        log_job_finish(job_id, "FAILED", {"error": repr(exc), "config": config})
        print(f"[FAIL] {exc!r}")
        raise
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
