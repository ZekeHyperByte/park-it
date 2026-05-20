"""Booth Bridge Service — runs on booth PC.

Connects to serial devices (e-money reader, receipt printer, running text),
exposes them via WebSocket for the POS frontend, drives the local serial
relay for boom barrier opens, and runs an autonomous PC/SC reader poll
(Omnikey 5427 CK) for member RFID exits.

Usage:
    python -m booth_bridge.main --config /etc/parking/booth.json
"""

import argparse
import asyncio
import json
import logging

from booth_bridge.api_client import ApiClient
from booth_bridge.gate_opener import GateOpener
from booth_bridge.serial_manager import SerialManager
from booth_bridge.omnikey_poller import OmnikeyPoller
from booth_bridge.websocket_server import WebSocketServer

logger = logging.getLogger("booth_bridge")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/etc/parking/booth.json")
    parser.add_argument("--port", type=int, default=5678)
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(
        "starting_booth_bridge", extra={"port": args.port, "booth": config.get("name")}
    )

    serial_manager = SerialManager(config.get("peripherals", {}))
    await serial_manager.start()

    api_config = None
    api_client = None
    if config.get("api_base_url") and config.get("api_key"):
        api_config = {"base_url": config["api_base_url"], "api_key": config["api_key"]}
        api_client = ApiClient(api_config["base_url"], api_config["api_key"])

    gate_opener = None
    rfid_poller = None
    gate_code = config.get("default_gate_code")
    ws_server_ref: list = [None]

    if api_client and gate_code:
        gate_data = await api_client.fetch_gate(gate_code)
        if gate_data:
            gate_opener = GateOpener(gate_data)
            logger.info("gate_opener_ready", extra={"gate": gate_code})

            hw = gate_data.get("hardware_config") or {}
            omnikey_cfg = hw.get("omnikey_reader") or {}
            if omnikey_cfg.get("enabled"):
                async def _broadcast(payload):
                    if ws_server_ref[0] is not None:
                        await ws_server_ref[0].broadcast(payload)

                rfid_poller = OmnikeyPoller(
                    gate_id=gate_data.get("code", ""),
                    gate_db_id=gate_data.get("id", 0),
                    api_client=api_client,
                    gate_opener=gate_opener,
                    broadcast=_broadcast,
                    device_path=omnikey_cfg.get("device_path"),
                    device_name_match=omnikey_cfg.get("device_name_match", "omnikey"),
                )

    ws_server = WebSocketServer(
        serial_manager, port=args.port, api_config=api_config, gate_opener=gate_opener
    )
    ws_server_ref[0] = ws_server
    await ws_server.start()

    if rfid_poller is not None:
        rfid_poller.start()
        logger.info("rfid_poller_started")

    try:
        await asyncio.Event().wait()
    finally:
        if rfid_poller is not None:
            await rfid_poller.stop()
        await ws_server.stop()
        await serial_manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
