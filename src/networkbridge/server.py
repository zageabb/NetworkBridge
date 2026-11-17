"""Read-only local Linux host metrics without subprocesses or network access."""

from __future__ import annotations

import os
import time
from pathlib import Path


def _cpu_times(proc_root: Path) -> tuple[int, int]:
    line = (proc_root / "stat").read_text(encoding="ascii").splitlines()[0].split()
    if line[0] != "cpu" or len(line) < 5:
        raise ValueError("Unexpected CPU stat format")
    values = [int(v) for v in line[1:]]
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return sum(values), idle


def _memory(proc_root: Path) -> dict[str, int]:
    fields = {}
    for line in (proc_root / "meminfo").read_text(encoding="ascii").splitlines():
        key, _, value = line.partition(":")
        if key in {"MemTotal", "MemAvailable"}:
            fields[key] = int(value.strip().split()[0]) * 1024
    total, available = fields["MemTotal"], fields["MemAvailable"]
    return {"total_bytes": total, "used_bytes": max(0, total - available)}


def snapshot(proc_root: Path = Path("/proc"), disk_path: Path = Path("/")) -> dict:
    """Collect a safe, aggregate snapshot; no hostname, processes or user details."""
    total, idle = _cpu_times(proc_root)
    uptime = float((proc_root / "uptime").read_text(encoding="ascii").split()[0])
    disk = os.statvfs(disk_path)
    disk_total = disk.f_blocks * disk.f_frsize
    disk_free = disk.f_bavail * disk.f_frsize
    return {
        "sampled_at_unix": int(time.time()),
        "uptime_seconds": uptime,
        "cpu": {"total_ticks": total, "idle_ticks": idle},
        "memory": _memory(proc_root),
        "disk": {"total_bytes": disk_total, "available_bytes": disk_free},
    }
