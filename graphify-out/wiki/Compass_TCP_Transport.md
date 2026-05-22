# Compass TCP Transport

> 48 nodes · cohesion 0.05

## Key Concepts

- **CompassTransport** (18 connections) — `protocols/compass/protocol.py`
- **test_factory.py** (13 connections) — `protocols/tests/test_factory.py`
- **create_transport()** (12 connections) — `protocols/factory.py`
- **SerialTransport** (9 connections) — `protocols/compass/protocol.py`
- **create_parser()** (6 connections) — `protocols/factory.py`
- **main()** (5 connections) — `scripts/emoney_diagnostic.py`
- **.close()** (3 connections) — `protocols/compass/protocol.py`
- **.connect()** (3 connections) — `protocols/compass/protocol.py`
- **factory.py** (3 connections) — `protocols/factory.py`
- **hexdump()** (3 connections) — `scripts/emoney_diagnostic.py`
- **.is_connected()** (2 connections) — `protocols/compass/protocol.py`
- **.recv_async()** (2 connections) — `protocols/compass/protocol.py`
- **.send()** (2 connections) — `protocols/compass/protocol.py`
- **.send_recv()** (2 connections) — `protocols/compass/protocol.py`
- **.close()** (2 connections) — `protocols/compass/protocol.py`
- **.connect()** (2 connections) — `protocols/compass/protocol.py`
- **emoney_diagnostic.py** (2 connections) — `scripts/emoney_diagnostic.py`
- **test_create_parser_compass()** (2 connections) — `protocols/tests/test_factory.py`
- **test_create_parser_enet()** (2 connections) — `protocols/tests/test_factory.py`
- **test_create_parser_serial()** (2 connections) — `protocols/tests/test_factory.py`
- **test_create_parser_unknown()** (2 connections) — `protocols/tests/test_factory.py`
- **test_create_transport_case_insensitive()** (2 connections) — `protocols/tests/test_factory.py`
- **test_create_transport_compass()** (2 connections) — `protocols/tests/test_factory.py`
- **test_create_transport_compass_default_port()** (2 connections) — `protocols/tests/test_factory.py`
- **test_create_transport_enet()** (2 connections) — `protocols/tests/test_factory.py`
- *... and 23 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `protocols/compass/protocol.py`
- `protocols/factory.py`
- `protocols/tests/test_factory.py`
- `scripts/emoney_diagnostic.py`

## Audit Trail

- EXTRACTED: 94 (71%)
- INFERRED: 38 (29%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*