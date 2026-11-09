from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    HDFS_URI: str = "hdfs://localhost:9000"
    HADOOP_USER_NAME: str = "hadoop"
    HDFS_BASE_PATH: str = "/karhutla"

    STAGING_DIR: Path = Path("C:/karhutla-data/staging")
    SPARK_TMP_DIR: Path = Path("C:/karhutla-data/spark-tmp")
    SERVING_DIR: Path = Path("C:/karhutla-data/serving")
    DOWNLOADS_DIR: Path = Path("C:/karhutla-data/downloads")
    SQLITE_PATH: Path = Path("C:/karhutla-data/serving/meta.db")

    SPARK_MASTER: str = "local[4]"
    SPARK_DRIVER_MEMORY: str = "4g"
    PYSPARK_PYTHON: str = "C:/projects/karhutla-watch/.venv/Scripts/python.exe"
    PYSPARK_DRIVER_PYTHON: str = "C:/projects/karhutla-watch/.venv/Scripts/python.exe"

    FIRMS_MAP_KEY: str = ""
    FIRMS_BBOX: str = "95,-11,141,6"

    BACKEND_PORT: int = 8000
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    NEXT_PUBLIC_API_BASE: str = "http://localhost:8000/api"
    NIFI_URL: str = "http://localhost:8080/nifi"
    CDS_API_URL: str = ""
    CDS_API_KEY: str = ""

    class Config:
        env_file = "C:/projects/karhutla-watch/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
