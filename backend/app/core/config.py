"""Konfigurasi terpusat PantauApi.

Semua path dan kredensial dibaca dari `.env` di root repo (lihat `.env.example`).
Nilai default hanya untuk pengembangan lokal dan tidak boleh mengandung rahasia.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "PantauApi"
    API_PREFIX: str = "/api"

    # HDFS
    HDFS_URI: str = "hdfs://localhost:9000"
    HDFS_BASE_PATH: str = "/karhutla"
    HADOOP_USER_NAME: str = "hadoop"

    # Folder lokal (tanpa spasi)
    DATA_DIR: Path = Path("C:/karhutla-data")
    INBOX_DIR: Path = Path("C:/karhutla-data/inbox")
    INBOX_PROCESSED_DIR: Path = Path("C:/karhutla-data/inbox/processed")
    INBOX_FAILED_DIR: Path = Path("C:/karhutla-data/inbox/failed")
    STAGING_DIR: Path = Path("C:/karhutla-data/staging")
    SPARK_TMP_DIR: Path = Path("C:/karhutla-data/spark-tmp")
    SERVING_DIR: Path = Path("C:/karhutla-data/serving")
    DOWNLOADS_DIR: Path = Path("C:/karhutla-data/downloads")
    UPLOAD_DIR: Path = Path("C:/karhutla-data/staging/uploads")

    # Metadata & serving
    SQLITE_PATH: Path = Path("C:/karhutla-data/serving/meta.db")
    DUCKDB_PATH: Path = Path("C:/karhutla-data/serving/pantauapi.duckdb")
    JOB_LOG_DIR: Path = Path("C:/karhutla-data/serving/logs/jobs")

    # Spark
    SPARK_MASTER: str = "local[4]"
    SPARK_DRIVER_MEMORY: str = "4g"
    SPARK_SHUFFLE_PARTITIONS: int = 8
    SPARK_SUBMIT: str = ""
    PYSPARK_PYTHON: str = ""
    PYSPARK_DRIVER_PYTHON: str = ""

    # Upload manual (jalur tambahan, pipeline sama)
    UPLOAD_CHUNK_SIZE: int = 5_000_000
    MAX_UPLOAD_BYTES: int = 2_000_000_000
    INBOX_SCAN_INTERVAL_SEC: int = 300

    # Data source
    FIRMS_MAP_KEY: str = ""
    FIRMS_BBOX: str = "95,-11,141,6"

    # Web
    BACKEND_PORT: int = 8000
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    NIFI_URL: str = "http://localhost:8080/nifi"
    MAP_MAX_POINTS: int = 20000
    NEXT_PUBLIC_API_BASE: str = "http://localhost:8000/api"
    NEXT_PUBLIC_BASEMAP_URL: str = (
        "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
    )
    NEXT_PUBLIC_BASEMAP_ATTRIBUTION: str = ""

    # Geospasial
    GEOJSON_PROVINCES: Path = REPO_ROOT / "backend" / "app" / "static" / "geo" / "provinces.geojson"
    PROVINCE_GRID_LOOKUP: Path = (
        REPO_ROOT / "backend" / "app" / "static" / "geo" / "province_grid_lookup.parquet"
    )

    @property
    def HDFS_URL(self) -> str:
        """Alias kompatibilitas untuk kode lama."""
        return self.HDFS_URI

    @property
    def HDFS_ROOT(self) -> str:
        """Alias kompatibilitas untuk kode lama."""
        return self.HDFS_BASE_PATH

    @property
    def SQLITE_URL(self) -> str:
        return f"sqlite:///{Path(self.SQLITE_PATH).as_posix()}"

    @property
    def BBOX_INDONESIA(self) -> dict[str, float]:
        """Bbox dari env FIRMS_BBOX berformat min_lon,min_lat,max_lon,max_lat."""
        min_lon, min_lat, max_lon, max_lat = (
            float(part.strip()) for part in self.FIRMS_BBOX.split(",")
        )
        return {
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon,
        }

    def ensure_dirs(self) -> None:
        for path in (
            self.INBOX_DIR,
            self.INBOX_PROCESSED_DIR,
            self.INBOX_FAILED_DIR,
            self.STAGING_DIR,
            self.SPARK_TMP_DIR,
            self.SERVING_DIR,
            self.DOWNLOADS_DIR,
            self.UPLOAD_DIR,
            self.JOB_LOG_DIR,
        ):
            Path(path).mkdir(parents=True, exist_ok=True)

    @property
    def HDFS_ALLOWED_PREFIX(self) -> str:
        """Hanya path di bawah prefix ini boleh dihapus lewat API (AGENTS.md)."""
        return f"{self.HDFS_BASE_PATH}/"


settings = Settings()
