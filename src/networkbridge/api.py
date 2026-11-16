from fastapi import FastAPI

app = FastAPI(title="NetworkBridge", version="0.1.0", docs_url=None, redoc_url=None)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "networkbridge"}


@app.get("/api/status")
def status() -> dict[str, object]:
    return {"phase": 1, "router_collection": "not_enabled", "devices": []}
