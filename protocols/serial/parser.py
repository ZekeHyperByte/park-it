"""Serial controller response parser.

Parses controller responses to extract:
- Input states (IN1, IN2, IN3, IN4)
- Wiegand data (W channel = RFID, X channel = UHF)

Serial-specific formats from v1:
- Frame: *<DATA>#
- IN1 ON:  *IN1ON#
- IN1 OFF: *IN1OFF#
- IN2 ON:  *IN2ON#
- IN3:     *IN3#
- IN3 OFF: *IN3OFF#
- IN4 ON:  *IN4ON#
- RFID:    *W<hex>#  or  *W<hex>#
- UHF:     *X<hex>#
"""



def parse_serial(response: bytes) -> dict:
    """Parse a Serial controller response.

    Args:
        response: Raw bytes from controller (may include * prefix and # suffix)

    Returns:
        Dict with extracted fields:
            - in1: bool (vehicle present)
            - in2: bool (ticket button)
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

    # Strip frame delimiters for easier parsing
    inner = text.strip("*#")

    # Parse IN states
    if "IN1ON" in inner:
        result["in1"] = True
    if "IN2ON" in inner:
        result["in2"] = True
    if "IN3OFF" in inner:
        result["in3"] = True  # Vehicle passed
    elif "IN3" in inner:
        result["in3"] = True
    if "IN4ON" in inner:
        result["in4"] = True

    # Parse Wiegand W (RFID)
    result["wiegand_w"] = _extract_wiegand(inner, "W")

    # Parse Wiegand X (UHF)
    result["wiegand_x"] = _extract_wiegand(inner, "X")

    return result


def _extract_wiegand(text: str, channel: str) -> str | None:
    """Extract card number from Wiegand channel.

    Args:
        text: Controller response text (without *# delimiters)
        channel: 'W' for RFID or 'X' for UHF

    Returns:
        Card number as decimal string, or None if not found
    """
    if channel not in text:
        return None

    try:
        parts = text.split(channel, 1)
        if len(parts) < 2:
            return None

        # Extract only valid hex characters
        hex_chars = ""
        for ch in parts[1]:
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
    """Extract RFID/UHF card number from Serial response.

    Returns:
        Tuple of (card_number, card_type) or (None, None)
    """
    parsed = parse_serial(response)

    if parsed["wiegand_w"]:
        return parsed["wiegand_w"], "RFID"
    if parsed["wiegand_x"]:
        return parsed["wiegand_x"], "UHF"

    return None, None
