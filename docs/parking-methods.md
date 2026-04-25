# Parking System - Hardware Communication Flow

## Overview

This document details the complete hardware communication flow for all parking methods in the E-Parking System. The system consists of multiple Python daemons that communicate with physical hardware (gate controllers, RFID/UHF readers, printers, LED displays, cameras) via TCP sockets, serial ports, and WebSockets.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Laravel 11 Backend                            │
│  REST API │ MySQL │ Queue Workers │ Reverb WebSockets                │
└──────────┬────────────────────────────────────┬──────────────────────┘
           │ HTTP API (port 80)                  │ WebSocket (port 5678)
┌──────────▼────────────────────────────────────▼──────────────────────┐
│                    Python Hardware Daemons                             │
│  parking.py │ parking-enet.py │ gate_out.py │ uhf-reader.py          │
└──────────┬────────────────────┬────────────────┬──────────────────────┘
           │ TCP Socket          │ Serial         │ TCP/Serial
┌──────────▼────────────────────▼────────────────▼──────────────────────┐
│                        Physical Hardware                               │
│  Gate Controllers │ RFID/UHF Readers │ Printers │ LED │ Cameras      │
└───────────────────────────────────────────────────────────────────────┘
```

### Systemd Services

| Service | Script | Purpose |
|---------|--------|---------|
| `parking.service` | `parking.py` | Primary gate-in controller daemon |
| `gate-out.service` | `gate_out.py` | Exit gate WebSocket server |
| `uhf-reader.service` | `uhf-reader.py` | UHF RFID reader daemon |
| `websocket.service` | Laravel Reverb | Real-time WebSocket server |

---

## Gate Controller Protocols

The system supports two gate controller board protocols:

### 1. Compass Protocol (Custom)
- **Prefix/Suffix**: `\xa6` (start) / `\xa9` (end)
- **Default Port**: `5000`
- **Used by**: `parking.py`, `parking-bak.py`, `parking-blocking.py`

### 2. ENET Protocol
- **Prefix/Suffix**: `:` (start) / `;` (end)
- **Default Port**: `4000`
- **Used by**: `parking-enet.py`

### 3. Serial Protocol
- **Delimiter**: `*` (start) / `#` (end)
- **Used by**: `parking-serial.py`

---

## Input/Sensor Mapping

All gate controllers use the same physical inputs mapped as follows:

| Input | Sensor Type | Purpose |
|-------|-------------|---------|
| **IN1** | Inductive Loop Detector | Vehicle presence at gate entrance |
| **IN2** | Push Button | Ticket button (for non-member visitors) |
| **IN3** | Inductive Loop Detector | Vehicle has passed through gate (exit loop) |
| **IN4** | Push Button | Help/assistance button |

### Protocol-Specific Input States

| Event | Compass | ENET | Serial |
|-------|---------|------|--------|
| Vehicle present (IN1 ON) | `IN1ON` / `STAT1` | `IN1ON` / `INP11` | `*IN1ON#` |
| Vehicle left (IN1 OFF) | `IN1OFF` | `IN1OFF` / `IN10` | `*IN1OFF#` |
| Ticket button pressed | `IN2ON` / `STAT11` | `IN2ON` / `INP21` | `*IN2ON#` |
| Reset (IN3) | `IN3` | `IN3ON` / `IN31` | `*IN3#` |
| Help button pressed | `IN4ON` | `IN4ON` / `IN41` | `*IN4ON#` |
| Vehicle passed (IN3 OFF) | `IN3OFF` | `IN30` | `*IN3OFF#` |

---

## Card Reader Protocols

### RFID Reader (Wiegand Protocol)
- **Format**: `W<hex_card_number>`
- **Delimiters**:
  - Compass: `W` ... `\xa9`
  - ENET: `W1` ... `;`
  - Serial: `W` ... `#`
- **Card Number**: Hexadecimal converted to decimal

### UHF Reader (Long-Range RFID)
- **Format**: `X<hex_card_number>`
- **Delimiters**:
  - Compass: `X` ... `\xa9`
  - Serial: `X` ... `#`
- **Card Number**: Hexadecimal converted to decimal

### ENET RFID Specific
- ENET uses `W1` prefix instead of just `W`

---

## Audio/Announcement Commands

### Compass Protocol Audio (`\xa6MTxxxxx\xa9`)

| Command | Track | Indonesian Message | English Translation |
|---------|-------|-------------------|---------------------|
| `\xa6MT00002\xa9` | 2 | "Silakan ambil tiket" | Please take your ticket |
| `\xa6MT00003\xa9` | 3 | "Kartu tidak terdaftar" | Card not registered |
| `\xa6MT00005\xa9` | 5 | "Mohon tunggu" | Please wait |
| `\xa6MT00006\xa9` | 6 | "Terima kasih" | Thank you |
| `\xa6MT00007\xa9` | 7 | "Selamat datang" | Welcome |
| `\xa6MT00011\xa9` | 11 | "Masa berlaku habis dalam 5 hari" | Expires in 5 days |
| `\xa6MT00012\xa9` | 12 | "Masa berlaku habis dalam 1 hari" | Expires in 1 day |
| `\xa6MT00013\xa9` | 13 | "Kartu habis masa berlaku" | Card expired |
| `\xa6MT00014\xa9` | 14 | "Kartu belum selesai transaksi" | Transaction not closed |

### ENET Protocol Audio (`:PLAYTRACKx;`)

| Command | Track | Purpose |
|---------|-------|---------|
| `:PLAYTRACK2;` | 2 | Please take your ticket |
| `:PLAYTRACK3;` | 3 | Card not registered |
| `:PLAYTRACK5;` | 5 | Please wait |
| `:PLAYTRACK6;` | 6 | Thank you |
| `:PLAYTRACK7;` | 7 | Welcome |
| `:PLAYTRACK11;` | 11 | Expires in 5 days |
| `:PLAYTRACK12;` | 12 | Expires in 1 day |
| `:PLAYTRACK13;` | 13 | Card expired |
| `:PLAYTRACK14;` | 14 | Transaction not closed |

### Serial Protocol Audio (Local MP3 Files)

The `parking-serial.py` uses local MP3 files via `playsound` library:

| File | Purpose |
|------|---------|
| `./audio/silakan-tekan-tombol.mp3` | Please press button |
| `./audio/kartu-invalid.mp3` | Invalid card |
| `./audio/kartu-expired.mp3` | Card expired |
| `./audio/transaksi-belum-selesai.mp3` | Transaction not closed |
| `./audio/expired-dalam-5hari.mp3` | Expires in 5 days |
| `./audio/expired-dalam-1hari.mp3` | Expires in 1 day |
| `./audio/silakan-ambil-tiket.mp3` | Please take your ticket |
| `./audio/terimakasih.mp3` | Thank you |
| `./audio/mohon-tunggu.mp3` | Please wait |

---

## LED Display / Running Text Commands

### Compass Protocol

**Set Running Text:**
```
\xa6DSD913003<line1>|13003<line2>\xa9
```

**Reset Running Text:**
```
\xa6DSU\xa9
```

### ENET Protocol

**Set Running Text:**
```
\xa6D915050<line1>|15050<line2>\xa9
```

**Reset Running Text:**
```
\xa6U\xa9
```

### WebSocket (via `gate_out.py`)

The gate_out.py WebSocket server handles running text for exit gates via serial port:

**Set Running Text:**
```
\xa6D915050<line1>|15050<line2>\xa9
```

**Reset Running Text:**
```
\xa6U\xa9
```

---

## Gate Open Commands

| Protocol | Command | Notes |
|----------|---------|-------|
| Compass | `\xa6TRIG1\xa9` | Trigger pulse (used in parking.py, parking-bak.py) |
| Compass | `\xa6OPEN1\xa9` | Open gate (used in parking-blocking.py) |
| ENET | `:OPEN1;` | Open gate |
| Serial | `*TRIG1#` | Trigger pulse |

---

## Ticket Printer Commands

### ESC/POS via Serial/Controller (Compass)

Used by `parking.py` (prefix `\xa6PR3`) and `parking-bak.py` / `parking-blocking.py` (prefix `\xa6PR4`):

```
\xa6PR3                              # Start print command
\x1b\x61\x01TIKET PARKIR\n           # Center align, title
\x1b\x21\x10<Location Name>\n\n     # Double height text
\x1b\x21\x00                         # Normal height
\x1b\x61\x00                         # Left align
GATE         : <gate_name>/<type>\n  # Gate info
TANGGAL      : <date>\n              # Date
JAM          : <time>\n\n            # Time
\x1b\x61\x01                         # Center align
\x1dhd                               # Barcode height 100
\x1dH\x02                            # Barcode text below
\x1dkE                               # Barcode type CODE39
<length><barcode>\n                  # Barcode content
<additional_info>\n                  # Footer
\x1d\x56A                           # Full cut
\xa9                                 # End command
```

### Network Printer (python-escpos)

Used by `parking-enet.py` and `parking-blocking.py` for network printers:

```python
from escpos.printer import Network
p = Network(gate['printer_ip_address'])
p.set(align='center')
p.text("TIKET PARKIR\n")
p.set(height=2, align='center')
p.text(SETTING['location_name'] + "\n\n")
p.set(align='left')
p.text('GATE         : ' + gate['name'] + "/" + gate['vehicle_type'] + "\n")
p.text('TANGGAL      : ' + <date> + "\n")
p.text('JAM          : ' + <time> + "\n\n")
p.set(align='center')
p.barcode(data['barcode_number'], 'CODE39', function_type='A', height=100, width=4, pos='BELOW', align_ct=True)
p.text("\n")
p.text(SETTING['additional_info_ticket'])
p.cut()
```

---

## UHF Reader Commands

The UHF reader communicates using a custom CRC-based protocol.

### Read Commands

| Command | Hex | Purpose |
|---------|-----|---------|
| Read TID | `06 FF 01 00 06` | Read Tag ID |
| Read EPC | `04 FF 0F` | Read Electronic Product Code |

### CRC Calculation

```python
PRESET_Value = 0xFFFF
POLYNOMIAL = 0x8408

def crc(cmd):
    cmd = bytes.fromhex(cmd)
    uiCrcValue = PRESET_Value
    for x in range(len(cmd)):
        uiCrcValue = uiCrcValue ^ cmd[x]
        for y in range(8):
            if uiCrcValue & 0x0001:
                uiCrcValue = (uiCrcValue >> 1) ^ POLYNOMIAL
            else:
                uiCrcValue = uiCrcValue >> 1
    crc_H = (uiCrcValue >> 8) & 0xFF
    crc_L = uiCrcValue & 0xFF
    return cmd + bytes([crc_L]) + bytes([crc_H])
```

### EPC Data Format

Response hex string (minimum 40 chars):
- Card number = `int(data[28:34], 16)` (decimal conversion of hex bytes 28-34)

---

## Parking Method Flows

---

### Method 1: Primary Gate-In (`parking.py`)

**Daemon**: `parking.py` (systemd: `parking.service`)
**Protocol**: Compass (`\xa6...\xa9`)
**Connection**: TCP Socket to gate controller board

#### Initialization Flow
1. **Login** to Laravel API (`POST /api/login`) with controller credentials
2. **Get settings** (`GET /api/setting`)
3. **Get active gates** (`GET /api/gateIn?status=1`)
4. **Start thread** for each gate

#### Main Loop Flow per Gate

```
┌─────────────────────────────────────────────┐
│ 1. CONNECT TO CONTROLLER                    │
│    TCP socket to controller_ip:controller_port│
│    Timeout: 3 seconds                       │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 2. POLL VEHICLE STATUS                      │
│    Send: \xa6STAT\xa9                        │
│    Response: IN1ON/STAT1 = Vehicle detected  │
└──────────────┬──────────────────────────────┘
               │ Vehicle detected
┌──────────────▼──────────────────────────────┐
│ 3. PLAY WELCOME                             │
│    LED: "SELAMAT DATANG|TEKAN TOMBOL TIKET" │
│    Audio: \xa6MT00007\xa9 (Welcome)          │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 4. WAIT FOR INPUT                           │
│    Poll: \xa6STAT\xa9 every 1 second         │
└──────────────┬──────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┬──────────┐
    │          │          │          │          │
┌───▼───┐ ┌────▼────┐ ┌───▼───┐ ┌───▼───┐ ┌───▼────┐
│ RFID  │ │ Ticket  │ │ Reset │ │ Help  │ │ Turn   │
│ Card  │ │ Button  │ │ (IN3) │ │(IN4ON)│ │ Back   │
│(W/PT) │ │(IN2ON)  │ │       │ │       │ │(IN1OFF)│
└───┬───┘ └────┬────┘ └───┬───┘ └───┬───┘ └───┬────┘
    │          │          │         │          │
    ▼          ▼          ▼         ▼          ▼
 Check    Non-member   Reset   Play help   Reset
 Card      Ticket              + notify
 (API)     (API)
```

#### Member Card Flow (RFID/UHF)

| Step | Action | Command/API | Response Handling |
|------|--------|-------------|-------------------|
| 1 | Detect card | Poll `\xa6STAT\xa9`, look for `W`/`X`/`PT` | Parse hex card number |
| 2 | Validate card | `GET /api/member/search?nomor_kartu=<card>&status=1` | Check `expired`, `unclosed` |
| 3 | Card invalid | `\xa6MT00003\xa9` + LED "MAAF\|KARTU TIDAK TERDAFTAR" | Continue polling |
| 4 | Card expired | `\xa6MT00013\xa9` + LED "MAAF\|KARTU HABIS MASA BERLAKU" | Continue polling |
| 5 | Unclosed trx | `\xa6MT00014\xa9` + LED "MAAF\|KARTU BELUM SELESAI TRANSAKSI" | Continue polling |
| 6 | Expires in 5d | `\xa6MT00011\xa9` + LED warning, sleep 6s | Proceed |
| 7 | Expires in 1d | `\xa6MT00012\xa9` + LED warning, sleep 6s | Proceed |
| 8 | Save data | `POST /api/parkingTransaction/apiStore` | With `is_member=1` |
| 9 | Play thanks | `\xa6MT00006\xa9` + LED "TERIMAKASIH\|SIMPAN TIKET" | |
| 10 | Open gate | `\xa6TRIG1\xa9` | |
| 11 | Wait vehicle exit | Poll `\xa6STAT\xa9` for `IN3OFF` | Max 5 checks |
| 12 | Reset LED | `\xa6DSU\xa9` | |

#### Non-Member (Visitor) Flow

| Step | Action | Command/API | Response Handling |
|------|--------|-------------|-------------------|
| 1 | Detect button | Poll `\xa6STAT\xa9`, look for `IN2ON`/`STAT11` | |
| 2 | Save data | `POST /api/parkingTransaction/apiStore` | `is_member=0`, server generates barcode |
| 3 | Print ticket | Send ESC/POS via socket (`\xa6PR3...`) | Network or local printer |
| 4 | Play ticket msg | `\xa6MT00002\xa9` + LED "SELAMAT DATANG\|SILAKAN AMBIL TIKET" | |
| 5 | Play thanks | `\xa6MT00006\xa9` + LED "TERIMAKASIH\|SIMPAN DENGAN BAIK TIKET" | |
| 6 | Open gate | `\xa6TRIG1\xa9` | |
| 7 | Wait vehicle exit | Poll for `IN3OFF` | Max 5 checks |
| 8 | Reset LED | `\xa6DSU\xa9` | |

#### Help Button Flow

| Step | Action | Command/API | Response Handling |
|------|--------|-------------|-------------------|
| 1 | Detect button | Poll `\xa6STAT\xa9`, look for `IN4ON` | |
| 2 | Play wait msg | `\xa6MT00005\xa9` + LED "MOHON TUNGGU\|PETUGAS AKAN MEMBANTU ANDA" | Sleep 10s |
| 3 | Notify staff | `POST /api/gateIn/notification/<id>` | Alert message |
| 4 | Reset to main loop | | |

---

### Method 2: ENET Gate-In (`parking-enet.py`)

**Daemon**: `parking-enet.py`
**Protocol**: ENET (`:...;`)
**Connection**: TCP Socket to ENET controller board

#### Initialization Flow
1. **Get settings** (`GET /api/setting`)
2. **Get IN gates** (`GET /api/parkingGate/search?type=IN`)
3. **Start thread** for each gate

#### Main Loop Differences from `parking.py`

| Feature | Compass (`parking.py`) | ENET (`parking-enet.py`) |
|---------|----------------------|--------------------------|
| Poll command | `\xa6STAT\xa9` | `:INFO;` |
| Vehicle detect | `IN1ON` / `STAT1` | `IN1ON` / `INP11` |
| Welcome audio | `\xa6MT00007\xa9` | `:PLAYTRACK7;` |
| Invalid card | `\xa6MT00003\xa9` | `:PLAYTRACK3;` |
| Card expired | `\xa6MT00013\xa9` | `:PLAYTRACK13;` |
| Unclosed | `\xa6MT00014\xa9` | `:PLAYTRACK14;` |
| Expires 5d | `\xa6MT00011\xa9` | `:PLAYTRACK11;` |
| Expires 1d | `\xa6MT00012\xa9` | `:PLAYTRACK12;` |
| Take ticket | `\xa6MT00002\xa9` | `:PLAYTRACK2;` |
| Thanks | `\xa6MT00006\xa9` | `:PLAYTRACK6;` |
| Help | `\xa6MT00005\xa9` | `:PLAYTRACK5;` |
| Open gate | `\xa6TRIG1\xa9` | `:OPEN1;` |
| Vehicle passed | `IN3OFF` | `IN30` |
| Ticket button | `IN2ON` / `STAT11` | `IN2ON` / `INP21` |
| Reset | `IN3` | `IN3ON` / `IN31` |
| Help button | `IN4ON` | `IN4ON` / `IN41` |
| Turn back | `IN1OFF` | `IN1OFF` / `IN10` |
| RFID card | `W` | `W1` |
| Print prefix | `\xa6PR4` / `\xa6PR3` | `:PR4;` |

#### Printer Handling

ENET supports two printer types:
1. **Network Printer**: Uses `python-escpos` `Network` class via `gate['printer_ip_address']`
2. **Local/Serial Printer**: Sends ESC/POS commands through the controller socket with `:PR4;` prefix

#### Barcode Generation

```python
import random, string
generate_barcode_number() = ''.join([random.choice(string.ascii_uppercase + string.digits) for n in range(5)])
# Example: "A3B9K"
```

---

### Method 3: Serial Gate-In (`parking-serial.py`)

**Daemon**: `parking-serial.py`
**Protocol**: Serial (`*...#`)
**Connection**: Direct serial port (RS-232) via `pyserial`

#### Initialization Flow
1. **Login** to Laravel API (`POST /api/login`)
2. **Get active gates** (`GET /api/gateIn?status=1`)
3. **Open serial port** (`Serial(gate["controller_ip_address"], gate["controller_port"])`)
4. **Start thread** for each gate

#### Main Loop Flow

```
┌─────────────────────────────────────────────┐
│ 1. READ SERIAL UNTIL VEHICLE DETECTED       │
│    Read until: *IN1ON#                       │
│    Play audio: silakan-tekan-tombol.mp3     │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 2. READ NEXT INPUT                          │
│    Read until: #                             │
└──────────────┬──────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┬──────────┐
    │          │          │          │          │
┌───▼───┐ ┌────▼────┐ ┌───▼───┐ ┌───▼───┐ ┌───▼────┐
│ RFID  │ │ Ticket  │ │ Reset │ │ Help  │ │ Turn   │
│ Card  │ │ Button  │ │(IN3)  │ │(IN4ON)│ │ Back   │
│(W/X)  │ │(IN2ON)  │ │       │ │       │ │(IN1OFF)│
└───┬───┘ └────┬────┘ └───┬───┘ └───┬───┘ └───┬────┘
    │          │          │         │          │
    ▼          ▼          ▼         ▼          ▼
 Check    Non-member   Reset   Play help   Reset
 Card      Ticket              + notify
 (API)     (API)
```

#### Member Card Flow (Serial)

| Step | Action | Command/Audio | Notes |
|------|--------|---------------|-------|
| 1 | Detect card | Read serial, look for `W` or `X` | Parse hex to decimal |
| 2 | Validate card | `GET /api/member/search` | |
| 3 | Card invalid | Play `kartu-invalid.mp3` | Continue loop |
| 4 | Card expired | Play `kartu-expired.mp3` | Continue loop |
| 5 | Unclosed trx | Play `transaksi-belum-selesai.mp3` | Continue loop |
| 6 | Expires <=5d | Play `expired-dalam-5hari.mp3` | Continue |
| 7 | Expires 1d | Play `expired-dalam-1hari.mp3` | Continue |
| 8 | Save data | `POST /api/parkingTransaction/apiStore` | `is_member=1` |
| 9 | Play thanks | `terimakasih.mp3` | |
| 10 | Open gate | Write `*TRIG1#` to serial | |
| 11 | Wait vehicle exit | Read until `*IN3OFF#` | |

#### Non-Member Flow (Serial)

| Step | Action | Command/Audio | Notes |
|------|--------|---------------|-------|
| 1 | Detect button | Read serial, look for `IN2ON` | |
| 2 | Save data | `POST /api/parkingTransaction/apiStore` | `is_member=0` |
| 3 | Play take ticket | `silakan-ambil-tiket.mp3` | |
| 4 | Open gate | Write `*TRIG1#` to serial | |
| 5 | Wait vehicle exit | Read until `*IN3OFF#` | |

---

### Method 4: Blocking I/O Gate-In (`parking-blocking.py`)

**Daemon**: `parking-blocking.py`
**Protocol**: Compass (`\xa6...\xa9`)
**Connection**: TCP Socket with **blocking recv** (no polling)

#### Key Differences from `parking.py`

| Feature | `parking.py` | `parking-blocking.py` |
|---------|-------------|----------------------|
| Vehicle detection | Poll `\xa6STAT\xa9` | Send `\xa6STAT\xa9`, then block on `recv()` |
| Button/card detection | Poll `\xa6STAT\xa9` | Block on `recv()` (controller pushes data) |
| Vehicle exit | Poll `\xa6STAT\xa9` | Block on `recv()` for `IN3OFF` |
| Timeout | 3s socket timeout | `None` (infinite) after connection |
| Error handling | Exception-based | `BrokenPipeError` for dropped connections |
| Gate open | `\xa6TRIG1\xa9` | `\xa6OPEN1\xa9` |

#### Audio Mapping (Helper Function)

```python
cmd_list = {
    'take_ticket': b'\xa6MT00002\xa9',
    'invalid_card': b'\xa6MT00003\xa9',
    'help': b'\xa6MT00005\xa9',
    'thanks': b'\xa6MT00006\xa9',
    'welcome': b'\xa6MT00007\xa9'
}
```

---

### Method 5: Backup Gate-In (`parking-bak.py`)

**Daemon**: `parking-bak.py`
**Protocol**: Compass (`\xa6...\xa9`)
**Connection**: TCP Socket

This is essentially a backup copy of `parking.py` with minor differences:
- Uses `/api/gateIn/search` instead of `/api/gateIn?status=1`
- No `login()` function (uses unauthenticated API requests)
- Same command protocol as `parking.py`

---

### Method 6: Exit Gate Control (`gate_out.py`)

**Daemon**: `gate_out.py` (systemd: `gate-out.service`)
**Protocol**: WebSocket server (port `5678`)
**Connection**: Listens for WebSocket connections, controls serial devices

#### WebSocket API

The exit gate controller acts as a WebSocket server that accepts commands from the Laravel backend.

##### Command Format

Commands are sent as strings over WebSocket:

```
<command>;<param1>;<param2>;...
```

##### 1. Open Gate Command

**Format:**
```
open;<serial_device>;<baudrate>;<open_command>;<close_command>
```

**Example:**
```
open;/dev/ttyUSB0;9600;*TRIG1#;*CLOSE1#
```

**Flow:**
1. Parse command string by `;` delimiter
2. Open serial port: `Serial(cfg[1], int(cfg[2]), timeout=1)`
3. Write open command: `ser.write(cfg[3].encode())`
4. If close command exists (not empty): `time.sleep(1)` then `ser.write(cfg[4].encode())`
5. Close serial port
6. Respond: `{"status": True, "message": "Gate berhasil dibuka"}`

##### 2. Running Text Command

**Format:**
```
rt;<serial_device>;<baudrate>;<line1>|<line2>
```

**Example:**
```
rt;/dev/ttyUSB0;9600;TERIMAKASIH|SIMPAN TIKET ANDA
```

**Flow:**
1. Open serial port
2. Split text by `|` into two lines
3. Write: `\xa6D915050<line1>|15050<line2>\xa9`
4. Close serial port
5. Respond: `{"status": True, "message": "Berhasil menampilkan display"}`

##### 3. Reset Running Text Command

**Format:**
```
rrt;<serial_device>;<baudrate>
```

**Example:**
```
rrt;/dev/ttyUSB0;9600
```

**Flow:**
1. Open serial port
2. Write: `\xa6U\xa9`
3. Close serial port
4. Respond: `{"status": True, "message": "Berhasil menampilkan display"}`

#### Error Responses

All commands return JSON:

```json
{"status": false, "message": "Error description"}
```

Common errors:
- Serial port not found
- Failed to write to serial device
- Unknown command

---

### Method 7: UHF Reader Exit (`uhf-reader.py`)

**Daemon**: `uhf-reader.py` (systemd: `uhf-reader.service`)
**Protocol**: Custom CRC TCP to UHF reader, WebSocket to gate_out.py
**Connection**: TCP to UHF reader, WebSocket to gate_out server

#### Initialization Flow
1. **Login** to Laravel API (`POST /api/login`)
2. **Get UHF readers** (`GET /api/uhfReaders`)
3. **Start async loop** for each reader

#### Main Loop Flow

```
┌─────────────────────────────────────────────┐
│ 1. CONNECT TO UHF READER                    │
│    TCP to uhf_reader_host:uhf_reader_port   │
│    Default port typically 4001 or similar   │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 2. SEND EPC READ COMMAND                    │
│    Command: crc("04FF0F")                    │
│    CRC: Preset=0xFFFF, Poly=0x8408          │
│    Sent every 0.5 seconds                   │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 3. PARSE RESPONSE                           │
│    Read 64 bytes, convert to hex            │
│    Skip if length < 40 chars                │
│    Card number = int(data[28:34], 16)       │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 4. DEBOUNCE CHECK                           │
│    Skip if same as last read (on_queue)     │
│    Reset on_queue after 3s cooldown         │
└──────────────┬──────────────────────────────┘
               │ New card detected
┌──────────────▼──────────────────────────────┐
│ 5. VALIDATE CARD                            │
│    API: GET /api/parkingTransaction/search  │
│    Params: nomor_barcode=<card_number>      │
└──────────────┬──────────────────────────────┘
               │
    ┌──────────┴──────────┐
    │ Not found           │ Found
    ▼                     ▼
  Skip                Check member.expired
                      Skip if expired
└──────────────┬──────────────────────────────┘
               │ Valid transaction
┌──────────────▼──────────────────────────────┐
│ 6. PREPARE EXIT DATA                        │
│    time_out = datetime.now()                │
│    gate_out_id = gate.id                    │
│    jenis_kendaraan = gate.jenis_kendaraan   │
│    plat_nomor = member.vehicles[0]          │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 7. OPEN GATE (via WebSocket)                │
│    Connect to ws://<pos_ip>:5678            │
│    Send: open;device;baudrate;open;close    │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 8. SAVE DATA                                │
│    API: PUT /api/parkingTransaction/<id>    │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 9. TAKE SNAPSHOT                            │
│    API: POST /api/takeSnapshot/<id>         │
│    Params: gate_out_id                      │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 10. COOLDOWN                                │
│     Sleep 3 seconds                         │
│     Reset on_queue = ""                     │
└─────────────────────────────────────────────┘
```

#### WebSocket Gate Open Message Format

```python
message = f'open;{gate["device"]};{gate["baudrate"]};{gate["open_command"]};{gate["close_command"]}'
# Example: "open;/dev/ttyUSB0;9600;*TRIG1#;"
uri = f'ws://{gate["pos"]["ip_address"]}:5678'
```

---

## API Endpoints Used by Hardware Daemons

### Authentication

| Method | Endpoint | Daemon | Purpose |
|--------|----------|--------|---------|
| POST | `/api/login` | parking.py, parking-serial.py, uhf-reader.py | Authenticate controller device |

### Settings & Configuration

| Method | Endpoint | Daemon | Purpose |
|--------|----------|--------|---------|
| GET | `/api/setting` | parking.py, parking-enet.py, parking-bak.py, parking-blocking.py | Get location name, ticket info |
| GET | `/api/gateIn?status=1` | parking.py, parking-serial.py | Get active entry gates |
| GET | `/api/gateIn/search` | parking-bak.py | Get all entry gates |
| GET | `/api/parkingGate/search?type=IN` | parking-enet.py, parking-blocking.py | Get IN gates |
| GET | `/api/uhfReaders` | uhf-reader.py | Get UHF reader configurations |

### Member Validation

| Method | Endpoint | Daemon | Purpose |
|--------|----------|--------|---------|
| GET | `/api/member/search?nomor_kartu=<card>&status=1&card_type=<type>` | parking.py, parking-serial.py | Validate RFID/UHF card |
| GET | `/api/parkingMember/search?card_number=<card>&active=1` | parking-enet.py, parking-bak.py, parking-blocking.py | Validate member card |

### Transaction Management

| Method | Endpoint | Daemon | Purpose |
|--------|----------|--------|---------|
| POST | `/api/parkingTransaction/apiStore` | parking.py, parking-serial.py | Create parking transaction |
| POST | `/api/parkingTransaction` | parking-enet.py, parking-bak.py, parking-blocking.py | Create parking transaction |
| GET | `/api/parkingTransaction/search?nomor_barcode=<card>` | uhf-reader.py | Find transaction by card |
| PUT | `/api/parkingTransaction/<id>` | uhf-reader.py | Update exit data |

### Notifications & Snapshots

| Method | Endpoint | Daemon | Purpose |
|--------|----------|--------|---------|
| POST | `/api/gateIn/notification/<id>` | parking.py, parking-serial.py | Send notification |
| POST | `/api/notification` | parking-enet.py, parking-bak.py, parking-blocking.py | Send notification |
| GET | `/api/gateIn/takeSnapshot/<id>` | parking-bak.py | Take camera snapshot |
| GET | `/api/parkingGate/takeSnapshot/<id>` | parking-enet.py, parking-blocking.py | Take camera snapshot |
| POST | `/api/takeSnapshot/<id>` | uhf-reader.py | Take exit snapshot |

---

## Hardware Configuration Parameters

### GateIn / GateOut Configuration (from API)

```json
{
  "id": 1,
  "nama": "GATE-IN-MOTOR",
  "name": "GATE-IN-MOTOR",
  "controller_ip_address": "192.168.1.100",
  "controller_port": 5000,
  "jenis_kendaraan": "MOTOR",
  "vehicle_type": "MOTOR",
  "printer": {
    "type": "local",
    "ip_address": "192.168.1.101"
  },
  "printer_ip_address": "192.168.1.101",
  "printer_type": "local",
  "camera_status": 1
}
```

### GateOut Configuration (for UHF)

```json
{
  "id": 1,
  "nama": "GATE-OUT-MOTOR",
  "device": "/dev/ttyUSB0",
  "baudrate": 9600,
  "open_command": "*TRIG1#",
  "close_command": "",
  "uhf_reader_host": "192.168.1.200",
  "uhf_reader_port": 4001,
  "pos": {
    "ip_address": "192.168.1.50"
  }
}
```

---

## Testing & Diagnostics

### Controller Test Tool (`controller_test.py`)

Interactive CLI for testing controller boards:

```bash
# Test ENET controller
python controller_test.py enet 192.168.1.100

# Test Compass controller
python controller_test.py compass 192.168.1.100
```

**Available commands:**
- `STAT` / `INFO` - Read input status
- `TRIG1` / `OPEN1` - Open gate
- `MT00007` / `PLAYTRACK7` - Play welcome
- `quit` / `exit` - Exit tool

### Printer Test Tool (`test_print.py`)

Tests thermal printer via TCP socket:
- Connects to printer at `192.168.1.101:5000`
- Sends sample ticket with barcode

---

## Log Files

| Daemon | Log File | Rotation |
|--------|----------|----------|
| parking.py | `/var/log/parking.log` | Append |
| parking-enet.py | `/var/log/parking.log` | Append |
| parking-serial.py | `/var/log/parking.log` | Append |
| parking-blocking.py | `parking.log` (local) | Append |
| parking-bak.py | `/var/log/parking.log` | Append |
| uhf-reader.py | `/var/log/uhf.log` | Append |

---

## Error Handling & Recovery

### Connection Recovery

All TCP-based daemons implement automatic reconnection:
1. **Connection failed**: Sleep 3 seconds, retry loop
2. **Communication error**: Break inner loop, reconnect socket
3. **Broken pipe**: Log error, sleep 3 seconds, continue outer loop

### API Failure Recovery

- **Login failed**: Exit application (critical)
- **No gates configured**: Exit application (critical)
- **API timeout**: Log error, send notification to staff
- **Save data failed**: Send notification to staff, visitor needs assistance

### Notification System

When hardware errors occur, daemons send notifications via:
- Laravel API notification endpoints
- Real-time WebSocket broadcasts (Laravel Reverb)
- Dashboard alerts for operators

---

## Summary of Commands Reference

### Compass Protocol Commands

| Command | Purpose |
|---------|---------|
| `\xa6STAT\xa9` | Read controller input status |
| `\xa6TRIG1\xa9` | Open gate (trigger pulse) |
| `\xa6OPEN1\xa9` | Open gate (continuous) |
| `\xa6MT00002\xa9` | Play "Please take ticket" |
| `\xa6MT00003\xa9` | Play "Card invalid" |
| `\xa6MT00005\xa9` | Play "Please wait" |
| `\xa6MT00006\xa9` | Play "Thank you" |
| `\xa6MT00007\xa9` | Play "Welcome" |
| `\xa6MT00011\xa9` | Play "Expires in 5 days" |
| `\xa6MT00012\xa9` | Play "Expires in 1 day" |
| `\xa6MT00013\xa9` | Play "Card expired" |
| `\xa6MT00014\xa9` | Play "Transaction unclosed" |
| `\xa6DSD913003<l1>\|13003<l2>\xa9` | Set running text (2 lines) |
| `\xa6DSU\xa9` | Reset/clear running text |
| `\xa6PR3...\xa9` | Print ticket (baudrate 9600) |
| `\xa6PR4...\xa9` | Print ticket (baudrate 19200) |

### ENET Protocol Commands

| Command | Purpose |
|---------|---------|
| `:INFO;` | Read controller input status |
| `:OPEN1;` | Open gate |
| `:PLAYTRACK2;` | Play "Please take ticket" |
| `:PLAYTRACK3;` | Play "Card invalid" |
| `:PLAYTRACK5;` | Play "Please wait" |
| `:PLAYTRACK6;` | Play "Thank you" |
| `:PLAYTRACK7;` | Play "Welcome" |
| `:PLAYTRACK11;` | Play "Expires in 5 days" |
| `:PLAYTRACK12;` | Play "Expires in 1 day" |
| `:PLAYTRACK13;` | Play "Card expired" |
| `:PLAYTRACK14;` | Play "Transaction unclosed" |
| `:PR4...;` | Print ticket |

### Serial Protocol Commands

| Command | Purpose |
|---------|---------|
| `*TRIG1#` | Open gate |
| `*IN1ON#` | Vehicle detected (read) |
| `*IN3OFF#` | Vehicle passed (read) |

### WebSocket Commands (gate_out.py)

| Command | Format | Purpose |
|---------|--------|---------|
| `open` | `open;device;baudrate;open_cmd;close_cmd` | Open exit gate |
| `rt` | `rt;device;baudrate;line1\|line2` | Set running text |
| `rrt` | `rrt;device;baudrate` | Reset running text |

---

*Document generated for E-Parking System v2. Last updated: 2025-04-25*
