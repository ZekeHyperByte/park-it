"""Payment routes."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.api_key import require_api_key
from api.app.middleware.auth import require_operator
from api.app.schemas.common import ErrorResponse, SuccessResponse
from api.app.schemas.payment import (
    CashPaymentRequest,
    EmoneyBoothResultRequest,
    EmoneyDeductRequest,
    EmoneyResultRequest,
    PaymentResponse,
    RfidPaymentRequest,
    TransactionLookupRequest,
    TransactionLookupResponse,
)
from api.app.services.payment import (
    process_cash_payment,
    process_emoney_deduct,
    process_emoney_result,
    process_rfid_payment,
)
from api.app.services.transaction import calculate_transaction_fee, find_active_transaction
from api.database import get_db
from shared.events import DeductStatus
from shared.logging import get_logger
from api.app.middleware.metrics import payment_attempts_total, payment_success_total

logger = get_logger("payment_routes")

router = APIRouter(prefix="/payments", tags=["Payments"])


def _get_operator_id(user: dict) -> int | None:
    """Extract operator ID from JWT payload."""
    sub = user.get("sub")
    return int(sub) if sub else None


@router.post("/cash", response_model=PaymentResponse)
async def cash_payment(
    request: Request,
    payment: CashPaymentRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> PaymentResponse:
    """Process cash payment and open gate."""
    payment_attempts_total.labels(method="cash").inc()
    try:
        result = await process_cash_payment(
            db,
            gate_id=payment.gate_id,
            gate_out_id=payment.gate_out_id,
            barcode=payment.barcode,
            plate_number=payment.plate_number,
            paid_amount=payment.paid_amount,
            operator_id=_get_operator_id(user),
        )
        payment_success_total.labels(method="cash").inc()
        return PaymentResponse(
            success=True,
            message="Payment successful. Receipt printed.",
            transaction_id=result["transaction"].id,
            fee=result["fee"],
            change_amount=result["change_amount"],
            payment_method="CASH",
            receipt_queued=True,
        )
    except ValueError as e:
        logger.warning("cash_payment_failed", error=str(e), gate_id=payment.gate_id)
        return PaymentResponse(
            success=False,
            message=str(e),
        )


@router.post("/rfid", response_model=PaymentResponse)
async def rfid_payment(
    request: Request,
    payment: RfidPaymentRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> PaymentResponse:
    """Process RFID member payment and open gate."""
    payment_attempts_total.labels(method="rfid").inc()
    try:
        result = await process_rfid_payment(
            db,
            gate_id=payment.gate_id,
            gate_out_id=payment.gate_out_id,
            card_number=payment.card_number,
            operator_id=_get_operator_id(user),
        )
        payment_success_total.labels(method="rfid").inc()
        return PaymentResponse(
            success=True,
            message="RFID payment successful",
            transaction_id=result["transaction"].id,
            fee=0,
            change_amount=0,
            payment_method="RFID_MEMBER",
        )
    except ValueError as e:
        logger.warning("rfid_payment_failed", error=str(e), gate_id=payment.gate_id)
        return PaymentResponse(
            success=False,
            message=str(e),
        )


@router.post("/emoney/deduct", response_model=PaymentResponse)
async def emoney_deduct(
    request: Request,
    payment: EmoneyDeductRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> PaymentResponse:
    """Initiate e-money deduct. Daemon will publish result via Pub/Sub."""
    payment_attempts_total.labels(method="emoney").inc()
    try:
        result = await process_emoney_deduct(
            db,
            gate_id=payment.gate_id,
            gate_out_id=payment.gate_out_id,
            card_number=payment.card_number,
            expected_transaction_counter=payment.expected_transaction_counter,
            operator_id=_get_operator_id(user),
        )
        payment_success_total.labels(method="emoney").inc()
        return PaymentResponse(
            success=True,
            message="E-money deduct initiated",
            transaction_id=result["transaction"].id,
            fee=result["fee"],
            payment_method="PENDING",
        )
    except ValueError as e:
        logger.warning("emoney_deduct_failed", error=str(e), gate_id=payment.gate_id)
        return PaymentResponse(
            success=False,
            message=str(e),
        )


@router.post("/emoney/result", response_model=PaymentResponse)
async def emoney_result(
    request: Request,
    result: EmoneyResultRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> PaymentResponse:
    """Process e-money deduct result (called by event handler or manually)."""
    try:
        status_enum = DeductStatus(result.status)
    except ValueError:
        return PaymentResponse(
            success=False,
            message=f"Invalid deduct status: {result.status}",
        )

    try:
        proc_result = await process_emoney_result(
            db,
            gate_id=result.gate_id,
            gate_out_id=result.gate_out_id,
            card_number=result.card_number,
            status=status_enum,
            deduct_amount=result.deduct_amount,
            balance_before=result.balance_before,
            balance_after=result.balance_after,
            transaction_counter=result.transaction_counter,
            raw_response_hex=result.raw_response_hex,
            operator_id=_get_operator_id(user),
        )
        return PaymentResponse(
            success=proc_result["success"],
            message="E-money payment processed" if proc_result["success"] else "E-money payment failed",
            transaction_id=proc_result["transaction"].id,
            fee=result.deduct_amount if proc_result["success"] else None,
            payment_method="EMONEY" if proc_result["success"] else None,
        )
    except ValueError as e:
        logger.warning("emoney_result_failed", error=str(e), gate_id=result.gate_id)
        return PaymentResponse(
            success=False,
            message=str(e),
        )


@router.post("/emoney/booth-result", response_model=PaymentResponse)
async def emoney_booth_result(
    request: Request,
    result: EmoneyBoothResultRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
) -> PaymentResponse:
    """Process e-money deduct result from booth bridge (machine-to-machine)."""
    try:
        status_enum = DeductStatus(result.status)
    except ValueError:
        return PaymentResponse(
            success=False,
            message=f"Invalid deduct status: {result.status}",
        )

    try:
        proc_result = await process_emoney_result(
            db,
            gate_id=result.gate_id,
            gate_out_id=result.gate_out_id,
            card_number=result.card_number,
            status=status_enum,
            deduct_amount=result.deduct_amount,
            balance_before=result.balance_before,
            balance_after=result.balance_after,
            transaction_counter=result.transaction_counter,
            raw_response_hex=result.raw_response_hex,
            operator_id=None,
        )
        return PaymentResponse(
            success=proc_result["success"],
            message="E-money payment processed" if proc_result["success"] else "E-money payment failed",
            transaction_id=proc_result["transaction"].id,
            fee=result.deduct_amount if proc_result["success"] else None,
            payment_method="EMONEY" if proc_result["success"] else None,
        )
    except ValueError as e:
        logger.warning("emoney_booth_result_failed", error=str(e), gate_id=result.gate_id)
        return PaymentResponse(success=False, message=str(e))


@router.post("/lookup", response_model=TransactionLookupResponse)
async def lookup_transaction(
    request: Request,
    lookup: TransactionLookupRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> TransactionLookupResponse:
    """Look up an active transaction by barcode, card, or plate."""
    tx = await find_active_transaction(
        db,
        barcode=lookup.barcode,
        card_number=lookup.card_number,
        plate_number=lookup.plate_number,
    )
    if tx is None:
        return TransactionLookupResponse(found=False)

    fee = await calculate_transaction_fee(db, tx)

    return TransactionLookupResponse(
        found=True,
        transaction={
            "id": tx.id,
            "barcode": tx.barcode,
            "card_number": tx.card_number,
            "plate_number": tx.plate_number,
            "entry_time": tx.entry_time.isoformat() if tx.entry_time else None,
            "vehicle_type_id": tx.vehicle_type_id,
            "gate_in_id": tx.gate_in_id,
            "payment_method": tx.payment_method,
        },
        fee=fee,
    )
