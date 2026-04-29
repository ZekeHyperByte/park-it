"""E2E tests for manless exit e-money deduct via GateOutDaemon."""

import pytest
from unittest.mock import AsyncMock

from daemons.gate_out import GateOutDaemon
from shared.events import DeductResultEvent, DeductStatus


@pytest.mark.asyncio
async def test_gate_out_deduct_command_publishes_result_event():
    """GateOutDaemon receiving DeductCommand sends PASSTI deduct and publishes DeductResultEvent."""
    gate_id = "e2e-gout-deduct-1"

    config = {
        "controller_host": "127.0.0.1",
        "controller_port": 4001,
        "payment_timeout_seconds": 120,
        "has_close_sensor": True,
        "gate_close_duration_ms": 500,
        "hardware_config": {
            "emoney": {"enabled": True},
        },
    }

    daemon = GateOutDaemon(gate_id=gate_id, config=config)

    # Mock passti_transport to return a successful deduct response
    body = (
        bytes([0x02])  # card_type_code
        + b"12345678"  # mid (8 bytes)
        + b"8765"  # tid (4 bytes)
        + bytes.fromhex("26042612000000")[:7]  # datetime (7 bytes)
        + bytes.fromhex("1234567890123456")  # card_number (8 bytes)
        + (500).to_bytes(4, "big")  # deducted = 500
        + (8700).to_bytes(4, "big")  # remaining = 8700
        + (1).to_bytes(4, "big")  # trans_counter = 1
    )

    mock_transport = AsyncMock()
    mock_transport.send_recv.return_value = {
        "ok": True,
        "body": body,
        "raw": "02002aef0103000000...",
        "status": (0x00, 0x00, 0x00),
    }
    daemon.passti_transport = mock_transport

    # Spy on publish_event
    published_events = []

    async def capture_publish(event):
        published_events.append(event)
        return 1

    daemon.publish_event = capture_publish

    # Build deduct command dict
    command_data = {
        "command_type": "deduct",
        "amount": "500",
        "expected_card_number": "1234567890123456",
    }

    # Execute
    result = await daemon.handle_command(command_data)

    # Assert command handler returned success
    assert result is True

    # 1. Sends PASSTI deduct via ControllerPassthroughTransport
    mock_transport.send_recv.assert_awaited_once()
    sent_frame = mock_transport.send_recv.await_args[0][0]
    # Frame should be a valid PASSTI deduct command
    assert sent_frame[0] == 0x02  # STX
    # Command code is at payload[2]; payload starts at index 3
    assert sent_frame[5] == 0x03  # CMD_DEDUCT

    # 2. Publishes DeductResultEvent with correct status
    assert len(published_events) == 1
    event = published_events[0]
    assert isinstance(event, DeductResultEvent)
    assert event.event_type == "deduct_result"
    assert event.gate_id == gate_id
    assert event.status == DeductStatus.SUCCESS
    assert event.card_number == "1234567890123456"
    assert event.card_type == "Mandiri eMoney"
    assert event.deduct_amount == 500
    assert event.balance_before == 9200  # 8700 + 500
    assert event.balance_after == 8700
    assert event.transaction_counter == 1
    assert event.raw_response_hex == "02002aef0103000000..."
