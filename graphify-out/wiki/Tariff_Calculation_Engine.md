# Tariff Calculation Engine

> 33 nodes · cohesion 0.07

## Key Concepts

- **TestCalculateTariff** (13 connections) — `api/tests/test_tariff.py`
- **get_vehicle_type_tariff_config()** (8 connections) — `api/app/services/transaction.py`
- **TariffConfig** (5 connections) — `api/app/services/tariff.py`
- **VehicleTypeRate** (5 connections) — `api/app/services/tariff.py`
- **tariff.py** (4 connections) — `api/app/services/tariff.py`
- **.test_custom_config()** (4 connections) — `api/tests/test_tariff.py`
- **TestGetVehicleTypeTariffConfig** (4 connections) — `api/tests/test_transaction_service.py`
- **test_tariff.py** (2 connections) — `api/tests/test_tariff.py`
- **calculate_tariff()** (2 connections) — `api/app/services/tariff.py`
- **.test_daily_cap()** (2 connections) — `api/tests/test_tariff.py`
- **.test_exit_before_entry_raises()** (2 connections) — `api/tests/test_tariff.py`
- **.test_grace_period()** (2 connections) — `api/tests/test_tariff.py`
- **.test_partial_hour_rounds_up()** (2 connections) — `api/tests/test_tariff.py`
- **.test_unknown_vehicle_type()** (2 connections) — `api/tests/test_tariff.py`
- **.test_from_database()** (2 connections) — `api/tests/test_transaction_service.py`
- **.test_invalid_id_returns_default()** (2 connections) — `api/tests/test_transaction_service.py`
- **.test_none_returns_default()** (2 connections) — `api/tests/test_transaction_service.py`
- **Tariff calculation engine.  This module provides configurable tariff calculation** (1 connections) — `api/app/services/tariff.py`
- **Rate configuration for a vehicle type.** (1 connections) — `api/app/services/tariff.py`
- **Complete tariff configuration.** (1 connections) — `api/app/services/tariff.py`
- **Calculate parking fee based on entry/exit time and vehicle type.      Args:** (1 connections) — `api/app/services/tariff.py`
- **Build TariffConfig from database VehicleType or fallback to default.      Args:** (1 connections) — `api/app/services/transaction.py`
- **Tests for tariff calculation engine.** (1 connections) — `api/tests/test_tariff.py`
- **Test tariff calculation scenarios.** (1 connections) — `api/tests/test_tariff.py`
- **No charge within grace period.** (1 connections) — `api/tests/test_tariff.py`
- *... and 8 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/app/services/tariff.py`
- `api/app/services/transaction.py`
- `api/tests/test_tariff.py`
- `api/tests/test_transaction_service.py`

## Audit Trail

- EXTRACTED: 61 (77%)
- INFERRED: 18 (23%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*