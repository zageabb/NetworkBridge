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
