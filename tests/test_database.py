import sqlite3
from contextlib import closing

from fastapi.testclient import TestClient

from networkbridge.aliases import list_aliases, save_alias
from networkbridge.api import app
from networkbridge.config import settings
from networkbridge.observations import recent_observations, record_scan


def test_fresh_install_initializes_without_router_polling(tmp_path, monkeypatch):
    path = tmp_path / "new" / "networkbridge.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{path}")
    monkeypatch.setattr(settings, "router_polling_enabled", False)
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        response = client.get("/api/wan/history")
        assert response.status_code == 200
        assert response.json() == {"samples": [], "count": 0}
        status = client.get("/api/status").json()
        assert status["router_collection"] == "disabled"
        assert status["database"] == "initialized"
        assert status["wan_history"] == "no_measurements"
    with closing(sqlite3.connect(path)) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert tables == {"wan_samples", "remembered_devices", "device_observations", "device_observation_events", "device_aliases", "device_monitor_checks"}


def test_startup_preserves_existing_device_data_and_is_repeatable(tmp_path, monkeypatch):
    path = tmp_path / "existing.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{path}")
    monkeypatch.setattr(settings, "router_polling_enabled", False)
    with closing(sqlite3.connect(path)) as db:
        record_scan(db, [{"address": "192.168.50.10", "state": "tcp_reachable"}])
        save_alias(db, "02:00:00:00:00:01", "Synthetic device")
        observations = recent_observations(db)
        labels = list_aliases(db)
    for _ in range(2):
        with TestClient(app) as client:
            assert client.get("/api/wan/history").json() == {"samples": [], "count": 0}
        with closing(sqlite3.connect(path)) as db:
            assert recent_observations(db) == observations
            assert list_aliases(db) == labels
