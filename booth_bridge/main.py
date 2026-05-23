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
from typing import Awaitable, Callable

from booth_bridge.api_client import ApiClient
from booth_bridge.gate_opener import GateOpener
from booth_bridge.serial_manager import SerialManager
from booth_bridge.omnikey_poller import OmnikeyPoller
from booth_bridge.websocket_server import WebSocketServer

logger = logging.getLogger("booth_bridge")


async def _supervise(
    name: str,
    coro_factory: Callable[[], Awaitable[None]],
    *,
    initial_backoff_s: float = 1.0,
    max_backoff_s: float = 30.0,
) -> None:
    """Restart `coro_factory()` whenever it raises. Honors cancellation.

    Each subtask (Omnikey poller loop, WS server lifetime, etc.) lives inside
    its own supervisor so one component's crash never kills the whole booth
    bridge process. Backoff caps at `max_backoff_s` and resets after a clean
    run >= 60s (subtask was healthy long enough to count as recovered).
    """
    backoff = initial_backoff_s
    while True:
        started = asyncio.get_event_loop().time()
        try:
            await coro_factory()
            logger.warning("supervised_task_returned", extra={"task": name})
        except asyncio.CancelledError:
            raise
        except Exception as e:
            ran_for = asyncio.get_event_loop().time() - started
            logger.exception(
                "supervised_task_crashed",
                extra={"task": name, "ran_for_s": round(ran_for, 2), "error": str(e)},
            )
            if ran_for >= 60.0:
                backoff = initial_backoff_s
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff_s)


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

    async def _hardware_status_heartbeat() -> None:
        while True:
            payload = {
                "type": "hardware_status",
                "rfid": {"connected": bool(rfid_poller and rfid_poller.connected)},
                "palang": {"connected": bool(gate_opener and gate_opener.is_present())},
            }
            try:
                await ws_server.broadcast(payload)
            except Exception as e:
                logger.warning("hardware_status_broadcast_failed", extra={"error": str(e)})
            await asyncio.sleep(5)

    heartbeat_task = asyncio.create_task(_hardware_status_heartbeat(), name="hw_status_heartbeat")

    # Supervisor loops: if the Omnikey poller's underlying task dies (USB
    # replug, driver error, partial frame parse blow-up), restart it without
    # taking down the booth process. WS server already manages clients with
    # try/except inside its handler; we still watch its serving task to be
    # safe.
    supervisors: list[asyncio.Task] = []

    if rfid_poller is not None:
        async def _omnikey_factory():
            # If poller task is dead, start fresh; else wait on existing.
            if rfid_poller._task is None or rfid_poller._task.done():
                rfid_poller.start()
            assert rfid_poller._task is not None
            await rfid_poller._task

        supervisors.append(
            asyncio.create_task(_supervise("omnikey_poller", _omnikey_factory))
        )

    try:
        await asyncio.Event().wait()
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except (asyncio.CancelledError, Exception):
            pass
        for sup in supervisors:
            sup.cancel()
        if supervisors:
            await asyncio.gather(*supervisors, return_exceptions=True)
        if rfid_poller is not None:
            await rfid_poller.stop()
        await ws_server.stop()
        await serial_manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
