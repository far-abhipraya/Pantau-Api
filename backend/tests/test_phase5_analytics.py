"""Unit test untuk API analitik (Fase 5, AC-5)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analytics_kpi():
    response = client.get("/api/analytics/kpi")
    assert response.status_code == 200
    data = response.json()
    assert "today" in data
    assert "last_7d" in data
    assert "last_30d" in data
    assert "top_province" in data
    assert data["meta"]["conf"] == "all"


def test_analytics_kpi_high_conf():
    response = client.get("/api/analytics/kpi?conf=high")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["conf"] == "high"


def test_analytics_trend():
    response = client.get("/api/analytics/trend?granularity=month&days=365")
    assert response.status_code == 200
    data = response.json()
    assert "points" in data
    assert isinstance(data["points"], list)
    assert data["meta"]["granularity"] == "month"


def test_analytics_ranking():
    response = client.get("/api/analytics/ranking?days=30&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) <= 5
    if data["items"]:
        assert "rank" in data["items"][0]
        assert "province" in data["items"][0]
        assert "share_percent" in data["items"][0]


def test_analytics_seasonality():
    response = client.get("/api/analytics/seasonality")
    assert response.status_code == 200
    data = response.json()
    assert "months" in data
    assert len(data["months"]) == 12
    assert "by_year" in data
    assert "by_province" in data


def test_analytics_year_compare():
    response = client.get("/api/analytics/year-compare")
    assert response.status_code == 200
    data = response.json()
    assert "years" in data
    assert "historical_mean" in data


def test_analytics_top_grid():
    response = client.get("/api/analytics/top-grid?days=30&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) <= 5


def test_analytics_weather_correlation():
    response = client.get("/api/analytics/weather-correlation")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert "reason" in data


def test_analytics_insights():
    response = client.get("/api/analytics/insights?days=90")
    assert response.status_code == 200
    data = response.json()
    assert "cards" in data
    assert isinstance(data["cards"], list)
    if data["cards"]:
        assert "id" in data["cards"][0]
        assert "confidence" in data["cards"][0]
        assert "sentence" in data["cards"][0]
