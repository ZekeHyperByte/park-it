# Hardware Integration Test Report

> **Date:** 25 April 2026
> **Tester:** Hardware-connected validation against Compass controller at 192.168.1.100:5000
> **Scope:** Controller TCP, STAT polling, gate trigger, inputs (IN1/IN2), RFID (Wiegand W), e-money reader (Serial2 passthrough)

---

## Test Environment

| Component | Details |
|-----------|---------|
| Controller | Compass protocol, IP 192.168.1.100, port 5000 |
| Connection | Direct Ethernet cable (no switch) |
| Laptop IP | 192.168.1.50/24 (static, manually assigned) |
| RFID Reader | Wiegand W channel |
| E-Money Reader | PASSTI dev kit on controller Serial2 (38400 baud) |
| Buttons | IN1 (ticket), IN2 (vehicle detect) |

---

## Test Results

| # | Test | Status | Notes |
|---|------|--------|-------|
| 1 | TCP Connectivity | ✅ PASS | Controller responds immediately |
| 2 | STAT Polling | ✅ PASS | All inputs readable, Wiegand parsed correctly |
| 3 | Gate Trigger (TRIG1) | ✅ PASS | Gate opens on command |
| 4 | Audio Playback | ⏭️ SKIP | No audio hardware installed |
| 5 | LED Display | ⏭️ SKIP | No display hardware installed |
| 6 | IN1 Button | ✅ PASS | Detected within 5 seconds |
| 7 | IN2 Button | ✅ PASS | Detected within 5 seconds |
| 8 | RFID Card Read | ✅ PASS | Card 761024665 detected via Wiegand W |
| 9 | E-Money Init | ✅ PASS | MID=D021095711020001, TID=09570004 |
| 10 | Check Balance | ✅ PASS | Card 5715048100000048, balance Rp 708,994 |
| 11 | Deduct | ✅ PASS | Rp 5,000 deducted, remaining Rp 693,994 |

**Final Score: 8/8 tested components passed (100%)**

---

## Bugs Found & Fixed

### Bug 1: E-Money Response Truncated by False `©` Delimiter

**Severity:** Critical — would break all deduct/get_last_transaction operations in production

**Root Cause:**
The controller wraps Serial2 responses as `\xa6QT<data>\xa9`. The code searched for `\xa9` as a footer delimiter using `buffer.find(b"\xa9")`. However, byte value `0xA9` (169) appears naturally inside encrypted transaction log data, causing the parser to truncate long responses.

**Evidence:**
- Check balance: 20 bytes QT data → worked fine
- Deduct: 181 bytes QT data → falsely truncated to 125 bytes at an internal `\xa9`

**Impact:**
- `parse_response()` received incomplete data → "Incomplete response" error
- Deduct and GetLastTransaction commands always failed

**Fix:**
Instead of searching for `\xa9`, parse the PASSTI frame length from the header:
```python
payload_len = (buffer[qt_start + 1] << 8) | buffer[qt_start + 2]
expected_qt_len = 3 + payload_len + 1  # STX+LEN + payload + LRC
```

**Files Modified:**
- `protocols/passti/transport.py` — `ControllerPassthroughTransport.send_recv()`
- `scripts/hardware_test.py` — `send_emoney_cmd()`

---

### Bug 2: `parse_check_balance_response()` Missing `"ok": True`

**Severity:** Medium — test/logic confusion, no functional impact on hardware

**Root Cause:**
`parse_check_balance_response()` only returned `"ok"` on error (`{"ok": False, "error": ...}`). On success it returned card data WITHOUT an `"ok"` key. This was inconsistent with `parse_deduct_response()` which returns `"ok": True`.

**Impact:**
- Test code checking `parsed.get("ok", False)` falsely reported failure
- Any downstream code relying on `"ok"` field would misinterpret success

**Fix:**
Added `"ok": True` to the successful return path.

**File Modified:**
- `protocols/passti/commands.py` — `parse_check_balance_response()`

---

### Bug 3: Socket Timeout Breaks Before QT Response Arrives

**Severity:** Medium — caused intermittent failures depending on timing

**Root Cause:**
The old code used one long socket timeout (e.g. 12s) and broke the loop on `socket.timeout`. But the controller sends:
1. Immediate `\xa6QROK\xa9` ack (6 bytes)
2. ~1-3 seconds later: `\xa6QT<data>\xa9` response

If the first `recv()` timed out after getting only the QROK, the loop broke before the QT data arrived.

**Fix:**
Use short 0.5s recv timeouts in a continuous loop, checking for complete frame after each chunk.

**Files Modified:**
- `protocols/passti/transport.py`
- `scripts/hardware_test.py`

---

## Network Setup Note

Direct laptop-to-controller cable requires a static IP on the laptop's Ethernet interface:

```bash
sudo ip addr add 192.168.1.50/24 dev enp0s31f6
```

The controller does not run DHCP. Without this, the laptop has no route to 192.168.1.100.

---

## Codebase Adjustments Summary

| File | Change | Reason |
|------|--------|--------|
| `protocols/passti/transport.py` | Complete rewrite of `send_recv()` | Fixes delimiter bug + timeout handling |
| `protocols/passti/commands.py` | Add `"ok": True` to `parse_check_balance_response()` | Consistency with other parsers |
| `scripts/hardware_test.py` | Rewrite `send_emoney_cmd()` | Same fixes as transport layer |
| `scripts/emoney_diagnostic.py` | New file | Raw byte capture for debugging |
| `scripts/deduct_diagnostic.py` | New file | Deduct-specific diagnostic |

---

## Recommendations

1. **The `©` delimiter bug exists in the prototype too** (`prototype/prototype.py` line 138). The prototype should be updated if it's still used.

2. **DirectSerialTransport** in `protocols/passti/transport.py` uses `read_until(expected=bytes([frame[-1]]))` which may have similar issues. Recommend switching to length-based parsing.

3. **For production deployment:** If the controller and server are on the same LAN via a switch (not direct cable), ensure the server has a static IP in the 192.168.1.x range or the controller is configured for the server's subnet.

4. **Test coverage:** The daemon tests use `FakeRedis` and `MockTransport` — they don't test real socket behavior. Consider adding integration tests that verify the passthrough framing logic with raw byte sequences containing internal `\xa9` bytes.

---

*End of Hardware Test Report*
