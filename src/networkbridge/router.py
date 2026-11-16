"""Read-only BT Smart Hub WAN collector and rate calculations."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
from urllib.parse import unquote
import xml.etree.ElementTree as ET

import httpx

ALLOWED_PATHS = frozenset({"/", "/nonAuth/wan_conn.xml", "/cgi/cgi_home.js"})


@dataclass(frozen=True)
class Counters:
    total: int
    received: int
    transmitted: int


def parse_counters(raw: str) -> Counters:
    parts = [x for x in unquote(raw).split(";") if x and x.lower() != "null"]
    if len(parts) != 3:
        raise ValueError("Unexpected WAN counter format")
    values = [int(x) for x in parts]
    if any(x < 0 for x in values):
        raise ValueError("Negative WAN counter")
    if values[0] != values[1] + values[2]:
        raise ValueError("Inconsistent WAN counters")
    return Counters(*values)


def rates(previous: Counters, current: Counters, elapsed: float) -> tuple[float, float] | None:
    if (elapsed <= 0 or current.received < previous.received
            or current.transmitted < previous.transmitted):
        return None
    return (8 * (current.received - previous.received) / elapsed,
            8 * (current.transmitted - previous.transmitted) / elapsed)


def parse_wan_xml(payload: str) -> dict[str, object]:
    if len(payload) > 1_000_000:
        raise ValueError("WAN response too large")
    root = ET.fromstring(payload)
    fields = {}
    for node in root.iter():
        for key, value in node.attrib.items():
            if key in {"wan_conn_volume_list", "sysuptime", "link_status", "status_rate"}:
                fields[key] = value
    if "wan_conn_volume_list" not in fields:
        raise ValueError("Missing WAN counters")
    return {"counters": parse_counters(str(fields["wan_conn_volume_list"]).split(",")[0]),
            "uptime": fields.get("sysuptime"), "link_status": fields.get("link_status"),
            "negotiated_rate": fields.get("status_rate")}


class SmartHubCollector:
    def __init__(self, url: str):
        if not url.startswith("https://"):
            raise ValueError("Router must use HTTPS")
        self.url = url.rstrip("/")
        self.client = httpx.AsyncClient(base_url=self.url, timeout=5.0, follow_redirects=False)
        self._initialized = False

    async def get(self, path: str) -> str:
        if path not in ALLOWED_PATHS:
            raise ValueError("Endpoint not allowed")
        if path != "/" and not self._initialized:
            await self.get("/")
        headers = {"Referer": self.url + "/"} if path != "/" else {}
        response = await self.client.get(path, headers=headers)
        response.raise_for_status()
        if path == "/":
            self._initialized = True
        if len(response.content) > 1_000_000:
            raise ValueError("Response too large")
        return response.text

    async def close(self) -> None:
        await self.client.aclose()


async def poll_wan(collector: SmartHubCollector, callback, interval: float = 5.0) -> None:
    previous = None
    previous_time = None
    previous_uptime = None
    while True:
        started = time.monotonic()
        try:
            sample = parse_wan_xml(await collector.get("/nonAuth/wan_conn.xml"))
            counters = sample["counters"]
            uptime = sample["uptime"]
            rate = rates(previous, counters, started - previous_time) if previous and previous_time else None
            if previous_uptime and uptime and str(uptime).isdigit() and str(previous_uptime).isdigit():
                if int(str(uptime)) < int(str(previous_uptime)):
                    rate = None
            await callback(sample, rate)
            previous, previous_time, previous_uptime = counters, started, uptime
        except (httpx.HTTPError, ValueError, ET.ParseError):
            previous, previous_time, previous_uptime = None, None, None
        await asyncio.sleep(max(0.0, interval - (time.monotonic() - started)))
