@echo off
REM Mengaktifkan virtual environment KarhutlaWatch dan konfigurasi PySpark
cd /d C:\projects\karhutla-watch
call .venv\Scripts\activate.bat
set HADOOP_USER_NAME=hadoop
set PYSPARK_PYTHON=C:\projects\karhutla-watch\.venv\Scripts\python.exe
set PYSPARK_DRIVER_PYTHON=C:\projects\karhutla-watch\.venv\Scripts\python.exe
echo ========================================================
echo  KarhutlaWatch Environment Aktif:
echo  - Python: %PYSPARK_PYTHON%
echo  - HADOOP_USER_NAME: %HADOOP_USER_NAME%
echo ========================================================

