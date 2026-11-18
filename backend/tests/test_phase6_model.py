"""Unit test Fase 6 (AC-7): metrik model ML dan lapisan risiko peta."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_model_endpoint_shape():
    response = client.get("/api/analytics/model")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data
    assert "risk" in data
    assert isinstance(data["risk"], dict)
    if not data["available"]:
        assert "message" in data
        return

    metrics = data["metrics"]
    assert {"model", "baseline_persistence"}.issubset(metrics)
    for key in ("auc_roc", "auc_pr", "precision", "recall", "f1", "confusion"):
        assert key in metrics["model"]
        assert key in metrics["baseline_persistence"]
    assert data["split"]["train_end"] < data["split"]["test_start"]
    assert "weather_missing" in data["features"]
    assert data["feature_importance"]
    total_importance = sum(item["value"] for item in data["feature_importance"])
    assert 0.99 <= total_importance <= 1.01


def test_model_metrics_file_consistency():
    path = Path(settings.SERVING_DIR) / "model_metrics.json"
    if not path.exists():
        pytest.skip("model belum dilatih pada mesin ini")
    metrics = json.loads(path.read_text(encoding="utf-8"))
    model = metrics["metrics"]["model"]
    baseline = metrics["metrics"]["baseline_persistence"]
    assert model["rows"] == baseline["rows"] > 0
    assert 0.0 <= model["auc_roc"] <= 1.0
    assert 0.0 <= model["auc_pr"] <= 1.0
    assert metrics["rows"]["train"] > 0
    assert metrics["rows"]["test"] > 0


def test_map_risk_geojson():
    response = client.get("/api/map/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert isinstance(data["features"], list)
    if data["features"]:
        properties = data["features"][0]["properties"]
        assert "risk_score" in properties
        assert properties["risk_category"] in {"rendah", "sedang", "tinggi", "sangat tinggi"}
        assert properties["horizon_days"] == 7
