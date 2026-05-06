"""Payment Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Requests
# =============================================================================

class CashPaymentRequest(BaseModel):
    """Cash payment confirmation request."""

    gate_id: str = Field(..., description="Daemon gate ID")
    gate_out_id: int = Field(..., description="Gate-out database ID")
    transaction_id: int | None = Field(None, description="Transaction ID (optional)")
    barcode: str | None = Field(None, description="Ticket barcode")
    plate_number: str | None = Field(None, description="License plate")
    paid_amount: int = Field(..., ge=0, description="Amount received from driver")


class RfidPaymentRequest(BaseModel):
    """RFID member payment request."""

    gate_id: str = Field(..., description="Daemon gate ID")
    gate_out_id: int = Field(..., description="Gate-out database ID")
    card_number: str = Field(..., description="Member card number")


class EmoneyDeductRequest(BaseModel):
    """E-money deduct initiation request."""

    gate_id: str = Field(..., description="Daemon gate ID")
    gate_out_id: int = Field(..., description="Gate-out database ID")
    card_number: str = Field(..., description="E-money card number")
    expected_transaction_counter: int = Field(default=0, description="Expected transaction counter")


class EmoneyResultRequest(BaseModel):
    """E-money deduct result callback (internal or from daemon event handler)."""

    gate_id: str = Field(..., description="Daemon gate ID")
    gate_out_id: int = Field(..., description="Gate-out database ID")
    card_number: str = Field(..., description="E-money card number")
    status: str = Field(..., description="Deduct result status")
    deduct_amount: int = Field(..., ge=0)
    balance_before: int = Field(..., ge=0)
    balance_after: int = Field(..., ge=0)
    transaction_counter: int = Field(..., ge=0)
    raw_response_hex: str = Field(default="")


class EmoneyBoothResultRequest(BaseModel):
    """E-money result from booth bridge (machine-to-machine)."""
    gate_id: str = Field(..., description="Daemon gate ID")
    gate_out_id: int = Field(..., description="Gate-out database ID")
    card_number: str = Field(..., description="E-money card number")
    status: str = Field(..., description="Deduct result status")
    deduct_amount: int = Field(..., ge=0)
    balance_before: int = Field(..., ge=0)
    balance_after: int = Field(..., ge=0)
    transaction_counter: int = Field(..., ge=0)
    raw_response_hex: str = Field(default="")


class TransactionLookupRequest(BaseModel):
    """Lookup an active transaction."""

    barcode: str | None = None
    card_number: str | None = None
    plate_number: str | None = None


# =============================================================================
# Responses
# =============================================================================

class PaymentResponse(BaseModel):
    """Standard payment response."""

    model_config = ConfigDict(from_attributes=True)

    success: bool
    message: str
    transaction_id: int | None = None
    fee: int | None = None
    change_amount: int | None = None
    payment_method: str | None = None
    receipt_queued: bool = False


class TransactionLookupResponse(BaseModel):
    """Active transaction lookup response."""

    model_config = ConfigDict(from_attributes=True)

    found: bool
    transaction: dict | None = None
    fee: int | None = None


class EmoneyResultResponse(BaseModel):
    """E-money result processing response."""

    success: bool
    message: str
    transaction_id: int | None = None
    emoney_transaction_id: int | None = None
    status: str | None = None
