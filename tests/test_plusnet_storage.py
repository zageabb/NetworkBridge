import sqlite3

from networkbridge.plusnet_storage import ensure_schema, recent_inventory, save_inventory


def test_inventory_snapshot_replace_and_empty_preservation():
    with sqlite3.connect(":memory:") as db:
        ensure_schema(db)
        record = {
            "mac": "aa:bb:cc:dd:ee:ff", "ip": "192.168.1.7",
            "hostname": "host", "name": "Example", "port": "wl0",
            "connection": "wifi_5ghz", "address_assignment": "dhcp",
            "router_active": True, "ipv4_active": None,
            "first_seen": None, "last_active": None,
        }
        assert save_inventory(db, [record]) == 1
        assert save_inventory(db, []) == 0
        rows = recent_inventory(db)
        assert len(rows) == 1
        assert rows[0]["mac"] == record["mac"]
        assert rows[0]["router_active"] is True
        assert rows[0]["ipv4_active"] is None


def test_same_mac_multiple_interfaces_and_legacy_migration():
    with sqlite3.connect(":memory:") as db:
        db.execute(
            """CREATE TABLE plusnet_inventory (
                mac TEXT PRIMARY KEY, ip TEXT NOT NULL, hostname TEXT NOT NULL,
                name TEXT NOT NULL, port TEXT NOT NULL, connection TEXT NOT NULL,
                address_assignment TEXT NOT NULL, router_active INTEGER NOT NULL,
                ipv4_active INTEGER, first_seen TEXT, last_active TEXT,
                collected_at TEXT NOT NULL
            )"""
        )
        db.execute(
            """INSERT INTO plusnet_inventory VALUES
            ('aa:bb:cc:dd:ee:ff','192.168.1.2','old','Old','wired',
             'ethernet','dhcp',1,NULL,NULL,NULL,'2026-01-01')"""
        )
        ensure_schema(db)
        assert len(recent_inventory(db)) == 1
        original = recent_inventory(db)[0]
        second = {
            "mac": original["mac"], "ip": "192.168.1.3",
            "hostname": "new", "name": "New", "port": "wl0",
            "connection": "wifi_5ghz", "address_assignment": "dhcp",
            "router_active": True, "ipv4_active": True,
            "first_seen": None, "last_active": None,
        }
        first = {key: original[key] for key in second}
        assert save_inventory(db, [first, second]) == 2
        assert len(recent_inventory(db)) == 2
        ensure_schema(db)
        assert len(recent_inventory(db)) == 2
