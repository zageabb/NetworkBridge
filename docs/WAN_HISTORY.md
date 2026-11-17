# WAN history increment

Phase 2 worker opt-in:
- `NETWORKBRIDGE_ROUTER_POLLING_ENABLED=false` by default.
- `NETWORKBRIDGE_DATABASE_URL=sqlite:////var/lib/networkbridge/history.db`
- `NETWORKBRIDGE_ROUTER_URL=https://192.168.1.254`

The worker collects only aggregate WAN counters via the read-only endpoint and writes timestamps, counters, link status, and calculated throughput to SQLite.

If the router certificate is not trusted by the host, save the verified router
certificate outside the repository and set `NETWORKBRIDGE_ROUTER_TLS_CERTIFICATE`
to its absolute path before enabling polling. NetworkBridge trusts that exact
certificate as the TLS anchor while retaining certificate expiry and hostname/IP
checks. Confirm its SHA-256 fingerprint out of band before installation. Replace
the pin deliberately when the router certificate changes. Never disable TLS
verification to work around a certificate failure.

The WAN XML parser supports both the synthetic attribute form used by older
fixtures and the BT Hub's node/value form. For the live list response it reads
only the counter group selected by `wan_active_idx`; it parses the encoded
counter text as data and never evaluates router-supplied JavaScript.

This increment does not parse client inventory, serve history via the web API, or create a real-time dashboard. It has no access to per-device bandwidth.
