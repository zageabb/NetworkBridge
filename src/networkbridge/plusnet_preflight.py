"""Offline readiness assessment for experimental Plusnet Hub Two collection."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit


def readiness(enabled: bool, router_url: str, password: str | None,
              certificate: Path | None) -> dict[str, object]:
    """Inspect configuration only. Never contact the router or expose secrets."""
    issues: list[str] = []
    if not enabled:
        issues.append("inventory_disabled")
    try:
        parts = urlsplit(router_url)
        if (parts.scheme != "https" or not parts.hostname or parts.username
                or parts.password or parts.query or parts.fragment
                or parts.path not in ("", "/")):
            issues.append("invalid_router_https_origin")
    except ValueError:
        issues.append("invalid_router_https_origin")
    if password is None or not password:
        issues.append("password_not_configured")
    elif any(ord(char) < 32 or ord(char) > 126 for char in password):
        issues.append("password_encoding_unverified")
    if certificate is not None and not certificate.is_file():
        issues.append("tls_certificate_not_found")
    return {
        "state": "ready_for_manual_hardware_test" if not issues else "configuration_incomplete",
        "issues": issues,
        "network_contacted": False,
        "authentication_attempted": False,
        "hardware_authentication_verified": False,
    }
