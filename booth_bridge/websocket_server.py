"""WebSocket server for POS frontend to access serial devices."""

import asyncio
import json
import urllib.request

import websockets

from shared.logging import get_logger

logger = get_logger("booth_ws")


class WebSocketServer:
    """WebSocket server exposing serial peripherals to POS frontend.

    Bound to ``localhost`` only — never expose this on a routable address;
    the protocol owns the booth's relays and printers without per-message
    auth. Connection count is capped at ``max_clients`` so a runaway browser
    tab or leaked Chrome session can't exhaust file descriptors and lock
    out the real POS UI.
    """

    def __init__(
        self,
        serial_manager,
        port: int = 5678,
        api_config: dict | None = None,
        gate_opener=None,
        max_clients: int = 8,
    ) -> None:
        self.serial_manager = serial_manager
        self.port = port
        self._api_config = api_config
        self.gate_opener = gate_opener
        self.max_clients = max_clients
        self._server = None
        self._clients: set = set()
        self._bg_tasks: set = set()

    def _spawn(self, coro, name: str) -> None:
        """Fire a background task with a strong ref + exception logging.

        Bare ``asyncio.create_task`` here gets garbage-collected mid-flight and
        swallows exceptions. Keep a ref until done and log any failure."""
        task = asyncio.create_task(coro, name=name)
        self._bg_tasks.add(task)

        def _on_done(t: asyncio.Task) -> None:
            self._bg_tasks.discard(t)
            if not t.cancelled() and t.exception() is not None:
                logger.error("bg_task_error", task=name, error=str(t.exception()))

        task.add_done_callback(_on_done)

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
        """Call the API booth-result endpoint via urllib (stdlib, no extra deps)."""
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

        try:
            status = await asyncio.to_thread(_post)
            if status == 200:
                logger.info("booth_api_call_success", status=payload["status"])
            else:
                logger.error("booth_api_call_failed", status=status)
        except Exception as e:
            logger.error("booth_api_call_exception", error=str(e))

    async def _handle_client(self, websocket, path=None):
        """Handle a client connection."""
        if len(self._clients) >= self.max_clients:
            # 1013 (Try Again Later) communicates capacity exhaustion more
            # precisely than a generic 1011. The POS frontend's reconnect
            # backoff treats either as recoverable.
            logger.warning(
                "ws_client_rejected_max_clients",
                current=len(self._clients),
                cap=self.max_clients,
                client=getattr(websocket, "remote_address", None),
            )
            try:
                await websocket.close(code=1013, reason="booth_bridge max_clients reached")
            except Exception:
                pass
            return

        self._clients.add(websocket)
        logger.info(
            "client_connected",
            client=websocket.remote_address,
            total=len(self._clients),
        )

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
            logger.info(
                "client_disconnected",
                client=websocket.remote_address,
                total=len(self._clients),
            )

    async def _process_message(self, message: str) -> dict:
        """Process a command from the POS frontend."""
        cmd = json.loads(message)
        action = cmd.get("action")
        peripheral = cmd.get("peripheral")

        if action == "open_gate":
            # Bridge owns the hardware path. Frontend may only request "open this
            # booth's gate" — device path, baudrate and open/close hex live in
            # gate.hardware_config (DB) + booth.json, never on the wire from POS.
            # This closes the prior trust hole where any local WS client could
            # drive arbitrary serial ports with arbitrary bytes.
            if self.gate_opener is None:
                logger.warning("open_gate_no_opener_configured")
                return {
                    "status": False,
                    "error": "gate_opener not configured for this booth",
                }
            requested = cmd.get("gate_code")
            if requested and requested != self.gate_opener.gate_id:
                logger.warning(
                    "open_gate_code_mismatch",
                    requested=requested,
                    bound=self.gate_opener.gate_id,
                )
                return {
                    "status": False,
                    "error": f"gate {requested} not bound to this booth",
                }
            opened = await self.gate_opener.open()
            return {
                "status": opened,
                "message": "Gate opened" if opened else "Gate open failed",
            }

        elif action == "emoney_check_balance":
            # Forward to e-money reader. The PASSTI transaction takes
            # multi-second wall time; run it on a thread so heartbeat,
            # other WS clients, and supervisor tasks keep advancing.
            from protocols.passti.commands import cmd_check_balance
            frame = cmd_check_balance(timeout_sec=10)
            response = await asyncio.to_thread(
                self.serial_manager.send, "emoney_reader", frame
            )
            return {"status": True, "data": response.hex()}

        elif action == "emoney_deduct":
            amount = cmd.get("amount", 0)
            gate_id = cmd.get("gate_id", "")
            gate_out_id = cmd.get("gate_out_id", 0)

            from protocols.passti.commands import cmd_deduct, parse_deduct_response
            from protocols.passti.frame import parse_response

            frame = cmd_deduct(amount, timeout_sec=30)
            raw_response = await asyncio.to_thread(
                self.serial_manager.send, "emoney_reader", frame
            )

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
                self._spawn(self._call_api_booth_result(result_payload), name="api_booth_result")

            # Auto-open relay on SUCCESS only; broadcast result to all POS clients
            if deduct_status == "SUCCESS" and self.gate_opener is not None:
                self._spawn(self.gate_opener.open(), name="gate_opener_open")

            broadcast_event = (
                "emoney_payment_completed" if deduct_status == "SUCCESS"
                else "emoney_payment_failed"
            )
            self._spawn(
                self.broadcast(
                    {
                        "event": broadcast_event,
                        "status": deduct_status,
                        "card_number": result_payload.get("card_number"),
                        "deduct_amount": result_payload.get("deduct_amount"),
                        "balance_after": result_payload.get("balance_after"),
                        "gate_id": gate_id,
                    }
                ),
                name="emoney_broadcast",
            )

            return result_payload

        elif action == "print_receipt":
            # Receipt printers (ESC/POS) don't ACK — use write_only so we
            # don't burn the 1s read timeout on every receipt. Still runs in
            # a worker thread because pyserial's write can briefly block on
            # USB-CDC flush.
            data = cmd.get("data", b"")
            if isinstance(data, str):
                data = data.encode()
            await asyncio.to_thread(
                self.serial_manager.write_only, "receipt_printer", data
            )
            return {"status": True, "message": "Printed"}

        elif action == "running_text":
            text = cmd.get("text", "")
            # Format and send to running text display
            return {"status": True, "message": "Display updated"}

        return {"status": False, "error": f"Unknown action: {action}"}
