"""Local-only observations from positive, explicitly requested discovery scans."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime


def ensure_schema(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS device_observations (
        address TEXT PRIMARY KEY,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        positive_scans INTEGER NOT NULL DEFAULT 1,
        source TEXT NOT NULL
    )""")
    db.commit()


def record_scan(db: sqlite3.Connection, devices: list[dict[str, str]]) -> None:
    """Only positive observations are persisted. Missing hosts are NOT marked offline."""
    ensure_schema(db)
    timestamp = datetime.now(UTC).isoformat()
    for device in devices:
        if device.get("state") != "tcp_reachable":
            continue
        db.execute("""INSERT INTO device_observations
            (address, first_seen, last_seen, positive_scans, source)
            VALUES (?, ?, ?, 1, 'tcp_probe')
            ON CONFLICT(address) DO UPDATE SET
              last_seen=excluded.last_seen,
              positive_scans=device_observations.positive_scans+1""",
                   (device["address"], timestamp, timestamp))
    db.commit()


def recent_observations(db: sqlite3.Connection, limit: int = 250) -> list[dict[str, object]]:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be 1..500")
    rows = db.execute("""SELECT address, first_seen, last_seen, positive_scans, source
                         FROM device_observations ORDER BY last_seen DESC LIMIT ?""",
                      (limit,)).fetchall()
    return [dict(zip(("address", "first_seen", "last_seen", "positive_scans", "source"), row))
            for row in rows]
