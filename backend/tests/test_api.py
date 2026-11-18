"""Tes endpoint API terhadap serving layer nyata (dilewati bila belum dibuat)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import serving

SERVING_READY = serving.available_tables().get("hotspot_latest", False)

pytestmark = pytest.mark.skipif(
    not SERVING_READY,
    reason="Serving layer belum dibuat; jalankan spark-submit backend/spark_jobs/aggregate.py",
)

BBOX = "95,-11,141,6"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_ok(client):
    body = client.get("/api/health").json()
    assert body["serving"]["available"] is True
    assert "freshness" in body["serving"]


def test_hotspots_respect_limit_and_bbox(client):
    body = client.get(
        "/api/map/hotspots", params={"bbox": BBOX, "hours": 24, "limit": 10}
    ).json()
    assert len(body["features"]) <= 10
    assert body["meta"]["truncated"] is True
    for feature in body["features"]:
        lon, lat = feature["geometry"]["coordinates"]
        assert 95 <= lon <= 141
        assert -11 <= lat <= 6


def test_hotspots_requires_valid_bbox(client):
    assert client.get("/api/map/hotspots", params={"hours": 24}).status_code == 422
    assert (
        client.get("/api/map/hotspots", params={"bbox": "141,-11,95,6"}).status_code == 422
    )


def test_hotspots_rejects_unknown_window(client):
    response = client.get("/api/map/hotspots", params={"bbox": BBOX, "hours": 12})
    assert response.status_code == 422


def test_hotspots_rejects_limit_above_cap(client):
    response = client.get(
        "/api/map/hotspots", params={"bbox": BBOX, "limit": 20001}
    )
    assert response.status_code == 422


def test_grid_resolution_follows_zoom(client):
    low = client.get("/api/map/grid", params={"bbox": BBOX, "zoom": 4}).json()
    high = client.get("/api/map/grid", params={"bbox": BBOX, "zoom": 9}).json()
    assert low["meta"]["resolution"] == 1.0
    assert high["meta"]["resolution"] == 0.25


def test_kpi_excludes_unknown_province(client):
    body = client.get("/api/map/kpi", params={"hours": 24}).json()
    assert body["top_province"]["name"] != "UNKNOWN"


def test_provinces_have_trend(client):
    body = client.get("/api/map/provinces", params={"hours": 24}).json()
    assert body["provinces"]
    for province in body["provinces"]:
        assert province["province"] != "UNKNOWN"
        assert 1 <= len(province["trend"]) <= 7


def test_risk_endpoint_matches_serving_state(client):
    body = client.get("/api/map/risk").json()
    assert body["type"] == "FeatureCollection"
    if body["meta"]["available"]:
        assert body["features"]
    else:
        assert body["features"] == []


def test_geo_provinces_geojson(client):
    response = client.get("/api/geo/provinces")
    assert response.status_code == 200
    assert response.json()["type"] == "FeatureCollection"
