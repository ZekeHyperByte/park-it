"""Payment service — orchestrates cash, RFID, and e-money payments.

Business logic for processing payments at gate-out. This service:
1. Finds the active transaction
2. Calculates the tariff
3. Updates the transaction record
4. Publishes the appropriate gate command to the daemon
"""


from sqlalchemy.ext.asyncio import AsyncSession

from api.app.models import Member
from api.app.services.gate_command import publish_command
from api.app.services.transaction import (
    calculate_transaction_fee,
    complete_exit_transaction,
    find_active_transaction,
    get_current_shift,
)
from shared.events import (
    DeductStatus,
    DisplayTextCommand,
    PlayAudioCommand,
)
from shared.logging import get_logger

logger = get_logger("payment_service")


async def _enqueue_print_receipt(db: AsyncSession, gate_id: str, transaction_data: dict) -> None:
    """Direct ARQ enqueue of exit receipt — bypasses gate_out daemon (attended exit).

    Skips enqueue if the gate's receipt_printer peripheral is disabled.
    """
    try:
        from sqlalchemy import select

        from api.app.models import Gate
        from shared.redis import get_arq_redis

        gate_result = await db.execute(select(Gate).where(Gate.code == gate_id))
        gate = gate_result.scalar_one_or_none()
        if gate is None or not gate.is_peripheral_enabled("receipt_printer"):
            logger.info("receipt_print_skipped_disabled", gate_id=gate_id)
            return

        arq_redis = await get_arq_redis()
        tx_id = transaction_data.get("transaction_id")
        await arq_redis.enqueue_job(
            "print_receipt",
            gate_id=gate_id,
            transaction_data=transaction_data,
            _job_id=f"receipt:{tx_id}" if tx_id else None,
        )
        logger.info("receipt_job_enqueued", gate_id=gate_id, transaction_id=tx_id)
    except Exception as e:
        logger.error("receipt_enqueue_failed", gate_id=gate_id, error=str(e))


async def _enqueue_exit_snapshot(db: AsyncSession, gate_id: str, transaction_id: int) -> None:
    """Fire-and-forget: enqueue exit snapshot for every camera on this gate."""
    try:
        from sqlalchemy import select

        from api.app.models import Gate
        from shared.redis import get_arq_redis

        gate_result = await db.execute(select(Gate).where(Gate.code == gate_id))
        gate = gate_result.scalar_one_or_none()
        if gate is None:
            return
        cameras = gate.get_cameras()
        if not cameras:
            return
        arq_redis = await get_arq_redis()
        for idx, cam in enumerate(cameras):
            cam_key = cam.get("label") or str(idx)
            await arq_redis.enqueue_job(
                "take_snapshot",
                gate_id=gate_id,
                camera_url=cam["url"],
                transaction_id=transaction_id,
                snapshot_type="exit",
                camera_label=cam.get("label"),
                _job_id=f"snapshot:exit:{transaction_id}:{cam_key}",
                _queue_name="arq:queue:snapshot",
            )
        logger.info("exit_snapshot_enqueued", gate_id=gate_id, transaction_id=transaction_id, count=len(cameras))
    except Exception as e:
        logger.warning("exit_snapshot_enqueue_failed", gate_id=gate_id, transaction_id=transaction_id, error=str(e))


# ---------------------------------------------------------------------------
# Cash Payment
# ---------------------------------------------------------------------------

async def process_cash_payment(
    db: AsyncSession,
    *,
    gate_id: str,
    gate_out_id: int,
    barcode: str | None = None,
    card_number: str | None = None,
    plate_number: str | None = None,
    paid_amount: int,
    operator_id: int | None = None,
) -> dict:
    """Process a cash payment at gate-out.

    Args:
        db: Database session
        gate_id: Daemon gate ID (for Redis command)
        gate_out_id: Gate-out database ID
        barcode: Transaction barcode
        card_number: Transaction card number
        plate_number: Transaction plate number
        paid_amount: Amount received from driver
        operator_id: POS operator ID

    Returns:
        dict with transaction, fee, change_amount

    Raises:
        ValueError: If no active transaction found
    """
    tx = await find_active_transaction(
        db, barcode=barcode, card_number=card_number, plate_number=plate_number,
        for_update=True,
    )
    if tx is None:
        raise ValueError("No active transaction found")

    await _enqueue_exit_snapshot(db, gate_id, tx.id)

    fee = await calculate_transaction_fee(db, tx)
    shift = await get_current_shift(db)

    tx = await complete_exit_transaction(
        db,
        transaction=tx,
        gate_out_id=gate_out_id,
        payment_method="CASH",
        fee=fee,
        paid_amount=paid_amount,
        operator_id=operator_id,
        shift_id=shift.id if shift else None,
    )

    # Print receipt — direct ARQ (attended exit, no gate_out daemon)
    await _enqueue_print_receipt(
        db,
        gate_id,
        {
            "transaction_id": tx.id,
            "barcode": tx.barcode,
            "plate_number": tx.plate_number,
            "entry_time": tx.entry_time.isoformat() if tx.entry_time else None,
            "exit_time": tx.exit_time.isoformat() if tx.exit_time else None,
            "fee": fee,
            "paid_amount": paid_amount,
            "payment_method": "CASH",
        },
    )

    logger.info(
        "cash_payment_processed",
        transaction_id=tx.id,
        fee=fee,
        paid_amount=paid_amount,
        gate_id=gate_id,
    )

    return {
        "transaction": tx,
        "fee": fee,
        "change_amount": max(0, paid_amount - fee),
    }


# ---------------------------------------------------------------------------
# RFID Member Payment
# ---------------------------------------------------------------------------

async def process_rfid_payment(
    db: AsyncSession,
    *,
    gate_id: str,
    gate_out_id: int,
    card_number: str,
    operator_id: int | None = None,
) -> dict:
    """Process an RFID member payment at gate-out.

    Validates the member is active, finds the active transaction by card number,
    and completes it with zero fee.

    Args:
        db: Database session
        gate_id: Daemon gate ID
        gate_out_id: Gate-out database ID
        card_number: Member card number
        operator_id: POS operator ID

    Returns:
        dict with transaction, fee=0

    Raises:
        ValueError: If no active transaction or invalid member
    """
    from sqlalchemy import select

    # Validate member
    result = await db.execute(
        select(Member).where(
            Member.card_number == card_number,
            Member.is_active == True,  # noqa: E712
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise ValueError("Invalid or inactive member card")

    tx = await find_active_transaction(db, card_number=card_number, for_update=True)
    if tx is None:
        raise ValueError("No active transaction found for this card")

    await _enqueue_exit_snapshot(db, gate_id, tx.id)

    shift = await get_current_shift(db)

    tx = await complete_exit_transaction(
        db,
        transaction=tx,
        gate_out_id=gate_out_id,
        payment_method="RFID_MEMBER",
        fee=0,
        member_id=member.id,
        operator_id=operator_id,
        shift_id=shift.id if shift else None,
    )

    # Attended exit: POS shows member info, operator opens gate via booth_bridge.

    logger.info(
        "rfid_payment_processed",
        transaction_id=tx.id,
        member_id=member.id,
        gate_id=gate_id,
    )

    return {
        "transaction": tx,
        "fee": 0,
        "member": member,
    }


# ---------------------------------------------------------------------------
# E-Money Payment
# ---------------------------------------------------------------------------

async def process_emoney_deduct(
    db: AsyncSession,
    *,
    gate_id: str,
    gate_out_id: int,
    card_number: str,
    expected_transaction_counter: int = 0,
    operator_id: int | None = None,
) -> dict:
    """Initiate an e-money deduct at gate-out.

    Finds the active transaction, calculates the fee, and publishes a
    `deduct` command to the daemon. The daemon will execute the deduct
    on the PASSTI reader and publish a `deduct_result` event.

    Args:
        db: Database session
        gate_id: Daemon gate ID
        gate_out_id: Gate-out database ID
        card_number: E-money card number
        expected_transaction_counter: Expected transaction counter for verification
        operator_id: POS operator ID

    Returns:
        dict with transaction, fee, status="PENDING"

    Raises:
        ValueError: If no active transaction found
    """
    from shared.events import DeductCommand

    tx = await find_active_transaction(db, card_number=card_number, for_update=True)
    if tx is None:
        raise ValueError("No active transaction found for this card")

    fee = await calculate_transaction_fee(db, tx)

    # Update transaction to PENDING while deduct is in progress
    tx.payment_method = "PENDING"
    tx.fee = fee
    tx.gate_out_id = gate_out_id
    await db.flush()

    # Publish deduct command to daemon
    await publish_command(
        DeductCommand(
            gate_id=gate_id,
            amount=fee,
            timeout_seconds=30,
            expected_card_number=card_number,
            expected_transaction_counter=expected_transaction_counter,
        )
    )

    logger.info(
        "emoney_deduct_initiated",
        transaction_id=tx.id,
        fee=fee,
        card_number=card_number,
        gate_id=gate_id,
    )

    return {
        "transaction": tx,
        "fee": fee,
        "status": "PENDING",
    }


async def process_emoney_result(
    db: AsyncSession,
    *,
    gate_id: str,
    gate_out_id: int,
    card_number: str,
    status: DeductStatus,
    deduct_amount: int,
    balance_before: int,
    balance_after: int,
    transaction_counter: int,
    raw_response_hex: str,
    settlement_payload_hex: str = "",
    card_type: str | None = None,
    card_type_code: int | None = None,
    operator_id: int | None = None,
) -> dict:
    """Process the result of an e-money deduct operation.

    This is called when FastAPI receives the `deduct_result` event from
    the daemon (via Redis Pub/Sub or internal handler).

    Args:
        db: Database session
        gate_id: Daemon gate ID
        gate_out_id: Gate-out database ID
        card_number: E-money card number
        status: Deduct result status
        deduct_amount: Amount deducted
        balance_before: Balance before deduction
        balance_after: Balance after deduction
        transaction_counter: PASSTI transaction counter
        raw_response_hex: Raw PASSTI response
        operator_id: POS operator ID

    Returns:
        dict with transaction, emoney_transaction_id, success bool
    """
    from api.app.models import EmoneyTransaction

    tx = await find_active_transaction(db, card_number=card_number, for_update=True)
    if tx is None:
        raise ValueError("No active transaction found for this card")

    # Create EmoneyTransaction record
    emoney_tx = EmoneyTransaction(
        parking_transaction_id=tx.id,
        card_number=card_number,
        card_type=card_type,
        card_type_code=card_type_code,
        amount_deducted=deduct_amount,
        balance_before=balance_before,
        balance_after=balance_after,
        transaction_counter=transaction_counter,
        raw_response_hex=raw_response_hex,
        settlement_payload_hex=settlement_payload_hex or None,
        status=status.value,
    )
    db.add(emoney_tx)
    await db.flush()
    await db.refresh(emoney_tx)

    # Determine outcome based on status
    success = status in (DeductStatus.SUCCESS, DeductStatus.CORRECTION_VERIFIED)
    is_intermediate = status == DeductStatus.LOST_CONTACT
    is_terminal_failure = status in (
        DeductStatus.FAILED,
        DeductStatus.WRONG_CARD,
        DeductStatus.INSUFFICIENT_BALANCE,
        DeductStatus.CORRECTION_FAILED,
    )

    if success:
        shift = await get_current_shift(db)

        tx = await complete_exit_transaction(
            db,
            transaction=tx,
            gate_out_id=gate_out_id,
            payment_method="EMONEY",
            fee=deduct_amount,
            paid_amount=deduct_amount,
            emoney_transaction_id=emoney_tx.id,
            operator_id=operator_id,
            shift_id=shift.id if shift else None,
        )

        await _enqueue_exit_snapshot(db, gate_id, tx.id)

        # Attended exit: POS shows payment result, operator opens gate via booth_bridge.
        await _enqueue_print_receipt(
            db,
            gate_id,
            {
                "transaction_id": tx.id,
                "barcode": tx.barcode,
                "plate_number": tx.plate_number,
                "entry_time": tx.entry_time.isoformat() if tx.entry_time else None,
                "exit_time": tx.exit_time.isoformat() if tx.exit_time else None,
                "fee": deduct_amount,
                "paid_amount": deduct_amount,
                "payment_method": "EMONEY",
                "balance_after": balance_after,
            },
        )

        logger.info(
            "emoney_payment_success",
            transaction_id=tx.id,
            emoney_transaction_id=emoney_tx.id,
            fee=deduct_amount,
            gate_id=gate_id,
            status=status.value,
        )

    elif is_intermediate:
        # LOST_CONTACT: keep transaction in PENDING, prompt user to retry same card
        # Do NOT reset payment_method — the daemon will auto-retry
        logger.warning(
            "emoney_lost_contact",
            transaction_id=tx.id,
            emoney_transaction_id=emoney_tx.id,
            gate_id=gate_id,
        )

        # Notify operator and driver
        await publish_command(
            DisplayTextCommand(
                gate_id=gate_id,
                line1="Proses Koreksi",
                line2="Tempel Kartu Lagi",
            )
        )
        await publish_command(PlayAudioCommand(gate_id=gate_id, track=7))

    elif is_terminal_failure:
        # Reset payment method so other methods can be tried
        tx.payment_method = None
        tx.fee = None
        await db.flush()

        logger.warning(
            "emoney_payment_failed",
            transaction_id=tx.id,
            emoney_transaction_id=emoney_tx.id,
            status=status.value,
            gate_id=gate_id,
        )

    elif status == DeductStatus.TIMEOUT:
        # TIMEOUT: daemon should have run GetLastTransaction internally
        # If daemon still sends TIMEOUT, treat as terminal failure
        tx.payment_method = None
        tx.fee = None
        await db.flush()

        logger.warning(
            "emoney_payment_timeout",
            transaction_id=tx.id,
            emoney_transaction_id=emoney_tx.id,
            gate_id=gate_id,
        )

    return {
        "transaction": tx,
        "emoney_transaction_id": emoney_tx.id,
        "success": success,
        "status": status.value,
        "is_intermediate": is_intermediate,
    }
