"""Hardware deployment automation script.

Generates systemd service files and deployment scripts for
physical gate installations.

Usage:
    python scripts/deploy_hardware.py --gate-id gate-in-1 --host 192.168.1.100 --port 5000
"""

import argparse
import os
import sys
from pathlib import Path

SYSTEMD_TEMPLATE = """\
[Unit]
Description=Parking Daemon -- {gate_type} {gate_id}
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=parking
Group=dialout
WorkingDirectory=/opt/parking-system-v2
Environment=PYTHONPATH=/opt/parking-system-v2
EnvironmentFile=/opt/parking-system-v2/.env
ExecStart=/opt/parking-system-v2/.venv/bin/python -m daemons.{daemon_module} --gate-id {gate_id}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=parking-daemon-{gate_id}

[Install]
WantedBy=multi-user.target
"""


def generate_systemd_service(
    gate_id: str,
    gate_type: str,
    daemon_module: str,
) -> str:
    """Generate a systemd service file for a gate daemon."""
    return SYSTEMD_TEMPLATE.format(
        gate_id=gate_id,
        gate_type=gate_type,
        daemon_module=daemon_module,
    )


def validate_before_deploy(gate_config: dict) -> dict:
    """Validate configuration before generating deployment artifacts."""
    from scripts.hardware.config_validator import validate_gate_config

    result = validate_gate_config(gate_config, gate_config.get("gate_type", "in"))
    result["deploy_ready"] = result["valid"]
    return result


def write_service_file(gate_id: str, gate_type: str, daemon_module: str, output_dir: str) -> Path:
    """Write systemd service file to disk."""
    content = generate_systemd_service(gate_id, gate_type, daemon_module)
    filename = f"parking-daemon-{gate_id.replace('_', '-')}.service"
    path = Path(output_dir) / filename
    path.write_text(content)
    return path


def main():
    parser = argparse.ArgumentParser(description="Hardware Deployment Generator")
    parser.add_argument("--gate-id", required=True, help="Gate identifier")
    parser.add_argument("--gate-type", choices=["in", "out"], required=True, help="Gate type")
    parser.add_argument("--host", required=True, help="Controller IP")
    parser.add_argument("--port", type=int, required=True, help="Controller port")
    parser.add_argument("--output-dir", default="./deploy", help="Output directory")
    parser.add_argument("--mode", default="CASH", help="Gate mode (CASH/RFID/EMONEY)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    gate_config = {
        "gate_id": args.gate_id,
        "gate_type": args.gate_type,
        "controller_host": args.host,
        "controller_port": args.port,
        "gate_mode": args.mode,
    }

    validation = validate_before_deploy(gate_config)
    if not validation["deploy_ready"]:
        print("Validation failed:")
        for error in validation["errors"]:
            print(f"  FAIL {error}")
        return 1

    daemon_module = "gate_in" if args.gate_type == "in" else "gate_out"
    path = write_service_file(args.gate_id, args.gate_type, daemon_module, args.output_dir)
    print(f"PASS Generated: {path}")
    print(f"PASS Run: sudo cp {path} /etc/systemd/system/ && sudo systemctl daemon-reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
