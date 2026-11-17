from pathlib import Path

import httpx
import pytest

from networkbridge.router import Counters, SmartHubCollector, parse_counters, parse_wan_xml, rates


def test_percent_encoded_counters():
    assert parse_counters("300%3B200%3B100") == Counters(300, 200, 100)


def test_rates():
    assert rates(Counters(300, 200, 100), Counters(600, 400, 200), 10) == (160.0, 80.0)


def test_counter_reset():
    assert rates(Counters(300, 200, 100), Counters(150, 100, 50), 10) is None


def test_invalid():
    with pytest.raises(ValueError):
        parse_counters("10%3B20%3B30")


def test_xml():
    result = parse_wan_xml('<root wan_conn_volume_list="300%3B200%3B100" sysuptime="120"/>')
    assert result["counters"].received == 200


def test_collector_rejects_missing_pinned_certificate(tmp_path):
    with pytest.raises(ValueError, match="certificate is not a file"):
        SmartHubCollector("https://192.168.1.254", tmp_path / "missing.pem")


def test_collector_uses_default_verification_without_pin(monkeypatch):
    captured = {}

    class Client:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    SmartHubCollector("https://192.168.1.254")
    assert captured["verify"] is True


def test_collector_pins_configured_certificate(monkeypatch):
    captured = {}
    certificate = Path(__file__).parent / "fixtures" / "router-cert.pem"

    class Client:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    SmartHubCollector("https://192.168.1.254", certificate)
    context = captured["verify"]
    assert context.check_hostname is True
    assert context.verify_mode.name == "CERT_REQUIRED"
