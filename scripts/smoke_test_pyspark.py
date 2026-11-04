"""Smoke test PySpark: tulis dan baca CSV dan Parquet ke HDFS lalu bersihkan."""
import os
import sys
import subprocess
from pathlib import Path

# Pastikan HADOOP_USER_NAME dan PYSPARK_PYTHON terdefinisi
os.environ["HADOOP_USER_NAME"] = "hadoop"
python_exe = sys.executable
os.environ["PYSPARK_PYTHON"] = python_exe
os.environ["PYSPARK_DRIVER_PYTHON"] = python_exe

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, DoubleType

def run_smoke_test():
    print(f"[INFO] Inisialisasi SparkSession...")
    print(f"[INFO] Python executable: {python_exe}")

    spark = (
        SparkSession.builder
        .appName("KarhutlaWatchSmokeTest")
        .master("local[2]")
        .config("spark.driver.memory", "2g")
        .config("spark.local.dir", "C:/karhutla-data/spark-tmp")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    sc = spark.sparkContext
    sc.setLogLevel("WARN")

    test_base = "hdfs://localhost:9000/karhutla/_smoke_test"
    csv_path = f"{test_base}/csv"
    parquet_path = f"{test_base}/parquet"

    test_data = [
        (1, "Hotspot A", -0.5, 101.2, 320.5),
        (2, "Hotspot B", -1.2, 102.4, 315.0),
        (3, "Hotspot C", 0.8, 100.9, 340.2),
        (4, "Hotspot D", -2.1, 104.5, 305.8),
        (5, "Hotspot E", 1.5, 99.8, 350.1),
    ]
    schema = StructType([
        StructField("id", IntegerType(), False),
        StructField("name", StringType(), False),
        StructField("latitude", DoubleType(), False),
        StructField("longitude", DoubleType(), False),
        StructField("brightness", DoubleType(), False),
    ])

    try:
        print("[INFO] Membuat DataFrame uji (5 baris)...")
        df = spark.createDataFrame(test_data, schema)

        # 1. Tulis CSV ke HDFS
        print(f"[INFO] Menulis CSV ke {csv_path}...")
        df.write.mode("overwrite").option("header", "true").csv(csv_path)

        # 2. Baca CSV dari HDFS
        print(f"[INFO] Membaca CSV dari {csv_path}...")
        df_csv = spark.read.option("header", "true").csv(csv_path)
        count_csv = df_csv.count()
        print(f"[PASS] CSV berhasil dibaca. Jumlah baris: {count_csv}")
        assert count_csv == 5, f"Ekspektasi 5 baris, didapat {count_csv}"

        # 3. Tulis Parquet ke HDFS
        print(f"[INFO] Menulis Parquet ke {parquet_path}...")
        df.write.mode("overwrite").parquet(parquet_path)

        # 4. Baca Parquet dari HDFS
        print(f"[INFO] Membaca Parquet dari {parquet_path}...")
        df_parquet = spark.read.parquet(parquet_path)
        count_parquet = df_parquet.count()
        print(f"[PASS] Parquet berhasil dibaca. Jumlah baris: {count_parquet}")
        assert count_parquet == 5, f"Ekspektasi 5 baris, didapat {count_parquet}"

        print("[SUCCESS] Seluruh uji tulis/baca HDFS CSV & Parquet BERHASIL!")

    finally:
        print("[INFO] Menghentikan SparkSession...")
        spark.stop()

    # 5. Bersihkan HDFS _smoke_test
    print(f"[INFO] Membersihkan path uji {test_base} di HDFS...")
    env = os.environ.copy()
    env["HADOOP_USER_NAME"] = "hadoop"
    res = subprocess.run(["hdfs", "dfs", "-rm", "-r", "-skipTrash", "/karhutla/_smoke_test"],
                         env=env, capture_output=True, text=True, shell=True)
    if res.returncode == 0:
        print("[PASS] Path /karhutla/_smoke_test berhasil dibersihkan dari HDFS.")
    else:
        print(f"[WARN] Gagal menghapus {test_base}: {res.stderr}")

if __name__ == "__main__":
    run_smoke_test()

