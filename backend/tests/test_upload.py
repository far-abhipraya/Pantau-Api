import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"

def test_upload_flow_and_summary():
    # 1. Init upload
    init_payload = {
        "filename": "test_hotspot.csv",
        "dataset_type": "firms_hist",
        "total_size": 250,
        "total_chunks": 1
    }
    res = client.post("/api/datasets/upload/init", json=init_payload)
    assert res.status_code == 200
    upload_id = res.json()["upload_id"]

    # 2. Upload chunk
    csv_content = (
        "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,confidence,version,bright_t31,frp,daynight\n"
        "-0.5,101.2,320.5,1.0,1.0,2026-10-01,0600,Terra,85,6.1,295.2,15.4,D\n"
        "-0.6,101.3,315.0,1.0,1.0,2026-10-01,0600,Terra,70,6.1,292.0,10.2,D\n"
    ).encode("utf-8")

    res = client.post(
        "/api/datasets/upload/chunk",
        data={"upload_id": upload_id, "chunk_index": 0},
        files={"file": ("chunk_00000.part", io.BytesIO(csv_content), "application/octet-stream")}
    )
    assert res.status_code == 200
    assert res.json()["received"] is True

    # 3. Complete upload
    res = client.post("/api/datasets/upload/complete", json={"upload_id": upload_id})
    assert res.status_code == 200
    dataset = res.json()
    assert dataset["name"] == "test_hotspot.csv"
    assert dataset["row_count"] == 2
    ds_id = dataset["id"]

    # 4. List datasets
    res = client.get("/api/datasets")
    assert res.status_code == 200
    datasets = res.json()
    assert any(d["id"] == ds_id for d in datasets)

    # 5. Summary
    res = client.get("/api/datasets/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_files"] >= 1
    assert summary["total_rows"] >= 2

    # 6. Preview
    res = client.get(f"/api/datasets/{ds_id}/preview?limit=5")
    assert res.status_code == 200
    preview = res.json()
    assert preview["total_rows"] == 2
    assert len(preview["preview_rows"]) == 2

    # 7. Delete dataset
    res = client.delete(f"/api/datasets/{ds_id}")
    assert res.status_code == 200

