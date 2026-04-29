"""E2E tests for e-money entry flow."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from daemons.gate_in import GateInDaemon
from shared.events import EmoneyPrintDecisionEvent, OpenGateCommand


@pytest.mark.asyncio
async def test_gate_in_emoney_print_decision_publishes_event(redis_client):
    """GateInDaemon after print decision publishes EmoneyPrintDecisionEvent to Redis."""
    gate_id = "e2e-gin-emoney-print-1"
    await redis_client.delete(f"daemon:state:{gate_id}")
    await redis_client.delete(f"parking.events.{gate_id}")

    config = {
        "controller_host": "127.0.0.1",
        "controller_port": 4001,
        "gate_mode": "EMONEY",
        "emoney_minimum_balance": 5000,
        "print_decision_timeout_seconds": 10,
        "has_close_sensor": True,
        "gate_close_duration_ms": 500,
        "hardware_config": {
            "emoney": {"enabled": True, "print_decision_timeout_seconds": 10},
            "rfid": {"enabled": False},
            "ticket_printer": {"enabled": True},
        },
    }

    daemon = GateInDaemon(gate_id=gate_id, config=config)
    daemon._redis = redis_client

    # Set state data as if card was tapped and balance checked
    daemon.state = "WAITING_PRINT_DECISION"
    daemon.state_data["passti_card_number"] = "1234567890123456"
    daemon.state_data["passti_card_type"] = "Mandiri eMoney"
    daemon.state_data["passti_balance"] = 10000

    # Subscribe to events before triggering
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"parking.events.{gate_id}")

    # Directly trigger print decision (simulating button press)
    await daemon._on_print_decision(printed=True)

    # Wait for event to propagate
    await asyncio.sleep(0.2)

    # Read published event from pub/sub (retry loop — aioredis pub/sub can be finicky in tests)
    msg = None
    for _ in range(100):
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.05)
        if msg is not None:
            break
        await asyncio.sleep(0.05)
    assert msg is not None, "Expected EmoneyPrintDecisionEvent to be published"
    data = json.loads(msg["data"])

    assert data["event_type"] == "emoney_print_decision"
    assert data["gate_id"] == gate_id
    assert data["printed"] is True
    assert data["card_number"] == "1234567890123456"
    assert data["card_type"] == "Mandiri eMoney"
    assert data["balance"] == 10000

    await pubsub.unsubscribe()
    await redis_client.delete(f"daemon:state:{gate_id}")
    await redis_client.delete(f"parking.events.{gate_id}")


@pytest.mark.asyncio
async def test_event_consumer_emoney_print_decision_sends_open_gate():
    """Event consumer handling emoney_print_decision creates transaction and sends OpenGateCommand."""
    from api.app.services.event_consumer import EventConsumer

    # Mock DB session and gate lookup
    mock_gate = MagicMock()
    mock_gate.id = 99

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_gate

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_session
    mock_session_ctx.__aexit__.return_value = None

    with patch("api.database.AsyncSessionLocal", return_value=mock_session_ctx):
        with patch(
            "api.app.services.transaction.create_entry_transaction",
            new_callable=AsyncMock,
        ) as mock_create_tx:
            mock_tx = MagicMock()
            mock_tx.id = 12345
            mock_create_tx.return_value = mock_tx

            with patch(
                "api.app.services.gate_command.publish_command",
                new_callable=AsyncMock,
            ) as mock_publish:
                consumer = EventConsumer()
                event = {
                    "gate_id": "GIN01",
                    "printed": True,
                    "card_number": "1234567890123456",
                    "card_type": "Mandiri eMoney",
                    "balance": 10000,
                }

                await consumer._handle_emoney_print_decision(event)

    # Assert transaction was created
    mock_create_tx.assert_awaited_once()
    call_kwargs = mock_create_tx.await_args.kwargs
    assert call_kwargs["gate_in_id"] == 99
    assert call_kwargs["card_number"] == "1234567890123456"
    assert call_kwargs["payment_method"] == "EMONEY"

    # Assert OpenGateCommand was published
    mock_publish.assert_awaited_once()
    published_cmd = mock_publish.await_args[0][0]
    assert isinstance(published_cmd, OpenGateCommand)
    assert published_cmd.gate_id == "GIN01"
