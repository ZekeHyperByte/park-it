# BaseDaemon Unit Tests

> 27 nodes · cohesion 0.13

## Key Concepts

- **test_base.py** (25 connections) — `daemons/tests/test_base.py`
- **.run()** (16 connections) — `daemons/tests/test_base.py`
- **TestableDaemon** (13 connections) — `daemons/tests/test_base.py`
- **.run_and_wait()** (5 connections) — `daemons/tests/test_base.py`
- **test_command_trace_id_binding()** (4 connections) — `daemons/tests/test_base.py`
- **test_process_command_nacks_failure()** (4 connections) — `daemons/tests/test_base.py`
- **.handle_command()** (4 connections) — `daemons/tests/test_base.py`
- **test_process_command_acks_success()** (3 connections) — `daemons/tests/test_base.py`
- **test_consumer_group_created()** (2 connections) — `daemons/tests/test_base.py`
- **test_consumer_group_idempotent()** (2 connections) — `daemons/tests/test_base.py`
- **test_daemon()** (2 connections) — `daemons/tests/test_base.py`
- **test_persist_state()** (2 connections) — `daemons/tests/test_base.py`
- **test_recover_empty_state()** (2 connections) — `daemons/tests/test_base.py`
- **test_recover_state()** (2 connections) — `daemons/tests/test_base.py`
- **test_redis_closed_on_stop()** (2 connections) — `daemons/tests/test_base.py`
- **test_run_injects_fake_redis()** (2 connections) — `daemons/tests/test_base.py`
- **test_stop_cancels_tasks()** (2 connections) — `daemons/tests/test_base.py`
- **test_stop_sets_running_false()** (2 connections) — `daemons/tests/test_base.py`
- **test_transition_persists()** (2 connections) — `daemons/tests/test_base.py`
- **.set_ack_result()** (2 connections) — `daemons/tests/test_base.py`
- **Tests for daemons/base.py.** (1 connections) — `daemons/tests/test_base.py`
- **Concrete daemon subclass for testing BaseDaemon.** (1 connections) — `daemons/tests/test_base.py`
- **Override run to inject fake Redis. Does not block.** (1 connections) — `daemons/tests/test_base.py`
- **Run with blocking shutdown wait (for shutdown tests).** (1 connections) — `daemons/tests/test_base.py`
- **test_initial_state()** (1 connections) — `daemons/tests/test_base.py`
- *... and 2 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `daemons/tests/test_base.py`

## Audit Trail

- EXTRACTED: 101 (96%)
- INFERRED: 4 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*