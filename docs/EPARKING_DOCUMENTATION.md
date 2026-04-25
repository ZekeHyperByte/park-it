# E-Parking System Documentation

## Overview

This document contains the technical specifications and infrastructure details for building a parking payment system using Indonesian e-money cards (Mandiri eMoney, BRI Brizzi, BNI TapCash, BCA Flazz, etc.) with the PASSTI Reader from PT Softorb.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Command Protocol](#command-protocol)
3. [Settlement Infrastructure](#settlement-infrastructure)
4. [Development Kit vs Production](#development-kit-vs-production)
5. [Preparation Checklist](#preparation-checklist)
6. [Vendor Contacts](#vendor-contacts)
7. [Resources](#resources)

---

## Architecture Overview

### System Flow

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Card      │──────│   Reader    │──────│  Payment    │──────│   Bank/     │
│  (eMoney)   │      │  (PASSTI)   │      │  Gateway    │      │  Acquirer   │
└─────────────┘      └─────────────┘      └─────────────┘      └─────────────┘
                                                 │
                                          ┌──────┴──────┐
                                          │   Issuer    │
                                          │ (Mandiri/   │
                                          │  BCA/etc)   │
                                          └─────────────┘
```

### Money Flow

| Step | What Happens | Where Money Is |
|------|---------------|----------------|
| **1. Deduct** | Card value decreased | Still on card (logically) |
| **2. Settlement** | File uploaded to acquirer | Being processed |
| **3. Clearing** | Acquirer validates transactions | In transit |
| **4. Settlement** | Funds transferred | **MERCHANT ACCOUNT** |

### Key Point: Where Does the Money Go?

The money goes to **YOUR merchant account**, not the card issuer!

```
User loads money:    User's bank → Card issuer → Card (stored value)
User pays parking:   Card → Your reader → Your merchant account (settlement)
```

---

## Command Protocol

### Frame Structure

```
┌─────────────────────────────────────────────────────────────┐
│  STX │ LEN-H │ LEN-L │ EF │ 01 │ CMD │ DATA[n] │ LRC        │
│ 0x02 │ 0xHH  │ 0xHH  │    │    │0x01-│         │ XOR checksum│
│      │       │       │    │    │0x0C │         │            │
└─────────────────────────────────────────────────────────────┘
```

### Command Reference

| Command | Code | Description | Parameters |
|---------|------|-------------|------------|
| **INIT** | `0x01` | Initialize reader | 16 bytes Init Key |
| **Check Balance** | `0x02` | Read card info | Date(4B BCD) + Time(3B BCD) + Timeout(2B BCD) |
| **Deduct** | `0x03` | Decrement card value | Date + Time + Amount(4B) + Timeout |
| **Cancel Deduct** | `0x04` | Cancel lost contact correction | None |
| **Get Last Transaction** | `0x05` | Retrieve last transaction log | None |
| **Mifare** | `0x07` | Mifare card operations | Various |
| **Display/Buzzer** | `0x09` | Control display and buzzer | TLV data |
| **Debug Log BRI** | `0x0B` | Get BRI debug log | None |
| **Get Reader Info** | `0x0C` | Get device information | None |

### Response Codes

| Code | Status | Description |
|------|--------|-------------|
| `00 00 00` | Success | Command executed successfully |
| `01 10 01` | Error | General error |
| `01 10 02` | Error | Reader waiting timeout (no card) |
| `01 10 03` | Error | Reader initialization failed (wrong key) |
| `01 10 04` | Error | Not enough card balance |
| `01 10 05` | Error | Lost contact during transaction |
| `01 10 06` | Error | Expected previous card (auto-correction) |
| `01 10 07` | Error | Deduct interval too short (default 2 sec) |
| `01 10 09` | Error | BNI inactive card |
| `01 10 10` | Error | Expected same deduct amount (correction) |

### Card Type Codes

| Code | Card Type |
|------|-----------|
| `0x01` | Luminos Prepaid Card |
| `0x02` | MANDIRI eMoney Card |
| `0x03` | BRI BRIZZI Card |
| `0x04` | BNI Tapcash Card |
| `0x05` | BCA FLAZZ Card |
| `0x06` | DKI JakCard |
| `0x07` | NOBU Card |
| `0x08` | MEGA MegaCash Card |
| `0x09` | QR Payment |

### Deduct Response Format

```
3B  Status Code
1B  Card Type
8B  MID Reader
4B  TID Reader
7B  DateTime (BCD ddmmyyyyhhnnss)
8B  Card Number
4B  Deduct Amount (Hex Integer)
4B  Remaining Balance (Hex Integer)
4B  Transaction Counter per day
nB  Card Log Transaction (encrypted)
```

### Lost Contact Handling

**Critical**: If a user removes their card mid-transaction (status `011005`):

1. **Reader flags the transaction as incomplete**
2. **You MUST retry with the SAME card** - reader enforces this (status `011006`)
3. **Or call Cancel Deduct Correction (`0x04`)** to allow a different card

```python
if deduct_result["status"] == (0x01, 0x10, 0x05):
    # Lost contact - need to retry with same card
    print("Card removed during transaction. Please tap the SAME card again.")
    # Retry deduct with SAME amount
```

---

## Settlement Infrastructure

### Settlement File Format

#### Filename Structure

```
YYYYMMDDHHMMSS + MID(16) + TID(8) + Version(2) + BatchNo(3) + .txt

Example: 2018010310470002034567890ABCDE8765432101101.txt
         │││││││││││││└MID───┘└─TID──┘││└Batch
         │││││││││││││                  │└Version
         └┴┴┴┴┴┴┴┴┴┴┴└──────────────────┘
          YYYYMMDDHHMMSS (Settlement Date/Time)
```

#### File Content Structure

```
0020000000002     ← Header: 2 transactions, Rp 2 total
[Transaction Log 1] ← Raw deduct response data
[Transaction Log 2] ← Raw deduct response data
```

#### Header Format

| Field | Length | Description |
|-------|--------|-------------|
| Trx Count | 3 | Total transactions (max 999) |
| Trx Amount | 10 | Total amount in Rupiah |
| Line Feed | 1 | Newline (LF) |

#### Transaction Data Format

| Field | Length | Description |
|-------|--------|-------------|
| Transaction Log | n | Response data from deduct command (Card Type to Card Log) |
| Line Feed | 1 | Newline (LF) |

### Settlement Response File

After uploading, acquirer returns response file:

**Filename**: Same as settlement file but with `.OK` or `.NOK` extension

**Content Structure**:
```
01002     ← Response Header (Type + Count)
[Transaction Data] + Status(2B)
[Transaction Data] + Status(2B)
```

#### Response Status Codes

| Code | Status | Description |
|------|--------|-------------|
| `00` | Accepted | Transaction accepted |
| `01` | Invalid Format | Format error |
| `02` | Duplicate | Duplicate transaction |
| `03` | Count Mismatch | Transaction count doesn't match |
| `04` | Amount Mismatch | Transaction amount doesn't match |
| `05` | Invalid Terminal | Merchant/Terminal invalid |
| `07` | Data Corrupt | Data corrupted |
| `08` | Invalid SN | Device serial number invalid |
| `09` | Invalid Bank Log | Bank log validation failed |
| `10` | Invalid Filename | Filename format error |
| `11` | Invalid Header | Header format error |

### Settlement Upload Process

```
1. End of business day
2. Generate settlement file from transaction logs
3. Upload via SFTP/API to acquirer
4. Wait for response file (.OK or .NOK)
5. Process response (handle rejections)
6. Funds settled to merchant account (T+1)
```

---

## Development Kit vs Production

### What You CAN Do with Dev Kit

✅ **Complete Software Development**
- Build parking logic (entry/exit flow)
- Database schema and session management
- Fee calculation algorithms
- UI/UX (display messages, buzzer patterns)
- Reporting and analytics
- **Settlement file generation**

✅ **Testing with Dummy Cards**
- Test all command sequences
- Simulate various scenarios (lost contact, insufficient balance, etc.)
- Validate frame protocols and error handling
- Test timeout and retry logic

✅ **Integration Testing**
- Test backend systems
- Build reconciliation logic
- Create settlement upload mechanisms
- Test file format generation

### What You CANNOT Do with Dev Kit

| Limitation | Why | Impact |
|------------|-----|--------|
| **Real e-money cards** | No SAM module = can't authenticate real cards | Can only use test cards |
| **Actual settlements** | No merchant credentials | Money won't transfer |
| **Production certification** | Dev kit not certified | Can't go live |

### Migration Path: Dev → Production

```
PHASE 1: DEVELOPMENT (Now)
├── Build complete parking software
├── Test all flows with dummy cards
├── Generate settlement files
├── Build backend/admin dashboard
└── Create reporting system

PHASE 2: UPGRADE HARDWARE
├── Order certified readers with SAM from Softorb
├── Get production init keys from acquirer
├── Sign merchant agreement
└── Get MID/TID assigned

PHASE 3: CERTIFICATION (2-4 weeks)
├── Submit system for BI certification
├── Pass security and compliance tests
└── Receive production approval

PHASE 4: GO LIVE
├── Replace dev kit with certified readers
├── Start accepting real e-money
└── Daily settlement uploads begin
```

---

## Preparation Checklist

### Immediate (Can Do Now with Dev Kit)

- [ ] Build complete entry/exit flow logic
- [ ] Implement fee calculation (grace period, hourly rates)
- [ ] Create session management (active, completed, abandoned)
- [ ] Implement all reader commands
- [ ] Build settlement file generator
- [ ] Create transaction log storage system
- [ ] Implement reconciliation logic
- [ ] Handle lost contact scenarios
- [ ] Build admin dashboard
- [ ] Create reporting system

### Hardware Preparation

- [ ] Contact PT Softorb for production reader quote
- [ ] Order readers with SAM modules
- [ ] Plan reader deployment locations
- [ ] Prepare installation infrastructure

### Business Requirements

- [ ] Register legal entity (PT/CV) if not done
- [ ] Prepare business documents (NPWP, SIUP, TDP)
- [ ] Open business bank account
- [ ] Prepare domicile letter

### Merchant Setup

- [ ] Choose acquirer (Luminos/Artajasa/Jalin/Rintis)
- [ ] Submit merchant application
- [ ] Sign acquirer agreement
- [ ] Get MID/TID assigned
- [ ] Receive production init keys
- [ ] Set up SFTP/API credentials for settlement

### Certification

- [ ] Submit for BI certification
- [ ] Pass security testing
- [ ] Pass compliance testing
- [ ] Receive production approval

### Go-Live

- [ ] Deploy certified readers
- [ ] Configure production keys
- [ ] Start accepting real e-money
- [ ] Begin daily settlement uploads
- [ ] Monitor transactions and reconciliation

---

## Vendor Contacts

### Reader Manufacturer

**PT Softorb Technology Indonesia**
- Address: Komplek Mutiara Taman Palem Blok A11 No.8, Cengkareng Timur, Jakarta Barat 11730
- Phone: +62 21 29668601/02/03
- Fax: +62 21 54350246
- Website: www.softorb.co.id
- **What to ask**: "Saya mau upgrade ke reader produksi dengan SAM module untuk parking system"

### Payment Switches/Acquirers

| Provider | Type | Website | What to Ask |
|----------|------|---------|-------------|
| **Luminos** | Payment Switch | www.luminos.co.id | "Saya ingin menjadi merchant untuk sistem parking dengan e-money" |
| **Artajasa** | Payment Switch | www.artajasa.co.id | "Proses registrasi merchant baru untuk terminal payment" |
| **Jalin** | Payment Switch (BUMN) | www.jalin.co.id | Merchant registration |
| **Rintis** | Payment Switch (BCA) | www.rintis.com | Merchant registration |

### Banks (Direct Acquirer)

- Bank Mandiri
- BCA (Bank Central Asia)
- BRI (Bank Rakyat Indonesia)
- BNI (Bank Negara Indonesia)

Contact their merchant services department.

### All-in-One Parking Solutions

- **Luminos** - Hardware + software + settlement
- **Lippolink** - Parking management system
- **PayAccess** - Payment infrastructure

---

## Resources

### Documents

1. **Command Protocol Reader V1.12 ENG.pdf** - Complete command reference
2. **Format File Settlement Multibank v1.3.pdf** - Settlement file specifications
3. **BI Regulations** - Bank Indonesia payment system regulations

### Technical References

- ISO 8583 - Financial transaction message format
- EMVCo specifications - Payment card standards
- PCI DSS - Payment card industry security standards

### Indonesian E-Money Systems Supported

- Mandiri eMoney
- BRI Brizzi
- BNI TapCash
- BCA Flazz
- DKI JakCard
- NOBU Card
- MEGA MegaCash
- Luminos Prepaid
- QR Payment (various providers)

---

## Important Notes

### Security

- **Never commit production init keys to version control**
- **Use environment variables for sensitive data**
- **Implement proper transaction log encryption**
- **Follow PCI DSS guidelines for card data handling**

### Daily Operations

- **Must upload settlement files daily** (typically end of business day)
- **Keep transaction logs for reconciliation**
- **Monitor settlement response files for rejections**
- **Handle chargebacks/disputes through acquirer**

### Compliance

- **BI Certification is mandatory** for production
- **SAM module is mandatory** for real card processing
- **Settlement is mandatory** - offline transactions won't be paid

---

## Document Information

- **Created**: April 2026
- **Based on**: Command Protocol Reader V1.12 ENG, Format File Settlement Multibank v1.3
- **Hardware**: PASSTI Reader from PT Softorb Technology Indonesia
- **Purpose**: E-Parking payment system using Indonesian e-money

---

*This is a confidential technical document for development purposes.*
