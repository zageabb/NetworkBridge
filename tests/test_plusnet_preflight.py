from pathlib import Path

from networkbridge.plusnet_preflight import readiness


def test_preflight_never_exposes_password():
    result = readiness(True, "https://192.168.1.254", "test-secret", None)
    assert result["state"] == "ready_for_manual_hardware_test"
    assert result["network_contacted"] is False
    assert result["authentication_attempted"] is False
    assert result["hardware_authentication_verified"] is False
    assert "test-secret" not in str(result)


def test_preflight_reports_disabled_and_invalid_configuration():
    result = readiness(False, "http://router.local/path", "", Path("/nonexistent/cert.pem"))
    assert set(result["issues"]) == {
        "inventory_disabled", "invalid_router_https_origin",
        "password_not_configured", "tls_certificate_not_found",
    }


def test_preflight_blocks_unverified_password_encoding():
    result = readiness(True, "https://192.168.1.254", "pássword", None)
    assert result["issues"] == ["password_encoding_unverified"]
