import os
import json
import uuid
import shutil
import csv
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.models import get_db, Dataset
from app.schemas.dataset import (
    DatasetUploadInitRequest, DatasetUploadInitResponse,
    DatasetUploadChunkResponse, DatasetUploadCompleteRequest,
    DatasetItem, DatasetSummaryResponse, DatasetPreviewResponse
)
from app.services.hdfs_cli import hdfs_put, hdfs_du, hdfs_rm, run_hdfs

router = APIRouter(prefix="/datasets", tags=["Datasets"])

UPLOAD_METADATA = {}

@router.post("/upload/init", response_model=DatasetUploadInitResponse)
def init_upload(req: DatasetUploadInitRequest):
    if not req.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Hanya file berekstensi .csv yang diizinkan.")
    
    if req.dataset_type not in ["firms_hist", "firms_nrt", "weather", "generic"]:
        raise HTTPException(status_code=400, detail="Tipe dataset tidak valid.")

    upload_id = str(uuid.uuid4())
    staging_upload_dir = settings.STAGING_DIR / upload_id
    staging_upload_dir.mkdir(parents=True, exist_ok=True)

    UPLOAD_METADATA[upload_id] = {
        "filename": req.filename,
        "dataset_type": req.dataset_type,
        "total_size": req.total_size,
        "total_chunks": req.total_chunks,
        "chunks_received": set(),
        "staging_dir": staging_upload_dir
    }

    return DatasetUploadInitResponse(upload_id=upload_id, chunk_size=8 * 1024 * 1024)

@router.post("/upload/chunk", response_model=DatasetUploadChunkResponse)
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...)
):
    meta = UPLOAD_METADATA.get(upload_id)
    if not meta:
        # Periksa apakah direktori staging ada di disk
        staging_upload_dir = settings.STAGING_DIR / upload_id
        if not staging_upload_dir.exists():
            raise HTTPException(status_code=404, detail="Upload session tidak ditemukan.")
        meta = {
            "staging_dir": staging_upload_dir,
            "chunks_received": set()
        }
        UPLOAD_METADATA[upload_id] = meta

    chunk_path = meta["staging_dir"] / f"chunk_{chunk_index:05d}.part"
    with open(chunk_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    meta["chunks_received"].add(chunk_index)
    return DatasetUploadChunkResponse(chunk_index=chunk_index, received=True)

@router.post("/upload/complete", response_model=DatasetItem)
def complete_upload(req: DatasetUploadCompleteRequest, db: Session = Depends(get_db)):
    meta = UPLOAD_METADATA.get(req.upload_id)
    staging_upload_dir = settings.STAGING_DIR / req.upload_id
    if not staging_upload_dir.exists():
        raise HTTPException(status_code=404, detail="Upload staging folder tidak ditemukan.")

    filename = meta.get("filename", "dataset.csv") if meta else "dataset.csv"
    dataset_type = meta.get("dataset_type", "generic") if meta else "generic"

    merged_file = staging_upload_dir / filename
    chunk_files = sorted(staging_upload_dir.glob("chunk_*.part"))
    if not chunk_files:
        raise HTTPException(status_code=400, detail="Tidak ada chunk yang ditemukan untuk digabung.")

    # Gabung chunk secara streaming (tanpa memuat seluruh isi file ke memori)
    total_bytes = 0
    row_count = 0
    headers = []

    with open(merged_file, "wb") as outfile:
        for chunk in chunk_files:
            with open(chunk, "rb") as infile:
                shutil.copyfileobj(infile, outfile, length=1024 * 1024)

    # Hitung baris dan baca header secara streaming
    with open(merged_file, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            headers = []
        for _ in reader:
            row_count += 1

    local_size = merged_file.stat().st_size

    # Tentukan path tujuan HDFS
    clean_filename = filename.replace(" ", "_")
    hdfs_target_dir = f"{settings.HDFS_BASE_PATH}/raw/{dataset_type}"
    hdfs_dest = f"{hdfs_target_dir}/{clean_filename}"

    # Jalankan hdfs dfs -put -f
    success, err = hdfs_put(merged_file, hdfs_dest)
    if not success:
        shutil.rmtree(staging_upload_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Gagal upload ke HDFS: {err}")

    # Verifikasi ukuran di HDFS
    hdfs_size = hdfs_du(hdfs_dest)
    if hdfs_size < 0:
        # du gagal mendeteksi
        hdfs_size = local_size

    # Bersihkan folder staging lokal
    shutil.rmtree(staging_upload_dir, ignore_errors=True)
    if req.upload_id in UPLOAD_METADATA:
        del UPLOAD_METADATA[req.upload_id]

    # Simpan metadata ke SQLite
    ds_id = str(uuid.uuid4())[:8]
    ds = Dataset(
        id=ds_id,
        name=clean_filename,
        dataset_type=dataset_type,
        hdfs_path=hdfs_dest,
        size_bytes=hdfs_size,
        row_count=row_count,
        column_count=len(headers),
        columns_json=json.dumps(headers),
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    return DatasetItem(
        id=ds.id,
        name=ds.name,
        dataset_type=ds.dataset_type,
        hdfs_path=ds.hdfs_path,
        size_bytes=ds.size_bytes,
        row_count=ds.row_count,
        column_count=ds.column_count,
        columns=headers,
        uploaded_at=ds.uploaded_at
    )

@router.get("", response_model=List[DatasetItem])
def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()
    results = []
    for d in datasets:
        cols = json.loads(d.columns_json) if d.columns_json else []
        results.append(DatasetItem(
            id=d.id,
            name=d.name,
            dataset_type=d.dataset_type,
            hdfs_path=d.hdfs_path,
            size_bytes=d.size_bytes,
            row_count=d.row_count,
            column_count=d.column_count,
            columns=cols,
            uploaded_at=d.uploaded_at
        ))
    return results

@router.get("/summary", response_model=DatasetSummaryResponse)
def get_summary(db: Session = Depends(get_db)):
    datasets = db.query(Dataset).all()
    total_files = len(datasets)
    total_size = sum(d.size_bytes for d in datasets)
    total_rows = sum(d.row_count for d in datasets)

    breakdown = {}
    for d in datasets:
        t = d.dataset_type
        if t not in breakdown:
            breakdown[t] = {"count": 0, "rows": 0, "size_bytes": 0}
        breakdown[t]["count"] += 1
        breakdown[t]["rows"] += d.row_count
        breakdown[t]["size_bytes"] += d.size_bytes

    return DatasetSummaryResponse(
        total_files=total_files,
        total_size_bytes=total_size,
        total_rows=total_rows,
        meets_1m_target=(total_rows >= 1_000_000),
        breakdown_by_type=breakdown
    )

@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def get_preview(dataset_id: str, limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan.")

    # Ambil sample preview baris menggunakan hdfs dfs -text atau -cat melalui pipe head
    # hdfs dfs -text hdfs_path | head -n (limit+1)
    code, stdout, stderr = run_hdfs(["-text", ds.hdfs_path])
    preview_rows = []
    columns = json.loads(ds.columns_json) if ds.columns_json else []

    if code == 0 and stdout:
        lines = stdout.splitlines()[:limit + 1]
        if lines:
            reader = csv.reader(lines)
            try:
                headers = next(reader)
                if not columns:
                    columns = headers
            except StopIteration:
                headers = []
            for row in reader:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i] if i < len(row) else ""
                preview_rows.append(row_dict)

    return DatasetPreviewResponse(
        id=ds.id,
        name=ds.name,
        total_rows=ds.row_count,
        columns=columns,
        preview_rows=preview_rows
    )

@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan.")

    success, err = hdfs_rm(ds.hdfs_path)
    if not success:
        raise HTTPException(status_code=500, detail=f"Gagal menghapus file dari HDFS: {err}")

    db.delete(ds)
    db.commit()
    return {"status": "success", "message": f"Dataset {ds.name} berhasil dihapus dari HDFS dan database."}

