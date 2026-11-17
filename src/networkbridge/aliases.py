"""User-defined labels for observed MAC addresses; never infer identity from DHCP IP."""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime

MAC = re.compile(r"^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$")


def validate(mac: str, label: str) -> tuple[str, str]:
    normalized = mac.strip().lower()
    cleaned = label.strip()
    if not MAC.fullmatch(normalized) or normalized in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"):
        raise ValueError("Invalid MAC address")
    if not 1 <= len(cleaned) <= 80 or any(ord(char) < 32 or ord(char) == 127 for char in cleaned):
        raise ValueError("Label must be 1–80 printable characters")
    return normalized, cleaned


def ensure_schema(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS device_aliases (
        mac TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    db.commit()


def save_alias(db: sqlite3.Connection, mac: str, label: str) -> None:
    mac, label = validate(mac, label)
    ensure_schema(db)
    db.execute("""INSERT INTO device_aliases(mac, label, updated_at)
                  VALUES (?, ?, ?) ON CONFLICT(mac) DO UPDATE SET
                  label=excluded.label, updated_at=excluded.updated_at""",
               (mac, label, datetime.now(UTC).isoformat()))
    db.commit()


def list_aliases(db: sqlite3.Connection) -> dict[str, str]:
    rows = db.execute("SELECT mac, label FROM device_aliases LIMIT 500").fetchall()
    return dict(rows)
