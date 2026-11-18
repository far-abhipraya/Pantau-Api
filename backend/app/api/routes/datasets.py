"""Endpoint dataset: daftar file di HDFS, pratinjau, hapus, dan upload manual."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.pipeline import catalog, hdfs, upload
from app.pipeline import job_manager as jm

router = APIRouter(prefix="/datasets", tags=["dataset"])


@router.get("", summary="Daftar dataset di HDFS + metadata ingest")
def list_datasets(
    source: Annotated[str | None, Query(description="filter jenis sumber")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
) -> dict[str, Any]:
    records = {row["hdfs_path"]: row for row in jm.list_datasets(limit=1000)}
    items: list[dict[str, Any]] = []
    for file in catalog.raw_files():
        record = records.pop(file["hdfs_path"], None)
        items.append(
            {
                **file,
                "id": record["id"] if record else None,
                "source": (record or {}).get("source") or file["origin"],
                "row_count": (record or {}).get("row_count"),
                "ingest_path": (record or {}).get("ingest_path") or "histori",
                "detected_format": (record or {}).get("detected_format"),
                "created_at": (record or {}).get("created_at"),
                "in_catalog": record is not None,
            }
        )
    # Metadata tanpa file di HDFS (mis. dihapus manual) tetap ditampilkan.
    for record in records.values():
        items.append(
            {
                "id": record["id"],
                "hdfs_path": record["hdfs_path"],
                "name": record["name"],
                "folder": record["hdfs_path"].split("/raw/")[-1].split("/")[0] if "/raw/" in record["hdfs_path"] else None,
                "origin": record["source"],
                "size_bytes": record["size_bytes"],
                "modified": record["created_at"],
                "source": record["source"],
                "row_count": record["row_count"],
                "ingest_path": record["ingest_path"],
                "detected_format": record["detected_format"],
                "created_at": record["created_at"],
                "in_catalog": True,
                "missing_in_hdfs": True,
            }
        )

    if source:
        items = [item for item in items if (item.get("source") or "").lower() == source.lower()]

    items.sort(key=lambda item: (item.get("created_at") or "", item["name"]), reverse=True)
    items = items[:limit]
    return {
        "items": items,
        "meta": {
            "count": len(items),
            "summary": jm.datasets_summary(),
            "sources": sorted({item.get("source") for item in items if item.get("source")}),
        },
    }


@router.get("/{dataset_id}/preview", summary="Pratinjau isi file dataset")
def preview_dataset(
    dataset_id: int,
    limit: Annotated[int, Query(ge=1, le=200)] = 30,
) -> dict[str, Any]:
    record = jm.get_dataset(dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    path = record["hdfs_path"]
    if not hdfs.is_within_base(path):
        raise HTTPException(status_code=403, detail="Path di luar /karhutla")
    lines = hdfs.head_lines(path, limit=limit + 1)
    if not lines:
        raise HTTPException(status_code=404, detail="File tidak ada atau kosong di HDFS")
    columns = [c.strip() for c in lines[0].split(",")]
    rows = [line.split(",") for line in lines[1:limit + 1]]
    return {
        "id": dataset_id,
        "name": record["name"],
        "hdfs_path": path,
        "columns": columns,
        "rows": rows,
        "preview_limit": limit,
        "truncated": len(lines) > limit,
    }


@router.delete("/{dataset_id}", summary="Hapus file dataset (hanya di bawah /karhutla)")
def delete_dataset(dataset_id: int) -> dict[str, Any]:
    record = jm.get_dataset(dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    path = record["hdfs_path"]
    if not hdfs.is_within_base(path):
        raise HTTPException(status_code=403, detail="Penghapusan hanya di bawah /karhutla")
    try:
        hdfs.remove(path)
    except hdfs.HdfsError as exc:
        raise HTTPException(status_code=502, detail=f"Hapus HDFS gagal: {exc}") from exc
    jm.delete_dataset(dataset_id)
    catalog.invalidate()
    return {"deleted": True, "id": dataset_id, "hdfs_path": path}


# --- Upload manual (jalur tambahan) ----------------------------------------


@router.post("/upload/init", summary="Mulai sesi upload bertahap")
def upload_init(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return upload.init(str(payload.get("filename", "")), int(payload.get("size_bytes", 0)))
    except (upload.UploadError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/upload/chunk", summary="Unggah satu potongan file")
async def upload_chunk(
    upload_id: Annotated[str, Form()],
    index: Annotated[int, Form()],
    file: Annotated[UploadFile, File()],
) -> dict[str, Any]:
    payload = await file.read()
    try:
        return upload.append_chunk(upload_id, index, payload)
    except upload.UploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/detect", summary="Deteksi format file yang diunggah (tanpa memproses)")
def detect(payload: dict[str, Any]) -> dict[str, Any]:
    upload_id = str(payload.get("upload_id", ""))
    try:
        return upload.detect(upload_id)
    except upload.UploadError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/upload/complete", summary="Selesaikan upload -> HDFS -> pipeline")
def upload_complete(payload: dict[str, Any]) -> dict[str, Any]:
    upload_id = str(payload.get("upload_id", ""))
    run_pipeline = bool(payload.get("run_pipeline", True))
    try:
        return upload.complete(upload_id, run_pipeline=run_pipeline)
    except upload.UploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/upload/{upload_id}", summary="Batalkan sesi upload")
def upload_cancel(upload_id: str) -> dict[str, Any]:
    try:
        removed = upload.cancel(upload_id)
    except upload.UploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Sesi upload tidak ditemukan")
    return {"cancelled": True, "upload_id": upload_id}
