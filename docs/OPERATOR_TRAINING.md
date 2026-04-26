# E-Parking v2 — Operator Training Guide

> **Date:** 26 April 2026
> **Audience:** Parking operators (cashiers, attendants)
> **Prerequisite:** User account with "operator" role

---

## 1. Getting Started

### Login
1. Open browser and navigate to the parking system URL
2. Enter your username and password
3. Click **Masuk**
4. You will be redirected to the POS (Point of Sale) page

### Logout
1. Click **Keluar** in the left sidebar
2. Confirm logout
3. Always logout when leaving your station

---

## 2. POS Page (Main Screen)

The POS page is where you process vehicle exits. This is your primary workspace.

### Layout
- **Top left**: Gate selector (dropdown) — select which exit gate you are monitoring
- **Center**: Current transaction information
- **Right**: Camera snapshot of the exit gate
- **Bottom**: Payment buttons (Cash, RFID, E-Money)

### Normal Flow
1. Vehicle approaches exit gate
2. Camera snapshot appears automatically
3. Transaction information loads (entry time, duration, fee)
4. Driver presents payment method
5. You process the payment
6. Gate opens automatically

---

## 3. Cash Payment

### When to Use
- Visitor paid with ticket
- Member wants to pay cash
- E-money payment failed

### Steps
1. Vehicle is at gate, transaction is displayed
2. Click **Bayar Tunai** (or press **F1**)
3. Cash modal opens showing:
   - Parking fee (e.g., Rp 5,000)
   - Input field for amount received
4. Enter amount received from driver
5. Change is calculated automatically
6. Click **Konfirmasi**
7. Gate opens, receipt prints

### Keyboard Shortcuts
- **F1** — Open cash payment modal
- **Escape** — Close modal

---

## 4. RFID Member Payment

### When to Use
- Member taps RFID card at exit
- No fee for members (prepaid subscription)

### Steps
1. Vehicle is at gate
2. Click **Bayar RFID** (or press **F2**)
3. RFID modal opens
4. Member taps card on reader (or enter card number manually)
5. System validates member
6. If valid: gate opens automatically
7. If invalid/expired: error message displayed

### Common Issues
| Issue | Cause | Solution |
|-------|-------|----------|
| "Kartu tidak valid" | Card not registered | Ask driver to pay cash |
| "Kartu habis masa berlaku" | Membership expired | Ask driver to pay cash, inform admin |
| "Kartu belum selesai transaksi" | Unclosed entry | Ask driver to contact admin |

---

## 5. E-Money Payment

### When to Use
- Driver wants to pay with e-money card (Mandiri eMoney, BRI Brizzi, BNI TapCash, BCA Flazz)

### Steps
1. Vehicle is at gate
2. Click **Bayar E-Money** (or press **F3**)
3. E-Money status panel shows **"Tempelkan kartu e-money"**
4. Driver taps card on PASSTI reader
5. System processes deduction
6. Status updates:
   - **PROCESSING** → spinner
   - **SUCCESS** → green check, gate opens
   - **INSUFFICIENT** → offer cash or RFID alternative
   - **FAILED** → offer retry or cash

### Lost Contact (Card Removed Early)
If driver removes card during processing:
1. Status shows **"Proses koreksi..."**
2. Ask driver to **tap the SAME card again**
3. System auto-continues the transaction
4. If successful: gate opens
5. If failed: offer cash payment

### Keyboard Shortcuts
- **F3** — Start e-money payment
- **Escape** — Cancel e-money payment

---

## 6. Timeout Alert

### What Happens
- If vehicle stays at gate > 120 seconds without payment
- System shows **"Mohon Hubungi Petugas"**
- Alert appears on your screen

### Your Actions
1. Check the camera snapshot
2. Approach the driver
3. Determine issue (no money, card problem, etc.)
4. Resolve:
   - **Buka Manual** — Open gate manually (logs reason)
   - **Reset Gate** — Reset gate state (vehicle left)
5. Always log the reason for manual override

---

## 7. Common Scenarios

### Scenario: Driver Lost Ticket
1. Ask driver for plate number
2. Go to **Transaksi** page
3. Search by plate number
4. Find active transaction
5. Return to POS and process payment

### Scenario: Wrong Vehicle at Gate
1. Do NOT open gate
2. Click **Reset Gate** (if available)
3. Wait for correct vehicle

### Scenario: Gate Doesn't Open After Payment
1. Check WebSocket connection indicator (green dot = connected)
2. If disconnected: refresh page (F5)
3. If still stuck: click **Buka Manual** and notify admin

### Scenario: Printer Not Working
1. Cash payment: collect money, note transaction ID
2. E-money/RFID: transaction completes normally
3. Notify admin about printer issue
4. Provide handwritten receipt if required

---

## 8. Daily Procedures

### Start of Shift
1. Login to system
2. Verify gate selector shows correct gate
3. Check WebSocket connection (green indicator)
4. Test printer (print test page if available)

### During Shift
1. Monitor POS page continuously
2. Process payments promptly
3. Watch for timeout alerts
4. Keep area clean

### End of Shift
1. Complete all pending transactions
2. Logout
3. Hand over to next operator
4. Report any issues to supervisor

---

## 9. Emergency Procedures

### System Down
1. Switch to **manual mode**
2. Open gates manually using physical button
3. Note all transactions on paper
4. Notify supervisor immediately
5. Do NOT restart equipment without admin

### Power Outage
1. Gates should fail-safe open (check with admin)
2. Direct traffic manually
3. Note license plates for reconciliation
4. Wait for power restoration

### Security Incident
1. Do NOT confront suspicious persons
2. Press emergency button (if available)
3. Call security/police
4. Note details for report

---

## 10. Support Contacts

| Issue | Contact | Method |
|-------|---------|--------|
| System not responding | Supervisor | Radio / Phone |
| Payment issue | Supervisor | Radio / Phone |
| Gate hardware failure | Maintenance | Phone |
| Security concern | Security | Emergency button / Phone |

---

*This guide should be kept at every POS station. Review monthly with supervisor.*
