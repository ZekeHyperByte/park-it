"""Tests for daemons/gate_in.py."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from daemons.gate_in import (
    STATE_GATE_CLOSED,
    STATE_IDLE,
    STATE_OPENING,
    STATE_PROCESSING,
    STATE_VEHICLE_PRESENT,
    STATE_WAITING_BUTTON,
    STATE_WAITING_CARD,
    STATE_WAITING_PRINT_DECISION,
    GateInDaemon,
)
from shared.events import GateMode


class TestableGateInDaemon(GateInDaemon):
    """Gate-in daemon with injectable mocks for testing."""

    def __init__(
        self,
        gate_id: str,
        config: dict[str, Any],
        fake_redis: Any,
        mock_compass: Any,
        mock_passti: Any | None = None,
    ) -> None:
        super().__init__(gate_id, config)
        self._fake_redis = fake_redis
        self.controller = mock_compass
        if mock_passti:
            self.passti_transport = mock_passti

    async def run(self) -> None:
        """Override to inject fake Redis without connecting real controller."""
        self._redis = self._fake_redis
        await self._recover_state()
        await self._ensure_consumer_group()
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_controller(), name="poll")
        self._tasks.append(self._poll_task)

    async def stop(self) -> None:
        """Override to properly cancel poll task."""
        self._running = False
        self._shutdown_event.set()
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        if self._redis:
            await self._redis.close()
            self._redis = None


@pytest.fixture
def gate_in_daemon(
    fake_redis, gate_in_config, mock_compass, mock_passti
) -> TestableGateInDaemon:
    return TestableGateInDaemon(
        "gate-in-1", gate_in_config, fake_redis, mock_compass, mock_passti
    )


class TestGateInCashMode:
    """Test gate-in CASH mode flow."""

    @pytest.mark.asyncio
    async def test_idle_to_vehicle_present(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """IN1 ON transitions IDLE → VEHICLE_PRESENT."""
        gate_in_daemon.gate_mode = GateMode.CASH.value
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        gate_in_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(0.2)

        assert gate_in_daemon.state == STATE_VEHICLE_PRESENT
        # Should have sent close gate command
        assert any(b"TRIG" in cmd for cmd in gate_in_daemon.controller.sent_commands)

    @pytest.mark.asyncio
    async def test_vehicle_present_to_gate_closed(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """After close timer, transitions to GATE_CLOSED → WAITING_BUTTON."""
        gate_in_daemon.gate_mode = GateMode.CASH.value
        gate_in_daemon.config["has_close_sensor"] = False
        gate_in_daemon.config["gate_close_duration_ms"] = 100
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        gate_in_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(0.3)

        assert gate_in_daemon.state == STATE_WAITING_BUTTON

    @pytest.mark.asyncio
    async def test_waiting_button_to_processing(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """IN2 ON in WAITING_BUTTON transitions to PROCESSING and publishes event."""
        gate_in_daemon.gate_mode = GateMode.CASH.value
        gate_in_daemon.config["has_close_sensor"] = False
        gate_in_daemon.config["gate_close_duration_ms"] = 50
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        # Simulate vehicle present + gate closed
        gate_in_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(0.15)
        assert gate_in_daemon.state == STATE_WAITING_BUTTON

        # Simulate ticket button press
        gate_in_daemon.controller.inject_stat_in2_on()
        await asyncio.sleep(0.15)

        assert gate_in_daemon.state == STATE_PROCESSING
        events = gate_in_daemon._fake_redis.pubsub.get("parking.events.gate-in-1", [])
        assert any(
            json.loads(e)["event_type"] == "ticket_button_pressed"
            for e in events
        )

    @pytest.mark.asyncio
    async def test_open_gate_command(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """open_gate command transitions to OPENING."""
        gate_in_daemon.gate_mode = GateMode.CASH.value
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        await gate_in_daemon.handle_command({
            "command_type": "open_gate",
            "gate_id": "gate-in-1",
        })

        assert gate_in_daemon.state == STATE_OPENING
        assert any(b"TRIG1" in cmd for cmd in gate_in_daemon.controller.sent_commands)


class TestGateInRfidMode:
    """Test gate-in RFID mode flow."""

    @pytest.mark.asyncio
    async def test_waiting_card_detects_rfid(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """Wiegand W read in WAITING_CARD publishes rfid_card_read event."""
        gate_in_daemon.gate_mode = GateMode.RFID.value
        gate_in_daemon.config["has_close_sensor"] = False
        gate_in_daemon.config["gate_close_duration_ms"] = 50
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        # Vehicle present → gate closed → waiting card
        gate_in_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(0.15)
        assert gate_in_daemon.state == STATE_WAITING_CARD

        # RFID card read
        gate_in_daemon.controller.inject_stat_wiegand_w("A1B2C3D4")
        await asyncio.sleep(0.15)

        events = gate_in_daemon._fake_redis.pubsub.get("parking.events.gate-in-1", [])
        rfid_events = [
            json.loads(e) for e in events
            if json.loads(e)["event_type"] == "rfid_card_read"
        ]
        assert len(rfid_events) == 1
        assert rfid_events[0]["card_number"] == "2712847316"
        assert rfid_events[0]["channel"] == "W"


class TestGateInEmoneyMode:
    """Test gate-in E-Money mode flow."""

    @pytest.mark.asyncio
    async def test_passti_tap_publishes_event(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """PASSTI card tap publishes passti_card_tap event."""
        gate_in_daemon.gate_mode = GateMode.EMONEY.value
        gate_in_daemon.config["has_close_sensor"] = False
        gate_in_daemon.config["gate_close_duration_ms"] = 50
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        # Vehicle present → gate closed → waiting card
        gate_in_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(0.15)
        assert gate_in_daemon.state == STATE_WAITING_CARD

        # Inject PASSTI check balance response
        gate_in_daemon.passti_transport.inject_check_balance("1234567890ABCDEF", 50000)
        await asyncio.sleep(0.3)

        events = gate_in_daemon._fake_redis.pubsub.get("parking.events.gate-in-1", [])
        passti_events = [
            json.loads(e) for e in events
            if json.loads(e)["event_type"] == "passti_card_tap"
        ]
        assert len(passti_events) == 1
        assert passti_events[0]["card_number"] == "1234567890ABCDEF"

    @pytest.mark.asyncio
    async def test_check_balance_command_insufficient(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """check_balance command with insufficient balance returns to IDLE."""
        gate_in_daemon.gate_mode = GateMode.EMONEY.value
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        gate_in_daemon.passti_transport.inject_insufficient_balance()
        await gate_in_daemon.handle_command({
            "command_type": "check_balance",
            "minimum_threshold": "20000",
            "gate_id": "gate-in-1",
        })

        assert gate_in_daemon.state == STATE_IDLE
        # Should display insufficient balance
        assert any(b"Saldo Tidak Cukup" in cmd for cmd in gate_in_daemon.controller.sent_commands)

    @pytest.mark.asyncio
    async def test_check_balance_command_sufficient(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """check_balance command with sufficient balance goes to WAITING_PRINT_DECISION."""
        gate_in_daemon.gate_mode = GateMode.EMONEY.value
        gate_in_daemon.config["print_decision_timeout_seconds"] = 1
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        gate_in_daemon.passti_transport.inject_check_balance("1234567890ABCDEF", 50000)
        await gate_in_daemon.handle_command({
            "command_type": "check_balance",
            "minimum_threshold": "10000",
            "gate_id": "gate-in-1",
        })

        assert gate_in_daemon.state == STATE_WAITING_PRINT_DECISION
        # Timer will expire and go to PROCESSING
        await asyncio.sleep(1.5)
        assert gate_in_daemon.state == STATE_PROCESSING


class TestGateInCommands:
    """Test command handlers."""

    @pytest.mark.asyncio
    async def test_play_audio_command(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """play_audio command sends MT to controller."""
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        await gate_in_daemon.handle_command({
            "command_type": "play_audio",
            "track": "7",
            "gate_id": "gate-in-1",
        })

        assert any(b"MT00007" in cmd for cmd in gate_in_daemon.controller.sent_commands)

    @pytest.mark.asyncio
    async def test_display_text_command(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """display_text command sends DS to controller."""
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        await gate_in_daemon.handle_command({
            "command_type": "display_text",
            "line1": "Hello",
            "line2": "World",
            "gate_id": "gate-in-1",
        })

        assert any(b"Hello" in cmd for cmd in gate_in_daemon.controller.sent_commands)

    @pytest.mark.asyncio
    async def test_reset_gate_command(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """reset_gate command returns to IDLE."""
        gate_in_daemon.state = STATE_PROCESSING
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        await gate_in_daemon.handle_command({
            "command_type": "reset_gate",
            "reason": "test",
            "gate_id": "gate-in-1",
        })

        assert gate_in_daemon.state == STATE_IDLE

    @pytest.mark.asyncio
    async def test_close_gate_dual_relay(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """close_gate command sends TRIG2 in DUAL mode."""
        gate_in_daemon.config["relay_mode"] = "DUAL"
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        await gate_in_daemon.handle_command({
            "command_type": "close_gate",
            "gate_id": "gate-in-1",
        })

        assert any(b"TRIG2" in cmd for cmd in gate_in_daemon.controller.sent_commands)

    @pytest.mark.asyncio
    async def test_unknown_command_returns_true(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """Unknown commands are ACKed (not retried)."""
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        result = await gate_in_daemon.handle_command({
            "command_type": "foo_bar",
            "gate_id": "gate-in-1",
        })

        assert result is True

    @pytest.mark.asyncio
    async def test_deduct_command_ignored(self, gate_in_daemon: TestableGateInDaemon) -> None:
        """deduct command is ignored at gate-in."""
        await gate_in_daemon.run()
        await asyncio.sleep(0.05)

        result = await gate_in_daemon.handle_command({
            "command_type": "deduct",
            "amount": "5000",
            "gate_id": "gate-in-1",
        })

        assert result is True  # Still ACKed so it's not retried
