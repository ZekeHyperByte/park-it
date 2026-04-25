"""Redis Pub/Sub broadcaster for WebSocket."""

import asyncio
import json

from shared.logging import get_logger
from shared.redis import redis_client

logger = get_logger("ws_broadcaster")


class RedisBroadcaster:
    """Subscribe to Redis pub/sub and forward events to WebSocket clients."""

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the Redis pub/sub listener."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._listen())
        logger.info("ws_broadcaster_started")

    async def stop(self) -> None:
        """Stop the Redis pub/sub listener."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ws_broadcaster_stopped")

    async def _listen(self) -> None:
        """Listen for Redis pub/sub messages."""
        await redis_client.connect()
        pubsub = redis_client.client.pubsub()
        await pubsub.psubscribe("parking.events.*")

        try:
            async for message in pubsub.listen():
                if not self._running:
                    break
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    data = message["data"]
                    await self._handle_message(channel, data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("ws_broadcaster_error", error=str(e))
        finally:
            await pubsub.punsubscribe("parking.events.*")
            await pubsub.close()

    async def _handle_message(self, channel: str, data: str) -> None:
        """Handle a Redis pub/sub message."""
        from api.app.websocket.connection_manager import ws_manager

        # Extract gate_id from channel: parking.events.{gate_id}
        parts = channel.rsplit(".", 1)
        if len(parts) != 2:
            return
        gate_id = parts[1]

        try:
            # Validate JSON
            json.loads(data)
        except json.JSONDecodeError:
            logger.warning("ws_broadcaster_invalid_json", data=data)
            return

        await ws_manager.send_to_gate(gate_id, data)


# Global instance
broadcaster = RedisBroadcaster()
