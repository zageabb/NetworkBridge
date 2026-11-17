import sqlite3

from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.devices import ensure_device_schema, list_devices


def test_device_schema_and_listing():
    with sqlite3.connect(":memory:") as db:
        ensure_device_schema(db)
        db.execute("""INSERT INTO remembered_devices
            (device_key, display_name, address, connection_type, last_seen, observed_at)
            VALUES ('test', 'Example device', NULL, 'wifi', NULL, '2026-01-01')""")
        records = list_devices(db)
    assert len(records) == 1
    assert records[0]["name"] == "Example device"
    assert records[0]["connection_type"] == "wifi"
    assert "device_key" not in records[0]


def test_disabled_devices_api_returns_no_identifiers():
    response = TestClient(app).get("/api/devices")
    assert response.status_code == 200
    assert response.json() == {"devices": [], "collection": "disabled"}


def test_device_limit_rejected():
    assert TestClient(app).get("/api/devices?limit=501").status_code == 422
