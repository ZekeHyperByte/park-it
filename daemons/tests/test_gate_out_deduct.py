"""Tests for DeductCommand handler in gate-out daemon."""

from __future__ import annotations

import asyncio
import json

import pytest

from daemons.tests.test_gate_out import TestableGateOutDaemon


@pytest.fixture
def gate_out_daemon_no_passti(fake_redis, gate_out_config, mock_compass) -> TestableGateOutDaemon:
    """Gate-out daemon without PASSTI transport (manless not enabled)."""
    return TestableGateOutDaemon(
        "gate-out-1", gate_out_config, fake_redis, mock_compass, mock_passti=None
    )


@pytest.fixture
def gate_out_daemon_with_passti(fake_redis, gate_out_config, mock_compass, mock_passti) -> TestableGateOutDaemon:
    """Gate-out daemon with mocked PASSTI transport."""
    return TestableGateOutDaemon(
        "gate-out-1", gate_out_config, fake_redis, mock_compass, mock_passti
    )


class TestDeductCommand:
    """Test DeductCommand handler for manless e-money passthrough."""

    @pytest.mark.asyncio
    async def test_deduct_no_transport_publishes_failed(self, gate_out_daemon_no_passti: TestableGateOutDaemon) -> None:
        """DeductCommand without passti_transport publishes FAILED event."""
        await gate_out_daemon_no_passti.run()
        await asyncio.sleep(0.05)

        await gate_out_daemon_no_passti.handle_command({
            "command_type": "deduct",
            "amount": "5000",
            "timeout_seconds": "10",
            "expected_card_number": "1234567890ABCDEF",
            "expected_transaction_counter": "41",
            "gate_id": "gate-out-1",
        })

        events = gate_out_daemon_no_passti._fake_redis.pubsub.get("parking.events.gate-out-1", [])
        deduct_events = [
            json.loads(e) for e in events
            if json.loads(e)["event_type"] == "deduct_result"
        ]
        assert len(deduct_events) == 1
        assert deduct_events[0]["status"] == "FAILED"
        assert deduct_events[0]["deduct_amount"] == 5000

    @pytest.mark.asyncio
    async def test_deduct_success_publishes_result(self, gate_out_daemon_with_passti: TestableGateOutDaemon) -> None:
        """DeductCommand with successful response publishes SUCCESS event."""
        await gate_out_daemon_with_passti.run()
        await asyncio.sleep(0.05)

        gate_out_daemon_with_passti.passti_transport.inject_deduct_success(
            card_number="1234567890ABCDEF",
            deducted=5000,
            remaining=45000,
            trans_counter=42,
        )
        await gate_out_daemon_with_passti.handle_command({
            "command_type": "deduct",
            "amount": "5000",
            "timeout_seconds": "10",
            "expected_card_number": "1234567890ABCDEF",
            "expected_transaction_counter": "41",
            "gate_id": "gate-out-1",
        })

        events = gate_out_daemon_with_passti._fake_redis.pubsub.get("parking.events.gate-out-1", [])
        deduct_events = [
            json.loads(e) for e in events
            if json.loads(e)["event_type"] == "deduct_result"
        ]
        assert len(deduct_events) == 1
        assert deduct_events[0]["status"] == "SUCCESS"
        assert deduct_events[0]["deduct_amount"] == 5000
        assert deduct_events[0]["card_number"] == "1234567890ABCDEF"
        assert deduct_events[0]["balance_after"] == 45000
        assert deduct_events[0]["transaction_counter"] == 42
