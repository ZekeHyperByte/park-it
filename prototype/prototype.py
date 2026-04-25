#!/usr/bin/env python3
"""
E-Money Parking System Prototype
=================================
Demonstrates tap-in/tap-out flow with PASSTI e-money reader.

Usage:
    python prototype.py              # Real gate controller mode
    python prototype.py --simulate   # Simulated gate controller mode

Commands:
    (press Enter to scan for card tap)
    /status    - Show system status
    /history   - Show transaction history
    /active    - Show active parking sessions
    /simulate  - Toggle simulation mode
    /quit      - Exit program
"""

import sqlite3
import time
import sys
import argparse
import socket
import threading
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

CONTROLLER_IP = "192.168.1.100"
CONTROLLER_PORT = 5000
EMONEY_INIT_KEY = bytes.fromhex("758F40D46D95D1641448AA19B9282C05")

CARD_TIMEOUT = 10  # seconds
SENSING_SCAN_TIMEOUT = 15  # seconds - how long e-money reader stays active per scan
SENSING_WINDOW = 30  # seconds - total sensing mode duration
DB_PATH = "emoney_parking.db"

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

STX = 0x02

CARD_TYPE = {
    0x01: "Luminos",
    0x02: "Mandiri eMoney",
    0x03: "BRI Brizzi",
    0x04: "BNI TapCash",
    0x05: "BCA Flazz",
    0x06: "DKI JakCard",
    0x07: "NOBU Card",
    0x08: "Mega MegaCash",
    0x09: "QR Payment",
}

STATUS_MSG = {
    (0x00, 0x00, 0x00): "OK",
    (0x01, 0x10, 0x01): "General error",
    (0x01, 0x10, 0x02): "Timeout - no card detected",
    (0x01, 0x10, 0x03): "Init failed (wrong key)",
    (0x01, 0x10, 0x04): "Insufficient balance",
    (0x01, 0x10, 0x05): "Lost contact",
    (0x01, 0x10, 0x06): "Expected previous card",
    (0x01, 0x10, 0x07): "Deduct interval too short",
    (0x01, 0x10, 0x09): "BNI inactive card",
    (0x01, 0x10, 0x10): "Expected same deduct amount",
}

# ─────────────────────────────────────────────
# SERIAL / FRAME LAYER
# ─────────────────────────────────────────────


def lrc(data: bytes) -> int:
    result = 0
    for b in data:
        result ^= b
    return result


def to_bcd(digits: str) -> bytes:
    if len(digits) % 2:
        digits = "0" + digits
    return bytes(int(digits[i : i + 2], 16) for i in range(0, len(digits), 2))


def bcd_timeout(sec: int) -> bytes:
    return bytes([sec // 100, sec % 100])


def build_frame(cmd: int, data: bytes = b"") -> bytes:
    payload = bytes([0xEF, 0x01, cmd]) + data
    lh = (len(payload) >> 8) & 0xFF
    ll = len(payload) & 0xFF
    chk = lrc(bytes([lh, ll]) + payload)
    return bytes([STX, lh, ll]) + payload + bytes([chk])


def send_recv(gate, frame: bytes) -> dict:
    """Send e-money command via controller Serial2 passthrough (QR/QT)."""
    # Build controller passthrough command: \xa6 QR5 <frame> \xa9
    # QR = serial2, 5 = 38400 baud
    qr_cmd = bytes([0xA6]) + b"QR5" + frame + bytes([0xA9])

    gate.pause_polling()
    sock = gate.shared_sock

    try:
        sock.sendall(qr_cmd)
    except Exception as e:
        gate.resume_polling()
        return {"ok": False, "error": f"Failed to send to controller: {e}"}

    # Read response from TCP stream
    try:
        buffer = b""
        qt_data = None

        # Give controller time to forward serial2 data
        sock.settimeout(CARD_TIMEOUT + 2)

        while True:
            try:
                chunk = sock.recv(2048)
                if not chunk:
                    break
                buffer += chunk
            except socket.timeout:
                break

            # Scan buffer for QT prefix followed by data and footer
            # Controller wraps serial2 response as: \xa6 QT <data> \xa9
            idx = buffer.find(b"\xa6QT")
            if idx != -1:
                footer_idx = buffer.find(b"\xa9", idx + 3)
                if footer_idx != -1:
                    qt_data = buffer[idx + 3 : footer_idx]
                    break

            # Also accept plain QT response (without header/footer per protocol)
            idx = buffer.find(b"QT")
            if idx != -1 and (idx == 0 or buffer[idx - 1 : idx] != b"\xa6"):
                end_idx = buffer.find(b"\xa6", idx + 2)
                if end_idx == -1:
                    end_idx = len(buffer)
                qt_data = buffer[idx + 2 : end_idx]
                break

        if qt_data is None:
            gate.resume_polling()
            return {"ok": False, "error": "No QT response from controller serial2"}

        raw = qt_data

        if len(raw) < 3:
            gate.resume_polling()
            return {"ok": False, "error": "Empty response from reader via controller"}

        data_len = (raw[1] << 8) | raw[2]
        expected_len = 3 + data_len + 1
        if len(raw) < expected_len:
            gate.resume_polling()
            return {"ok": False, "error": "Incomplete response from reader via controller"}

        resp_code = raw[3]
        payload = raw[4 : 4 + data_len - 1]
        status = tuple(payload[:3]) if len(payload) >= 3 else (0xFF, 0xFF, 0xFF)
        body = payload[3:] if len(payload) > 3 else b""

        gate.resume_polling()
        return {
            "ok": resp_code == 0x00 and status == (0, 0, 0),
            "resp_code": resp_code,
            "status": status,
            "status_msg": STATUS_MSG.get(status, f"Unknown {bytes(status).hex()}"),
            "body": body,
        }
    except Exception as e:
        gate.resume_polling()
        return {"ok": False, "error": f"Communication error via controller: {e}"}


# ─────────────────────────────────────────────
# READER COMMANDS
# ─────────────────────────────────────────────


def cmd_init(gate, key: bytes) -> dict:
    return send_recv(gate, build_frame(0x01, key))


def cmd_check_balance(gate, timeout_sec: int) -> dict:
    now = datetime.now()
    data = (
        to_bcd(now.strftime("%d%m%Y"))
        + to_bcd(now.strftime("%H%M%S"))
        + bcd_timeout(timeout_sec)
    )
    result = send_recv(gate, build_frame(0x02, data))
    if result["ok"] and len(result["body"]) >= 13:
        b = result["body"]
        result["card_type_code"] = b[0]
        result["card_type"] = CARD_TYPE.get(b[0], f"Unknown({b[0]:02X})")
        result["card_number"] = b[1:9].hex().upper()
        result["balance"] = int.from_bytes(b[9:13], "big")
    return result


def cmd_deduct(gate, amount: int, timeout_sec: int) -> dict:
    now = datetime.now()
    data = (
        to_bcd(now.strftime("%d%m%Y"))
        + to_bcd(now.strftime("%H%M%S"))
        + amount.to_bytes(4, "big")
        + bcd_timeout(timeout_sec)
    )
    result = send_recv(gate, build_frame(0x03, data))
    if result["ok"] and len(result["body"]) >= 40:
        b = result["body"]
        result["card_type"] = CARD_TYPE.get(b[0], f"Unknown({b[0]:02X})")
        result["card_number"] = b[20:28].hex().upper()
        result["deducted"] = int.from_bytes(b[28:32], "big")
        result["remaining"] = int.from_bytes(b[32:36], "big")
        result["trans_counter"] = int.from_bytes(b[36:40], "big")
    return result


def cmd_get_last_transaction(gate) -> dict:
    result = send_recv(gate, build_frame(0x05))
    if result["ok"] and len(result["body"]) >= 40:
        b = result["body"]
        result["card_type"] = CARD_TYPE.get(b[0], f"Unknown({b[0]:02X})")
        result["card_number"] = b[20:28].hex().upper()
        result["deducted"] = int.from_bytes(b[28:32], "big")
        result["remaining"] = int.from_bytes(b[32:36], "big")
        result["trans_counter"] = int.from_bytes(b[36:40], "big")
    return result


def cmd_cancel_correction(gate) -> dict:
    return send_recv(gate, build_frame(0x04))


def cmd_buzzer(gate, success: bool):
    send_recv(gate, build_frame(0x09, bytes([0x02, 0x00 if success else 0x01])))


def cmd_display(gate, text: str):
    t = text.encode("ascii")[:16].ljust(16)
    tlv = bytes([0xD1, 0x01, 0x01, 0xD2, len(t)]) + t + bytes(
        [0xD3, 0x01, 0x02, 0xD4, 0x01, 0x01]
    )
    send_recv(gate, build_frame(0x09, bytes([0x03]) + tlv))


def cmd_reset_display(gate):
    send_recv(gate, build_frame(0x09, bytes([0x00])))


# ─────────────────────────────────────────────
# GATE CONTROLLER (Real + Simulated)
# ─────────────────────────────────────────────


class GateController:
    """Interface for gate barrier control."""

    def open_gate(self):
        raise NotImplementedError

    def close_gate(self):
        raise NotImplementedError


class SimulatedGateController(GateController):
    """Simulated gate controller for demo."""

    def __init__(self):
        self.is_open = False
        self.shared_sock = None

    def open_gate(self):
        print("\n  [GATE] >>> GATE OPENED <<<")
        self.is_open = True
        time.sleep(2)
        self.close_gate()

    def close_gate(self):
        print("  [GATE] >>> GATE CLOSED <<<")
        self.is_open = False

    def pause_polling(self):
        pass

    def resume_polling(self):
        pass


class RealGateController(GateController):
    """Real gate controller via shared TCP socket (Compass protocol).

    Simple socket wrapper — no background threads. Main loop handles
    all STAT polling and input detection directly.
    """

    def __init__(self, shared_sock: socket.socket):
        self.shared_sock = shared_sock
        self.connected = True

    def _send(self, command: bytes):
        """Send command to gate controller via shared socket."""
        if self.connected:
            try:
                self.shared_sock.send(command)
            except Exception:
                self.connected = False

    def _send_recv(self, command: bytes, timeout: float = 1.0) -> bytes:
        """Send command and receive response from gate controller."""
        if not self.connected:
            return b""
        try:
            self.shared_sock.settimeout(timeout)
            self.shared_sock.send(command)
            response = self.shared_sock.recv(1024)
            return response
        except Exception:
            self.connected = False
            return b""

    def pause_polling(self):
        """No-op — kept for compatibility with send_recv()."""
        pass

    def resume_polling(self):
        """No-op — kept for compatibility with send_recv()."""
        pass

    def start(self):
        """No-op — main loop handles polling directly."""
        print(f"  [GATE] Controller ready on shared socket")

    def stop(self):
        """No-op — main loop closes the socket."""
        self.connected = False
        print(f"  [GATE] Controller stopped")

    def open_gate(self):
        """Open the gate barrier."""
        print(f"\n  [GATE] Opening barrier...")
        self._send(b"\xa6TRIG1\xa9")
        time.sleep(2)

    def close_gate(self):
        """Close the gate barrier (no-op in this protocol)."""
        print(f"  [GATE] Closing barrier...")


# ─────────────────────────────────────────────
# CONTROLLER HELPERS
# ─────────────────────────────────────────────


def controller_send_recv(gate, cmd: bytes, timeout: float = 1.0) -> bytes:
    """Send raw command to controller and read response."""
    if not gate.connected:
        return b""
    try:
        gate.shared_sock.settimeout(timeout)
        gate.shared_sock.send(cmd)
        return gate.shared_sock.recv(1024)
    except Exception:
        return b""


def play_audio(gate, track: str):
    """Play MP3 track on controller."""
    controller_send_recv(gate, f"\xa6MT{track}\xa9".encode())


def show_display(gate, line1: str, line2: str):
    """Show two-line text on controller LED display."""
    controller_send_recv(gate, b"\xa6DSD913003" + line1.encode() + b"|13003" + line2.encode() + b"\xa9")


def reset_display_controller(gate):
    """Reset controller LED display."""
    controller_send_recv(gate, b"\xa6DSU\xa9")


def parse_rfid(response: bytes) -> tuple:
    """Parse W/X RFID data from controller STAT response.
    
    Returns (card_number, card_type) or (None, None) if no RFID.
    """
    text = response.decode("latin-1", errors="ignore")
    
    # Wiegand 1 (W) - RFID
    if "W" in text:
        try:
            card_hex = text.split("W")[1].split("\xa9")[0]
            card_num = str(int(card_hex, 16))
            return card_num, "RFID"
        except Exception:
            pass
    
    # Wiegand 2 (X) - UHF
    if "X" in text:
        try:
            card_hex = text.split("X")[1].split("\xa9")[0]
            card_num = str(int(card_hex, 16))
            return card_num, "UHF"
        except Exception:
            pass
    
    return None, None


def handle_rfid_tap(gate, card_number: str, card_type: str):
    """Handle RFID/UHF card tap during sensing mode."""
    print(f"\n  [RFID] Card detected: {card_number} ({card_type})")
    play_audio(gate, "00007")
    show_display(gate, "KARTU RFID", "TERDETEKSI")
    time.sleep(2)
    reset_display_controller(gate)
    
    log_transaction(
        card_number,
        card_type,
        "TAP_IN",
        status="RFID_DETECTED",
        gate_status="OPENED",
    )
    gate.open_gate()


def handle_ticket(gate):
    """Handle IN1 ticket button - non-member entry."""
    print(f"\n  [TICKET] Tombol tiket ditekan - Non-member entry")
    play_audio(gate, "00002")
    show_display(gate, "SILAKAN AMBIL", "TIKET PARKIR")
    
    # Generate dummy barcode
    barcode = f"T{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    log_transaction(
        barcode,
        "TICKET",
        "TAP_IN",
        status="SUCCESS",
        gate_status="OPENED",
    )
    gate.open_gate()
    time.sleep(1)
    reset_display_controller(gate)


def handle_help(gate):
    """Handle IN4 help button."""
    print(f"\n  [HELP] Tombol bantuan ditekan")
    play_audio(gate, "00005")
    show_display(gate, "MOHON TUNGGU", "PETUGAS DATANG")
    time.sleep(10)
    reset_display_controller(gate)


# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            card_number TEXT NOT NULL,
            card_type TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount INTEGER,
            balance_before INTEGER,
            balance_after INTEGER,
            status TEXT NOT NULL,
            gate_status TEXT
        )
    """
    )
    con.commit()
    con.close()


def log_transaction(
    card_number: str,
    card_type: str,
    trans_type: str,
    amount: int = None,
    balance_before: int = None,
    balance_after: int = None,
    status: str = "SUCCESS",
    gate_status: str = None,
):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """INSERT INTO transactions
           (timestamp, card_number, card_type, transaction_type, amount,
            balance_before, balance_after, status, gate_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now().isoformat(),
            card_number,
            card_type,
            trans_type,
            amount,
            balance_before,
            balance_after,
            status,
            gate_status,
        ),
    )
    con.commit()
    con.close()


def show_transaction_history(limit: int = 10):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    con.close()

    print("\n" + "=" * 90)
    print("TRANSACTION HISTORY (Last {} records)".format(limit))
    print("=" * 90)
    print(
        f"{'Time':<20} {'Card':<18} {'Type':<15} {'Dir':<6} {'Amount':<12} {'Balance':<12} {'Status'}"
    )
    print("-" * 90)
    for row in rows:
        time_str = row["timestamp"][:19].replace("T", " ")
        amount = f"Rp {row['amount']:,}" if row["amount"] else "-"
        balance = f"Rp {row['balance_after']:,}" if row["balance_after"] else "-"
        direction = "IN" if row["transaction_type"] == "TAP_IN" else "OUT"
        print(
            f"{time_str:<20} {row['card_number'][-8:]:>8} {row['card_type']:<15} {direction:<6} {amount:<12} {balance:<12} {row['status']}"
        )
    print("=" * 90)


# ─────────────────────────────────────────────
# TARIFF CALCULATION (Simplified)
# ─────────────────────────────────────────────


def calculate_tariff(time_in: datetime, time_out: datetime) -> int:
    """Simplified tariff: Rp 3,000 per hour, max Rp 25,000/day."""
    durasi_menit = (time_out - time_in).total_seconds() / 60
    if durasi_menit <= 0:
        return 3000

    jam = int(durasi_menit // 60) + (1 if durasi_menit % 60 > 0 else 0)
    tarif = jam * 3000
    return min(tarif, 25000)


# ─────────────────────────────────────────────
# ACTIVE TRANSACTIONS (In-memory)
# ─────────────────────────────────────────────

active_parking = {}  # card_number -> {time_in, card_type, balance}


# ─────────────────────────────────────────────
# MAIN FLOWS
# ─────────────────────────────────────────────


def handle_tap_in(gate, card_info: dict):
    """Handle vehicle entry with e-money card."""
    card_number = card_info["card_number"]
    card_type = card_info["card_type"]
    balance = card_info["balance"]

    print(f"\n  [TAP-IN] Processing entry...")
    print(f"  Card: {card_type} ({card_number[-8:]})")
    print(f"  Balance: Rp {balance:,}")

    if card_number in active_parking:
        print(f"  [!] Card already tapped in! Please tap out first.")
        cmd_buzzer(gate, False)
        cmd_display(gate, "SUDAH MASUK!")
        time.sleep(2)
        cmd_reset_display(gate)
        log_transaction(
            card_number,
            card_type,
            "TAP_IN",
            status="DUPLICATE",
            gate_status="DENIED",
        )
        return

    min_balance = 10000
    if balance < min_balance:
        print(f"  [!] Insufficient balance (min Rp {min_balance:,})")
        cmd_buzzer(gate, False)
        cmd_display(gate, "SALDO MINIMUM!")
        time.sleep(2)
        cmd_reset_display(gate)
        log_transaction(
            card_number,
            card_type,
            "TAP_IN",
            balance_before=balance,
            balance_after=balance,
            status="INSUFFICIENT_BALANCE",
            gate_status="DENIED",
        )
        return

    active_parking[card_number] = {
        "time_in": datetime.now(),
        "card_type": card_type,
        "balance": balance,
    }

    print(f"  [OK] Entry recorded at {active_parking[card_number]['time_in']}")

    gate.open_gate()

    cmd_buzzer(gate, True)
    cmd_display(gate, "SELAMAT\nDATANG")
    time.sleep(1.5)
    cmd_reset_display(gate)

    log_transaction(
        card_number,
        card_type,
        "TAP_IN",
        balance_before=balance,
        balance_after=balance,
        status="SUCCESS",
        gate_status="OPENED",
    )


def handle_tap_out(gate, card_info: dict):
    """Handle vehicle exit with e-money card."""
    card_number = card_info["card_number"]
    card_type = card_info["card_type"]
    balance = card_info["balance"]

    print(f"\n  [TAP-OUT] Processing exit...")
    print(f"  Card: {card_type} ({card_number[-8:]})")
    print(f"  Current Balance: Rp {balance:,}")

    if card_number not in active_parking:
        print(f"  [!] No active entry found for this card!")
        cmd_buzzer(gate, False)
        cmd_display(gate, "KARTU TIDAK AKTIF")
        time.sleep(2)
        cmd_reset_display(gate)
        log_transaction(
            card_number,
            card_type,
            "TAP_OUT",
            status="NO_ENTRY",
            gate_status="DENIED",
        )
        return

    entry_data = active_parking[card_number]
    time_in = entry_data["time_in"]
    time_out = datetime.now()
    tarif = calculate_tariff(time_in, time_out)

    durasi = time_out - time_in
    durasi_menit = int(durasi.total_seconds() / 60)
    jam = durasi_menit // 60
    menit = durasi_menit % 60

    print(f"  Time In:  {time_in.strftime('%H:%M:%S')}")
    print(f"  Time Out: {time_out.strftime('%H:%M:%S')}")
    print(f"  Duration: {jam}h {menit}m")
    print(f"  Tariff:   Rp {tarif:,}")

    if balance < tarif:
        print(f"  [!] Insufficient balance for payment!")
        print(f"      Required: Rp {tarif:,}")
        print(f"      Available: Rp {balance:,}")
        cmd_buzzer(gate, False)
        cmd_display(gate, "SALDO KURANG!")
        time.sleep(2)
        cmd_reset_display(gate)
        log_transaction(
            card_number,
            card_type,
            "TAP_OUT",
            amount=tarif,
            balance_before=balance,
            balance_after=balance,
            status="INSUFFICIENT_BALANCE",
            gate_status="DENIED",
        )
        return

    print(f"\n  [DEDUCT] Processing payment of Rp {tarif:,}...")
    deduct_result = cmd_deduct(gate, tarif, CARD_TIMEOUT)

    if deduct_result["ok"]:
        remaining = deduct_result["remaining"]
        print(f"  [OK] Deduction successful!")
        print(f"  Remaining Balance: Rp {remaining:,}")

        del active_parking[card_number]

        gate.open_gate()

        cmd_buzzer(gate, True)
        cmd_display(gate, f"BAYAR {tarif//1000}K OK")
        time.sleep(2)
        cmd_reset_display(gate)

        log_transaction(
            card_number,
            card_type,
            "TAP_OUT",
            amount=tarif,
            balance_before=balance,
            balance_after=remaining,
            status="SUCCESS",
            gate_status="OPENED",
        )
    else:
        if "status" not in deduct_result:
            # Communication error (no response from controller/reader)
            error_msg = deduct_result.get("error", "Unknown communication error")
            print(f"  [!] Deduct failed: {error_msg}")
            cmd_buzzer(gate, False)
            cmd_display(gate, "GAGAL!")
            time.sleep(2)
            cmd_reset_display(gate)
            log_transaction(
                card_number,
                card_type,
                "TAP_OUT",
                amount=tarif,
                balance_before=balance,
                balance_after=balance,
                status=f"FAILED: {error_msg}",
                gate_status="DENIED",
            )
            return

        status = deduct_result["status"]

        if status == (0x01, 0x10, 0x05):
            print(f"  [!] Lost contact during deduct!")
            print(f"  Please tap the SAME card again to complete payment.")
            cmd_display(gate, "TAP LAGI KARTU")

            last_trx = cmd_get_last_transaction(gate)
            if last_trx["ok"]:
                print(f"  [RECOVERY] Last transaction found in reader")
                print(f"  Card: {last_trx['card_number'][-8:]}")
                print(f"  Deducted: Rp {last_trx['deducted']:,}")
                print(f"  Remaining: Rp {last_trx['remaining']:,}")

                del active_parking[card_number]
                gate.open_gate()
                cmd_buzzer(gate, True)
                cmd_display(gate, "PEMBAYARAN OK")
                time.sleep(2)
                cmd_reset_display(gate)

                log_transaction(
                    last_trx["card_number"],
                    last_trx["card_type"],
                    "TAP_OUT",
                    amount=last_trx["deducted"],
                    balance_before=balance,
                    balance_after=last_trx["remaining"],
                    status="RECOVERED",
                    gate_status="OPENED",
                )
            else:
                cmd_buzzer(gate, False)
                log_transaction(
                    card_number,
                    card_type,
                    "TAP_OUT",
                    amount=tarif,
                    balance_before=balance,
                    balance_after=balance,
                    status="LOST_CONTACT",
                    gate_status="DENIED",
                )

        elif status == (0x01, 0x10, 0x06):
            print(f"  [!] Wrong card! Expected the previous card.")
            cmd_display(gate, "KARTU SALAH!")
            time.sleep(2)
            cmd_reset_display(gate)
            cmd_buzzer(gate, False)

        else:
            print(f"  [!] Deduct failed: {deduct_result['status_msg']}")
            cmd_buzzer(gate, False)
            cmd_display(gate, "GAGAL!")
            time.sleep(2)
            cmd_reset_display(gate)

            log_transaction(
                card_number,
                card_type,
                "TAP_OUT",
                amount=tarif,
                balance_before=balance,
                balance_after=balance,
                status=f"FAILED: {deduct_result['status_msg']}",
                gate_status="DENIED",
            )


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────


def print_header(simulate_mode: bool):
    print("=" * 60)
    print("   E-MONEY PARKING SYSTEM - PROTOTYPE")
    print("   Tap-In / Tap-Out Demo")
    mode = "SIMULATED" if simulate_mode else "REAL"
    print(f"   Gate Controller: {mode}")
    print("=" * 60)


def print_help():
    print("\n" + "=" * 50)
    print("AVAILABLE COMMANDS")
    print("=" * 50)
    print("  (Enter)    - Scan for card tap")
    print("  /status    - Show system status")
    print("  /history   - Show recent transactions")
    print("  /active    - Show active parking sessions")
    print("  /simulate  - Toggle gate simulation mode")
    print("  /help      - Show this help")
    print("  /quit      - Exit program")
    print("=" * 50)


def show_status(gate, simulate_mode: bool):
    print("\n" + "=" * 50)
    print("SYSTEM STATUS")
    print("=" * 50)
    if simulate_mode:
        controller_status = "Simulated"
    else:
        try:
            gate.shared_sock.getpeername()
            controller_status = f"Connected ({CONTROLLER_IP}:{CONTROLLER_PORT})"
        except Exception:
            controller_status = "Disconnected"
    print(f"  Controller     : {controller_status}")
    print(f"  Active Sessions: {len(active_parking)}")
    print(f"  Database       : {DB_PATH}")
    print("=" * 50)


def print_help_auto():
    print("\n" + "=" * 50)
    print("PROTOTYPE AUTO-MODE")
    print("=" * 50)
    print("  IN2 button     = Trigger vehicle detection / scan")
    print("  IN1 button     = Print ticket (non-member)")
    print("  IN4 button     = Call help")
    print("  RFID (W/X)     = Tap RFID/UHF card")
    print("  E-money (QR/QT)= Tap e-money card during sensing")
    print("  Commands:")
    print("    /status      - Show system status")
    print("    /history     - Show transaction history")
    print("    /active      - Show active parking sessions")
    print("    /simulate    - Toggle simulation mode")
    print("    /quit        - Exit program")
    print("=" * 50)


def show_active():
    print("\n" + "=" * 70)
    print("ACTIVE PARKING SESSIONS")
    print("=" * 70)
    if not active_parking:
        print("  No active sessions")
    else:
        print(
            f"{'Card':<18} {'Type':<15} {'Entry Time':<20} {'Duration':<10}"
        )
        print("-" * 70)
        now = datetime.now()
        for card_num, data in active_parking.items():
            duration = now - data["time_in"]
            dur_min = int(duration.total_seconds() / 60)
            print(
                f"{card_num[-8:]:>8} {data['card_type']:<15} {data['time_in'].strftime('%H:%M:%S'):<20} {dur_min}m"
            )
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="E-Money Parking System Prototype")
    parser.add_argument(
        "--simulate", action="store_true", help="Use simulated gate controller"
    )
    args = parser.parse_args()

    simulate_mode = args.simulate

    print_header(simulate_mode)

    init_db()
    print(f"[+] Database initialized: {DB_PATH}")

    try:
        shared_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        shared_sock.settimeout(5)
        shared_sock.connect((CONTROLLER_IP, CONTROLLER_PORT))
        print(f"[+] Connected to controller at {CONTROLLER_IP}:{CONTROLLER_PORT}")
    except Exception as e:
        print(f"[FATAL] Cannot connect to controller: {e}")
        print(f"        Check if {CONTROLLER_IP}:{CONTROLLER_PORT} is reachable.")
        return

    print("\n[INIT] Initializing e-money reader...")
    if simulate_mode:
        gate = SimulatedGateController()
        print(f"[+] Using SIMULATED gate controller")
    else:
        gate = RealGateController(shared_sock)
        gate.start()
        print(f"[+] Using REAL gate controller via shared socket")

    init = cmd_init(gate, EMONEY_INIT_KEY)
    if not init["ok"]:
        print(f"[FATAL] Init failed: {init['status_msg']}")
        print("        Check your INIT_KEY")
        shared_sock.close()
        return

    if len(init["body"]) >= 12:
        mid = init["body"][:8].hex().upper()
        tid = init["body"][8:12].hex().upper()
        print(f"[OK] Reader ready! MID={mid}, TID={tid}")
    else:
        print(f"[OK] Reader ready!")

    print_help_auto()

    # ── STATE MACHINE ──
    state = "IDLE"
    sensing_start = 0
    last_status_check = 0
    user_input_buffer = ""

    try:
        while True:
            # ── Check for keyboard input (non-blocking) ──
            import select
            if select.select([sys.stdin], [], [], 0)[0]:
                char = sys.stdin.read(1)
                if char == '\n':
                    cmd = user_input_buffer.strip().lower()
                    user_input_buffer = ""
                    
                    if cmd in ("/quit", "/exit"):
                        print("\n[EXIT] Shutting down...")
                        break
                    elif cmd == "/status":
                        show_status(gate, simulate_mode)
                    elif cmd == "/history":
                        show_transaction_history()
                    elif cmd == "/active":
                        show_active()
                    elif cmd == "/simulate":
                        simulate_mode = not simulate_mode
                        if simulate_mode:
                            gate.stop()
                            gate = SimulatedGateController()
                            print("  -> Switched to SIMULATED gate controller")
                        else:
                            gate = RealGateController(shared_sock)
                            gate.start()
                            print("  -> Switched to REAL gate controller via shared socket")
                    elif cmd == "/help":
                        print_help_auto()
                    elif cmd:
                        print(f"  [!] Unknown command: {cmd}")
                else:
                    user_input_buffer += char

            # ── IDLE STATE ──
            if state == "IDLE":
                if simulate_mode:
                    time.sleep(0.5)
                    continue

                # Poll controller for inputs
                response = controller_send_recv(gate, b"\xa6STAT\xa9", timeout=0.5)
                
                if not response:
                    time.sleep(0.5)
                    continue

                # IN2 = Vehicle detected (trigger sensing)
                if b"IN2ON" in response or b"STAT1" in response:
                    print("\n  [DETECT] IN2 ON - Vehicle detected!")
                    state = "SENSING"
                    sensing_start = time.time()
                    play_audio(gate, "00007")
                    show_display(gate, "SELAMAT DATANG", "SILAKAN TEMPEL KARTU")
                    continue

                # IN1 = Ticket button (non-member)
                if b"IN1ON" in response or b"STAT10" in response:
                    handle_ticket(gate)
                    continue

                # IN4 = Help button
                if b"IN4ON" in response:
                    handle_help(gate)
                    continue

                # RFID passive detection (if resend enabled)
                card_num, card_type = parse_rfid(response)
                if card_num:
                    handle_rfid_tap(gate, card_num, card_type)
                    continue

                time.sleep(0.5)

            # ── SENSING STATE ──
            elif state == "SENSING":
                elapsed = time.time() - sensing_start

                # Timeout after sensing window
                if elapsed > SENSING_WINDOW:
                    print("  [TIMEOUT] No card detected, returning to idle")
                    show_display(gate, "MOHON MAAF", "WAKTU HABIS")
                    time.sleep(2)
                    reset_display_controller(gate)
                    state = "IDLE"
                    continue

                # 1. Scan e-money reader
                print(f"  [SCAN] Checking e-money card... ({int(SENSING_WINDOW-elapsed)}s remaining)")
                result = cmd_check_balance(gate, SENSING_SCAN_TIMEOUT)

                if result["ok"]:
                    # E-money card detected!
                    card_number = result["card_number"]
                    print(f"  [CARD] E-money detected: {card_number}")
                    
                    if card_number in active_parking:
                        handle_tap_out(gate, result)
                    else:
                        handle_tap_in(gate, result)
                    
                    state = "IDLE"
                    continue

                # If timeout (no card), continue to check controller inputs
                # If other error, log it but continue
                if "status" not in result or result.get("status") != (0x01, 0x10, 0x02):
                    if "error" in result:
                        print(f"  [!] E-money scan error: {result['error']}")

                # 2. Check controller for RFID / buttons
                response = controller_send_recv(gate, b"\xa6STAT\xa9", timeout=0.3)
                
                if response:
                    # RFID card
                    card_num, card_type = parse_rfid(response)
                    if card_num:
                        handle_rfid_tap(gate, card_num, card_type)
                        state = "IDLE"
                        continue

                    # IN4 = Help
                    if b"IN4ON" in response:
                        handle_help(gate)
                        state = "IDLE"
                        continue

                    # IN2 again = Cancel
                    if b"IN2ON" in response:
                        print("  [CANCEL] IN2 pressed again - cancelling")
                        reset_display_controller(gate)
                        state = "IDLE"
                        continue

                time.sleep(0.3)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

    finally:
        if not simulate_mode and hasattr(gate, 'stop'):
            gate.stop()
        shared_sock.close()
        print("[+] Shared TCP connection closed")
        print("[+] Done.")


if __name__ == "__main__":
    main()
