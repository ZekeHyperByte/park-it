"""Site configuration routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.site_config import SiteConfig
from api.app.schemas.site_config import SiteConfigResponse, SiteConfigUpdate
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("site_config_routes")

router = APIRouter(prefix="/site-config", tags=["Site Config"])


@router.get("", response_model=SiteConfigResponse)
async def get_site_config(
    db: AsyncSession = Depends(get_db),
) -> SiteConfigResponse:
    """Get site configuration (singleton)."""
    result = await db.execute(select(SiteConfig))
    config = result.scalar_one_or_none()

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site config not set",
        )

    return SiteConfigResponse.model_validate(config)


@router.put("", response_model=SiteConfigResponse)
async def update_site_config(
    data: SiteConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SiteConfigResponse:
    """Update site configuration (create if not exists)."""
    result = await db.execute(select(SiteConfig))
    config = result.scalar_one_or_none()

    if config is None:
        create_data = data.model_dump(exclude_unset=True)
        if "name" not in create_data or create_data["name"] is None:
            create_data["name"] = "E-Parking"
        config = SiteConfig(**create_data)
        db.add(config)
    else:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    logger.info("site_config_updated")
    return SiteConfigResponse.model_validate(config)
