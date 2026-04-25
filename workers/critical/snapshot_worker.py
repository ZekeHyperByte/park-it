"""Critical snapshot worker job."""

import os
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
    """Download camera snapshot and save locally.

    Args:
        gate_id: Gate identifier
        camera_url: HTTP URL to camera snapshot (e.g. http://cam1/snapshot.jpg)
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

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(camera_url)
            response.raise_for_status()
            image_data = response.content
    except Exception as e:
        logger.error("snapshot_download_failed", error=str(e), camera_url=camera_url)
        return {"status": "error", "message": f"Download failed: {e}"}

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

    # TODO: Create Snapshot database record in Week 3 when DB session is available in workers
    return {
        "status": "success",
        "filepath": str(filepath),
        "filename": filename,
        "size": len(image_data),
    }
