# PASSTI E-Money Simulator

> 28 nodes · cohesion 0.10

## Key Concepts

- **PasstiSimulator** (21 connections) — `tests/e2e/simulator/passti_sim.py`
- **._process_frame()** (10 connections) — `tests/e2e/simulator/passti_sim.py`
- **._build_deduct_response()** (4 connections) — `tests/e2e/simulator/passti_sim.py`
- **._build_error_response()** (4 connections) — `tests/e2e/simulator/passti_sim.py`
- **._build_cancel_response()** (3 connections) — `tests/e2e/simulator/passti_sim.py`
- **._build_check_balance_response()** (3 connections) — `tests/e2e/simulator/passti_sim.py`
- **._build_init_response()** (3 connections) — `tests/e2e/simulator/passti_sim.py`
- **test_passti_sim.py** (3 connections) — `tests/e2e/simulator/test_passti_sim.py`
- **._handle_client()** (2 connections) — `tests/e2e/simulator/passti_sim.py`
- **test_deduct_response()** (2 connections) — `tests/e2e/simulator/test_passti_sim.py`
- **test_start_stop()** (2 connections) — `tests/e2e/simulator/test_passti_sim.py`
- **TestPasstiSimulator** (2 connections) — `tests/e2e/simulator/test_passti_sim.py`
- **passti_sim.py** (2 connections) — `tests/e2e/simulator/passti_sim.py`
- **.clear_command_log()** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- **.get_command_log()** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- **.__init__()** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- **.set_card_type()** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- **.set_next_status()** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- **.start()** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- **.stop()** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- **PASSTI e-money reader TCP simulator.  Simulates PASSTI reader frame protocol: -** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- **Build CheckBalance success response.** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- **Build Deduct response based on configured status.** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- **Build CancelDeduct success response.** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- **Build INIT success response.** (1 connections) — `tests/e2e/simulator/passti_sim.py`
- *... and 3 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `tests/e2e/simulator/passti_sim.py`
- `tests/e2e/simulator/test_passti_sim.py`

## Audit Trail

- EXTRACTED: 66 (87%)
- INFERRED: 10 (13%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*