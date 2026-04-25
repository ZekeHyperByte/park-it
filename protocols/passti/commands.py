"""PASSTI high-level commands."""

from datetime import datetime

from protocols.passti.frame import (
    CMD_CANCEL_CORRECTION,
    CMD_CHECK_BALANCE,
    CMD_DEDUCT,
    CMD_DISPLAY_BUZZER,
    CMD_GET_LAST_TRANSACTION,
    CMD_INIT,
    CARD_TYPES,
    build_frame,
)


def _to_bcd(digits: str) -> bytes:
    """Convert decimal string to BCD bytes."""
    if len(digits) % 2:
        digits = "0" + digits
    return bytes(int(digits[i : i + 2], 16) for i in range(0, len(digits), 2))


def _bcd_timeout(sec: int) -> bytes:
    """Convert seconds to BCD timeout bytes."""
    return bytes([sec // 100, sec % 100])


def cmd_init(key: bytes) -> bytes:
    """Build INIT command frame."""
    return build_frame(CMD_INIT, key)


def cmd_check_balance(timeout_sec: int) -> bytes:
    """Build Check Balance command frame."""
    now = datetime.now()
    data = (
        _to_bcd(now.strftime("%d%m%Y"))
        + _to_bcd(now.strftime("%H%M%S"))
        + _bcd_timeout(timeout_sec)
    )
    return build_frame(CMD_CHECK_BALANCE, data)


def cmd_deduct(amount: int, timeout_sec: int) -> bytes:
    """Build Deduct command frame."""
    now = datetime.now()
    data = (
        _to_bcd(now.strftime("%d%m%Y"))
        + _to_bcd(now.strftime("%H%M%S"))
        + amount.to_bytes(4, "big")
        + _bcd_timeout(timeout_sec)
    )
    return build_frame(CMD_DEDUCT, data)


def cmd_get_last_transaction() -> bytes:
    """Build Get Last Transaction command frame."""
    return build_frame(CMD_GET_LAST_TRANSACTION)


def cmd_cancel_correction() -> bytes:
    """Build Cancel Correction command frame."""
    return build_frame(CMD_CANCEL_CORRECTION)


def cmd_buzzer(success: bool) -> bytes:
    """Build Buzzer command frame."""
    data = bytes([0x02, 0x00 if success else 0x01])
    return build_frame(CMD_DISPLAY_BUZZER, data)


def cmd_display(text: str) -> bytes:
    """Build Display command frame."""
    t = text.encode("ascii")[:16].ljust(16)
    tlv = bytes([0xD1, 0x01, 0x01, 0xD2, len(t)]) + t + bytes(
        [0xD3, 0x01, 0x02, 0xD4, 0x01, 0x01]
    )
    return build_frame(CMD_DISPLAY_BUZZER, bytes([0x03]) + tlv)


def cmd_reset_display() -> bytes:
    """Build Reset Display command frame."""
    return build_frame(CMD_DISPLAY_BUZZER, bytes([0x00]))


# Response parsers


def parse_check_balance_response(body: bytes) -> dict:
    """Parse Check Balance response body."""
    if len(body) < 13:
        return {"ok": False, "error": "Body too short"}
    return {
        "ok": True,
        "card_type_code": body[0],
        "card_type": CARD_TYPES.get(body[0], f"Unknown({body[0]:02X})"),
        "card_number": body[1:9].hex().upper(),
        "balance": int.from_bytes(body[9:13], "big"),
    }


def parse_deduct_response(body: bytes) -> dict:
    """Parse Deduct response body."""
    if len(body) < 40:
        return {"ok": False, "error": "Body too short"}
    return {
        "ok": True,
        "card_type_code": body[0],
        "card_type": CARD_TYPES.get(body[0], f"Unknown({body[0]:02X})"),
        "mid": body[1:9].hex().upper(),
        "tid": body[9:13].hex().upper(),
        "datetime_bcd": body[13:20].hex(),
        "card_number": body[20:28].hex().upper(),
        "deducted": int.from_bytes(body[28:32], "big"),
        "remaining": int.from_bytes(body[32:36], "big"),
        "trans_counter": int.from_bytes(body[36:40], "big"),
    }
