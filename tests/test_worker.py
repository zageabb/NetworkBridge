import asyncio
import sqlite3
from contextlib import closing

import pytest

from networkbridge import worker
from networkbridge.config import settings
from networkbridge.worker import database_path


def test_database_path():
    assert str(database_path("sqlite:////var/lib/networkbridge/history.db")) == (
        "/var/lib/networkbridge/history.db"
    )


def test_non_sqlite_rejected():
    with pytest.raises(ValueError):
        database_path("postgresql://localhost/networkbridge")


def test_disabled_worker_initializes_before_waiting(tmp_path, monkeypatch):
    path = tmp_path / "new" / "worker.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{path}")
    monkeypatch.setattr(settings, "router_polling_enabled", False)

    def unexpected_collector(*args, **kwargs):
        pytest.fail("Disabled worker must not contact the router")

    async def stop_after_initialization(seconds):
        with closing(sqlite3.connect(path)) as db:
            assert db.execute("SELECT count(*) FROM wan_samples").fetchone()[0] == 0
        raise asyncio.CancelledError

    monkeypatch.setattr(worker, "SmartHubCollector", unexpected_collector)
    monkeypatch.setattr(worker.asyncio, "sleep", stop_after_initialization)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(worker.run())
