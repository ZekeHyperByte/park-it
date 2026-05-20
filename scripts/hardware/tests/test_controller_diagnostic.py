"""Tests for controller diagnostic."""


from scripts.hardware.controller_diagnostic import check_tcp_connect, run_full_diagnostic
from protocols.compass.protocol import cmd_stat


class TestTcpConnect:
    def test_tcp_connect_success(self):
        """Test that we can connect to an open port."""
        import socket
        # Start a temporary server
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        result = check_tcp_connect("127.0.0.1", port, timeout=1.0)
        server.close()

        assert result["status"] == "ok"
        assert result["host"] == "127.0.0.1"
        assert result["port"] == port
        assert "latency_ms" in result

    def test_tcp_connect_refused(self):
        """Test graceful failure when connection is refused."""
        result = check_tcp_connect("127.0.0.1", 65432, timeout=0.5)
        assert result["status"] == "refused"
        assert "error" in result

    def test_tcp_connect_timeout(self):
        """Test timeout on non-routable IP."""
        result = check_tcp_connect("192.0.2.1", 12345, timeout=0.1)
        assert result["status"] in ("timeout", "error")


class TestSendStatCommand:
    def test_stat_command_structure(self):
        """Verify STAT command sends correct bytes."""
        cmd = cmd_stat()
        assert cmd.startswith(b"\xa6")
        assert cmd.endswith(b"\xa9")
        assert b"STAT" in cmd


class TestRunFullDiagnostic:
    def test_full_diagnostic_refused(self):
        """Full diagnostic on refused port should report TCP failure."""
        result = run_full_diagnostic("127.0.0.1", 65433)
        assert result["tcp_connect"]["status"] == "refused"
        assert "stat_command" not in result
