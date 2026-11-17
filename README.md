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

## WAN history without router polling

The API and worker initialise the SQLite tables on startup, independently of
`NETWORKBRIDGE_ROUTER_POLLING_ENABLED`. Initialisation is additive and preserves
existing device observations and labels. Router polling remains disabled by default.

`GET /api/wan/history` returns HTTP 200 with `{"samples": [], "count": 0}` when
there are no samples, including a missing database or missing `wan_samples` table.
Invalid paths, unreadable/corrupt databases and incompatible existing WAN schemas
still return HTTP 503. Startup storage failures are logged while API health and
status remain available for diagnosis.

`GET /api/status` reports independent states: `router_collection` (`enabled` or
`disabled`), `database` (WAN schema `initialized`, `not_initialized`, or
`unavailable`), and `wan_history` (`available`, `no_measurements`, or `unavailable`).
The WAN Traffic page shows **No WAN measurements recorded yet** while waiting;
a database failure is displayed separately from the collector's enabled state.
`httpx` is a runtime dependency so production installs can start the worker.

Router polling requires normal TLS trust or an explicitly verified certificate
pin. For a router with a private CA, store its certificate outside the checkout,
set `NETWORKBRIDGE_ROUTER_TLS_CERTIFICATE` to that absolute PEM path, verify the
SHA-256 fingerprint independently, and then enable
`NETWORKBRIDGE_ROUTER_POLLING_ENABLED=true`. Expiry and hostname/IP validation
remain active; NetworkBridge never disables TLS verification.

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

## Local device labels (opt-in)

Set `NETWORKBRIDGE_DEVICE_ALIAS_WRITES_ENABLED=true` only when the application
is protected by UDA authentication and appropriate authorization. The custom
request header is an intentional-action safeguard, **not authentication**.
The Devices table permits saving a 1–80 character label against a currently
observed MAC address using `PUT /api/devices/alias`. Labels persist in SQLite
and are displayed only when a matching MAC is present in the current ARP cache.
They do not attach to IP addresses, so DHCP changes do not carry labels to a
new occupant. MAC addresses may also be spoofed or randomized, so labels are
operator annotations, not a verified device identity.

## WAN polling diagnostics

The independent WAN worker logs sanitized failure categories on the first failed
poll and every twelfth consecutive failed poll (roughly once per minute at the
default five-second interval). A successful sample logs recovery and resets the
failure counter. Categories include router HTTP status, timeout, connection and
invalid router response; router addresses, raw responses and exception messages
are not logged. Inspect the worker's systemd journal when WAN history stays empty.
A running worker does not prove that the router's endpoint is compatible.

## Long-term WAN history

The WAN chart offers 1-hour, 24-hour and 7-day views through
`GET /api/wan/aggregated?hours=1|24|168`. SQLite groups valid rate
measurements into UTC buckets of 60, 900 and 3600 seconds respectively,
returning mean download/upload rates and the contributing sample count.
Only existing samples are shown: gaps are not synthesized and mean rates
are not billed data usage totals. History is limited to retained raw samples;
no retention or automatic downsampling policy is implemented yet.
