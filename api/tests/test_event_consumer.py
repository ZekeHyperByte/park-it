"""Tests for the Redis Pub/Sub event consumer."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.app.services.event_consumer import EventConsumer
from shared.events import DeductStatus


class MockPubSub:
    """Mock aioredis pub/sub for testing."""

    def __init__(self, messages=None):
        self.messages = messages or []
        self.psubscribe_called = False
        self.punsubscribe_called = False
        self.closed = False
        self.pattern = None

    async def psubscribe(self, *args):
        self.psubscribe_called = True
        self.pattern = args[0] if args else None

    async def punsubscribe(self, *args):
        self.punsubscribe_called = True

    async def close(self):
        self.closed = True

    async def listen(self):
        for msg in self.messages:
            yield msg
        # Block until cancelled so the consumer task stays alive
        while True:
            await asyncio.sleep(0.05)


def _make_mock_redis_client(mock_pubsub):
    """Build a mock redis_client with async connect and a pubsub factory."""
    mock_redis = MagicMock()
    mock_redis.pubsub.return_value = mock_pubsub

    mock_rc = MagicMock()
    mock_rc.connect = AsyncMock()
    mock_rc.client = mock_redis
    return mock_rc


@pytest.mark.asyncio
async def test_event_consumer_subscribes_to_redis():
    """EventConsumer should psubscribe to parking.events.* on start."""
    mock_pubsub = MockPubSub()
    mock_rc = _make_mock_redis_client(mock_pubsub)

    with patch("api.app.services.event_consumer.redis_client", mock_rc):
        consumer = EventConsumer()
        await consumer.start()
        # Give the task a moment to reach psubscribe
        await asyncio.sleep(0.1)

        assert mock_pubsub.psubscribe_called is True
        assert mock_pubsub.pattern == "parking.events.*"
        assert mock_rc.connect.called is True

        await consumer.stop()
        assert mock_pubsub.punsubscribe_called is True
        assert mock_pubsub.closed is True


@pytest.mark.asyncio
async def test_deduct_result_triggers_process_emoney_result():
    """A deduct_result event should call process_emoney_result with parsed data."""
    event_payload = {
        "event_type": "deduct_result",
        "gate_id": "GOUT01",
        "status": DeductStatus.SUCCESS.value,
        "card_number": "1234567890",
        "card_type": "FLAZZ",
        "deduct_amount": 5000,
        "balance_before": 50000,
        "balance_after": 45000,
        "transaction_counter": 7,
        "raw_response_hex": "EF0105...",
    }

    mock_pubsub = MockPubSub(
        messages=[
            {
                "type": "pmessage",
                "channel": "parking.events.GOUT01",
                "data": json.dumps(event_payload),
            }
        ]
    )
    mock_rc = _make_mock_redis_client(mock_pubsub)

    # Mock DB session + gate lookup
    mock_gate = MagicMock()
    mock_gate.id = 42

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_gate

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_session
    mock_session_ctx.__aexit__.return_value = None

    with patch("api.app.services.event_consumer.redis_client", mock_rc):
        with patch(
            "api.database.AsyncSessionLocal",
            return_value=mock_session_ctx,
        ):
            with patch(
                "api.app.services.payment.process_emoney_result",
                new_callable=AsyncMock,
            ) as mock_process:
                consumer = EventConsumer()
                await consumer.start()
                # Allow time for the message to be processed
                await asyncio.sleep(0.2)
                await consumer.stop()

    mock_process.assert_awaited_once()
    call_kwargs = mock_process.await_args.kwargs
    assert call_kwargs["gate_id"] == "GOUT01"
    assert call_kwargs["gate_out_id"] == 42
    assert call_kwargs["card_number"] == "1234567890"
    assert call_kwargs["status"] == DeductStatus.SUCCESS
    assert call_kwargs["deduct_amount"] == 5000
    assert call_kwargs["balance_before"] == 50000
    assert call_kwargs["balance_after"] == 45000
    assert call_kwargs["transaction_counter"] == 7
    assert call_kwargs["raw_response_hex"] == "EF0105..."
