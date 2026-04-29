"""Redis Pub/Sub event consumer for server-side event processing.

Subscribes to parking.events.* and handles business logic for specific event types:
- passti_card_tap: logged (entry flow is daemon-driven)
- deduct_result: delegates to payment service to complete e-money exit
"""

import asyncio
import json

from shared.logging import get_logger
from shared.redis import redis_client

logger = get_logger("event_consumer")


class EventConsumer:
    """Subscribe to Redis pub/sub and process events server-side."""

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the Redis pub/sub listener."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._listen())
        logger.info("event_consumer_started")

    async def stop(self) -> None:
        """Stop the Redis pub/sub listener."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("event_consumer_stopped")

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
            logger.error("event_consumer_listen_error", error=str(e))
        finally:
            await pubsub.punsubscribe("parking.events.*")
            await pubsub.close()

    async def _handle_message(self, channel: str, data: str) -> None:
        """Handle a Redis pub/sub message."""
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            logger.warning("event_consumer_invalid_json", channel=channel, data=data)
            return

        event_type = payload.get("event_type")
        if event_type is None:
            logger.warning("event_consumer_missing_event_type", channel=channel, payload=payload)
            return

        if event_type == "passti_card_tap":
            await self._handle_passti_card_tap(payload)
        elif event_type == "deduct_result":
            await self._handle_deduct_result(payload)
        else:
            # Other events are broadcast-only; no server-side action needed
            pass

    async def _handle_passti_card_tap(self, payload: dict) -> None:
        """Handle passti_card_tap event.

        The entry gate daemon drives the entry flow (sends check_balance and
        waits for response). For now we just log the tap.
        """
        gate_id = payload.get("gate_id", "unknown")
        card_number = payload.get("card_number", "unknown")
        card_type = payload.get("card_type", "unknown")
        logger.info(
            "passti_card_tap_received",
            gate_id=gate_id,
            card_number=card_number,
            card_type=card_type,
        )

    async def _handle_deduct_result(self, payload: dict) -> None:
        """Handle deduct_result event by processing the e-money payment."""
        from sqlalchemy import select

        from api.app.models import Gate
        from api.app.services.payment import process_emoney_result
        from api.database import AsyncSessionLocal
        from shared.events import DeductStatus

        gate_id = payload.get("gate_id")
        if gate_id is None:
            logger.error("deduct_result_missing_gate_id", payload=payload)
            return

        async with AsyncSessionLocal() as db:
            try:
                # Look up gate by code to obtain the integer DB id
                result = await db.execute(select(Gate).where(Gate.code == gate_id))
                gate = result.scalar_one_or_none()
                if gate is None:
                    logger.error("deduct_result_gate_not_found", gate_id=gate_id)
                    return

                status_str = payload.get("status")
                try:
                    status = DeductStatus(status_str)
                except ValueError:
                    logger.error(
                        "deduct_result_invalid_status",
                        gate_id=gate_id,
                        status=status_str,
                    )
                    return

                await process_emoney_result(
                    db,
                    gate_id=gate_id,
                    gate_out_id=gate.id,
                    card_number=payload.get("card_number", ""),
                    status=status,
                    deduct_amount=payload.get("deduct_amount", 0),
                    balance_before=payload.get("balance_before", 0),
                    balance_after=payload.get("balance_after", 0),
                    transaction_counter=payload.get("transaction_counter", 0),
                    raw_response_hex=payload.get("raw_response_hex", ""),
                )
                logger.info(
                    "deduct_result_processed",
                    gate_id=gate_id,
                    gate_out_id=gate.id,
                    status=status.value,
                )
            except Exception as e:
                logger.error(
                    "deduct_result_processing_error",
                    gate_id=gate_id,
                    error=str(e),
                )


# Global instance
event_consumer = EventConsumer()
