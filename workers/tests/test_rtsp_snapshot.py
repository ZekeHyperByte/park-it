"""Tests for RTSP snapshot capture."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workers.critical.rtsp_snapshot import capture_rtsp_frame_to_bytes


class TestCaptureRtspFrameToBytes:
    """Test RTSP capture via image2pipe."""

    @pytest.mark.asyncio
    async def test_ffmpeg_not_found(self):
        """Should return None when ffmpeg is not installed."""
        with patch("workers.critical.rtsp_snapshot.shutil.which", return_value=None):
            result = await capture_rtsp_frame_to_bytes("rtsp://192.168.1.1/stream")
        assert result is None

    @pytest.mark.asyncio
    async def test_successful_capture(self):
        """Should return stdout bytes when ffmpeg succeeds."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"fake_jpeg_data", b""))

        with patch("workers.critical.rtsp_snapshot.shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                result = await capture_rtsp_frame_to_bytes("rtsp://192.168.1.1/stream")

        assert result == b"fake_jpeg_data"

    @pytest.mark.asyncio
    async def test_ffmpeg_failure(self):
        """Should return None when ffmpeg exits with error."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Connection refused"))

        with patch("workers.critical.rtsp_snapshot.shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                result = await capture_rtsp_frame_to_bytes("rtsp://192.168.1.1/stream")

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_stdout(self):
        """Should return None when ffmpeg succeeds but stdout is empty."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch("workers.critical.rtsp_snapshot.shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                result = await capture_rtsp_frame_to_bytes("rtsp://192.168.1.1/stream")

        assert result is None

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Should return None when ffmpeg times out."""
        mock_proc = MagicMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        async def slow_communicate():
            import asyncio
            await asyncio.sleep(100)
            return (b"", b"")

        mock_proc.communicate = slow_communicate

        with patch("workers.critical.rtsp_snapshot.shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                result = await capture_rtsp_frame_to_bytes(
                    "rtsp://192.168.1.1/stream",
                    timeout=0.01,
                )

        assert result is None
        mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_ffmpeg_command_args(self):
        """Should invoke ffmpeg with correct arguments."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"fake", b""))

        called_args = []

        async def mock_exec(*args, **_):
            called_args.extend(args)
            return mock_proc

        with patch("workers.critical.rtsp_snapshot.shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
                await capture_rtsp_frame_to_bytes("rtsp://192.168.1.1/stream")

        assert "/usr/bin/ffmpeg" in called_args
        assert "image2pipe" in called_args
