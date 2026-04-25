"""Transaction list routes (operator/admin)."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_operator
from api.app.models.parking_transaction import ParkingTransaction
from api.app.schemas.transaction import TransactionListItem
from api.app.utils.pagination import PaginationParams, paginated_list
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("transaction_routes")

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=list[TransactionListItem])
async def list_transactions(
    pagination: PaginationParams = Depends(),
    status_filter: str | None = Query(None, alias="status"),
    payment_method: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
) -> list[TransactionListItem]:
    """List parking transactions with optional filters."""
    stmt = select(ParkingTransaction).order_by(ParkingTransaction.entry_time.desc())

    if pagination.q:
        stmt = stmt.where(
            ParkingTransaction.barcode.ilike(f"%{pagination.q}%")
            | ParkingTransaction.card_number.ilike(f"%{pagination.q}%")
            | ParkingTransaction.plate_number.ilike(f"%{pagination.q}%")
        )

    if status_filter:
        stmt = stmt.where(ParkingTransaction.status == status_filter.upper())

    if payment_method:
        stmt = stmt.where(ParkingTransaction.payment_method == payment_method.upper())

    if date_from:
        stmt = stmt.where(ParkingTransaction.entry_time >= date_from)

    if date_to:
        stmt = stmt.where(ParkingTransaction.entry_time < date_to)

    result = await paginated_list(db, stmt, skip=pagination.skip, limit=pagination.limit)
    return [TransactionListItem.model_validate(t) for t in result.items]


@router.get("/{tx_id}", response_model=TransactionListItem)
async def get_transaction(
    tx_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
) -> TransactionListItem:
    """Get transaction by ID."""
    from fastapi import HTTPException, status

    tx = await db.get(ParkingTransaction, tx_id)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return TransactionListItem.model_validate(tx)
