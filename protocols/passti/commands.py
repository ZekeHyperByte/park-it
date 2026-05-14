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
    _bcd_timeout,
    _to_bcd,
    build_frame,
)


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
    """Parse Deduct response body.

    Branches on card type: 0x09 = QR Payment (different layout per V1.12 §C.1),
    all others = prepaid card.
    """
    if len(body) < 1:
        return {"ok": False, "error": "Body too short"}

    card_type_code = body[0]

    if card_type_code == 0x09:
        return _parse_qr_deduct_response(body)

    # Prepaid card: CardType(1)+MID(8)+TID(4)+DT(7)+CardNo(8)+Amt(4)+Remain(4)+Counter(4)+Log(n)
    if len(body) < 40:
        return {"ok": False, "error": "Body too short for prepaid card response"}
    return {
        "ok": True,
        "card_type_code": card_type_code,
        "card_type": CARD_TYPES.get(card_type_code, f"Unknown({card_type_code:02X})"),
        "mid": body[1:9].hex().upper(),
        "tid": body[9:13].hex().upper(),
        "datetime_bcd": body[13:20].hex(),
        "card_number": body[20:28].hex().upper(),
        "deducted": int.from_bytes(body[28:32], "big"),
        "remaining": int.from_bytes(body[32:36], "big"),
        "trans_counter": int.from_bytes(body[36:40], "big"),
    }


def _parse_qr_deduct_response(body: bytes) -> dict:
    """Parse QR Payment deduct response body (V1.12 §C.1).

    Layout: CardType(1)+MID(8)+TID(4)+DT(7)+QRType(1)+Amt(4)+OrderID(22)+TrxID(36)+RFULen(1)+RFU(n)
    """
    # Minimum fixed fields before RFU: 1+8+4+7+1+4+22+36+1 = 84 bytes
    MIN_QR_LEN = 84
    if len(body) < MIN_QR_LEN:
        return {"ok": False, "error": "Body too short for QR payment response"}

    # Offsets: CardType[0] MID[1:9] TID[9:13] DT[13:20] QRType[20]
    #          Amt[21:25] OrderID[25:47] TrxID[47:83] RFULen[83] RFU[84:]
    qr_payment_type = body[20]
    order_id_hex = body[25:47].hex().upper()
    trx_id_hex = body[47:83].hex()
    rfu_len = body[83]
    try:
        trx_id = bytes.fromhex(trx_id_hex).decode("ascii", errors="replace")
    except Exception:
        trx_id = trx_id_hex

    return {
        "ok": True,
        "card_type_code": 0x09,
        "card_type": "QR Payment",
        "mid": body[1:9].hex().upper(),
        "tid": body[9:13].hex().upper(),
        "datetime_bcd": body[13:20].hex(),
        "qr_payment_type": qr_payment_type,
        "deducted": int.from_bytes(body[21:25], "big"),
        "order_id_hex": order_id_hex,
        "trx_id": trx_id,
        "rfu": body[84 : 84 + rfu_len].hex() if rfu_len > 0 else "",
        # QR payment has no remaining balance or per-card transaction counter
        "card_number": "",
        "remaining": 0,
        "trans_counter": 0,
    }
