"""E2E orchestration tests for gate-out daemon with TCP simulators."""

import asyncio

import pytest

from daemons.gate_out import GateOutDaemon
from tests.e2e.conftest import GateOrchestrator


async def _wait_for_state(daemon, target_states, timeout=5.0):
    """Poll daemon state until it matches one of target_states."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if daemon.state in target_states:
            return
        await asyncio.sleep(0.1)
    raise TimeoutError(f"State never reached {target_states}, stuck at {daemon.state}")


@pytest.mark.asyncio
async def test_gate_out_cash_payment_command(controller_sim, redis_client):
    """End-to-end: vehicle detected → cash payment command → gate opens."""
    gate_id = "e2e-gout-cash-1"
    await redis_client.delete(f"daemon:state:{gate_id}")
    await redis_client.delete(f"parking.commands.{gate_id}")
    await redis_client.delete(f"parking.events:{gate_id}")

    config = {
        "controller_host": controller_sim.host,
        "controller_port": controller_sim.port,
        "payment_timeout_seconds": 120,
        "has_close_sensor": True,
        "gate_close_duration_ms": 500,
    }
    daemon = GateOutDaemon(gate_id=gate_id, config=config)
    orch = GateOrchestrator(daemon, controller_sim)

    published_events = []
    original_publish = daemon.publish_event

    async def capture_publish(event):
        published_events.append(event)
        await original_publish(event)

    daemon.publish_event = capture_publish

    await orch.start()

    try:
        # Vehicle arrives
        controller_sim.set_in1(True)
        await _wait_for_state(daemon, ("WAITING_PAYMENT",))

        # Publish cash payment confirmed command from "POS"
        await redis_client.xadd(
            f"parking.commands.{gate_id}",
            {
                "command_type": "cash_payment_confirmed",
                "gate_id": gate_id,
                "transaction_id": "test-tx-123",
            },
        )

        # Wait for pos task to win and daemon to process it
        await asyncio.sleep(0.5)

        # FastAPI would then send open_gate command
        await redis_client.xadd(
            f"parking.commands.{gate_id}",
            {
                "command_type": "open_gate",
                "gate_id": gate_id,
            },
        )

        await asyncio.sleep(0.3)

        commands = controller_sim.get_command_log()
        assert any(b"TRIG1" in c for c in commands), f"Expected TRIG1 (open gate) in {commands}"

        event_types = [e.event_type for e in published_events]
        assert "vehicle_detected" in event_types, f"Expected vehicle_detected event, got {event_types}"
    finally:
        await orch.stop()
        await redis_client.delete(f"daemon:state:{gate_id}")
        await redis_client.delete(f"parking.commands.{gate_id}")
        await redis_client.delete(f"parking.events:{gate_id}")


@pytest.mark.asyncio
async def test_gate_out_rfid_card_read(controller_sim, redis_client):
    """End-to-end: vehicle detected → RFID card read → event published."""
    gate_id = "e2e-gout-rfid-1"
    await redis_client.delete(f"daemon:state:{gate_id}")
    await redis_client.delete(f"parking.commands.{gate_id}")
    await redis_client.delete(f"parking.events:{gate_id}")

    config = {
        "controller_host": controller_sim.host,
        "controller_port": controller_sim.port,
        "payment_timeout_seconds": 120,
        "has_close_sensor": True,
        "gate_close_duration_ms": 500,
    }
    daemon = GateOutDaemon(gate_id=gate_id, config=config)
    orch = GateOrchestrator(daemon, controller_sim)

    published_events = []
    original_publish = daemon.publish_event

    async def capture_publish(event):
        published_events.append(event)
        await original_publish(event)

    daemon.publish_event = capture_publish

    await orch.start()

    try:
        # Vehicle arrives
        controller_sim.set_in1(True)
        await _wait_for_state(daemon, ("WAITING_PAYMENT",))

        # RFID card presented (hold in simulator so multiple STAT polls can see it)
        controller_sim.inject_wiegand("AABBCCDD", channel="W")
        await asyncio.sleep(0.5)

        # FastAPI would validate member and send open_gate
        await redis_client.xadd(
            f"parking.commands.{gate_id}",
            {
                "command_type": "open_gate",
                "gate_id": gate_id,
            },
        )
        await asyncio.sleep(0.3)

        commands = controller_sim.get_command_log()
        assert any(b"TRIG1" in c for c in commands), f"Expected TRIG1 (open gate) in {commands}"

        event_types = [e.event_type for e in published_events]
        assert "vehicle_detected" in event_types, f"Expected vehicle_detected event, got {event_types}"
        assert "rfid_card_read" in event_types, f"Expected rfid_card_read event, got {event_types}"
    finally:
        await orch.stop()
        await redis_client.delete(f"daemon:state:{gate_id}")
        await redis_client.delete(f"parking.commands.{gate_id}")
        await redis_client.delete(f"parking.events:{gate_id}")


@pytest.mark.asyncio
async def test_gate_out_emoney_tap(controller_sim, passti_sim, redis_client):
    """End-to-end: vehicle detected → PASSTI tap → card tap event published."""
    gate_id = "e2e-gout-emoney-1"
    await redis_client.delete(f"daemon:state:{gate_id}")
    await redis_client.delete(f"parking.commands.{gate_id}")
    await redis_client.delete(f"parking.events:{gate_id}")

    config = {
        "controller_host": controller_sim.host,
        "controller_port": controller_sim.port,
        "payment_timeout_seconds": 120,
        "has_close_sensor": True,
        "gate_close_duration_ms": 500,
        "emoney_reader_id": 1,
        "emoney_reader_host": passti_sim.host,
        "emoney_reader_port": passti_sim.port,
    }
    daemon = GateOutDaemon(gate_id=gate_id, config=config)
    orch = GateOrchestrator(daemon, controller_sim, passti_sim)

    published_events = []
    original_publish = daemon.publish_event

    async def capture_publish(event):
        published_events.append(event)
        await original_publish(event)

    daemon.publish_event = capture_publish

    await orch.start()

    try:
        # Vehicle arrives
        controller_sim.set_in1(True)
        await _wait_for_state(daemon, ("WAITING_PAYMENT",))
        # Give time for PASSTI polling to detect card
        await asyncio.sleep(0.5)

        # E-money flow publishes passti_card_tap event; FastAPI sends deduct then open_gate
        event_types = [e.event_type for e in published_events]
        assert "vehicle_detected" in event_types, f"Expected vehicle_detected event, got {event_types}"
    finally:
        await orch.stop()
        await redis_client.delete(f"daemon:state:{gate_id}")
        await redis_client.delete(f"parking.commands.{gate_id}")
        await redis_client.delete(f"parking.events:{gate_id}")


@pytest.mark.asyncio
async def test_gate_out_timeout_alert(controller_sim, redis_client):
    """End-to-end: vehicle detected → timeout → alert event published."""
    gate_id = "e2e-gout-timeout-1"
    await redis_client.delete(f"daemon:state:{gate_id}")
    await redis_client.delete(f"parking.commands.{gate_id}")
    await redis_client.delete(f"parking.events:{gate_id}")

    # Short timeout for faster test
    config = {
        "controller_host": controller_sim.host,
        "controller_port": controller_sim.port,
        "payment_timeout_seconds": 2,
        "has_close_sensor": True,
        "gate_close_duration_ms": 500,
    }
    daemon = GateOutDaemon(gate_id=gate_id, config=config)
    orch = GateOrchestrator(daemon, controller_sim)

    published_events = []
    original_publish = daemon.publish_event

    async def capture_publish(event):
        published_events.append(event)
        await original_publish(event)

    daemon.publish_event = capture_publish

    await orch.start()

    try:
        # Vehicle arrives
        controller_sim.set_in1(True)
        await _wait_for_state(daemon, ("WAITING_PAYMENT",))

        # Wait for timeout alert (2s timeout + 1s buffer)
        await asyncio.sleep(3.5)

        event_types = [e.event_type for e in published_events]
        assert "vehicle_detected" in event_types, f"Expected vehicle_detected event, got {event_types}"
        assert "timeout_alert" in event_types, f"Expected timeout_alert event, got {event_types}"
    finally:
        await orch.stop()
        await redis_client.delete(f"daemon:state:{gate_id}")
        await redis_client.delete(f"parking.commands.{gate_id}")
        await redis_client.delete(f"parking.events:{gate_id}")
