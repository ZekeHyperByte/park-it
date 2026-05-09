"""Snapshot file serving routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_operator
from api.app.models.snapshot import Snapshot
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("snapshot_routes")
router = APIRouter(prefix="/snapshots", tags=["Snapshots"])


@router.get("/{snapshot_id}/image")
async def get_snapshot_image(
    snapshot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
) -> FileResponse:
    """Serve snapshot image file by Snapshot DB id."""
    snapshot = await db.get(Snapshot, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    path = Path(snapshot.file_path)
    if not path.exists():
        logger.warning("snapshot_file_missing", snapshot_id=snapshot_id, path=str(path))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot file not found")

    return FileResponse(path, media_type="image/jpeg", filename=snapshot.filename)
