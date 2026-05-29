# Setup Wizard & Dashboard UX Redesign

> **Date:** 2026-05-14 · **Updated:** 2026-05-28
> **Status:** Implemented (P1–P3). P4 dashboard redesign deferred.
> **Goal:** Field technician installs E-Parking v2 in under 30 minutes with zero terminal use after `sudo ./setup.sh` completes.

---

## 0. As-Built Notes (2026-05-28)

The wizard shipped. The design below is preserved as the original intent; these
points record where the implementation diverged:

1. **Wizard is 6 steps, not 8.** Order: `welcome → admin → config → topology →
   gates → finalize` (`frontend/pages/setup.vue`). Site Info + Tariffs + Areas
   were merged into a single **config** step. Go-Live = **finalize**.
2. **No Booth-PC step.** Booth devices (e-money reader, receipt printer, scanner)
   are configured in `booth.json` on the booth PC by its own installer, not in
   the wizard. Booths join the server via the **enrollment token** flow
   (`POST /api/setup/enroll`), not a wizard screen.
3. **Per-gate peripherals trimmed to `rfid` + `camera`.** The design's
   printer/emoney/uhf rows were set-but-never-read, so they were dropped. rfid is
   read by `gate_in`; camera by the Gate model.
4. **Two install tokens, not one.** Besides the one-time `setup-token`, the
   server installer mints a reusable (24h) `enroll-token` so every booth brought
   online can fetch `INTERNAL_API_KEY` + Redis address without hand-copying.
5. **Gate codes** are `GIN-NN` / `GOUT-NN` (e.g. `GIN-01`), not the
   `GATE-IN-01` / `GATE-OUT-01` shown in mockups.
6. **Extra endpoints** beyond the Section 6 table: `POST /api/setup/enroll`,
   `POST /api/setup/logout`, `GET /api/setup/session`, `POST /api/setup/test-gate`
   (end-to-end open/close ACK test).

---

## 1. Problem

Current setup pain points:

1. Two settings pages (`frontend/pages/setting.vue` + `frontend/pages/device.vue`) overlap concepts. No unified flow.
2. Installer = shell scripts (`installer/{server,booth_pc,booth_with_server}/setup.sh`) — interactive `read -rp` prompts for IP, ports, baudrates, device paths.
3. Serial detection lives in `scripts/detect-serial-devices.sh` (CLI only, not in UI).
4. No first-run wizard. No connectivity-test buttons. No device probe in dashboard.
5. "Umum" settings tab = raw key-value table — poor UX for field tech.
6. After install, technician manually runs `enable-gate-daemons.sh` — no UI trigger.
7. Hardware status not surfaced (gate online/offline, printer paper, reader heartbeat).

## 2. Goals

- Walk-in tech, 30 min from install to first car through gate.
- Zero terminal use after `sudo ./setup.sh` completes.
- No "type /dev/ttyUSB0" anywhere — pick from list or auto-detect with confirmation.
- Every config save has a "Test before commit" button.
- Resume mid-setup safely (browser crash, lunch break OK).
- Target: field technician, non-developer.

## 3. Non-Goals

- Replace shell installer. Shell still handles: package install, DB create, systemd unit drop, nginx config, sudoers drop.
- Multi-tenant SaaS. One install = one site.
- Mobile UI. Tech operates on laptop / booth PC.

---

## 4. Install Flow (Hybrid)

```
[1] Tech runs: sudo ./installer/setup.sh   (dispatcher → _roles/<role>/setup.sh)
    Server role does: deps + DB + Redis + nginx + systemd units (started) +
                sudoers drop + setup-token + enroll-token generation
    Shell ends with: "Open http://<ip>/setup?token=<X> to finish configuration"
    Auto-launches browser at /setup?token=<X> if DISPLAY/WAYLAND_DISPLAY set.
    Runs scripts/parking_doctor.py as a final diagnostic.

[2] Browser → /setup
    Wizard redeems token, runs, writes config to DB via API.

[3] Wizard finalize step: "Aktifkan Gate & Selesai" → API calls
    enable-gate-daemons.sh --run --json [--include-local-serial] via sudoers.

[4] Wizard sets setup_complete=true, deletes session + token + cookie,
    redirects to /. /setup remains reachable via /setup?force=1 for admins
    (no auto-redirect).
```

DB additions: row in `settings` table — `key=setup_complete, value=false`. Middleware: if `setup_complete=false` and route is not `/setup` or `/api/setup/*`, redirect to `/setup`.

---

## 5. Wizard — Steps

> **As-built:** shipped as 6 steps (`welcome, admin, config, topology, gates,
> finalize`). The 8-step breakdown below is the original design — Site/Tariff/
> Areas were merged into one **config** step and the Booth-PC step was dropped
> (see Section 0). Step bodies remain accurate per-screen.

### Step 0 — Token redeem + Welcome

```
┌─────────────────────────────────────────────────┐
│  E-Parking Setup                          1 / 8 │
├─────────────────────────────────────────────────┤
│                                                 │
│     Welcome. Let's get your parking lot         │
│     running. Takes about 20 minutes.            │
│                                                 │
│     What you'll need:                           │
│     • Controller IP address                     │
│     • Booth PC reachable on network             │
│     • Hardware powered on and connected         │
│                                                 │
│     [ Run Preflight Check ]   [ Start → ]       │
└─────────────────────────────────────────────────┘
```

Token verification happens automatically when wizard loads with `?token=<X>` query param. `POST /api/setup/redeem-token` returns a setup-scoped session cookie. Preflight calls `GET /api/setup/preflight` which runs the existing `scripts/preflight_check.py` logic and returns JSON. UI shows green / yellow / red rows. "Start" button is disabled if any FAIL exists.

### Step 0a — Create Admin Account

```
┌─────────────────────────────────────────────────┐
│  Create Admin Account                     2 / 8 │
├─────────────────────────────────────────────────┤
│  Full Name:    [ Pak Budi                     ] │
│  Email:        [ admin@parkir.com             ] │
│  Password:     [ ••••••••••••                 ] │
│  Confirm:      [ ••••••••••••                 ] │
│                                                 │
│  Min 12 chars, 1 number, 1 symbol               │
│                                                 │
│  [ ← Back ]                    [ Save & Next → ]│
└─────────────────────────────────────────────────┘
```

Saves first admin via `POST /api/setup/create-admin` (separate from `/api/users` to allow no-auth path). Subsequent steps use issued JWT.

### Step 1 — Site Info

Fields: name, address, city, phone, email, NPWP. Live receipt preview on right side. Saves to `site_config` table (existing model in `api/app/models/site_config.py`).

### Step 2 — Topology Detection + Picker

```
┌─────────────────────────────────────────────────┐
│  System Topology                          4 / 8 │
├─────────────────────────────────────────────────┤
│                                                 │
│  Detected: Server + Local Booth (combo PC) ✓    │
│  This machine runs the API and serves Booth 1   │
│  directly.                                      │
│                                                 │
│  [ Looks right, continue ]   [ Override ]       │
│                                                 │
│  ─────────────────────────────────────────────  │
│                                                 │
│  How many gates?                                │
│                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────┐│
│  │  1 + 1  │  │  2 + 2  │  │  1 + 2  │  │  ⚙  ││
│  │ ░░░ IN  │  │ ░░ IN×2 │  │ ░░ IN×1 │  │Cus- ││
│  │ ░░░ OUT │  │ ░░ OUT×2│  │ ░ OUT×2 │  │tom  ││
│  └─────────┘  └─────────┘  └─────────┘  └─────┘│
│                                                 │
│  Pick one. You can add more gates later.        │
└─────────────────────────────────────────────────┘
```

Auto-detection logic in `GET /api/setup/state`:

```python
def detect_topology() -> Literal["combo", "server_only", "booth_only", "unknown"]:
    is_server = is_systemd_unit_active("parking-api")
    has_booth_bridge = is_systemd_unit_active("booth-bridge")
    has_local_serial = any(glob("/dev/parking-*"))

    if is_server and has_booth_bridge and has_local_serial:
        return "combo"
    if is_server and not has_local_serial:
        return "server_only"
    if not is_server and has_booth_bridge:
        return "booth_only"
    return "unknown"
```

Combo flag impacts Step 7 — passes `--include-local-serial` to `enable-gate-daemons.sh`. Preset creates `Gate` rows in DB with default names (`GATE-IN-01`, `GATE-OUT-01`, etc.). Tech edits in next step.

### Step 3 — Per-Gate Hardware

Loop over each gate created in step 2.

```
┌─────────────────────────────────────────────────┐
│  Configure Gate: GATE-OUT-01              5 / 8 │
├─────────────────────────────────────────────────┤
│  Name:     [Exit Gate Lobby     ]               │
│  Code:     [GOUT01              ]               │
│                                                 │
│  Controller                                     │
│  ○ Network (Compass/ENET)                       │
│  ● Serial (RS-232 / USB)                        │
│                                                 │
│  Device:   [  /dev/parking-gate ▼ ]  🔍 Detect  │
│  Baudrate: [ 9600  ▼ ]                          │
│            [ Test Connection ]  ✓ OK 142ms      │
│                                                 │
│  Peripherals                                    │
│  ☑ Receipt Printer    🔍 Detect  → Configure ↓ │
│  ☑ E-Money Reader     🔍 Detect  → Configure ↓ │
│  ☐ RFID Member Reader                           │
│  ☐ Camera                                       │
│  ☐ UHF Reader                                   │
│                                                 │
│  [ ← Back ]                    [ Save & Next → ]│
└─────────────────────────────────────────────────┘
```

**Detect button** flow:

1. Calls `POST /api/setup/detect-serial` which runs `scripts/detect-serial-devices.sh --json`. Response:

```json
{
  "candidates": [
    {
      "port": "/dev/ttyUSB0",
      "vid_pid": "0403:6001",
      "chip": "FTDI FT232R",
      "suggested_role": "emoney",
      "confidence": "high"
    },
    {
      "port": "/dev/ttyUSB1",
      "vid_pid": "067b:2303",
      "chip": "Prolific PL2303",
      "suggested_role": "printer",
      "confidence": "high"
    }
  ]
}
```

2. UI shows toast/modal: "Found PASSTI reader on /dev/ttyUSB0. Use it for E-Money?" with [ Yes ] [ Pick another ] [ Skip ].
3. On Yes, UI also calls `POST /api/setup/write-udev` to create the `/dev/parking-emoney` symlink. From this point the wizard uses the stable symlink path, never `/dev/ttyUSB0`.

**Test Connection button** — `POST /api/setup/test-device`:

```
Request:  {"type": "serial", "device": "/dev/parking-gate", "baudrate": 9600}
       OR {"type": "tcp", "host": "192.168.1.100", "port": 5000}

Response: {"ok": true, "latency_ms": 142, "detail": "Port opened, no data"}
       OR {"ok": false, "error": "Permission denied"}
```

Peripheral sub-panels expand inline (no modals). Each peripheral row has its own Test button.

### Step 4 — Booth PCs

Only shown if any IN/OUT gate has an attended booth.

```
┌─────────────────────────────────────────────────┐
│  Booth Stations                           6 / 8 │
├─────────────────────────────────────────────────┤
│  Which PC runs the operator screen?             │
│                                                 │
│  ┌─ Booth 1 ──────────────────────────────────┐│
│  │ Name:   [Booth Utama        ]              ││
│  │ IP:     [192.168.1.50       ] ✓ Reachable  ││
│  │ Gate:   [ GATE-OUT-01 ▼     ]              ││
│  │ ☑ This booth uses local printer/emoney      ││
│  └─────────────────────────────────────────────┘│
│  [ + Add Booth ]                                │
└─────────────────────────────────────────────────┘
```

IP field auto-pings on blur via `POST /api/setup/test-device` with `type=ping`. Live "✓ Reachable" or "✗ No response".

### Step 5 — Vehicle Types + Tariffs

Preset templates as cards. Tech clicks one, then edits prices inline.

```
┌─ Preset: Indonesian Mall ──────────────────────┐
│ • Motor    Rp 2.000 first hour, Rp 1.000/h     │
│ • Mobil    Rp 5.000 first hour, Rp 2.000/h     │
│ • Truk     Rp 10.000 first hour, Rp 3.000/h    │
│ [ Use Preset ]   [ Build From Scratch ]        │
└────────────────────────────────────────────────┘

┌─ Preset: Office Building ──────────────────────┐
│ • Motor    Rp 3.000 flat                       │
│ • Mobil    Rp 5.000 first 2h, Rp 3.000/h       │
│ [ Use Preset ]                                  │
└────────────────────────────────────────────────┘
```

After preset selection, inline table editor for tariff / cap / overnight / progressive flag. Presets defined in `frontend/composables/useTariffPresets.js`.

### Step 6 — Areas + Capacity

Simple table editor. Tech adds rows: name, capacity. Default row: "Main" with capacity 100.

### Step 7 — Go Live

```
┌─────────────────────────────────────────────────┐
│  Ready to Go Live                         8 / 8 │
├─────────────────────────────────────────────────┤
│  Configuration summary:                         │
│  ✓ Site: Parking Mall ABC                       │
│  ✓ 2 gates configured                           │
│  ✓ 1 booth station                              │
│  ✓ 3 vehicle types                              │
│  ✓ 1 parking area (cap 100)                     │
│                                                 │
│  Connectivity check:                            │
│  ✓ Controller GATE-OUT-01           42ms       │
│  ✓ Printer /dev/parking-printer     open       │
│  ✓ E-Money /dev/parking-emoney      INIT ok    │
│  ✓ Camera RTSP stream               connected  │
│                                                 │
│  [ Enable Gates & Finish ]                      │
└─────────────────────────────────────────────────┘
```

"Enable Gates & Finish" → `POST /api/setup/finalize`:

1. Runs `enable-gate-daemons.sh --run --include-local-serial` (combo flag from Step 2).
2. Sets `setup_complete=true` in settings table.
3. Deletes setup token from `/etc/parking/setup-token`.
4. Returns success, frontend redirects to `/login` (or directly to `/` if admin JWT still valid).

---

## 6. Backend API Additions

New router `api/app/routes/setup.py`:

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/setup/state` | Public | Returns `{setup_complete, current_step, topology, has_admin, has_session}` |
| POST | `/api/setup/redeem-token` | Token in body | Validates `/etc/parking/setup-token`, issues setup session cookie |
| POST | `/api/setup/enroll` | Enroll token in body | Hands a booth PC `INTERNAL_API_KEY` + Redis address (reusable 24h) |
| POST | `/api/setup/logout` | Public | Clears setup session cookie |
| POST | `/api/setup/create-admin` | Setup session | Creates first admin user, issues real JWT cookies |
| GET | `/api/setup/preflight` | Admin or setup | Runs preflight_check.py logic, returns list |
| POST | `/api/setup/state` | Setup session | Persists a step's data for resume |
| GET | `/api/setup/session` | Setup session | Returns `{current_step, data}` for resume |
| POST | `/api/setup/detect-serial` | Admin or setup | Runs detect-serial-devices.sh in JSON mode |
| POST | `/api/setup/test-device` | Admin or setup | Probes serial/TCP/ping device, returns latency |
| POST | `/api/setup/test-gate` | Admin or setup | End-to-end open/close test, waits for daemon ACK |
| POST | `/api/setup/write-udev` | Admin or setup | Writes udev symlink rule atomically |
| POST | `/api/setup/topology` | Admin or setup | Bulk-creates `GIN-NN`/`GOUT-NN` gates from preset |
| POST | `/api/setup/finalize` | Admin or setup | Enables daemons, flips setup_complete, deletes session/token |

Existing CRUD routes (`/api/gates`, `/api/printers`, `/api/emoney-readers`, etc.) reused for per-record saves during the wizard.

### Required script changes

- `scripts/detect-serial-devices.sh`: add `--json` mode (currently human-readable only).
- `scripts/detect-serial-devices.sh`: add `--write-udev <role> <port>` mode for atomic single-symlink write.
- `scripts/test_device.py`: **new file**, opens serial port or TCP socket, returns JSON `{ok, latency_ms, detail|error}`.
- `scripts/enable-gate-daemons.sh`: add `--json` output mode for API to parse status.

### Permission model

Wizard runs as `parking` user via API. The detect / udev / daemon-enable scripts need root. Use a pre-installed sudoers drop-in:

```
# /etc/sudoers.d/parking-setup (owned by root, mode 0440)
parking ALL=(root) NOPASSWD: \
  /opt/parking-system-v2/scripts/detect-serial-devices.sh, \
  /opt/parking-system-v2/scripts/enable-gate-daemons.sh, \
  /usr/bin/systemctl start parking-gate@*, \
  /usr/bin/systemctl enable parking-gate@*, \
  /usr/bin/systemctl restart parking-gate@*, \
  /usr/bin/udevadm control --reload-rules, \
  /usr/bin/udevadm trigger
```

Sudoers file dropped by `installer/server/setup.sh`. Visudo validation in CI.

### Setup token mechanics

1. `installer/server/setup.sh` generates: `openssl rand -hex 32 > /etc/parking/setup-token` (mode 0600, owner root).
2. Shell prints token and URL: `http://<ip>/setup?token=<X>`.
3. `POST /api/setup/redeem-token` reads file, compares constant-time, deletes file on success, issues setup session cookie (httpOnly, sameSite=strict, 1h TTL).
4. Token has 24h hard expiry (mtime check) — if installer ran but tech never opened browser, token still valid for 24h then auto-purged by systemd timer.

### udev write safety

`POST /api/setup/write-udev` flow:

1. Read existing `/etc/udev/rules.d/99-parking-serial.rules`.
2. Parse lines, replace any existing rule with same `SYMLINK+=` target.
3. Write atomically: `tmpfile + fsync + rename`.
4. Run `udevadm control --reload-rules && udevadm trigger`.
5. Verify symlink exists at expected path (with 2s timeout polling).
6. Audit log: user_id, VID:PID, symlink target, timestamp.

Only the wizard endpoint writes udev. `device.vue` CRUD never touches it (too easy to corrupt).

---

## 7. Dashboard Redesign (Phase 4 — Deferred)

Replace `device.vue` tab grid with a status-card grid. One card per gate:

```
┌─ GATE-OUT-01 ──────────────────────── ●online ─┐
│ Compass · 192.168.1.100:5000                   │
│                                                │
│ Printer    ●  Paper: 78%  (refill)             │
│ E-Money    ●  Last init: 12s ago               │
│ Camera     ●  RTSP ok                          │
│                                                │
│ Last heartbeat: 4s ago                         │
│ [ Test ] [ Edit ] [ Open Gate ] [ Restart ]    │
└────────────────────────────────────────────────┘
```

Inline edit popover for common fields (IP, port, baudrate). Full modal only for hardware re-wiring. Live updates via existing WebSocket (`shared/events.py` already publishes gate state).

Consolidate `setting.vue` tabs:

| Old tabs | New tabs |
|----------|----------|
| Site Info | **Site** |
| Umum (key/value) | **Advanced** (collapsible, admin-only) |
| Jenis Kendaraan | **Tarif** (merged with Areas) |
| Shift | **Shifts** |
| Area Parkir | merged into **Tarif** |

Add top-right button: "🔧 Run Setup Wizard Again" (admin only, opens `/setup?force=1`).

---

## 8. Phasing

| Phase | Deliverable | Files touched | Est. effort |
|-------|-------------|---------------|-------------|
| **P1** | Wizard skeleton + Steps 0, 0a, 1, 5, 6 (no hardware) | `frontend/pages/setup.vue` (new), `api/app/routes/setup.py` (new), Alembic migration for `setup_complete` setting key | 2-3 days |
| **P2** | Hardware detect + test endpoints + Steps 2, 3, 4 | `scripts/detect-serial-devices.sh` `--json` mode, `scripts/test_device.py` (new), `api/app/routes/setup.py` extended | 3-4 days |
| **P3** | Finalize step + sudoers + daemon enable | `installer/server/setup.sh` sudoers drop + token gen, `scripts/enable-gate-daemons.sh` `--json` mode | 2 days |
| **P4** | Dashboard status cards | `frontend/pages/device.vue` rewrite, `frontend/pages/setting.vue` consolidation | 3-4 days |

P1+P2+P3 = MVP for wizard. P4 = day-2 operational quality.

---

## 9. Acceptance Criteria

MVP (P1-P3) complete when:

1. Fresh Ubuntu 22.04 VM → `sudo bash installer/server/setup.sh` → tech opens browser at printed URL → completes wizard without opening a terminal again.
2. Wizard creates first admin, configures site, picks topology, configures 2 gates (1 IN + 1 OUT) with peripherals, sets tariffs and areas, enables daemons.
3. Hardware auto-detect proposes correct role for at least: FTDI FT232R (emoney), Prolific PL2303 (printer), CH340 (gate).
4. udev rules persist symlinks across reboot.
5. Wizard resumable: kill browser at any step → reopen `/setup` → resume from same step (state stored in DB row per session).
6. Re-running wizard after `setup_complete=true` does not wipe existing data (upsert semantics).

## 10. Open Risks

| Risk | Mitigation |
|------|------------|
| `scripts/detect-serial-devices.sh` VID:PID DB incomplete | Show all unmatched USB ports as "Unknown" with manual role pick |
| udev rule reload races with serial device opening | `udevadm settle --timeout=5` after trigger |
| Token leaked in shell history / SSH session | 24h expiry + one-time use + delete on redeem |
| Setup session cookie collides with admin JWT | Separate cookie name `parking_setup_session` vs `parking_access` |
| Tech runs wizard twice in parallel tabs | DB lock on `setup_complete` row, second tab gets error |
| Combo PC detection wrong | "Override" button on Step 2 always available |

## 11. Decisions Locked

1. **Wizard re-run allowed** for admin role at `/setup?force=1`. No middleware redirect after `setup_complete=true`.
2. **First admin via wizard** using setup token from `/etc/parking/setup-token`. Shell installer generates token, prints URL.
3. **udev rules written by wizard** via dedicated endpoint, sudoers-scoped to exact script path + flag.
4. **Topology auto-detected** by checking systemd unit state + `/dev/parking-*` symlinks. Override always available.

---

## 12. UI/UX Specification

### 12.1 Design Principles

| Principle | Implementation |
|-----------|----------------|
| **One thing per screen** | Each wizard step has a single primary task. No scrolling for primary action. |
| **Big targets** | Min button height 44px (touch-friendly, technician may wear gloves). |
| **Read-then-do** | Each step opens with one-sentence intent in muted text before form. |
| **Test before save** | Every hardware field has a sibling "Test" button. Save disabled until test green. |
| **No jargon** | "Pemindai e-money" not "PASSTI reader". "Pintu masuk" not "GateIn". |
| **Indonesian-first** | All copy in Bahasa Indonesia. English tooltips for technical terms. |
| **Forgiving** | Every destructive action confirmable. Back button always present. State saved on every field blur. |
| **Live feedback** | Validation runs on blur, not on submit. Status pills update in real-time. |

### 12.2 Design Tokens (reuse existing)

From `frontend/assets/css/tailwind.css`:

```
Layout
  bg-background       page background
  bg-surface          card background
  bg-surface-hover    interactive surface hover
  bg-muted            disabled / chip background
  border-border       all dividers and form borders

Typography
  text-foreground     primary text (oklch 0.95 dark / 0.15 light)
  text-muted-foreground   secondary, hints, labels

Semantic colors
  text-primary / bg-primary       blue — primary CTA, focus ring, active step
  text-success / bg-success       green — test passed, online, valid
  text-warning / bg-warning       amber — warning, slow response, paper low
  text-destructive / bg-destructive  red — test failed, offline, error

Radius
  rounded-md (0.5rem)   default form controls
  rounded-lg (0.75rem)  cards
  rounded-xl (1rem)     hero cards (topology picker)
```

No new tokens introduced. Wizard inherits global theme; tech toggles dark/light via existing app switcher.

### 12.3 Wizard Shell Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  ┌──────────────────────────────────────────────────────────┐    │  ← page bg
│  │ [LOGO]  E-Parking Setup           Step 4 of 8  [Help ?]  │    │  ← top bar  h-14
│  ├──────────────────────────────────────────────────────────┤    │
│  │  ●─────●─────●─────●─────○─────○─────○─────○             │    │  ← stepper
│  │  Site  Admin Site  Topo  Gate  Booth Tarif Live          │    │     h-12
│  ├──────────────────────────────────────────────────────────┤    │
│  │                                                          │    │
│  │   <Step intent: one-line muted text>                     │    │
│  │                                                          │    │
│  │   <Step body — single column, max-w-2xl, card surface>   │    │
│  │                                                          │    │
│  │                                                          │    │
│  │                                                          │    │
│  ├──────────────────────────────────────────────────────────┤    │
│  │ [← Kembali]            Auto-saved ✓        [Lanjut →]    │    │  ← footer h-16
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

**Container**: `min-h-screen bg-background flex items-center justify-center p-6`. Inner card `w-full max-w-3xl bg-surface border border-border rounded-xl shadow-lg`. Card height fluid; min-h-[600px] to avoid jumpy layout.

**Top bar**: `h-14 px-6 flex items-center justify-between border-b border-border`. Logo left, step counter center (`text-sm text-muted-foreground`), help icon right (opens floating panel with FAQ + "Contact support" button — no modal stack).

**Stepper**: horizontal pill chain. Each step:
- Future: `w-8 h-8 rounded-full bg-muted text-muted-foreground` + label below `text-xs text-muted-foreground`.
- Current: `bg-primary text-primary-foreground ring-4 ring-primary/20` + label `text-xs font-medium text-foreground`.
- Done: `bg-success text-white` with checkmark icon.
Clicking a done step navigates back (warning toast if forward step has unsaved data).

**Body**: `p-8 space-y-6`. Single column for cognitive load. Right rail only on Step 1 (live receipt preview).

**Footer**: sticky `h-16 px-6 border-t border-border flex items-center justify-between`. Save indicator in middle: `<CheckIcon /> Tersimpan otomatis 2 detik yang lalu` (muted text).

### 12.4 Component Inventory

**Reuse**:
- `~/components/ui/button` — primary, secondary, ghost variants
- `~/components/ui/input` — text fields
- `~/components/ui/badge` — status chips (online/offline/paper)
- `~/components/ui/dialog` — only for confirmation prompts (e.g., "Overwrite existing udev rule?")
- `~/components/ui/progress` — preflight check progress bar
- `~/components/ui/tooltip` — technical term hover hints

**New components** (under `frontend/components/setup/`):

| Component | Purpose | Props |
|-----------|---------|-------|
| `SetupShell.vue` | Top bar + stepper + footer scaffolding | `currentStep, totalSteps, autosavedAt, onBack, onNext, canAdvance` |
| `SetupStepper.vue` | Horizontal step pill chain | `steps: {key,label,status}[]` |
| `PreflightList.vue` | List of check rows with status icons | `checks: {name,status,message}[]` |
| `TopologyCard.vue` | Big clickable preset card with ASCII gate diagram | `inCount, outCount, selected, onClick` |
| `DeviceProbeRow.vue` | Inline serial/TCP field + Test button + status pill | `v-model, type, onTest, status` |
| `PeripheralAccordion.vue` | Collapsible peripheral section with own probe rows | `title, enabled, children` |
| `TariffPresetCard.vue` | Preset bundle card with sample prices | `name, items, onApply` |
| `StatusPill.vue` | Reusable badge: online/offline/testing/warning | `status, label` |
| `TokenGate.vue` | Token redeem entry screen (handles ?token= param) | none |
| `WizardField.vue` | Label + input + helper text + error wrapper | `label, helper, error, slot` |

### 12.5 State & Status Visualization

**StatusPill** variants (used everywhere):

```
●online      bg-success/15  text-success  border-success/30
●offline     bg-destructive/15 text-destructive  border-destructive/30
●testing     bg-primary/15  text-primary  animate-pulse
●warning     bg-warning/15  text-warning
●idle        bg-muted text-muted-foreground
```

All pills: `inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border`.

**Test Connection button states**:

```
Idle:     [ Test Koneksi ]               border-border
Testing:  [ ⟳ Menguji... ]                animate-spin icon, disabled
Success:  [ ✓ Berhasil  142ms ]          text-success
Failed:   [ ✗ Gagal — Permission denied ] text-destructive, click to retry
```

State transitions inline (no toast for success). Failures expand a small detail panel underneath with the raw error message in `font-mono text-xs`.

### 12.6 Form Validation

- **On blur**: required-field check, format check (IP regex, port range 1-65535, baudrate enum).
- **On change**: clear previous error after first keystroke.
- **Field errors**: `text-destructive text-xs mt-1` under input, plus red border on the input itself.
- **Step-level errors**: top of body, dismissable banner `bg-destructive/10 border-destructive/30 text-destructive`.
- **"Lanjut" button**: disabled (`opacity-50 cursor-not-allowed`) until step valid. Tooltip on hover explains why.

### 12.7 Resume State / Autosave

- Every field saves on `blur` to `localStorage` key `setup_state_v1` for resume.
- Every step transition saves to backend (`POST /api/setup/state` body `{step, data}`) — server persists in a new `setup_state` JSONB column on `settings` table or a dedicated `setup_session` table.
- Footer shows `Tersimpan otomatis HH:MM:SS` after each save (debounce 1s).
- On wizard load: hydrate from backend first, fall back to localStorage if 404.
- If backend version newer than local (other tab edited), show banner "Konfigurasi diperbarui di tab lain. [Muat ulang]".

### 12.8 Loading & Skeleton States

- **Preflight check running**: `<Progress :value="percent" />` bar + scrolling check list with each row fading from idle to result.
- **Device detect running**: button shows `⟳ Mendeteksi perangkat...` for 2-8 seconds, results animate in.
- **Topology auto-detect on page load**: skeleton boxes (`bg-muted animate-pulse rounded-lg h-24`) for ~500ms, then real cards.
- **Finalize step running**: full-card overlay with spinner + step-by-step log lines streaming in (matches `enable-gate-daemons.sh` output).

### 12.9 Empty States

- **No USB devices detected**: friendly illustration (SVG) + headline "Tidak ada perangkat terdeteksi" + body "Pastikan kabel USB tersambung dan perangkat menyala." + button "Coba lagi".
- **No gates configured yet** (custom topology branch): "Belum ada gate. [Tambah gate pertama]".

### 12.10 Animations & Transitions

- Step change: `transition: opacity 200ms, transform 200ms`. Outgoing step slides left -8px and fades, incoming slides from right +8px.
- Status pill state change: 150ms color crossfade.
- Inline accordion expand: `transition-[max-height] duration-300 ease-out`.
- No page-level loaders; everything inline. No spinners >2s without showing log output.
- Respect `prefers-reduced-motion`: disable slides, keep crossfades only.

### 12.11 Accessibility

- **Keyboard nav**: Tab through fields. Enter on focused button activates. Esc closes any open dialog. Arrow keys move within stepper (focused step).
- **Focus ring**: `focus-visible:ring-2 ring-primary ring-offset-2 ring-offset-background` on every interactive element.
- **ARIA**:
  - Stepper: `role="navigation" aria-label="Setup steps"`, each step `aria-current="step"` when active.
  - Status pills: `aria-live="polite"` so screen reader announces "Connection test passed, 142 milliseconds".
  - Form errors: `aria-describedby` linking input → error text.
- **Color**: status info never communicated by color alone — always paired with icon (✓ / ✗ / ⚠) and text.
- **Touch targets**: 44px min. Buttons `h-11 px-5`.
- **Contrast**: dark mode uses oklch lightness ≥0.65 for accent colors against `oklch(0.20)` surface = WCAG AA pass.

### 12.12 Indonesian Copy Guide

| Concept | Bahasa Indonesia | Avoid |
|---------|------------------|-------|
| Continue / Next | Lanjut | Selanjutnya |
| Back | Kembali | Mundur |
| Save | Simpan | Save |
| Test Connection | Test Koneksi | Uji Penghubungan |
| Detect | Deteksi | Pendeteksian |
| Gate (entry) | Pintu Masuk | Gerbang Masuk |
| Gate (exit) | Pintu Keluar | Gerbang Keluar |
| Booth / POS | Loket | Booth |
| Reader (e-money) | Pemindai E-Money | Reader E-Money |
| Printer | Pencetak Struk | Printer |
| Auto-saved | Tersimpan otomatis | Auto-save |
| Online | Terhubung | Online |
| Offline | Tidak Terhubung | Offline |

Technical jargon (RTSP, baudrate, /dev/parking-emoney) stays as-is — exposed only in collapsed "Lanjutan / Advanced" panels and tooltips.

### 12.13 Detailed Mockup — Step 3 (Hardware) with Real Tailwind

```vue
<div class="space-y-6">
  <!-- Step intent -->
  <p class="text-sm text-muted-foreground">
    Atur perangkat untuk <span class="font-medium text-foreground">GATE-OUT-01</span>.
    Klik Deteksi untuk mencari perangkat USB otomatis.
  </p>

  <!-- Gate identity -->
  <div class="grid grid-cols-2 gap-4">
    <WizardField label="Nama Gate" helper="Contoh: Pintu Keluar Lobi">
      <Input v-model="gate.name" placeholder="Pintu Keluar Lobi" />
    </WizardField>
    <WizardField label="Kode Gate" helper="Tidak bisa diubah nanti">
      <Input v-model="gate.code" class="font-mono" />
    </WizardField>
  </div>

  <!-- Controller -->
  <section class="rounded-lg border border-border bg-surface p-4 space-y-3">
    <h3 class="text-sm font-semibold text-foreground">Controller</h3>

    <div class="flex gap-2">
      <button
        v-for="proto in ['compass', 'enet', 'serial']"
        :key="proto"
        :class="[
          'flex-1 rounded-md border px-3 py-2 text-sm font-medium transition-colors',
          gate.protocol === proto
            ? 'border-primary bg-primary/10 text-primary'
            : 'border-border bg-background text-muted-foreground hover:bg-surface-hover'
        ]"
        @click="gate.protocol = proto"
      >
        {{ protoLabel(proto) }}
      </button>
    </div>

    <DeviceProbeRow
      v-if="gate.protocol === 'serial'"
      v-model:device="gate.controller_device"
      v-model:baudrate="gate.controller_baudrate"
      type="serial"
      role="gate"
    />
    <DeviceProbeRow
      v-else
      v-model:host="gate.controller_host"
      v-model:port="gate.controller_port"
      type="tcp"
    />
  </section>

  <!-- Peripherals -->
  <section class="space-y-2">
    <h3 class="text-sm font-semibold text-foreground">Perangkat Tambahan</h3>
    <PeripheralAccordion title="Pencetak Struk" v-model:enabled="peripherals.printer">
      <DeviceProbeRow v-model="peripherals.printer_config" type="serial" role="printer" />
    </PeripheralAccordion>
    <PeripheralAccordion title="Pemindai E-Money" v-model:enabled="peripherals.emoney">
      <DeviceProbeRow v-model="peripherals.emoney_config" type="serial" role="emoney" />
    </PeripheralAccordion>
    <PeripheralAccordion title="RFID Member" v-model:enabled="peripherals.rfid" />
    <PeripheralAccordion title="Kamera" v-model:enabled="peripherals.camera" />
  </section>
</div>
```

`DeviceProbeRow` internal:

```vue
<div class="flex items-end gap-2">
  <WizardField label="Device" class="flex-1">
    <div class="flex gap-2">
      <select v-model="device" class="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm">
        <option v-for="opt in detectedDevices" :value="opt.port">{{ opt.port }} — {{ opt.chip }}</option>
        <option value="__custom__">Lainnya...</option>
      </select>
      <Button variant="secondary" size="sm" :loading="detecting" @click="onDetect">
        <SearchIcon class="h-4 w-4" /> Deteksi
      </Button>
    </div>
  </WizardField>
  <WizardField label="Baudrate" class="w-32">
    <select v-model="baudrate" class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm">
      <option v-for="b in [9600, 19200, 38400, 57600, 115200]">{{ b }}</option>
    </select>
  </WizardField>
  <Button
    variant="outline"
    size="sm"
    :loading="testing"
    @click="onTest"
    class="h-10"
  >
    Test
  </Button>
  <StatusPill v-if="testResult" :status="testResult.ok ? 'online' : 'offline'"
    :label="testResult.ok ? `${testResult.latency_ms}ms` : 'Gagal'" />
</div>
```

### 12.14 Detailed Mockup — Step 7 (Go Live) Log Streaming

```vue
<div v-if="finalizing" class="space-y-4">
  <div class="flex items-center gap-3">
    <Spinner class="h-5 w-5 text-primary" />
    <p class="text-sm text-foreground">Mengaktifkan layanan...</p>
  </div>

  <div class="rounded-lg border border-border bg-black/40 p-4 font-mono text-xs max-h-64 overflow-y-auto">
    <div v-for="line in logLines" :key="line.id" :class="lineClass(line.level)">
      <span class="text-muted-foreground">{{ line.ts }}</span> {{ line.text }}
    </div>
  </div>
</div>
```

Log lines from server-sent events. Color: info=foreground, warn=warning, error=destructive, ok=success. Auto-scroll to bottom.

### 12.15 Error Recovery UX

- **Test failed**: inline panel under field with raw error + suggested fix.
  - "Permission denied" → "Jalankan: `sudo usermod -aG dialout parking`" + Copy button.
  - "No such device" → "Coba cabut & pasang kembali kabel USB" + Re-detect button.
  - "Connection refused" → "Pastikan controller menyala dan IP benar".
- **Finalize fails mid-way**: rollback button preserves config in DB, surfaces stderr from script. Tech can retry. `setup_complete` stays false until clean finalize.
- **Token expired**: dedicated screen with instruction "Jalankan ulang installer di server untuk mendapat token baru." No silent failure.

### 12.16 Help Drawer

Triggered by `?` icon in top bar. Slide-in from right (`fixed inset-y-0 right-0 w-96 bg-surface border-l border-border`). Contents:

- "Cara menggunakan wizard ini" — 2 paragraph intro
- Per-step FAQ (auto-scrolls to current step's section)
- "Hubungi support" — phone + WhatsApp link from `site_config`
- "Riwayat perubahan" — list of saves with timestamp

Closes on Esc or click-outside. Does not block wizard interaction.

### 12.17 Responsive

- Min width 1024px (desktop / laptop / booth PC). Below: show "Buka pada layar laptop atau PC booth untuk hasil terbaik." with continue-anyway link.
- No mobile design — explicit non-goal. Wizard runs once on a real screen.
- Print stylesheet: prints completed wizard summary (Step 7 view) for tech to leave at site.

### 12.18 Visual Hierarchy Audit Checklist

- [ ] Largest text on screen = current step's primary question.
- [ ] Only ONE primary button per screen (`bg-primary`). Others are `variant="secondary"` or `ghost`.
- [ ] Test buttons sit next to the field they test, not in a separate "Test All" tray.
- [ ] Auto-detect button always to the right of the manual-input field.
- [ ] Destructive actions (Reset, Override topology) appear only as ghost links, never primary.
- [ ] No more than 3 colors per screen excluding text (background, surface, one accent).

---

*Plan author: design-mode session 2026-05-14. Next action: lock P1 scope and start implementation.*
