# Redis Client (Streams & Pub/Sub)

> 30 nodes · cohesion 0.07

## Key Concepts

- **RedisClient** (21 connections) — `shared/redis.py`
- **redis.py** (3 connections) — `shared/redis.py`
- **.cache_delete_pattern()** (3 connections) — `shared/redis.py`
- **.delete()** (3 connections) — `shared/redis.py`
- **.connect()** (2 connections) — `shared/redis.py`
- **.disconnect()** (2 connections) — `shared/redis.py`
- **.publish()** (2 connections) — `shared/redis.py`
- **.xack()** (2 connections) — `shared/redis.py`
- **.xadd()** (2 connections) — `shared/redis.py`
- **.xgroup_create()** (2 connections) — `shared/redis.py`
- **.xgroup_createconsumer()** (2 connections) — `shared/redis.py`
- **.xreadgroup()** (2 connections) — `shared/redis.py`
- **client()** (1 connections) — `shared/redis.py`
- **Async Redis client with Streams and Pub/Sub helpers.** (1 connections) — `shared/redis.py`
- **Create a consumer within a group.** (1 connections) — `shared/redis.py`
- **Async Redis client singleton.** (1 connections) — `shared/redis.py`
- **Delete keys from Redis.** (1 connections) — `shared/redis.py`
- **Delete all keys matching a pattern.** (1 connections) — `shared/redis.py`
- **Establish Redis connection.** (1 connections) — `shared/redis.py`
- **Close Redis connection.** (1 connections) — `shared/redis.py`
- **Publish a message to a Pub/Sub channel.** (1 connections) — `shared/redis.py`
- **Add a message to a Redis Stream.** (1 connections) — `shared/redis.py`
- **Read from a consumer group.** (1 connections) — `shared/redis.py`
- **Acknowledge messages in a stream.** (1 connections) — `shared/redis.py`
- **Create a consumer group.** (1 connections) — `shared/redis.py`
- *... and 5 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `shared/redis.py`

## Audit Trail

- EXTRACTED: 64 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*