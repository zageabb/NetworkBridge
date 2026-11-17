"""Local SQLite WAN history. No sensitive client identifiers are stored."""
from __future__ import annotations

import sqlite3
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
        {"sampled_at": __import__("datetime").datetime.fromtimestamp(
            bucket, tz=__import__("datetime").timezone.utc
        ).isoformat(), "download_bps": down, "upload_bps": up, "sample_count": count}
        for bucket, down, up, count in rows
    ]
