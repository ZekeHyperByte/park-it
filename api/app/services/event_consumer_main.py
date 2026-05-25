"""Standalone entrypoint for the Redis Pub/Sub event consumer.

Runs as its own systemd service (parking-events.service) — NOT inside the API
process. The API runs with multiple gunicorn workers; if the consumer started in
each worker's lifespan, every pub/sub event would be handled once per worker
(create_entry_transaction, process_emoney_result, ...), producing duplicate
transactions and deducts. A single dedicated process guarantees exactly-once
server-side handling.

Usage:
    python -m api.app.services.event_consumer_main
"""

import asyncio
import signal

from api.app.services.event_consumer import event_consumer
from shared.logging import get_logger

logger = get_logger("event_consumer_main")


async def _run() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    await event_consumer.start()
    logger.info("event_consumer_service_ready")
    try:
        await stop.wait()
    finally:
        await event_consumer.stop()
        logger.info("event_consumer_service_stopped")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
