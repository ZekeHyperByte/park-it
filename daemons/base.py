"""Abstract base daemon for gate controllers.

Handles Redis Streams command consumption (ACK-based), Pub/Sub event publishing,
heartbeat, and state persistence/recovery.
"""

from __future__ import annotations

import asyncio
import json
import signal
import sys
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

from shared.config import get_settings
from shared.events import BaseEvent, HeartbeatEvent, RedisCommand
from shared.logging import bind_trace_id, clear_context, get_logger

logger = get_logger(__name__)


class BaseDaemon(ABC):
    """Abstract base class for gate daemons.

    Responsibilities:
    - Connect to Redis (independent connection, not shared singleton)
    - Consume commands from Redis Streams (consumer group, ACK-based)
    - Publish events to Redis Pub/Sub
    - Heartbeat every 30 seconds
    - Persist/recover state from Redis Hash
    - Graceful shutdown on SIGTERM/SIGINT
    """

    def __init__(self, gate_id: str, config: dict[str, Any]) -> None:
        """Initialize daemon.

        Args:
            gate_id: Unique gate identifier (e.g., "gate-in-1")
            config: Gate configuration dict from database (host, port, mode, etc.)
        """
        self.gate_id = gate_id
        self.config = config
        self.state: str = self.get_initial_state()
        self.state_data: dict[str, Any] = {}
        self._redis: aioredis.Redis | None = None
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._consumer_group = f"daemon-{gate_id}"
        self._consumer_name = f"{gate_id}-{uuid.uuid4().hex[:8]}"
        self._command_stream = f"parking.commands.{gate_id}"
        self._event_channel = f"parking.events.{gate_id}"
        self._state_key = f"daemon:state:{gate_id}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Main entry point. Connects to Redis, recovers state, starts loops."""
        settings = get_settings()
        self._redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )

        # Recover state from Redis
        await self._recover_state()

        # Ensure consumer group exists
        await self._ensure_consumer_group()

        self._running = True
        logger.info(
            "daemon_starting",
            gate_id=self.gate_id,
            state=self.state,
            consumer_group=self._consumer_group,
        )

        # Start concurrent tasks
        self._tasks = [
            asyncio.create_task(self._consume_commands(), name="consume"),
            asyncio.create_task(self._heartbeat(), name="heartbeat"),
        ]

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._request_shutdown)

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        # Cancel all tasks
        logger.info("daemon_shutting_down", gate_id=self.gate_id)
        for task in self._tasks:
            task.cancel()

        results = await asyncio.gather(*self._tasks, return_exceptions=True)
        for task, result in zip(self._tasks, results):
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                logger.error(
                    "daemon_task_error",
                    gate_id=self.gate_id,
                    task=task.get_name(),
                    error=str(result),
                )

        if self._redis:
            await self._redis.close()
            self._redis = None

        logger.info("daemon_stopped", gate_id=self.gate_id)

    def _request_shutdown(self) -> None:
        """Signal handler — request graceful shutdown."""
        self._running = False
        self._shutdown_event.set()

    async def stop(self) -> None:
        """Programmatic stop (for testing)."""
        self._running = False
        self._shutdown_event.set()

    # ------------------------------------------------------------------
    # Redis Streams — Command Consumption
    # ------------------------------------------------------------------

    async def _ensure_consumer_group(self) -> None:
        """Create consumer group if it doesn't exist."""
        if self._redis is None:
            raise RuntimeError("Redis not connected")
        try:
            await self._redis.xgroup_create(
                self._command_stream,
                self._consumer_group,
                id="0",  # Process from beginning if new
                mkstream=True,
            )
            logger.info(
                "consumer_group_created",
                gate_id=self.gate_id,
                group=self._consumer_group,
            )
        except aioredis.ResponseError as e:
            if "already exists" in str(e):
                logger.debug(
                    "consumer_group_exists",
                    gate_id=self.gate_id,
                    group=self._consumer_group,
                )
            else:
                raise

    async def _consume_commands(self) -> None:
        """Main command consumption loop."""
        if self._redis is None:
            raise RuntimeError("Redis not connected")

        while self._running:
            try:
                messages = await self._redis.xreadgroup(
                    groupname=self._consumer_group,
                    consumername=self._consumer_name,
                    streams={self._command_stream: ">"},
                    count=1,
                    block=5000,  # 5 second block
                )

                if not messages:
                    continue

                for stream_name, entries in messages:
                    for msg_id, fields in entries:
                        await self._process_command(msg_id, fields)

            except asyncio.CancelledError:
                logger.debug("consume_cancelled", gate_id=self.gate_id)
                raise
            except Exception as e:
                logger.error(
                    "consume_error",
                    gate_id=self.gate_id,
                    error=str(e),
                )
                await asyncio.sleep(1)

    async def _process_command(self, msg_id: str, fields: dict[str, str]) -> None:
        """Process a single command message."""
        if self._redis is None:
            return

        try:
            # Bind trace_id for structured logging correlation
            trace_id = fields.get("trace_id", uuid.uuid4().hex[:16])
            bind_trace_id(trace_id)

            command_type = fields.get("command_type", "unknown")
            logger.info(
                "command_received",
                gate_id=self.gate_id,
                command_type=command_type,
                msg_id=msg_id,
            )

            # Deserialize fields into a RedisCommand-like dict
            command_data = dict(fields)

            # Let subclass handle the command
            ack = await self.handle_command(command_data)

            if ack:
                await self._redis.xack(
                    self._command_stream,
                    self._consumer_group,
                    msg_id,
                )
                logger.info(
                    "command_acked",
                    gate_id=self.gate_id,
                    command_type=command_type,
                    msg_id=msg_id,
                )
            else:
                # Do not ACK — Redis will redeliver
                logger.warning(
                    "command_nack",
                    gate_id=self.gate_id,
                    command_type=command_type,
                    msg_id=msg_id,
                )

        except Exception as e:
            logger.error(
                "command_processing_error",
                gate_id=self.gate_id,
                command_type=fields.get("command_type", "unknown"),
                error=str(e),
            )
            # Do not ACK on exception — allow retry
        finally:
            clear_context()

    # ------------------------------------------------------------------
    # Pub/Sub — Event Publishing
    # ------------------------------------------------------------------

    async def publish_event(self, event: BaseEvent) -> int:
        """Publish an event to the Redis Pub/Sub channel.

        Returns:
            Number of subscribers that received the message.
        """
        if self._redis is None:
            raise RuntimeError("Redis not connected")
        payload = event.model_dump_json()
        result = await self._redis.publish(self._event_channel, payload)
        logger.debug(
            "event_published",
            gate_id=self.gate_id,
            event_type=event.event_type,
            subscribers=result,
        )
        return result

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def _heartbeat(self) -> None:
        """Publish heartbeat every 30 seconds."""
        while self._running:
            try:
                event = HeartbeatEvent(
                    event_type="heartbeat",
                    gate_id=self.gate_id,
                    controller_ok=True,  # Subclasses should override
                    passti_ok=True,
                )
                await self.publish_event(event)
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.debug("heartbeat_cancelled", gate_id=self.gate_id)
                raise
            except Exception as e:
                logger.error("heartbeat_error", gate_id=self.gate_id, error=str(e))
                await asyncio.sleep(5)

    # ------------------------------------------------------------------
    # State Persistence & Recovery
    # ------------------------------------------------------------------

    async def _persist_state(self) -> None:
        """Persist current state and state_data to Redis Hash."""
        if self._redis is None:
            return
        data = {
            "state": self.state,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "state_data": json.dumps(self.state_data, default=str),
        }
        await self._redis.hset(self._state_key, mapping=data)
        logger.debug(
            "state_persisted",
            gate_id=self.gate_id,
            state=self.state,
        )

    async def _recover_state(self) -> None:
        """Recover state from Redis Hash on startup."""
        if self._redis is None:
            return
        try:
            data = await self._redis.hgetall(self._state_key)
            if data:
                self.state = data.get("state", self.get_initial_state())
                try:
                    self.state_data = json.loads(data.get("state_data", "{}"))
                except json.JSONDecodeError:
                    self.state_data = {}
                logger.info(
                    "state_recovered",
                    gate_id=self.gate_id,
                    state=self.state,
                )
            else:
                logger.info(
                    "state_no_previous",
                    gate_id=self.gate_id,
                    state=self.state,
                )
        except Exception as e:
            logger.error("state_recovery_error", gate_id=self.gate_id, error=str(e))
            self.state = self.get_initial_state()
            self.state_data = {}

    async def _transition(self, new_state: str, **kwargs: Any) -> None:
        """Transition to a new state and persist.

        Args:
            new_state: The new state name.
            **kwargs: Additional data to store in state_data.
        """
        old_state = self.state
        self.state = new_state
        if kwargs:
            self.state_data.update(kwargs)
        await self._persist_state()
        logger.info(
            "state_transition",
            gate_id=self.gate_id,
            old_state=old_state,
            new_state=new_state,
        )

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    async def handle_command(self, command_data: dict[str, str]) -> bool:
        """Process a command from Redis Streams.

        Args:
            command_data: Dict of command fields from Redis Stream.

        Returns:
            True if command was processed successfully (will ACK).
            False if command should be retried (will NOT ACK).
        """
        ...

    @abstractmethod
    def get_initial_state(self) -> str:
        """Return the initial state for this daemon."""
        ...
