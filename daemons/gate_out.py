"""Gate-out daemon implementing the full exit state machine.

Three concurrent payment methods (RFID, E-Money via booth bridge, Cash) with asyncio.wait FIRST_COMPLETED.
Timeout handling with operator alert and resolution.

NOTE: E-Money is now handled by the booth bridge, not controller passthrough.
The gate daemon still publishes events when PASSTI is used, but the actual
reader is connected to the booth PC, not the gate controller.
"""

from __future__ import annotations

import asyncio
from typing import Any

from protocols.compass.parser import parse_stat
from protocols.compass.protocol import (
    CompassTransport,
    cmd_ds,
    cmd_dsu,
    cmd_mt,
    cmd_stat,
    cmd_trig1,
    cmd_trig2,
)
from protocols.passti.transport import ControllerPassthroughTransport
from shared.events import (
    BaseEvent,
    DeductResultEvent,
    DeductStatus,
    GateOpenedEvent,
    PasstiCardTapEvent,
    RfidCardReadEvent,
    TimeoutAlertEvent,
    VehicleDetectedEvent,
    VehicleLeftEvent,
    VehiclePassedEvent,
)
from shared.logging import get_logger

from daemons.base import BaseDaemon

logger = get_logger(__name__)

# State constants
STATE_IDLE = "IDLE"
STATE_VEHICLE_PRESENT = "VEHICLE_PRESENT"
STATE_WAITING_PAYMENT = "WAITING_PAYMENT"
STATE_TIMEOUT_ALERT = "TIMEOUT_ALERT"
STATE_OPENING = "OPENING"

# Poll interval for controller STAT
STAT_POLL_INTERVAL_MS = 100


class GateOutDaemon(BaseDaemon):
    """Gate-out daemon for vehicle exit processing."""

    def __init__(self, gate_id: str, config: dict[str, Any]) -> None:
        super().__init__(gate_id, config)
        self.controller: CompassTransport | None = None
        self._controller_lock = asyncio.Lock()
        self._poll_task: asyncio.Task | None = None
        self._payment_task: asyncio.Task | None = None
        self._cash_payment_event = asyncio.Event()
        self._debounce_event: asyncio.Event | None = None
        self.passti_transport: ControllerPassthroughTransport | None = None
        self.has_emoney = self.config.get("hardware_config", {}).get("emoney", {}).get("enabled", False)

    # ------------------------------------------------------------------
    # Lifecycle overrides
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start daemon: connect controller, then delegate to base run."""
        await self._connect_controller()
        await super().run()

    async def _on_started(self) -> None:
        """Start controller polling after base sets _running=True."""
        await self._start_polling()

    async def stop(self) -> None:
        """Graceful stop with controller disconnect."""
        await super().stop()
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        if self._payment_task and not self._payment_task.done():
            self._payment_task.cancel()
        await self._disconnect_controller()

    def get_initial_state(self) -> str:
        return STATE_IDLE

    # ------------------------------------------------------------------
    # Controller connection
    # ------------------------------------------------------------------

    async def _connect_controller(self) -> None:
        """Connect to Compass TCP controller."""
        host = self.config.get("controller_host")
        port = self.config.get("controller_port")
        if not host or not port:
            logger.warning("no_controller_config", gate_id=self.gate_id)
            return
        try:
            self.controller = CompassTransport(host, port)
            self.controller.connect(timeout=5.0)
            if self.has_emoney:
                self.passti_transport = ControllerPassthroughTransport(self.controller._sock)
            logger.info("controller_connected", gate_id=self.gate_id, host=host, port=port)
        except Exception as e:
            logger.error("controller_connect_failed", gate_id=self.gate_id, error=str(e))
            self.controller = None

    async def _disconnect_controller(self) -> None:
        """Disconnect from controller."""
        if self.controller:
            self.controller.close()
            self.controller = None
            logger.info("controller_disconnected", gate_id=self.gate_id)

    # ------------------------------------------------------------------
    # Main polling loop
    # ------------------------------------------------------------------

    async def _start_polling(self) -> None:
        """Start the controller polling loop."""
        self._poll_task = asyncio.create_task(self._poll_controller(), name="poll")
        self._tasks.append(self._poll_task)

    async def _poll_controller(self) -> None:
        """Poll controller STAT and handle state transitions."""
        while self._running:
            try:
                if self.controller and self.controller.is_connected():
                    async with self._controller_lock:
                        response = self.controller.send_recv(cmd_stat(), timeout=0.5)
                    await self._handle_stat_response(response or b"")
                await asyncio.sleep(STAT_POLL_INTERVAL_MS / 1000.0)
            except asyncio.CancelledError:
                logger.debug("poll_cancelled", gate_id=self.gate_id)
                raise
            except Exception as e:
                logger.error("poll_error", gate_id=self.gate_id, error=str(e))
                await asyncio.sleep(1)

    # ------------------------------------------------------------------
    # STAT response handler
    # ------------------------------------------------------------------

    async def _handle_stat_response(self, response: bytes) -> None:
        """Process a STAT response based on current state."""
        parsed = parse_stat(response)

        if self.state == STATE_IDLE:
            if parsed["in1"]:
                # Start debounce timer
                if self._debounce_event is None or self._debounce_event.is_set():
                    self._debounce_event = asyncio.Event()
                    asyncio.create_task(self._vehicle_debounce_timer(0.5))

        elif self.state == STATE_VEHICLE_PRESENT:
            # Debounce completed; waiting for snapshot / payment start
            pass

        elif self.state == STATE_WAITING_PAYMENT:
            # Payment tasks handle their own inputs
            pass

        elif self.state == STATE_TIMEOUT_ALERT:
            if not parsed["in1"]:
                # Vehicle left without payment
                await self._on_vehicle_left(reason="abandoned")

        elif self.state == STATE_OPENING:
            # Wait for vehicle to pass
            if parsed["in3"] or not parsed["in1"]:
                await self._on_vehicle_passed()

    # ------------------------------------------------------------------
    # State transition handlers
    # ------------------------------------------------------------------

    async def _vehicle_debounce_timer(self, duration: float) -> None:
        """500ms debounce before confirming vehicle presence."""
        await asyncio.sleep(duration)
        if self.state == STATE_IDLE and self._debounce_event and not self._debounce_event.is_set():
            self._debounce_event.set()
            await self._on_vehicle_detected()

    async def _on_vehicle_detected(self) -> None:
        """Vehicle detected at exit after debounce."""
        await self._transition(STATE_VEHICLE_PRESENT)
        await self.publish_event(
            VehicleDetectedEvent(
                event_type="vehicle_detected",
                gate_id=self.gate_id,
                sensor="IN1",
            )
        )
        # FastAPI will take snapshot and notify POS
        # After a short delay, start payment waiting
        await asyncio.sleep(0.2)
        await self._start_waiting_payment()

    async def _start_waiting_payment(self) -> None:
        """Start the concurrent payment method tasks."""
        await self._transition(STATE_WAITING_PAYMENT)
        self._cash_payment_event.clear()

        timeout_seconds = self.config.get("payment_timeout_seconds", 120)
        logger.info(
            "waiting_payment_started",
            gate_id=self.gate_id,
            timeout=timeout_seconds,
        )

        task_wiegand = asyncio.create_task(self._wait_for_wiegand(), name="wiegand")
        task_pos = asyncio.create_task(self._wait_for_pos_confirm(), name="pos")
        task_timeout = asyncio.create_task(
            self._payment_timeout(timeout_seconds), name="timeout"
        )

        # E-money is now handled by booth bridge; daemon only waits for booth events
        # via Redis commands (e.g., "emoney_payment_confirmed" or "open_gate")
        # We don't poll controller for PASSTI anymore.

        tasks = [task_wiegand, task_pos, task_timeout]
        self._payment_task = asyncio.gather(*tasks, return_exceptions=True)

        try:
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

            # Determine winner
            winner = next(iter(done))
            exc = winner.exception()
            if exc and not isinstance(exc, asyncio.CancelledError):
                logger.error("payment_task_error", gate_id=self.gate_id, error=str(exc))

            winner_name = winner.get_name()
            logger.info("payment_method_resolved", gate_id=self.gate_id, winner=winner_name)

            if winner_name == "wiegand":
                await self._on_rfid_exit()
            elif winner_name == "pos":
                await self._on_cash_exit()
            elif winner_name == "timeout":
                await self._on_payment_timeout()

        except Exception as e:
            logger.error("payment_resolution_error", gate_id=self.gate_id, error=str(e))

    async def _wait_for_wiegand(self) -> None:
        """Poll controller until Wiegand card is read."""
        while self.state == STATE_WAITING_PAYMENT and self._running:
            if self.controller and self.controller.is_connected():
                async with self._controller_lock:
                    response = self.controller.send_recv(cmd_stat(), timeout=0.5)
                parsed = parse_stat(response)
                if parsed["wiegand_w"]:
                    self.state_data["rfid_card"] = parsed["wiegand_w"]
                    self.state_data["rfid_channel"] = "W"
                    return
                if parsed["wiegand_x"]:
                    self.state_data["rfid_card"] = parsed["wiegand_x"]
                    self.state_data["rfid_channel"] = "X"
                    return
            await asyncio.sleep(0.1)

    async def _wait_for_pos_confirm(self) -> None:
        """Wait for cash payment confirmed signal from handle_command."""
        try:
            await asyncio.wait_for(
                self._cash_payment_event.wait(),
                timeout=None,  # Cancelled by parent when another task wins
            )
        except asyncio.TimeoutError:
            pass

    async def _payment_timeout(self, timeout_seconds: float) -> None:
        """Sleep until payment timeout."""
        await asyncio.sleep(timeout_seconds)

    # ------------------------------------------------------------------
    # Payment method resolution
    # ------------------------------------------------------------------

    async def _on_rfid_exit(self) -> None:
        """RFID card was read — publish event and wait for FastAPI open_gate."""
        card_number = self.state_data.get("rfid_card", "")
        channel = self.state_data.get("rfid_channel", "W")
        await self.publish_event(
            RfidCardReadEvent(
                event_type="rfid_card_read",
                gate_id=self.gate_id,
                card_number=card_number,
                channel=channel,
            )
        )
        logger.info("rfid_exit_detected", gate_id=self.gate_id, card=card_number)
        # FastAPI validates member and sends open_gate command

    async def _on_cash_exit(self) -> None:
        """Cash payment confirmed by POS — FastAPI will send open_gate."""
        logger.info("cash_exit_detected", gate_id=self.gate_id)
        # FastAPI has already confirmed payment; open_gate command will follow

    async def _on_payment_timeout(self) -> None:
        """Payment timed out — alert operator."""
        await self._transition(STATE_TIMEOUT_ALERT)
        waiting_seconds = self.config.get("payment_timeout_seconds", 120)
        await self.publish_event(
            TimeoutAlertEvent(
                event_type="timeout_alert",
                gate_id=self.gate_id,
                transaction_id=self.state_data.get("transaction_id"),
                waiting_seconds=waiting_seconds,
            )
        )
        await self._send_controller_command(
            cmd_ds("Mohon Hubungi Petugas", "")
        )
        await self._send_controller_command(cmd_mt("00008"))  # Track 8
        logger.warning("payment_timeout", gate_id=self.gate_id, seconds=waiting_seconds)

    async def _on_vehicle_left(self, reason: str) -> None:
        """Vehicle left without completing payment."""
        await self.publish_event(
            VehicleLeftEvent(
                event_type="vehicle_left",
                gate_id=self.gate_id,
                reason=reason,
            )
        )
        await self._transition(STATE_IDLE)
        await self._send_controller_command(cmd_dsu())
        logger.info("vehicle_left", gate_id=self.gate_id, reason=reason)

    async def _on_vehicle_passed(self) -> None:
        """Vehicle has passed through gate."""
        await self._transition(STATE_IDLE)
        await self.publish_event(
            VehiclePassedEvent(
                event_type="vehicle_passed",
                gate_id=self.gate_id,
            )
        )
        await self._send_controller_command(cmd_dsu())

    async def _on_gate_opened(self) -> None:
        """Gate has opened."""
        await self._transition(STATE_OPENING)
        await self.publish_event(
            GateOpenedEvent(
                event_type="gate_opened",
                gate_id=self.gate_id,
            )
        )
        asyncio.create_task(self._vehicle_pass_timer())

    async def _vehicle_pass_timer(self) -> None:
        """Timer to detect vehicle has passed."""
        await asyncio.sleep(self.config.get("gate_open_timeout_s", 10))
        if self.state == STATE_OPENING:
            await self._on_vehicle_passed()

    # ------------------------------------------------------------------
    # Command handlers (from Redis Streams)
    # ------------------------------------------------------------------

    async def handle_command(self, command_data: dict[str, str]) -> bool:
        """Process a command from FastAPI."""
        command_type = command_data.get("command_type", "")
        logger.info("gate_out_command", gate_id=self.gate_id, command_type=command_type)

        try:
            if command_type == "open_gate":
                duration = command_data.get("duration_seconds")
                dur = int(duration) if duration else None
                await self._cmd_open_gate(dur)

            elif command_type == "close_gate":
                await self._cmd_close_gate()

            elif command_type == "play_audio":
                track = int(command_data.get("track", 1))
                await self._cmd_play_audio(track)

            elif command_type == "display_text":
                line1 = command_data.get("line1", "")
                line2 = command_data.get("line2", "")
                await self._cmd_display_text(line1, line2)

            elif command_type == "buzzer":
                success = command_data.get("success", "true").lower() == "true"
                await self._cmd_buzzer(success)

            elif command_type == "print_receipt":
                await self._cmd_print_receipt(command_data)

            elif command_type == "deduct":
                amount = int(command_data.get("amount", 0))
                expected_card = command_data.get("expected_card_number", "")
                await self._cmd_deduct(amount, expected_card)

            elif command_type == "cash_payment_confirmed":
                transaction_id = command_data.get("transaction_id", "")
                self.state_data["cash_transaction_id"] = transaction_id
                self._cash_payment_event.set()

            elif command_type == "emoney_payment_confirmed":
                # New command from booth bridge via FastAPI relay
                transaction_id = command_data.get("transaction_id", "")
                self.state_data["emoney_transaction_id"] = transaction_id
                self._cash_payment_event.set()

            elif command_type == "cancel_correction":
                logger.info("cancel_correction_ignored", gate_id=self.gate_id)

            elif command_type == "reset_gate":
                reason = command_data.get("reason", "operator")
                await self._cmd_reset_gate(reason)

            else:
                logger.warning("unknown_command", gate_id=self.gate_id, command_type=command_type)

            return True
        except Exception as e:
            logger.error("command_error", gate_id=self.gate_id, command_type=command_type, error=str(e))
            return False

    async def _cmd_open_gate(self, duration_seconds: int | None = None) -> None:
        """Open the gate."""
        await self._send_controller_command(cmd_trig1())
        if self.state in (STATE_WAITING_PAYMENT, STATE_TIMEOUT_ALERT):
            await self._on_gate_opened()

    async def _cmd_close_gate(self) -> None:
        """Close the gate (DUAL relay mode)."""
        if self.config.get("relay_mode") == "DUAL":
            await self._send_controller_command(cmd_trig2())

    async def _cmd_play_audio(self, track: int) -> None:
        """Play audio track."""
        track_str = f"{track:05d}"
        await self._send_controller_command(cmd_mt(track_str))

    async def _cmd_display_text(self, line1: str, line2: str) -> None:
        """Display text on LED."""
        await self._send_controller_command(cmd_ds(line1, line2))

    async def _cmd_buzzer(self, success: bool) -> None:
        """Trigger buzzer."""
        if not success:
            await self._cmd_play_audio(11)

    async def _cmd_print_receipt(self, command_data: dict[str, str]) -> None:
        """Print exit receipt."""
        logger.info("print_receipt_commanded", gate_id=self.gate_id)

    async def _cmd_reset_gate(self, reason: str) -> None:
        """Reset gate to IDLE."""
        logger.info("reset_gate", gate_id=self.gate_id, reason=reason)
        # Cancel any running payment tasks
        for task in asyncio.all_tasks():
            if task.get_name() in ("wiegand", "pos", "timeout"):
                task.cancel()
        await self._transition(STATE_IDLE)
        await self._send_controller_command(cmd_dsu())

    async def _cmd_deduct(self, amount: int, expected_card_number: str) -> None:
        """Execute PASSTI deduct and publish DeductResultEvent."""
        if not self.passti_transport:
            logger.warning("deduct_no_transport", gate_id=self.gate_id)
            await self.publish_event(
                DeductResultEvent(
                    event_type="deduct_result",
                    gate_id=self.gate_id,
                    status=DeductStatus.FAILED,
                    card_number="",
                    card_type="",
                    deduct_amount=amount,
                    balance_before=0,
                    balance_after=0,
                    transaction_counter=0,
                    raw_response_hex="",
                )
            )
            return

        from protocols.passti.commands import cmd_deduct, parse_deduct_response

        frame = cmd_deduct(amount, timeout_sec=30)
        result = await self.passti_transport.send_recv(frame)

        if not result.get("ok"):
            status = self._map_passti_status_to_deduct(result.get("status"))
            await self.publish_event(
                DeductResultEvent(
                    event_type="deduct_result",
                    gate_id=self.gate_id,
                    status=status,
                    card_number="",
                    card_type="",
                    deduct_amount=amount,
                    balance_before=0,
                    balance_after=0,
                    transaction_counter=0,
                    raw_response_hex=result.get("raw", ""),
                )
            )
            return

        body = result.get("body", b"")
        deduct_data = parse_deduct_response(body)

        if not deduct_data.get("ok"):
            await self.publish_event(
                DeductResultEvent(
                    event_type="deduct_result",
                    gate_id=self.gate_id,
                    status=DeductStatus.FAILED,
                    card_number="",
                    card_type="",
                    deduct_amount=amount,
                    balance_before=0,
                    balance_after=0,
                    transaction_counter=0,
                    raw_response_hex=result.get("raw", ""),
                )
            )
            return

        await self.publish_event(
            DeductResultEvent(
                event_type="deduct_result",
                gate_id=self.gate_id,
                status=DeductStatus.SUCCESS,
                card_number=deduct_data.get("card_number", ""),
                card_type=deduct_data.get("card_type", ""),
                deduct_amount=deduct_data.get("deducted", 0),
                balance_before=deduct_data.get("remaining", 0) + deduct_data.get("deducted", 0),
                balance_after=deduct_data.get("remaining", 0),
                transaction_counter=deduct_data.get("trans_counter", 0),
                raw_response_hex=result.get("raw", ""),
            )
        )

    def _map_passti_status_to_deduct(self, status: tuple | None) -> DeductStatus:
        """Map PASSTI status tuple to DeductStatus enum."""
        if status == (0x00, 0x00, 0x00):
            return DeductStatus.SUCCESS
        if status == (0x01, 0x10, 0x02):
            return DeductStatus.TIMEOUT
        if status == (0x01, 0x10, 0x04):
            return DeductStatus.INSUFFICIENT_BALANCE
        if status == (0x01, 0x10, 0x05):
            return DeductStatus.LOST_CONTACT
        if status == (0x01, 0x10, 0x06):
            return DeductStatus.WRONG_CARD
        return DeductStatus.FAILED

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _send_controller_command(self, command: bytes) -> None:
        """Send a command to the Compass controller."""
        if self.controller and self.controller.is_connected():
            try:
                async with self._controller_lock:
                    self.controller.send(command)
                logger.debug("controller_cmd_sent", gate_id=self.gate_id, cmd=command.hex())
            except Exception as e:
                logger.error("controller_cmd_error", gate_id=self.gate_id, error=str(e))

    @staticmethod
    def _card_type_name(code: int) -> str:
        """Map PASSTI card type code to name."""
        from protocols.passti.frame import CARD_TYPES
        return CARD_TYPES.get(code, f"Unknown({code:02X})")
