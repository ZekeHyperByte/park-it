"""Gate-in daemon implementing the full entry state machine.

Modes: CASH, RFID, EMONEY
States: IDLE → VEHICLE_PRESENT → GATE_CLOSED → method branch → OPENING → IDLE

The daemon polls the Compass controller for sensor inputs, publishes events
to FastAPI via Redis Pub/Sub, and executes commands from FastAPI via Redis Streams.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from protocols.compass.parser import parse_rfid_card, parse_stat
from protocols.compass.protocol import (
    CompassTransport,
    cmd_ds,
    cmd_dsu,
    cmd_mt,
    cmd_qr5,
    cmd_stat,
    cmd_trig1,
    cmd_trig2,
)
from protocols.passti.frame import parse_response
from protocols.passti.transport import ControllerPassthroughTransport
from shared.events import (
    BaseEvent,
    GateClosedEvent,
    GateMode,
    GateOpenedEvent,
    PasstiCardTapEvent,
    PlayAudioCommand,
    RfidCardReadEvent,
    TicketButtonPressedEvent,
    VehicleDetectedEvent,
    VehiclePassedEvent,
)
from shared.logging import get_logger

from daemons.base import BaseDaemon

logger = get_logger(__name__)

# State constants
STATE_IDLE = "IDLE"
STATE_VEHICLE_PRESENT = "VEHICLE_PRESENT"
STATE_GATE_CLOSED = "GATE_CLOSED"
STATE_WAITING_BUTTON = "WAITING_BUTTON"
STATE_WAITING_CARD = "WAITING_CARD"
STATE_VALIDATING = "VALIDATING"
STATE_CHECKING_BALANCE = "CHECKING_BALANCE"
STATE_WAITING_PRINT_DECISION = "WAITING_PRINT_DECISION"
STATE_PROCESSING = "PROCESSING"
STATE_OPENING = "OPENING"
STATE_ERROR = "ERROR"

# Poll interval for controller STAT
STAT_POLL_INTERVAL_MS = 100


class GateInDaemon(BaseDaemon):
    """Gate-in daemon for vehicle entry processing."""

    def __init__(self, gate_id: str, config: dict[str, Any]) -> None:
        super().__init__(gate_id, config)
        self.gate_mode: str = config.get("gate_mode", "CASH")
        self.controller: CompassTransport | None = None
        self.passti_transport: ControllerPassthroughTransport | None = None
        self._controller_lock = asyncio.Lock()
        self._poll_task: asyncio.Task | None = None
        self._print_decision_timer: asyncio.Task | None = None

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
            # Create PASSTI passthrough transport only when e-money mode is enabled
            if self.gate_mode == GateMode.EMONEY.value:
                self.passti_transport = ControllerPassthroughTransport(self.controller._sock)
            logger.info("controller_connected", gate_id=self.gate_id, host=host, port=port)
        except Exception as e:
            logger.error("controller_connect_failed", gate_id=self.gate_id, error=str(e))
            self.controller = None
            self.passti_transport = None

    async def _disconnect_controller(self) -> None:
        """Disconnect from controller."""
        if self.controller:
            self.controller.close()
            self.controller = None
            self.passti_transport = None
            logger.info("controller_disconnected", gate_id=self.gate_id)

    # ------------------------------------------------------------------
    # Main polling loop (started by base run as additional task)
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
                    # Always handle response (even empty) so state-specific polling
                    # (e.g., PASSTI tap check in WAITING_CARD) can run.
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
                await self._on_vehicle_detected()

        elif self.state == STATE_VEHICLE_PRESENT:
            # Wait for gate close confirmation
            has_sensor = self.config.get("has_close_sensor", False)
            if has_sensor and parsed["in3"]:
                await self._on_gate_closed()
            # Timer fallback is handled by _gate_close_timer

        elif self.state == STATE_WAITING_BUTTON:
            if parsed["in2"]:
                await self._on_ticket_button_pressed()

        elif self.state == STATE_WAITING_CARD:
            # Check for RFID (W channel)
            if parsed["wiegand_w"]:
                await self._on_rfid_card_read(parsed["wiegand_w"], "W")
                return
            # Check for UHF (X channel)
            if parsed["wiegand_x"]:
                await self._on_rfid_card_read(parsed["wiegand_x"], "X")
                return
            # Check for PASSTI tap (EMONEY mode)
            if self.gate_mode == GateMode.EMONEY.value:
                await self._check_passti_tap()

        elif self.state == STATE_WAITING_PRINT_DECISION:
            if parsed["in2"]:
                await self._on_print_decision(printed=True)

        elif self.state == STATE_OPENING:
            # Wait for vehicle to pass (IN3 or IN1 off + timer)
            if parsed["in3"] or not parsed["in1"]:
                await self._on_vehicle_passed()

    # ------------------------------------------------------------------
    # State transition handlers
    # ------------------------------------------------------------------

    async def _on_vehicle_detected(self) -> None:
        """Vehicle detected at entry."""
        await self._transition(STATE_VEHICLE_PRESENT)
        await self.publish_event(
            VehicleDetectedEvent(
                event_type="vehicle_detected",
                gate_id=self.gate_id,
                sensor="IN1",
            )
        )
        # Close gate
        await self._send_controller_command(cmd_trig2() if self.config.get("relay_mode") == "DUAL" else cmd_trig1())
        # Start gate close timer (fallback if no sensor)
        duration_ms = self.config.get("gate_close_duration_ms", 5000)
        asyncio.create_task(self._gate_close_timer(duration_ms / 1000.0))

    async def _gate_close_timer(self, duration: float) -> None:
        """Fallback timer for gate close confirmation."""
        await asyncio.sleep(duration)
        if self.state == STATE_VEHICLE_PRESENT:
            await self._on_gate_closed()

    async def _on_gate_closed(self) -> None:
        """Gate has closed — branch to method-specific flow."""
        await self._transition(STATE_GATE_CLOSED)
        await self.publish_event(
            GateClosedEvent(
                event_type="gate_closed",
                gate_id=self.gate_id,
            )
        )
        # Reset display
        await self._send_controller_command(cmd_dsu())

        # Branch based on gate mode
        if self.gate_mode == GateMode.CASH.value:
            await self._transition(STATE_WAITING_BUTTON)
            await self._send_controller_command(
                cmd_ds("Selamat Datang", "Ambil Tiket")
            )

        elif self.gate_mode == GateMode.RFID.value:
            await self._transition(STATE_WAITING_CARD)
            await self._send_controller_command(
                cmd_ds("Tempelkan Kartu", "Member RFID")
            )

        elif self.gate_mode == GateMode.EMONEY.value:
            await self._transition(STATE_WAITING_CARD)
            await self._send_controller_command(
                cmd_ds("Tempelkan Kartu", "E-Money")
            )

    async def _on_ticket_button_pressed(self) -> None:
        """Ticket button pressed in CASH mode."""
        await self._transition(STATE_PROCESSING)
        await self.publish_event(
            TicketButtonPressedEvent(
                event_type="ticket_button_pressed",
                gate_id=self.gate_id,
            )
        )
        # FastAPI will create transaction and send print_ticket + open_gate commands

    async def _on_rfid_card_read(self, card_number: str, channel: str) -> None:
        """RFID/UHF card read."""
        await self._transition(STATE_VALIDATING if self.gate_mode == GateMode.RFID.value else STATE_PROCESSING)
        await self.publish_event(
            RfidCardReadEvent(
                event_type="rfid_card_read",
                gate_id=self.gate_id,
                card_number=card_number,
                channel=channel,
            )
        )
        # FastAPI validates member and sends open_gate command

    async def _check_passti_tap(self) -> None:
        """Check for PASSTI card tap in EMONEY mode."""
        if not self.passti_transport:
            return
        try:
            from protocols.passti.commands import cmd_check_balance

            frame = cmd_check_balance(timeout_sec=10)
            result = await self.passti_transport.send_recv(frame, timeout=2.0)
            if result.get("ok"):
                body = result.get("body", b"")
                if len(body) >= 13:
                    card_number = body[1:9].hex().upper()
                    card_type_code = body[0]
                    balance = int.from_bytes(body[9:13], "big")
                    await self._on_passti_card_tap(card_number, card_type_code, balance)
        except Exception as e:
            logger.debug("passti_poll_no_card", gate_id=self.gate_id, error=str(e))

    async def _on_passti_card_tap(self, card_number: str, card_type_code: int, balance: int) -> None:
        """PASSTI card tapped in EMONEY mode."""
        await self._transition(STATE_CHECKING_BALANCE)
        card_type = self._card_type_name(card_type_code)
        await self.publish_event(
            PasstiCardTapEvent(
                event_type="passti_card_tap",
                gate_id=self.gate_id,
                card_number=card_number,
                card_type=card_type,
            )
        )
        # FastAPI will check balance against threshold and send next command
        # (either display insufficient balance, or proceed to print decision)

    async def _start_print_decision_timer(self, timeout: float) -> None:
        """Start timer for print decision in EMONEY mode."""
        async def timer() -> None:
            await asyncio.sleep(timeout)
            if self.state == STATE_WAITING_PRINT_DECISION:
                await self._on_print_decision(printed=False)

        self._print_decision_timer = asyncio.create_task(timer(), name="print_timer")

    async def _on_print_decision(self, printed: bool) -> None:
        """Print decision made (button pressed or timeout)."""
        if self._print_decision_timer and not self._print_decision_timer.done():
            self._print_decision_timer.cancel()
        self.state_data["ticket_printed"] = printed
        await self._transition(STATE_PROCESSING)
        # FastAPI will create transaction and send open_gate command

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
        # Start timer to detect vehicle passing
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
        logger.info("gate_in_command", gate_id=self.gate_id, command_type=command_type)

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

            elif command_type == "print_ticket":
                barcode = command_data.get("barcode", "")
                gate_name = command_data.get("gate_name", self.config.get("name", ""))
                await self._cmd_print_ticket(barcode, gate_name)

            elif command_type == "check_balance":
                threshold = int(command_data.get("minimum_threshold", 10000))
                await self._cmd_check_balance(threshold)

            elif command_type == "reset_gate":
                reason = command_data.get("reason", "operator")
                await self._cmd_reset_gate(reason)

            elif command_type == "deduct":
                # Gate-in does not handle deduct; gate-out only
                logger.warning("deduct_ignored_at_gate_in", gate_id=self.gate_id)

            else:
                logger.warning("unknown_command", gate_id=self.gate_id, command_type=command_type)

            return True
        except Exception as e:
            logger.error("command_error", gate_id=self.gate_id, command_type=command_type, error=str(e))
            return False

    async def _cmd_open_gate(self, duration_seconds: int | None = None) -> None:
        """Open the gate."""
        await self._send_controller_command(cmd_trig1())
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
        # Compass protocol doesn't have direct buzzer; use audio track 11 for failure
        if not success:
            await self._cmd_play_audio(11)

    async def _cmd_print_ticket(self, barcode: str, gate_name: str) -> None:
        """Print entry ticket."""
        # Ticket printing is handled by ARQ critical worker
        # The daemon just confirms it received the command
        # In a real implementation, this might trigger a local printer via escpos
        logger.info("print_ticket_commanded", gate_id=self.gate_id, barcode=barcode)

    async def _cmd_check_balance(self, minimum_threshold: int) -> None:
        """Check PASSTI balance and transition based on result."""
        if not self.passti_transport:
            logger.error("passti_not_connected", gate_id=self.gate_id)
            return

        try:
            from protocols.passti.commands import cmd_check_balance

            frame = cmd_check_balance(timeout_sec=10)
            result = await self.passti_transport.send_recv(frame, timeout=5.0)

            if result.get("ok"):
                body = result.get("body", b"")
                if len(body) >= 13:
                    balance = int.from_bytes(body[9:13], "big")
                    if balance < minimum_threshold:
                        await self._send_controller_command(
                            cmd_ds("Saldo Tidak Cukup", f"Rp {balance:,}")
                        )
                        await self._cmd_play_audio(6)
                        await self._transition(STATE_IDLE)
                    else:
                        # Sufficient balance — proceed to print decision
                        await self._transition(STATE_WAITING_PRINT_DECISION)
                        await self._send_controller_command(
                            cmd_ds("Cetak Tiket?", "Tekan Tombol")
                        )
                        timeout = self.config.get("print_decision_timeout_seconds", 10)
                        await self._start_print_decision_timer(timeout)
                else:
                    await self._send_controller_command(cmd_ds("Kartu Error", "Coba Lagi"))
                    await self._transition(STATE_IDLE)
            else:
                status_msg = result.get("status_msg", "Unknown error")
                await self._send_controller_command(cmd_ds("Error", status_msg))
                await self._transition(STATE_IDLE)
        except Exception as e:
            logger.error("check_balance_error", gate_id=self.gate_id, error=str(e))
            await self._transition(STATE_IDLE)

    async def _cmd_reset_gate(self, reason: str) -> None:
        """Reset gate to IDLE."""
        logger.info("reset_gate", gate_id=self.gate_id, reason=reason)
        await self._transition(STATE_IDLE)
        await self._send_controller_command(cmd_dsu())

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
