"""Report routes (admin only)."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.emoney_transaction import EmoneyTransaction
from api.app.models.parking_transaction import ParkingTransaction
from api.app.schemas.report import EmoneyReport, SummaryReport
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("report_routes")

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary", response_model=SummaryReport)
async def get_summary_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SummaryReport:
    """Get parking summary report for date range."""
    # Total transactions
    total_stmt = select(func.count(ParkingTransaction.id)).where(
        ParkingTransaction.entry_time >= date_from,
        ParkingTransaction.entry_time < date_to,
    )
    total_result = await db.execute(total_stmt)
    total_transactions = total_result.scalar() or 0

    # Revenue by method
    revenue_stmt = select(
        ParkingTransaction.payment_method,
        func.sum(ParkingTransaction.fee),
        func.count(ParkingTransaction.id),
    ).where(
        ParkingTransaction.entry_time >= date_from,
        ParkingTransaction.entry_time < date_to,
    ).group_by(ParkingTransaction.payment_method)
    revenue_result = await db.execute(revenue_stmt)

    cash_revenue = 0
    emoney_revenue = 0
    rfid_revenue = 0
    for method, fee_sum, count in revenue_result.all():
        if method == "CASH":
            cash_revenue = fee_sum or 0
        elif method == "EMONEY":
            emoney_revenue = fee_sum or 0
        elif method == "RFID_MEMBER":
            rfid_revenue = fee_sum or 0

    # Total revenue
    total_revenue_stmt = select(func.sum(ParkingTransaction.fee)).where(
        ParkingTransaction.entry_time >= date_from,
        ParkingTransaction.entry_time < date_to,
    )
    total_revenue_result = await db.execute(total_revenue_stmt)
    total_revenue = total_revenue_result.scalar() or 0

    # Status counts
    active_stmt = select(func.count(ParkingTransaction.id)).where(
        ParkingTransaction.entry_time >= date_from,
        ParkingTransaction.entry_time < date_to,
        ParkingTransaction.status == "ACTIVE",
    )
    active_result = await db.execute(active_stmt)

    completed_stmt = select(func.count(ParkingTransaction.id)).where(
        ParkingTransaction.entry_time >= date_from,
        ParkingTransaction.entry_time < date_to,
        ParkingTransaction.status == "COMPLETED",
    )
    completed_result = await db.execute(completed_stmt)

    avg_fee = total_revenue / total_transactions if total_transactions > 0 else 0

    return SummaryReport(
        total_transactions=total_transactions,
        total_revenue=total_revenue,
        cash_revenue=cash_revenue,
        emoney_revenue=emoney_revenue,
        rfid_revenue=rfid_revenue,
        total_vehicles=total_transactions,
        average_fee=round(avg_fee, 2),
        active_transactions=active_result.scalar() or 0,
        completed_transactions=completed_result.scalar() or 0,
    )


@router.get("/emoney", response_model=EmoneyReport)
async def get_emoney_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> EmoneyReport:
    """Get e-money report for date range."""
    # Total e-money transactions
    total_stmt = select(func.count(EmoneyTransaction.id)).where(
        EmoneyTransaction.created_at >= date_from,
        EmoneyTransaction.created_at < date_to,
    )
    total_result = await db.execute(total_stmt)
    total_emoney = total_result.scalar() or 0

    # Total deducted
    deducted_stmt = select(func.sum(EmoneyTransaction.amount_deducted)).where(
        EmoneyTransaction.created_at >= date_from,
        EmoneyTransaction.created_at < date_to,
    )
    deducted_result = await db.execute(deducted_stmt)
    total_deducted = deducted_result.scalar() or 0

    # Status counts
    status_stmt = select(
        EmoneyTransaction.status,
        func.count(EmoneyTransaction.id),
    ).where(
        EmoneyTransaction.created_at >= date_from,
        EmoneyTransaction.created_at < date_to,
    ).group_by(EmoneyTransaction.status)
    status_result = await db.execute(status_stmt)

    success_count = 0
    failed_count = 0
    lost_contact_count = 0
    for status, count in status_result.all():
        if status == "SUCCESS":
            success_count = count
        elif status in ("FAILED", "CORRECTION_FAILED"):
            failed_count += count
        elif status == "LOST_CONTACT":
            lost_contact_count = count

    # Settlement counts
    settled_stmt = select(func.count(EmoneyTransaction.id)).where(
        EmoneyTransaction.created_at >= date_from,
        EmoneyTransaction.created_at < date_to,
        EmoneyTransaction.settlement_batch_id.isnot(None),
    )
    settled_result = await db.execute(settled_stmt)

    unsettled_stmt = select(func.count(EmoneyTransaction.id)).where(
        EmoneyTransaction.created_at >= date_from,
        EmoneyTransaction.created_at < date_to,
        EmoneyTransaction.settlement_batch_id.is_(None),
        EmoneyTransaction.status == "SUCCESS",
    )
    unsettled_result = await db.execute(unsettled_stmt)

    avg_deduct = total_deducted / total_emoney if total_emoney > 0 else 0

    return EmoneyReport(
        total_emoney_transactions=total_emoney,
        total_deducted=total_deducted,
        success_count=success_count,
        failed_count=failed_count,
        lost_contact_count=lost_contact_count,
        average_deduct_amount=round(avg_deduct, 2),
        unsettled_count=unsettled_result.scalar() or 0,
        settled_count=settled_result.scalar() or 0,
    )
