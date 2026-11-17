"""Local SQLite WAN history. No sensitive client identifiers are stored."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path


def connect(path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(path))
    try:
        ensure_schema(db)
    except sqlite3.Error:
        db.close()
        raise
    return db


def ensure_schema(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS wan_samples (
        id INTEGER PRIMARY KEY,
        sampled_at TEXT NOT NULL,
        router_uptime TEXT,
        connected TEXT,
        total_bytes INTEGER NOT NULL,
        received_bytes INTEGER NOT NULL,
        transmitted_bytes INTEGER NOT NULL,
        download_bps REAL,
        upload_bps REAL
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_wan_sample_time ON wan_samples(sampled_at)")
    db.commit()


def add_wan_sample(db: sqlite3.Connection, sampled_at: str, sample: dict,
                   rate: tuple[float, float] | None) -> None:
    counters = sample["counters"]
    db.execute("""INSERT INTO wan_samples (
        sampled_at, router_uptime, connected, total_bytes, received_bytes,
        transmitted_bytes, download_bps, upload_bps
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
        sampled_at, sample.get("uptime"), sample.get("link_status"),
        counters.total, counters.received, counters.transmitted,
        rate[0] if rate else None, rate[1] if rate else None))
    db.commit()


def recent_wan(db: sqlite3.Connection, limit: int = 300) -> list[dict]:
    if not 1 <= limit <= 1000:
        raise ValueError("Limit must be 1..1000")
    if not wan_schema_exists(db):
        return []
    rows = db.execute("""SELECT sampled_at, connected, download_bps, upload_bps
        FROM wan_samples ORDER BY id DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(zip(("sampled_at", "connected", "download_bps", "upload_bps"), row))
            for row in reversed(rows)]


def wan_schema_exists(db: sqlite3.Connection) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='wan_samples'"
    ).fetchone() is not None


def aggregated_wan(db: sqlite3.Connection, hours: int) -> list[dict]:
    """Average valid WAN rates in UTC buckets; missing buckets remain gaps."""
    if hours not in (1, 24, 168):
        raise ValueError("Supported windows are 1, 24 and 168 hours")
    if not wan_schema_exists(db):
        return []
    bucket_seconds = {1: 60, 24: 900, 168: 3600}[hours]
    rows = db.execute(
        """SELECT (CAST(strftime('%s', sampled_at) AS INTEGER) / ?) * ? AS bucket,
                  AVG(download_bps), AVG(upload_bps), COUNT(*)
           FROM wan_samples
           WHERE strftime('%s', sampled_at) >= strftime('%s', 'now') - ?
             AND download_bps IS NOT NULL AND upload_bps IS NOT NULL
           GROUP BY bucket ORDER BY bucket""",
        (bucket_seconds, bucket_seconds, hours * 3600),
    ).fetchall()
    return [
        {"sampled_at": datetime.fromtimestamp(bucket, tz=UTC).isoformat(), "download_bps": down, "upload_bps": up, "sample_count": count}
        for bucket, down, up, count in rows
    ]


def prune_wan_samples(db: sqlite3.Connection, retention_days: int,
                      now: datetime | None = None) -> int:
    """Delete expired WAN samples only when retention is explicitly enabled."""
    if not 0 <= retention_days <= 3650:
        raise ValueError("retention_days must be between 0 and 3650")
    if retention_days == 0 or not wan_schema_exists(db):
        return 0
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    cutoff = (current.astimezone(UTC) - timedelta(days=retention_days)).isoformat()
    cursor = db.execute(
        "DELETE FROM wan_samples WHERE julianday(sampled_at) < julianday(?)", (cutoff,)
    )
    db.commit()
    return cursor.rowcount


def wan_usage(db: sqlite3.Connection, now: datetime | None = None) -> dict:
    """Conservative UTC usage from consecutive counters, skipping resets and gaps."""
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    current = current.astimezone(UTC)
    result = {
        "day_received_bytes": 0, "day_transmitted_bytes": 0,
        "month_received_bytes": 0, "month_transmitted_bytes": 0,
        "accepted_intervals": 0, "skipped_intervals": 0,
        "coverage": "partial_estimate",
    }
    if not wan_schema_exists(db):
        return result
    month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = db.execute(
        """SELECT sampled_at, router_uptime, received_bytes, transmitted_bytes
           FROM wan_samples
           WHERE julianday(sampled_at) >= julianday(?) - (120.0 / 86400.0)
             AND julianday(sampled_at) <= julianday(?)
           ORDER BY julianday(sampled_at), id""",
        (month_start.isoformat(), current.isoformat()),
    ).fetchall()
    previous = None
    for raw_time, uptime, received, transmitted in rows:
        timestamp = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            result["skipped_intervals"] += 1
            previous = None
            continue
        timestamp = timestamp.astimezone(UTC)
        if previous is not None:
            old_time, old_uptime, old_received, old_transmitted = previous
            elapsed = (timestamp - old_time).total_seconds()
            reset = (
                uptime is not None and old_uptime is not None
                and str(uptime).isdigit() and str(old_uptime).isdigit()
                and int(uptime) < int(old_uptime)
            )
            if (0 < elapsed <= 120 and not reset
                    and received >= old_received and transmitted >= old_transmitted):
                delta_received = received - old_received
                delta_transmitted = transmitted - old_transmitted
                if timestamp >= month_start:
                    result["month_received_bytes"] += delta_received
                    result["month_transmitted_bytes"] += delta_transmitted
                    if timestamp >= day_start:
                        result["day_received_bytes"] += delta_received
                        result["day_transmitted_bytes"] += delta_transmitted
                    result["accepted_intervals"] += 1
            else:
                result["skipped_intervals"] += 1
        previous = (timestamp, uptime, received, transmitted)
    return result
