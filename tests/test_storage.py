from networkbridge.router import Counters
from networkbridge.storage import add_wan_sample, connect, recent_wan


def test_wan_storage(tmp_path):
    db = connect(tmp_path / "test.sqlite")
    sample = {"counters": Counters(300, 200, 100), "uptime": "100", "link_status": "up"}
    add_wan_sample(db, "2026-11-16T10:00:00Z", sample, (160.0, 80.0))
    assert recent_wan(db) == [{
        "sampled_at": "2026-11-16T10:00:00Z", "connected": "up",
        "download_bps": 160.0, "upload_bps": 80.0
    }]
    db.close()
