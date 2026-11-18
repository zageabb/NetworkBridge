"""SQLite history for opt-in TCP checks; failed probes do not prove outages."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta


def ensure_schema(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS device_monitor_checks (
        id INTEGER PRIMARY KEY,
        address TEXT NOT NULL,
        checked_at TEXT NOT NULL,
        tcp_responded INTEGER NOT NULL CHECK(tcp_responded IN (0, 1))
    )""")
    db.execute("""CREATE INDEX IF NOT EXISTS idx_device_monitor_checks_address
                  ON device_monitor_checks(address, id DESC)""")
    db.commit()


def record_checks(db: sqlite3.Connection, results: dict[str, bool],
                  checked_at: datetime | None = None) -> None:
    ensure_schema(db)
    now = checked_at or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("checked_at must be timezone-aware")
    db.executemany(
        "INSERT INTO device_monitor_checks(address, checked_at, tcp_responded) VALUES (?, ?, ?)",
        [(address, now.astimezone(UTC).isoformat(), int(responded))
         for address, responded in results.items()],
    )
    db.commit()


def recent_checks(db: sqlite3.Connection, limit: int = 100,
                  address: str | None = None) -> list[dict[str, object]]:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be 1..500")
    if address is not None and (not address or len(address) > 45):
        raise ValueError("Invalid address filter")
    sql = "SELECT address, checked_at, tcp_responded FROM device_monitor_checks"
    params: tuple[object, ...]
    if address is None:
        params = (limit,)
    else:
        sql += " WHERE address = ?"
        params = (address, limit)
    rows = db.execute(sql + " ORDER BY id DESC LIMIT ?", params).fetchall()
    return [{"address": ip, "checked_at": timestamp,
             "result": "tcp_responded" if responded else "no_tcp_response",
             "availability_verdict": "not_evaluated"}
            for ip, timestamp, responded in rows]


def prune_checks(db: sqlite3.Connection, retention_days: int,
                 now: datetime | None = None) -> int:
    """Delete checks older than retention_days; zero disables pruning."""
    if not 0 <= retention_days <= 3650:
        raise ValueError("retention_days must be 0..3650")
    if retention_days == 0:
        return 0
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    cutoff = (current.astimezone(UTC) - timedelta(days=retention_days)).isoformat()
    cursor = db.execute("DELETE FROM device_monitor_checks WHERE checked_at < ?", (cutoff,))
    db.commit()
    return cursor.rowcount
