"""Independent read-only WAN polling worker (opt-in)."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from networkbridge.config import settings
from networkbridge.router import SmartHubCollector, poll_wan
from networkbridge.storage import add_wan_sample, connect

logger = logging.getLogger(__name__)


def database_path(url: str) -> Path:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError("Phase 2 worker requires a sqlite:/// database URL")
    return Path(url[len(prefix):])


async def run() -> None:
    if not settings.router_polling_enabled:
        logger.info("Router polling disabled; set NETWORKBRIDGE_ROUTER_POLLING_ENABLED=true")
        while True:
            await asyncio.sleep(60)

    path = database_path(settings.database_url)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = connect(path)
    collector = SmartHubCollector(settings.router_url)

    async def save(sample: dict, rate: tuple[float, float] | None) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        add_wan_sample(db, timestamp, sample, rate)

    try:
        logger.info("WAN collector enabled (read-only)")
        await poll_wan(collector, save)
    finally:
        await collector.close()
        db.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
