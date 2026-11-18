"""Endpoint pre-processing: skema konfigurasi, profiling, dan menjalankan pipeline."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.pipeline import job_manager as jm
from app.pipeline.spark_runner import queue

router = APIRouter(prefix="/preprocessing", tags=["pre-processing"])

RUNS_DIR = Path(settings.SERVING_DIR) / "runs"
CONFIG_DIR = Path(settings.SERVING_DIR) / "configs"
PROFILING_DIR = Path(settings.SERVING_DIR) / "profiling"
SUMMARY_PATH = Path(settings.SERVING_DIR) / "pipeline_run_summary.json"


# --- Skema konfigurasi (sumber kebenaran untuk stepper di UI) ---------------

CONFIG_SCHEMA: dict[str, Any] = {
    "steps": [
        {
            "key": "cleaning",
            "label": "Cleaning",
            "description": "Duplikat, nilai kosong, bbox, confidence, outlier.",
            "available": True,
            "options": [
                {"key": "drop_duplicates", "label": "Hapus duplikat", "type": "boolean", "default": True,
                 "help": "Kunci (latitude, longitude, acq_date, acq_time, satellite)."},
                {"key": "filter_bbox", "label": "Filter bbox Indonesia", "type": "boolean", "default": True},
                {"key": "min_confidence", "label": "Confidence minimum", "type": "select", "default": "low",
                 "choices": [
                     {"value": "low", "label": "Semua (low+)"},
                     {"value": "nominal", "label": "Nominal+"},
                     {"value": "high", "label": "High saja"},
                 ]},
                {"key": "null_strategy", "label": "Nilai kosong numerik", "type": "select", "default": "constant",
                 "choices": [
                     {"value": "drop", "label": "Buang baris"},
                     {"value": "mean", "label": "Isi rata-rata"},
                     {"value": "median", "label": "Isi median"},
                     {"value": "mode", "label": "Isi modus"},
                     {"value": "constant", "label": "Isi konstan"},
                 ]},
                {"key": "null_constant", "label": "Nilai konstan", "type": "number", "default": 0},
                {"key": "outlier_method", "label": "Filter outlier", "type": "select", "default": "none",
                 "choices": [
                     {"value": "none", "label": "Tanpa filter"},
                     {"value": "iqr", "label": "IQR"},
                     {"value": "zscore", "label": "Z-score"},
                 ]},
                {"key": "outlier_column", "label": "Kolom outlier", "type": "select", "default": "frp",
                 "choices": [{"value": "frp", "label": "FRP"}, {"value": "brightness", "label": "Brightness"}]},
                {"key": "outlier_threshold", "label": "Ambang outlier", "type": "number", "default": 1.5},
            ],
        },
        {
            "key": "transform",
            "label": "Transformasi",
            "description": "Timestamp UTC/WIB selalu dibuat; opsi di bawah menambah kolom turunan.",
            "available": True,
            "options": [
                {"key": "time_parts", "label": "Tambah year/month/day/dayofyear/hour", "type": "boolean", "default": True,
                 "help": "Bila dimatikan, kolom tetap ada tetapi bernilai null."},
            ],
        },
        {
            "key": "normalization",
            "label": "Normalisasi",
            "description": "Parameter disimpan pada laporan job.",
            "available": True,
            "options": [
                {"key": "method", "label": "Metode", "type": "select", "default": "minmax",
                 "choices": [
                     {"value": "minmax", "label": "Min-Max"},
                     {"value": "zscore", "label": "Z-score"},
                     {"value": "none", "label": "Tanpa normalisasi"},
                 ]},
            ],
        },
        {
            "key": "spatial",
            "label": "Spatial enrichment",
            "description": "Grid dan provinsi dari lookup poligon.",
            "available": True,
            "options": [
                {"key": "grid_id", "label": "Hitung grid_id 0,25°", "type": "boolean", "default": True},
                {"key": "province", "label": "Tambah provinsi", "type": "boolean", "default": True},
            ],
        },
        {
            "key": "encoding",
            "label": "Encoding",
            "description": "StringIndexer/OneHot dipakai saat pelatihan model.",
            "available": False,
            "note": "Dijadwalkan Fase 6 (ML).",
            "options": [],
        },
        {
            "key": "weather",
            "label": "Integrasi cuaca",
            "description": "Gabung CHIRPS/ERA5 harian.",
            "available": False,
            "note": "Data cuaca belum lengkap (clean/weather kosong).",
            "options": [],
        },
        {
            "key": "features",
            "label": "Feature engineering",
            "description": "Lag/rolling hotspot per grid.",
            "available": False,
            "note": "Dijadwalkan Fase 6 (ML).",
            "options": [],
        },
    ],
    "defaults": {
        "cleaning": {
            "drop_duplicates": True,
            "filter_bbox": True,
            "min_confidence": "low",
            "null_strategy": "constant",
            "null_constant": 0,
            "outlier_method": "none",
            "outlier_column": "frp",
            "outlier_threshold": 1.5,
        },
        "transform": {"time_parts": True},
        "normalization": {"method": "minmax"},
        "spatial": {"grid_id": True, "province": True},
    },
}


# --- Model konfigurasi ------------------------------------------------------


class CleaningConfig(BaseModel):
    drop_duplicates: bool = True
    filter_bbox: bool = True
    min_confidence: Literal["low", "nominal", "high"] = "low"
    null_strategy: Literal["drop", "mean", "median", "mode", "constant"] = "constant"
    null_constant: float = 0.0
    outlier_method: Literal["none", "iqr", "zscore"] = "none"
    outlier_column: Literal["frp", "brightness"] = "frp"
    outlier_threshold: float = Field(default=1.5, gt=0)


class TransformConfig(BaseModel):
    time_parts: bool = True


class NormalizationConfig(BaseModel):
    method: Literal["minmax", "zscore", "none"] = "minmax"


class SpatialConfig(BaseModel):
    grid_id: bool = True
    province: bool = True


class PreprocessConfig(BaseModel):
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    transform: TransformConfig = Field(default_factory=TransformConfig)
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)
    spatial: SpatialConfig = Field(default_factory=SpatialConfig)
    inputs: list[str] | None = None
    output: str | None = None


class ProfileRequest(BaseModel):
    dataset_id: int | None = None
    hdfs_path: str | None = None
    inputs: list[str] | None = None


class RunRequest(BaseModel):
    config: PreprocessConfig = Field(default_factory=PreprocessConfig)


class SaveConfigRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    config: PreprocessConfig = Field(default_factory=PreprocessConfig)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def _uri(hdfs_path: str) -> str:
    if hdfs_path.startswith(("hdfs://", "file://")):
        return hdfs_path
    return f"{settings.HDFS_URI}{hdfs_path}"


@router.get("/config-schema", summary="Skema opsi stepper pre-processing")
def config_schema() -> dict[str, Any]:
    return CONFIG_SCHEMA


@router.post("/profile", summary="Profil dataset sumber (job asinkron)")
def profile(request: ProfileRequest) -> dict[str, Any]:
    if request.dataset_id is not None:
        record = jm.get_dataset(request.dataset_id)
        if not record:
            raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
        inputs = [_uri(record["hdfs_path"])]
    elif request.hdfs_path:
        inputs = [_uri(request.hdfs_path)]
    elif request.inputs:
        inputs = list(request.inputs)
    else:
        inputs = [
            f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/raw/firms_hist/*.csv",
            f"{settings.HDFS_URI}{settings.HDFS_BASE_PATH}/raw/firms_nrt/*.csv",
        ]

    job_id = f"profile-{_stamp()}"
    output = PROFILING_DIR / f"{job_id}.json"
    submission = queue.submit(
        job_id,
        "PROFILING",
        "data_profile.py",
        [*inputs, "--output", str(output), "--job-id", job_id],
        {"inputs": inputs, "dataset_id": request.dataset_id},
    )
    return {**submission, "report_path": str(output)}


@router.post("/run", summary="Jalankan pipeline pre-processing (job asinkron)")
def run(request: RunRequest) -> dict[str, Any]:
    job_id = f"preprocess-{_stamp()}"
    config_path = RUNS_DIR / f"{job_id}_config.json"
    summary_path = RUNS_DIR / f"{job_id}.json"
    config_payload = request.config.model_dump()
    _write_json(config_path, {"job_id": job_id, "config": config_payload})

    args = [
        "--config", str(config_path),
        "--summary", str(summary_path),
        "--job-id", job_id,
    ]
    if request.config.output:
        # Dipakai untuk pengujian: jangan timpa `clean/hotspot` bila tak diminta.
        args += ["--output", request.config.output]
    if request.config.inputs:
        args = [*request.config.inputs, *args]
    submission = queue.submit(
        job_id,
        "PREPROCESSING",
        "preprocess.py",
        args,
        {"config": config_payload, "config_path": str(config_path)},
    )
    return {**submission, "config_path": str(config_path), "report_path": str(summary_path)}


@router.get("/latest", summary="Laporan pre-processing terakhir")
def latest() -> dict[str, Any]:
    report: dict[str, Any] | None = None
    if SUMMARY_PATH.exists():
        try:
            report = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = None

    config: dict[str, Any] | None = None
    if RUNS_DIR.exists():
        files = sorted(RUNS_DIR.glob("*_config.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for candidate in files:
            try:
                config = json.loads(candidate.read_text(encoding="utf-8"))
                break
            except (OSError, json.JSONDecodeError):
                continue

    profiling: Path | None = None
    if PROFILING_DIR.exists():
        files = sorted(PROFILING_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        profiling = files[0] if files else None

    return {
        "report": report,
        "config": config,
        "profiling_path": str(profiling) if profiling else None,
    }


@router.get("/profile/{job_id}", summary="Laporan profiling per job")
def profile_report(job_id: str) -> dict[str, Any]:
    path = PROFILING_DIR / f"{job_id}.json"
    if not path.exists():
        row = jm.get_job(job_id)
        if row and row.get("status") in {"queued", "running"}:
            return {"status": row["status"], "ready": False, "job_id": job_id}
        raise HTTPException(status_code=404, detail="Laporan profiling tidak ditemukan")
    return {
        "status": "COMPLETED",
        "ready": True,
        "job_id": job_id,
        "report": json.loads(path.read_text(encoding="utf-8")),
    }


@router.get("/configs", summary="Daftar konfigurasi pre-processing tersimpan")
def list_configs() -> dict[str, Any]:
    items = []
    if CONFIG_DIR.exists():
        for path in sorted(CONFIG_DIR.glob("*.json"), key=lambda p: p.name):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            items.append({"name": payload.get("name") or path.stem, "path": str(path), "config": payload.get("config")})
    return {"items": items, "meta": {"count": len(items)}}


@router.post("/configs", summary="Simpan konfigurasi pre-processing sebagai JSON")
def save_config(request: SaveConfigRequest) -> dict[str, Any]:
    safe = "".join(c for c in request.name if c.isalnum() or c in "-_ ").strip().replace(" ", "-")
    if not safe:
        raise HTTPException(status_code=422, detail="Nama konfigurasi tidak valid")
    path = CONFIG_DIR / f"{safe}.json"
    _write_json(path, {"name": safe, "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "config": request.config.model_dump()})
    return {"saved": True, "name": safe, "path": str(path)}
