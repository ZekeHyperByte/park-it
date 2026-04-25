"""ENET controller INFO response parser.

Parses controller responses to extract:
- Input states (IN1, IN2, IN3, IN4)
- Wiegand data (W1 channel = RFID)

ENET-specific formats from v1:
- IN1 ON:  IN1ON, INP11, STAT10
- IN1 OFF: IN1OFF, IN10
- IN2 ON:  IN2ON, INP21
- IN2 OFF: IN20
- IN3 ON:  IN3ON, IN31
- IN3 OFF: IN30
- IN4 ON:  IN4ON, IN41
- RFID:    W1<hex>...;
"""

import re


def parse_info(response: bytes) -> dict:
    """Parse an INFO response from the ENET controller.

    Args:
        response: Raw bytes from controller

    Returns:
        Dict with extracted fields:
            - in1: bool (vehicle present)
            - in2: bool (ticket button)
            - in3: bool (gate close sensor / vehicle passed)
            - in4: bool (help button)
            - wiegand_w: str | None (RFID card number)
            - raw: str (decoded raw response)
    """
    text = response.decode("latin-1", errors="ignore")

    result = {
        "in1": False,
        "in2": False,
        "in3": False,
        "in4": False,
        "wiegand_w": None,
        "raw": text,
    }

    # Parse IN1 states
    if "IN1ON" in text or "INP11" in text or "STAT10" in text:
        result["in1"] = True

    # Parse IN2 states
    if "IN2ON" in text or "INP21" in text:
        result["in2"] = True

    # Parse IN3 states
    if "IN3ON" in text or "IN31" in text:
        result["in3"] = True

    # Parse IN4 states
    if "IN4ON" in text or "IN41" in text:
        result["in4"] = True

    # Parse Wiegand W1 (ENET RFID)
    result["wiegand_w"] = _extract_wiegand_w1(text)

    return result


def _extract_wiegand_w1(text: str) -> str | None:
    """Extract card number from ENET W1 channel.

    ENET uses W1 prefix instead of W.
    Format: W1<hex>...;

    Args:
        text: Decoded controller response

    Returns:
        Card number as decimal string, or None if not found
    """
    if "W1" not in text:
        return None

    try:
        parts = text.split("W1", 1)
        if len(parts) < 2:
            return None

        # Get everything before the ENET frame terminator
        remainder = parts[1].split(";", 1)[0]
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
    """Extract RFID card number from ENET response.

    Returns:
        Tuple of (card_number, card_type) or (None, None)
    """
    parsed = parse_info(response)

    if parsed["wiegand_w"]:
        return parsed["wiegand_w"], "RFID"

    return None, None
