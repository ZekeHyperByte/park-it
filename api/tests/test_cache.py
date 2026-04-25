"""Tests for Redis caching layer."""

import pytest
import pytest_asyncio

from api.app.cache import reference_data as cache
from shared.redis import redis_client


@pytest_asyncio.fixture(autouse=True)
async def clear_cache():
    """Clear all cache keys before each test."""
    # Reset RedisClient singleton to avoid loop mismatch
    redis_client._instance = None
    redis_client._redis = None
    await redis_client.connect()
    for key in cache.CACHE_KEYS.values():
        await redis_client.delete(key)
    yield
    await redis_client.disconnect()


class TestVehicleTypeCache:
    async def test_cache_miss_returns_none(self):
        result = await cache.get_cached_vehicle_types()
        assert result is None

    async def test_cache_hit_returns_data(self):
        test_data = [
            {"id": 1, "name": "Motor", "code": "MOTOR"},
            {"id": 2, "name": "Mobil", "code": "MOBIL"},
        ]
        await cache._set_cached(cache.CACHE_KEYS["vehicle_types"], test_data)

        result = await cache.get_cached_vehicle_types()
        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "Motor"

    async def test_invalidate_removes_cache(self):
        test_data = [{"id": 1, "name": "Motor"}]
        await cache._set_cached(cache.CACHE_KEYS["vehicle_types"], test_data)
        assert await cache.get_cached_vehicle_types() is not None

        await cache.invalidate_vehicle_types()
        assert await cache.get_cached_vehicle_types() is None


class TestMemberCache:
    async def test_cache_round_trip(self):
        test_data = [
            {"id": 1, "name": "John", "card_number": "123"},
        ]
        await cache._set_cached(cache.CACHE_KEYS["members"], test_data)

        result = await cache.get_cached_members()
        assert result is not None
        assert result[0]["name"] == "John"

    async def test_invalidate_all_clears_everything(self):
        await cache._set_cached(cache.CACHE_KEYS["vehicle_types"], [{"id": 1}])
        await cache._set_cached(cache.CACHE_KEYS["members"], [{"id": 2}])
        await cache._set_cached(cache.CACHE_KEYS["gate_ins"], [{"id": 3}])

        await cache.invalidate_all_reference_data()

        assert await cache.get_cached_vehicle_types() is None
        assert await cache.get_cached_members() is None
        assert await cache.get_cached_gate_ins() is None


class TestCacheTTL:
    async def test_cache_expires_after_ttl(self):
        test_data = [{"id": 1}]
        await cache._set_cached(cache.CACHE_KEYS["shifts"], test_data, ttl=1)

        # Should exist immediately
        assert await cache.get_cached_shifts() is not None

        # Wait for expiry
        import asyncio

        await asyncio.sleep(1.5)

        # Should be expired (Redis removes key)
        # Note: In real Redis, TTL is approximate. For tests we check it's gone or stale.
        result = await cache.get_cached_shifts()
        assert result is None


class TestJsonSerialization:
    async def test_complex_data_serializes_correctly(self):
        test_data = [
            {
                "id": 1,
                "name": "Test",
                "is_active": True,
                "count": 42,
                "nested": {"key": "value"},
            }
        ]
        await cache._set_cached(cache.CACHE_KEYS["areas"], test_data)

        result = await cache.get_cached_areas()
        assert result == test_data
