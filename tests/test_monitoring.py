import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from networkbridge.api import app
from networkbridge.monitoring import monitoring_preflight, validate_targets


def test_rfc1918_targets_only():
    assert validate_targets("192.168.1.10,10.0.0.2") == ["192.168.1.10", "10.0.0.2"]
    for raw in ("8.8.8.8", "127.0.0.1", "::1", "192.168.1.10,192.168.1.10",
                "example.com", ",".join(["10.0.0.1"] * 33)):
        with pytest.raises(ValueError):
            validate_targets(raw)


def test_preflight_never_starts_probes_or_alerts():
    result = monitoring_preflight(True, "192.168.1.10", 60, 3)
    assert result["state"] == "ready_not_running"
    assert result["probes_running"] is False
    assert result["alerts_enabled"] is False
    assert monitoring_preflight(True, "8.8.8.8", 60, 3)["state"] == "invalid_configuration"
    assert monitoring_preflight(False, "", 60, 3)["state"] == "disabled"


def test_preflight_endpoint_defaults_disabled():
    with patch("networkbridge.api.settings.device_monitoring_enabled", False):
        response = TestClient(app).get("/api/devices/monitoring-preflight")
    assert response.status_code == 200
    assert response.json()["probes_running"] is False
