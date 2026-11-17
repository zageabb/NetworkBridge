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

## Optional active LAN discovery

To enable the **Discover LAN devices** button, set both variables in the API
service environment and restart it:

```sh
NETWORKBRIDGE_ACTIVE_DISCOVERY_ENABLED=true
NETWORKBRIDGE_ACTIVE_DISCOVERY_CIDR=192.168.1.0/24
```

Use the actual LAN CIDR, not the example, and only on a network you administer.
Only strict private IPv4 subnets of /24 or smaller are accepted. A button click
performs bounded TCP connection attempts to ports 22, 80, 443 and 445, with
16 concurrent hosts and a one-minute process-local cooldown. A positive result
means a TCP port accepted a connection at that moment, **not** that all devices
were found. Closed ports, firewalls, isolated VLANs and sleeping machines may
cause false negatives. No hostnames or MAC addresses are inferred from probes.

The POST endpoint must remain behind UDA authentication; a custom action header
is required. This operation is disabled by default and does not run periodically.

## Persistent discovery observations

Successful, manually triggered active discovery results are recorded in the
NetworkBridge SQLite database as positive TCP observations. The Devices screen
shows first seen, last positive response and number of successful scans.
`GET /api/devices/observations` reads that history (when active discovery is
enabled). Hosts missing from later scans are **not** marked offline because
firewalls, sleeping hosts and closed ports can produce false negatives.
These records are keyed by IP address, not permanent device identity; DHCP
reassignment can associate one IP with different machines over time. Future
router-assisted MAC identification is needed for reliable device identities.

## Correlated device evidence

When either passive ARP or active discovery is enabled, the Devices screen
combines current ARP entries with stored positive TCP observations using their
IPv4 address. `GET /api/devices/identified` returns IP, currently observed
MAC/interface (if available), positive scan count and last TCP response.
This join is temporary evidence only: DHCP can reassign addresses, and a
previously observed MAC must not be attributed to a different future occupant
of that IP. No online/offline classification is asserted.

## Discovery network boundary

Active scanning is explicitly limited to RFC1918 private IPv4 blocks
(`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), with a maximum
configured scope of /24. Loopback, link-local, carrier-grade NAT and reserved
ranges are rejected even if an IP library considers them non-global. Discovery
remains disabled by default, requires the deliberate UI action and is limited
by concurrency and cooldown.
