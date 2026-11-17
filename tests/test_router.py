from pathlib import Path

import httpx
import logging
import pytest

from networkbridge.router import Counters, PollDiagnostics, SmartHubCollector, parse_counters, parse_wan_xml, rates


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


def test_live_shaped_xml_uses_active_wan_counter_group():
    payload = """<status>
        <wan_conn_volume_list type="list"
            value="[['0%3B0%3B0'], ['300%3B200%3B100'], ['0%3B0%3B0'], null]"/>
        <wan_active_idx value="1"/>
        <sysuptime value="120"/>
        <link_status value="connected%3Bvdsl%3B19838"/>
        <status_rate value="18.6 Mbps%3B4.4 Mbps"/>
    </status>"""
    result = parse_wan_xml(payload)
    assert result["counters"] == Counters(300, 200, 100)
    assert result["uptime"] == "120"
    assert result["link_status"] == "connected"


def test_live_shaped_xml_rejects_invalid_active_index():
    payload = """<status>
        <wan_conn_volume_list value="[['300%3B200%3B100']]"/>
        <wan_active_idx value="5"/>
    </status>"""
    with pytest.raises(ValueError, match="active WAN counter index"):
        parse_wan_xml(payload)


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


def test_poll_diagnostics_rate_limited_and_recovery(caplog):
    diagnostic = PollDiagnostics()
    with caplog.at_level(logging.INFO, logger="networkbridge.router"):
        for _ in range(13):
            diagnostic.failure(ValueError("secret router response data"))
        diagnostic.success()
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert "consecutive_failures=1" in warnings[0].message
    assert "consecutive_failures=12" in warnings[1].message
    assert "recovered after 13 failed attempts" in caplog.text
    assert "secret router response data" not in caplog.text
    assert diagnostic.failures == 0


def test_poll_diagnostics_classifies_without_leaking_urls(caplog):
    diagnostic = PollDiagnostics()
    with caplog.at_level(logging.WARNING, logger="networkbridge.router"):
        diagnostic.failure(httpx.ConnectError("https://router.local/private?password=secret"))
    assert "reason=router_connection" in caplog.text
    assert "password=secret" not in caplog.text
