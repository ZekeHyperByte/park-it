# E-Parking v2 — Server + Booth Combo Installation Guide

> Install the full server stack AND configure the local PC as Booth 1. Best for small lots where the server doubles as an operator station.

---

## Use Case

You have a **small parking lot** (2 entry + 2 exit gates) and want to minimize hardware:

| Machine | Role | Gates |
|---------|------|-------|
| **Server PC** (this machine) | Server + Booth 1 | Gate In 1, Gate In 2, Gate Out 1 |
| **Booth PC 2** (separate) | Booth 2 | Gate Out 2 |

The server PC sits in the guard house/office, right next to one exit gate. That exit gate's serial devices (e-money reader, printer, scanner) plug directly into the server.

---

## Prerequisites

### Server PC (This Machine)

| Requirement | Minimum |
|------------|---------|
| OS | Ubuntu 24.04 LTS |
| CPU | 4 cores |
| RAM | 8 GB |
| Disk | 50 GB SSD |
| Network | Static IP |
| Serial | 2-3 USB-to-Serial adapters for Booth 1 |

### Booth PC 2 (Separate Machine)

| Requirement | Minimum |
|------------|---------|
| OS | Ubuntu 24.04 LTS |
| CPU | 2 cores |
| RAM | 4 GB |
| Disk | 20 GB SSD |
| Serial | 2-3 USB-to-Serial adapters for Booth 2 |

---

## Quick Start

```bash
# On the server PC
cd parking-system-v2/installer/booth_with_server
sudo ./setup.sh
```

This single script does everything:
1. Installs the full server (PostgreSQL, Redis, API, nginx, workers)
2. Builds the frontend
3. Configures this PC as Booth 1
4. Creates the Chrome kiosk shortcut

---

## What Gets Installed

### Server Stack
Same as `installer/server/` — see [Server README](../server/README.md) for details.

### Local Booth (Booth 1)

| Component | Details |
|-----------|---------|
| Service | `booth-bridge-booth_01.service` |
| Config | `/etc/parking/booth.json` |
| WebSocket | `ws://localhost:5678` |
| Serial devices | USB-to-serial for e-money, printer, scanner |
| POS shortcut | `~/Desktop/Parking-POS.desktop` → `http://localhost` |

---

## Post-Installation

### 1. Verify Server Services

```bash
sudo systemctl status parking-api
sudo systemctl status parking-worker-critical
sudo systemctl status parking-worker-bg
sudo systemctl status nginx
sudo systemctl status booth-bridge-booth_01
```

### 2. Configure Gates in Admin UI

Open `http://<server-ip>` and log in as admin.

**Gates tab:**

| Gate | Direction | Controller Host | POS |
|------|-----------|-----------------|-----|
| Gate Masuk 1 (`GIN-01`) | IN | `192.168.1.101` | — |
| Gate Masuk 2 (`GIN-02`) | IN | `192.168.1.102` | — |
| Gate Keluar 1 (`GOUT-01`) | OUT | `192.168.1.201` | Booth 1 |
| Gate Keluar 2 (`GOUT-02`) | OUT | `192.168.1.202` | Booth 2 |

**POS tab:**

| Booth | Code | IP Address | Default Gate |
|-------|------|------------|--------------|
| Booth 1 | `BOOTH_01` | `192.168.1.100` | `GOUT-01` |
| Booth 2 | `BOOTH_02` | `192.168.1.101` | `GOUT-02` |

### 3. Start Gate Daemons (After Configuring Gates in Web UI)

**Important:** Gate daemons read their config from the database. You must add gates in the web UI **before** starting daemons.

```bash
# Auto-enable all configured gates
sudo -u parking /opt/parking-system-v2/scripts/enable-gate-daemons.sh --run

# Or manually (entry gates only — exit lanes have no daemon, booth-bridge drives the relay):
sudo systemctl enable --now parking-daemon-gate-in@GIN-01
sudo systemctl enable --now parking-daemon-gate-in@GIN-02
```

> `enable --now` enables auto-start on boot **and** starts immediately. Run once per gate.

### 4. Set Up Booth PC 2

On the second booth PC:
```bash
# Copy the booth installer
scp -r parking-system-v2/installer/booth_pc/ booth-pc-2:/tmp/
ssh booth-pc-2

# Run it
cd /tmp/booth_pc
sudo ./setup.sh
```

When prompted:
- Server IP: `192.168.1.100`
- Booth name: `Booth 2`
- Booth code: `BOOTH_02`
- Default gate: `GOUT-02`

### 5. Test End-to-End

**On Server PC (Booth 1):**
1. Double-click **Parking POS** shortcut
2. Log in as operator
3. Gate dropdown should auto-hide and show `GOUT-01`

**On Booth PC 2:**
1. Double-click **Parking POS** shortcut
2. Log in as operator
3. Gate dropdown should auto-hide and show `GOUT-02`

**Test flows:**
- Drive through Gate In 1 → ticket printed → drive to Gate Out 1 → pay cash → gate opens
- Drive through Gate In 2 → ticket printed → drive to Gate Out 2 → tap e-money → gate opens

---

## Troubleshooting

See individual guides:
- [Server Troubleshooting](../server/README.md#troubleshooting)
- [Booth PC Troubleshooting](../booth_pc/README.md#troubleshooting)

### Common Combo-Specific Issues

**Server PC is too slow with booth bridge + API + PostgreSQL**
- Add more RAM (16 GB recommended for combined server+booth)
- Consider disabling `ANPR` if not needed

**Booth 1 POS opens but says "Booth Disconnected"**
```bash
# Check booth bridge on server
sudo systemctl status booth-bridge-booth_01
sudo journalctl -u booth-bridge-booth_01 -f

# Test local WebSocket
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:5678/
```

**Exit gate doesn't open**
```bash
# Verify gate config in database
curl -s http://localhost/api/gates/GOUT-01

# Exit lanes have no daemon — booth-bridge drives the relay. Check its logs:
sudo journalctl -u booth-bridge-booth_01 -f
```

---

## Maintenance

### Update Everything
```bash
cd /opt/parking-system-v2
sudo -u parking git pull origin main
sudo -u parking .venv/bin/pip install -e .
sudo -u parking .venv/bin/alembic upgrade head
cd frontend && sudo -u parking npm ci && NUXT_PUBLIC_API_BASE_URL="" npm run build

sudo systemctl restart parking-api parking-worker-critical parking-worker-bg
sudo systemctl restart booth-bridge-booth_01
sudo systemctl restart 'parking-daemon-gate-in@*'
```

---

*Last updated: April 2026*
