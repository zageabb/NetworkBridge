import sqlite3
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.monitor_history import ensure_schema, recent_checks, record_checks


def test_monitoring_history_positive_and_inconclusive():
    with sqlite3.connect(":memory:") as db:
        ensure_schema(db)
        record_checks(db, {"192.168.1.10": True, "192.168.1.11": False},
                      datetime(2026, 11, 18, tzinfo=UTC))
        rows = recent_checks(db)
        assert len(rows) == 2
        assert rows[0]["result"] == "no_tcp_response"
        assert rows[0]["availability_verdict"] == "not_evaluated"
        assert recent_checks(db, address="192.168.1.10")[0]["result"] == "tcp_responded"


def test_history_api_uninitialized(tmp_path):
    with patch("networkbridge.api.settings.database_url",
               f"sqlite:///{tmp_path / 'missing.db'}"):
        response = TestClient(app).get("/api/devices/monitoring-history")
    assert response.status_code == 200
    assert response.json()["collection"] == "not_initialized"


def test_history_api_rejects_invalid_limit():
    assert TestClient(app).get("/api/devices/monitoring-history?limit=501").status_code == 422
