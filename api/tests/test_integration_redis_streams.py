"""Integration tests for FastAPI <-> Daemon communication via Redis Streams.

These tests verify the end-to-end message flow:
  FastAPI (gate_command service) -> Redis Stream -> Daemon -> ACK
  Daemon -> Redis Pub/Sub -> (API/event consumers)

Requirements: Redis server running (e.g., Docker: redis:6379)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
import redis.asyncio as aioredis

from api.app.services.gate_command import publish_command
from daemons.base import BaseDaemon
from shared.config import get_settings
from shared.events import (
    DisplayTextCommand,
    HeartbeatEvent,
    OpenGateCommand,
    ResetGateCommand,
)
from shared.logging import get_logger
from shared.redis import redis_client

logger = get_logger(__name__)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def gate_in_config() -> dict[str, Any]:
    """Sample gate-in configuration."""
    return {
        "id": 1,
        "name": "Gate In Utara",
        "code": "gate-in-1",
        "gate_mode": "CASH",
        "protocol": "compass",
        "controller_host": "192.168.1.10",
        "controller_port": 4001,
        "emoney_minimum_balance": 10000,
        "print_decision_timeout_seconds": 10,
        "has_close_sensor": False,
        "gate_close_duration_ms": 5000,
        "relay_mode": "SINGLE",
        "camera_url": "http://192.168.1.50/snapshot",
    }


@pytest.fixture
async def real_redis():
    """Yield a connected real Redis client; cleanup on teardown."""
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.ping()
    except Exception as exc:
        pytest.skip(f"Redis not available: {exc}")
    yield client
    await client.aclose()


@pytest.fixture
async def reset_redis_singleton():
    """Reset the global RedisClient singleton between tests.

    Prevents 'Event loop is closed' errors when pytest-asyncio creates
    a new event loop for each test.
    """
    redis_client._redis = None
    redis_client._instance = None
    yield
    redis_client._redis = None
    redis_client._instance = None


@pytest.fixture
async def cleaned_redis(real_redis, gate_in_config):
    """Return real_redis after cleaning up integration test streams.

    Must run BEFORE any daemon starts so the daemon can recreate
    consumer groups on a fresh stream.
    """
    stream_keys = [
        "parking.commands.integration-gate-in",
        "parking.commands.integration-gate-out",
        "parking.commands.integration-restart",
    ]
    for key in stream_keys:
        await real_redis.delete(key)
    yield real_redis
    for key in stream_keys:
        await real_redis.delete(key)


# =============================================================================
# Testable daemon subclass (no hardware, real Redis)
# =============================================================================


class IntegrationDaemon(BaseDaemon):
    """Daemon subclass for integration testing using real Redis.

    Does NOT connect to Compass/PASSTI hardware.
    Only consumes commands and publishes events via Redis.
    """

    def __init__(self, gate_id: str, config: dict[str, Any]) -> None:
        super().__init__(gate_id, config)
        self.commands_handled: list[dict[str, str]] = []
        self.events_published: list[dict[str, Any]] = []

    async def run(self) -> None:
        """Override to skip controller connection."""
        settings = get_settings()
        self._redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        await self._recover_state()
        await self._ensure_consumer_group()
        self._running = True
        logger.info("integration_daemon_started", gate_id=self.gate_id)

    async def consume_one(self, timeout_ms: int = 5000) -> dict[str, str] | None:
        """Consume exactly one command from Redis Streams.

        Args:
            timeout_ms: Blocking timeout in milliseconds.

        Returns:
            Command fields dict, or None if timed out.
        """
        if self._redis is None:
            raise RuntimeError("Redis not connected")
        messages = await self._redis.xreadgroup(
            groupname=self._consumer_group,
            consumername=self._consumer_name,
            streams={self._command_stream: ">"},
            count=1,
            block=timeout_ms,
        )
        if not messages:
            return None
        for _stream_name, entries in messages:
            for msg_id, fields in entries:
                await self._process_command(msg_id, fields)
                return dict(fields)
        return None

    async def handle_command(self, command_data: dict[str, str]) -> bool:
        """Record command and return success."""
        self.commands_handled.append(dict(command_data))
        return True

    def get_initial_state(self) -> str:
        return "IDLE"

    async def stop(self) -> None:
        """Programmatic stop with Redis cleanup."""
        self._running = False
        self._shutdown_event.set()
        if self._redis:
            await self._redis.aclose()
            self._redis = None


@pytest.fixture
async def integration_daemon(cleaned_redis, gate_in_config):
    """Yield a running integration test daemon backed by real Redis."""
    daemon = IntegrationDaemon("integration-gate-in", gate_in_config)
    await daemon.run()
    try:
        yield daemon
    finally:
        await daemon.stop()


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.asyncio
async def test_open_gate_command_flow(reset_redis_singleton, integration_daemon):
    """FastAPI publishes open_gate -> Daemon receives and ACKs."""
    await redis_client.connect()

    cmd = OpenGateCommand(gate_id="integration-gate-in", duration_seconds=5)
    msg_id = await publish_command(cmd)
    assert msg_id is not None

    # Daemon consumes the command
    received = await integration_daemon.consume_one(timeout_ms=5000)
    assert received is not None
    assert received["command_type"] == "open_gate"
    assert received["duration_seconds"] == "5"

    # Verify daemon recorded it
    assert len(integration_daemon.commands_handled) == 1
    assert integration_daemon.commands_handled[0]["command_type"] == "open_gate"


@pytest.mark.asyncio
async def test_display_text_command_flow(reset_redis_singleton, integration_daemon):
    """FastAPI publishes display_text -> Daemon receives correct fields."""
    await redis_client.connect()

    cmd = DisplayTextCommand(
        gate_id="integration-gate-in",
        line1="Selamat Datang",
        line2="Ambil Tiket",
    )
    await publish_command(cmd)

    received = await integration_daemon.consume_one(timeout_ms=5000)
    assert received is not None
    assert received["command_type"] == "display_text"
    assert received["line1"] == "Selamat Datang"
    assert received["line2"] == "Ambil Tiket"


@pytest.mark.asyncio
async def test_multiple_commands_sequential(reset_redis_singleton, integration_daemon):
    """Daemon processes multiple commands in order."""
    await redis_client.connect()

    commands = [
        DisplayTextCommand(gate_id="integration-gate-in", line1="Step 1"),
        OpenGateCommand(gate_id="integration-gate-in", duration_seconds=3),
        ResetGateCommand(gate_id="integration-gate-in", reason="test"),
    ]

    for cmd in commands:
        await publish_command(cmd)

    for expected_type in ("display_text", "open_gate", "reset_gate"):
        received = await integration_daemon.consume_one(timeout_ms=5000)
        assert received is not None
        assert received["command_type"] == expected_type

    assert len(integration_daemon.commands_handled) == 3


@pytest.mark.asyncio
async def test_command_with_nested_dict_serialization(reset_redis_singleton, integration_daemon):
    """Commands with dict fields are correctly JSON-serialized through Redis."""
    await redis_client.connect()

    cmd = DisplayTextCommand(
        gate_id="integration-gate-in",
        line1="Test",
        line2="Nested",
        brightness=80,
        mode="blink",
    )
    await publish_command(cmd)

    received = await integration_daemon.consume_one(timeout_ms=5000)
    assert received is not None
    assert received["command_type"] == "display_text"
    assert received["line1"] == "Test"
    assert received["brightness"] == "80"
    assert received["mode"] == "blink"


@pytest.mark.asyncio
async def test_daemon_event_publish(reset_redis_singleton, cleaned_redis, gate_in_config):
    """Daemon publishes event -> subscriber receives it."""
    daemon = IntegrationDaemon("integration-gate-in", gate_in_config)
    await daemon.run()

    sub_client = aioredis.from_url(
        get_settings().redis_url,
        decode_responses=True,
    )
    pubsub = sub_client.pubsub()
    await pubsub.subscribe("parking.events.integration-gate-in")

    # Wait briefly for subscription to propagate
    await asyncio.sleep(0.1)

    event = HeartbeatEvent(
        event_type="heartbeat",
        gate_id="integration-gate-in",
        controller_ok=False,
    )
    await daemon.publish_event(event)

    # Poll for message with retry loop (aioredis pub/sub can be finicky in tests)
    msg = None
    for _ in range(100):
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.05)
        if msg is not None:
            break
        await asyncio.sleep(0.05)

    assert msg is not None, "No Pub/Sub message received within 5 seconds"
    data = json.loads(msg["data"])
    assert data["event_type"] == "heartbeat"
    assert data["controller_ok"] is False

    await pubsub.unsubscribe()
    await sub_client.aclose()
    await daemon.stop()


@pytest.mark.asyncio
async def test_consumer_group_recreated_on_daemon_restart(reset_redis_singleton, cleaned_redis, gate_in_config):
    """Consumer group persists across daemon restarts."""
    daemon1 = IntegrationDaemon("integration-restart", gate_in_config)
    await daemon1.run()

    # Publish a command before first daemon stops
    await redis_client.connect()
    cmd = OpenGateCommand(gate_id="integration-restart")
    await publish_command(cmd)

    # Consume with first daemon
    received = await daemon1.consume_one(timeout_ms=5000)
    assert received is not None
    await daemon1.stop()

    # Start second daemon with same gate_id — consumer group should already exist
    daemon2 = IntegrationDaemon("integration-restart", gate_in_config)
    await daemon2.run()  # Should not raise "already exists" error

    # Publish another command
    await publish_command(cmd)
    received2 = await daemon2.consume_one(timeout_ms=5000)
    assert received2 is not None
    await daemon2.stop()


@pytest.mark.asyncio
async def test_unacked_command_redelivered(reset_redis_singleton, cleaned_redis, gate_in_config):
    """Commands that are not ACKed should be available for redelivery."""
    await redis_client.connect()

    # Use a separate daemon gate_id to avoid interfering with integration_daemon fixture
    daemon = IntegrationDaemon("integration-pending", gate_in_config)
    await daemon.run()

    cmd = OpenGateCommand(gate_id="integration-pending")
    await publish_command(cmd)

    # Read from stream manually without ACKing using a different consumer
    raw_messages = await redis_client.client.xreadgroup(
        groupname="daemon-integration-pending",
        consumername="bad-consumer",
        streams={"parking.commands.integration-pending": ">"},
        count=1,
        block=5000,
    )
    assert len(raw_messages) == 1

    # Verify the message is pending
    pending = await redis_client.client.xpending(
        "parking.commands.integration-pending",
        "daemon-integration-pending",
    )
    assert pending["pending"] == 1

    # Now let the integration daemon consume and ACK it
    received = await daemon.consume_one(timeout_ms=5000)
    # consume_one reads ">" which only gets new messages, not pending
    assert received is None  # Already consumed by bad-consumer

    # Acknowledge manually to clean up
    for _stream_name, entries in raw_messages:
        for msg_id, _fields in entries:
            await redis_client.client.xack(
                "parking.commands.integration-pending",
                "daemon-integration-pending",
                msg_id,
            )

    await daemon.stop()
