"""Tests for the Redis Pub/Sub event consumer."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.app.services.event_consumer import EventConsumer


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


