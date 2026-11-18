"""Tes API Fase 4: katalog dataset, karantina, job, dan upload manual.

Tes upload/HDFS dilewati bila HDFS tidak dapat dijangkau.
"""
from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline import hdfs
from app.services import serving

HDFS_UP = hdfs.exists("/karhutla")

pytestmark = pytest.mark.skipif(
    not HDFS_UP, reason="HDFS tidak aktif; tes katalog/upload dilewati"
)

SAMPLE_VIIRS = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,"
    "instrument,confidence,version,bright_ti5,frp,daynight\n"
    "0.5123,101.4477,330.1,0.4,0.4,2026-11-16,0700,N,VIIRS,n,2.0NRT,295.1,12.5,N\n"
    "-1.2000,113.9000,360.4,0.4,0.4,2026-11-16,0712,N,VIIRS,h,2.0NRT,300.2,45.0,D\n"
    "1.6700,124.8000,340.9,0.4,0.4,2026-11-16,0730,N,VIIRS,l,2.0NRT,298.0,8.1,N\n"
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_config_schema_exposes_steps(client):
    body = client.get("/api/preprocessing/config-schema").json()
    keys = [step["key"] for step in body["steps"]]
    assert keys == ["cleaning", "transform", "normalization", "spatial", "encoding", "weather", "features"]
    available = {step["key"]: step["available"] for step in body["steps"]}
    assert available["cleaning"] is True
    assert available["weather"] is False  # data cuaca belum lengkap
    assert body["defaults"]["normalization"]["method"] == "minmax"


def test_jobs_list_includes_queue_meta(client):
    body = client.get("/api/jobs", params={"limit": 5}).json()
    assert "items" in body
    assert "queue" in body["meta"]
    for job in body["items"]:
        assert {"id", "job_type", "status", "rows_in", "rows_out"} <= set(job)


def test_quarantine_and_datasets_list(client):
    quarantine = client.get("/api/quarantine").json()
    assert "items" in quarantine
    assert "failed_dir" in quarantine["meta"]

    datasets = client.get("/api/datasets").json()
    assert "items" in datasets
    assert "summary" in datasets["meta"]


def test_preprocessing_latest(client):
    body = client.get("/api/preprocessing/latest").json()
    assert set(body) == {"report", "config", "profiling_path"}


def test_upload_detect_complete_preview_delete(client):
    name = f"test_viirs_{uuid.uuid4().hex[:8]}.csv"
    payload = SAMPLE_VIIRS.encode("utf-8")

    init = client.post(
        "/api/datasets/upload/init",
        json={"filename": name, "size_bytes": len(payload)},
    ).json()
    upload_id = init["upload_id"]
    assert len(upload_id) == 32
    assert init["chunk_size"] > 0

    chunk = client.post(
        "/api/datasets/upload/chunk",
        data={"upload_id": upload_id, "index": 0},
        files={"file": (name, io.BytesIO(payload), "text/csv")},
    ).json()
    assert chunk["received_bytes"] == len(payload)

    detection = client.post("/api/datasets/detect", json={"upload_id": upload_id}).json()
    assert detection["detected_format"] == "FIRMS_VIIRS"
    assert detection["procesable"] is True
    assert "latitude" in detection["columns"]["recognized"]
    assert detection["estimated_rows"] == 3

    complete = client.post(
        "/api/datasets/upload/complete",
        json={"upload_id": upload_id, "run_pipeline": False},
    ).json()
    assert complete["status"] == "ingested"
    assert complete["hdfs_path"].startswith("/karhutla/raw/")
    assert complete["rows"]["input"] == 3

    listing = client.get("/api/datasets", params={"source": "FIRMS_VIIRS"}).json()
    item = next((row for row in listing["items"] if row["name"] == complete["hdfs_path"].split("/")[-1]), None)
    assert item is not None
    assert item["ingest_path"] == "manual"
    assert item["row_count"] == 3

    preview = client.get(f"/api/datasets/{item['id']}/preview", params={"limit": 2}).json()
    assert "latitude" in preview["columns"]
    assert len(preview["rows"]) == 2

    deleted = client.delete(f"/api/datasets/{item['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert not hdfs.exists(complete["hdfs_path"])
    serving.invalidate("raw_hdfs_files")


def test_upload_rejects_unknown_suffix(client):
    response = client.post(
        "/api/datasets/upload/init", json={"filename": "catatan.txt", "size_bytes": 10}
    )
    assert response.status_code == 422


def test_delete_outside_karhutla_is_blocked(client):
    # Tidak ada dataset dengan path di luar /karhutla, jadi uji pagarnya langsung.
    assert hdfs.is_within_base("/karhutla/raw/x.csv") is True
    assert hdfs.is_within_base("/user/alfarel/x.csv") is False
    assert hdfs.is_within_base("/karhutla-evil/x") is False
