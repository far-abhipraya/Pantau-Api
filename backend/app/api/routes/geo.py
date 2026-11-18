"""Endpoint geospasial: batas provinsi untuk peta dan choropleth."""
from __future__ import annotations

import gzip
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.core.config import settings

router = APIRouter(prefix="/geo", tags=["geo"])

_cache: dict[str, object] = {"mtime": None, "raw": b"", "gz": b"", "etag": ""}


def _load(path: Path) -> dict[str, object]:
    stat = path.stat()
    if _cache["mtime"] != stat.st_mtime:
        raw = path.read_bytes()
        _cache.update(
            mtime=stat.st_mtime,
            raw=raw,
            gz=gzip.compress(raw, compresslevel=6),
            etag=f'"{int(stat.st_mtime)}-{len(raw)}"',
        )
    return _cache


@router.get("/provinces", summary="GeoJSON batas provinsi (disederhanakan)")
def provinces_geojson(request: Request):
    path = Path(settings.GEOJSON_PROVINCES)
    if not path.exists():
        raise HTTPException(status_code=404, detail="GeoJSON provinsi belum tersedia")

    cached = _load(path)
    etag = str(cached["etag"])
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)

    headers = {
        "Cache-Control": "public, max-age=3600",
        "ETag": etag,
        "Vary": "Accept-Encoding",
    }
    if "gzip" in request.headers.get("accept-encoding", "").lower():
        return Response(
            content=cached["gz"],
            media_type="application/geo+json",
            headers={**headers, "Content-Encoding": "gzip"},
        )
    return Response(content=cached["raw"], media_type="application/geo+json", headers=headers)
