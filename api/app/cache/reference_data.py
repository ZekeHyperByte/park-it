"""Redis caching layer for reference data (gates, vehicle types, members, settings)."""

from typing import Any

from shared.redis import redis_client

DEFAULT_TTL = 300  # 5 minutes

# Cache key prefixes
CACHE_KEYS = {
    "gates": "cache:gates",
    "vehicle_types": "cache:vehicle_types",
    "members": "cache:members",
    "settings": "cache:settings",
    "member_groups": "cache:member_groups",
    "shifts": "cache:shifts",
    "areas": "cache:areas",
    "emoney_readers": "cache:emoney_readers",
}


async def _get_cached(key: str) -> list[dict] | None:
    """Generic cache getter."""
    await redis_client.connect()
    return await redis_client.cache_get_json(key)


async def _set_cached(key: str, data: list[dict], ttl: int = DEFAULT_TTL) -> None:
    """Generic cache setter."""
    await redis_client.connect()
    await redis_client.cache_set_json(key, data, ttl=ttl)


async def _invalidate(key: str) -> None:
    """Generic cache invalidator."""
    await redis_client.connect()
    await redis_client.delete(key)


# Gates (unified)
async def get_cached_gates() -> list[dict] | None:
    return await _get_cached(CACHE_KEYS["gates"])


async def invalidate_gates() -> None:
    await _invalidate(CACHE_KEYS["gates"])


# Vehicle Types
async def get_cached_vehicle_types() -> list[dict] | None:
    return await _get_cached(CACHE_KEYS["vehicle_types"])


async def invalidate_vehicle_types() -> None:
    await _invalidate(CACHE_KEYS["vehicle_types"])


# Members
async def get_cached_members() -> list[dict] | None:
    return await _get_cached(CACHE_KEYS["members"])


async def invalidate_members() -> None:
    await _invalidate(CACHE_KEYS["members"])


# Settings
async def get_cached_settings() -> list[dict] | None:
    return await _get_cached(CACHE_KEYS["settings"])


async def invalidate_settings() -> None:
    await _invalidate(CACHE_KEYS["settings"])


# Member Groups
async def get_cached_member_groups() -> list[dict] | None:
    return await _get_cached(CACHE_KEYS["member_groups"])


async def invalidate_member_groups() -> None:
    await _invalidate(CACHE_KEYS["member_groups"])


# Shifts
async def get_cached_shifts() -> list[dict] | None:
    return await _get_cached(CACHE_KEYS["shifts"])


async def invalidate_shifts() -> None:
    await _invalidate(CACHE_KEYS["shifts"])


# Areas
async def get_cached_areas() -> list[dict] | None:
    return await _get_cached(CACHE_KEYS["areas"])


async def invalidate_areas() -> None:
    await _invalidate(CACHE_KEYS["areas"])


# Emoney Readers
async def get_cached_emoney_readers() -> list[dict] | None:
    return await _get_cached(CACHE_KEYS["emoney_readers"])


async def invalidate_emoney_readers() -> None:
    await _invalidate(CACHE_KEYS["emoney_readers"])


# Bulk invalidation helpers
async def invalidate_all_reference_data() -> None:
    """Invalidate all reference data caches."""
    for key in CACHE_KEYS.values():
        await _invalidate(key)
