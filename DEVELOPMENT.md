# Development roadmap

## WAN history initialisation fix — AWAITING ACCEPTANCE

- Shared additive initialisation of WAN, observations, labels and remembered-device
  tables at API and worker startup, independent of router polling.
- Missing WAN tables return empty HTTP 200 history; actual storage failures retain
  HTTP 503. Status separates collector, schema and measurement availability.
- WAN page distinguishes empty history from unavailable storage and keeps API
  health visible on WAN errors. `httpx` is a production dependency.
- Implementation: `database.py`, `storage.py`, `api.py`, `worker.py`, `ui/src/App.tsx`.
- Regression coverage: fresh installs with polling disabled, repeated startup and
  preservation of observations/labels, missing tables, corrupt/inaccessible storage,
  incompatible schemas, UI empty/error states and recovery.
- Local validation: 59 Python tests, 2 React regression tests, Ruff and production
  TypeScript/Vite build passed. GitHub CI passed for implementation commit `00a0c9f`
  ([run](https://github.com/zageabb/NetworkBridge/actions/runs/44108699325)).
- Merged in [PR #16](https://github.com/zageabb/NetworkBridge/pull/16) as `ad5a2e4`.
  UDA deployed that commit on 2026-11-17. Live verification: health HTTP 200;
  WAN history HTTP 200 with zero samples; status reports polling `disabled`, database
  `initialized`, history `no_measurements`; API and worker active with zero restarts;
  all 8 device observations and 1 saved alias preserved; SQLite quick check passed.
  A pre-deployment SQLite backup is retained on the Ubuntu host. User acceptance: pending.

## Router TLS certificate pinning — AWAITING ACCEPTANCE

- Add opt-in trust for an explicitly verified router certificate while retaining
  certificate expiry and hostname/IP validation.
- Keep system CA verification as the default and reject missing certificate files.
- Local validation: 64 Python tests, Ruff, 2 React regression tests and the
  production TypeScript/Vite build pass. Merged in
  [PR #18](https://github.com/zageabb/NetworkBridge/pull/18) as `963e606`.
- UDA deployed the release on 2026-11-17. The installed BT Hub certificate pin
  matched the independently inspected SHA-256 fingerprint; expiry and IP SAN checks
  remain active. The worker established verified HTTPS and received HTTP 200 responses.
  User acceptance: pending.

## Live BT Hub WAN response parser — AWAITING ACCEPTANCE

- Support the router's node/value XML shape and select its active WAN counter group
  using `wan_active_idx`, without executing router-supplied content.
- Preserve support for the existing synthetic attribute-shaped fixtures.
- Local validation is included in the 64-test suite above. Merged in
  [PR #19](https://github.com/zageabb/NetworkBridge/pull/19) as `6f8e7af` and deployed
  through UDA on 2026-11-17.
- Live verification: router polling `enabled`; WAN history `available`; six samples
  stored after deployment; the latest five all contained calculated upload/download
  rates and link state `connected`; API and worker active with zero restarts; SQLite
  quick check passed; the original 8 device observations remain present.
  User acceptance: pending.

## Phase 1 — Foundation
- [x] FastAPI health/status skeleton
- [x] Independent asyncio worker skeleton
- [x] React/Vite dashboard skeleton
- [x] Configuration and local-only defaults
- [x] Initial unit tests and CI workflow
- [x] Ubuntu systemd example units
- [x] Run tests in CI and verify on Ubuntu
- [x] Complete UDA integration before exposing private endpoints
- [x] Built UI serving compatible with a stripped UDA path prefix
- [x] Production Caddy routing on the target UDA host

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
