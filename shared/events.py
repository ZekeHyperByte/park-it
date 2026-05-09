"""Pydantic schemas for all Redis IPC messages.

Daemon -> FastAPI: parking.events.{gate_id} (Pub/Sub)
FastAPI -> Daemon: parking.commands.{gate_id} (Redis Streams)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class PaymentMethod(str, Enum):
    """Payment method types."""

    CASH = "CASH"
    RFID_MEMBER = "RFID_MEMBER"
    EMONEY = "EMONEY"
    PENDING = "PENDING"


class GateMode(str, Enum):
    """Gate-in operational mode."""

    CASH = "CASH"
    RFID = "RFID"
    EMONEY = "EMONEY"


class DeductStatus(str, Enum):
    """E-money deduct result status."""

    SUCCESS = "SUCCESS"
    LOST_CONTACT = "LOST_CONTACT"
    CORRECTION_VERIFIED = "CORRECTION_VERIFIED"
    CORRECTION_FAILED = "CORRECTION_FAILED"
    WRONG_CARD = "WRONG_CARD"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    TIMEOUT = "TIMEOUT"
    FAILED = "FAILED"


class TransactionStatus(str, Enum):
    """Parking transaction status."""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    LOST_CONTACT = "LOST_CONTACT"


class AlertType(str, Enum):
    """Operator alert types."""

    TIMEOUT = "TIMEOUT"
    HARDWARE_FAILURE = "HARDWARE_FAILURE"
    SENSOR_STUCK = "SENSOR_STUCK"
    LOST_CONTACT = "LOST_CONTACT"
    CORRECTION_FAILED = "CORRECTION_FAILED"


# =============================================================================
# Daemon -> FastAPI Events (Pub/Sub)
# =============================================================================

class BaseEvent(BaseModel):
    """Base class for all events."""

    event_type: str
    gate_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VehicleDetectedEvent(BaseEvent):
    """Vehicle detected at sensor."""

    event_type: Literal["vehicle_detected"] = "vehicle_detected"
    sensor: str


class GateClosedEvent(BaseEvent):
    """Gate has closed."""

    event_type: Literal["gate_closed"] = "gate_closed"


class RfidCardReadEvent(BaseEvent):
    """RFID card read by Wiegand reader."""

    event_type: Literal["rfid_card_read"] = "rfid_card_read"
    card_number: str
    channel: str  # W or X


class PasstiCardTapEvent(BaseEvent):
    """PASSTI card tapped."""

    event_type: Literal["passti_card_tap"] = "passti_card_tap"
    card_number: str
    card_type: str


class TicketButtonPressedEvent(BaseEvent):
    """Ticket button pressed."""

    event_type: Literal["ticket_button_pressed"] = "ticket_button_pressed"


class HelpButtonPressedEvent(BaseEvent):
    """IN4 help button pressed — operator assistance requested."""

    event_type: Literal["help_button_pressed"] = "help_button_pressed"


class VehiclePassedEvent(BaseEvent):
    """Vehicle has passed through gate."""

    event_type: Literal["vehicle_passed"] = "vehicle_passed"


class EmoneyPrintDecisionEvent(BaseEvent):
    """Driver made print decision at entry gate (e-money mode)."""

    event_type: Literal["emoney_print_decision"] = "emoney_print_decision"
    printed: bool
    card_number: str
    card_type: str
    balance: int


class GateOpenedEvent(BaseEvent):
    """Gate has opened."""

    event_type: Literal["gate_opened"] = "gate_opened"


class DeductResultEvent(BaseEvent):
    """E-money deduct result."""

    event_type: Literal["deduct_result"] = "deduct_result"
    status: DeductStatus
    card_number: str
    card_type: str
    card_type_code: int = 0
    deduct_amount: int
    balance_before: int
    balance_after: int
    transaction_counter: int
    raw_response_hex: str
    settlement_payload_hex: str = ""


class CancelCorrectionResultEvent(BaseEvent):
    """Cancel correction result."""

    event_type: Literal["cancel_correction_result"] = "cancel_correction_result"
    card_number: str
    card_type: str


class TimeoutAlertEvent(BaseEvent):
    """Payment timeout alert."""

    event_type: Literal["timeout_alert"] = "timeout_alert"
    transaction_id: str | None
    waiting_seconds: int


class VehicleLeftEvent(BaseEvent):
    """Vehicle left without payment."""

    event_type: Literal["vehicle_left"] = "vehicle_left"
    reason: str  # passed, abandoned


class PlayAudioEvent(BaseEvent):
    """Request frontend to play audio locally (serial/booth gates only)."""

    event_type: Literal["play_audio"] = "play_audio"
    track: int


class ReaderErrorEvent(BaseEvent):
    """E-money reader error."""

    event_type: Literal["reader_error"] = "reader_error"
    error_code: str
    message: str


class HeartbeatEvent(BaseEvent):
    """Daemon heartbeat."""

    event_type: Literal["heartbeat"] = "heartbeat"
    controller_ok: bool
    passti_ok: bool


# Union type for all events
RedisEvent = (
    VehicleDetectedEvent
    | GateClosedEvent
    | RfidCardReadEvent
    | PasstiCardTapEvent
    | TicketButtonPressedEvent
    | HelpButtonPressedEvent
    | VehiclePassedEvent
    | EmoneyPrintDecisionEvent
    | GateOpenedEvent
    | DeductResultEvent
    | CancelCorrectionResultEvent
    | TimeoutAlertEvent
    | VehicleLeftEvent
    | PlayAudioEvent
    | ReaderErrorEvent
    | HeartbeatEvent
)


# =============================================================================
# FastAPI -> Daemon Commands (Redis Streams)
# =============================================================================

class BaseCommand(BaseModel):
    """Base class for all commands."""

    command_type: str
    gate_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OpenGateCommand(BaseCommand):
    """Open the gate."""

    command_type: Literal["open_gate"] = "open_gate"
    duration_seconds: int | None = None
    reason: str = "operator"


class CloseGateCommand(BaseCommand):
    """Close the gate."""

    command_type: Literal["close_gate"] = "close_gate"
    reason: str = "operator"


class PlayAudioCommand(BaseCommand):
    """Play audio track."""

    command_type: Literal["play_audio"] = "play_audio"
    track: int


class DisplayTextCommand(BaseCommand):
    """Display text on LED."""

    command_type: Literal["display_text"] = "display_text"
    line1: str
    line2: str = ""
    brightness: int = 100
    mode: str = "normal"


class BuzzerCommand(BaseCommand):
    """Trigger buzzer."""

    command_type: Literal["buzzer"] = "buzzer"
    success: bool = True


class PrintTicketCommand(BaseCommand):
    """Print entry ticket."""

    command_type: Literal["print_ticket"] = "print_ticket"
    barcode: str
    gate_name: str
    barcode_format: str = "CODE39"


class PrintTicketThenOpenCommand(BaseCommand):
    """Print entry ticket then open gate (cash flow)."""

    command_type: Literal["print_ticket_then_open"] = "print_ticket_then_open"
    barcode: str
    gate_name: str


class PrintReceiptCommand(BaseCommand):
    """Print exit receipt."""

    command_type: Literal["print_receipt"] = "print_receipt"
    transaction_data: dict  # serialized transaction info


class CheckBalanceCommand(BaseCommand):
    """Check PASSTI card balance."""

    command_type: Literal["check_balance"] = "check_balance"
    minimum_threshold: int


class DeductCommand(BaseCommand):
    """Deduct from PASSTI card."""

    command_type: Literal["deduct"] = "deduct"
    amount: int
    timeout_seconds: int
    expected_card_number: str
    expected_transaction_counter: int


class CancelCorrectionCommand(BaseCommand):
    """Cancel correction mode."""

    command_type: Literal["cancel_correction"] = "cancel_correction"


class CashPaymentConfirmedCommand(BaseCommand):
    """Cash payment confirmed by POS."""

    command_type: Literal["cash_payment_confirmed"] = "cash_payment_confirmed"
    transaction_id: str


class EmoneyPaymentConfirmedCommand(BaseCommand):
    """E-money payment confirmed by POS or booth bridge."""

    command_type: Literal["emoney_payment_confirmed"] = "emoney_payment_confirmed"
    transaction_id: str


class ResetGateCommand(BaseCommand):
    """Reset gate to IDLE."""

    command_type: Literal["reset_gate"] = "reset_gate"
    reason: str


# Union type for all commands
RedisCommand = (
    OpenGateCommand
    | CloseGateCommand
    | PlayAudioCommand
    | DisplayTextCommand
    | BuzzerCommand
    | PrintTicketCommand
    | PrintTicketThenOpenCommand
    | PrintReceiptCommand
    | CheckBalanceCommand
    | DeductCommand
    | CancelCorrectionCommand
    | CashPaymentConfirmedCommand
    | EmoneyPaymentConfirmedCommand
    | ResetGateCommand
)
