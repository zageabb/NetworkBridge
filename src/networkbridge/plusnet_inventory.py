"""Parse Plusnet Hub Two known_device_list without executing JavaScript.

The router's inventory is a device/interface observation, not a DHCP lease
expiry record or a definitive online/offline status.
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import unquote

MAX_PAYLOAD = 1_000_000
MAX_DEVICES = 512
_LIST = re.compile(r"\b(?:var\s+)?known_device_list\s*=\s*\[")
_FIELD = re.compile(r"""(?:^|,)\s*(?:([A-Za-z_][\w]*)|"([^"]+)"|'([^']+)')\s*:\s*(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)'|(-?\d+))\s*""")
_MAC = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")


def _objects(raw: str) -> list[str]:
    match = _LIST.search(raw)
    if not match:
        raise ValueError("Missing known_device_list")
    items: list[str] = []
    depth = 0
    start = -1
    quote = ""
    escaped = False
    for char in raw[match.end():]:
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            if depth == 0:
                start = len(items)  # overwritten below by buffer creation
                buffer = []
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                raise ValueError("Invalid device object")
            if depth == 0:
                items.append("".join(buffer))
                if len(items) > MAX_DEVICES:
                    raise ValueError("Too many devices")
        elif char == "]" and depth == 0:
            return items
        if depth > 0 and char != "{" or depth == 0 and char == "}" and start >= 0:
            if depth > 0:
                buffer.append(char)
    raise ValueError("Unterminated device list")


def _fields(obj: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in _FIELD.finditer(obj):
        key = next(value for value in match.groups()[:3] if value is not None)
        value = next((value for value in match.groups()[3:] if value is not None), "")
        fields[key] = unquote(value.replace("\\'", "'").replace('\\"', '"'))
    return fields


def parse_inventory(raw: str) -> list[dict[str, object]]:
    if len(raw) > MAX_PAYLOAD:
        raise ValueError("Inventory response too large")
    records: list[dict[str, object]] = []
    for obj in _objects(raw):
        fields = _fields(obj)
        macs = fields.get("mac", "").split(",")
        ips = fields.get("ip", "").split(",")
        ports = fields.get("port", "").split(",")
        activities = fields.get("activity_ip", "").split(",")
        for index, mac in enumerate(macs):
            mac = mac.strip()
            if not _MAC.fullmatch(mac):
                continue
            ip = ips[index].strip() if len(ips) == len(macs) else ""
            try:
                ip = str(ipaddress.IPv4Address(ip))
            except ipaddress.AddressValueError:
                ip = ""
            port = ports[index].strip() if len(ports) == len(macs) else "NA"
            records.append({
                "mac": mac.lower(), "ip": ip,
                "hostname": fields.get("hostname", ""),
                "name": fields.get("name", ""),
                "port": port,
                "connection": {"wl0": "wifi_5ghz", "wl1": "wifi_2_4ghz",
                               "wired": "ethernet"}.get(port, "unknown"),
                "address_assignment": "static" if fields.get("dhcp_option") == "NA" else "dhcp",
                "router_active": fields.get("activity") == "1",
                "ipv4_active": activities[index] == "1" if len(activities) == len(macs) else None,
                "first_seen": fields.get("time_first_seen") or None,
                "last_active": fields.get("time_last_active") or None,
                "source": "plusnet_hub_two",
            })
    return records
