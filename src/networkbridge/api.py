"""Local-only API for aggregate WAN monitoring history."""

import sqlite3
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from networkbridge.alerts import evaluate
from networkbridge.aliases import ensure_schema as ensure_alias_schema
from networkbridge.aliases import list_aliases, save_alias
from networkbridge.config import settings
from networkbridge.devices import list_devices
from networkbridge.discovery import scan
from networkbridge.environment import environment_report
from networkbridge.identity import correlate
from networkbridge.neighbours import neighbours
from networkbridge.observations import recent_observations, record_scan
from networkbridge.server import snapshot
from networkbridge.services import check_services
from networkbridge.storage import recent_wan

app = FastAPI(title="NetworkBridge", version="0.2.0", docs_url=None, redoc_url=None)


class AliasUpdate(BaseModel):
    mac: str
    label: str


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


@app.post("/api/devices/discover")
async def discover_devices(x_networkbridge_action: str | None = Header(default=None)) -> dict:
    if not settings.active_discovery_enabled or not settings.active_discovery_cidr:
        raise HTTPException(status_code=403, detail="Active discovery is disabled")
    if x_networkbridge_action != "discover":
        raise HTTPException(status_code=403, detail="Explicit discovery action required")
    try:
        result = await scan(settings.active_discovery_cidr)
        path = database_path(settings.database_url)
        try:
            with sqlite3.connect(path, timeout=2) as db:
                record_scan(db, result["devices"])
        except (sqlite3.Error, OSError):
            result["persistence"] = "unavailable"
        else:
            result["persistence"] = "saved"
        return result
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid configured discovery subnet") from None
    except RuntimeError:
        raise HTTPException(status_code=429, detail="Discovery cooldown active") from None


@app.get("/api/devices/observations")
def observations(limit: int = 250) -> dict[str, object]:
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit must be 1..500")
    if not settings.active_discovery_enabled:
        return {"devices": [], "collection": "disabled"}
    path = database_path(settings.database_url)
    if not path.is_file():
        return {"devices": [], "collection": "not_initialized"}
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2) as db:
            devices = recent_observations(db, limit)
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return {"devices": [], "collection": "not_initialized"}
        raise HTTPException(status_code=503, detail="Observations unavailable") from None
    return {"devices": devices, "collection": "positive_tcp_observations"}


@app.get("/api/devices/identified")
def identified_devices(limit: int = 250) -> dict[str, object]:
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit must be 1..500")
    if not (settings.active_discovery_enabled or settings.neighbour_discovery_enabled):
        return {"devices": [], "collection": "disabled"}
    observed = []
    if settings.active_discovery_enabled:
        path = database_path(settings.database_url)
        if path.is_file():
            try:
                with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2) as db:
                    observed = recent_observations(db, 500)
            except sqlite3.OperationalError as exc:
                if "no such table" not in str(exc):
                    raise HTTPException(status_code=503, detail="Observations unavailable") from None
    arp = []
    if settings.neighbour_discovery_enabled:
        try:
            arp = neighbours(limit=500)
        except (OSError, ValueError):
            raise HTTPException(status_code=503, detail="Neighbour cache unavailable") from None
    identified = correlate(observed, arp, limit)
    path = database_path(settings.database_url)
    if path.is_file():
        try:
            with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2) as db:
                labels = list_aliases(db)
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc):
                raise HTTPException(status_code=503, detail="Device labels unavailable") from None
            labels = {}
    else:
        labels = {}
    for item in identified:
        item["label"] = labels.get(item["mac"]) if item["mac"] else None
    return {"devices": identified, "collection": "correlated_evidence",
            "note": "ARP and historical TCP IP joins do not establish permanent device identity"}


@app.put("/api/devices/alias")
def update_device_alias(
    body: AliasUpdate,
    x_networkbridge_action: str | None = Header(default=None),
) -> dict[str, str]:
    if not settings.device_alias_writes_enabled:
        raise HTTPException(status_code=403, detail="Device alias writes disabled")
    if x_networkbridge_action != "save-device-alias":
        raise HTTPException(status_code=403, detail="Explicit device alias action required")
    try:
        path = database_path(settings.database_url)
        with sqlite3.connect(path, timeout=2) as db:
            ensure_alias_schema(db)
            save_alias(db, body.mac, body.label)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except (sqlite3.Error, OSError):
        raise HTTPException(status_code=503, detail="Device alias storage unavailable") from None
    return {"status": "saved"}


if settings.static_dir.is_dir():
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="ui")
