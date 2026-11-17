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

## Optional WAN sample retention

WAN sample deletion is **disabled by default**. To limit raw WAN history growth,
set `NETWORKBRIDGE_WAN_RETENTION_DAYS=30` in the independent polling worker's
environment and restart it. Valid values are 0 (off) through 3650 days. When
polling successfully writes a sample, the worker removes samples older than the
configured period at most once per UTC day and logs the deleted row count.
This is destructive for expired samples; back up SQLite before enabling. Keep
at least seven days if you need the full 7-day WAN chart. This does not delete
device observations, labels or other tables. SQLite may retain freed disk pages
until a separately scheduled, maintenance-window VACUUM; no automatic VACUUM
runs during polling.

## Observed WAN data usage

`GET /api/wan/usage` reports today's and this month's observed download and
upload byte totals in UTC. Values are sums of consecutive router counter deltas
with at most 120 seconds between samples. Counter decreases, detected uptime
resets and longer gaps are skipped, so figures are **partial estimates**, not
ISP billing totals. Deltas are assigned to the later sample's UTC day/month;
intervals crossing midnight are not split. Retention and missing measurements
reduce historical coverage. No device-specific usage is inferred.

## WAN collector freshness

`GET /api/wan/collector-health` reports `disabled`, `no_measurements`,
`fresh`, `stale`, or `invalid_timestamp` with the last persisted WAN sample
and its age. The default stale threshold is 30 seconds (six nominal 5-second
polls). Freshness checks are read-only and do not contact the router. A stale
sample is a symptom, not a definitive diagnosis: consult the WAN worker logs
for sanitized failure reasons. The UI shows a warning for stale samples.

## Device observation recency

The opt-in `GET /api/devices/observations` response includes `recency`
(`recent_positive`, `previously_observed`, or `unknown`) and
`minutes_since_seen`. A positive TCP probe within the last 15 minutes is
labelled recent; older observations remain visible. This is **not** a live
online/offline determination: no background probing is added, and hosts that
reject TCP probes may not appear. Historical IP addresses can be reassigned.

Device observation recency can be configured with
`NETWORKBRIDGE_DEVICE_RECENCY_MINUTES=30` (allowed 1–1440; default 15).
This changes labels only, not discovery frequency, and does not initiate
background scans. The API returns the effective `recency_window_minutes`.

## Device discovery event history

Successful TCP probes from explicitly initiated LAN scans are appended to
`device_observation_events` in SQLite, in addition to the existing per-IP
summary. The read-only `GET /api/devices/observation-events` endpoint accepts
`limit=1..500` (default 100) and optional exact `address` filter. The Devices
screen displays the 100 latest positive events. Existing summary observations
are not backfilled into individual events; no negative/offline events are
inferred, and no background scanning is introduced. Future retention controls
should bound the event table for long-running installations.

## Device event retention

Set `NETWORKBRIDGE_DEVICE_EVENT_RETENTION_DAYS=30` to prune positive
observation event rows older than 30 days after each **explicitly requested**
LAN discovery scan. Allowed range is 0–3650 days; default `0` disables
pruning and preserves existing data. This does not delete the per-IP device
observation summary, run scheduled scans, or infer devices are offline.
If no further manual scan occurs, expired rows remain until the next scan.
