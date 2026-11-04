@echo off
REM Jalankan dari CMD sebagai Administrator.
REM Proyek ini hanya butuh HDFS (YARN tidak dipakai) untuk menghemat RAM.
set HADOOP_USER_NAME=hadoop
call "%HADOOP_HOME%\sbin\start-dfs.cmd"
echo Menunggu NameNode...
timeout /t 15 /nobreak >nul
hdfs dfsadmin -safemode get
hdfs dfs -ls /
echo NameNode UI: http://localhost:9870
