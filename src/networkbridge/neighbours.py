"""Passive IPv4 neighbour discovery from the Linux ARP cache; no network probes."""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path

MAC = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")


def parse_arp(content: str, limit: int = 500) -> list[dict[str, str]]:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be 1..500")
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in content.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        address, _, flags, mac, _, interface = parts[:6]
        try:
            ip = ipaddress.ip_address(address)
            valid = int(flags, 16) & 0x2
        except ValueError:
            continue
        if (ip.version != 4 or not ip.is_private or not valid or
                not MAC.fullmatch(mac) or mac == "00:00:00:00:00:00" or
                address in seen):
            continue
        seen.add(address)
        results.append({"name": "Unknown device", "address": address,
                        "mac": mac.lower(), "interface": interface,
                        "source": "linux_arp_cache", "state": "recently_observed"})
        if len(results) >= limit:
            break
    return results


def neighbours(path: Path = Path("/proc/net/arp"), limit: int = 250) -> list[dict[str, str]]:
    return parse_arp(path.read_text(encoding="ascii"), limit)
