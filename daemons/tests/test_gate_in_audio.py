"""Tests for gate_in daemon welcome audio and LED display."""

from unittest.mock import AsyncMock

import pytest

from daemons.gate_in import STATE_OPENING, GateInDaemon


def _make_config(hw_overrides: dict | None = None) -> dict:
    """Build a test config for cash-only mode."""
    hw = {
        "rfid": {"enabled": False},
        "ticket_printer": {"enabled": True},
        "emoney": {"enabled": False},
        "audio": {"enabled": True, "welcome_track": 1, "ticket_track": 2, "error_track": 11},
        "led": {"enabled": True},
        **(hw_overrides or {}),
    }
    return {
        "controller_host": "192.168.1.100",
        "controller_port": 5000,
        "hardware_config": hw,
        "has_close_sensor": False,
        "gate_close_duration_ms": 5000,
        "relay_mode": "SINGLE",
    }


class TestGateInAudio:
    @pytest.mark.asyncio
    async def test_vehicle_detected_plays_welcome_audio(self):
        """Welcome audio should play when vehicle is detected."""
        daemon = GateInDaemon(gate_id="GIN01", config=_make_config())
        daemon._send_controller_command = AsyncMock()
        daemon.publish_event = AsyncMock()
        daemon._transition = AsyncMock()
        daemon.state = "IDLE"

        await daemon._on_vehicle_detected()

        sent = [str(c.args[0]) for c in daemon._send_controller_command.call_args_list]
        mt_calls = [s for s in sent if "MT" in s]
        assert any("MT00001" in s for s in mt_calls), "Welcome audio (MT00001) should play"

    @pytest.mark.asyncio
    async def test_vehicle_detected_shows_welcome_led(self):
        """LED should show welcome message when vehicle is detected."""
        daemon = GateInDaemon(gate_id="GIN01", config=_make_config())
        daemon._send_controller_command = AsyncMock()
        daemon.publish_event = AsyncMock()
        daemon._transition = AsyncMock()
        daemon.state = "IDLE"

        await daemon._on_vehicle_detected()

        sent = [str(c.args[0]) for c in daemon._send_controller_command.call_args_list]
        ds_calls = [s for s in sent if "Selamat Datang" in s]
        assert any("DS" in s for s in ds_calls), "LED should show 'Selamat Datang'"

    @pytest.mark.asyncio
    async def test_vehicle_detected_no_audio_when_disabled(self):
        """No audio should play when audio is disabled in config."""
        config = _make_config({"audio": {"enabled": False}})
        daemon = GateInDaemon(gate_id="GIN01", config=config)
        daemon._send_controller_command = AsyncMock()
        daemon.publish_event = AsyncMock()
        daemon._transition = AsyncMock()
        daemon.state = "IDLE"

        await daemon._on_vehicle_detected()

        sent = [str(c.args[0]) for c in daemon._send_controller_command.call_args_list]
        mt_calls = [s for s in sent if "MT" in s]
        assert len(mt_calls) == 0, "No audio should play when disabled"

    @pytest.mark.asyncio
    async def test_vehicle_detected_uses_custom_track(self):
        """Custom welcome track should be used when configured."""
        config = _make_config({"audio": {"enabled": True, "welcome_track": 5}})
        daemon = GateInDaemon(gate_id="GIN01", config=config)
        daemon._send_controller_command = AsyncMock()
        daemon.publish_event = AsyncMock()
        daemon._transition = AsyncMock()
        daemon.state = "IDLE"

        await daemon._on_vehicle_detected()

        sent = [str(c.args[0]) for c in daemon._send_controller_command.call_args_list]
        mt_calls = [s for s in sent if "MT" in s]
        assert any("MT00005" in s for s in mt_calls), "Custom welcome track 5 should play"

    @pytest.mark.asyncio
    async def test_vehicle_passed_closes_dual_relay(self):
        """Gate should close when vehicle passes in DUAL relay mode."""
        config = _make_config()
        config["relay_mode"] = "DUAL"
        daemon = GateInDaemon(gate_id="GIN01", config=config)
        daemon._send_controller_command = AsyncMock()
        daemon.publish_event = AsyncMock()
        daemon._transition = AsyncMock()
        daemon.state = "OPENING"

        await daemon._on_vehicle_passed()

        sent = [str(c.args[0]) for c in daemon._send_controller_command.call_args_list]
        # DUAL close path sends cmd_close1() (relay1 off, relay3 off, relay2 on 1s).
        assert any("CLOSE1" in s for s in sent), "CLOSE1 should be sent in DUAL mode"

    @pytest.mark.asyncio
    async def test_vehicle_passed_no_close_single_relay(self):
        """Gate should NOT close when vehicle passes in SINGLE relay mode."""
        config = _make_config()
        config["relay_mode"] = "SINGLE"
        daemon = GateInDaemon(gate_id="GIN01", config=config)
        daemon._send_controller_command = AsyncMock()
        daemon.publish_event = AsyncMock()
        daemon._transition = AsyncMock()
        daemon.state = "OPENING"

        await daemon._on_vehicle_passed()

        sent = [str(c.args[0]) for c in daemon._send_controller_command.call_args_list]
        trig2_calls = [s for s in sent if "TRIG2" in s]
        assert len(trig2_calls) == 0, "No TRIG2 should be sent in SINGLE mode"


class TestGateInOpenReliability:
    """The critical gate-open path must retry across a brief controller
    reconnect, and on a hard-down controller report the failure (event + log)
    without advancing to OPENING. The command is always ACKed — a stale open
    must never be redelivered (it would ghost-open for the wrong vehicle)."""

    def _daemon(self) -> GateInDaemon:
        daemon = GateInDaemon(gate_id="GIN01", config=_make_config())
        daemon.publish_event = AsyncMock()
        daemon._on_gate_opened = AsyncMock()
        daemon._cmd_play_audio = AsyncMock()
        return daemon

    @pytest.mark.asyncio
    async def test_open_gate_acks_on_success(self):
        daemon = self._daemon()
        daemon._send_controller_command = AsyncMock(return_value=True)

        ok = await daemon.handle_command({"command_type": "open_gate"})

        assert ok is True, "successful open must ACK"
        daemon._on_gate_opened.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_open_gate_reports_failure_but_acks_when_hard_down(self, monkeypatch):
        daemon = self._daemon()
        daemon._send_controller_command = AsyncMock(return_value=False)
        monkeypatch.setattr("daemons.gate_in.asyncio.sleep", AsyncMock())

        ok = await daemon.handle_command({"command_type": "open_gate"})

        assert ok is True, "hard-down open is still ACKed — reported via event, not NACK"
        daemon._on_gate_opened.assert_not_awaited()
        assert daemon.state != STATE_OPENING, "must not claim OPENING on a failed open"
        event_types = [c.args[0].event_type for c in daemon.publish_event.call_args_list]
        assert "gate_open_failed" in event_types

    @pytest.mark.asyncio
    async def test_open_gate_retries_then_succeeds(self, monkeypatch):
        daemon = self._daemon()
        # First two writes dropped (controller mid-reconnect), third lands.
        daemon._send_controller_command = AsyncMock(side_effect=[False, False, True])
        monkeypatch.setattr("daemons.gate_in.asyncio.sleep", AsyncMock())

        ok = await daemon.handle_command({"command_type": "open_gate"})

        assert ok is True, "open must succeed once the controller reconnects"
        daemon._on_gate_opened.assert_awaited_once()
        assert daemon._send_controller_command.await_count == 3
