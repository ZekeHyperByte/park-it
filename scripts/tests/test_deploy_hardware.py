"""Tests for hardware deployment script."""


from scripts.deploy_hardware import generate_systemd_service, validate_before_deploy, write_service_file


class TestGenerateSystemdService:
    def test_gate_in_service(self):
        content = generate_systemd_service("gate-in-1", "IN", "gate_in")
        assert "Description=Parking Daemon -- IN gate-in-1" in content
        assert "ExecStart=/opt/parking-system-v2/.venv/bin/python -m daemons.gate_in --gate-id gate-in-1" in content
        assert "User=parking" in content
        assert "Group=dialout" in content
        assert "Restart=always" in content

    def test_gate_out_service(self):
        content = generate_systemd_service("gate-out-1", "OUT", "gate_out")
        assert "Description=Parking Daemon -- OUT gate-out-1" in content
        assert "ExecStart=/opt/parking-system-v2/.venv/bin/python -m daemons.gate_out --gate-id gate-out-1" in content


class TestValidateBeforeDeploy:
    def test_valid_config(self):
        config = {
            "gate_id": "gin-1",
            "gate_type": "in",
            "controller_host": "192.168.1.100",
            "controller_port": 5000,
            "gate_mode": "CASH",
        }
        result = validate_before_deploy(config)
        assert result["deploy_ready"] is True
        assert result["valid"] is True

    def test_invalid_config(self):
        config = {
            "gate_id": "gin-1",
            "gate_type": "in",
            "controller_port": 5000,
            "gate_mode": "CASH",
        }
        result = validate_before_deploy(config)
        assert result["deploy_ready"] is False
        assert result["valid"] is False


class TestWriteServiceFile:
    def test_writes_file(self, tmp_path):
        path = write_service_file("test-gate", "IN", "gate_in", str(tmp_path))
        assert path.exists()
        content = path.read_text()
        assert "test-gate" in content
