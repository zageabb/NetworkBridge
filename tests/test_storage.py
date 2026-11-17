from datetime import UTC, datetime, timedelta

import pytest

from networkbridge.router import Counters
from networkbridge.storage import (
    add_wan_sample,
    aggregated_wan,
    connect,
    prune_wan_samples,
    recent_wan,
    wan_freshness,
    wan_usage,
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


def test_usage_counts_valid_deltas_and_skips_counter_reset(tmp_path):
    db = connect(tmp_path / "usage.sqlite")
    now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    def record(at, received, transmitted, uptime):
        add_wan_sample(
            db, at, {"counters": Counters(received + transmitted, received, transmitted),
                     "uptime": uptime}, (1.0, 1.0)
        )
    record("2026-11-17T11:58:00Z", 100, 50, "100")
    record("2026-11-17T11:58:05Z", 300, 100, "105")
    record("2026-11-17T11:58:10Z", 20, 10, "1")
    record("2026-11-17T11:58:15Z", 70, 40, "6")
    record("2026-11-17T11:59:55Z", 100, 60, "106")
    result = wan_usage(db, now)
    assert result["day_received_bytes"] == 280
    assert result["day_transmitted_bytes"] == 100
    assert result["month_received_bytes"] == 280
    assert result["skipped_intervals"] == 1
    db.close()


def test_usage_skips_long_gaps(tmp_path):
    db = connect(tmp_path / "usage.sqlite")
    sample = {"counters": Counters(300, 200, 100), "uptime": "100"}
    add_wan_sample(db, "2026-11-17T10:00:00Z", sample, None)
    sample2 = {"counters": Counters(600, 400, 200), "uptime": "500"}
    add_wan_sample(db, "2026-11-17T10:10:00Z", sample2, None)
    result = wan_usage(db, datetime(2026, 11, 17, 12, tzinfo=UTC))
    assert result["day_received_bytes"] == 0
    assert result["skipped_intervals"] == 1
    db.close()


def test_collector_freshness_states(tmp_path):
    db = connect(tmp_path / "freshness.sqlite")
    now = datetime(2026, 11, 17, 12, tzinfo=UTC)
    assert wan_freshness(db, now)["state"] == "no_measurements"
    sample = {"counters": Counters(300, 200, 100)}
    add_wan_sample(db, "2026-11-17T11:59:50Z", sample, (1.0, 2.0))
    assert wan_freshness(db, now)["state"] == "fresh"
    assert wan_freshness(db, now + timedelta(seconds=31))["state"] == "stale"
    with pytest.raises(ValueError):
        wan_freshness(db, now, 0)
    db.close()
