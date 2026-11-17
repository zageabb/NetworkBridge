"""Bounded opt-in LAN TCP discovery. No external targets or privileged raw sockets."""

from __future__ import annotations

import asyncio
import ipaddress
import time

PORTS = (22, 80, 443, 445)
RFC1918 = tuple(ipaddress.ip_network(cidr) for cidr in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
_last_run = 0.0
_lock = asyncio.Lock()


def targets(cidr: str) -> list[str]:
    network = ipaddress.ip_network(cidr, strict=True)
    if (network.version != 4 or not any(network.subnet_of(block) for block in RFC1918) or
            network.num_addresses > 256 or network.prefixlen < 24):
        raise ValueError("Only RFC1918 IPv4 networks of /24 or smaller are allowed")
    return [str(ip) for ip in network.hosts()]


async def probe(address: str, timeout: float = 0.25) -> bool:
    for port in PORTS:
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(address, port), timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, TimeoutError):
            continue
    return False


async def scan(cidr: str) -> dict[str, object]:
    """At most one scan per minute per process, with 16 concurrent hosts."""
    global _last_run
    hosts = targets(cidr)
    async with _lock:
        now = time.monotonic()
        if now - _last_run < 60:
            raise RuntimeError("Discovery cooldown active")
        _last_run = now
        semaphore = asyncio.Semaphore(16)

        async def check(host: str) -> dict[str, str] | None:
            async with semaphore:
                if await probe(host):
                    return {"address": host, "state": "tcp_reachable", "source": "tcp_probe"}
                return None

        found = await asyncio.gather(*(check(host) for host in hosts))
    devices = [device for device in found if device is not None]
    return {"devices": devices, "probed_hosts": len(hosts), "open_ports_tested": list(PORTS),
            "note": "Closed/filtered ports do not prove a host is offline"}
