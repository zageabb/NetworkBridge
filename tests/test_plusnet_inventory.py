import pytest

from networkbridge.plusnet_inventory import parse_inventory


def test_parses_device_and_multiple_interfaces():
    raw = """var known_device_list = [
      {mac:"AA:BB:CC:DD:EE:01,AA:BB:CC:DD:EE:02",
       ip:"192.168.1.20,192.168.1.21", name:"Laptop",
       hostname:"laptop", port:"wl0,wl1", activity:"1",
       activity_ip:"1,0", dhcp_option:"NA",
       time_first_seen:"123", time_last_active:"456"}
    ];"""
    records = parse_inventory(raw)
    assert len(records) == 2
    assert records[0]["connection"] == "wifi_5ghz"
    assert records[1]["connection"] == "wifi_2_4ghz"
    assert records[0]["address_assignment"] == "static"
    assert records[0]["router_active"] is True
    assert records[1]["ipv4_active"] is False


def test_missing_list_rejected():
    with pytest.raises(ValueError):
        parse_inventory("var other = [];")


def test_oversized_payload_rejected():
    with pytest.raises(ValueError):
        parse_inventory("x" * 1_000_001)


def test_invalid_mac_skipped():
    assert parse_inventory('var known_device_list = [{mac:"invalid",ip:"192.168.1.1"}];') == []
