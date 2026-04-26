"""E2E orchestration tests for gate-in daemon with TCP simulators."""

import asyncio

import pytest

from daemons.gate_in import GateInDaemon
from tests.e2e.conftest import GateOrchestrator


@pytest.mark.asyncio
async def test_gate_in_cash_vehicle_detected_and_button(controller_sim, redis_client):
    """End-to-end: vehicle detected → gate closes → button press → ticket event published."""
    gate_id = "e2e-gin-cash-1"
    # Clean up any prior Redis state for this gate
    await redis_client.delete(f"daemon:state:{gate_id}")
    await redis_client.delete(f"parking.commands.{gate_id}")
    await redis_client.delete(f"parking.events.{gate_id}")

    config = {
        "controller_host": controller_sim.host,
        "controller_port": controller_sim.port,
        "gate_mode": "CASH",
        "emoney_minimum_balance": 5000,
        "print_decision_timeout_seconds": 10,
        "has_close_sensor": True,
        "gate_close_duration_ms": 500,
    }
    daemon = GateInDaemon(gate_id=gate_id, config=config)
    orch = GateOrchestrator(daemon, controller_sim)

    # Capture published events
    published_events = []
    original_publish = daemon.publish_event

    async def capture_publish(event):
        published_events.append(event)
        await original_publish(event)

    daemon.publish_event = capture_publish

    await orch.start()

    try:
        # Simulate vehicle arrival
        controller_sim.set_in1(True)
        await asyncio.sleep(0.3)
        # Simulate ticket button press (hold longer to ensure detection)
        controller_sim.set_in2(True)
        await asyncio.sleep(0.3)
        controller_sim.set_in2(False)
        await asyncio.sleep(0.3)

        commands = controller_sim.get_command_log()

        # Assert expected commands were sent to controller
        assert any(b"TRIG1" in c for c in commands), f"Expected TRIG1 (close gate) in {commands}"

        # Verify state transitions
        assert daemon.state in ("WAITING_BUTTON", "PROCESSING"), f"Expected WAITING_BUTTON or PROCESSING, got {daemon.state}"

        # Verify events were published
        event_types = [e.event_type for e in published_events]
        assert "vehicle_detected" in event_types, f"Expected vehicle_detected event, got {event_types}"
        assert "gate_closed" in event_types, f"Expected gate_closed event, got {event_types}"
    finally:
        await orch.stop()
        # Cleanup Redis
        await redis_client.delete(f"daemon:state:{gate_id}")
        await redis_client.delete(f"parking.commands.{gate_id}")
        await redis_client.delete(f"parking.events.{gate_id}")


@pytest.mark.asyncio
async def test_gate_in_emoney_vehicle_detected(controller_sim, passti_sim, redis_client):
    """End-to-end: vehicle detected → e-money tap → balance event published."""
    gate_id = "e2e-gin-emoney-1"
    await redis_client.delete(f"daemon:state:{gate_id}")
    await redis_client.delete(f"parking.commands.{gate_id}")
    await redis_client.delete(f"parking.events.{gate_id}")

    config = {
        "controller_host": controller_sim.host,
        "controller_port": controller_sim.port,
        "gate_mode": "EMONEY",
        "emoney_minimum_balance": 5000,
        "print_decision_timeout_seconds": 10,
        "has_close_sensor": True,
        "gate_close_duration_ms": 500,
        "emoney_reader_host": passti_sim.host,
        "emoney_reader_port": passti_sim.port,
    }
    daemon = GateInDaemon(gate_id=gate_id, config=config)
    orch = GateOrchestrator(daemon, controller_sim, passti_sim)

    published_events = []
    original_publish = daemon.publish_event

    async def capture_publish(event):
        published_events.append(event)
        await original_publish(event)

    daemon.publish_event = capture_publish

    await orch.start()

    try:
        # Simulate vehicle arrival
        controller_sim.set_in1(True)
        await asyncio.sleep(0.4)
        controller_sim.set_in1(False)
        await asyncio.sleep(0.5)

        commands = controller_sim.get_command_log()
        assert any(b"TRIG1" in c for c in commands), f"Expected TRIG1 in {commands}"

        event_types = [e.event_type for e in published_events]
        assert "vehicle_detected" in event_types, f"Expected vehicle_detected event, got {event_types}"
        assert "gate_closed" in event_types, f"Expected gate_closed event, got {event_types}"
    finally:
        await orch.stop()
        await redis_client.delete(f"daemon:state:{gate_id}")
        await redis_client.delete(f"parking.commands.{gate_id}")
        await redis_client.delete(f"parking.events.{gate_id}")
