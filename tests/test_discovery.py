import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.discovery import targets


def test_private_subnet_bounds():
    assert len(targets("192.168.1.0/24")) == 254
    assert len(targets("10.12.3.0/24")) == 254
    assert len(targets("172.16.2.0/24")) == 254
    for cidr in ("8.8.8.0/24", "192.168.0.0/16", "192.168.1.1/24", "::1/128", "127.0.0.0/24",
                 "169.254.1.0/24", "0.0.0.0/24", "100.64.0.0/24",
                 "198.18.0.0/24"):
        with pytest.raises(ValueError):
            targets(cidr)


def test_discovery_disabled():
    assert TestClient(app).post("/api/devices/discover",
                                headers={"X-NetworkBridge-Action": "discover"}).status_code == 403


def test_explicit_action_required():
    with (patch("networkbridge.api.settings.active_discovery_enabled", True),
          patch("networkbridge.api.settings.active_discovery_cidr", "192.168.1.0/24")):
        assert TestClient(app).post("/api/devices/discover").status_code == 403


def test_enabled_discovery_mocked():
    async def fake_scan(_cidr):
        await asyncio.sleep(0)
        return {"devices": [{"address": "192.168.1.10", "state": "tcp_reachable"}],
                "probed_hosts": 254, "note": "test"}

    with (patch("networkbridge.api.settings.active_discovery_enabled", True),
          patch("networkbridge.api.settings.active_discovery_cidr", "192.168.1.0/24"),
          patch("networkbridge.api.scan", side_effect=fake_scan)):
        response = TestClient(app).post("/api/devices/discover",
                                        headers={"X-NetworkBridge-Action": "discover"})
    assert response.status_code == 200
    assert response.json()["devices"][0]["address"] == "192.168.1.10"
