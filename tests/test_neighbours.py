from unittest.mock import patch

from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.neighbours import parse_arp

ARP = """IP address       HW type     Flags       HW address            Mask     Device
192.168.1.10     0x1         0x2         aa:bb:cc:dd:ee:01     *        eth0
192.168.1.11     0x1         0x0         00:00:00:00:00:00     *        eth0
8.8.8.8          0x1         0x2         aa:bb:cc:dd:ee:02     *        eth0
192.168.1.12     0x1         0x2         aa:bb:cc:dd:ee:03     *        eth1
"""


def test_parse_arp_filters_incomplete_and_public_entries():
    devices = parse_arp(ARP)
    assert [d["address"] for d in devices] == ["192.168.1.10", "192.168.1.12"]
    assert devices[0]["mac"] == "aa:bb:cc:dd:ee:01"
    assert parse_arp(ARP, limit=1)[0]["address"] == "192.168.1.10"
    assert len(parse_arp(ARP, limit=1)) == 1


def test_neighbour_api_disabled_by_default():
    response = TestClient(app).get("/api/devices/neighbours")
    assert response.status_code == 200
    assert response.json()["collection"] == "disabled"
    assert response.json()["devices"] == []


def test_neighbour_api_enabled():
    with (patch("networkbridge.api.settings.neighbour_discovery_enabled", True),
          patch("networkbridge.api.neighbours", return_value=[{"address": "192.168.1.10"}])):
        response = TestClient(app).get("/api/devices/neighbours")
    assert response.status_code == 200
    assert response.json()["devices"][0]["address"] == "192.168.1.10"


def test_neighbour_limit_validation():
    assert TestClient(app).get("/api/devices/neighbours?limit=501").status_code == 422
