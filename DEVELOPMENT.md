# Development roadmap

## Phase 1 — Foundation
- [x] FastAPI health/status skeleton
- [x] Independent asyncio worker skeleton
- [x] React/Vite dashboard skeleton
- [x] Configuration and local-only defaults
- [x] Initial unit tests and CI workflow
- [x] Ubuntu systemd example units
- [ ] Run tests in CI and verify on Ubuntu
- [ ] Complete UDA integration before exposing private endpoints
- [x] Built UI serving compatible with a stripped UDA path prefix
- [ ] Production Caddy routing on the target UDA host

## Phase 2 — BT Smart Hub router
- [ ] Establish read-only unauthenticated session
- [ ] GET /nonAuth/wan_conn.xml at 5-second intervals
- [ ] GET /cgi/cgi_home.js at 30–60-second intervals
- [ ] Hardened XML and non-executing JS parsing
- [ ] Calculate rates from counter deltas; detect resets/reboots
- [ ] Persist to SQLite with retention/aggregation
- [ ] Display history, live rates and private device inventory
- [ ] Alerts and synthetic fixture tests

## Phase 3 — Ubuntu monitoring
- [ ] psutil/systemd, Caddy, PostgreSQL, Ollama, Docker checks
- [ ] Endpoint health and certificate checks
- [ ] Resource history and alert thresholds

## Phase 3A — Server environment inventory and reports
- [ ] Add an on-demand **Environment Report** screen with refresh, history, comparison, and download (JSON, Markdown, optionally PDF).
- [ ] Collect OS distribution/version, kernel, architecture, hostname pseudonym, boot time and uptime.
- [ ] Collect RAM/swap totals and utilization, CPU model/count/load, mounted filesystems, disk capacity/free space (including root).
- [ ] Inventory installed software versions: Python, Node.js/npm, PostgreSQL client/server, Caddy, Ollama, Docker, and configurable additional executables; distinguish not installed, inaccessible, and failed.
- [ ] Discover PostgreSQL clusters via pg_lsclusters when available, including version, port, state and data directory with sensitive paths redacted by default.
- [ ] Report systemd services: running, failed, enabled, and selected inactive services, including descriptions and uptime where available.
- [ ] Include network interfaces, listening ports (process details only where authorized), and app health endpoints as optional report sections.
- [ ] Generate human-readable summary plus machine-readable structured snapshot with collection timestamp, host identifier, tool versions, and individual check errors.
- [ ] Support baseline comparison: highlight software upgrades, changed services, capacity changes, and newly failed services.
- [ ] Provide a scheduled weekly snapshot option and alerts on meaningful changes.
- [ ] Run collectors as a restricted local agent using psutil, /etc/os-release, /proc, /sys, and allow-listed subprocess commands with fixed arguments; never accept arbitrary shell input from the web UI.
- [ ] Add timeouts, output size limits, error handling, secrets/hostname/path redaction, RBAC and audit logging; require UDA authentication to view reports.
- [ ] Add synthetic fixtures and tests for missing tools, nonzero exits, malformed output, large service lists and permission failures.
- [ ] Keep report collection read-only and disabled for remote hosts until an explicitly approved agent/SSH integration exists.

## Phase 4 — Alerts and topology
- [ ] Event rules, notifications, inferred vs verified links

## Phase 5 — Advanced
- [ ] Optional agents and explicitly approved actions

Design principle: Design what matters, let AI propose what's missing, and approve what changes.
