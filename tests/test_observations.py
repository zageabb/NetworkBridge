import sqlite3
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.observations import (
    observation_events,
    observation_recency,
    prune_observation_events,
    recent_observations,
    record_scan,
)


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


def test_observation_recency_does_not_claim_online_status():
    now = datetime(2026, 11, 17, 12, tzinfo=UTC)
    rows = [
        {"address": "192.0.2.1", "last_seen": "2026-11-17T11:50:00Z"},
        {"address": "192.0.2.2", "last_seen": "2026-11-17T11:00:00Z"},
        {"address": "192.0.2.3", "last_seen": "invalid"},
    ]
    result = observation_recency(rows, now)
    assert [row["recency"] for row in result] == [
        "recent_positive", "previously_observed", "unknown",
    ]
    assert result[0]["minutes_since_seen"] == 10.0
    assert all("online" not in row for row in result)


def test_configurable_recency_window():
    now = datetime(2026, 11, 17, 12, tzinfo=UTC)
    rows = [{"address": "192.0.2.1", "last_seen": "2026-11-17T11:40:00Z"}]
    assert observation_recency(rows, now, recent_within_minutes=15)[0]["recency"] == "previously_observed"
    assert observation_recency(rows, now, recent_within_minutes=30)[0]["recency"] == "recent_positive"


def test_observations_api_uses_configured_window(tmp_path):
    from networkbridge.config import settings

    path = tmp_path / "observations.sqlite"
    with sqlite3.connect(path) as db:
        record_scan(db, [{"address": "192.0.2.5", "state": "tcp_reachable"}])
    with patch.object(settings, "active_discovery_enabled", True), (
        patch.object(settings, "database_url", "sqlite:///" + str(path))
    ), patch.object(settings, "device_recency_minutes", 45):
        response = TestClient(app).get("/api/devices/observations")
    assert response.status_code == 200
    assert response.json()["recency_window_minutes"] == 45
    assert response.json()["devices"][0]["recency"] == "recent_positive"


def test_positive_observation_events_preserve_each_scan():
    with sqlite3.connect(":memory:") as db:
        record_scan(db, [{"address": "192.0.2.5", "state": "tcp_reachable"},
                         {"address": "192.0.2.6", "state": "unknown"}])
        record_scan(db, [{"address": "192.0.2.5", "state": "tcp_reachable"}])
        events = observation_events(db)
        assert len(events) == 2
        assert all(e["address"] == "192.0.2.5" for e in events)
        assert len(observation_events(db, address="192.0.2.6")) == 0
        assert len(observation_events(db, limit=1)) == 1


def test_observation_events_api_disabled_and_invalid_limit():
    with patch("networkbridge.api.settings.active_discovery_enabled", False):
        response = TestClient(app).get("/api/devices/observation-events")
    assert response.status_code == 200
    assert response.json()["collection"] == "disabled"
    assert TestClient(app).get("/api/devices/observation-events?limit=501").status_code == 422


def test_device_event_retention_preserves_summary_and_recent_events():
    now = datetime(2026, 11, 17, 12, tzinfo=UTC)
    with sqlite3.connect(":memory:") as db:
        record_scan(db, [{"address": "192.0.2.5", "state": "tcp_reachable"}])
        db.execute(
            "UPDATE device_observation_events SET observed_at = ?",
            ((now - timedelta(days=40)).isoformat(),),
        )
        db.execute(
            "INSERT INTO device_observation_events (address, observed_at, source) "
            "VALUES (?, ?, ?)",
            ("192.0.2.5", (now - timedelta(days=2)).isoformat(), "tcp_probe"),
        )
        db.commit()
        assert prune_observation_events(db, 30, now) == 1
        assert len(observation_events(db)) == 1
        assert len(recent_observations(db)) == 1
        assert prune_observation_events(db, 0, now) == 0


def test_device_event_retention_rejects_invalid_values():
    import pytest

    with sqlite3.connect(":memory:") as db:
        for days in (-1, 3651):
            with pytest.raises(ValueError):
                prune_observation_events(db, days)
        with pytest.raises(ValueError):
            prune_observation_events(db, 30, datetime(2026, 11, 17))
