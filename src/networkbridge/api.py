from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from networkbridge.config import settings

app = FastAPI(title="NetworkBridge", version="0.1.0", docs_url=None, redoc_url=None)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "networkbridge"}


@app.get("/api/status")
def status() -> dict[str, object]:
    return {"phase": 1, "router_collection": "not_enabled", "devices": []}


if settings.static_dir.is_dir():
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="ui")
