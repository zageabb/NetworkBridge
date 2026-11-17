"""Read-only preflight for future opt-in device monitoring."""

from __future__ import annotations

import ipaddress


def validate_targets(raw: str) -> list[str]:
    """Allow only unique RFC1918 IPv4 addresses, capped at 32."""
    if not raw.strip():
        return []
    entries = [item.strip() for item in raw.split(",")]
    if len(entries) > 32 or any(not item for item in entries):
        raise ValueError("Monitoring requires 1..32 non-empty targets")
    blocks = tuple(ipaddress.ip_network(cidr) for cidr in (
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
    result = []
    for item in entries:
        try:
            address = ipaddress.ip_address(item)
        except ValueError:
            raise ValueError("Targets must be literal RFC1918 IPv4 addresses") from None
        if address.version != 4 or not any(address in block for block in blocks):
            raise ValueError("Targets must be RFC1918 IPv4 addresses")
        if str(address) in result:
            raise ValueError("Duplicate monitoring target")
        result.append(str(address))
    return result


def monitoring_preflight(enabled: bool, raw_targets: str, interval_seconds: int,
                         failure_threshold: int) -> dict[str, object]:
    """Describe configuration without probing, scheduling or alerting."""
    if not 30 <= interval_seconds <= 3600:
        raise ValueError("interval_seconds must be 30..3600")
    if not 2 <= failure_threshold <= 10:
        raise ValueError("failure_threshold must be 2..10")
    try:
        targets = validate_targets(raw_targets)
        error = None
    except ValueError as exc:
        targets = []
        error = str(exc)
    return {
        "state": "disabled" if not enabled else (
            "invalid_configuration" if error or not targets else "ready_not_running"),
        "enabled": enabled,
        "target_count": len(targets),
        "interval_seconds": interval_seconds,
        "failure_threshold": failure_threshold,
        "configuration_error": error if enabled else None,
        "probes_running": False,
        "alerts_enabled": False,
        "note": "Preflight only: no automatic probes, offline verdicts or alerts.",
    }
