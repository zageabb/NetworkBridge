"""Join positive TCP observations with current ARP evidence, without guessing identity."""

from __future__ import annotations

import ipaddress
from typing import Any


def correlate(
    observed: list[dict[str, Any]], neighbours: list[dict[str, str]],
    limit: int = 250,
) -> list[dict[str, Any]]:
    """IP is a temporary join key, not a permanent device identity."""
    if not 1 <= limit <= 500:
        raise ValueError("limit must be 1..500")
    by_ip = {entry["address"]: entry for entry in neighbours}
    results: dict[str, dict[str, Any]] = {}
    for row in observed:
        ip = row["address"]
        arp = by_ip.get(ip)
        results[ip] = {
            "address": ip, "mac": arp["mac"] if arp else None,
            "interface": arp["interface"] if arp else None,
            "last_positive_tcp": row["last_seen"],
            "positive_scans": row["positive_scans"],
            "evidence": ["tcp_probe", "linux_arp_cache"] if arp else ["tcp_probe"],
            "status": "recently_observed" if arp else "historical_positive",
        }
    for ip, arp in by_ip.items():
        if ip not in results:
            results[ip] = {
                "address": ip, "mac": arp["mac"], "interface": arp["interface"],
                "last_positive_tcp": None, "positive_scans": 0,
                "evidence": ["linux_arp_cache"], "status": "recently_observed",
            }
    return sorted(results.values(), key=lambda d: ipaddress.ip_address(d["address"]))[:limit]
