"""Compass controller STAT response parser.

Parses controller responses to extract:
- Input states (IN1, IN2, IN3, IN4)
- Wiegand data (W channel = RFID, X channel = UHF)
- Status flags
"""

import re


def parse_stat(response: bytes) -> dict:
    """Parse a STAT response from the controller.

    Args:
        response: Raw bytes from controller

    Returns:
        Dict with extracted fields:
            - in1: bool (ticket button / vehicle present)
            - in2: bool (vehicle detect / trigger)
            - in3: bool (gate close sensor / vehicle passed)
            - in4: bool (help button)
            - wiegand_w: str | None (RFID card number)
            - wiegand_x: str | None (UHF card number)
            - raw: str (decoded raw response)
    """
    text = response.decode("latin-1", errors="ignore")

    result = {
        "in1": False,
        "in2": False,
        "in3": False,
        "in4": False,
        "wiegand_w": None,
        "wiegand_x": None,
        "raw": text,
    }

    # Parse IN states
    # STAT responses may contain "IN1ON", "IN2ON", etc.
    if "IN1ON" in text or "STAT10" in text:
        result["in1"] = True
    if "IN2ON" in text or "STAT1" in text:
        result["in2"] = True
    if "IN3ON" in text:
        result["in3"] = True
    if "IN4ON" in text:
        result["in4"] = True

    # Parse Wiegand W (RFID)
    result["wiegand_w"] = _extract_wiegand(text, "W")

    # Parse Wiegand X (UHF)
    result["wiegand_x"] = _extract_wiegand(text, "X")

    return result


def _extract_wiegand(text: str, channel: str) -> str | None:
    """Extract card number from Wiegand channel.

    Args:
        text: Decoded controller response
        channel: 'W' for RFID or 'X' for UHF

    Returns:
        Card number as decimal string, or None if not found
    """
    if channel not in text:
        return None

    try:
        # Split on channel letter and get hex before footer or next non-hex char
        parts = text.split(channel, 1)
        if len(parts) < 2:
            return None

        remainder = parts[1].split("\xa9", 1)[0]
        if not remainder:
            return None

        # Extract only valid hex characters
        hex_chars = ""
        for ch in remainder:
            if ch in "0123456789abcdefABCDEF":
                hex_chars += ch
            else:
                break

        if not hex_chars:
            return None

        # Convert hex to decimal card number
        card_num = str(int(hex_chars, 16))
        return card_num
    except (ValueError, IndexError):
        return None


def parse_rfid_card(response: bytes) -> tuple[str | None, str | None]:
    """Extract RFID/UHF card number from response.

    Returns:
        Tuple of (card_number, card_type) or (None, None)
    """
    parsed = parse_stat(response)

    if parsed["wiegand_w"]:
        return parsed["wiegand_w"], "RFID"
    if parsed["wiegand_x"]:
        return parsed["wiegand_x"], "UHF"

    return None, None
