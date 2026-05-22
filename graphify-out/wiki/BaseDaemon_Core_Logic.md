# BaseDaemon Core Logic

> 28 nodes · cohesion 0.10

## Key Concepts

- **BaseDaemon** (28 connections) — `daemons/base.py`
- **.run()** (8 connections) — `daemons/base.py`
- **._process_command()** (7 connections) — `daemons/base.py`
- **._heartbeat()** (6 connections) — `daemons/base.py`
- **._consume_commands()** (5 connections) — `daemons/base.py`
- **._recover_state()** (5 connections) — `daemons/base.py`
- **base.py** (5 connections) — `daemons/base.py`
- **._ensure_consumer_group()** (4 connections) — `daemons/base.py`
- **.__init__()** (3 connections) — `daemons/base.py`
- **._on_started()** (3 connections) — `daemons/base.py`
- **.publish_event()** (3 connections) — `daemons/base.py`
- **get_initial_state()** (3 connections) — `daemons/base.py`
- **._request_shutdown()** (2 connections) — `daemons/base.py`
- **.stop()** (2 connections) — `daemons/base.py`
- **handle_command()** (2 connections) — `daemons/base.py`
- **Abstract base daemon for gate controllers.  Handles Redis Streams command consum** (1 connections) — `daemons/base.py`
- **Signal handler — request graceful shutdown.** (1 connections) — `daemons/base.py`
- **Programmatic stop (for testing).** (1 connections) — `daemons/base.py`
- **Hook called after _running is set to True but before main tasks start.** (1 connections) — `daemons/base.py`
- **Create consumer group if it doesn't exist.** (1 connections) — `daemons/base.py`
- **Main command consumption loop.** (1 connections) — `daemons/base.py`
- **Process a single command message.** (1 connections) — `daemons/base.py`
- **Publish an event to the Redis Pub/Sub channel.          Returns:             Num** (1 connections) — `daemons/base.py`
- **Abstract base class for gate daemons.      Responsibilities:     - Connect to Re** (1 connections) — `daemons/base.py`
- **Publish heartbeat every 30 seconds with daemon state.** (1 connections) — `daemons/base.py`
- *... and 3 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `daemons/base.py`

## Audit Trail

- EXTRACTED: 78 (79%)
- INFERRED: 21 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*