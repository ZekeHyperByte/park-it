"""Gate and reader configuration validator.

Validates that gate configurations have all required fields
for safe daemon startup.
"""

from typing import Any


REQUIRED_GATE_IN_FIELDS = ["controller_host", "controller_port", "gate_mode"]
REQUIRED_GATE_OUT_FIELDS = ["controller_host", "controller_port"]
REQUIRED_EMONEY_FIELDS = ["emoney_reader_serial_port", "emoney_reader_baudrate"]


def validate_gate_config(config: dict[str, Any], gate_type: str = "in") -> dict:
    """Validate a single gate configuration.

    Returns:
        {"valid": bool, "errors": list[str], "warnings": list[str]}
    """
    errors = []
    warnings = []

    required = REQUIRED_GATE_IN_FIELDS if gate_type == "in" else REQUIRED_GATE_OUT_FIELDS

    for field in required:
        if field not in config or config[field] is None:
            errors.append(f"Missing required field: {field}")

    if "controller_port" in config:
        port = config["controller_port"]
        if not isinstance(port, int) or not (1 <= port <= 65535):
            errors.append(f"Invalid controller_port: {port}")

    if config.get("gate_mode") == "EMONEY" and gate_type == "in":
        for field in REQUIRED_EMONEY_FIELDS:
            if field not in config or config[field] is None:
                errors.append(f"EMONEY mode requires: {field}")

    if config.get("has_close_sensor") is None:
        warnings.append("has_close_sensor not set -- defaulting to False")

    if config.get("gate_close_duration_ms", 0) < 100:
        warnings.append("gate_close_duration_ms seems very low (< 100ms)")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def validate_system_config(configs: list[dict[str, Any]]) -> dict:
    """Validate entire system configuration.

    Returns:
        {"valid": bool, "gate_results": list[dict], "summary": str}
    """
    gate_results = []
    all_valid = True

    for i, cfg in enumerate(configs):
        gate_type = cfg.get("gate_type", "in")
        result = validate_gate_config(cfg, gate_type)
        result["gate_id"] = cfg.get("gate_id", f"gate-{i}")
        result["gate_type"] = gate_type
        gate_results.append(result)
        if not result["valid"]:
            all_valid = False

    return {
        "valid": all_valid,
        "gate_results": gate_results,
        "summary": f"{sum(1 for r in gate_results if r['valid'])}/{len(gate_results)} gates valid",
    }
