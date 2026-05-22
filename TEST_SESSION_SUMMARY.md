# Test Session Summary — E-Parking v2 Local Testing

## Infrastructure

```bash
# Database + Redis
docker compose up -d        # parking-postgres, parking-redis, parking-pgbouncer, parking-api

# Schema
alembic upgrade head        # from project root, NOT api/

# Seed admin + operator + gates
python scripts/seed.py
```

Seed creds:
- `admin` / `admin123`     → dashboard + member CRUD
- `operator` / `operator123` → POS page

Seed emails use `@eparking.com` (RFC-safe; `.local` rejected by Pydantic EmailStr).

## Services (separate terminals)

```bash
source .venv/bin/activate

# Terminal 1 — API
uvicorn api.app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Critical worker (print/snapshot jobs)
arq workers.settings.CriticalWorkerSettings

# Terminal 3 — Background worker (settlement/cleanup)
arq workers.settings.BackgroundWorkerSettings

# Terminal 4 — Frontend
cd frontend && npm run dev

# Terminal 5 — Gate IN daemon
python -m daemons.cli --gate-id GIN-01

# Terminal 6 — Booth bridge (Gate OUT + Omnikey RFID poller)
python -m booth_bridge.main --config /tmp/booth_gout01.json --port 5678
```

## Booth Bridge Config

```bash
cat > /tmp/booth_gout01.json << 'EOF'
{
  "name": "GOUT-01 Booth",
  "api_base_url": "http://localhost:8000",
  "api_key": "change-me-in-production",
  "default_gate_code": "GOUT-01",
  "peripherals": {}
}
EOF
```

## Gate Hardware Config (per-gate, in DB)

`gates.hardware_config` JSONB controls peripherals + relay commands. Required fields for GOUT-01:

```bash
docker exec parking-postgres psql -U parking -d parking -c "
UPDATE gates SET hardware_config = hardware_config || '{
  \"omnikey_reader\": {\"enabled\": true},
  \"open_command\": \"*TRIG1#\",
  \"close_command\": \"\",
  \"close_delay_seconds\": 0
}'::jsonb WHERE code='GOUT-01';"
```

- `open_command` ASCII or hex string written to controller_device (serial)
- `omnikey_reader.enabled` toggles booth_bridge's OmnikeyPoller
- Schema: `api/app/schemas/gate.py:HardwareConfig`

## IN1 Simulation (dev only — replace with physical button/sensor for real testing)

```bash
alias in1on='redis-cli XADD parking.commands.GIN-01 "*" command_type inject_rss signal IN1ON'
alias in1off='redis-cli XADD parking.commands.GIN-01 "*" command_type inject_rss signal IN1OFF'
alias in2on='redis-cli XADD parking.commands.GIN-01 "*" command_type inject_rss signal IN2ON'
```

Daemon's `inject_rss` synthesizes an RSS frame and dispatches it through the normal handler. Log line `mock_inject_rss` flags it as sim (NOT mock-mode fallback — daemon is still TCP-connected to real Compass controller).

**Real hardware:**
- Wire physical button to controller IN1 input → controller pushes `IN1ON`/`IN1OFF` on press/release
- Wire button to IN2 for ticket button, or keep injecting IN2 via redis until physical wire ready
- All entry methods (IN2, RFID Wiegand, PASSTI e-money) gated by `_in1_on=True`

## Omnikey 5427 CK Setup (POS-side RFID reader)

### One-time

1. **Switch reader to HID Keyboard mode** (factory default may be CCID admin mode 0x5428 — doesn't read cards):
   - On Windows: HID OMNIKEY Workbench → set Operating Mode → CCID + Keyboard (or Keyboard only)
   - Verify on Linux: `lsusb | grep -i omnikey` should show `076b:5427` (keyboard) NOT `076b:5428` (admin)

2. **Install evdev access**:
   ```bash
   pip install evdev
   # Persistent udev rule (gives qiu rw on the Omnikey event node, survives replug):
   echo 'KERNEL=="event*", SUBSYSTEM=="input", ATTRS{idVendor}=="076b", ATTRS{idProduct}=="5427", MODE="0660", OWNER="qiu", GROUP="input"' | sudo tee /etc/udev/rules.d/99-omnikey.rules
   sudo udevadm control --reload-rules
   ```
   Use product ID matching your reader's actual mode (5427 keyboard, 5428 admin).

3. **Replug reader** → `ls -l /dev/input/event<N>` shows owner `qiu`.

### How the poller reads

`booth_bridge/omnikey_poller.py` grabs the keyboard event node exclusively, buffers digit keystrokes, flushes on Enter OR after 200ms idle (some Omnikey firmwares omit trailing Enter). Calls `/api/payments/rfid/booth` → on success, opens local relay via `GateOpener`.

## Test Flows

### Gate IN — Cash entry

1. Sim or real IN1 → daemon `IDLE → WAITING_INPUT`, plays welcome audio
2. Sim IN2 (or press physical IN2 button) → ticket prints, gate opens
3. Sim IN1OFF (or release IN1) → daemon `OPENING → IDLE`

### Gate OUT — Cash exit (POS operator)

1. POS at `localhost:3000/pos` (operator login)
2. Type barcode in input → Enter → tx loads, `paymentState = WAITING_PAYMENT`
3. Click TUNAI (F1) → calculator → confirm → toast "Tekan Space untuk buka palang"
4. Press Space → boothWs sends `open_gate` → booth_bridge writes `*TRIG1#` to `/dev/ttyUSB0` → relay click
5. `clearTransaction()` resets POS to IDLE

### Gate OUT — RFID member (Omnikey auto)

1. Tap member card on Omnikey
2. Poller reads UID → POST `/api/payments/rfid/booth` → API closes tx
3. `gate_opener.open()` → relay click (auto, no operator action)
4. POS WS receives `member_card_scanned` → toast + sound

## Bugs Fixed This Session

### Auth / Permissions
- Operator was hitting `require_admin` on `/api/gates`, `/api/settings`, `/api/vehicle-types`, `/api/pos/shift-summary` (all 403). Relaxed to `require_auth` for read endpoints.
- `/api/pos/shift-summary` route didn't exist — added; returns current shift + today's CASH totals.
- Seed emails `admin@eparking.local` rejected by Pydantic `EmailStr` (RFC-reserved TLD). Renamed to `.com`. Also need DB migration of existing rows.

### POS UI
- `<Toaster>` unresolved — added explicit `import { Toaster } from 'vue-sonner'` in `app.vue`.
- `<QuickActionBar>`, `<CashDialog>`, `<RfidDialog>` unresolved — renamed usage in `pos.vue` to `<PosQuickActionBar>` etc. (Nuxt path-prefix auto-import).
- `PosUnifiedView.vue` focusBarcode: `input?.focus is not a function` → guarded for HTMLElement.
- WS status indicator stuck "Offline" — `$ws.isConnected()` polled while socket still CONNECTING; now updates on `ws_open`/`ws_close` events.
- Layout overlap (Total Parkir colliding with barcode input) — compact photos h-28, price text-5xl, PaymentButton h-14, `min-h-0` chain.
- Payment buttons disabled after barcode lookup — `lookupTransaction` now sets `paymentState='WAITING_PAYMENT'`.
- Edit member POST'd instead of PATCH'd — `CrudModal` was stripping `id` from formData; now preserves `initialData.id`.
- Cash payment "Buka Palang" via booth path never cleared transaction — added `gateStore.clearTransaction()` after booth send.

### Hardware Integration
- `HardwareConfig` Pydantic schema dropped unknown JSONB keys → `open_command`, `omnikey_reader` invisible to API consumers. Added fields.
- GateOpener empty `open_command` → no relay write. Set per-gate (legacy used `*TRIG1#`).
- Omnikey keyboard mode omits Enter terminator → buffer never flushed. Added 200ms idle flush.
- Compass controller LED pulsed rapidly (saw no PC traffic) despite TCP `ESTAB`. Added:
  - `SO_KEEPALIVE` + `TCP_KEEPIDLE=10/INTVL=5/CNT=3` on `CompassTransport.connect`
  - `_controller_heartbeat` task in `gate_in.py` sends `STAT` every 5s

## Known Issues / Not Done

- Gate IN RFID/e-money: requires physical Wiegand + PASSTI reader at entry (no inject command for RFID currently)
- Settlement / shift-close UI flows untested
- Manless gate OUT (no daemon at exit) untested
- Camera snapshot + thermal printer require real hardware
- Hardcoded RFC-edge cases in user emails: keep usernames distinct from emails

## DB Quick Checks

```bash
# Gates + online status
docker exec parking-postgres psql -U parking -d parking -c "SELECT code, direction, is_active, is_online, hardware_config->>'open_command' AS open_cmd FROM gates;"

# Active tx
docker exec parking-postgres psql -U parking -d parking -c "SELECT barcode, plate_number, card_number, status, entry_time FROM parking_transactions WHERE status='ACTIVE' ORDER BY entry_time DESC LIMIT 10;"

# Members + expiry
docker exec parking-postgres psql -U parking -d parking -c "SELECT id, card_number, name, is_active, valid_until FROM members ORDER BY id;"

# Close orphan ACTIVE tx by card
docker exec parking-postgres psql -U parking -d parking -c "UPDATE parking_transactions SET status='CANCELLED', exit_time=NOW() WHERE card_number='<N>' AND status='ACTIVE';"
```

## Booth Bridge Log

```bash
tail -f /tmp/booth_bridge.log
```

Healthy startup shows: `ws_server_started`, `rfid_poller_started`, `omnikey_device_opened`. Tap = `omnikey_card_read card=...`. Relay write = `gate_opened gate_id=GOUT-01 device=/dev/ttyUSB0`.
