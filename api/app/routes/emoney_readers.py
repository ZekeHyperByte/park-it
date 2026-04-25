"""Emoney reader management routes (admin only)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.emoney_reader import EmoneyReader
from api.app.schemas.common import SuccessResponse
from api.app.schemas.emoney_reader import (
    EmoneyReaderCreate,
    EmoneyReaderResponse,
    EmoneyReaderUpdate,
)
from api.app.utils.pagination import PaginationParams, paginated_list
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("emoney_reader_routes")

router = APIRouter(prefix="/emoney-readers", tags=["E-Money Readers"])


@router.get("", response_model=list[EmoneyReaderResponse])
async def list_emoney_readers(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[EmoneyReaderResponse]:
    """List all e-money readers."""
    stmt = select(EmoneyReader)
    if pagination.q:
        stmt = stmt.where(
            EmoneyReader.name.ilike(f"%{pagination.q}%")
            | EmoneyReader.code.ilike(f"%{pagination.q}%")
        )
    result = await paginated_list(db, stmt, skip=pagination.skip, limit=pagination.limit)
    return [EmoneyReaderResponse.model_validate(r) for r in result.items]


@router.post("", response_model=EmoneyReaderResponse, status_code=status.HTTP_201_CREATED)
async def create_emoney_reader(
    data: EmoneyReaderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> EmoneyReaderResponse:
    """Create a new e-money reader."""
    reader = EmoneyReader(**data.model_dump())
    db.add(reader)
    await db.commit()
    await db.refresh(reader)
    logger.info("emoney_reader_created", id=reader.id, code=reader.code)
    return EmoneyReaderResponse.model_validate(reader)


@router.get("/{reader_id}", response_model=EmoneyReaderResponse)
async def get_emoney_reader(
    reader_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> EmoneyReaderResponse:
    """Get e-money reader by ID."""
    from fastapi import HTTPException

    reader = await db.get(EmoneyReader, reader_id)
    if reader is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="E-money reader not found")
    return EmoneyReaderResponse.model_validate(reader)


@router.patch("/{reader_id}", response_model=EmoneyReaderResponse)
async def update_emoney_reader(
    reader_id: int,
    data: EmoneyReaderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> EmoneyReaderResponse:
    """Update e-money reader."""
    from fastapi import HTTPException

    reader = await db.get(EmoneyReader, reader_id)
    if reader is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="E-money reader not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(reader, field, value)

    await db.commit()
    await db.refresh(reader)
    logger.info("emoney_reader_updated", id=reader.id)
    return EmoneyReaderResponse.model_validate(reader)


@router.delete("/{reader_id}", response_model=SuccessResponse)
async def delete_emoney_reader(
    reader_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete e-money reader."""
    from fastapi import HTTPException

    reader = await db.get(EmoneyReader, reader_id)
    if reader is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="E-money reader not found")
    await db.delete(reader)
    await db.commit()
    logger.info("emoney_reader_deleted", id=reader_id)
    return SuccessResponse(message="E-money reader deleted")
