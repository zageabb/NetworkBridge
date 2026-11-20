"""Run one opt-in Hub Two inventory snapshot; never starts an automatic poller."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sqlite3

from networkbridge.config import settings
from networkbridge.database import database_path, initialize_database
from networkbridge.plusnet_client import PlusnetHubTwoClient
from networkbridge.plusnet_preflight import readiness
from networkbridge.plusnet_storage import save_inventory

logger = logging.getLogger(__name__)


async def collect_once() -> int:
    if not settings.plusnet_inventory_enabled:
        raise RuntimeError("Plusnet inventory collection disabled")
    client = PlusnetHubTwoClient(
        settings.router_url,
        password=settings.plusnet_admin_password,
        tls_certificate=settings.router_tls_certificate,
    )
    try:
        devices = await client.inventory()
    finally:
        await client.close()
    if not devices:
        raise ValueError("Router returned no valid devices; preserving previous snapshot")
    initialize_database(settings.database_url)
    with sqlite3.connect(database_path(settings.database_url), timeout=5) as db:
        return save_inventory(db, devices)


def main() -> None:
    parser = argparse.ArgumentParser(description="Experimental Plusnet inventory snapshot")
    parser.add_argument("--preflight", action="store_true",
                        help="Check configuration without contacting the router")
    args = parser.parse_args()
    if args.preflight:
        result = readiness(
            settings.plusnet_inventory_enabled, settings.router_url,
            settings.plusnet_admin_password, settings.router_tls_certificate,
        )
        print(json.dumps(result, indent=2))
        return
    try:
        count = asyncio.run(collect_once())
    except Exception:
        logger.exception("Plusnet inventory snapshot failed")
        raise SystemExit(1) from None
    print(f"Plusnet inventory snapshot saved: {count} interfaces")


if __name__ == "__main__":
    main()
