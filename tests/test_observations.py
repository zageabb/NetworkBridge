import sqlite3
from unittest.mock import patch

from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.observations import record_scan, recent_observations


def test_observations_positive_only_and_repeat():
    with sqlite3.connect(":memory:") as db:
        record_scan(db, [{"address": "192.168.1.10", "state": "tcp_reachable"},
                         {"address": "192.168.1.11", "state": "unknown"}])
        record_scan(db, [{"address": "192.168.1.10", "state": "tcp_reachable"}])
        record_scan(db, [])
        rows = recent_observations(db)
    assert len(rows) == 1
    assert rows[0]["address"] == "192.168.1.10"
    assert rows[0]["positive_scans"] == 2
    assert rows[0]["first_seen"] <= rows[0]["last_seen"]


def test_observations_api_disabled():
    with patch("networkbridge.api.settings.active_discovery_enabled", False):
        response = TestClient(app).get("/api/devices/observations")
    assert response.status_code == 200
    assert response.json()["collection"] == "disabled"


def test_observations_limit():
    assert TestClient(app).get("/api/devices/observations?limit=501").status_code == 422
