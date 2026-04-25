#!/usr/bin/env python3
"""
E-Parking v2 — Hardware Integration Test
=========================================

Tests each hardware component connected to the Compass controller.
Uses the v2 protocol modules (protocols/compass/, protocols/passti/).

Prerequisites:
- Controller powered on and connected via LAN to this laptop
- Laptop Ethernet interface has IP 192.168.1.x/24
- RFID reader connected to Wiegand W channel
- E-money reader connected to controller Serial2 (QR5 passthrough)
- IN1 and IN2 buttons wired to controller inputs

Usage:
    python scripts/hardware_test.py
"""

import socket
import time
import sys

from protocols.compass.protocol import (
    CompassTransport,
    cmd_ds,
    cmd_dsu,
    cmd_mt,
    cmd_qr5,
    cmd_stat,
    cmd_trig1,
)
from protocols.compass.parser import parse_stat, parse_rfid_card
from protocols.passti.commands import (
    cmd_buzzer,
    cmd_check_balance,
    cmd_display,
    cmd_init,
    cmd_reset_display,
    parse_check_balance_response,
)
from protocols.passti.frame import parse_response

CONTROLLER_IP = "192.168.1.100"
CONTROLLER_PORT = 5000
EMONEY_INIT_KEY = bytes.fromhex("758F40D46D95D1641448AA19B9282C05")
CARD_TIMEOUT = 10  # seconds for e-money scan


def banner(text: str):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def prompt(msg: str) -> bool:
    """Ask user yes/no question."""
    while True:
        resp = input(f"{msg} [y/n]: ").strip().lower()
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("  Please answer y or n")


def send_recv_raw(transport: CompassTransport, cmd: bytes, timeout: float = 1.0) -> bytes:
    """Send command and read response from controller."""
    transport.send(cmd)
    transport._sock.settimeout(timeout)
    try:
        return transport._sock.recv(1024)
    except socket.timeout:
        return b""


def send_emoney_cmd(transport: CompassTransport, passti_frame: bytes, timeout: float = 12.0) -> dict:
    """Send e-money command via controller Serial2 passthrough (QR5/QT).

    Uses PASSTI frame length from header instead of searching for \\xa9,
    because \\xa9 bytes can appear inside encrypted transaction log data.
    """
    qr_cmd = cmd_qr5(passti_frame)
    transport.send(qr_cmd)

    buffer = b""
    qt_data = None
    expected_qt_len = None

    start = time.time()
    while time.time() - start < timeout:
        try:
            transport._sock.settimeout(0.5)
            chunk = transport._sock.recv(4096)
            if chunk:
                buffer += chunk
        except socket.timeout:
            pass

        # Find \\xa6QT header
        idx = buffer.find(b"\xa6QT")
        if idx == -1:
            continue

        # We have QT header — calculate expected frame length from PASSTI header
        qt_start = idx + 3  # After \\xa6QT
        if expected_qt_len is None and len(buffer) >= qt_start + 3:
            if buffer[qt_start] == 0x02:  # STX
                payload_len = (buffer[qt_start + 1] << 8) | buffer[qt_start + 2]
                expected_qt_len = 3 + payload_len + 1  # STX+LEN + payload + LRC

        # If we know expected length, check if we have enough data
        if expected_qt_len and len(buffer) >= qt_start + expected_qt_len:
            qt_data = buffer[qt_start : qt_start + expected_qt_len]
            break

    if qt_data is None:
        if len(buffer) == 0:
            return {"ok": False, "error": "No response from controller"}
        if b"\xa6QT" not in buffer:
            return {"ok": False, "error": "No card detected (timeout)", "status": (0x01, 0x10, 0x02), "raw": buffer.hex()}
        if expected_qt_len:
            return {"ok": False, "error": f"Incomplete QT response (expected {expected_qt_len} bytes)", "raw": buffer.hex()}
        return {"ok": False, "error": "Incomplete QT response", "raw": buffer.hex()}

    return parse_response(qt_data)


# ═══════════════════════════════════════════════════════════
# TEST 1: TCP Connectivity
# ═══════════════════════════════════════════════════════════

def test_connectivity() -> CompassTransport | None:
    banner("TEST 1: Controller TCP Connectivity")
    print(f"  Connecting to {CONTROLLER_IP}:{CONTROLLER_PORT}...")

    transport = CompassTransport(CONTROLLER_IP, CONTROLLER_PORT)
    try:
        transport.connect(timeout=5.0)
        print(f"  ✅ Connected successfully!")
        return transport
    except Exception as e:
        print(f"  ❌ Failed to connect: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# TEST 2: STAT Polling
# ═══════════════════════════════════════════════════════════

def test_stat_polling(transport: CompassTransport):
    banner("TEST 2: Controller STAT Polling")
    print("  Sending STAT command...")

    response = send_recv_raw(transport, cmd_stat(), timeout=1.0)
    if not response:
        print("  ❌ No response from controller")
        return False

    parsed = parse_stat(response)
    print(f"  Raw response: {parsed['raw'][:80]}...")
    print(f"  IN1 (ticket button): {'ON' if parsed['in1'] else 'OFF'}")
    print(f"  IN2 (vehicle detect): {'ON' if parsed['in2'] else 'OFF'}")
    print(f"  IN3 (gate close sensor): {'ON' if parsed['in3'] else 'OFF'}")
    print(f"  IN4 (help button): {'ON' if parsed['in4'] else 'OFF'}")
    print(f"  Wiegand W (RFID): {parsed['wiegand_w'] or 'None'}")
    print(f"  Wiegand X (UHF): {parsed['wiegand_x'] or 'None'}")
    print("  ✅ STAT parsing works")
    return True


# ═══════════════════════════════════════════════════════════
# TEST 3: Gate Trigger (Output)
# ═══════════════════════════════════════════════════════════

def test_gate_trigger(transport: CompassTransport):
    banner("TEST 3: Gate Trigger (TRIG1)")
    print("  WARNING: Gate will OPEN in 3 seconds!")
    print("  Make sure gate area is clear.")

    if not prompt("  Proceed with gate open test?"):
        print("  ⏭️  Skipped")
        return None

    print("  Sending TRIG1...")
    transport.send(cmd_trig1())
    time.sleep(0.5)

    if prompt("  Did the gate open?"):
        print("  ✅ Gate trigger works")
        return True
    else:
        print("  ❌ Gate did not open")
        return False


# ═══════════════════════════════════════════════════════════
# TEST 4: Audio Playback (Output)
# ═══════════════════════════════════════════════════════════

def test_audio(transport: CompassTransport):
    banner("TEST 4: Audio Playback")
    print("  Will play track 00002 (Silakan Ambil Tiket)")

    if not prompt("  Proceed with audio test?"):
        print("  ⏭️  Skipped")
        return None

    print("  Playing audio track 00002...")
    transport.send(cmd_mt("00002"))
    time.sleep(2)

    if prompt("  Did you hear audio?"):
        print("  ✅ Audio playback works")
        return True
    else:
        print("  ❌ No audio heard")
        return False


# ═══════════════════════════════════════════════════════════
# TEST 5: LED Display (Output)
# ═══════════════════════════════════════════════════════════

def test_display(transport: CompassTransport):
    banner("TEST 5: LED Display")
    print("  Will show 'TEST DISPLAY' on the controller LED")

    if not prompt("  Proceed with display test?"):
        print("  ⏭️  Skipped")
        return None

    print("  Sending display command...")
    transport.send(cmd_ds("TEST", "DISPLAY"))
    time.sleep(3)

    result = prompt("  Did you see 'TEST DISPLAY' on the LED?")

    print("  Resetting display...")
    transport.send(cmd_dsu())
    time.sleep(1)

    if result:
        print("  ✅ LED display works")
        return True
    else:
        print("  ❌ Display not visible")
        return False


# ═══════════════════════════════════════════════════════════
# TEST 6: Input Detection (IN1 / IN2 Buttons)
# ═══════════════════════════════════════════════════════════

def test_inputs(transport: CompassTransport):
    banner("TEST 6: Input Detection (IN1 / IN2 Buttons)")
    print("  We will test each button. Press the button when prompted.")

    results = {}

    for name, key in [("IN1 (ticket button)", "in1"), ("IN2 (vehicle detect)", "in2")]:
        if not prompt(f"  Test {name}?"):
            print(f"  ⏭️  {name} skipped")
            results[key] = None
            continue

        print(f"  Press and hold {name} now...")
        detected = False
        for _ in range(10):  # Poll for 5 seconds
            response = send_recv_raw(transport, cmd_stat(), timeout=0.5)
            if response:
                parsed = parse_stat(response)
                if parsed[key]:
                    detected = True
                    break
            time.sleep(0.5)

        if detected:
            print(f"  ✅ {name} detected")
            results[key] = True
        else:
            print(f"  ❌ {name} NOT detected")
            results[key] = False

    return results


# ═══════════════════════════════════════════════════════════
# TEST 7: RFID Card Read
# ═══════════════════════════════════════════════════════════

def test_rfid(transport: CompassTransport):
    banner("TEST 7: RFID Card Read (Wiegand W)")
    print("  Tap an RFID card on the Wiegand reader now...")

    if not prompt("  Ready to test RFID?"):
        print("  ⏭️  Skipped")
        return None

    print("  Listening for 10 seconds...")
    card_found = None

    for _ in range(20):
        response = send_recv_raw(transport, cmd_stat(), timeout=0.5)
        if response:
            card_num, card_type = parse_rfid_card(response)
            if card_num:
                card_found = (card_num, card_type)
                break
        time.sleep(0.5)

    if card_found:
        print(f"  ✅ RFID card detected!")
        print(f"     Card number: {card_found[0]}")
        print(f"     Card type: {card_found[1]}")
        return True
    else:
        print("  ❌ No RFID card detected")
        return False


# ═══════════════════════════════════════════════════════════
# TEST 8: E-Money Reader Initialization
# ═══════════════════════════════════════════════════════════

def test_emoney_init(transport: CompassTransport):
    banner("TEST 8: E-Money Reader Initialization")
    print("  Sending INIT command to e-money reader via Serial2...")

    if not prompt("  Ready to test e-money reader init?"):
        print("  ⏭️  Skipped")
        return None

    init_frame = cmd_init(EMONEY_INIT_KEY)
    result = send_emoney_cmd(transport, init_frame, timeout=5.0)

    if result.get("ok"):
        body = result.get("body", b"")
        if len(body) >= 12:
            mid = body[:8].hex().upper()
            tid = body[8:12].hex().upper()
            print(f"  ✅ Reader initialized successfully!")
            print(f"     MID: {mid}")
            print(f"     TID: {tid}")
        else:
            print(f"  ✅ Reader initialized (no MID/TID in response)")
        return True
    else:
        print(f"  ❌ Init failed: {result.get('status_msg', result.get('error', 'Unknown'))}")
        print(f"     Raw: {result.get('raw', 'N/A')}")
        return False


# ═══════════════════════════════════════════════════════════
# TEST 9: E-Money Check Balance
# ═══════════════════════════════════════════════════════════

def test_emoney_balance(transport: CompassTransport):
    banner("TEST 9: E-Money Check Balance")
    print("  Tap an e-money card on the reader now...")
    print("  You have 15 seconds.")

    if not prompt("  Ready to test check balance?"):
        print("  ⏭️  Skipped")
        return None

    cb_frame = cmd_check_balance(CARD_TIMEOUT)
    result = send_emoney_cmd(transport, cb_frame, timeout=15.0)

    if result.get("ok"):
        parsed = parse_check_balance_response(result.get("body", b""))
        if parsed.get("ok"):
            print(f"  ✅ Card detected!")
            print(f"     Type: {parsed['card_type']}")
            print(f"     Number: {parsed['card_number']}")
            print(f"     Balance: Rp {parsed['balance']:,}")
            return True
        else:
            print(f"  ⚠️  Response OK but parsing failed: {parsed.get('error', 'Unknown')}")
            return False
    else:
        status = result.get("status")
        if status == (0x01, 0x10, 0x02):
            print("  ⚠️  No card detected within timeout (this is normal if no card was tapped)")
        else:
            print(f"  ❌ Check balance failed: {result.get('status_msg', result.get('error', 'Unknown'))}")
        return False


# ═══════════════════════════════════════════════════════════
# TEST 10: E-Money Deduct
# ═══════════════════════════════════════════════════════════

def test_emoney_deduct(transport: CompassTransport):
    banner("TEST 10: E-Money Deduct")
    print("  This will deduct Rp 5,000 from the card.")
    print("  Make sure the card has sufficient balance!")

    if not prompt("  Proceed with deduct test?"):
        print("  ⏭️  Skipped")
        return None

    from protocols.passti.commands import cmd_deduct, parse_deduct_response

    deduct_frame = cmd_deduct(5000, CARD_TIMEOUT)
    result = send_emoney_cmd(transport, deduct_frame, timeout=15.0)

    if result.get("ok"):
        parsed = parse_deduct_response(result.get("body", b""))
        if parsed.get("ok", False):
            print(f"  ✅ Deduct successful!")
            print(f"     Card: {parsed['card_number']}")
            print(f"     Deducted: Rp {parsed['deducted']:,}")
            print(f"     Remaining: Rp {parsed['remaining']:,}")
            print(f"     Counter: {parsed['trans_counter']}")
            return True
        else:
            print(f"  ⚠️  Response OK but parsing failed: {parsed.get('error')}")
            return False
    else:
        print(f"  ❌ Deduct failed: {result.get('status_msg', result.get('error', 'Unknown'))}")
        return False


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     E-PARKING v2 — HARDWARE INTEGRATION TEST               ║")
    print("║     Compass Controller + RFID + E-Money Reader             ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n  Target: {CONTROLLER_IP}:{CONTROLLER_PORT}")
    print("  Make sure controller is powered on and Ethernet is connected.")

    # Step 1: Connect
    transport = test_connectivity()
    if transport is None:
        print("\n❌ Cannot continue without controller connection.")
        print("   Check power, cable, and IP configuration.")
        sys.exit(1)

    results = {}

    try:
        # Step 2: STAT
        results["stat"] = test_stat_polling(transport)

        # Step 3: Gate
        results["gate"] = test_gate_trigger(transport)

        # Step 4: Audio
        results["audio"] = test_audio(transport)

        # Step 5: Display
        results["display"] = test_display(transport)

        # Step 6: Inputs
        input_results = test_inputs(transport)
        results["in1"] = input_results.get("in1")
        results["in2"] = input_results.get("in2")

        # Step 7: RFID
        results["rfid"] = test_rfid(transport)

        # Step 8: E-money init
        results["emoney_init"] = test_emoney_init(transport)

        # Step 9: E-money balance
        if results.get("emoney_init"):
            results["emoney_balance"] = test_emoney_balance(transport)
        else:
            print("\n  ⏭️  Skipping balance test — reader init failed")

        # Step 10: E-money deduct
        if results.get("emoney_balance"):
            results["emoney_deduct"] = test_emoney_deduct(transport)
        else:
            print("\n  ⏭️  Skipping deduct test — balance check failed or skipped")

    except KeyboardInterrupt:
        print("\n\n  [INTERRUPTED] Test stopped by user")
    finally:
        transport.close()
        print("\n  Controller connection closed")

    # Summary
    banner("TEST SUMMARY")
    passed = 0
    failed = 0
    skipped = 0

    for name, result in results.items():
        if result is True:
            print(f"  ✅ {name:20s} PASS")
            passed += 1
        elif result is False:
            print(f"  ❌ {name:20s} FAIL")
            failed += 1
        else:
            print(f"  ⏭️  {name:20s} SKIP")
            skipped += 1

    total_tested = passed + failed
    print(f"\n  Results: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"  Success rate: {passed}/{total_tested} ({passed * 100 // max(total_tested, 1)}%)")

    if failed == 0 and skipped == 0:
        print("\n  🎉 All tests passed! Hardware is fully operational.")
    elif failed == 0:
        print("\n  ⚠️  All tested components passed. Skipped tests may need manual setup.")
    else:
        print("\n  ⚠️  Some tests failed. Check connections and retry failed tests.")


if __name__ == "__main__":
    main()
