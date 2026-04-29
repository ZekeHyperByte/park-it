"""Booth Bridge Service — runs on booth PC.

Connects to serial devices (e-money reader, receipt printer, running text)
and exposes them via WebSocket for the POS frontend.

Usage:
    python -m booth_bridge.main --config /etc/parking/booth.json
"""

import argparse
import asyncio
import json
import logging

from booth_bridge.serial_manager import SerialManager
from booth_bridge.websocket_server import WebSocketServer

logger = logging.getLogger("booth_bridge")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/etc/parking/booth.json")
    parser.add_argument("--port", type=int, default=5678)
    args = parser.parse_args()

    # Load booth configuration
    with open(args.config) as f:
        config = json.load(f)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting booth bridge", extra={"port": args.port, "booth": config.get("name")})

    # Initialize serial connections
    serial_manager = SerialManager(config.get("peripherals", {}))
    await serial_manager.start()

    # Build API config if available
    api_config = None
    if config.get("api_base_url") and config.get("api_key"):
        api_config = {
            "base_url": config["api_base_url"],
            "api_key": config["api_key"],
        }

    # Start WebSocket server
    ws_server = WebSocketServer(serial_manager, port=args.port, api_config=api_config)
    await ws_server.start()

    try:
        await asyncio.Event().wait()  # Run forever
    finally:
        await ws_server.stop()
        await serial_manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
