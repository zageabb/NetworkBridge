"""WAN history API tests."""

import sqlite3

from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.config import settings
from networkbridge.router import Counters
from networkbridge.storage import add_wan_sample, connect

client = TestClient(app)


def test_history_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'missing.db'}")
    response = client.get("/api/wan/history")
    assert response.status_code == 200
    assert response.json() == {"samples": [], "count": 0}


def test_history_populated(tmp_path, monkeypatch):
    path = tmp_path / "history.db"
    db = connect(path)
    add_wan_sample(
        db,
        "2026-11-16T18:00:00Z",
        {"counters": Counters(300, 200, 100), "uptime": "10"},
        (160.0, 80.0),
    )
    db.close()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{path}")
    response = client.get("/api/wan/history?limit=1")
    assert response.status_code == 200
    assert response.json()["samples"][0]["download_bps"] == 160.0


def test_history_invalid_limit():
    assert client.get("/api/wan/history?limit=0").status_code == 422


def test_history_invalid_database(tmp_path, monkeypatch):
    path = tmp_path / "bad.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE something_else (id INTEGER)")
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{path}")
    assert client.get("/api/wan/history").status_code == 503
