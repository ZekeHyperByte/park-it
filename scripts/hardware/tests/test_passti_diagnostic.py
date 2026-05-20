"""Tests for PASSTI diagnostic."""


from scripts.hardware.passti_diagnostic import diagnose_passti
from protocols.passti.commands import cmd_init, cmd_check_balance


class TestDiagnosePassti:
    def test_diagnose_no_serial(self):
        """When pyserial is not available or port doesn't exist, should return error."""
        result = diagnose_passti("/dev/nonexistent", baudrate=9600)
        assert result["serial_open"]["status"] == "error"

    def test_init_command_structure(self):
        """Verify INIT frame structure."""
        frame = cmd_init(("0" * 32).encode())
        # parse_response expects a response frame with STX, not a command frame
        # So we just verify the command frame was built
        assert frame[0] == 0x02  # STX
        assert len(frame) > 5

    def test_check_balance_command_structure(self):
        """Verify CheckBalance frame structure."""
        frame = cmd_check_balance(timeout_sec=5)
        assert frame[0] == 0x02  # STX
        assert len(frame) > 5

    def test_diagnose_result_keys(self):
        """Result should contain all expected keys."""
        result = diagnose_passti("/dev/nonexistent")
        assert "serial_port" in result
        assert "baudrate" in result
        assert "serial_open" in result
        assert "init" in result
        assert "reader_info" in result
        assert "check_balance" in result
