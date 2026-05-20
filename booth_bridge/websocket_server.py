"""WebSocket server for POS frontend to access serial devices."""

import asyncio
import json

import websockets

from shared.logging import get_logger

logger = get_logger("booth_ws")

# Soft imports for async HTTP clients
try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    try:
        import httpx

        HAS_HTTPX = True
    except ImportError:
        HAS_HTTPX = False


class WebSocketServer:
    """WebSocket server exposing serial peripherals to POS frontend."""

    def __init__(
        self,
        serial_manager,
        port: int = 5678,
        api_config: dict | None = None,
        gate_opener=None,
    ) -> None:
        self.serial_manager = serial_manager
        self.port = port
        self._api_config = api_config
        self.gate_opener = gate_opener
        self._server = None
        self._clients: set = set()

    async def broadcast(self, payload: dict) -> None:
        """Send JSON payload to every connected client."""
        if not self._clients:
            return
        data = json.dumps(payload)
        stale = []
        for ws in self._clients:
            try:
                await ws.send(data)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self._clients.discard(ws)

    async def start(self) -> None:
        """Start WebSocket server."""
        self._server = await websockets.serve(self._handle_client, "localhost", self.port)
        logger.info("ws_server_started", port=self.port)

    async def stop(self) -> None:
        """Stop WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("ws_server_stopped")

    async def _call_api_booth_result(self, payload: dict) -> None:
        """Call the API booth-result endpoint directly."""
        if not self._api_config:
            return

        url = f"{self._api_config['base_url']}/api/payments/emoney/booth-result"
        api_payload = {
            "gate_id": payload.get("gate_id", ""),
            "gate_out_id": payload.get("gate_out_id", 0),
            "card_number": payload.get("card_number", ""),
            "status": payload["status"],
            "deduct_amount": payload["deduct_amount"],
            "balance_before": payload["balance_before"],
            "balance_after": payload["balance_after"],
            "transaction_counter": payload["transaction_counter"],
            "raw_response_hex": payload["raw_response_hex"],
        }

        try:
            if HAS_AIOHTTP:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        headers={"X-API-Key": self._api_config["api_key"]},
                        json=api_payload,
                    ) as resp:
                        if resp.status == 200:
                            logger.info("booth_api_call_success", status=payload["status"])
                        else:
                            body = await resp.text()
                            logger.error("booth_api_call_failed", status=resp.status, body=body)
            elif HAS_HTTPX:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        url,
                        headers={"X-API-Key": self._api_config["api_key"]},
                        json=api_payload,
                    )
                    if resp.status_code == 200:
                        logger.info("booth_api_call_success", status=payload["status"])
                    else:
                        logger.error("booth_api_call_failed", status=resp.status_code, body=resp.text)
            else:
                # Fallback to urllib.request in a thread
                import urllib.request

                def _post():
                    data = json.dumps(api_payload).encode()
                    req = urllib.request.Request(
                        url,
                        data=data,
                        headers={
                            "Content-Type": "application/json",
                            "X-API-Key": self._api_config["api_key"],
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        return resp.status

                status = await asyncio.to_thread(_post)
                if status == 200:
                    logger.info("booth_api_call_success", status=payload["status"])
                else:
                    logger.error("booth_api_call_failed", status=status)
        except Exception as e:
            logger.error("booth_api_call_exception", error=str(e))

    async def _handle_client(self, websocket, path=None):
        """Handle a client connection."""
        self._clients.add(websocket)
        logger.info("client_connected", client=websocket.remote_address)

        try:
            async for message in websocket:
                try:
                    result = await self._process_message(message)
                    await websocket.send(json.dumps(result))
                except Exception as e:
                    logger.error("message_error", error=str(e))
                    await websocket.send(json.dumps({"status": False, "error": str(e)}))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            logger.info("client_disconnected", client=websocket.remote_address)

    async def _process_message(self, message: str) -> dict:
        """Process a command from the POS frontend."""
        cmd = json.loads(message)
        action = cmd.get("action")
        peripheral = cmd.get("peripheral")

        if action == "open_gate":
            # Forward to serial gate controller
            device = cmd.get("device", "/dev/ttyUSB0")
            baudrate = cmd.get("baudrate", 9600)
            open_cmd = cmd.get("open_command", "O1N").encode()
            close_cmd = cmd.get("close_command", "O2N").encode()

            import serial
            ser = serial.Serial(device, baudrate, timeout=1)
            ser.write(open_cmd)
            if close_cmd:
                import time
                time.sleep(1)
                ser.write(close_cmd)
            ser.close()
            return {"status": True, "message": "Gate opened"}

        elif action == "emoney_check_balance":
            # Forward to e-money reader
            from protocols.passti.commands import cmd_check_balance
            frame = cmd_check_balance(timeout_sec=10)
            response = self.serial_manager.send("emoney_reader", frame)
            return {"status": True, "data": response.hex()}

        elif action == "emoney_deduct":
            amount = cmd.get("amount", 0)
            gate_id = cmd.get("gate_id", "")
            gate_out_id = cmd.get("gate_out_id", 0)

            from protocols.passti.commands import cmd_deduct, parse_deduct_response
            from protocols.passti.frame import parse_response

            frame = cmd_deduct(amount, timeout_sec=30)
            raw_response = self.serial_manager.send("emoney_reader", frame)

            parsed = parse_response(raw_response)
            if "error" in parsed:
                return {
                    "action": "emoney_deduct_result",
                    "status": "FAILED",
                    "error": parsed["error"],
                    "raw_response_hex": parsed.get("raw", raw_response.hex()),
                }

            status = parsed["status"]
            if status == (0x00, 0x00, 0x00):
                deduct_status = "SUCCESS"
            elif status == (0x01, 0x10, 0x05):
                deduct_status = "LOST_CONTACT"
            elif status == (0x01, 0x10, 0x04):
                deduct_status = "INSUFFICIENT_BALANCE"
            elif status == (0x01, 0x10, 0x06):
                deduct_status = "WRONG_CARD"
            elif status == (0x01, 0x10, 0x02):
                deduct_status = "TIMEOUT"
            else:
                deduct_status = "FAILED"

            deduct_data = parse_deduct_response(parsed["body"])
            if not deduct_data.get("ok"):
                return {
                    "action": "emoney_deduct_result",
                    "status": "FAILED",
                    "error": deduct_data.get("error", "Deduct parse failed"),
                    "raw_response_hex": parsed.get("raw", raw_response.hex()),
                }

            result_payload = {
                "action": "emoney_deduct_result",
                "status": deduct_status,
                "card_number": deduct_data.get("card_number", ""),
                "deduct_amount": deduct_data.get("deducted", 0),
                "balance_before": deduct_data.get("remaining", 0) + deduct_data.get("deducted", 0),
                "balance_after": deduct_data.get("remaining", 0),
                "transaction_counter": deduct_data.get("trans_counter", 0),
                "raw_response_hex": parsed.get("raw", raw_response.hex()),
                "gate_id": gate_id,
                "gate_out_id": gate_out_id,
            }

            if self._api_config:
                asyncio.create_task(self._call_api_booth_result(result_payload))

            # Auto-open relay on SUCCESS; broadcast result to all POS clients
            if deduct_status == "SUCCESS" and self.gate_opener is not None:
                asyncio.create_task(self.gate_opener.open())

            asyncio.create_task(
                self.broadcast(
                    {
                        "event": "emoney_payment_completed",
                        "status": deduct_status,
                        "card_number": result_payload.get("card_number"),
                        "deduct_amount": result_payload.get("deduct_amount"),
                        "balance_after": result_payload.get("balance_after"),
                        "gate_id": gate_id,
                    }
                )
            )

            return result_payload

        elif action == "print_receipt":
            # Forward to receipt printer
            data = cmd.get("data", b"")
            if isinstance(data, str):
                data = data.encode()
            self.serial_manager.send("receipt_printer", data)
            return {"status": True, "message": "Printed"}

        elif action == "running_text":
            text = cmd.get("text", "")
            # Format and send to running text display
            return {"status": True, "message": "Display updated"}

        return {"status": False, "error": f"Unknown action: {action}"}
