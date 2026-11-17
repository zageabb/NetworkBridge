from datetime import UTC, datetime, timedelta

import pytest

from networkbridge.router import Counters
from networkbridge.storage import (
    add_wan_sample,
    aggregated_wan,
    connect,
    prune_wan_samples,
    recent_wan,
)


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


def test_retention_disabled_preserves_all_rows(tmp_path):
    db = connect(tmp_path / "retention.sqlite")
    sample = {"counters": Counters(300, 200, 100)}
    add_wan_sample(db, "2020-01-01T00:00:00Z", sample, (1.0, 2.0))
    assert prune_wan_samples(db, 0, datetime(2026, 11, 17, tzinfo=UTC)) == 0
    assert len(recent_wan(db)) == 1
    db.close()


def test_retention_removes_only_expired_rows(tmp_path):
    db = connect(tmp_path / "retention.sqlite")
    sample = {"counters": Counters(300, 200, 100)}
    add_wan_sample(db, "2026-11-01T00:00:00Z", sample, (1.0, 2.0))
    add_wan_sample(db, "2026-11-16T00:00:00+00:00", sample, (3.0, 4.0))
    assert prune_wan_samples(db, 7, datetime(2026, 11, 17, tzinfo=UTC)) == 1
    assert len(recent_wan(db)) == 1
    assert recent_wan(db)[0]["download_bps"] == 3.0
    db.close()


def test_retention_rejects_invalid_period(tmp_path):
    db = connect(tmp_path / "retention.sqlite")
    with pytest.raises(ValueError):
        prune_wan_samples(db, -1)
    with pytest.raises(ValueError):
        prune_wan_samples(db, 3651)
    db.close()
