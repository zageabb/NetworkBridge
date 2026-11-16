# BT Smart Hub integration specification

Target gateway: 192.168.1.254; identified as BT Home Hub 6 / Smart Hub family, exact firmware unverified.

Assessment: LAN-side, read-only, unauthenticated. Initialize a session using GET / to receive a urn cookie, retain it in a cookie jar, and send Referer: https://192.168.1.254/ on subsequent requests.

Allow-listed collection endpoints:
- GET /nonAuth/wan_conn.xml: every 5 seconds; WAN status, cumulative counters, sysuptime, DSL negotiated rates, Wi-Fi channels.
- GET /cgi/cgi_home.js: every 30–60 seconds; known device inventory and activity flags.

WAN counters are percent-encoded and use total_bytes;received_bytes;transmitted_bytes, potentially with trailing null items. Decode safely. Throughput in bps = 8 * nonnegative byte delta / monotonic elapsed seconds. On reboot or reset, start a new series. Use jitter, exponential backoff, and no overlapping polls.

The generated JavaScript is not JSON: never execute it; use a purpose-built allow-list parser and reject unexpected syntax. Store only pseudonyms and keyed MAC hashes by default.

The router does not expose per-device throughput, traffic destinations, protocol classification or packet payloads via these endpoints. No credential guessing, write endpoints, or configuration changes. Use synthetic fixtures for tests.

Source: user-supplied router-monitoring-development-brief.md (2026-11-16).
