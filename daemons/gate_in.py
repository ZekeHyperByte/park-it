"""Gate-in daemon — combined entry state machine.

Single WAITING_INPUT state handles all payment methods simultaneously:
button (cash), Wiegand W/X (RFID/UHF), PASSTI (e-money).

States: IDLE → WAITING_INPUT → method branch → OPENING → IDLE
"""

from __future__ import annotations

import asyncio
from typing import Any

from daemons.base import BaseDaemon
from protocols.compass.parser import parse_stat
from protocols.compass.protocol import (
    CompassTransport,
    SerialTransport,
    cmd_ack_in1off,
    cmd_ack_in1on,
    cmd_ack_in2on,
    cmd_ack_in3on,
    cmd_ack_in4off,
    cmd_ack_in4on,
    cmd_ack_wiegand,
    cmd_close1,
    cmd_ds,
    cmd_dsu,
    cmd_mt,
    cmd_open1,
    cmd_pr3,
    cmd_rss,
    cmd_stop1,
    cmd_trig1,
)
from protocols.passti.transport import ControllerPassthroughTransport
from shared.events import (
    BaseEvent,
    EmoneyPrintDecisionEvent,
    GateOpenedEvent,
    HelpButtonPressedEvent,
    PasstiCardTapEvent,
    PlayAudioEvent,
    RfidCardReadEvent,
    TicketButtonPressedEvent,
    VehicleDetectedEvent,
    VehiclePassedEvent,
)
from shared.logging import get_logger

logger = get_logger(__name__)

# State constants
STATE_IDLE = "IDLE"
STATE_WAITING_INPUT = "WAITING_INPUT"
STATE_VALIDATING = "VALIDATING"
STATE_CHECKING_BALANCE = "CHECKING_BALANCE"
STATE_WAITING_PRINT_DECISION = "WAITING_PRINT_DECISION"
STATE_PROCESSING = "PROCESSING"
STATE_OPENING = "OPENING"
STATE_ERROR = "ERROR"


class GateInDaemon(BaseDaemon):
    """Gate-in daemon for vehicle entry processing."""

    def __init__(self, gate_id: str, config: dict[str, Any]) -> None:
        super().__init__(gate_id, config)
        self.hw = config.get("hardware_config", {})
        self.has_rfid = self.hw.get("rfid", {}).get("enabled", False)
        self.has_ticket_printer = self.hw.get("ticket_printer", {}).get("enabled", False)
        self.has_emoney = self.hw.get("emoney", {}).get("enabled", False)

        self.controller: CompassTransport | SerialTransport | None = None
        self.passti_transport: ControllerPassthroughTransport | None = None
        self._controller_lock = asyncio.Lock()
        self._poll_task: asyncio.Task | None = None
        self._print_decision_timer: asyncio.Task | None = None
        self._validating_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run(self) -> None:
        await self._connect_controller()
        await super().run()

    async def _on_started(self) -> None:
        if self.state != STATE_IDLE:
            logger.warning("startup_state_reset", gate_id=self.gate_id, old_state=self.state)
            await self._transition(STATE_IDLE)
        await self._start_polling()

    async def stop(self) -> None:
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
                if self.has_emoney:
                    self.passti_transport = ControllerPassthroughTransport(self.controller._sock)
                logger.info("controller_connected", gate_id=self.gate_id, host=host, port=port)
        except Exception as e:
            logger.error("controller_connect_failed", gate_id=self.gate_id, error=str(e))
            self.controller = None
            self.passti_transport = None

    async def _disconnect_controller(self) -> None:
        if self.controller:
            self.controller.close()
            self.controller = None
            self.passti_transport = None
            logger.info("controller_disconnected", gate_id=self.gate_id)

    # ------------------------------------------------------------------
    # Relay mode helpers
    # ------------------------------------------------------------------

    async def _relay_open(self) -> None:
        relay_mode = self.config.get("relay_mode", "SINGLE")
        if relay_mode == "SINGLE":
            await self._send_controller_command(cmd_trig1())
        else:
            await self._send_controller_command(cmd_open1())

    async def _relay_close(self) -> None:
        if self.config.get("relay_mode") in ("DUAL", "TRIPLE"):
            await self._send_controller_command(cmd_close1())

    async def _relay_brake(self) -> None:
        if self.config.get("relay_mode") == "TRIPLE":
            await self._send_controller_command(cmd_stop1())

    async def _display(self, line1: str = "", line2: str = "") -> None:
        if self.hw.get("display", {}).get("enabled", True):
            cmd = cmd_dsu() if not line1 else cmd_ds(line1, line2)
            await self._send_controller_command(cmd)

    # ------------------------------------------------------------------
    # RSS listener
    # ------------------------------------------------------------------

    async def _start_polling(self) -> None:
        self._poll_task = asyncio.create_task(self._rss_listener(), name="poll")
        self._tasks.append(self._poll_task)
        if self.has_rfid and self.hw.get("rfid", {}).get("connection") == "direct_serial":
            task = asyncio.create_task(self._rfid_serial_reader_task(), name="rfid_serial")
            self._tasks.append(task)

    async def _setup_rss(self) -> None:
        if self.controller and self.controller.is_connected():
            async with self._controller_lock:
                self.controller.send(cmd_rss(interval_100ms=2))
            logger.info("rss_configured", gate_id=self.gate_id)

    async def _rss_listener(self) -> None:
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
        text = msg.decode("latin-1", errors="ignore")

        if text.rstrip("\xa9").endswith("OK"):
            return

        if "IN1ON" in text:
            await self._send_controller_command(cmd_ack_in1on())
            if self.state == STATE_IDLE:
                await self._on_vehicle_detected()

        elif "IN1OFF" in text:
            await self._send_controller_command(cmd_ack_in1off())
            if self.state == STATE_WAITING_INPUT:
                await self._on_vehicle_backed_up()
            elif self.state == STATE_OPENING:
                await self._on_vehicle_passed()

        elif "IN2ON" in text:
            await self._send_controller_command(cmd_ack_in2on())
            if self.state == STATE_WAITING_INPUT:
                await self._on_ticket_button_pressed()
            elif self.state == STATE_WAITING_PRINT_DECISION:
                await self._on_print_decision(printed=True)

        elif "IN3ON" in text:
            await self._send_controller_command(cmd_ack_in3on())
            if self.state == STATE_WAITING_INPUT:
                await self._on_help_button()

        elif "IN4ON" in text:
            await self._send_controller_command(cmd_ack_in4on())
            if self.state == STATE_WAITING_INPUT:
                await self._on_reset()
            elif self.state == STATE_OPENING:
                await self._on_vehicle_passed()

        elif "IN4OFF" in text:
            await self._send_controller_command(cmd_ack_in4off())
            if self.state == STATE_OPENING:
                await self._on_vehicle_passed()

        else:
            parsed = parse_stat(msg)
            if parsed["wiegand_w"] or parsed["wiegand_x"]:
                await self._send_controller_command(cmd_ack_wiegand())
                if self.state == STATE_WAITING_INPUT and self.has_rfid:
                    if parsed["wiegand_w"]:
                        await self._on_rfid_card_read(parsed["wiegand_w"], "W")
                    elif parsed["wiegand_x"]:
                        await self._on_rfid_card_read(parsed["wiegand_x"], "X")

    # ------------------------------------------------------------------
    # PASSTI polling (serial port — not RSS-pushable)
    # ------------------------------------------------------------------

    async def _passti_poll_loop(self) -> None:
        while self.state == STATE_WAITING_INPUT and self._running:
            await self._check_passti_tap()
            await asyncio.sleep(0.5)

    async def _check_passti_tap(self) -> None:
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

    # ------------------------------------------------------------------
    # State transition handlers
    # ------------------------------------------------------------------

    async def _on_vehicle_detected(self) -> None:
        """Vehicle at sensor — go straight to WAITING_INPUT, no gate close."""
        await self._transition(STATE_WAITING_INPUT)
        await self.publish_event(
            VehicleDetectedEvent(event_type="vehicle_detected", gate_id=self.gate_id, sensor="IN1")
        )
        audio_cfg = self.hw.get("audio", {})
        if audio_cfg.get("enabled", True):
            track = audio_cfg.get("welcome_track", 1)
            await self._cmd_play_audio(track)
        await self._display("Selamat Datang", "Tombol/Tempel Kartu")
        if self.has_emoney:
            asyncio.create_task(self._passti_poll_loop(), name="passti_poll")

    async def _on_vehicle_backed_up(self) -> None:
        """Vehicle reversed before completing entry."""
        await self._transition(STATE_IDLE)
        await self._display()
        logger.info("vehicle_backed_up", gate_id=self.gate_id)

    async def _on_reset(self) -> None:
        """IN4 triggered during input wait — reset to IDLE."""
        await self._transition(STATE_IDLE)
        await self._display()
        logger.info("gate_reset_by_sensor", gate_id=self.gate_id)

    async def _on_help_button(self) -> None:
        """IN3 help button — alert operator, hold 10s, reset."""
        await self._cmd_play_audio(5)
        await self._display("Mohon Tunggu", "Petugas Membantu Anda")
        await self.publish_event(
            HelpButtonPressedEvent(event_type="help_button_pressed", gate_id=self.gate_id)
        )
        await asyncio.sleep(10)
        await self._transition(STATE_IDLE)
        await self._display()

    async def _on_ticket_button_pressed(self) -> None:
        """Cash button pressed — notify API to create transaction and print."""
        await self._transition(STATE_PROCESSING)
        await self.publish_event(
            TicketButtonPressedEvent(event_type="ticket_button_pressed", gate_id=self.gate_id)
        )

    async def _on_rfid_card_read(self, card_number: str, channel: str) -> None:
        """Wiegand card read — notify API to validate member."""
        await self._transition(STATE_VALIDATING)
        await self.publish_event(
            RfidCardReadEvent(
                event_type="rfid_card_read",
                gate_id=self.gate_id,
                card_number=card_number,
                channel=channel,
            )
        )
        self._validating_task = asyncio.create_task(self._validating_timeout(), name="validating_timeout")

    async def _validating_timeout(self) -> None:
        timeout = self.config.get("gate_open_timeout_s") or 10
        await asyncio.sleep(timeout)
        if self.state == STATE_VALIDATING:
            logger.warning("validating_timeout_reset", gate_id=self.gate_id)
            await self._transition(STATE_IDLE)
            await self._display()

    async def _on_passti_card_tap(self, card_number: str, card_type_code: int, balance: int) -> None:
        """E-money card tapped — notify API to check balance threshold."""
        await self._transition(STATE_CHECKING_BALANCE)
        card_type = self._card_type_name(card_type_code)
        self.state_data["passti_card_number"] = card_number
        self.state_data["passti_card_type"] = card_type
        self.state_data["passti_balance"] = balance
        await self.publish_event(
            PasstiCardTapEvent(
                event_type="passti_card_tap",
                gate_id=self.gate_id,
                card_number=card_number,
                card_type=card_type,
            )
        )

    async def _start_print_decision_timer(self, timeout: float) -> None:
        async def timer() -> None:
            await asyncio.sleep(timeout)
            if self.state == STATE_WAITING_PRINT_DECISION:
                await self._on_print_decision(printed=False)
        self._print_decision_timer = asyncio.create_task(timer(), name="print_timer")

    async def _on_print_decision(self, printed: bool) -> None:
        """Driver made print decision (button or timeout)."""
        if self._print_decision_timer and not self._print_decision_timer.done():
            self._print_decision_timer.cancel()
        self.state_data["ticket_printed"] = printed
        await self._transition(STATE_PROCESSING)
        await self.publish_event(
            EmoneyPrintDecisionEvent(
                event_type="emoney_print_decision",
                gate_id=self.gate_id,
                printed=printed,
                card_number=self.state_data.get("passti_card_number", ""),
                card_type=self.state_data.get("passti_card_type", ""),
                balance=self.state_data.get("passti_balance", 0),
            )
        )

    async def _on_gate_opened(self) -> None:
        await self._transition(STATE_OPENING)
        await self.publish_event(
            GateOpenedEvent(event_type="gate_opened", gate_id=self.gate_id)
        )
        asyncio.create_task(self._vehicle_pass_timer())

    async def _vehicle_pass_timer(self) -> None:
        await asyncio.sleep(self.config.get("gate_open_timeout_s") or 10)
        if self.state == STATE_OPENING:
            await self._on_vehicle_passed()

    async def _on_vehicle_passed(self) -> None:
        await self._transition(STATE_IDLE)
        await self.publish_event(
            VehiclePassedEvent(event_type="vehicle_passed", gate_id=self.gate_id)
        )
        await self._display()
        await self._relay_close()

    # ------------------------------------------------------------------
    # Command handlers (from Redis Streams)
    # ------------------------------------------------------------------

    async def handle_command(self, command_data: dict[str, str]) -> bool:
        command_type = command_data.get("command_type", "")
        logger.info("gate_in_command", gate_id=self.gate_id, command_type=command_type)
        try:
            if command_type == "open_gate":
                await self._cmd_open_gate()
            elif command_type == "close_gate":
                await self._relay_close()
            elif command_type == "brake_gate":
                await self._relay_brake()
            elif command_type == "play_audio":
                await self._cmd_play_audio(int(command_data.get("track", 1)))
            elif command_type == "display_text":
                await self._cmd_display_text(
                    command_data.get("line1", ""), command_data.get("line2", "")
                )
            elif command_type == "buzzer":
                if command_data.get("success", "true").lower() != "true":
                    await self._cmd_play_audio(11)
            elif command_type == "print_ticket":
                await self._cmd_print_ticket(
                    command_data.get("barcode", ""),
                    command_data.get("gate_name", self.config.get("name", "")),
                )
            elif command_type == "print_ticket_then_open":
                await self._cmd_print_ticket_then_open(
                    command_data.get("barcode", ""),
                    command_data.get("gate_name", self.config.get("name", "")),
                )
            elif command_type == "check_balance":
                await self._cmd_check_balance(
                    int(command_data.get("minimum_threshold", 10000))
                )
            elif command_type == "reject_card":
                await self._cmd_reject_card(
                    command_data.get("line1", "Kartu Tidak Valid"),
                    command_data.get("line2", ""),
                    int(command_data.get("audio_track", 3)),
                    float(command_data.get("display_seconds", 3.0)),
                )
            elif command_type == "reset_gate":
                await self._cmd_reset_gate(command_data.get("reason", "operator"))
            elif command_type == "inject_rss":
                signal = command_data.get("signal", "")
                logger.warning("mock_inject_rss", gate_id=self.gate_id, signal=signal)
                frame = b"\xa6" + signal.encode("latin-1") + b"\xa9"
                await self._dispatch_rss_message(frame)
            elif command_type == "deduct":
                logger.warning("deduct_ignored_at_gate_in", gate_id=self.gate_id)
            else:
                logger.warning("unknown_command", gate_id=self.gate_id, command_type=command_type)
            return True
        except Exception as e:
            logger.error("command_error", gate_id=self.gate_id, command_type=command_type, error=str(e))
            return False

    async def _cmd_open_gate(self) -> None:
        await self._relay_open()
        await self._cmd_play_audio(9)  # terima_kasih
        await self._on_gate_opened()

    async def _cmd_play_audio(self, track: int) -> None:
        track_map = self.hw.get("audio", {}).get("track_map", {})
        actual = track_map.get(str(track), track)
        if self.config.get("protocol", "compass") == "serial":
            await self.publish_event(PlayAudioEvent(gate_id=self.gate_id, track=actual))
        else:
            await self._send_controller_command(cmd_mt(f"{actual:05d}"))

    async def _cmd_display_text(self, line1: str, line2: str) -> None:
        await self._display(line1, line2)

    async def _cmd_print_ticket(self, barcode: str, gate_name: str) -> None:
        logger.info("print_ticket_commanded", gate_id=self.gate_id, barcode=barcode)
        try:
            from shared.redis import get_arq_redis
            arq_redis = await get_arq_redis()
            await arq_redis.enqueue_job("print_ticket", gate_id=self.gate_id, barcode=barcode, gate_name=gate_name)
        except Exception as e:
            logger.error("print_ticket_enqueue_failed", gate_id=self.gate_id, error=str(e))

    async def _cmd_print_ticket_then_open(self, barcode: str, gate_name: str) -> None:
        """Print-first cash entry flow. Gate ALWAYS opens — never trap a vehicle."""
        logger.info("print_ticket_then_open", gate_id=self.gate_id, barcode=barcode)
        print_success = False
        try:
            from datetime import datetime
            timestamp_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            escpos_data = b"".join([
                b"\x1b\x61\x01",
                b"TIKET PARKIR\n",
                b"\x1b\x61\x00",
                f"GATE    : {gate_name}\n".encode(),
                f"TANGGAL : {timestamp_str}\n".encode(),
                b"\x1b\x61\x01",
                b"\x1d\x68\x64",
                b"\x1d\x48\x02",
                b"\x1d\x6b\x45",
                bytes([len(barcode)]) + barcode.encode() + b"\x00",
                b"\n\x1d\x56\x41",
            ])
            await self._send_controller_command(cmd_pr3(escpos_data))
            await asyncio.sleep(1.5)
            print_success = True
            logger.info("cash_ticket_printed", gate_id=self.gate_id, barcode=barcode)
        except Exception as e:
            logger.error("cash_ticket_print_failed", gate_id=self.gate_id, barcode=barcode, error=str(e))

        audio_cfg = self.hw.get("audio", {})
        if not print_success:
            await self._send_controller_command(cmd_ds("CATAT NOMOR:", barcode))
            await self.publish_event(BaseEvent(event_type="print_failed_alert", gate_id=self.gate_id))
            await asyncio.sleep(3)
            if audio_cfg.get("enabled", True):
                await self._cmd_play_audio(audio_cfg.get("error_track", 11))
        else:
            if audio_cfg.get("enabled", True):
                await self._cmd_play_audio(audio_cfg.get("ticket_track", 2))

        await self._cmd_open_gate()

    async def _cmd_check_balance(self, minimum_threshold: int) -> None:
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
                        await self._display("Saldo Tidak Cukup", f"Rp {balance:,}")
                        await self._cmd_play_audio(6)
                        await self._transition(STATE_IDLE)
                    else:
                        await self._transition(STATE_WAITING_PRINT_DECISION)
                        await self._display("Cetak Tiket?", "Tekan Tombol")
                        timeout = self.hw.get("emoney", {}).get("print_decision_timeout_seconds", 10)
                        await self._start_print_decision_timer(timeout)
                else:
                    await self._display("Kartu Error", "Coba Lagi")
                    await self._transition(STATE_IDLE)
            else:
                await self._display("Error", result.get("status_msg", ""))
                await self._transition(STATE_IDLE)
        except Exception as e:
            logger.error("check_balance_error", gate_id=self.gate_id, error=str(e))
            await self._transition(STATE_IDLE)

    async def _cmd_reject_card(self, line1: str, line2: str, audio_track: int, display_seconds: float) -> None:
        """Show rejection message then return to WAITING_INPUT — driver can retry immediately."""
        if self._validating_task and not self._validating_task.done():
            self._validating_task.cancel()
        await self._display(line1, line2)
        await self._cmd_play_audio(audio_track)
        await asyncio.sleep(display_seconds)
        await self._transition(STATE_WAITING_INPUT)
        await self._display("Selamat Datang", "Tombol/Tempel Kartu")
        if self.has_emoney:
            asyncio.create_task(self._passti_poll_loop(), name="passti_poll")

    async def _cmd_reset_gate(self, reason: str) -> None:
        logger.info("reset_gate", gate_id=self.gate_id, reason=reason)
        await self._transition(STATE_IDLE)
        await self._display()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _rfid_serial_reader_task(self) -> None:
        """Read card numbers from a directly-connected serial RFID reader."""
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
                    if card_number and self.state == STATE_WAITING_INPUT and self.has_rfid:
                        await self._on_rfid_card_read(card_number, "S")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error("rfid_serial_read_error", gate_id=self.gate_id, error=str(e))
                    await asyncio.sleep(1)
        finally:
            ser.close()

    async def _send_controller_command(self, command: bytes) -> None:
        if self.controller and self.controller.is_connected():
            try:
                async with self._controller_lock:
                    self.controller.send(command)
                logger.debug("controller_cmd_sent", gate_id=self.gate_id, cmd=command.hex())
            except Exception as e:
                logger.error("controller_cmd_error", gate_id=self.gate_id, error=str(e))

    @staticmethod
    def _card_type_name(code: int) -> str:
        from protocols.passti.frame import CARD_TYPES
        return CARD_TYPES.get(code, f"Unknown({code:02X})")
