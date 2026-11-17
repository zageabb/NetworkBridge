"""Read-only loopback TCP reachability probes for configured local services."""

from __future__ import annotations

import socket

# Only fixed loopback endpoints. TCP acceptance is not application health.
SERVICES: tuple[tuple[str, int], ...] = (
    ("Caddy", 80),
    ("PostgreSQL", 5432),
    ("Ollama", 11434),
    ("NetworkBridge", 8765),
)


def check_services(timeout: float = 0.25) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for name, port in SERVICES:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=timeout):
                state = "reachable"
        except OSError:
            state = "unreachable"
        results.append({"name": name, "port": port, "state": state, "probe": "loopback_tcp"})
    return results
