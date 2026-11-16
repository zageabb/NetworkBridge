# WAN history increment

Phase 2 worker opt-in:
- `NETWORKBRIDGE_ROUTER_POLLING_ENABLED=false` by default.
- `NETWORKBRIDGE_DATABASE_URL=sqlite:////var/lib/networkbridge/history.db`
- `NETWORKBRIDGE_ROUTER_URL=https://192.168.1.254`

The worker collects only aggregate WAN counters via the read-only endpoint and writes timestamps, counters, link status, and calculated throughput to SQLite.

**Do not enable on the actual router yet** if its certificate is not trusted by the host: TLS pinning / custom CA verification and real response schema validation are still outstanding. Never disable TLS verification to work around this.

This increment does not parse client inventory, serve history via the web API, or create a real-time dashboard. It has no access to per-device bandwidth.
