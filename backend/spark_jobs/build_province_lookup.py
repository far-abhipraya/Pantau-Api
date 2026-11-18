"""Bangun lookup grid -> provinsi dari GeoJSON batas provinsi.

Lookup ini dipakai Spark saat pre-processing agar penentuan provinsi memakai
poligon batas administratif, bukan titik tengah provinsi. Hasil disimpan sebagai
Parquet kecil dan dapat dipakai ulang (idempoten).

Jalankan:
    python backend/spark_jobs/build_province_lookup.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import Point, shape
from shapely.prepared import prep

# Agar `app.core.config` bisa diimpor saat dijalankan dari root repo.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings  # noqa: E402

STEP = 0.02  # derajat, sekitar 2,2 km
LAT_MIN, LAT_MAX = -11.0, 6.0
LON_MIN, LON_MAX = 95.0, 141.0


def load_provinces(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    provinces = []
    for feature in data["features"]:
        props = feature.get("properties") or {}
        name = props.get("name") or props.get("PROVINSI") or props.get("NAME_1")
        if not name:
            continue
        geom = shape(feature["geometry"])
        provinces.append(
            {
                "name": str(name),
                "geom": geom,
                "prepared": prep(geom),
                "bounds": geom.bounds,
            }
        )
    return provinces


def province_at(lat: float, lon: float, provinces) -> str | None:
    point = Point(lon, lat)
    for province in provinces:
        minx, miny, maxx, maxy = province["bounds"]
        if minx <= lon <= maxx and miny <= lat <= maxy:
            if province["prepared"].covers(point):
                return province["name"]
    return None


def province_for_cell(lat: float, lon: float, provinces) -> str | None:
    """Coba pusat sel, lalu beberapa titik di dalam sel untuk wilayah pesisir."""
    direct = province_at(lat, lon, provinces)
    if direct:
        return direct
    offsets = (
        (-STEP / 2, -STEP / 2),
        (-STEP / 2, STEP / 2),
        (STEP / 2, -STEP / 2),
        (STEP / 2, STEP / 2),
        (0.0, -STEP / 2),
        (0.0, STEP / 2),
        (-STEP / 2, 0.0),
        (STEP / 2, 0.0),
    )
    votes: dict[str, int] = {}
    for dy, dx in offsets:
        found = province_at(lat + dy, lon + dx, provinces)
        if found:
            votes[found] = votes.get(found, 0) + 1
    if not votes:
        return None
    return max(votes, key=votes.get)


def main() -> int:
    source = Path(settings.GEOJSON_PROVINCES)
    output = Path(settings.PROVINCE_GRID_LOOKUP)
    if not source.exists():
        print(f"[FAIL] GeoJSON tidak ditemukan: {source}")
        return 1

    provinces = load_provinces(source)
    print(f"[INFO] {len(provinces)} provinsi dimuat dari {source}")

    started = time.perf_counter()
    cell_lat: list[int] = []
    cell_lon: list[int] = []
    names: list[str] = []

    lat = LAT_MIN + STEP / 2
    total = 0
    while lat < LAT_MAX:
        lon = LON_MIN + STEP / 2
        # Kunci sel memakai floor agar konsisten dengan Spark (round beda untuk .5).
        iy = math.floor(lat / STEP)
        while lon < LON_MAX:
            total += 1
            found = province_for_cell(lat, lon, provinces)
            if found:
                cell_lat.append(iy)
                cell_lon.append(math.floor(lon / STEP))
                names.append(found)
            lon += STEP
        lat += STEP

    elapsed = time.perf_counter() - started
    table = pa.table(
        {
            "cell_lat": pa.array(cell_lat, type=pa.int32()),
            "cell_lon": pa.array(cell_lon, type=pa.int32()),
            "province": pa.array(names, type=pa.string()),
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output, compression="snappy")

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_geojson": str(source),
        "step_degrees": STEP,
        "cells_tested": total,
        "cells_with_province": len(names),
        "provinces": len(provinces),
        "elapsed_seconds": round(elapsed, 2),
    }
    output.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(
        f"[SUCCESS] {len(names):,} sel provinsi dari {total:,} sel diuji "
        f"dalam {elapsed:.1f}s -> {output}"
    )
    print(f"[INFO] Metadata: {output.with_suffix('.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
