from datetime import UTC, datetime, timedelta

import pytest

from networkbridge.router import Counters
from networkbridge.storage import add_wan_sample, aggregated_wan, connect, recent_wan


def test_wan_storage(tmp_path):
    db = connect(tmp_path / "test.sqlite")
    sample = {"counters": Counters(300, 200, 100), "uptime": "100", "link_status": "up"}
    add_wan_sample(db, "2026-11-16T10:00:00Z", sample, (160.0, 80.0))
    assert recent_wan(db) == [{
        "sampled_at": "2026-11-16T10:00:00Z", "connected": "up",
        "download_bps": 160.0, "upload_bps": 80.0
    }]
    db.close()


def test_aggregated_wan_groups_valid_samples(tmp_path):
    db = connect(tmp_path / "aggregate.sqlite")
    now = datetime.now(UTC).replace(second=10, microsecond=0)
    sample = {"counters": Counters(300, 200, 100), "link_status": "connected"}
    add_wan_sample(db, (now - timedelta(seconds=15)).isoformat(), sample, (100.0, 20.0))
    add_wan_sample(db, (now - timedelta(seconds=10)).isoformat(), sample, (300.0, 60.0))
    add_wan_sample(db, (now - timedelta(seconds=5)).isoformat(), sample, None)
    result = aggregated_wan(db, 1)
    assert result
    assert sum(item["sample_count"] for item in result) == 2
    assert all(item["download_bps"] is not None for item in result)
    db.close()


def test_aggregated_wan_missing_table_and_invalid_window(tmp_path):
    import sqlite3

    db = sqlite3.connect(tmp_path / "empty.sqlite")
    assert aggregated_wan(db, 24) == []
    with pytest.raises(ValueError):
        aggregated_wan(db, 2)
    db.close()
