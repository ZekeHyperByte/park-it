#!/usr/bin/env python3
"""
E-Money Deduct Diagnostic
=========================

Debug the deduct command specifically to see raw bytes.
"""

import socket
import time

from protocols.compass.protocol import CompassTransport, cmd_qr5
from protocols.passti.commands import cmd_deduct, parse_deduct_response
from protocols.passti.frame import parse_response

CONTROLLER_IP = "192.168.1.100"
CONTROLLER_PORT = 5000


def hexdump(data: bytes, label: str = ""):
    if label:
        print(f"  [{label}] {len(data)} bytes:")
    hex_str = data.hex()
    for i in range(0, len(hex_str), 32):
        chunk = hex_str[i : i + 32]
        print(f"    {i:04x}: {chunk}")


def main():
    print("E-Money Deduct Diagnostic")
    print("=" * 60)

    transport = CompassTransport(CONTROLLER_IP, CONTROLLER_PORT)
    transport.connect(timeout=5.0)
    print("✅ Connected\n")

    deduct_frame = cmd_deduct(5000, 10)
    print("Deduct frame:")
    hexdump(deduct_frame, "PASSTI")

    qr_cmd = cmd_qr5(deduct_frame)
    print("\nQR5 command:")
    hexdump(qr_cmd, "Compass")

    print("\n⏳ Send command and tap card NOW (within 15 seconds)...")
    input("Press ENTER to send...")

    transport.send(qr_cmd)

    # Read ALL data for 15 seconds
    print("\nReading response (15s max)...")
    transport._sock.settimeout(15.0)
    buffer = b""
    start = time.time()

    while time.time() - start < 15:
        try:
            transport._sock.settimeout(0.3)
            chunk = transport._sock.recv(4096)
            if chunk:
                buffer += chunk
                print(f"  [{time.time()-start:.1f}s] +{len(chunk)} bytes = {len(buffer)} total")
        except socket.timeout:
            pass

        # Check if we have complete QT wrapper
        idx = buffer.find(b"\xa6QT")
        if idx != -1:
            footer = buffer.find(b"\xa9", idx + 3)
            if footer != -1:
                # Make sure we have ALL the data between QT and \xa9
                qt_len = footer - (idx + 3)
                print(f"  Found \\xa6QT..\\xa9 wrapper, {qt_len} bytes between them")
                # Don't break yet — keep reading in case more data
                # But check if the frame says it's complete
                qt_data = buffer[idx + 3 : footer]
                if len(qt_data) >= 3:
                    data_len = (qt_data[1] << 8) | qt_data[2]
                    expected = 3 + data_len + 1
                    print(f"  Frame says length={data_len}, expected total={expected}, have={len(qt_data)}")
                    if len(qt_data) >= expected:
                        print(f"  ✅ Complete frame received!")
                        break

    print(f"\n{'='*60}")
    print(f"Total received: {len(buffer)} bytes")
    hexdump(buffer, "RAW")

    # Extract QT
    idx = buffer.find(b"\xa6QT")
    if idx != -1:
        footer = buffer.find(b"\xa9", idx + 3)
        if footer != -1:
            qt_data = buffer[idx + 3 : footer]
            print(f"\nQT data ({len(qt_data)} bytes):")
            hexdump(qt_data)

            result = parse_response(qt_data)
            print(f"\nParsed:")
            for k, v in result.items():
                if isinstance(v, bytes):
                    print(f"  {k}: {v.hex()}")
                else:
                    print(f"  {k}: {v}")

            if result.get("ok"):
                parsed = parse_deduct_response(result.get("body", b""))
                print(f"\nDeduct parse:")
                for k, v in parsed.items():
                    if isinstance(v, bytes):
                        print(f"  {k}: {v.hex()}")
                    else:
                        print(f"  {k}: {v}")

    transport.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
