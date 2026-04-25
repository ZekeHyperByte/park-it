"""Transaction service — creation, lookup, and completion of parking transactions.

This module handles the core database operations for parking transactions,
including entry creation, active transaction lookup, and exit completion.
"""

from datetime import datetime, time, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.models import ParkingTransaction, Shift, VehicleType
from api.app.services.tariff import DEFAULT_TARIFF_CONFIG, TariffConfig, VehicleTypeRate, calculate_tariff
from shared.logging import get_logger

logger = get_logger("transaction_service")


async def create_entry_transaction(
    db: AsyncSession,
    *,
    barcode: str | None = None,
    card_number: str | None = None,
    plate_number: str | None = None,
    vehicle_type_id: int | None = None,
    gate_in_id: int | None = None,
    payment_method: Literal["CASH", "RFID_MEMBER", "EMONEY", "PENDING"] = "CASH",
    member_id: int | None = None,
) -> ParkingTransaction:
    """Create a new parking transaction at entry time.

    Args:
        db: Database session
        barcode: Ticket barcode (for CASH mode)
        card_number: RFID/e-money card number
        plate_number: License plate
        vehicle_type_id: Vehicle type FK
        gate_in_id: Gate-in FK
        payment_method: Payment method at entry
        member_id: Member FK (for RFID mode)

    Returns:
        Created ParkingTransaction
    """
    tx = ParkingTransaction(
        barcode=barcode,
        card_number=card_number,
        plate_number=plate_number,
        vehicle_type_id=vehicle_type_id,
        gate_in_id=gate_in_id,
        entry_time=datetime.now(timezone.utc),
        payment_method=payment_method,
        member_id=member_id,
        status="ACTIVE",
    )
    db.add(tx)
    await db.flush()
    await db.refresh(tx)

    logger.info(
        "transaction_created",
        transaction_id=tx.id,
        barcode=barcode,
        card_number=card_number,
        gate_in_id=gate_in_id,
    )
    return tx


async def find_active_transaction(
    db: AsyncSession,
    *,
    barcode: str | None = None,
    card_number: str | None = None,
    plate_number: str | None = None,
) -> ParkingTransaction | None:
    """Find an active (uncompleted) parking transaction.

    Searches by barcode, card_number, or plate_number. Only one criterion
    should be provided; they are checked in order of specificity.

    Args:
        db: Database session
        barcode: Ticket barcode
        card_number: Card number
        plate_number: License plate

    Returns:
        Active ParkingTransaction or None
    """
    query = select(ParkingTransaction).where(ParkingTransaction.status == "ACTIVE")

    if barcode:
        query = query.where(ParkingTransaction.barcode == barcode)
    elif card_number:
        query = query.where(ParkingTransaction.card_number == card_number)
    elif plate_number:
        query = query.where(ParkingTransaction.plate_number == plate_number)
    else:
        return None

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_vehicle_type_tariff_config(
    db: AsyncSession,
    vehicle_type_id: int | None,
) -> TariffConfig:
    """Build TariffConfig from database VehicleType or fallback to default.

    Args:
        db: Database session
        vehicle_type_id: Vehicle type primary key

    Returns:
        TariffConfig for fee calculation
    """
    if vehicle_type_id is None:
        return DEFAULT_TARIFF_CONFIG

    result = await db.execute(
        select(VehicleType).where(VehicleType.id == vehicle_type_id)
    )
    vt = result.scalar_one_or_none()
    if vt is None:
        return DEFAULT_TARIFF_CONFIG

    # Build config from database rates
    return TariffConfig(
        vehicle_types={
            vt.code: VehicleTypeRate(
                hourly_rate=vt.hourly_rate or vt.base_tariff,
                daily_cap=vt.max_daily_cap or 999999,
            )
        },
        grace_period_minutes=15,
    )


async def calculate_transaction_fee(
    db: AsyncSession,
    transaction: ParkingTransaction,
    exit_time: datetime | None = None,
) -> int:
    """Calculate parking fee for a transaction.

    Args:
        db: Database session
        transaction: The parking transaction
        exit_time: Exit timestamp (defaults to now)

    Returns:
        Fee in IDR
    """
    if exit_time is None:
        exit_time = datetime.now(timezone.utc)

    config = await get_vehicle_type_tariff_config(db, transaction.vehicle_type_id)

    # Determine vehicle type code
    vt_code = "MOBIL"  # default
    if transaction.vehicle_type_id:
        result = await db.execute(
            select(VehicleType.code).where(VehicleType.id == transaction.vehicle_type_id)
        )
        code = result.scalar_one_or_none()
        if code:
            vt_code = code

    try:
        fee = calculate_tariff(
            entry_time=transaction.entry_time,
            exit_time=exit_time,
            vehicle_type_code=vt_code,
            config=config,
        )
    except ValueError:
        fee = 0

    return fee


async def get_current_shift(db: AsyncSession) -> Shift | None:
    """Determine the current active shift based on current time.

    Args:
        db: Database session

    Returns:
        Current Shift or None
    """
    now = datetime.now(timezone.utc).time()

    result = await db.execute(
        select(Shift)
        .where(Shift.is_active == True)  # noqa: E712
        .order_by(Shift.start_time)
    )
    shifts = result.scalars().all()

    for shift in shifts:
        start = shift.start_time
        end = shift.end_time

        if start <= end:
            # Normal range (e.g., 08:00 - 16:00)
            if start <= now <= end:
                return shift
        else:
            # Overnight range (e.g., 22:00 - 06:00)
            if now >= start or now <= end:
                return shift

    # Fallback: return first active shift
    return shifts[0] if shifts else None


async def complete_exit_transaction(
    db: AsyncSession,
    transaction: ParkingTransaction,
    *,
    gate_out_id: int,
    payment_method: Literal["CASH", "RFID_MEMBER", "EMONEY"],
    fee: int,
    paid_amount: int | None = None,
    member_id: int | None = None,
    emoney_transaction_id: int | None = None,
    operator_id: int | None = None,
    shift_id: int | None = None,
) -> ParkingTransaction:
    """Complete a parking transaction at exit.

    Args:
        db: Database session
        transaction: The active transaction to complete
        gate_out_id: Exit gate FK
        payment_method: Final payment method
        fee: Calculated fee
        paid_amount: Amount paid (for CASH)
        member_id: Member FK (for RFID)
        emoney_transaction_id: E-money transaction FK
        operator_id: Operator who processed payment
        shift_id: Assigned shift (gate_out_time)

    Returns:
        Updated ParkingTransaction
    """
    now = datetime.now(timezone.utc)

    transaction.gate_out_id = gate_out_id
    transaction.exit_time = now
    transaction.payment_method = payment_method
    transaction.fee = fee
    transaction.paid_amount = paid_amount
    transaction.member_id = member_id
    transaction.emoney_transaction_id = emoney_transaction_id
    transaction.operator_id = operator_id
    transaction.shift_id = shift_id
    transaction.status = "COMPLETED"

    await db.flush()
    await db.refresh(transaction)

    logger.info(
        "transaction_completed",
        transaction_id=transaction.id,
        payment_method=payment_method,
        fee=fee,
        gate_out_id=gate_out_id,
    )
    return transaction
