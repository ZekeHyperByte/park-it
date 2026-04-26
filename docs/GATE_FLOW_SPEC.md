# Gate Flow Specification — Entry & Exit

> **Version**: 2.0 (Corrected)  
> **Status**: Approved  
> **Key Change**: Gate-first mandate is now method-dependent at entry.

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Gate-In Flows](#2-gate-in-flows)
3. [Gate-Out Flows](#3-gate-out-flows)
4. [Error Handling Matrix](#4-error-handling-matrix)
5. [State Machine Diagrams](#5-state-machine-diagrams)

---

## 1. Design Principles

### Priority Hierarchy

```
1. Gate movement    → MUST happen (physical safety, never trap a vehicle)
2. Transaction DB   → MUST happen (business record)
3. Ticket/receipt   → SHOULD happen (can be recovered)
4. Snapshot/ANPR    → SHOULD happen (best-effort)
5. Display/audio    → CAN happen (cosmetic)
```

### Gate-First Rule (Corrected)

> **Gate-first applies at exit only — NOT universally at entry.**

| Context | Rule | Rationale |
|---|---|---|
| **Cash Entry** | Print-first, then open gate | Ticket IS the transaction identifier |
| **RFID Entry** | Gate-first (card is identifier) | Card can be used to look up transaction |
| **E-Money Entry** | Gate-first (card is identifier) | Card number stored, no ticket needed |
| **All Exit Methods** | Gate-first (payment already done) | Missing receipt is recoverable |

### Never Trap a Vehicle

A vehicle should never be physically trapped due to a peripheral failure (printer, camera, display). If a cash-entry ticket fails to print, the fallback is to display the barcode on the LED and alert the operator — the gate still opens after a reasonable attempt.

---

## 2. Gate-In Flows

### 2.1 Cash Entry (Print-First)

```
 ┌─ Vehicle Detection ─────────────────────────────────────────────────┐
 │                                                                     │
 │  IN1 ON ──▶ Display "Selamat Datang / Tekan Tombol"                 │
 │            + Play audio track 7 (welcome)                           │
 │                                                                     │
 ├─ Button Press ──────────────────────────────────────────────────────┤
 │                                                                     │
 │  IN2 ON ──▶ Create transaction in DB (barcode generated)            │
 │           ▶ Take snapshot (async, best-effort)                      │
 │           ▶ Run ANPR if enabled (async, best-effort)                │
 │           ▶ Run vehicle detection if enabled (async, best-effort)   │
 │           ▶ PRINT TICKET ◀── BLOCKING                               │
 │              │                                                      │
 │              ├── Print OK ──▶ Play "Ambil Tiket" + OPEN GATE        │
 │              │                                                      │
 │              └── Print FAIL ▶ Display barcode on LED                │
 │                             ▶ Alert operator with barcode number    │
 │                             ▶ OPEN GATE (don't trap)                │
 │                                                                     │
 ├─ Vehicle Pass-Through ──────────────────────────────────────────────┤
 │                                                                     │
 │  IN3 ON/OFF or IN1 OFF ──▶ Display "Terima Kasih" ──▶ IDLE         │
 │  Timeout (10s fallback) ──▶ IDLE                                    │
 │                                                                     │
 └─────────────────────────────────────────────────────────────────────┘
```

**Key**: Ticket printing is attempted synchronously. If print fails, barcode is shown on LED display and operator is notified. Gate still opens to avoid trapping the vehicle, but only after the fallback is executed.

### 2.2 RFID Entry (Gate-First)

```
 ┌─ Vehicle Detection ─────────────────────────────────────────────────┐
 │                                                                     │
 │  IN1 ON ──▶ Display "Tempelkan Kartu / Member RFID"                 │
 │                                                                     │
 ├─ Card Read ─────────────────────────────────────────────────────────┤
 │                                                                     │
 │  Wiegand W/X ──▶ Validate member via API                           │
 │                  │                                                  │
 │                  ├── Valid + Active ──▶ OPEN GATE                    │
 │                  │                    ▶ Take snapshot (async)        │
 │                  │                    ▶ Print ticket (async, opt.)   │
 │                  │                                                  │
 │                  ├── Expired ──▶ Play track 13 + "Masa Berlaku Habis"│
 │                  │              ▶ Wait for different card            │
 │                  │                                                  │
 │                  ├── Unclosed ──▶ Play track 14 + "Belum Selesai"    │
 │                  │               ▶ Wait for different card           │
 │                  │                                                  │
 │                  ├── Expiring Soon (≤5 days) ──▶ Play track 11/12    │
 │                  │                              ▶ Continue normally  │
 │                  │                                                  │
 │                  └── Not Found ──▶ Play track 3 + "Kartu Invalid"   │
 │                                   ▶ Wait for different card         │
 │                                                                     │
 └─────────────────────────────────────────────────────────────────────┘
```

**Key**: Card IS the identifier. No ticket needed. Gate opens immediately on valid card.

### 2.3 E-Money Entry (Gate-First)

```
 ┌─ Vehicle Detection ─────────────────────────────────────────────────┐
 │                                                                     │
 │  IN1 ON ──▶ Display "Tempelkan Kartu / E-Money"                     │
 │                                                                     │
 ├─ Card Tap ──────────────────────────────────────────────────────────┤
 │                                                                     │
 │  PASSTI card detected ──▶ Check Balance                             │
 │                           │                                         │
 │                           ├── Balance ≥ threshold ──▶ OPEN GATE     │
 │                           │   ▶ Display "Cetak Tiket? Tekan Tombol" │
 │                           │   ▶ Wait 10s for print decision         │
 │                           │     ├── Button pressed → print ticket   │
 │                           │     └── Timeout → skip print            │
 │                           │                                         │
 │                           └── Balance < threshold ──▶ Display saldo │
 │                               ▶ Play track 6 + "Saldo Tidak Cukup" │
 │                               ▶ Return to IDLE                      │
 │                                                                     │
 │  NOTE: No deduction at entry. Deduction only happens at exit.       │
 │  Entry balance check is a courtesy warning only.                    │
 │                                                                     │
 └─────────────────────────────────────────────────────────────────────┘
```

**Key**: Card number is stored as identifier. Balance is checked but NOT deducted. Gate opens for sufficient balance.

### 2.4 Common Inputs (All Modes)

| Input | Behavior |
|---|---|
| **IN3 ON** (exit loop) | Reset to IDLE |
| **IN4 ON** (help button) | Play track 5, notify operator, wait |
| **IN1 OFF** (vehicle turn-back) | Reset to IDLE |

---

## 3. Gate-Out Flows

### 3.1 Concurrent Payment Detection

Gate-out accepts **three payment methods simultaneously** using `asyncio.wait(FIRST_COMPLETED)`:

```
 ┌─ Vehicle Detected (IN1 + 500ms debounce) ────────────────────────┐
 │                                                                   │
 │  ▶ Take snapshot (async)                                          │
 │  ▶ Run ANPR if enabled (async, match against entry plate)         │
 │  ▶ Start 3 concurrent listeners:                                  │
 │                                                                   │
 │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐              │
 │  │  Wiegand     │  │  PASSTI     │  │  POS Cash    │              │
 │  │  (RFID tap)  │  │  (E-Money)  │  │  (Operator)  │              │
 │  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘              │
 │         │                │                │                       │
 │         └────────────────┼────────────────┘                       │
 │                          │                                        │
 │              FIRST_COMPLETED wins                                 │
 │              Other tasks cancelled                                │
 │                                                                   │
 ├─ Timeout (default 120s) ──▶ Alert operator + "Hubungi Petugas"    │
 │                                                                   │
 └───────────────────────────────────────────────────────────────────┘
```

### 3.2 Cash Payment (Gate-First)

```
POS operator scans barcode / enters plate
  ▶ API: find transaction → calculate fee → display fee
  ▶ Operator collects cash, confirms on POS
  ▶ DB: complete transaction (payment_method = CASH)
  ▶ OPEN GATE
  ▶ Print receipt (async, can fail)
  ▶ Play track 10 (thank you)
```

### 3.3 RFID Member Payment (Gate-First)

```
Card tap detected (Wiegand W/X)
  ▶ API: validate member + find transaction
  ▶ DB: complete transaction (payment_method = RFID_MEMBER, fee = 0)
  ▶ OPEN GATE
  ▶ Play track 9 (member approved)
```

### 3.4 E-Money Payment (Gate-First)

```
Card tap detected (PASSTI)
  ▶ API: find transaction → calculate fee
  ▶ Daemon: send DEDUCT command to PASSTI reader
  │
  ├── SUCCESS ──▶ DB: save emoney_transaction + complete parking_transaction
  │               ▶ OPEN GATE
  │               ▶ Print receipt (async)
  │               ▶ Play track 10
  │
  ├── LOST_CONTACT ──▶ Display "Tempel Kartu Lagi"
  │                    ▶ Retry with same card (auto-correction)
  │                    ▶ If correction verified → SUCCESS flow
  │                    ▶ If correction failed → FAILED flow
  │
  ├── INSUFFICIENT_BALANCE ──▶ Display "Saldo Tidak Cukup"
  │                            ▶ Reset, allow other payment method
  │
  ├── WRONG_CARD ──▶ Display "Kartu Salah"
  │                  ▶ Reset, allow retry
  │
  └── TIMEOUT ──▶ GetLastTransaction to verify
                  ▶ If found → SUCCESS flow
                  ▶ If not found → FAILED flow
```

### 3.5 Vehicle Left Without Payment

```
IN1 OFF during TIMEOUT_ALERT state
  ▶ Publish VehicleLeftEvent (reason: "abandoned")
  ▶ Flag transaction as LOST_CONTACT
  ▶ Log for investigation
  ▶ Return to IDLE
```

---

## 4. Error Handling Matrix

### Gate-In Errors

| Error | State | Response | Gate Opens? |
|---|---|---|---|
| Printer jam (cash) | PROCESSING | Show barcode on LED, alert operator | ✅ Yes (after fallback) |
| Controller disconnect | Any | Reconnect loop, alert operator | ❌ No (can't send TRIG1) |
| API unreachable | VALIDATING | Retry, then offline cache if available | ⚠️ Depends on cache |
| Camera failure | Any | Log warning, continue without snapshot | ✅ Yes (snapshot is optional) |
| ANPR failure | Any | Set plate_number = NULL, continue | ✅ Yes (ANPR is optional) |
| RFID card not found | WAITING_CARD | Play "invalid", wait for next card | ❌ No |
| E-Money low balance | CHECKING_BALANCE | Display saldo, return to IDLE | ❌ No |
| Paper counter at 0 | PROCESSING | Show barcode on LED, skip print | ✅ Yes |

### Gate-Out Errors

| Error | State | Response | Gate Opens? |
|---|---|---|---|
| E-Money deduct LOST_CONTACT | WAITING_PAYMENT | Prompt re-tap same card | ❌ No (retry) |
| E-Money deduct FAILED | WAITING_PAYMENT | Reset, allow other method | ❌ No |
| Payment timeout (120s) | TIMEOUT_ALERT | Alert operator, display help msg | ❌ No |
| Vehicle left unpaid | TIMEOUT_ALERT | Log abandonment, flag transaction | N/A |
| Receipt print fail | OPENING | Log warning, vehicle exits normally | ✅ Yes |
| Controller disconnect | Any | Reconnect loop, FORCE_OPEN if stuck | ✅ Yes (safety) |

---

## 5. State Machine Diagrams

### Gate-In States

```
                    ┌──────┐
                    │ IDLE │◀─────────────────────────────────────┐
                    └──┬───┘                                      │
                       │ IN1 ON                                   │
                    ┌──▼──────────────┐                           │
                    │ VEHICLE_PRESENT │                            │
                    └──┬──────────────┘                           │
                       │ gate close confirmed                     │
                    ┌──▼──────────┐                               │
                    │ GATE_CLOSED │                                │
                    └──┬──┬──┬───┘                                │
            ┌──────────┘  │  └──────────┐                         │
            ▼             ▼             ▼                         │
    ┌───────────────┐ ┌──────────┐ ┌──────────────┐              │
    │WAITING_BUTTON │ │WAITING   │ │WAITING_CARD  │              │
    │(CASH)         │ │_CARD     │ │(EMONEY)      │              │
    └───────┬───────┘ │(RFID)    │ └──────┬───────┘              │
            │ IN2     └────┬─────┘        │ PASSTI tap           │
            ▼              │              ▼                       │
    ┌───────────────┐      │      ┌───────────────┐              │
    │  PROCESSING   │◀─────┘      │CHECKING       │              │
    │  (print+open) │             │_BALANCE        │              │
    └───────┬───────┘             └───────┬───────┘              │
            │                             │ balance OK            │
            │                     ┌───────▼───────────┐          │
            │                     │WAITING_PRINT      │          │
            │                     │_DECISION           │          │
            │                     └───────┬───────────┘          │
            │                             │                       │
            ▼                             ▼                       │
    ┌───────────────┐             ┌───────────────┐              │
    │   OPENING     │◀────────────│  PROCESSING   │              │
    └───────┬───────┘             └───────────────┘              │
            │ vehicle passed                                      │
            └─────────────────────────────────────────────────────┘
```

### Gate-Out States

```
            ┌──────┐
            │ IDLE │◀──────────────────────────────┐
            └──┬───┘                                │
               │ IN1 ON + debounce                  │
            ┌──▼──────────────┐                     │
            │ VEHICLE_PRESENT │                     │
            └──┬──────────────┘                     │
               │ snapshot taken                     │
            ┌──▼──────────────┐                     │
            │WAITING_PAYMENT  │                     │
            │ (3 concurrent)  │                     │
            └──┬──────┬──┬───┘                     │
               │      │  │                          │
     ┌─────────┘      │  └──────────┐              │
     ▼                 ▼             ▼              │
  Wiegand          PASSTI          POS             │
  (RFID)          (E-Money)       (Cash)           │
     │                │             │               │
     └────────────────┼─────────────┘               │
                      │ FIRST_COMPLETED             │
                      ▼                              │
              ┌───────────────┐                     │
              │   OPENING     │                     │
              └───────┬───────┘                     │
                      │ vehicle passed               │
                      └──────────────────────────────┘
                      
              ┌─── If TIMEOUT (120s) ───┐
              ▼                          │
      ┌───────────────┐                 │
      │ TIMEOUT_ALERT │                 │
      └───────┬───────┘                 │
              │ IN1 OFF (vehicle left)  │
              └─────────────────────────┘
```

### Audio Track Mapping

| Track | Message | Used In |
|---|---|---|
| 2 | Silakan Ambil Tiket | Cash entry, ticket printed |
| 3 | Kartu Tidak Terdaftar | Invalid card |
| 5 | Mohon Tunggu Petugas | Help button |
| 6 | Terimakasih / Saldo Tidak Cukup | Thank you / low balance |
| 7 | Selamat Datang | Vehicle detected |
| 8 | Hubungi Petugas | Payment timeout |
| 9 | Member Approved | RFID member exit |
| 10 | Pembayaran Berhasil | E-Money success |
| 11 | Kartu Expired Dalam 5 Hari | Card expiring warning |
| 12 | Kartu Expired Dalam 1 Hari | Card expiring warning |
| 13 | Kartu Habis Masa Berlaku | Card expired |
| 14 | Transaksi Belum Selesai | Unclosed transaction |

---

*Document Information — Created: April 2026 — E-Parking V2*
