"""Critical snapshot worker job."""

from datetime import datetime
from pathlib import Path

import httpx

from shared.logging import get_logger

logger = get_logger("snapshot_worker")

# Local snapshot storage directory
SNAPSHOT_DIR = Path("/var/lib/parking/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


async def take_snapshot(
    ctx,
    gate_id: str,
    camera_url: str,
    transaction_id: int | None = None,
    snapshot_type: str = "entry",
) -> dict:
    """Download or capture camera snapshot and save locally.

    Supports both HTTP snapshot URLs and RTSP streams.

    Args:
        gate_id: Gate identifier
        camera_url: HTTP URL or RTSP URL (e.g. http://cam1/snapshot.jpg, rtsp://cam1/stream)
        transaction_id: Optional parking transaction ID to link snapshot
        snapshot_type: 'entry' or 'exit'
    """
    logger.info(
        "take_snapshot_job",
        gate_id=gate_id,
        camera_url=camera_url,
        transaction_id=transaction_id,
        snapshot_type=snapshot_type,
    )

    # Determine capture method based on URL scheme
    is_rtsp = camera_url.lower().startswith("rtsp://")

    if is_rtsp:
        image_data = await _capture_rtsp(camera_url)
    else:
        image_data = await _download_http(camera_url)

    if image_data is None:
        return {"status": "error", "message": "Snapshot capture failed"}

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{gate_id}_{snapshot_type}_{timestamp}.jpg"
    filepath = SNAPSHOT_DIR / filename

    # Save to filesystem
    try:
        filepath.write_bytes(image_data)
    except Exception as e:
        logger.error("snapshot_save_failed", error=str(e), filepath=str(filepath))
        return {"status": "error", "message": f"Save failed: {e}"}

    logger.info("snapshot_saved", filepath=str(filepath), size=len(image_data))

    return {
        "status": "success",
        "filepath": str(filepath),
        "filename": filename,
        "size": len(image_data),
    }


async def _download_http(camera_url: str) -> bytes | None:
    """Download snapshot via HTTP."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(camera_url)
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error("snapshot_download_failed", error=str(e), camera_url=camera_url)
        return None


async def _capture_rtsp(camera_url: str) -> bytes | None:
    """Capture frame from RTSP stream."""
    from workers.critical.rtsp_snapshot import capture_rtsp_frame_to_bytes

    try:
        return await capture_rtsp_frame_to_bytes(camera_url)
    except Exception as e:
        logger.error("rtsp_capture_failed", error=str(e), camera_url=camera_url)
        return None
