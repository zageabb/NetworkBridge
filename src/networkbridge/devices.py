"""Read-only inventory persistence for opt-in router discovery.

Device collection is not enabled until the router payload has a validated parser.
No real identifiers are embedded in source code.
"""

from __future__ import annotations

import sqlite3


def ensure_device_schema(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS remembered_devices (
        device_key TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        address TEXT,
        connection_type TEXT,
        last_seen TEXT,
        observed_at TEXT NOT NULL
    )""")
    db.commit()


def list_devices(db: sqlite3.Connection, limit: int = 250) -> list[dict[str, str | None]]:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be 1..500")
    rows = db.execute("""SELECT display_name, address, connection_type, last_seen,
                                observed_at
                         FROM remembered_devices
                         ORDER BY display_name COLLATE NOCASE LIMIT ?""", (limit,)).fetchall()
    fields = ("name", "address", "connection_type", "last_seen", "observed_at")
    return [dict(zip(fields, row)) for row in rows]
