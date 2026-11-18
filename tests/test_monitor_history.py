import sqlite3
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.monitor_history import ensure_schema, prune_checks, recent_checks, record_checks


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


def test_monitor_history_prunes_only_older_checks():
    with sqlite3.connect(":memory:") as db:
        record_checks(db, {"192.168.1.10": True}, datetime(2026, 11, 1, tzinfo=UTC))
        record_checks(db, {"192.168.1.11": False}, datetime(2026, 11, 17, tzinfo=UTC))
        now = datetime(2026, 11, 18, tzinfo=UTC)
        assert prune_checks(db, 0, now) == 0
        assert prune_checks(db, 7, now) == 1
        rows = recent_checks(db)
        assert len(rows) == 1
        assert rows[0]["address"] == "192.168.1.11"


def test_monitor_history_rejects_invalid_retention():
    with sqlite3.connect(":memory:") as db:
        ensure_schema(db)
        with pytest.raises(ValueError):
            prune_checks(db, -1)
