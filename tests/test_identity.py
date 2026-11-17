from unittest.mock import patch

from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.identity import correlate


def test_correlation_uses_only_current_arp_evidence():
    observed = [{"address": "192.168.1.10", "last_seen": "2026-11-17T10:00:00+00:00",
                 "positive_scans": 3}]
    arp = [{"address": "192.168.1.10", "mac": "aa:bb:cc:dd:ee:ff", "interface": "eth0"},
           {"address": "192.168.1.11", "mac": "aa:bb:cc:dd:ee:01", "interface": "eth0"}]
    rows = correlate(observed, arp)
    assert len(rows) == 2
    assert rows[0]["mac"] == "aa:bb:cc:dd:ee:ff"
    assert rows[0]["positive_scans"] == 3
    assert rows[0]["status"] == "recently_observed"
    assert rows[1]["last_positive_tcp"] is None


def test_unmatched_history_has_no_mac():
    rows = correlate([{"address": "192.168.1.20", "last_seen": "yesterday",
                       "positive_scans": 1}], [])
    assert rows[0]["mac"] is None
    assert rows[0]["status"] == "historical_positive"


def test_disabled_api():
    with (patch("networkbridge.api.settings.active_discovery_enabled", False),
          patch("networkbridge.api.settings.neighbour_discovery_enabled", False)):
        response = TestClient(app).get("/api/devices/identified")
    assert response.json()["collection"] == "disabled"


def test_limit_validation():
    assert TestClient(app).get("/api/devices/identified?limit=501").status_code == 422
