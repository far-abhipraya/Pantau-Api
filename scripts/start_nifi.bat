@echo off
REM Jalankan hanya bila perlu (sekitar 1,5 GB RAM). TODO(verify): nama skrip NiFi di C:\nifi-1.28.1\bin
start "NiFi" cmd /k "C:\nifi-1.28.1\bin\run-nifi.bat"
echo NiFi UI: http://localhost:8080/nifi
