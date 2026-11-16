import pytest
from networkbridge.router import Counters, parse_counters, rates, parse_wan_xml


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
