"""Local-only API for aggregate WAN monitoring history."""

import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from networkbridge.alerts import evaluate
from networkbridge.config import settings
from networkbridge.devices import list_devices
from networkbridge.environment import environment_report
from networkbridge.neighbours import neighbours
from networkbridge.server import snapshot
from networkbridge.services import check_services
from networkbridge.storage import recent_wan

app = FastAPI(title="NetworkBridge", version="0.2.0", docs_url=None, redoc_url=None)


def database_path(url: str) -> Path:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError("Only SQLite is supported")
    return Path(url[len(prefix):])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "networkbridge"}


@app.get("/api/status")
def status() -> dict[str, object]:
    return {
        "phase": 2,
        "router_collection": "enabled" if settings.router_polling_enabled else "disabled",
        "devices": [],
    }


@app.get("/api/wan/history")
def wan_history(limit: int = 300) -> dict[str, object]:
    if not 1 <= limit <= 1000:
        raise HTTPException(status_code=422, detail="limit must be 1..1000")
    path = database_path(settings.database_url)
    if not path.is_file():
        return {"samples": [], "count": 0}
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2) as db:
            samples = recent_wan(db, limit)
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="WAN history unavailable") from None
    return {"samples": samples, "count": len(samples)}


@app.get("/api/server/health")
def server_health() -> dict:
    try:
        return snapshot()
    except (OSError, ValueError, KeyError, IndexError):
        raise HTTPException(status_code=503, detail="Server metrics unavailable") from None


@app.get("/api/services")
def services() -> dict[str, object]:
    return {"services": check_services(), "note": "Loopback TCP reachability only; not application health"}


@app.get("/api/environment")
def environment() -> dict[str, str]:
    return environment_report()


@app.get("/api/devices")
def devices(limit: int = 250) -> dict[str, object]:
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit must be 1..500")
    if not settings.router_polling_enabled:
        return {"devices": [], "collection": "disabled"}
    path = database_path(settings.database_url)
    if not path.is_file():
        return {"devices": [], "collection": "not_initialized"}
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2) as db:
            found = list_devices(db, limit)
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return {"devices": [], "collection": "not_initialized"}
        raise HTTPException(status_code=503, detail="Device inventory unavailable") from None
    return {"devices": found, "collection": "stored_inventory"}


@app.get("/api/alerts")
def alerts() -> dict[str, object]:
    try:
        host = snapshot()
        active = evaluate(host, settings.memory_alert_percent, settings.disk_alert_percent)
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(status_code=503, detail="Resource alerts unavailable") from None
    return {"alerts": active, "count": len(active), "sampled_at_unix": host["sampled_at_unix"],
            "mode": "current_snapshot_only"}


@app.get("/api/devices/neighbours")
def live_neighbours(limit: int = 250) -> dict[str, object]:
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit must be 1..500")
    if not settings.neighbour_discovery_enabled:
        return {"devices": [], "collection": "disabled", "source": "linux_arp_cache"}
    try:
        found = neighbours(limit=limit)
    except (OSError, ValueError):
        raise HTTPException(status_code=503, detail="Neighbour cache unavailable") from None
    return {"devices": found, "collection": "passive", "source": "linux_arp_cache"}


if settings.static_dir.is_dir():
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="ui")
