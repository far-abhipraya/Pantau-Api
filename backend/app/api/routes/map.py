"""Endpoint peta: titik hotspot, agregasi grid, ringkasan provinsi, KPI, risiko."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.services import serving

router = APIRouter(prefix="/map", tags=["peta"])

ALLOWED_HOURS = (24, 48, 168)
CONFIDENCE_SETS: dict[str, tuple[str, ...]] = {
    "all": ("low", "nominal", "high"),
    "nominal": ("nominal", "high"),
    "high": ("high",),
}
SENSORS: dict[str, str | None] = {"all": None, "viirs": "VIIRS", "modis": "MODIS"}


def _meta_point_ts() -> datetime:
    meta = serving.read_meta()
    raw = meta.get("max_acq_ts")
    if not raw:
        raise HTTPException(
            status_code=503,
            detail="Serving layer belum tersedia. Jalankan `spark-submit backend/spark_jobs/aggregate.py`.",
        )
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:  # pragma: no cover - data rusak
        raise HTTPException(status_code=503, detail="serving_meta.json tidak valid") from exc


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(status_code=422, detail="bbox harus 'minLon,minLat,maxLon,maxLat'")
    try:
        min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="bbox harus berisi angka") from exc
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=422, detail="bbox tidak valid: min harus < max")
    if min_lat < -90 or max_lat > 90 or min_lon < -180 or max_lon > 180:
        raise HTTPException(status_code=422, detail="bbox di luar rentang koordinat")
    return min_lon, min_lat, max_lon, max_lat


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _iso_utc(value: Any) -> Any:
    """Timestamp DuckDB tanpa zona diperlakukan sebagai UTC (kolom *_utc)."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value


def _features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        props = {k: _iso(v) for k, v in row.items() if k not in ("longitude", "latitude")}
        out.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
                "properties": props,
            }
        )
    return out


@router.get("/hotspots", summary="Titik hotspot dalam bbox dan jendela waktu")
def hotspots(
    bbox: Annotated[str, Query(description="minLon,minLat,maxLon,maxLat")],
    hours: Annotated[int, Query(description="24, 48, atau 168")] = 24,
    sensor: Annotated[str, Query(description="all | viirs | modis")] = "all",
    min_conf: Annotated[str, Query(description="all | nominal | high")] = "all",
    limit: Annotated[int, Query(ge=1, le=settings.MAP_MAX_POINTS)] = settings.MAP_MAX_POINTS,
) -> dict[str, Any]:
    if hours not in ALLOWED_HOURS:
        raise HTTPException(status_code=422, detail=f"hours harus salah satu dari {ALLOWED_HOURS}")
    if sensor not in SENSORS:
        raise HTTPException(status_code=422, detail="sensor harus all, viirs, atau modis")
    if min_conf not in CONFIDENCE_SETS:
        raise HTTPException(status_code=422, detail="min_conf harus all, nominal, atau high")

    min_lon, min_lat, max_lon, max_lat = _parse_bbox(bbox)
    max_ts = _meta_point_ts()
    start = serving.window_start(max_ts, hours)

    sql = [
        "SELECT latitude, longitude, acq_ts_wib, satellite, instrument,",
        "confidence_level, confidence_score, frp, province",
        "FROM hotspot_latest",
        "WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?",
        "AND acq_ts_utc >= ?",
    ]
    params: list[Any] = [min_lat, max_lat, min_lon, max_lon, start]
    if SENSORS[sensor]:
        sql.append("AND instrument = ?")
        params.append(SENSORS[sensor])
    confidence = CONFIDENCE_SETS[min_conf]
    if len(confidence) < 3:
        placeholders = ",".join("?" for _ in confidence)
        sql.append(f"AND confidence_level IN ({placeholders})")
        params.extend(confidence)
    sql.append("ORDER BY acq_ts_utc DESC LIMIT ?")
    params.append(limit + 1)

    rows = serving.query(" ".join(sql), params)
    truncated = len(rows) > limit
    rows = rows[:limit]

    return {
        "type": "FeatureCollection",
        "features": _features(rows),
        "meta": {
            "count": len(rows),
            "limit": limit,
            "truncated": truncated,
            "window_hours": hours,
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "max_acq_ts": max_ts.isoformat(),
            "freshness": serving.freshness(),
        },
    }


def _resolution_for_zoom(zoom: int) -> float:
    if zoom < 5:
        return 1.0
    if zoom < 8:
        return 0.5
    return 0.25


@router.get("/grid", summary="Agregasi grid per zoom dan jendela waktu")
def grid(
    bbox: Annotated[str, Query(description="minLon,minLat,maxLon,maxLat")],
    zoom: Annotated[int, Query(ge=0, le=18)] = 5,
    hours: Annotated[int, Query(description="24, 48, atau 168")] = 24,
    resolution: Annotated[float | None, Query(description="1.0, 0.5, atau 0.25")] = None,
) -> dict[str, Any]:
    if hours not in ALLOWED_HOURS:
        raise HTTPException(status_code=422, detail=f"hours harus salah satu dari {ALLOWED_HOURS}")
    step = resolution if resolution is not None else _resolution_for_zoom(zoom)
    if step not in (1.0, 0.5, 0.25):
        raise HTTPException(status_code=422, detail="resolution harus 1.0, 0.5, atau 0.25")

    min_lon, min_lat, max_lon, max_lat = _parse_bbox(bbox)
    table = f"grid_latest_{str(step).replace('.', '_')}"
    if not serving.available_tables().get(table):
        raise HTTPException(
            status_code=503,
            detail=f"Tabel {table} belum ada. Jalankan aggregate.py terlebih dahulu.",
        )

    rows = serving.query(
        f"""
        SELECT grid_lat, grid_lon, cell_lat, cell_lon, hotspot_count, high_count,
               nominal_count, low_count, frp_sum, frp_max, frp_avg, province
        FROM {table}
        WHERE window_hours = ?
          AND cell_lat BETWEEN ? AND ?
          AND cell_lon BETWEEN ? AND ?
        ORDER BY hotspot_count DESC
        """,
        [hours, min_lat, max_lat, min_lon, max_lon],
    )

    half = step / 2
    features = []
    for row in rows:
        lat, lon = row["grid_lat"], row["grid_lon"]
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [lon, lat],
                            [lon + step, lat],
                            [lon + step, lat + step],
                            [lon, lat + step],
                            [lon, lat],
                        ]
                    ],
                },
                "properties": {
                    "hotspot_count": row["hotspot_count"],
                    "high_count": row["high_count"],
                    "nominal_count": row["nominal_count"],
                    "low_count": row["low_count"],
                    "frp_sum": row["frp_sum"],
                    "frp_max": row["frp_max"],
                    "frp_avg": row["frp_avg"],
                    "province": row["province"],
                    "grid_lat": round(row["cell_lat"] - half, 4),
                    "grid_lon": round(row["cell_lon"] - half, 4),
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "count": len(features),
            "window_hours": hours,
            "resolution": step,
            "zoom": zoom,
            "bbox": [min_lon, min_lat, max_lon, max_lat],
        },
    }


@router.get("/kpi", summary="KPI ringkas untuk panel peta")
def kpi(hours: Annotated[int, Query(description="24, 48, atau 168")] = 24) -> dict[str, Any]:
    if hours not in ALLOWED_HOURS:
        raise HTTPException(status_code=422, detail=f"hours harus salah satu dari {ALLOWED_HOURS}")
    max_ts = _meta_point_ts()
    start = serving.window_start(max_ts, hours)

    def produce() -> dict[str, Any]:
        totals = serving.query_one(
            """
            SELECT count(*) AS hotspots,
                   sum(CASE WHEN confidence_level = 'high' THEN 1 ELSE 0 END) AS high_confidence,
                   max(acq_ts_utc) AS latest_acq_ts
            FROM hotspot_latest
            WHERE acq_ts_utc >= ?
            """,
            [start],
        )
        top = serving.query_one(
            """
            SELECT province, count(*) AS count
            FROM hotspot_latest
            WHERE acq_ts_utc >= ? AND province <> 'UNKNOWN'
            GROUP BY province
            ORDER BY count DESC
            LIMIT 1
            """,
            [start],
        )
        return {
            "window_hours": hours,
            "hotspots": int(totals["hotspots"] or 0),
            "high_confidence": int(totals["high_confidence"] or 0),
            "top_province": {"name": top["province"], "count": int(top["count"])} if top else None,
            "latest_acq_ts": _iso_utc(totals["latest_acq_ts"]),
            "freshness": serving.freshness(),
        }

    return serving.cached(("kpi", hours, max_ts.isoformat()), produce)


@router.get("/provinces", summary="Ringkasan hotspot per provinsi + tren 7 hari")
def provinces(
    hours: Annotated[int, Query(description="24 atau 168")] = 24,
) -> dict[str, Any]:
    if hours not in (24, 168):
        raise HTTPException(status_code=422, detail="hours harus 24 atau 168")
    if not serving.available_tables().get("agg_daily_province"):
        raise HTTPException(status_code=503, detail="agg_daily_province belum tersedia")

    def produce() -> dict[str, Any]:
        bounds = serving.query_one(
            "SELECT max(date) AS max_date FROM agg_daily_province"
        )
        max_date = bounds["max_date"]
        if max_date is None:
            return {"provinces": [], "meta": {"count": 0, "hours": hours}}
        if isinstance(max_date, datetime):
            max_date = max_date.date()
        window_days = 1 if hours == 24 else 7

        rows = serving.query(
            """
            SELECT province,
                   sum(CASE WHEN date > ? THEN hotspot_count ELSE 0 END) AS last_window,
                   sum(CASE WHEN date > ? AND date <= ? THEN hotspot_count ELSE 0 END) AS previous_window,
                   sum(CASE WHEN date > ? THEN hotspot_count ELSE 0 END) AS last_7d,
                   sum(CASE WHEN date > ? THEN high_count ELSE 0 END) AS high_last_window
            FROM agg_daily_province
            WHERE date > ? AND province <> 'UNKNOWN'
            GROUP BY province
            """,
            [
                max_date - timedelta(days=window_days),
                max_date - timedelta(days=window_days * 2),
                max_date - timedelta(days=window_days),
                max_date - timedelta(days=7),
                max_date - timedelta(days=window_days),
                max_date - timedelta(days=7),
            ],
        )
        trend_rows = serving.query(
            """
            SELECT province, date, hotspot_count
            FROM agg_daily_province
            WHERE date > ? AND province <> 'UNKNOWN'
            ORDER BY date
            """,
            [max_date - timedelta(days=7)],
        )
        trend: dict[str, list[dict[str, Any]]] = {}
        for row in trend_rows:
            trend.setdefault(row["province"], []).append(
                {"date": str(row["date"]), "count": int(row["hotspot_count"])}
            )

        ranked = sorted(rows, key=lambda r: int(r["last_7d"] or 0), reverse=True)
        payload = []
        for index, row in enumerate(ranked, start=1):
            payload.append(
                {
                    "province": row["province"],
                    "last_window": int(row["last_window"] or 0),
                    "previous_window": int(row["previous_window"] or 0),
                    "last_7d": int(row["last_7d"] or 0),
                    "high_last_window": int(row["high_last_window"] or 0),
                    "rank": index,
                    "trend": [
                        {"date": str(item["date"]), "count": int(item["count"])}
                        for item in trend.get(row["province"], [])
                    ],
                }
            )
        return {
            "provinces": payload,
            "meta": {
                "count": len(payload),
                "hours": hours,
                "max_date": str(max_date),
                "freshness": serving.freshness(),
            },
        }

    return serving.cached(("provinces", hours), produce)


@router.get("/risk", summary="Grid risiko prediksi 7 hari (Fase 6)")
def risk() -> dict[str, Any]:
    if not serving.available_tables().get("risk_prediction"):
        return {
            "type": "FeatureCollection",
            "features": [],
            "meta": {
                "available": False,
                "message": "Prediksi risiko belum tersedia. Jalankan job ML pada Fase 6.",
            },
        }
    rows = serving.query(
        """
        SELECT grid_id, lat, lon, target_date, horizon_days, risk_score, risk_category,
               model_version, predicted_at
        FROM risk_prediction
        ORDER BY risk_score DESC
        LIMIT ?
        """,
        [settings.MAP_MAX_POINTS],
    )
    features = []
    for row in rows:
        props = {k: _iso(v) for k, v in row.items() if k not in ("lat", "lon")}
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
                "properties": props,
            }
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "available": True,
            "count": len(features),
            "max_acq_ts": datetime.now(timezone.utc).isoformat(),
        },
    }
