from fastapi.testclient import TestClient

from networkbridge.api import app


def test_health() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status_is_safe() -> None:
    payload = TestClient(app).get("/api/status").json()
    assert payload["router_collection"] == "disabled"
    assert payload["devices"] == []


def test_aggregated_history_rejects_invalid_hours():
    response = TestClient(app).get("/api/wan/aggregated?hours=2")
    assert response.status_code == 422


def test_aggregated_history_empty_database(tmp_path, monkeypatch):
    from networkbridge.config import settings

    monkeypatch.setattr(settings, "database_url", "sqlite:///" + str(tmp_path / "missing.db"))
    response = TestClient(app).get("/api/wan/aggregated?hours=24")
    assert response.status_code == 200
    assert response.json() == {
        "samples": [], "count": 0, "hours": 24,
        "aggregation": "mean_valid_rate", "bucket_seconds": 900,
    }


def test_collector_health_disabled():
    response = TestClient(app).get("/api/wan/collector-health")
    assert response.status_code == 200
    assert response.json()["state"] == "disabled"
