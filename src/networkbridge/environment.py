"""Minimal read-only runtime inventory; excludes identities, addresses and environment variables."""

import platform
import sys
from pathlib import Path


def environment_report(os_release: Path = Path("/etc/os-release")) -> dict[str, str]:
    release = "Unavailable"
    try:
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                release = line.partition("=")[2].strip().strip('"')[:120]
                break
    except OSError:
        pass
    return {
        "operating_system": release,
        "kernel": platform.release()[:120],
        "architecture": platform.machine()[:60],
        "python_version": ".".join(str(n) for n in sys.version_info[:3]),
        "monitoring_mode": "read-only",
    }
