# Aturan: Hadoop/Spark native Windows

Berlaku untuk semua kode yang memanggil Hadoop, HDFS, atau Spark.

## Environment subprocess
Selalu bangun env eksplisit untuk subprocess:

```python
import os, subprocess
def hadoop_env():
    env = os.environ.copy()
    env["HADOOP_USER_NAME"] = "hadoop"
    return env

def run_hdfs(args, timeout=600):
    # hdfs adalah hdfs.cmd di Windows, jadi shell=True atau resolve lewat shutil.which("hdfs.cmd")
    return subprocess.run(["hdfs", "dfs", *args], env=hadoop_env(),
                          capture_output=True, text=True, timeout=timeout, shell=True)
```

## Larangan dan kebiasaan
- Jangan `hdfs dfs -stat` dengan `%`. Gunakan `-ls`, `-du -s`, `-count`.
- Path konfigurasi memakai forward slash (`C:/karhutla-data/spark-tmp`).
- Gunakan `pathlib.Path`. Quote semua path pada perintah shell.
- URI HDFS: `hdfs://localhost:9000/karhutla/...`.
- Spark: set `spark.local.dir` ke `C:/karhutla-data/spark-tmp`, `spark.sql.shuffle.partitions` sekitar 16-32 (bukan 200), `spark.sql.session.timeZone=UTC`.
- Tulis Parquet dengan `mode("overwrite")` + `partitionOverwriteMode=dynamic` untuk output berpartisi.
- Jangan `collect()`/`toPandas()` pada data besar. Hanya untuk agregat kecil (puluhan ribu baris).
- Hindari file kecil banyak di HDFS. Gunakan `coalesce` atau `repartition` sebelum menulis.
- Jangan memakai `localhost:9870` WebHDFS untuk upload. Upload = staging lokal + `hdfs dfs -put -f`.
- YARN tidak dibutuhkan (Spark `local[*]`). Jangan memaksa submit ke YARN.

## Verifikasi kompatibilitas (Fase 0, laporkan sebelum lanjut)
1. PySpark bawaan Spark 4.2.0 vs Python 3.14. Bila gagal, buat venv Python 3.12/3.13 berdampingan dan set `PYSPARK_PYTHON` dan `PYSPARK_DRIVER_PYTHON`. Jangan hapus Python 3.14.
2. Baca dan tulis CSV dan Parquet ke `hdfs://localhost:9000/karhutla/_smoke_test` dari PySpark. Hapus setelah uji.
3. Wheel paket (fastapi, pydantic-core, pyarrow, duckdb, pandas) tersedia di versi Python terpilih.
