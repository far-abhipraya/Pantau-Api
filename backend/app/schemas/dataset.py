from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel

class DatasetUploadInitRequest(BaseModel):
    filename: str
    dataset_type: str  # firms_hist, firms_nrt, weather, generic
    total_size: int
    total_chunks: int

class DatasetUploadInitResponse(BaseModel):
    upload_id: str
    chunk_size: int

class DatasetUploadChunkResponse(BaseModel):
    chunk_index: int
    received: bool

class DatasetUploadCompleteRequest(BaseModel):
    upload_id: str

class DatasetItem(BaseModel):
    id: str
    name: str
    dataset_type: str
    hdfs_path: str
    size_bytes: int
    row_count: int
    column_count: int
    columns: List[str]
    uploaded_at: datetime

    class Config:
        from_attributes = True

class DatasetSummaryResponse(BaseModel):
    total_files: int
    total_size_bytes: int
    total_rows: int
    meets_1m_target: bool
    breakdown_by_type: Dict[str, Dict[str, Any]]

class DatasetPreviewResponse(BaseModel):
    id: str
    name: str
    total_rows: int
    columns: List[str]
    preview_rows: List[Dict[str, Any]]

