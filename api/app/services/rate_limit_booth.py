"""Per-gate rate limit for booth (machine-to-machine) endpoints.

Sliding window via Redis sorted set keyed by gate_id. Shielded against Redis
outage: if Redis fails, the check fails open (allow) — we never want a Redis
blip to lock a real customer out of the gate.
"""

from __future__ import annotations

import time

from fastapi import HTTPException

from shared.logging import get_logger
from shared.redis import redis_client

logger = get_logger("rate_limit_booth")

# 60 req/min per gate_id. One Omnikey tap takes >1s; legitimate bursts (shift
# handover, multiple taps) stay well under this. Anything above = stuck poller
# or attack.
BOOTH_LIMIT_MAX = 60
BOOTH_LIMIT_WINDOW = 60


async def enforce_booth_rate_limit(gate_id: str) -> None:
    """Raise HTTPException(429) when this gate exceeds the booth-call budget.

    Fails open on Redis errors — paying customer must not be blocked by infra.
    """
    if not gate_id:
        return
    key = f"rate_limit:booth:{gate_id}"
    try:
        await redis_client.connect()
        redis = redis_client.client
        now = time.time()
        window_start = now - BOOTH_LIMIT_WINDOW
        await redis.zremrangebyscore(key, 0, window_start)
        count = await redis.zcard(key)
        if count >= BOOTH_LIMIT_MAX:
            oldest = await redis.zrange(key, 0, 0, withscores=True)
            retry_after = max(
                1, int(oldest[0][1] + BOOTH_LIMIT_WINDOW - now) if oldest else BOOTH_LIMIT_WINDOW
            )
            logger.warning(
                "booth_rate_limit_exceeded", gate_id=gate_id, count=count, retry_after=retry_after
            )
            raise HTTPException(
                status_code=429,
                detail="Too many booth requests for this gate",
                headers={"Retry-After": str(retry_after)},
            )
        await redis.zadd(key, {str(now): now})
        await redis.expire(key, BOOTH_LIMIT_WINDOW + 1)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("booth_rate_limit_redis_error", gate_id=gate_id, error=str(e))
        return
