# NetworkBridge — UDA V2 review (DEV-020)

**Draft only: no production installation, router polling, scanning, database writes or migration permission.**

Source examined: `README.md`, `pyproject.toml`, `src/networkbridge/api.py`,
`src/networkbridge/worker.py`, `src/networkbridge/database.py`,
`deploy/networkbridge-api.service`, `deploy/networkbridge-worker.service`
and `ui/package.json` / `ui/package-lock.json`.

- API `uvicorn networkbridge.api:app` listens on loopback port 8765 and serves
  the built Vite UI from `ui/dist`. Both API and worker are separate
  processes; their runtime and health must be assessed independently.
- Worker uses `python -m networkbridge.worker`; router polling is opt-in
  (`NETWORKBRIDGE_ROUTER_POLLING_ENABLED=false` by default).
- UI `npm ci && npm run build` is source-backed; a committed npm lockfile
  exists. Browser-facing /apps/networkbridge/ must remain UDA authenticated.
- **Database mutation blocker:** both API lifespan and worker startup call
  `initialize_database`, which creates/adjusts several SQLite tables.
  Its writes must be classified and reviewed as a migration; not implicitly
  authorized by a valid V2 manifest. Current V2 draft intentionally omits
  a database-write capability pending path/backup/restore review.
- **Discovery boundary:** passive ARP reading and opt-in active TCP discovery
  have distinct privacy/network permissions; do not enable active discovery,
  router admin login, TLS certificate overrides or router polling implicitly.
- `deploy/` systemd files are examples for a service account, not proof
  of the effective host units. Inspect exact user/system service ownership,
  storage paths and protected env file *names* read-only on `m901-lenovo`.

Outstanding:
- [ ] Canonical V2 schema and semantic checks with immutable source SHA.
- [ ] Independent backend and frontend test/build using disposable SQLite.
- [ ] Confirm release data directory, backup/restore and migration policies.
- [ ] Read-only effective host API/worker units, Caddy and UDA registry checks.
- [ ] Authenticate all API endpoints; verify real process and health semantics.
- [ ] Explicit per-capability sign-off for active discovery/router polling and
      any database write operation, separately from the V2 source review.

Do not assume that `/api/health` alone proves the collection worker, data
schema or upstream router are healthy.
