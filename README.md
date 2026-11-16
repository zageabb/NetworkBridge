# NetworkBridge

Self-hosted, local-first router and Ubuntu service monitoring.

## Phase 1
- FastAPI backend and independent background worker
- React/Vite dashboard
- SQLite storage for initial release
- localhost-only API, Caddy path /apps/networkbridge/
- Synthetic tests; no live router polling until Phase 2

## Quick start (development)
Python 3.12+:
```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn networkbridge.api:app --host 127.0.0.1 --port 8765
```
In another terminal:
```sh
cd ui && npm install && npm run dev
```
For production build: `cd ui && npm ci && npm run build`. FastAPI serves the resulting
`ui/dist` directory, including when UDA strips the `/apps/networkbridge/` prefix before
proxying to `127.0.0.1:8765`. Configure Caddy to protect the complete route with UDA
authentication. Do not expose the API without authentication. The example API currently
serves health/status only; no device data is exposed.

Set `NETWORKBRIDGE_STATIC_DIR` when the built UI is stored somewhere other than `ui/dist`.

## Safety
Never commit router response captures, MAC addresses, credentials, cookies or secrets. Router monitoring is read-only and uses explicit allow-listed endpoints only. See SECURITY.md and docs/ROUTER.md.
