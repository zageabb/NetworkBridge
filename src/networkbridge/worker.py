"""Independent monitoring worker; real collectors are introduced in Phase 2."""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run() -> None:
    logger.info("NetworkBridge worker started (phase 1; no router polling)")
    while True:
        await asyncio.sleep(60)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
