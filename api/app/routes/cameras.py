"""Camera management routes."""

import base64

import httpx
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


@router.get("/{camera_id}/test")
async def test_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> dict:
    """Proxy a snapshot from this camera and return it as base64 JPEG.

    Fetches from the server's network perspective so cameras on isolated
    VLANs (unreachable from the browser) can still be verified.
    """
    camera = await db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    is_rtsp = camera.type == "rtsp" or (
        camera.rtsp_url is not None and camera.snapshot_url is None
    )

    if is_rtsp:
        url = camera.rtsp_url
        if not url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No RTSP URL configured")
        from workers.critical.rtsp_snapshot import capture_rtsp_frame_to_bytes
        image_bytes = await capture_rtsp_frame_to_bytes(url)
    else:
        url = camera.snapshot_url
        if not url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No snapshot URL configured")
        auth = None
        if camera.username and camera.password:
            if camera.auth_type == "digest":
                auth = httpx.DigestAuth(camera.username, camera.password)
            else:
                auth = httpx.BasicAuth(camera.username, camera.password)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, auth=auth)
                response.raise_for_status()
                image_bytes = response.content
        except httpx.HTTPStatusError as e:
            logger.warning("camera_test_http_error", camera_id=camera_id, status=e.response.status_code)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Camera returned HTTP {e.response.status_code}",
            )
        except Exception as e:
            logger.warning("camera_test_failed", camera_id=camera_id, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to reach camera: {e}",
            )

    if image_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Camera did not return an image",
        )

    logger.info("camera_test_ok", camera_id=camera_id, size=len(image_bytes))
    return {
        "success": True,
        "snapshot": base64.b64encode(image_bytes).decode(),
    }
