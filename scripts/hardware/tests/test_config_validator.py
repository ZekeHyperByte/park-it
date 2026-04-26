"""Tests for configuration validator."""

import pytest

from scripts.hardware.config_validator import validate_gate_config, validate_system_config


class TestValidateGateConfig:
    def test_valid_gate_in_cash(self):
        config = {
            "controller_host": "192.168.1.100",
            "controller_port": 5000,
            "gate_mode": "CASH",
            "has_close_sensor": True,
            "gate_close_duration_ms": 5000,
        }
        result = validate_gate_config(config, "in")
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_valid_gate_out(self):
        config = {
            "controller_host": "192.168.1.100",
            "controller_port": 5000,
        }
        result = validate_gate_config(config, "out")
        assert result["valid"] is True

    def test_missing_host(self):
        config = {
            "controller_port": 5000,
            "gate_mode": "CASH",
        }
        result = validate_gate_config(config, "in")
        assert result["valid"] is False
        assert any("controller_host" in e for e in result["errors"])

    def test_invalid_port(self):
        config = {
            "controller_host": "192.168.1.100",
            "controller_port": 70000,
            "gate_mode": "CASH",
        }
        result = validate_gate_config(config, "in")
        assert result["valid"] is False
        assert any("controller_port" in e for e in result["errors"])

    def test_emoney_missing_reader(self):
        config = {
            "controller_host": "192.168.1.100",
            "controller_port": 5000,
            "gate_mode": "EMONEY",
        }
        result = validate_gate_config(config, "in")
        assert result["valid"] is False
        assert any("emoney_reader_serial_port" in e for e in result["errors"])

    def test_warning_close_sensor_unset(self):
        config = {
            "controller_host": "192.168.1.100",
            "controller_port": 5000,
            "gate_mode": "CASH",
        }
        result = validate_gate_config(config, "in")
        assert len(result["warnings"]) > 0
        assert any("has_close_sensor" in w for w in result["warnings"])

    def test_warning_low_duration(self):
        config = {
            "controller_host": "192.168.1.100",
            "controller_port": 5000,
            "gate_mode": "CASH",
            "gate_close_duration_ms": 50,
        }
        result = validate_gate_config(config, "in")
        assert any("gate_close_duration_ms" in w for w in result["warnings"])


class TestValidateSystemConfig:
    def test_all_valid(self):
        configs = [
            {"gate_id": "gin-1", "gate_type": "in", "controller_host": "192.168.1.100", "controller_port": 5000, "gate_mode": "CASH"},
            {"gate_id": "gout-1", "gate_type": "out", "controller_host": "192.168.1.101", "controller_port": 5000},
        ]
        result = validate_system_config(configs)
        assert result["valid"] is True
        assert "2/2 gates valid" in result["summary"]

    def test_one_invalid(self):
        configs = [
            {"gate_id": "gin-1", "gate_type": "in", "controller_host": "192.168.1.100", "controller_port": 5000, "gate_mode": "CASH"},
            {"gate_id": "gout-1", "gate_type": "out", "controller_port": 5000},  # missing host
        ]
        result = validate_system_config(configs)
        assert result["valid"] is False
        assert "1/2 gates valid" in result["summary"]
