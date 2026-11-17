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
authentication. Do not expose the API without authentication. The API now includes WAN history, server metrics, service reachability, resource alerts,
and an opt-in passive LAN neighbour list. These endpoints must remain behind UDA authentication.

Set `NETWORKBRIDGE_STATIC_DIR` when the built UI is stored somewhere other than `ui/dist`.

## Safety
Never commit router response captures, MAC addresses, credentials, cookies or secrets. Router monitoring is read-only and uses explicit allow-listed endpoints only. See SECURITY.md and docs/ROUTER.md.

## See recently observed machines (Ubuntu Linux)

After CI is green and the release is deployed, set
`NETWORKBRIDGE_NEIGHBOUR_DISCOVERY_ENABLED=true` in the **NetworkBridge API
service environment** (not only in the WAN polling worker), then restart the API.
Open the **Devices** screen. The **Recently observed LAN neighbours** section
shows private IPv4 addresses, MAC addresses and interfaces read from
`/proc/net/arp`. The endpoint is `GET /api/devices/neighbours`.

This is **passive** discovery: no ICMP, TCP scans, router logins or active
probes. The ARP cache can be empty and only contains neighbours recently
contacted by the Ubuntu host on reachable L2 segments. Entries do **not**
prove devices are currently online. For fuller discovery, a router device-list
integration or separately approved active discovery will be needed.

To verify locally on Ubuntu, compare the Devices screen with `cat /proc/net/arp`
(run on the same host and network namespace as NetworkBridge). Do not post
actual MAC addresses, hostnames or router captures in GitHub issues.
