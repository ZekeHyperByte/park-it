"""Camera management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.camera import Camera
from api.app.schemas.camera import CameraCreate, CameraResponse, CameraUpdate
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("camera_routes")
router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.get("", response_model=list[CameraResponse])
async def list_cameras(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[CameraResponse]:
    """List all cameras."""
    result = await db.execute(select(Camera))
    cameras = result.scalars().all()
    return [CameraResponse.model_validate(c) for c in cameras]


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    data: CameraCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> CameraResponse:
    """Create a new camera."""
    camera = Camera(**data.model_dump())
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    logger.info("camera_created", camera_id=camera.id, name=camera.name)
    return CameraResponse.model_validate(camera)


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> CameraResponse:
    """Get camera by ID."""
    camera = await db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return CameraResponse.model_validate(camera)


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    data: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> CameraResponse:
    """Update camera configuration."""
    camera = await db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)

    await db.commit()
    await db.refresh(camera)
    logger.info("camera_updated", camera_id=camera.id)
    return CameraResponse.model_validate(camera)


@router.delete("/{camera_id}", response_model=CameraResponse)
async def delete_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> CameraResponse:
    """Delete camera."""
    camera = await db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    await db.delete(camera)
    await db.commit()
    logger.info("camera_deleted", camera_id=camera_id)
    return CameraResponse.model_validate(camera)
