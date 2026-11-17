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
    db.execute("""CREATE TABLE IF NOT EXISTS device_observation_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        source TEXT NOT NULL
    )""")
    db.execute("""CREATE INDEX IF NOT EXISTS idx_device_observation_events_time
                  ON device_observation_events(observed_at DESC)""")
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
        db.execute("""INSERT INTO device_observation_events (address, observed_at, source)
                      VALUES (?, ?, ?)""", (device["address"], timestamp, "tcp_probe"))
    db.commit()


def recent_observations(db: sqlite3.Connection, limit: int = 250) -> list[dict[str, object]]:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be 1..500")
    rows = db.execute("""SELECT address, first_seen, last_seen, positive_scans, source
                         FROM device_observations ORDER BY last_seen DESC LIMIT ?""",
                      (limit,)).fetchall()
    return [dict(zip(("address", "first_seen", "last_seen", "positive_scans", "source"), row))
            for row in rows]


def observation_recency(devices: list[dict[str, object]],
                        now: datetime | None = None,
                        recent_within_minutes: int = 15) -> list[dict[str, object]]:
    """Annotate positive scan history without claiming that hosts are online."""
    if not 1 <= recent_within_minutes <= 1440:
        raise ValueError("recent_within_minutes must be 1..1440")
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    result = []
    for device in devices:
        row = dict(device)
        try:
            last_seen = datetime.fromisoformat(str(row["last_seen"]))
            if last_seen.tzinfo is None:
                raise ValueError("Naive timestamp")
            age = (current.astimezone(UTC) - last_seen.astimezone(UTC)).total_seconds()
            row["minutes_since_seen"] = round(max(age, 0) / 60, 1)
            row["recency"] = (
                "recent_positive" if 0 <= age <= recent_within_minutes * 60
                else "previously_observed"
            )
        except (ValueError, TypeError, OverflowError, KeyError):
            row["minutes_since_seen"] = None
            row["recency"] = "unknown"
        result.append(row)
    return result


def observation_events(db: sqlite3.Connection, address: str | None = None,
                       limit: int = 100) -> list[dict[str, object]]:
    """Recent positive scan events only; never synthesise negative observations."""
    if not 1 <= limit <= 500:
        raise ValueError("limit must be 1..500")
    if address is not None and (not address or len(address) > 45):
        raise ValueError("Invalid address filter")
    if address is None:
        rows = db.execute(
            "SELECT address, observed_at, source FROM device_observation_events "
            "ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT address, observed_at, source FROM device_observation_events "
            "WHERE address = ? ORDER BY id DESC LIMIT ?", (address, limit)
        ).fetchall()
    return [dict(zip(("address", "observed_at", "source"), row)) for row in rows]
