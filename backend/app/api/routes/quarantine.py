"""Endpoint karantina: file/baris yang gagal diparse beserta alasannya."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.config import settings
from app.pipeline import job_manager as jm

router = APIRouter(prefix="/quarantine", tags=["karantina"])


@router.get("", summary="Daftar karantina dan alasan")
def list_quarantine(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    items = jm.list_quarantine(limit=limit)
    failed_dir = Path(settings.INBOX_FAILED_DIR)
    files = (
        [
            {"name": p.name, "size_bytes": p.stat().st_size}
            for p in sorted(failed_dir.glob("*"), reverse=True)
            if p.is_file()
        ]
        if failed_dir.exists()
        else []
    )
    return {
        "items": items,
        "meta": {"count": len(items), "failed_dir": str(failed_dir), "files": files[:limit]},
    }
