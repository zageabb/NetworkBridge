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
