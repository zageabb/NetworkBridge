from pathlib import Path

from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.server import snapshot


def test_server_snapshot(tmp_path: Path, monkeypatch):
    proc = tmp_path / "proc"
    proc.mkdir()
    (proc / "stat").write_text("cpu  100 0 50 200 20 0 0 0 0 0\n", encoding="ascii")
    (proc / "uptime").write_text("123.45 12.0\n", encoding="ascii")
    (proc / "meminfo").write_text(
        "MemTotal: 1000 kB\nMemAvailable: 400 kB\n", encoding="ascii"
    )
    monkeypatch.setattr("networkbridge.server.time.time", lambda: 1000)
    result = snapshot(proc_root=proc, disk_path=tmp_path)
    assert result["cpu"] == {"total_ticks": 370, "idle_ticks": 220}
    assert result["memory"] == {"total_bytes": 1024000, "used_bytes": 614400}
    assert result["uptime_seconds"] == 123.45
    assert result["disk"]["total_bytes"] >= 0
    assert "hostname" not in result


def test_server_health_endpoint():
    response = TestClient(app).get("/api/server/health")
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        assert "memory" in response.json()
