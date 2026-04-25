"""Gate command publisher — sends Redis Stream commands to daemons.

This module provides a thin wrapper around Redis Streams for publishing
commands from FastAPI to gate daemons.
"""

import json

from shared.events import RedisCommand
from shared.logging import get_logger
from shared.redis import redis_client

logger = get_logger("gate_command")


async def publish_command(command: RedisCommand) -> str:
    """Publish a command to the gate's Redis Stream.

    Args:
        command: Pydantic command model (any RedisCommand subtype)

    Returns:
        Redis stream message ID
    """
    await redis_client.connect()

    stream = f"parking.commands.{command.gate_id}"
    payload = command.model_dump(mode="json")

    # Serialize nested dicts to JSON strings for Redis hash storage
    fields: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            fields[key] = json.dumps(value)
        elif value is not None:
            fields[key] = str(value)

    message_id = await redis_client.xadd(stream, fields)

    logger.info(
        "command_published",
        stream=stream,
        command_type=command.command_type,
        gate_id=command.gate_id,
        message_id=message_id,
    )
    return message_id
