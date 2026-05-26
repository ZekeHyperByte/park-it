# Combo Demo Rehearsal — Dual-Boot + Full Test

Goal: install E-Parking v2 in **combo** role (server + booth on one PC) on **bare-metal Ubuntu**, with your real hardware (TCP gate-in controller + USB barrier-gate interface), so you can rehearse the exact flow a client's technician will run.

Combo = single PC. No second machine, no network enrollment. Everything local. This is the simplest topology to demo and the one that maps cleanly to a dual-boot box.

Two parts:

- **Part A** — make room for Ubuntu and install it (Windows → dual-boot).
- **Part B** — install + test E-Parking combo with your hardware.

---

## Part A — Dual-Boot Ubuntu Alongside Windows

> ⚠️ **Back up Windows first.** Partition changes can fail (power loss, bad sectors). A backup is your undo button. Best option of all: install Ubuntu on a **separate physical SSD** — zero risk to the Windows disk. The steps below cover both.

### A1. Pre-flight on Windows

1. **Disable Fast Startup** — Control Panel → Power Options → "Choose what the power buttons do" → uncheck *Turn on fast startup*. (Fast Startup leaves the disk in a half-hibernated state that corrupts dual-boot.)
2. **Suspend/disable BitLocker** — if the drive is encrypted, Ubuntu can't resize it. Settings → Privacy & Security → Device encryption → Off (or `manage-bde -off C:`). Wait for full decrypt.
3. **Note your firmware mode** — press the BIOS/UEFI key at boot (often `Del`/`F2`/`F10`). Confirm **UEFI** mode (modern). Note where the boot-order menu is.

### A2. Make space (skip if using a separate SSD)

Use **Windows Disk Management**, not the Ubuntu installer, to shrink — Windows knows where its own files are.

1. `Win+X` → Disk Management.
2. Right-click the `C:` partition → **Shrink Volume**.
3. Free space to allocate:
   - **Minimum 60 GB** (Ubuntu + Postgres + node_modules + frontend build + Chrome).
   - **Recommended 100–120 GB** so you can rebuild/snapshot without running out.
4. After shrink you'll see **Unallocated** space. Leave it unallocated — the Ubuntu installer will use it.

### A3. Make the Ubuntu installer USB

1. Download **Ubuntu 22.04 LTS** ISO (the installers target 22.04 specifically — other versions just print a warning, but stick to 22.04 for the rehearsal).
2. Flash to an 8 GB+ USB with **Rufus** (Windows): select ISO, partition scheme **GPT**, target **UEFI**. Write.

### A4. Install Ubuntu

1. Plug USB, reboot, open the boot menu, pick the USB (UEFI entry).
2. *Secure Boot:* if the installer won't boot, disable Secure Boot in UEFI (re-enable later if you like).
3. Choose **Install Ubuntu** → "Normal installation" + "Download updates."
4. Install type:
   - **Separate SSD:** pick *Erase disk and install Ubuntu* — but **select the empty SSD**, not the Windows one. Double-check the target disk.
   - **Same disk:** pick *Install Ubuntu alongside Windows Manager* (uses your unallocated space and sets up the dual-boot menu automatically).
5. Set username/password. Finish, reboot, remove USB.
6. At each power-on you now get the **GRUB menu**: Ubuntu or Windows. (One OS at a time — that's why combo, not server+booth, is what you test here.)

### A5. First boot in Ubuntu

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl
```

You're ready for Part B.

---

## Part B — Install + Test E-Parking (Combo)

### B0. Before you start — hardware on the LAN

- **TCP gate-in controller** (Compass): powered, plugged into the same network/switch as the PC, has a known IP + port (e.g. `192.168.1.100:5000`).
- **USB barrier-gate interface**: plugged into a USB port on the PC. Don't worry about which `/dev/ttyUSB*` it lands on — detection handles that.
- Know your PC's IP: `hostname -I`.

### B1. Get the code

```bash
git clone <your-repo-url> ~/parking-system-v2
cd ~/parking-system-v2
```

### B2. Run the combo installer

```bash
sudo ./installer/setup.sh --role combo
```

It runs the **server stack first**, then configures **this PC as Booth 1**. Prompts you'll hit (Enter accepts the default in brackets):

**Server phase**

| Prompt | What to enter |
|---|---|
| `Press Enter to continue` | Enter |
| `Server IP address [auto]` | Enter (auto-detected is fine) |
| `PostgreSQL password [parking_secret]` | pick one (hidden) |
| `JWT secret` | Enter → auto-generates |
| `Git repository URL [<prefilled>]` | Enter (now prefilled from your clone's remote) |

Then it installs Postgres 16, Redis, nginx, Python 3.12, Node 20, Chrome, builds the frontend, installs systemd services, mints tokens. Takes a few minutes (apt + npm).

**Booth phase**

| Prompt | What to enter |
|---|---|
| `Booth 1 name [Booth 1]` | Enter |
| `Booth 1 code [BOOTH_01]` | Enter |
| `Default gate for Booth 1` | e.g. `GOUT-01` (must match the OUT gate you create in the wizard) |
| **Serial detection** | see B3 below |
| baudrates | Enter for defaults (emoney 38400, printer/scanner 9600) |
| `Barrier gate connection type (tcp/serial) [tcp]` | `serial` if your USB gate is the booth's exit barrier; `tcp` if the booth uses the network controller |
| `Enable auto-login for operator? [y/N]` | `N` for a test box |

### B3. Serial detection (the part that kills "guessing")

During the booth phase the installer runs `detect-serial-devices.sh`. It:

1. Lists every USB serial device by **chipset / VID:PID**.
2. Suggests a role per device (e-money / printer / scanner / gate).
3. You confirm or correct each (press Enter to accept the suggestion).
4. Writes **stable symlinks**: `/dev/parking-emoney`, `/dev/parking-printer`, `/dev/parking-scanner`, `/dev/parking-gate` — pinned by serial# (or USB port), so they survive reboot/replug.

For this rehearsal your USB barrier gate should land as **gate** → `/dev/parking-gate`. The installer then uses that stable path in `booth.json` instead of a guessed `/dev/ttyUSB3`.

Verify after:

```bash
ls -la /dev/parking-*
```

> If a device has no serial number, the rule falls back to USB-port path — keep it plugged into the **same physical port**. The script warns you when this happens.

### B4. Probe the hardware BEFORE the wizard

Prove wiring independently of any config. Run from the install root with the venv:

```bash
cd /opt/parking-system-v2
sudo -u parking ./.venv/bin/python -m scripts.hardware.controller_diagnostic 192.168.1.100 5000
```

Expected: TCP connect OK + a parsed Compass STAT reply. This isolates **wiring/network** from daemon/config — if this fails, fix the cable/IP before blaming software.

USB gate serial probe:

```bash
sudo -u parking ./.venv/bin/python scripts/test_device.py serial --device /dev/parking-gate --baudrate 9600
```

Expected: JSON `{"ok": true, ...}` — port opens.

### B5. Finish in the browser (setup wizard)

The installer prints a setup URL and tries to open Chrome. Otherwise:

```
http://localhost/setup?token=<printed-token>
```

(If the token expired — box sat overnight — regenerate: `sudo /opt/parking-system-v2/scripts/regen-setup-token.sh`.)

In the wizard:

1. **Create admin** — your demo login.
2. **Topology** — set IN/OUT gate counts. Creates gate rows (e.g. `GIN-01`, `GOUT-01`).
3. **Configure each gate:**
   - Gate-in (TCP controller): `protocol = compass`, `controller_host = 192.168.1.100`, `controller_port = 5000`.
   - Exit gate (USB interface): `protocol = serial`, `controller_device = /dev/parking-gate`, `controller_baudrate = 9600`.
4. **POS record** — confirm Booth 1: code `BOOTH_01`, IP = this PC, default gate = your OUT gate. Link the OUT gate to the POS.
5. **Test buka/tutup** — each gate row has this button. It sends a real open command and waits for the daemon's `gate_opened` event. **A real barrier should move.** This is the money shot for the demo — end-to-end proof.

### B6. Start the gate daemons

The wizard's finalize step runs this, but to do it manually (combo, with a local serial gate):

```bash
sudo /opt/parking-system-v2/scripts/enable-gate-daemons.sh --run --include-local-serial
```

- `--include-local-serial` = also run the RS232/USB gate daemon on this machine (combo only).
- Drop that flag if your booth exit uses the TCP controller, not the USB gate.

### B7. Full diagnostic

```bash
sudo -u parking /opt/parking-system-v2/.venv/bin/python /opt/parking-system-v2/scripts/parking_doctor.py
```

Checks DB, Redis, each gate's controller reachability, daemon heartbeats, `/dev/parking-*` symlinks, and POS linkage. Exit 0 = all critical checks pass. Run `--gate GIN-01` to focus one gate.

### B8. Open the POS

Open the **Parking POS** desktop shortcut (kiosk → `http://localhost`). Test:

- E-money tap (if reader connected) → relay/gate opens.
- Cash exit → receipt prints → press Space → gate opens.
- Gate-in vehicle detect → ticket/barcode → barrier opens.

---

## Diagnostic Quick Reference

| Command | Checks |
|---|---|
| `python -m scripts.hardware.controller_diagnostic <ip> <port>` | TCP controller wiring + Compass protocol |
| `python scripts/test_device.py serial --device /dev/parking-gate --baudrate 9600` | USB serial port opens |
| `python scripts/test_device.py tcp --host <ip> --port <port>` | Raw TCP reachability |
| `ls -la /dev/parking-*` | Stable serial symlinks present |
| `parking_doctor.py` | Everything, one shot |
| `parking_doctor.py --gate <CODE>` | One gate, first FAIL row = the cause |
| `sudo journalctl -u parking-api -f` | API logs |
| `sudo journalctl -u booth-bridge-booth_01 -f` | Booth bridge / exit relay |
| `systemctl status parking-api parking-worker-critical nginx` | Service health |

## Troubleshooting

| Symptom | Action |
|---|---|
| Detection finds no devices | Replug USB; `watch -n1 ls /dev/ttyUSB*`; re-run `sudo bash scripts/detect-serial-devices.sh` |
| `/dev/parking-gate` missing after reboot | Device had no serial# → keep in same USB port, or re-run detection |
| `controller_diagnostic` timeout | Wrong IP/port, cable, or controller off — fix before touching the wizard |
| Test buka/tutup fails (no movement) | `parking_doctor.py --gate <CODE>` — first FAIL row tells you why (daemon down? controller unreachable?) |
| Daemon stuck PROCESSING | `redis-cli del daemon:state:<CODE>` then restart the unit |
| Setup token expired | `sudo scripts/regen-setup-token.sh` |
| Re-running installer | Safe — existing `JWT_SECRET` / `INTERNAL_API_KEY` are preserved (no operator logout, no booth break) |

## Demo-Day Tips

- Do a **full dry run end-to-end** the day before. Time it. The client watches the *experience*, not the code.
- Have this doc + the diagnostic table open on a second screen.
- If a gate misbehaves live, run `parking_doctor.py --gate <CODE>` — it gives a clean "here's the one thing wrong" answer instead of guessing in front of the client.
- Re-running the installer is now safe, so a half-finished install is recoverable mid-demo.
