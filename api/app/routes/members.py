"""Member management routes (admin/operator)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.member import Member
from api.app.schemas.common import SuccessResponse
from api.app.schemas.member import MemberCreate, MemberResponse, MemberUpdate
from api.app.utils.pagination import PaginationParams, paginated_list
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("member_routes")

router = APIRouter(prefix="/members", tags=["Members"])


@router.get("", response_model=list[MemberResponse])
async def list_members(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[MemberResponse]:
    """List all members."""
    stmt = select(Member)
    if pagination.q:
        stmt = stmt.where(
            Member.name.ilike(f"%{pagination.q}%")
            | Member.card_number.ilike(f"%{pagination.q}%")
            | Member.plate_number.ilike(f"%{pagination.q}%")
        )
    result = await paginated_list(db, stmt, skip=pagination.skip, limit=pagination.limit)
    return [MemberResponse.model_validate(m) for m in result.items]


@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def create_member(
    data: MemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> MemberResponse:
    """Create a new member."""
    member = Member(**data.model_dump())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    logger.info("member_created", id=member.id, card=member.card_number)
    return MemberResponse.model_validate(member)


@router.get("/{member_id}", response_model=MemberResponse)
async def get_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> MemberResponse:
    """Get member by ID."""
    from fastapi import HTTPException

    member = await db.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return MemberResponse.model_validate(member)


@router.patch("/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: int,
    data: MemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> MemberResponse:
    """Update member."""
    from fastapi import HTTPException

    member = await db.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(member, field, value)

    await db.commit()
    await db.refresh(member)
    logger.info("member_updated", id=member.id)
    return MemberResponse.model_validate(member)


@router.delete("/{member_id}", response_model=SuccessResponse)
async def delete_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete member."""
    from fastapi import HTTPException

    member = await db.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    await db.delete(member)
    await db.commit()
    logger.info("member_deleted", id=member_id)
    return SuccessResponse(message="Member deleted")
