"""Endpoint analitik deskriptif dari serving layer (AC-5, FR-A1..A4, A7).

Semua angka berasal dari tabel agregat (`agg_daily_province`, `agg_daily_grid`)
yang dilayani DuckDB - tidak ada perhitungan di sisi klien. Insight memakai
bahasa asosiasi (ANALYTICS_SPEC Bagian 3); langkah yang membutuhkan data cuaca
atau model (Fase 6) dikembalikan sebagai `available: false`, bukan angka palsu.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.pipeline.spark_runner import queue
from app.services import serving

router = APIRouter(prefix="/analytics", tags=["analitik"])

DAY_WINDOWS = (7, 30, 90, 365, 0)  # 0 = semua riwayat
MONTHS_ID = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _num(value: int | float) -> str:
    """Format angka gaya Indonesia: 1.234.567 dan 51,5."""
    if isinstance(value, float):
        return f"{value:,.1f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"{value:,}".replace(",", ".")


def _check_window(days: int) -> None:
    if days not in DAY_WINDOWS:
        raise HTTPException(status_code=422, detail=f"days harus salah satu dari {list(DAY_WINDOWS)}")


def _col(conf: str) -> str:
    if conf == "all":
        return "hotspot_count"
    if conf == "high":
        return "high_count"
    raise HTTPException(status_code=422, detail="conf harus 'all' atau 'high'")


def _filters(province: str | None, conf: str) -> tuple[str, list[Any]]:
    clauses = ["province <> 'UNKNOWN'"]
    params: list[Any] = []
    if province:
        clauses.append("province = ?")
        params.append(province)
    return " AND ".join(clauses), params


def _rows(sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    return serving.query(sql, params or [])


@router.get("/kpi", summary="KPI hero: hari ini, 7/30 hari, provinsi tertinggi, FRP")
def kpi(
    conf: Annotated[str, Query(description="all | high")] = "all",
) -> dict[str, Any]:
    column = _col(conf)
    where, params = _filters(None, conf)

    def produce() -> dict[str, Any]:
        row = _rows(
            f"""
            WITH base AS (
                SELECT date, sum({column}) AS c, sum(frp_sum) AS frp_sum
                FROM agg_daily_province
                WHERE {where}
                GROUP BY date
            ), bounds AS (SELECT max(date) AS max_date, min(date) AS min_date FROM base)
            SELECT
              (SELECT max_date FROM bounds) AS max_date,
              (SELECT min_date FROM bounds) AS min_date,
              (SELECT coalesce(sum(c), 0) FROM base WHERE date = (SELECT max_date FROM bounds)) AS today,
              (SELECT coalesce(sum(c), 0) FROM base WHERE date > (SELECT max_date FROM bounds) - 7) AS last_7d,
              (SELECT coalesce(sum(c), 0) FROM base WHERE date > (SELECT max_date FROM bounds) - 30) AS last_30d,
              (SELECT coalesce(sum(c), 0) FROM base WHERE date = (SELECT max_date FROM bounds) - 1) AS yesterday,
              (SELECT coalesce(sum(c), 0) FROM base WHERE date > (SELECT max_date FROM bounds) - 14
                 AND date <= (SELECT max_date FROM bounds) - 7) AS prev_7d,
              (SELECT coalesce(sum(c), 0) FROM base WHERE date > (SELECT max_date FROM bounds) - 60
                 AND date <= (SELECT max_date FROM bounds) - 30) AS prev_30d,
              (SELECT coalesce(sum(frp_sum), 0) FROM base WHERE date > (SELECT max_date FROM bounds) - 30)
                / nullif((SELECT coalesce(sum(c), 0) FROM base WHERE date > (SELECT max_date FROM bounds) - 30), 0) AS avg_frp_30d
            """,
            params,
        )[0]

        top = _rows(
            f"""
            SELECT province, sum({column}) AS c
            FROM agg_daily_province
            WHERE {where} AND date > (SELECT max(date) FROM agg_daily_province) - 30
            GROUP BY province ORDER BY c DESC LIMIT 1
            """,
            params,
        )
        high = _rows(
            f"""
            SELECT coalesce(sum(high_count), 0) AS c
            FROM agg_daily_province
            WHERE {where} AND date > (SELECT max(date) FROM agg_daily_province) - 30
            """,
            params,
        )[0]

        max_date = row["max_date"]
        return {
            "today": int(row["today"] or 0),
            "yesterday": int(row["yesterday"] or 0),
            "last_7d": int(row["last_7d"] or 0),
            "prev_7d": int(row["prev_7d"] or 0),
            "last_30d": int(row["last_30d"] or 0),
            "prev_30d": int(row["prev_30d"] or 0),
            "top_province": {"name": top[0]["province"], "count": int(top[0]["c"])} if top else None,
            "high_confidence_30d": int(high["c"] or 0),
            "avg_frp_30d": round(float(row["avg_frp_30d"] or 0), 2),
            "meta": {
                "computed_at": _now(),
                "conf": conf,
                "max_date": str(max_date) if max_date else None,
                "history_start": str(row["min_date"]) if row["min_date"] else None,
                "n_days": (
                    (max_date - row["min_date"]).days + 1
                    if isinstance(max_date, date) and isinstance(row["min_date"], date)
                    else 0
                ),
            },
        }

    return serving.cached(("analytics-kpi", conf), produce)


@router.get("/trend", summary="Tren harian/mingguan/bulanan")
def trend(
    granularity: Annotated[str, Query(description="day | week | month")] = "day",
    days: Annotated[int, Query(description="7, 30, 90, 365, atau 0 (semua)")] = 90,
    province: Annotated[str | None, Query()] = None,
    conf: Annotated[str, Query(description="all | high")] = "all",
) -> dict[str, Any]:
    _check_window(days)
    if granularity not in ("day", "week", "month"):
        raise HTTPException(status_code=422, detail="granularity harus day, week, atau month")
    column = _col(conf)
    where, params = _filters(province, conf)
    bucket = f"date_trunc('{granularity}', date)"

    def produce() -> dict[str, Any]:
        rows = _rows(
            f"""
            SELECT {bucket} AS bucket,
                   sum({column}) AS count,
                   sum(high_count) AS high_count
            FROM agg_daily_province
            WHERE {where}
              AND (? = 0 OR date > (SELECT max(date) FROM agg_daily_province) - ?)
            GROUP BY bucket ORDER BY bucket
            """,
            [*params, days, days],
        )
        return {
            "points": [
                {
                    "date": str(row["bucket"])[:10],
                    "count": int(row["count"] or 0),
                    "high_count": int(row["high_count"] or 0),
                }
                for row in rows
            ],
            "meta": {
                "computed_at": _now(),
                "granularity": granularity,
                "days": days,
                "province": province,
                "conf": conf,
                "n": len(rows),
            },
        }

    return serving.cached(("analytics-trend", granularity, days, province, conf), produce)


@router.get("/ranking", summary="Ranking provinsi + pangsa + delta periode sebelumnya")
def ranking(
    days: Annotated[int, Query(description="7, 30, 90, 365, atau 0 (semua)")] = 30,
    limit: Annotated[int, Query(ge=1, le=38)] = 38,
    conf: Annotated[str, Query(description="all | high")] = "all",
) -> dict[str, Any]:
    _check_window(days)
    column = _col(conf)

    def produce() -> dict[str, Any]:
        if days:
            rows = _rows(
                f"""
                WITH bounds AS (SELECT max(date) AS max_date FROM agg_daily_province)
                SELECT province,
                       sum(CASE WHEN date > (SELECT max_date FROM bounds) - ? THEN {column} ELSE 0 END) AS current,
                       sum(CASE WHEN date > (SELECT max_date FROM bounds) - ? * 2
                                 AND date <= (SELECT max_date FROM bounds) - ? THEN {column} ELSE 0 END) AS previous
                FROM agg_daily_province
                WHERE province <> 'UNKNOWN'
                GROUP BY province
                """,
                [days, days, days],
            )
        else:
            rows = _rows(
                f"""
                SELECT province, sum({column}) AS current, 0 AS previous
                FROM agg_daily_province
                WHERE province <> 'UNKNOWN'
                GROUP BY province
                """,
            )
        total = sum(int(row["current"] or 0) for row in rows)
        ranked = sorted(rows, key=lambda row: int(row["current"] or 0), reverse=True)[:limit]
        items = []
        for index, row in enumerate(ranked, start=1):
            current = int(row["current"] or 0)
            previous = int(row["previous"] or 0)
            delta = round((current - previous) / previous * 100, 1) if previous else None
            items.append(
                {
                    "rank": index,
                    "province": row["province"],
                    "count": current,
                    "share_percent": round(current / total * 100, 1) if total else 0.0,
                    "previous": previous,
                    "delta_percent": delta,
                }
            )
        return {
            "items": items,
            "meta": {
                "computed_at": _now(),
                "days": days,
                "conf": conf,
                "total": total,
                "n": len(items),
            },
        }

    return serving.cached(("analytics-ranking", days, conf), produce)


@router.get("/seasonality", summary="Heatmap bulan x tahun dan bulan x provinsi")
def seasonality(
    province: Annotated[str | None, Query()] = None,
    conf: Annotated[str, Query(description="all | high")] = "all",
) -> dict[str, Any]:
    column = _col(conf)
    where, params = _filters(province, conf)

    def produce() -> dict[str, Any]:
        year_rows = _rows(
            f"""
            SELECT year(date) AS y, month(date) AS m, sum({column}) AS c
            FROM agg_daily_province
            WHERE {where}
            GROUP BY y, m ORDER BY y, m
            """,
            params,
        )
        years = sorted({int(row["y"]) for row in year_rows})
        matrix: dict[int, list[float]] = {
            year: [0.0] * 12 for year in years
        }
        for row in year_rows:
            matrix[int(row["y"])][int(row["m"]) - 1] = int(row["c"] or 0)

        province_rows = _rows(
            f"""
            SELECT province, month(date) AS m, sum({column}) AS c
            FROM agg_daily_province
            WHERE province <> 'UNKNOWN'
              {"AND province = ?" if province else ""}
            GROUP BY province, m
            """,
            [province] if province else None,
        )
        totals: dict[str, int] = {}
        per_province: dict[str, list[float]] = {}
        for row in province_rows:
            per_province.setdefault(str(row["province"]), [0.0] * 12)[int(row["m"]) - 1] = int(row["c"] or 0)
        top_provinces = sorted(per_province, key=lambda key: sum(per_province[key]), reverse=True)[:10]

        return {
            "months": MONTHS_ID[1:],
            "years": years,
            "by_year": {year: matrix[year] for year in years},
            "by_province": {key: per_province[key] for key in top_provinces},
            "meta": {
                "computed_at": _now(),
                "province": province,
                "conf": conf,
                "n_years": len(years),
                "n_provinces": len(per_province),
                "years_covered": f"{years[0]}-{years[-1]}" if years else None,
            },
        }

    return serving.cached(("analytics-seasonality", province, conf), produce)


@router.get("/year-compare", summary="Kumulatif hotspot per hari dalam tahun (FP5)")
def year_compare(
    province: Annotated[str | None, Query()] = None,
    conf: Annotated[str, Query(description="all | high")] = "all",
) -> dict[str, Any]:
    column = _col(conf)
    where, params = _filters(province, conf)

    def produce() -> dict[str, Any]:
        rows = _rows(
            f"""
            SELECT year(date) AS y,
                   dayofyear(date) AS doy,
                   sum({column}) AS c
            FROM agg_daily_province
            WHERE {where}
            GROUP BY y, doy ORDER BY y, doy
            """,
            params,
        )
        series: dict[int, list[dict[str, int]]] = {}
        running: dict[int, int] = {}
        for row in rows:
            year = int(row["y"])
            running[year] = running.get(year, 0) + int(row["c"] or 0)
            series.setdefault(year, []).append({"doy": int(row["doy"]), "cum": running[year]})

        years = sorted(series)
        if not years:
            return {"years": [], "historical_mean": [], "meta": {"computed_at": _now(), "n": 0}}
        current = max(years)
        past = [year for year in years if year != current]
        mean_points: list[dict[str, float]] = []
        if past:
            max_doy = max(point["doy"] for year in past for point in series[year])
            for doy in range(1, max_doy + 1):
                values = [
                    max((point["cum"] for point in series[year] if point["doy"] <= doy), default=0)
                    for year in past
                ]
                if values:
                    mean_points.append(
                        {"doy": doy, "cum": round(sum(values) / len(values), 1)}
                    )
        return {
            "years": [{"year": year, "points": series[year]} for year in years],
            "current_year": current,
            "historical_mean": mean_points,
            "meta": {
                "computed_at": _now(),
                "province": province,
                "conf": conf,
                "n_years": len(years),
            },
        }

    return serving.cached(("analytics-year", province, conf), produce)


@router.get("/top-grid", summary="Grid dengan hotspot terbanyak pada periode")
def top_grid(
    days: Annotated[int, Query(description="7, 30, 90, 365, atau 0 (semua)")] = 30,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    province: Annotated[str | None, Query()] = None,
    conf: Annotated[str, Query(description="all | high")] = "all",
) -> dict[str, Any]:
    _check_window(days)
    column = _col(conf)
    province_clause = "AND province = ?" if province else ""
    base_params: list[Any] = [province] if province else []

    def produce() -> dict[str, Any]:
        rows = _rows(
            f"""
            SELECT grid_lat, grid_lon, max(province) AS province,
                   sum({column}) AS c, sum(high_count) AS high_count
            FROM agg_daily_grid
            WHERE (? = 0 OR date > (SELECT max(date) FROM agg_daily_grid) - ?)
              {province_clause}
            GROUP BY grid_lat, grid_lon
            ORDER BY c DESC
            LIMIT ?
            """,
            [days, days, *base_params, limit],
        )
        return {
            "items": [
                {
                    "grid_lat": float(row["grid_lat"]),
                    "grid_lon": float(row["grid_lon"]),
                    "province": row["province"],
                    "count": int(row["c"] or 0),
                    "high_count": int(row["high_count"] or 0),
                }
                for row in rows
            ],
            "meta": {"computed_at": _now(), "days": days, "province": province, "conf": conf, "n": len(rows)},
        }

    return serving.cached(("analytics-top-grid", days, limit, province, conf), produce)


@router.get("/weather-correlation", summary="Korelasi cuaca vs hotspot (butuh data cuaca)")
def weather_correlation() -> dict[str, Any]:
    return {
        "available": False,
        "reason": "Data cuaca belum lengkap di serving layer (clean/weather kosong pada HDFS).",
        "needs": ["raw/weather CHIRPS + ERA5 terisi", "preprocessing clean/weather", "features/grid_daily (Fase 6)"],
        "computed_at": _now(),
    }


@router.get("/insights", summary="Kartu insight otomatis (rule-based, bahasa asosiasi)")
def insights(
    days: Annotated[int, Query(description="30, 90, 365, atau 0 (semua)")] = 30,
    province: Annotated[str | None, Query()] = None,
    conf: Annotated[str, Query(description="all | high")] = "all",
) -> dict[str, Any]:
    _check_window(days)
    if days == 7:
        raise HTTPException(status_code=422, detail="insights butuh jendela >= 30 hari")
    column = _col(conf)
    scope_label = province or "nasional"

    def produce() -> dict[str, Any]:
        cards: list[dict[str, Any]] = []
        computed_at = _now()

        # I1 - Tren 7 hari vs 7 hari sebelumnya.
        scope_where, scope_params = _filters(province, conf)
        trend_rows = _rows(
            f"""
            WITH bounds AS (SELECT max(date) AS max_date FROM agg_daily_province)
            SELECT sum(CASE WHEN date > (SELECT max_date FROM bounds) - 7 THEN {column} ELSE 0 END) AS recent,
                   sum(CASE WHEN date > (SELECT max_date FROM bounds) - 14
                             AND date <= (SELECT max_date FROM bounds) - 7 THEN {column} ELSE 0 END) AS prior
            FROM agg_daily_province
            WHERE {scope_where}
            """,
            scope_params,
        )[0]
        recent, prior = int(trend_rows["recent"] or 0), int(trend_rows["prior"] or 0)
        if recent + prior >= 30:
            pct = round((recent - prior) / prior * 100, 1) if prior else None
            direction = "naik" if (pct or 0) > 0 else "turun"
            magnitude = abs(pct or 0)
            cards.append(
                {
                    "id": "I1",
                    "type": "tren",
                    "score": min(100, magnitude),
                    "title": "Tren 7 hari",
                    "key_figure": f"{'+' if (pct or 0) >= 0 else ''}{_num(float(pct or 0))}%",
                    "sentence": (
                        f"Hotspot {scope_label} {direction} {_num(abs(pct or 0))}% dalam 7 hari terakhir "
                        f"dibanding 7 hari sebelumnya ({_num(recent)} vs {_num(prior)})."
                        if pct is not None
                        else f"Periode sebelumnya tanpa hotspot; 7 hari terakhir {_num(recent)} hotspot."
                    ),
                    "confidence": ("Tinggi" if (recent + prior) >= 500 and magnitude >= 40
                                   else "Sedang" if (recent + prior) >= 100 and magnitude >= 25 else "Rendah"),
                    "evidence": {
                        "recent_7d": recent,
                        "prior_7d": prior,
                        "n": recent + prior,
                        "window": "7 hari vs 7 hari sebelumnya",
                        "computed_at": computed_at,
                    },
                    "anchor": "ringkasan",
                }
            )

        # I2 - Pangsa tiga provinsi teratas.
        ranking_rows = _rows(
            f"""
            SELECT province, sum({column}) AS c
            FROM agg_daily_province
            WHERE province <> 'UNKNOWN'
              AND (? = 0 OR date > (SELECT max(date) FROM agg_daily_province) - ?)
            GROUP BY province ORDER BY c DESC
            """,
            [days, days],
        )
        total = sum(int(row["c"] or 0) for row in ranking_rows)
        if not province and total >= 100 and len(ranking_rows) >= 3:
            top3 = ranking_rows[:3]
            share = round(sum(int(row["c"] or 0) for row in top3) / total * 100, 1)
            cards.append(
                {
                    "id": "I2",
                    "type": "wilayah",
                    "score": min(100, share),
                    "title": "Konsentrasi wilayah",
                    "key_figure": f"{_num(float(share))}%",
                    "sentence": (
                        f"{top3[0]['province']}, {top3[1]['province']}, dan {top3[2]['province']} "
                        f"menyumbang {_num(share)}% hotspot pada periode ini."
                    ),
                    "confidence": ("Tinggi" if total >= 500 and share >= 50
                                   else "Sedang" if total >= 100 and share >= 35 else "Rendah"),
                    "evidence": {
                        "top3": [{"province": row["province"], "count": int(row["c"] or 0)} for row in top3],
                        "total": total,
                        "n": total,
                        "window": f"{days} hari" if days else "semua riwayat",
                        "computed_at": computed_at,
                    },
                    "anchor": "wilayah",
                }
            )

        # I6 - Puncak musiman historis.
        month_rows = _rows(
            f"""
            SELECT month(date) AS m, sum({column}) AS c
            FROM agg_daily_province
            WHERE {scope_where}
            GROUP BY m ORDER BY c DESC
            """,
            scope_params,
        )
        month_total = sum(int(row["c"] or 0) for row in month_rows)
        if month_rows and month_total >= 500:
            peak = month_rows[0]
            peak_month = int(peak["m"])
            current_month = datetime.now(timezone.utc).month
            forward = (peak_month - current_month) % 12
            if forward == 0:
                position = "di dalam"
            elif forward <= 6:
                position = "sebelum"
            else:
                position = "setelah"
            cards.append(
                {
                    "id": "I6",
                    "type": "musiman",
                    "score": min(100, round(int(peak["c"] or 0) / month_total * 100, 1)),
                    "title": "Puncak musiman",
                    "key_figure": MONTHS_ID[peak_month],
                    "sentence": (
                        f"Secara historis, puncak hotspot terjadi pada bulan {MONTHS_ID[peak_month]} "
                        f"({_num(int(peak['c'] or 0))} hotspot, "
                        f"{_num(round(int(peak['c'] or 0) / month_total * 100, 1))}% dari total); "
                        f"saat ini {position} periode puncak."
                    ),
                    "confidence": "Tinggi" if month_total >= 5000 else "Sedang",
                    "evidence": {
                        "peak_month": MONTHS_ID[peak_month],
                        "peak_count": int(peak["c"] or 0),
                        "share_percent": round(int(peak["c"] or 0) / month_total * 100, 1),
                        "n": month_total,
                        "window": "semua riwayat",
                        "computed_at": computed_at,
                    },
                    "anchor": "musiman",
                }
            )

        cards.sort(key=lambda card: card["score"], reverse=True)
        return {
            "cards": cards[:7],
            "meta": {
                "computed_at": computed_at,
                "days": days,
                "province": province,
                "conf": conf,
                "scope": scope_label,
                "n": len(cards),
                "skipped": [
                    {"id": "I3/I4/I5", "reason": "butuh data cuaca (belum lengkap)"},
                    {"id": "I7", "reason": "butuh model prediksi (Fase 6)"},
                    {"id": "I8", "reason": "butuh data validasi eksternal (Fase 8)"},
                ],
            },
        }

    return serving.cached(("analytics-insights", days, province, conf), produce)


@router.post("/refresh", summary="Jalankan ulang agregasi serving layer (FR-A7)")
def refresh() -> dict[str, Any]:
    job_id = f"aggregate-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    submission = queue.submit(
        job_id,
        "AGGREGATION",
        "aggregate.py",
        ["--job-id", job_id],
        {"trigger": "analytics-refresh"},
    )
    return submission
