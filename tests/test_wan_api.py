"""WAN history API tests."""

import sqlite3

import pytest
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
    status = client.get("/api/status").json()
    assert status["wan_history"] == "available"
    assert status["database"] == "initialized"


def test_history_invalid_limit():
    assert client.get("/api/wan/history?limit=0").status_code == 422


def test_history_missing_table(tmp_path, monkeypatch):
    path = tmp_path / "bad.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE something_else (id INTEGER)")
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{path}")
    response = client.get("/api/wan/history")
    assert response.status_code == 200
    assert response.json() == {"samples": [], "count": 0}
    assert client.get("/api/status").json()["database"] == "not_initialized"


@pytest.mark.parametrize("failure", ["corrupt", "directory", "invalid_url", "bad_schema"])
def test_genuine_database_errors_stay_unavailable(tmp_path, monkeypatch, failure):
    path = tmp_path / "bad.db"
    if failure == "corrupt":
        path.write_bytes(b"not a SQLite database")
    elif failure == "directory":
        path.mkdir()
    elif failure == "bad_schema":
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE wan_samples (id INTEGER)")
    url = "postgresql://invalid" if failure == "invalid_url" else f"sqlite:///{path}"
    monkeypatch.setattr(settings, "database_url", url)
    # A startup failure must leave diagnostics reachable, without masking database errors.
    with TestClient(app) as running:
        assert running.get("/api/health").status_code == 200
        response = running.get("/api/wan/history")
        assert response.status_code == 503
        assert response.json() == {"detail": "WAN history unavailable"}
        status = running.get("/api/status").json()
        assert status["database"] == "unavailable"
        assert status["wan_history"] == "unavailable"


def test_database_access_failure_is_not_empty_history(tmp_path, monkeypatch):
    path = tmp_path / "unreadable.db"
    path.touch()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{path}")

    def denied(*args, **kwargs):
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(sqlite3, "connect", denied)
    assert client.get("/api/wan/history").status_code == 503
    assert client.get("/api/status").json()["database"] == "unavailable"
