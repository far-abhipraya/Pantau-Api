# ENVIRONMENT: Fakta Lingkungan (jangan diubah tanpa persetujuan)

## Perangkat
- Lenovo Yoga 7 (LENOVO-YOGA-7), AMD Ryzen 7 8840HS (8 core/16 thread), RAM 16 GB (sekitar 13,8 GB usable), tanpa GPU NVIDIA, Windows 11 (10.0.26200).
- Disk: sisa sekitar 240 GB dari 954 GB.
- Username Windows mengandung spasi (`Alfarel Abhipraya`, short name `ALFARE~1`) sehingga rawan error path.

## Perangkat Lunak
| Komponen | Versi | Lokasi/Catatan |
|---|---|---|
| Java | Eclipse Adoptium JDK 17.0.12.7 | `C:\Program Files\Eclipse Adoptium\jdk-17.0.12.7-hotspot` |
| Hadoop | 3.5.0, single-node pseudo-distributed (NN, DN, RM, NM) | `C:\hadoop-3.5.0`; `winutils.exe` dan `hadoop.dll` di `bin` (cdarlint) |
| Spark | 4.2.0 (Scala 2.13.18), mode `local[*]` | `C:\spark-4.2.0-bin-hadoop3`; `SPARK_HOME` dan `SPARK_DIST_CLASSPATH` (dari `hadoop classpath`) di-set |
| NiFi | 1.28.1, HTTP :8080 (`nifi.web.https.port` kosong, `nifi.remote.input.secure=false`) | `C:\nifi-1.28.1`; alur GetFile -> PutHDFS memakai core-site.xml dan hdfs-site.xml |
| Python | 3.14 | `C:\Python314` (kompatibilitas PySpark/paket perlu diverifikasi) |

## Environment Variable
- System: `JAVA_HOME`, `HADOOP_HOME=C:\hadoop-3.5.0`; PATH memuat `%JAVA_HOME%\bin`, `%HADOOP_HOME%\bin`, `%HADOOP_HOME%\sbin`.
- User: `HADOOP_USER_NAME=hadoop`.

## Konfigurasi Hadoop (`C:\hadoop-3.5.0\etc\hadoop`)
- `core-site.xml`: `fs.defaultFS=hdfs://localhost:9000`, `hadoop.tmp.dir=C:/hadoop-3.5.0/tmp`
- `hdfs-site.xml`: `dfs.replication=1`, `dfs.namenode.name.dir=file:///C:/hadoop-3.5.0/data/namenode`, `dfs.datanode.data.dir=file:///C:/hadoop-3.5.0/data/datanode` (wajib forward slash)
- `mapred-site.xml`: `mapreduce.framework.name=yarn`
- `yarn-site.xml`: `yarn.nodemanager.aux-services=mapreduce_shuffle`, handler `org.apache.hadoop.mapred.ShuffleHandler`
- `hadoop-env.cmd`: `set JAVA_HOME=C:\PROGRA~1\ECLIPS~1\jdk-17.0.12.7-hotspot` (short path), `set HADOOP_IDENT_STRING=hadoop`

## Menjalankan
- NameNode sudah diformat (2026-09-01). JANGAN format ulang (akan menghapus semua data HDFS).
- Start: `start-all.cmd` dari CMD Administrator (peringatan deprecated normal). Untuk proyek ini cukup `start-dfs.cmd` (YARN tidak dibutuhkan, hemat RAM). Stop: `stop-all.cmd` atau `stop-dfs.cmd`.
- UI: NameNode http://localhost:9870, YARN http://localhost:8088, RPC HDFS localhost:9000, RM 0.0.0.0:8032.

## Penyesuaian Windows (jangan dihapus)
- `HADOOP_IDENT_STRING=hadoop` dan `HADOOP_USER_NAME=hadoop` mengatasi error "Could not find or load main class Abhipraya" dan path container YARN yang terpotong di spasi username.
- Path di XML memakai forward slash (backslash menyebabkan URISyntaxException).
- `hdfs dfs -stat` dengan `%` rusak di CMD. Gunakan `-ls` atau `-du`.
- Upload lewat NameNode Web UI gagal karena redirect ke hostname DataNode. Upload memakai `hdfs dfs -put` atau NiFi.

## Status Terverifikasi
- NameNode active, Safemode off, 1 Active Node YARN (8 GB, 8 vcores, Capacity Scheduler).
- Job MapReduce (Hadoop Streaming + Python) sukses: `application_1790081629251_0001`, 2.000.000 record.
- Isi HDFS lama (JANGAN diubah): `/hr-data` (2 CSV masing-masing 2.000.001 baris termasuk header, plus `output_avg_salary`), `/warehouse/dataset1-3` (via NiFi), `/user/alfarel`, `/test`, `/testupload`.

## Folder Kerja Proyek (tanpa spasi)
- Kode: `C:\projects\karhutla-watch`
- Data lokal: `C:\karhutla-data\staging`, `C:\karhutla-data\spark-tmp`, `C:\karhutla-data\serving`, `C:\karhutla-data\downloads`

## Anggaran Memori
Windows + browser + IDE sekitar 4 GB; HDFS NN+DN sekitar 2 GB; Spark job 4 GB (`local[4]`, `--driver-memory 4g`); NiFi sekitar 1,5 GB (heap 1 GB, jalankan saat perlu); FastAPI sekitar 0,5 GB; Next.js dev sekitar 0,5 GB. Satu job Spark pada satu waktu.
