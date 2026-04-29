# E-Parking v2 — Booth & Multi-PC Deployment Guide

> **Version:** 2.1.0  
> **Last Updated:** 27 April 2026  
> **Applies to:** Hardware Configuration & Booth Architecture Migration

---

## Overview

This guide covers deploying E-Parking v2 across multiple physical computers:

- **Server PC** (PC 1): Runs API, database, Redis, and optionally serves as Booth 1
- **Booth PC(s)** (PC 2, 3, ...): Run booth bridge + browser POS for additional gate-outs

Each gate-out has its own booth PC with serial devices (e-money reader, receipt printer, barcode scanner). The booth bridge exposes these devices via WebSocket so the POS web app can access them.

---

## Architecture

```
┌─────────────────────────────────────────┐
│         SERVER PC (PC 1)                │
│  ┌──────────────┐  ┌─────────────────┐  │
│  │ PostgreSQL   │  │ FastAPI Server  │  │
│  │ Redis        │  │ (port 8000)     │  │
│  └──────────────┘  └─────────────────┘  │
│         ▲                   ▲           │
│         │ HTTP/WS           │ HTTP      │
│  ┌──────┴───────────────────┴──────┐   │
│  │       Nuxt Frontend             │   │
│  │       (port 3000)               │   │
│  └─────────────────────────────────┘   │
│         ▲                              │
│         │ ws://localhost:5678          │
│  ┌──────┴──────┐                       │
│  │ Booth Bridge│ ← serial/USB devices  │
│  │ (Booth 1)   │   for Gate-Out-1      │
│  └─────────────┘                       │
└─────────────────────────────────────────┘
           ▲
           │ HTTP (from Booth PC 2 browser)
           ▼
┌─────────────────────────────────────────┐
│         BOOTH PC 2                      │
│  ┌─────────────────────────────────┐   │
│  │ Browser (Chrome app mode)       │   │
│  │ opens http://PC1:3000           │   │
│  │                                 │   │
│  │ API calls → PC1:8000            │   │
│  │ WebSocket gate events → PC1     │   │
│  │ Booth serial devices → localhost│   │
│  └─────────────────────────────────┘   │
│         ▲                              │
│         │ ws://localhost:5678          │
│  ┌──────┴──────┐                       │
│  │ Booth Bridge│ ← serial/USB devices  │
│  │ (Booth 2)   │   for Gate-Out-2      │
│  └─────────────┘                       │
└─────────────────────────────────────────┘
```

---

## Prerequisites

### All PCs (Server + Booths)

| Requirement | Server | Booth PC |
|------------|--------|----------|
| Ubuntu 22.04 LTS | ✅ Required | ✅ Required |
| Python 3.12+ | ✅ Required | ✅ Required |
| Google Chrome | ✅ Required | ✅ Required |
| Static IP or mDNS | ✅ Recommended | ✅ Required |
| Serial port access (`dialout` group) | ⚠️ If local booth | ✅ Required |

### Network

- All PCs on same LAN (or routable network)
- Server PC IP known and stable (recommend static IP or `parking-server.local` via mDNS)
- Ports open:
  - `8000` — API (HTTP/WebSocket)
  - `3000` — Frontend (HTTP)
  - `5678` — Booth bridge (WebSocket, localhost only)
  - `5432` — PostgreSQL (localhost only on server)
  - `6379` — Redis (localhost only on server)

---

## Server PC Setup (PC 1)

### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y postgresql-16 redis-server nginx python3.12 python3.12-venv \
    google-chrome-stable git ffmpeg

# Create parking user
sudo useradd -r -s /bin/false -m parking || true
sudo usermod -aG dialout parking
```

### 2. Clone and Install Application

```bash
cd /opt
sudo git clone <repo-url> parking-system-v2
sudo chown -R parking:parking parking-system-v2
cd parking-system-v2

# Create virtual environment
sudo -u parking python3.12 -m venv .venv
sudo -u parking .venv/bin/pip install -e ".[dev]"
```

### 3. Configure Environment

```bash
sudo -u parking cp .env.example .env
sudo -u parking nano .env
```

Key variables:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=parking
DB_USER=parking
DB_PASSWORD=<strong-secret>

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET=<64-char-random-string>
APP_ENV=production

# Settlement
SETTLEMENT_DIR=/var/lib/parking/settlements
```

### 4. Initialize Database

```bash
# Create database and user
sudo -u postgres psql -c "CREATE USER parking WITH PASSWORD '<strong-secret>';"
sudo -u postgres psql -c "CREATE DATABASE parking OWNER parking;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE parking TO parking;"

# Run migrations
sudo -u parking .venv/bin/alembic upgrade head

# Seed initial data (optional)
sudo -u parking .venv/bin/python scripts/seed.py
```

### 5. Build Frontend

```bash
cd /opt/parking-system-v2/frontend
npm install

# Build with server IP so booth PCs can connect
NUXT_PUBLIC_API_BASE_URL=http://$(hostname -I | awk '{print $1}'):8000 \
    npm run build
cd ..
```

### 6. Create Directories

```bash
sudo mkdir -p /var/lib/parking/{snapshots,settlements,logs}
sudo chown -R parking:parking /var/lib/parking
```

### 7. Install Systemd Services

```bash
# Core services
sudo cp systemd/parking-api.service /etc/systemd/system/
sudo cp systemd/parking-worker-critical.service /etc/systemd/system/
sudo cp systemd/parking-worker-bg.service /etc/systemd/system/

# Booth bridge (for Booth 1 if server also has serial devices)
sudo cp systemd/booth-bridge.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable parking-api parking-worker-critical parking-worker-bg
sudo systemctl start parking-api parking-worker-critical parking-worker-bg
```

### 8. Configure Nginx

```nginx
# /etc/nginx/sites-available/parking
server {
    listen 80;
    server_name _;
    
    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    # API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Metrics
    location /metrics {
        proxy_pass http://localhost:8000;
        allow 192.168.0.0/16;
        allow 10.0.0.0/8;
        deny all;
    }
}
```

Enable:

```bash
sudo ln -sf /etc/nginx/sites-available/parking /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Booth PC Setup (PC 2, 3, ...)

Each booth PC needs:
1. Python + booth bridge service
2. Chrome desktop shortcut pointing to server
3. Serial device configuration

### 1. Install Minimal Dependencies

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv google-chrome-stable git

# Create parking user
sudo useradd -r -s /bin/false -m parking || true
sudo usermod -aG dialout parking
```

### 2. Clone Repository (Code Only)

```bash
cd /opt
sudo git clone <repo-url> parking-system-v2
sudo chown -R parking:parking parking-system-v2
cd parking-system-v2

# Create virtual environment (only for booth bridge dependencies)
sudo -u parking python3.12 -m venv .venv
sudo -u parking .venv/bin/pip install pyserial websockets
```

### 3. Configure Booth Bridge

Create config file for this booth:

```bash
sudo mkdir -p /etc/parking
sudo tee /etc/parking/booth.json > /dev/null <<'EOF'
{
  "name": "Booth 2",
  "code": "BOOTH_02",
  "peripherals": {
    "emoney_reader": {
      "enabled": true,
      "device": "/dev/ttyUSB1",
      "baudrate": 38400
    },
    "receipt_printer": {
      "enabled": true,
      "device": "/dev/ttyUSB2",
      "baudrate": 9600
    },
    "barcode_scanner": {
      "enabled": true,
      "device": "/dev/ttyUSB0",
      "baudrate": 9600
    },
    "running_text": {
      "enabled": false
    }
  }
}
EOF
sudo chown parking:parking /etc/parking/booth.json
```

> **Note:** Adjust `/dev/ttyUSB*` paths based on your actual hardware. Use `dmesg | grep ttyUSB` after plugging in devices to identify correct ports.

### 4. Install Booth Bridge Service

```bash
sudo cp systemd/booth-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now booth-bridge
```

Verify it's running:

```bash
sudo systemctl status booth-bridge
sudo journalctl -u booth-bridge -f
```

### 5. Create Desktop Shortcut

```bash
# From the repository
cd /opt/parking-system-v2
sudo ./scripts/create-desktop-shortcut.sh 192.168.1.101 "Parking-POS"

# Or manually:
cat > ~/Desktop/Parking-POS.desktop <<EOF
[Desktop Entry]
Name=Parking POS
Comment=E-Parking POS System
Exec=/usr/bin/google-chrome --app=http://192.168.1.101:3000 --start-fullscreen --no-first-run --no-default-browser-check
Icon=/usr/share/icons/hicolor/256x256/apps/google-chrome.png
Type=Application
Terminal=false
Categories=Application;
StartupNotify=true
EOF
chmod +x ~/Desktop/Parking-POS.desktop
```

> **Replace `192.168.1.101`** with your actual server IP.

### 6. Auto-Login (Optional)

For dedicated booth PCs, configure auto-login so the operator doesn't need to enter OS credentials:

```bash
# For GDM (GNOME)
sudo tee /etc/gdm3/custom.conf > /dev/null <<'EOF'
[daemon]
AutomaticLoginEnable=true
AutomaticLogin=operator
EOF

# For LightDM
sudo tee /etc/lightdm/lightdm.conf.d/50-autologin.conf > /dev/null <<'EOF'
[Seat:*]
autologin-user=operator
autologin-user-timeout=0
EOF
```

---

## Admin Configuration (Device Page)

After deployment, access the Device page as admin to configure booth-to-gate assignments:

### 1. Configure Gates

Navigate to **Device → Gates** tab:

| Field | Example Value | Notes |
|-------|--------------|-------|
| Name | `Gate Keluar 1` | Display name |
| Code | `GOUT01` | Unique identifier |
| Direction | `OUT` | Must be OUT for exit gates |
| Protocol | `compass` | Controller protocol |
| Controller Host | `192.168.1.201` | Gate controller IP |
| POS | (select booth) | Assign booth to this gate |

### 2. Configure Booths (POS)

Navigate to **Device → Booth POS** tab:

| Field | Example Value | Notes |
|-------|--------------|-------|
| Name | `Booth 1` | Display name |
| Code | `BOOTH_01` | Unique identifier |
| IP Address | `192.168.1.101` | PC's static IP for auto-detection |
| Gate Default | `GOUT01` | Auto-assign this gate to the booth |

**Important:**
- Set `IP Address` to the booth PC's actual IP
- Set `Gate Default` to the gate this booth controls
- When both are set, the POS page auto-detects the booth and locks to its gate

### 3. Verify Auto-Detection

On each booth PC:

1. Open the POS shortcut
2. Login as operator
3. The gate dropdown should **auto-select** and **hide**
4. The header should show the assigned gate name

If auto-detection fails:
- Check browser console for errors
- Verify booth IP matches `ip_address` in database
- Ensure operator is not an admin (admins see the dropdown)

---

## Gate Daemon Configuration

### Gate-In Daemons (Entry Gates)

```bash
# Create systemd service for each gate-in
sudo systemctl enable --now parking-daemon-gate-in@GIN01
```

The daemon reads from the unified `gates` table with `direction='IN'`. It auto-detects enabled peripherals from `hardware_config` JSONB.

### Gate-Out Daemons (Exit Gates)

```bash
# Create systemd service for each gate-out
sudo systemctl enable --now parking-daemon-gate-out@GOUT01
```

The daemon handles controller communication only. E-money transactions are now delegated to the booth bridge.

---

## Verification Checklist

### Server PC

- [ ] API responds: `curl http://localhost:8000/api/health`
- [ ] Database migrations current: `.venv/bin/alembic current`
- [ ] Redis responding: `redis-cli ping`
- [ ] Frontend accessible: `curl http://localhost:3000`
- [ ] Nginx serving both frontend and API
- [ ] Gate-in daemon connected to controller
- [ ] Gate-out daemon connected to controller

### Each Booth PC

- [ ] Booth bridge running: `sudo systemctl status booth-bridge`
- [ ] Serial devices detected: `ls -la /dev/ttyUSB*`
- [ ] Bridge accepting WebSocket: `curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:5678/`
- [ ] Chrome shortcut opens POS page
- [ ] POS auto-detects booth and locks to correct gate
- [ ] E-money reader responds to test tap
- [ ] Receipt printer prints test page
- [ ] Barcode scanner inputs to barcode field

### End-to-End Flows

- [ ] Cash entry → exit flow
- [ ] RFID member entry → exit flow
- [ ] E-money entry → booth deduct → exit flow
- [ ] Lost contact recovery at booth
- [ ] Timeout alert triggers correctly
- [ ] Manual override from admin page

---

## Maintenance

### Updating the Application

```bash
# On server
cd /opt/parking-system-v2
sudo -u parking git pull origin main

# Install new dependencies
sudo -u parking .venv/bin/pip install -e ".[dev]"

# Run new migrations
sudo -u parking .venv/bin/alembic upgrade head

# Rebuild frontend
sudo -u parking bash -c 'cd frontend && npm install && npm run build'

# Restart services
sudo systemctl restart parking-api parking-worker-critical parking-worker-bg

# On booth PCs (if booth bridge code changed)
cd /opt/parking-system-v2
sudo -u parking git pull origin main
sudo systemctl restart booth-bridge
```

### Backing Up

```bash
# Database
DATE=$(date +%Y%m%d_%H%M%S)
sudo -u postgres pg_dump parking | gzip > /backup/parking_${DATE}.sql.gz

# Booth configs
sudo tar czf /backup/booth-configs_${DATE}.tar.gz /etc/parking/

# Application code
cd /opt/parking-system-v2
sudo -u parking git bundle create /backup/code_${DATE}.bundle --all
```

### Troubleshooting Booth PCs

**Booth bridge won't start:**
```bash
sudo journalctl -u booth-bridge -n 50
# Check: serial device paths correct? permissions (dialout group)?
```

**POS says "Booth Disconnected":**
```bash
# On booth PC, check bridge
sudo systemctl status booth-bridge
netstat -tlnp | grep 5678

# Test WebSocket connection
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:5678/
```

**Auto-detection fails:**
```bash
# Check client IP from browser console
# Verify IP matches pos.ip_address in database
docker exec parking-postgres psql -U parking -d parking \
  -c "SELECT code, ip_address, default_gate_id FROM pos;"
```

**E-money reader not responding:**
```bash
# Check device path
ls -la /dev/ttyUSB*
dmesg | grep ttyUSB

# Test serial connection
python3 -c "
import serial
s = serial.Serial('/dev/ttyUSB1', 38400, timeout=1)
print('Connected:', s.is_open)
s.close()
"
```

---

## FAQ

### Q: Can the server PC also be a booth?

**A:** Yes. Install `booth-bridge.service` on the server PC and configure `/etc/parking/booth.json` for Gate-Out-1. The operator opens `http://localhost:3000` on the server.

### Q: Do booth PCs need PostgreSQL/Redis?

**A:** No. Booth PCs only need Python + booth bridge + Chrome. They connect to the server's PostgreSQL and Redis via HTTP/WebSocket.

### Q: What if a booth PC reboots?

**A:** `systemctl enable booth-bridge` ensures it auto-starts. The operator just double-clicks the desktop shortcut again.

### Q: Can operators switch gates?

**A:** Only admins see the gate dropdown. Operators are locked to their booth's `default_gate_id`.

### Q: How do I add a new booth?

**A:**
1. Set up new booth PC following this guide
2. Add POS record in Device page with IP and default gate
3. Update gate's `pos_id` to link to the new booth
4. Test auto-detection

---

*This guide should be kept with the system documentation and updated when hardware or network topology changes.*
