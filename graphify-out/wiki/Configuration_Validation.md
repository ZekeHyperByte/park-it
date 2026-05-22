# Configuration Validation

> 38 nodes · cohesion 0.08

## Key Concepts

- **validate_gate_config()** (11 connections) — `scripts/hardware/config_validator.py`
- **TestValidateGateConfig** (8 connections) — `scripts/hardware/tests/test_config_validator.py`
- **validate_before_deploy()** (6 connections) — `scripts/deploy_hardware.py`
- **validate_system_config()** (5 connections) — `scripts/hardware/config_validator.py`
- **generate_systemd_service()** (5 connections) — `scripts/deploy_hardware.py`
- **deploy_hardware.py** (5 connections) — `scripts/deploy_hardware.py`
- **write_service_file()** (5 connections) — `scripts/deploy_hardware.py`
- **test_deploy_hardware.py** (4 connections) — `scripts/tests/test_deploy_hardware.py`
- **main()** (3 connections) — `scripts/deploy_hardware.py`
- **config_validator.py** (3 connections) — `scripts/hardware/config_validator.py`
- **test_config_validator.py** (3 connections) — `scripts/hardware/tests/test_config_validator.py`
- **TestValidateSystemConfig** (3 connections) — `scripts/hardware/tests/test_config_validator.py`
- **TestGenerateSystemdService** (3 connections) — `scripts/tests/test_deploy_hardware.py`
- **TestValidateBeforeDeploy** (3 connections) — `scripts/tests/test_deploy_hardware.py`
- **.test_writes_file()** (3 connections) — `scripts/tests/test_deploy_hardware.py`
- **.test_emoney_missing_reader()** (2 connections) — `scripts/hardware/tests/test_config_validator.py`
- **.test_invalid_port()** (2 connections) — `scripts/hardware/tests/test_config_validator.py`
- **.test_missing_host()** (2 connections) — `scripts/hardware/tests/test_config_validator.py`
- **.test_valid_gate_in_cash()** (2 connections) — `scripts/hardware/tests/test_config_validator.py`
- **.test_valid_gate_out()** (2 connections) — `scripts/hardware/tests/test_config_validator.py`
- **.test_warning_close_sensor_unset()** (2 connections) — `scripts/hardware/tests/test_config_validator.py`
- **.test_warning_low_duration()** (2 connections) — `scripts/hardware/tests/test_config_validator.py`
- **.test_all_valid()** (2 connections) — `scripts/hardware/tests/test_config_validator.py`
- **.test_one_invalid()** (2 connections) — `scripts/hardware/tests/test_config_validator.py`
- **.test_gate_in_service()** (2 connections) — `scripts/tests/test_deploy_hardware.py`
- *... and 13 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `scripts/deploy_hardware.py`
- `scripts/hardware/config_validator.py`
- `scripts/hardware/tests/test_config_validator.py`
- `scripts/tests/test_deploy_hardware.py`

## Audit Trail

- EXTRACTED: 76 (71%)
- INFERRED: 31 (29%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*