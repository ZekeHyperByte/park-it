# Redis Integration Tests

> 36 nodes · cohesion 0.08

## Key Concepts

- **IntegrationDaemon** (18 connections) — `api/tests/test_integration_redis_streams.py`
- **test_integration_redis_streams.py** (14 connections) — `api/tests/test_integration_redis_streams.py`
- **.consume_one()** (8 connections) — `api/tests/test_integration_redis_streams.py`
- **test_consumer_group_recreated_on_daemon_restart()** (8 connections) — `api/tests/test_integration_redis_streams.py`
- **test_unacked_command_redelivered()** (8 connections) — `api/tests/test_integration_redis_streams.py`
- **.run()** (6 connections) — `api/tests/test_integration_redis_streams.py`
- **.stop()** (6 connections) — `api/tests/test_integration_redis_streams.py`
- **test_daemon_event_publish()** (6 connections) — `api/tests/test_integration_redis_streams.py`
- **integration_daemon()** (5 connections) — `api/tests/test_integration_redis_streams.py`
- **test_command_with_nested_dict_serialization()** (5 connections) — `api/tests/test_integration_redis_streams.py`
- **test_display_text_command_flow()** (5 connections) — `api/tests/test_integration_redis_streams.py`
- **test_open_gate_command_flow()** (5 connections) — `api/tests/test_integration_redis_streams.py`
- **cleaned_redis()** (2 connections) — `api/tests/test_integration_redis_streams.py`
- **gate_in_config()** (2 connections) — `api/tests/test_integration_redis_streams.py`
- **.handle_command()** (2 connections) — `api/tests/test_integration_redis_streams.py`
- **real_redis()** (2 connections) — `api/tests/test_integration_redis_streams.py`
- **reset_redis_singleton()** (2 connections) — `api/tests/test_integration_redis_streams.py`
- **.get_initial_state()** (1 connections) — `api/tests/test_integration_redis_streams.py`
- **.__init__()** (1 connections) — `api/tests/test_integration_redis_streams.py`
- **Integration tests for FastAPI <-> Daemon communication via Redis Streams.  These** (1 connections) — `api/tests/test_integration_redis_streams.py`
- **Daemon subclass for integration testing using real Redis.      Does NOT connect** (1 connections) — `api/tests/test_integration_redis_streams.py`
- **Override to skip controller connection.** (1 connections) — `api/tests/test_integration_redis_streams.py`
- **Consume exactly one command from Redis Streams.          Args:             timeo** (1 connections) — `api/tests/test_integration_redis_streams.py`
- **Record command and return success.** (1 connections) — `api/tests/test_integration_redis_streams.py`
- **Programmatic stop with Redis cleanup.** (1 connections) — `api/tests/test_integration_redis_streams.py`
- *... and 11 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/tests/test_integration_redis_streams.py`

## Audit Trail

- EXTRACTED: 107 (87%)
- INFERRED: 16 (13%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*