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
- [ ] Production Caddy routing and built UI serving

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

## Phase 4 — Alerts and topology
- [ ] Event rules, notifications, inferred vs verified links

## Phase 5 — Advanced
- [ ] Optional agents and explicitly approved actions

Design principle: Design what matters, let AI propose what's missing, and approve what changes.
