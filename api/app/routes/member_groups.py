"""Member group management routes (admin only)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.member_group import MemberGroup
from api.app.schemas.common import SuccessResponse
from api.app.schemas.member_group import (
    MemberGroupCreate,
    MemberGroupResponse,
    MemberGroupUpdate,
)
from api.app.utils.pagination import PaginationParams, paginated_list
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("member_group_routes")

router = APIRouter(prefix="/member-groups", tags=["Member Groups"])


@router.get("", response_model=list[MemberGroupResponse])
async def list_member_groups(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[MemberGroupResponse]:
    """List all member groups."""
    stmt = select(MemberGroup)
    if pagination.q:
        stmt = stmt.where(
            MemberGroup.name.ilike(f"%{pagination.q}%")
            | MemberGroup.code.ilike(f"%{pagination.q}%")
        )
    result = await paginated_list(db, stmt, skip=pagination.skip, limit=pagination.limit)
    return [MemberGroupResponse.model_validate(g) for g in result.items]


@router.post("", response_model=MemberGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_member_group(
    data: MemberGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> MemberGroupResponse:
    """Create a new member group."""
    group = MemberGroup(**data.model_dump())
    db.add(group)
    await db.commit()
    await db.refresh(group)
    logger.info("member_group_created", id=group.id, code=group.code)
    return MemberGroupResponse.model_validate(group)


@router.get("/{group_id}", response_model=MemberGroupResponse)
async def get_member_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> MemberGroupResponse:
    """Get member group by ID."""
    from fastapi import HTTPException

    group = await db.get(MemberGroup, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member group not found")
    return MemberGroupResponse.model_validate(group)


@router.patch("/{group_id}", response_model=MemberGroupResponse)
async def update_member_group(
    group_id: int,
    data: MemberGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> MemberGroupResponse:
    """Update member group."""
    from fastapi import HTTPException

    group = await db.get(MemberGroup, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member group not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(group, field, value)

    await db.commit()
    await db.refresh(group)
    logger.info("member_group_updated", id=group.id)
    return MemberGroupResponse.model_validate(group)


@router.delete("/{group_id}", response_model=SuccessResponse)
async def delete_member_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete member group."""
    from fastapi import HTTPException

    group = await db.get(MemberGroup, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member group not found")
    await db.delete(group)
    await db.commit()
    logger.info("member_group_deleted", id=group_id)
    return SuccessResponse(message="Member group deleted")
