import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from networkbridge.aliases import list_aliases, save_alias, validate
from networkbridge.api import app


def test_mac_alias_persistence():
    with sqlite3.connect(":memory:") as db:
        save_alias(db, "AA:BB:CC:DD:EE:01", "  Living room TV ")
        save_alias(db, "aa:bb:cc:dd:ee:01", "Television")
        assert list_aliases(db) == {"aa:bb:cc:dd:ee:01": "Television"}


@pytest.mark.parametrize("mac,label", [
    ("not-a-mac", "TV"), ("00:00:00:00:00:00", "TV"),
    ("ff:ff:ff:ff:ff:ff", "TV"), ("aa:bb:cc:dd:ee:ff", ""),
    ("aa:bb:cc:dd:ee:ff", "x" * 81),
    ("aa:bb:cc:dd:ee:ff", "bad\nlabel"),
])
def test_invalid_alias(mac, label):
    with pytest.raises(ValueError):
        validate(mac, label)


def test_alias_writes_disabled_by_default():
    with patch("networkbridge.api.settings.device_alias_writes_enabled", False):
        response = TestClient(app).put("/api/devices/alias",
            json={"mac": "aa:bb:cc:dd:ee:ff", "label": "Printer"},
            headers={"X-NetworkBridge-Action": "save-device-alias"})
    assert response.status_code == 403


def test_alias_action_header_required():
    with patch("networkbridge.api.settings.device_alias_writes_enabled", True):
        response = TestClient(app).put("/api/devices/alias",
            json={"mac": "aa:bb:cc:dd:ee:ff", "label": "Printer"})
    assert response.status_code == 403
