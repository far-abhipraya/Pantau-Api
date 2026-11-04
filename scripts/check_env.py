"""Cek lingkungan KarhutlaWatch (Windows native). Hanya membaca, tidak mengubah apa pun."""
import os, shutil, socket, subprocess, sys

OK, FAIL, WARN = "[OK]  ", "[FAIL]", "[WARN]"
results = []

def report(status, msg):
    results.append(status)
    print(f"{status} {msg}")

def run(cmd, timeout=60):
    env = os.environ.copy()
    env["HADOOP_USER_NAME"] = "hadoop"
    try:
        p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout, shell=True)
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as e:
        return 1, str(e)

def port_open(port, host="127.0.0.1"):
    with socket.socket() as s:
        s.settimeout(1.5)
        return s.connect_ex((host, port)) == 0

print(f"Python: {sys.version.split()[0]} ({sys.executable})")
if sys.version_info >= (3, 14):
    report(WARN, "Python 3.14: verifikasi kompatibilitas PySpark dan wheel paket; siapkan venv 3.12/3.13 bila perlu")

for var in ["JAVA_HOME", "HADOOP_HOME", "SPARK_HOME", "HADOOP_USER_NAME"]:
    val = os.environ.get(var)
    report(OK if val else FAIL, f"{var} = {val}")
if os.environ.get("HADOOP_USER_NAME") != "hadoop":
    report(WARN, "HADOOP_USER_NAME bukan 'hadoop' di proses ini")

for tool in ["java", "hdfs", "spark-submit"]:
    path = shutil.which(tool)
    report(OK if path else FAIL, f"{tool}: {path}")

code, out = run("java -version")
report(OK if code == 0 else FAIL, "java -version: " + out.splitlines()[0] if out else "java -version gagal")
code, out = run("spark-submit --version")
first = [l for l in out.splitlines() if "version" in l.lower()]
report(OK if code == 0 else FAIL, "spark-submit: " + (first[0].strip() if first else out[:120]))

for port, name in [(9000, "HDFS RPC"), (9870, "NameNode UI"), (8080, "NiFi (opsional)"), (8088, "YARN UI (opsional)")]:
    up = port_open(port)
    optional = "opsional" in name
    report(OK if up else (WARN if optional else FAIL), f"port {port} {name}: {'terbuka' if up else 'tertutup'}")

code, out = run("hdfs dfs -ls /")
report(OK if code == 0 else FAIL, "hdfs dfs -ls / -> " + ("\n" + out if code == 0 else out[:200]))
code, out = run("hdfs dfsadmin -safemode get")
report(OK if "OFF" in out.upper() else WARN, "safemode: " + out[:80])

for mod in ["pyspark", "fastapi", "uvicorn", "pydantic", "sqlalchemy", "duckdb", "pyarrow", "pandas"]:
    try:
        m = __import__(mod)
        report(OK, f"modul {mod} {getattr(m, '__version__', '')}")
    except Exception as e:
        report(WARN, f"modul {mod} tidak tersedia ({type(e).__name__})")

for d in ["C:/karhutla-data/staging", "C:/karhutla-data/spark-tmp", "C:/karhutla-data/serving", "C:/karhutla-data/downloads"]:
    report(OK if os.path.isdir(d) else WARN, f"folder {d}")

if " " in os.getcwd():
    report(WARN, f"Folder kerja mengandung spasi: {os.getcwd()}")

total, used, free = shutil.disk_usage("C:/")
report(OK if free > 50 * 2**30 else WARN, f"disk C: bebas {free / 2**30:.0f} GB")
try:
    import psutil
    vm = psutil.virtual_memory()
    report(OK if vm.available > 4 * 2**30 else WARN, f"RAM tersedia {vm.available / 2**30:.1f} GB dari {vm.total / 2**30:.1f} GB")
except ImportError:
    report(WARN, "psutil tidak terpasang; cek RAM dilewati")

print(f"\nRingkasan: {results.count(OK)} OK, {results.count(WARN)} WARN, {results.count(FAIL)} FAIL")
sys.exit(1 if FAIL in results else 0)
