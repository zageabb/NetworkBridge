"""Standalone opt-in TCP monitoring worker; no alerts or offline classification."""

from __future__ import annotations

import asyncio
import logging

from networkbridge.config import settings
from networkbridge.discovery import probe
from networkbridge.monitoring import validate_targets

logger = logging.getLogger(__name__)


async def check_once(targets: list[str], timeout: float = 0.25) -> dict[str, bool]:
    """Probe only explicitly configured private hosts, with bounded concurrency."""
    semaphore = asyncio.Semaphore(8)

    async def check(address: str) -> tuple[str, bool]:
        async with semaphore:
            return address, await probe(address, timeout=timeout)

    return dict(await asyncio.gather(*(check(address) for address in targets)))


async def run() -> None:
    """Runs only as a separately launched process with explicit opt-in settings."""
    if not settings.device_monitoring_enabled:
        logger.info("Device monitoring disabled; worker exiting without probes")
        return
    targets = validate_targets(settings.device_monitoring_targets)
    if not targets:
        raise ValueError("Enabled monitoring requires at least one RFC1918 IPv4 target")
    interval = settings.device_monitoring_interval_seconds
    threshold = settings.device_monitoring_failure_threshold
    failures = dict.fromkeys(targets, 0)
    logger.info("Monitoring %d configured targets; no alerts or offline verdicts", len(targets))
    while True:
        results = await check_once(targets)
        for address, reachable in results.items():
            failures[address] = 0 if reachable else min(threshold, failures[address] + 1)
            if reachable:
                logger.info("Positive TCP response from %s", address)
            elif failures[address] >= threshold:
                logger.warning(
                    "No TCP response from %s in %d consecutive checks; "
                    "this does not establish device offline status",
                    address, failures[address],
                )
        await asyncio.sleep(interval)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
