"""Read-only query and explicit-write persistence for Hub Two inventory snapshots."""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS plusnet_inventory (
    mac TEXT PRIMARY KEY,
    ip TEXT NOT NULL,
    hostname TEXT NOT NULL,
    name TEXT NOT NULL,
    port TEXT NOT NULL,
    connection TEXT NOT NULL,
    address_assignment TEXT NOT NULL,
    router_active INTEGER NOT NULL,
    ipv4_active INTEGER,
    first_seen TEXT,
    last_active TEXT,
    collected_at TEXT NOT NULL
);
"""


def ensure_schema(db: sqlite3.Connection) -> None:
    db.executescript(SCHEMA)
    db.commit()


def save_inventory(db: sqlite3.Connection, devices: list[dict[str, object]]) -> int:
    """Replace the current snapshot atomically; empty snapshots are not destructive."""
    if not devices:
        return 0
    stamp = datetime.now(UTC).isoformat()
    rows = []
    for device in devices:
        rows.append((
            device["mac"], device["ip"], device["hostname"], device["name"],
            device["port"], device["connection"], device["address_assignment"],
            int(device["router_active"]),
            None if device["ipv4_active"] is None else int(device["ipv4_active"]),
            device["first_seen"], device["last_active"], stamp,
        ))
    with db:
        db.execute("DELETE FROM plusnet_inventory")
        db.executemany(
            """INSERT INTO plusnet_inventory (
                mac, ip, hostname, name, port, connection, address_assignment,
                router_active, ipv4_active, first_seen, last_active, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
    return len(rows)


def recent_inventory(db: sqlite3.Connection, limit: int = 250) -> list[dict[str, object]]:
    rows = db.execute(
        """SELECT mac, ip, hostname, name, port, connection, address_assignment,
                  router_active, ipv4_active, first_seen, last_active, collected_at
           FROM plusnet_inventory ORDER BY name, mac LIMIT ?""", (limit,)
    ).fetchall()
    keys = ("mac", "ip", "hostname", "name", "port", "connection",
            "address_assignment", "router_active", "ipv4_active",
            "first_seen", "last_active", "collected_at")
    return [
        {**dict(zip(keys, row)),
         "router_active": bool(row[7]),
         "ipv4_active": None if row[8] is None else bool(row[8]),
         "source": "plusnet_hub_two"}
        for row in rows
    ]
