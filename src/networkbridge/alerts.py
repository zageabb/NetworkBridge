"""Read-only threshold evaluation of a single host snapshot."""

from __future__ import annotations


def evaluate(snapshot: dict, memory_threshold: float = 85, disk_threshold: float = 90) -> list[dict]:
    """Return active resource warnings; no persistence or notifications."""
    alerts = []
    for metric, used, total, threshold in (
        ("memory", snapshot["memory"]["used_bytes"], snapshot["memory"]["total_bytes"], memory_threshold),
        ("disk", snapshot["disk"]["total_bytes"] - snapshot["disk"]["available_bytes"],
         snapshot["disk"]["total_bytes"], disk_threshold),
    ):
        if not 0 < threshold <= 100:
            raise ValueError("Threshold must be between 0 and 100")
        if total <= 0:
            continue
        percent = round(max(0, min(100, used / total * 100)), 1)
        if percent >= threshold:
            alerts.append({"metric": metric, "percent": percent, "threshold": threshold,
                           "severity": "warning"})
    return alerts
