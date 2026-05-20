"""RTSP snapshot capture using ffmpeg.

Provides fallback mechanisms for capturing still frames from RTSP camera streams.
Primary: ffmpeg CLI (fastest, most reliable)
Fallback: None (ffmpeg is required for RTSP support)
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

from shared.logging import get_logger

logger = get_logger("rtsp_snapshot")

FFMPEG_TIMEOUT = 8.0  # seconds


async def capture_rtsp_frame(
    rtsp_url: str,
    output_path: Path,
    timeout: float = FFMPEG_TIMEOUT,
) -> bool:
    """Capture a single JPEG frame from an RTSP stream using ffmpeg.

    Args:
        rtsp_url: RTSP URL (e.g. rtsp://192.168.1.201/stream)
        output_path: Where to save the JPEG file
        timeout: Maximum time to wait for capture

    Returns:
        True if frame was captured successfully, False otherwise
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        logger.error("ffmpeg_not_found", rtsp_url=rtsp_url)
        return False

    # ffmpeg args: -y overwrite, -i input, -vframes 1 single frame,
    #              -q:v 2 quality, -f image2 format
    cmd = [
        ffmpeg_path,
        "-y",
        "-rtsp_transport",
        "tcp",
        "-i",
        rtsp_url,
        "-vframes",
        "1",
        "-q:v",
        "2",
        "-f",
        "image2",
        str(output_path),
    ]

    logger.info(
        "rtsp_capture_start",
        rtsp_url=rtsp_url,
        output=str(output_path),
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            _, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.warning("rtsp_capture_timeout", rtsp_url=rtsp_url, timeout=timeout)
            return False

        if proc.returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="ignore")[:500]
            logger.error(
                "rtsp_capture_failed",
                rtsp_url=rtsp_url,
                returncode=proc.returncode,
                stderr=stderr_text,
            )
            return False

        # Verify file was created and has content
        if not output_path.exists() or output_path.stat().st_size == 0:
            logger.error("rtsp_capture_empty_file", rtsp_url=rtsp_url)
            return False

        logger.info(
            "rtsp_capture_success",
            rtsp_url=rtsp_url,
            output=str(output_path),
            size=output_path.stat().st_size,
        )
        return True

    except Exception as e:
        logger.error("rtsp_capture_exception", rtsp_url=rtsp_url, error=str(e))
        return False


async def capture_rtsp_frame_to_bytes(
    rtsp_url: str,
    timeout: float = FFMPEG_TIMEOUT,
) -> bytes | None:
    """Capture a single JPEG frame from RTSP and return as bytes.

    Uses a temporary file internally.

    Args:
        rtsp_url: RTSP URL
        timeout: Maximum time to wait

    Returns:
        JPEG image bytes, or None if capture failed
    """
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        success = await capture_rtsp_frame(rtsp_url, tmp_path, timeout)
        if success:
            return tmp_path.read_bytes()
        return None
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
