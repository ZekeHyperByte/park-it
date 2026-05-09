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
    SerialTransport,
    cmd_ack_in1off,
    cmd_ack_in1on,
    cmd_ack_in3off,
    cmd_ack_in3on,
    cmd_ack_wiegand,
    cmd_close1,
    cmd_ds,
    cmd_dsu,
    cmd_mt,
    cmd_open1,
    cmd_rss,
    cmd_stat,
    cmd_stop1,
    cmd_trig1,
)
from protocols.passti.transport import ControllerPassthroughTransport, DirectSerialTransport
from shared.events import (
    BaseEvent,
    DeductResultEvent,
    DeductStatus,
    GateOpenedEvent,
    PasstiCardTapEvent,
    PlayAudioEvent,
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



class GateOutDaemon(BaseDaemon):
    """Gate-out daemon for vehicle exit processing."""

    def __init__(self, gate_id: str, config: dict[str, Any]) -> None:
        super().__init__(gate_id, config)
        self.hw = config.get("hardware_config", {})
        self.has_rfid = self.hw.get("rfid", {}).get("enabled", False)
        self.has_emoney = self.hw.get("emoney", {}).get("enabled", False)
        self.controller: CompassTransport | SerialTransport | None = None
        self._controller_lock = asyncio.Lock()
        self._poll_task: asyncio.Task | None = None
        self._payment_task: asyncio.Task | None = None
        self._cash_payment_event = asyncio.Event()
        self._debounce_event: asyncio.Event | None = None
        self._wiegand_event = asyncio.Event()
        self._wiegand_data: tuple[str, str] | None = None
        self.passti_transport: ControllerPassthroughTransport | DirectSerialTransport | None = None

    # ------------------------------------------------------------------
    # Lifecycle overrides
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start daemon: connect controller, then delegate to base run."""
        await self._connect_controller()
        await super().run()

    async def _on_started(self) -> None:
        """Start controller polling after base sets _running=True."""
        await self._initialize_gate_position()
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
        """Connect to gate controller (TCP or serial based on protocol config)."""
        protocol = self.config.get("protocol", "compass")
        try:
            if protocol == "serial":
                device = self.config.get("controller_device")
                baudrate = self.config.get("controller_baudrate", 9600)
                if not device:
                    logger.warning("no_controller_config", gate_id=self.gate_id, protocol=protocol)
                    return
                self.controller = SerialTransport(device, baudrate)
                self.controller.connect(timeout=5.0)
                logger.info("controller_connected", gate_id=self.gate_id, device=device, baudrate=baudrate)
            else:
                host = self.config.get("controller_host")
                port = self.config.get("controller_port")
                if not host or not port:
                    logger.warning("no_controller_config", gate_id=self.gate_id, protocol=protocol)
                    return
                self.controller = CompassTransport(host, port)
                self.controller.connect(timeout=5.0)
                logger.info("controller_connected", gate_id=self.gate_id, host=host, port=port)

            # Wire PASSTI transport (resolved after controller connects)
            if self.has_emoney:
                emoney_cfg = self.hw.get("emoney", {})
                if emoney_cfg.get("connection", "controller") == "direct_serial":
                    emoney_device = emoney_cfg.get("device")
                    emoney_baudrate = emoney_cfg.get("baudrate", 38400)
                    if emoney_device:
                        self.passti_transport = DirectSerialTransport(emoney_device, emoney_baudrate)
                        logger.info("passti_direct_serial", gate_id=self.gate_id, device=emoney_device)
                    else:
                        logger.warning("passti_direct_serial_no_device", gate_id=self.gate_id)
                elif protocol != "serial":
                    # Controller passthrough requires TCP socket — not available on serial controller
                    self.passti_transport = ControllerPassthroughTransport(self.controller._sock)

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
    # Relay mode helpers
    # ------------------------------------------------------------------

    async def _relay_open(self) -> None:
        """Open gate using relay_mode-appropriate command."""
        relay_mode = self.config.get("relay_mode", "SINGLE")
        if relay_mode == "SINGLE":
            await self._send_controller_command(cmd_trig1())
        else:
            await self._send_controller_command(cmd_open1())

    async def _relay_close(self) -> None:
        """Close gate using relay_mode-appropriate command. No-op for SINGLE."""
        relay_mode = self.config.get("relay_mode", "SINGLE")
        if relay_mode in ("DUAL", "TRIPLE"):
            await self._send_controller_command(cmd_close1())

    async def _relay_brake(self) -> None:
        """Brake gate motor. Only valid for TRIPLE relay mode."""
        if self.config.get("relay_mode") == "TRIPLE":
            await self._send_controller_command(cmd_stop1())

    # ------------------------------------------------------------------
    # Gate position initialization
    # ------------------------------------------------------------------

    async def _initialize_gate_position(self) -> None:
        """Ensure gate is physically closed on daemon startup."""
        relay_mode = self.config.get("relay_mode", "SINGLE")
        has_close_sensor = self.config.get("has_close_sensor", False)

        if relay_mode in ("DUAL", "TRIPLE"):
            await self._relay_close()
            logger.info("gate_initialized_closed", gate_id=self.gate_id, mode=relay_mode)
        elif has_close_sensor:
            if self.controller and self.controller.is_connected():
                async with self._controller_lock:
                    response = self.controller.send_recv(cmd_stat(), timeout=0.5)
                parsed = parse_stat(response or b"")
                if not parsed["in3"]:
                    await self._relay_open()
                    logger.info("gate_initialized_closed", gate_id=self.gate_id, mode="SINGLE_SENSOR")
                else:
                    logger.info("gate_already_closed", gate_id=self.gate_id, mode="SINGLE_SENSOR")
        else:
            logger.warning(
                "gate_init_state_unknown",
                gate_id=self.gate_id,
                mode="SINGLE_NO_SENSOR",
                note="trusting hardware power-on default",
            )

    # ------------------------------------------------------------------
    # RSS listener (replaces STAT poll)
    # ------------------------------------------------------------------

    async def _start_polling(self) -> None:
        """Start RSS listener task and optional direct serial RFID reader."""
        self._poll_task = asyncio.create_task(self._rss_listener(), name="poll")
        self._tasks.append(self._poll_task)
        if self.has_rfid and self.hw.get("rfid", {}).get("connection") == "direct_serial":
            task = asyncio.create_task(self._rfid_serial_reader_task(), name="rfid_serial")
            self._tasks.append(task)

    async def _setup_rss(self) -> None:
        """Send RSS config — controller will push input events automatically."""
        if self.controller and self.controller.is_connected():
            async with self._controller_lock:
                self.controller.send(cmd_rss(interval_100ms=2))
            logger.info("rss_configured", gate_id=self.gate_id)

    async def _rss_listener(self) -> None:
        """Read RSS push events from controller. No STAT polling needed."""
        await self._setup_rss()
        buffer = b""
        while self._running:
            try:
                if self.controller and self.controller.is_connected():
                    chunk = await self.controller.recv_async(timeout=0.5)
                    if chunk:
                        buffer += chunk
                        buffer = await self._process_rss_buffer(buffer)
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                logger.debug("rss_listener_cancelled", gate_id=self.gate_id)
                raise
            except Exception as e:
                logger.error("rss_listener_error", gate_id=self.gate_id, error=str(e))
                await asyncio.sleep(1)

    async def _process_rss_buffer(self, buffer: bytes) -> bytes:
        """Parse framed messages from buffer, dispatch each. Returns unconsumed bytes."""
        while len(buffer) >= 2:
            try:
                start = buffer.index(0xA6)
            except ValueError:
                return b""
            try:
                end = buffer.index(0xA9, start + 1)
            except ValueError:
                break
            msg = buffer[start: end + 1]
            buffer = buffer[end + 1:]
            await self._dispatch_rss_message(msg)
        return buffer

    async def _dispatch_rss_message(self, msg: bytes) -> None:
        """Route RSS message to appropriate state handler."""
        text = msg.decode("latin-1", errors="ignore")

        # Ignore command responses
        if text.rstrip("\xa9").endswith("OK"):
            return

        if "IN1ON" in text:
            await self._send_controller_command(cmd_ack_in1on())
            if self.state == STATE_IDLE:
                if self._debounce_event is None or self._debounce_event.is_set():
                    self._debounce_event = asyncio.Event()
                    asyncio.create_task(self._vehicle_debounce_timer(0.5))

        elif "IN1OFF" in text:
            await self._send_controller_command(cmd_ack_in1off())
            if self.state == STATE_OPENING:
                await self._on_vehicle_passed()
            elif self.state == STATE_TIMEOUT_ALERT:
                await self._on_vehicle_left(reason="abandoned")

        elif "IN3ON" in text:
            await self._send_controller_command(cmd_ack_in3on())
            if self.state == STATE_OPENING:
                await self._on_vehicle_passed()

        elif "IN3OFF" in text:
            await self._send_controller_command(cmd_ack_in3off())
            if self.state == STATE_OPENING:
                await self._on_vehicle_passed()

        else:
            parsed = parse_stat(msg)
            if parsed["wiegand_w"] or parsed["wiegand_x"]:
                await self._send_controller_command(cmd_ack_wiegand())
                if parsed["wiegand_w"]:
                    self._wiegand_data = (parsed["wiegand_w"], "W")
                else:
                    self._wiegand_data = (parsed["wiegand_x"], "X")
                self._wiegand_event.set()

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
        """Wait for Wiegand card via RSS event (set by _dispatch_rss_message)."""
        self._wiegand_event.clear()
        self._wiegand_data = None
        while self.state == STATE_WAITING_PAYMENT and self._running:
            try:
                await asyncio.wait_for(self._wiegand_event.wait(), timeout=1.0)
                if self._wiegand_data:
                    self.state_data["rfid_card"] = self._wiegand_data[0]
                    self.state_data["rfid_channel"] = self._wiegand_data[1]
                    self._wiegand_event.clear()
                    self._wiegand_data = None
                    return
            except asyncio.TimeoutError:
                continue

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
        await self._send_controller_command(cmd_ds("Mohon Hubungi Petugas", ""))
        await self._cmd_play_audio(8)
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

            elif command_type == "brake_gate":
                await self._cmd_brake_gate()

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
        await self._relay_open()
        await self._cmd_play_audio(10)  # pembayaran_berhasil
        if self.state in (STATE_WAITING_PAYMENT, STATE_TIMEOUT_ALERT):
            await self._on_gate_opened()

    async def _cmd_close_gate(self) -> None:
        """Close the gate (DUAL/TRIPLE relay mode)."""
        await self._relay_close()

    async def _cmd_brake_gate(self) -> None:
        """Brake the gate motor mid-travel (TRIPLE relay mode only)."""
        await self._relay_brake()

    async def _cmd_play_audio(self, track: int) -> None:
        """Play audio track — via controller MP3 module (TCP) or browser (serial)."""
        if self.config.get("protocol", "compass") == "serial":
            await self.publish_event(PlayAudioEvent(gate_id=self.gate_id, track=track))
        else:
            await self._send_controller_command(cmd_mt(f"{track:05d}"))

    async def _cmd_display_text(self, line1: str, line2: str) -> None:
        """Display text on LED."""
        await self._send_controller_command(cmd_ds(line1, line2))

    async def _cmd_buzzer(self, success: bool) -> None:
        """Trigger buzzer."""
        if not success:
            await self._cmd_play_audio(11)

    async def _cmd_print_receipt(self, command_data: dict[str, str]) -> None:
        """Print exit receipt — enqueue ARQ print job."""
        import json as json_mod

        logger.info("print_receipt_commanded", gate_id=self.gate_id)

        try:
            from shared.redis import get_arq_redis

            transaction_data_raw = command_data.get("transaction_data", "{}")
            if isinstance(transaction_data_raw, str):
                transaction_data = json_mod.loads(transaction_data_raw)
            else:
                transaction_data = transaction_data_raw

            arq_redis = await get_arq_redis()
            await arq_redis.enqueue_job(
                "print_receipt",
                gate_id=self.gate_id,
                transaction_data=transaction_data,
            )
            logger.info("receipt_job_enqueued", gate_id=self.gate_id)
        except Exception as e:
            logger.error("receipt_enqueue_failed", gate_id=self.gate_id, error=str(e))

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
                card_type_code=deduct_data.get("card_type_code", 0),
                deduct_amount=deduct_data.get("deducted", 0),
                balance_before=deduct_data.get("remaining", 0) + deduct_data.get("deducted", 0),
                balance_after=deduct_data.get("remaining", 0),
                transaction_counter=deduct_data.get("trans_counter", 0),
                raw_response_hex=result.get("raw", ""),
                settlement_payload_hex=result.get("body_hex", ""),
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

    async def _rfid_serial_reader_task(self) -> None:
        """Read card numbers from a directly-connected serial RFID reader.

        Sets _wiegand_event identical to controller RSS path — _wait_for_wiegand
        works unchanged regardless of which source fires the event.
        """
        rfid_cfg = self.hw.get("rfid", {})
        device = rfid_cfg.get("device")
        baudrate = rfid_cfg.get("baudrate", 9600)
        if not device:
            logger.error("rfid_serial_no_device", gate_id=self.gate_id)
            return

        loop = asyncio.get_event_loop()
        try:
            import serial as _serial
            ser = _serial.Serial(port=device, baudrate=baudrate, timeout=0.5)
        except Exception as e:
            logger.error("rfid_serial_open_failed", gate_id=self.gate_id, error=str(e))
            return

        logger.info("rfid_serial_reader_started", gate_id=self.gate_id, device=device)
        try:
            while self._running:
                try:
                    raw = await loop.run_in_executor(None, ser.readline)
                    card_number = raw.decode("ascii", errors="ignore").strip()
                    if card_number:
                        self._wiegand_data = (card_number, "S")
                        self._wiegand_event.set()
                        logger.info("rfid_serial_card_read", gate_id=self.gate_id, card=card_number)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error("rfid_serial_read_error", gate_id=self.gate_id, error=str(e))
                    await asyncio.sleep(1)
        finally:
            ser.close()

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
