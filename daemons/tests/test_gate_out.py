"""Tests for daemons/gate_out.py."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from daemons.gate_out import (
    STATE_IDLE,
    STATE_OPENING,
    STATE_TIMEOUT_ALERT,
    STATE_VEHICLE_PRESENT,
    STATE_WAITING_PAYMENT,
    GateOutDaemon,
)


class TestableGateOutDaemon(GateOutDaemon):
    """Gate-out daemon with injectable mocks for testing."""

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
        if self._payment_task and not self._payment_task.done():
            for task in asyncio.all_tasks():
                if task.get_name() in ("wiegand", "passti", "pos", "timeout"):
                    task.cancel()
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
def gate_out_daemon(
    fake_redis, gate_out_config, mock_compass, mock_passti
) -> TestableGateOutDaemon:
    return TestableGateOutDaemon(
        "gate-out-1", gate_out_config, fake_redis, mock_compass, mock_passti
    )


class TestGateOutVehicleDetection:
    """Test vehicle detection and debounce."""

    @pytest.mark.asyncio
    async def test_debounce_before_vehicle_present(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """Vehicle must be present for 500ms before state changes."""
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        gate_out_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(0.2)

        # Should still be IDLE during debounce
        assert gate_out_daemon.state == STATE_IDLE

        await asyncio.sleep(0.4)
        # After 500ms debounce + some margin
        assert gate_out_daemon.state == STATE_VEHICLE_PRESENT

    @pytest.mark.asyncio
    async def test_vehicle_present_publishes_event(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """Vehicle detection publishes vehicle_detected event."""
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        gate_out_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(0.7)

        events = gate_out_daemon._fake_redis.pubsub.get("parking.events.gate-out-1", [])
        detected = [json.loads(e) for e in events if json.loads(e)["event_type"] == "vehicle_detected"]
        assert len(detected) == 1


class TestGateOutCashFlow:
    """Test cash payment exit flow."""

    @pytest.mark.asyncio
    async def test_cash_payment_confirmed(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """cash_payment_confirmed command resolves payment and opens gate."""
        gate_out_daemon.config["payment_timeout_seconds"] = 5
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        # Trigger vehicle detection
        gate_out_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(1.0)
        assert gate_out_daemon.state == STATE_WAITING_PAYMENT

        # Simulate POS cash confirmation
        await gate_out_daemon.handle_command({
            "command_type": "cash_payment_confirmed",
            "transaction_id": "txn-123",
            "gate_id": "gate-out-1",
        })

        # Wait for payment resolution
        await asyncio.sleep(0.5)

        # FastAPI then sends open_gate command
        await gate_out_daemon.handle_command({
            "command_type": "open_gate",
            "gate_id": "gate-out-1",
        })

        assert gate_out_daemon.state == STATE_OPENING
        assert any(b"TRIG1" in cmd for cmd in gate_out_daemon.controller.sent_commands)


class TestGateOutRfidFlow:
    """Test RFID payment exit flow."""

    @pytest.mark.asyncio
    async def test_rfid_card_resolves_payment(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """Wiegand card read resolves payment."""
        gate_out_daemon.config["payment_timeout_seconds"] = 5
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        # Trigger vehicle detection
        gate_out_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(1.0)
        assert gate_out_daemon.state == STATE_WAITING_PAYMENT

        # Inject RFID card read
        gate_out_daemon.controller.inject_stat_wiegand_w("A1B2C3D4")
        await asyncio.sleep(0.5)

        # Should have published rfid_card_read event
        events = gate_out_daemon._fake_redis.pubsub.get("parking.events.gate-out-1", [])
        rfid_events = [
            json.loads(e) for e in events
            if json.loads(e)["event_type"] == "rfid_card_read"
        ]
        assert len(rfid_events) == 1
        assert rfid_events[0]["card_number"] == "2712847316"


class TestGateOutEmoneyFlow:
    """Test E-Money payment exit flow."""

    @pytest.mark.asyncio
    async def test_passti_tap_resolves_payment(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """PASSTI card tap resolves payment."""
        gate_out_daemon.config["payment_timeout_seconds"] = 5
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        # Trigger vehicle detection
        gate_out_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(1.0)
        assert gate_out_daemon.state == STATE_WAITING_PAYMENT

        # Inject PASSTI response
        gate_out_daemon.passti_transport.inject_check_balance("1234567890ABCDEF", 50000)
        await asyncio.sleep(1.0)

        # Should have published passti_card_tap event
        events = gate_out_daemon._fake_redis.pubsub.get("parking.events.gate-out-1", [])
        passti_events = [
            json.loads(e) for e in events
            if json.loads(e)["event_type"] == "passti_card_tap"
        ]
        assert len(passti_events) == 1

    @pytest.mark.asyncio
    async def test_deduct_command_publishes_result(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """deduct command executes PASSTI deduct and publishes deduct_result."""
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        gate_out_daemon.passti_transport.inject_deduct_success(
            card_number="1234567890ABCDEF",
            deducted=5000,
            remaining=45000,
            trans_counter=42,
        )
        await gate_out_daemon.handle_command({
            "command_type": "deduct",
            "amount": "5000",
            "timeout_seconds": "10",
            "expected_card_number": "1234567890ABCDEF",
            "expected_transaction_counter": "41",
            "gate_id": "gate-out-1",
        })

        events = gate_out_daemon._fake_redis.pubsub.get("parking.events.gate-out-1", [])
        deduct_events = [
            json.loads(e) for e in events
            if json.loads(e)["event_type"] == "deduct_result"
        ]
        assert len(deduct_events) == 1
        assert deduct_events[0]["status"] == "SUCCESS"
        assert deduct_events[0]["deduct_amount"] == 5000

    @pytest.mark.asyncio
    async def test_deduct_insufficient_balance(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """deduct with insufficient balance publishes correct status."""
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        gate_out_daemon.passti_transport.inject_response({
            "ok": False,
            "resp_code": 0x00,
            "status": (0x01, 0x10, 0x04),
            "status_msg": "Insufficient balance",
            "body": b"",
        })
        await gate_out_daemon.handle_command({
            "command_type": "deduct",
            "amount": "5000",
            "timeout_seconds": "10",
            "expected_card_number": "1234567890ABCDEF",
            "expected_transaction_counter": "41",
            "gate_id": "gate-out-1",
        })

        events = gate_out_daemon._fake_redis.pubsub.get("parking.events.gate-out-1", [])
        deduct_events = [
            json.loads(e) for e in events
            if json.loads(e)["event_type"] == "deduct_result"
        ]
        assert len(deduct_events) == 1
        assert deduct_events[0]["status"] == "INSUFFICIENT_BALANCE"


class TestGateOutTimeout:
    """Test timeout alert flow."""

    @pytest.mark.asyncio
    async def test_payment_timeout(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """Payment timeout transitions to TIMEOUT_ALERT."""
        gate_out_daemon.config["payment_timeout_seconds"] = 1
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        # Trigger vehicle detection
        gate_out_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(1.0)
        assert gate_out_daemon.state == STATE_WAITING_PAYMENT

        # Wait for timeout
        await asyncio.sleep(1.5)
        assert gate_out_daemon.state == STATE_TIMEOUT_ALERT

        # Should have published timeout_alert event
        events = gate_out_daemon._fake_redis.pubsub.get("parking.events.gate-out-1", [])
        timeout_events = [
            json.loads(e) for e in events
            if json.loads(e)["event_type"] == "timeout_alert"
        ]
        assert len(timeout_events) == 1

    @pytest.mark.asyncio
    async def test_timeout_vehicle_left(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """Vehicle leaving during timeout returns to IDLE."""
        gate_out_daemon.config["payment_timeout_seconds"] = 1
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        # Trigger vehicle detection and timeout
        gate_out_daemon.controller.inject_stat_in1_on()
        await asyncio.sleep(1.0)
        await asyncio.sleep(1.5)
        assert gate_out_daemon.state == STATE_TIMEOUT_ALERT

        # Vehicle leaves (IN1 OFF)
        gate_out_daemon.controller.reset()
        gate_out_daemon.controller.inject_stat_empty()
        await asyncio.sleep(0.3)

        assert gate_out_daemon.state == STATE_IDLE


class TestGateOutCommands:
    """Test command handlers."""

    @pytest.mark.asyncio
    async def test_open_gate_from_timeout(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """open_gate command from TIMEOUT_ALERT opens gate."""
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        gate_out_daemon.state = STATE_TIMEOUT_ALERT
        await gate_out_daemon.handle_command({
            "command_type": "open_gate",
            "gate_id": "gate-out-1",
        })

        assert gate_out_daemon.state == STATE_OPENING
        assert any(b"TRIG1" in cmd for cmd in gate_out_daemon.controller.sent_commands)

    @pytest.mark.asyncio
    async def test_cancel_correction_command(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """cancel_correction command sends PASSTI cancel."""
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        await gate_out_daemon.handle_command({
            "command_type": "cancel_correction",
            "gate_id": "gate-out-1",
        })

        # PASSTI transport should have received a frame
        assert len(gate_out_daemon.passti_transport.sent_frames) == 1

    @pytest.mark.asyncio
    async def test_reset_gate_cancels_payment(self, gate_out_daemon: TestableGateOutDaemon) -> None:
        """reset_gate command cancels payment tasks and returns to IDLE."""
        gate_out_daemon.config["payment_timeout_seconds"] = 10
        await gate_out_daemon.run()
        await asyncio.sleep(0.05)

        # Start a payment task manually
        gate_out_daemon.state = STATE_WAITING_PAYMENT
        gate_out_daemon._cash_payment_event.clear()
        task = asyncio.create_task(gate_out_daemon._wait_for_pos_confirm(), name="pos")

        await gate_out_daemon.handle_command({
            "command_type": "reset_gate",
            "reason": "operator_test",
            "gate_id": "gate-out-1",
        })
        await asyncio.sleep(0.1)

        assert gate_out_daemon.state == STATE_IDLE
        assert task.cancelled() or task.done()
