#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# detect-serial-devices.sh
#
# Detects USB serial devices, suggests parking role assignments based on
# known VID:PID signatures, confirms with technician, then writes stable
# udev symlink rules so device names survive reboots and re-plug order changes.
#
# Symlinks created under /dev/parking-*:
#   /dev/parking-emoney    → e-money reader (PASSTI)
#   /dev/parking-printer   → thermal receipt printer
#   /dev/parking-scanner   → barcode scanner
#   /dev/parking-gate      → RS232/USB barrier gate controller
#   /dev/parking-rfid      → RFID reader (if separate)
#
# Usage:
#   sudo bash scripts/detect-serial-devices.sh          # interactive
#   sudo bash scripts/detect-serial-devices.sh --dry-run # show rules, no write
#
# After running, update /etc/parking/booth.json and installer answers to use
# /dev/parking-* paths instead of /dev/ttyUSBx.
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

DRY_RUN=false
JSON_MODE=false
WRITE_UDEV_MODE=false
WRITE_UDEV_ROLE=""
WRITE_UDEV_PORT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --json)    JSON_MODE=true; shift ;;
        --write-udev)
            WRITE_UDEV_MODE=true
            WRITE_UDEV_ROLE="${2:-}"
            WRITE_UDEV_PORT="${3:-}"
            shift 3 || shift 1
            ;;
        *) shift ;;
    esac
done

RULES_FILE="/etc/udev/rules.d/99-parking-serial.rules"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
section() { echo -e "\n${BOLD}${CYAN}$*${NC}"; }

# ── Known USB chipset database ────────────────────────────────────────────────
# Format: "VID:PID" => "chip_name|suggested_role"
declare -A USB_DB
USB_DB["0403:6001"]="FTDI FT232R|emoney"        # PASSTI e-money readers universally use FTDI
USB_DB["0403:6010"]="FTDI FT2232H|emoney"
USB_DB["0403:6014"]="FTDI FT232H|emoney"
USB_DB["067b:2303"]="Prolific PL2303|printer"   # Common in receipt printers
USB_DB["067b:23a3"]="Prolific PL2303GC|printer"
USB_DB["1a86:7523"]="WCH CH340|gate"            # Common in cheap gate controllers
USB_DB["1a86:7522"]="WCH CH340K|gate"
USB_DB["1a86:55d4"]="WCH CH9102|gate"
USB_DB["1a86:5523"]="WCH CH341|gate"
USB_DB["10c4:ea60"]="Silicon Labs CP2102|scanner" # Common in barcode scanners
USB_DB["10c4:ea70"]="Silicon Labs CP2105|scanner"
USB_DB["10c4:ea71"]="Silicon Labs CP2108|scanner"
USB_DB["04b8:0202"]="Epson USB|printer"
USB_DB["0519:0002"]="Star Micronics|printer"
USB_DB["1234:0206"]="Argox|scanner"

# Parking device roles and their display names
declare -A ROLE_NAMES
ROLE_NAMES["emoney"]="E-Money Reader (PASSTI)"
ROLE_NAMES["printer"]="Thermal Receipt Printer"
ROLE_NAMES["scanner"]="Barcode Scanner"
ROLE_NAMES["gate"]="RS232/USB Barrier Gate Controller"
ROLE_NAMES["rfid"]="RFID Reader"
ROLE_NAMES["skip"]="Not a parking device (skip)"

# ── Preflight ─────────────────────────────────────────────────────────────────
# Allow read-only modes (--dry-run, --json) without root.
NEEDS_ROOT=true
$DRY_RUN && NEEDS_ROOT=false
$JSON_MODE && NEEDS_ROOT=false
if $NEEDS_ROOT && [[ $EUID -ne 0 ]]; then
    error "Must run as root to write udev rules. Use: sudo bash $0"
    error "Or run with --dry-run / --json to preview without writing."
    exit 1
fi

if ! command -v udevadm &>/dev/null; then
    if $JSON_MODE; then
        printf '{"candidates":[],"error":"udevadm not found"}\n'
        exit 1
    fi
    error "udevadm not found. Is udev installed?"
    exit 1
fi

# ── --write-udev <role> <port>: atomic single-symlink write ───────────────────
if $WRITE_UDEV_MODE; then
    if [[ -z "$WRITE_UDEV_ROLE" || -z "$WRITE_UDEV_PORT" ]]; then
        printf '{"ok":false,"error":"missing role or port"}\n'
        exit 2
    fi
    if [[ ! -e "$WRITE_UDEV_PORT" ]]; then
        printf '{"ok":false,"error":"port %s not present"}\n' "$WRITE_UDEV_PORT"
        exit 2
    fi

    info_raw=$(udevadm info --query=all --name="$WRITE_UDEV_PORT" 2>/dev/null || true)
    vid=$(echo "$info_raw" | grep "ID_VENDOR_ID=" | cut -d= -f2 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
    pid=$(echo "$info_raw" | grep "ID_MODEL_ID="  | cut -d= -f2 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
    serial=$(echo "$info_raw" | grep "ID_SERIAL_SHORT=" | cut -d= -f2 | tr -d '[:space:]')

    symlink="parking-${WRITE_UDEV_ROLE}"

    tmpfile=$(mktemp /tmp/parking-udev.XXXXXX)
    if [[ -f "$RULES_FILE" ]]; then
        # Preserve other rules, drop any prior rule producing the same symlink.
        grep -vE "SYMLINK\\+=\"${symlink}\"" "$RULES_FILE" > "$tmpfile" || true
    else
        echo "# E-Parking v2 — Stable serial device symlinks" > "$tmpfile"
        echo "# Generated by detect-serial-devices.sh" >> "$tmpfile"
        echo "" >> "$tmpfile"
    fi

    if [[ -n "$serial" ]]; then
        match="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"${vid}\", ATTRS{idProduct}==\"${pid}\", ATTRS{serial}==\"${serial}\""
    else
        match="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"${vid}\", ATTRS{idProduct}==\"${pid}\""
    fi
    echo "${match}, SYMLINK+=\"${symlink}\", MODE=\"0660\", GROUP=\"dialout\"" >> "$tmpfile"

    install -m 0644 "$tmpfile" "$RULES_FILE"
    sync
    rm -f "$tmpfile"

    udevadm control --reload-rules >/dev/null 2>&1
    udevadm trigger --subsystem-match=tty >/dev/null 2>&1
    # Wait for udev to settle and the symlink to appear.
    udevadm settle --timeout=5 >/dev/null 2>&1 || true

    final_link="/dev/${symlink}"
    if [[ -L "$final_link" ]]; then
        printf '{"ok":true,"symlink":"%s","port":"%s"}\n' "$final_link" "$WRITE_UDEV_PORT"
        exit 0
    fi
    printf '{"ok":false,"symlink":"%s","error":"symlink not present after trigger"}\n' "$final_link"
    exit 3
fi

# ── Step 1: Enumerate devices ─────────────────────────────────────────────────
$JSON_MODE || section "Step 1/3 — Scanning USB serial devices"
$JSON_MODE || echo ""

shopt -s nullglob
DEVICES=(/dev/ttyUSB* /dev/ttyACM*)

if [[ ${#DEVICES[@]} -eq 0 ]]; then
    if $JSON_MODE; then
        printf '{"candidates":[]}\n'
        exit 0
    fi
    warn "No USB serial devices found (/dev/ttyUSB* or /dev/ttyACM*)."
    echo ""
    echo "Plug in your devices and re-run this script."
    echo "Tip: watch -n1 ls /dev/ttyUSB*"
    exit 1
fi

# Collect device info
declare -A DEV_VID
declare -A DEV_PID
declare -A DEV_SERIAL
declare -A DEV_MANUFACTURER
declare -A DEV_MODEL
declare -A DEV_DEVPATH
declare -A DEV_CHIP
declare -A DEV_SUGGESTION

for dev in "${DEVICES[@]}"; do
    info_raw=$(udevadm info --query=all --name="$dev" 2>/dev/null || true)

    vid=$(echo "$info_raw"   | grep "ID_VENDOR_ID="    | cut -d= -f2 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
    pid=$(echo "$info_raw"   | grep "ID_MODEL_ID="     | cut -d= -f2 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
    serial=$(echo "$info_raw" | grep "ID_SERIAL_SHORT=" | cut -d= -f2 | tr -d '[:space:]')
    mfr=$(echo "$info_raw"   | grep "ID_VENDOR_FROM_DATABASE=" | cut -d= -f2)
    model=$(echo "$info_raw" | grep "ID_MODEL_FROM_DATABASE="  | cut -d= -f2)
    devpath=$(echo "$info_raw" | grep "^P:" | cut -d' ' -f2)

    [[ -z "$mfr" ]]   && mfr=$(echo "$info_raw" | grep "ID_VENDOR="  | head -1 | cut -d= -f2)
    [[ -z "$model" ]] && model=$(echo "$info_raw" | grep "ID_MODEL="  | head -1 | cut -d= -f2)

    DEV_VID[$dev]="$vid"
    DEV_PID[$dev]="$pid"
    DEV_SERIAL[$dev]="$serial"
    DEV_MANUFACTURER[$dev]="${mfr:-Unknown}"
    DEV_MODEL[$dev]="${model:-Unknown}"
    DEV_DEVPATH[$dev]="$devpath"

    vidpid="${vid}:${pid}"
    if [[ -n "${USB_DB[$vidpid]+x}" ]]; then
        IFS='|' read -r chip suggestion <<< "${USB_DB[$vidpid]}"
        DEV_CHIP[$dev]="$chip"
        DEV_SUGGESTION[$dev]="$suggestion"
    else
        DEV_CHIP[$dev]="${mfr:-Unknown} ${model:-}"
        DEV_SUGGESTION[$dev]="skip"
    fi
done

# ── --json: emit candidates and exit ─────────────────────────────────────────
if $JSON_MODE; then
    n=${#DEVICES[@]}
    i=0
    printf '{"candidates":['
    for dev in "${DEVICES[@]}"; do
        vidpid="${DEV_VID[$dev]}:${DEV_PID[$dev]}"
        chip="${DEV_CHIP[$dev]}"
        chip_escaped="${chip//\"/\\\"}"
        serial="${DEV_SERIAL[$dev]:-}"
        suggestion="${DEV_SUGGESTION[$dev]}"
        if [[ "$suggestion" != "skip" ]]; then
            confidence="high"
        else
            confidence="unknown"
            suggestion=""
        fi
        printf '{"port":"%s","vid_pid":"%s","chip":"%s","serial":"%s","suggested_role":"%s","confidence":"%s"}' \
            "$dev" "$vidpid" "$chip_escaped" "$serial" "$suggestion" "$confidence"
        i=$((i+1))
        if [[ $i -lt $n ]]; then printf ','; fi
    done
    printf ']}\n'
    exit 0
fi

# ── Step 2: Display table + interactive assignment ────────────────────────────
section "Step 2/3 — Device identification"
echo ""
printf "  %-14s %-10s %-24s %-10s %s\n" "Device" "VID:PID" "Chip / Manufacturer" "Serial#" "Suggested Role"
printf "  %-14s %-10s %-24s %-10s %s\n" "──────────────" "──────────" "────────────────────────" "──────────" "──────────────────────"

for dev in "${DEVICES[@]}"; do
    vidpid="${DEV_VID[$dev]}:${DEV_PID[$dev]}"
    serial="${DEV_SERIAL[$dev]:-none}"
    chip="${DEV_CHIP[$dev]}"
    suggestion="${DEV_SUGGESTION[$dev]}"
    role_name="${ROLE_NAMES[$suggestion]:-$suggestion}"
    printf "  %-14s %-10s %-24s %-10s %s\n" "$dev" "$vidpid" "${chip:0:24}" "${serial:0:10}" "$role_name"
done

echo ""
echo "─────────────────────────────────────────────────────────────────────────────"
echo "  Assign each device a parking role. Press Enter to accept suggestion."
echo "  Roles: emoney  printer  scanner  gate  rfid  skip"
echo "─────────────────────────────────────────────────────────────────────────────"
echo ""

declare -A ASSIGNED_ROLE  # dev → role
declare -A ROLE_DEV       # role → dev (to detect duplicates)

for dev in "${DEVICES[@]}"; do
    suggestion="${DEV_SUGGESTION[$dev]}"
    chip="${DEV_CHIP[$dev]}"
    serial="${DEV_SERIAL[$dev]:-}"

    if [[ -n "$serial" ]]; then
        id_info="serial=${serial}"
    else
        id_info="VID:PID=${DEV_VID[$dev]}:${DEV_PID[$dev]}"
    fi

    echo -e "  ${BOLD}${dev}${NC}  [${chip}]  (${id_info})"
    read -rp "    Role [${suggestion}]: " chosen
    chosen="${chosen:-$suggestion}"

    # Validate
    while [[ -z "${ROLE_NAMES[$chosen]+x}" ]]; do
        warn "Unknown role '${chosen}'. Valid: ${!ROLE_NAMES[*]}"
        read -rp "    Role [${suggestion}]: " chosen
        chosen="${chosen:-$suggestion}"
    done

    if [[ "$chosen" != "skip" ]]; then
        if [[ -n "${ROLE_DEV[$chosen]+x}" ]]; then
            warn "Role '${chosen}' already assigned to ${ROLE_DEV[$chosen]}."
            warn "Two devices with same role will both get rules (e.g. gate-1, gate-2 for dual gates)."
        fi
        ROLE_DEV[$chosen]="${dev}"
    fi

    ASSIGNED_ROLE[$dev]="$chosen"
    echo ""
done

# ── Step 3: Generate udev rules ───────────────────────────────────────────────
section "Step 3/3 — Generating udev rules"
echo ""

RULES_LINES=()
RULES_LINES+=("# E-Parking v2 — Stable serial device symlinks")
RULES_LINES+=("# Generated by detect-serial-devices.sh on $(date -Iseconds)")
RULES_LINES+=("# Re-run this script if you replace or swap hardware.")
RULES_LINES+=("")

# Track role counts for duplicate roles (e.g. two gates)
declare -A ROLE_COUNT

for dev in "${DEVICES[@]}"; do
    role="${ASSIGNED_ROLE[$dev]}"
    [[ "$role" == "skip" ]] && continue

    vid="${DEV_VID[$dev]}"
    pid="${DEV_PID[$dev]}"
    serial="${DEV_SERIAL[$dev]:-}"
    devpath="${DEV_DEVPATH[$dev]}"

    # Increment role counter
    ROLE_COUNT[$role]=$((${ROLE_COUNT[$role]:-0} + 1))
    count="${ROLE_COUNT[$role]}"
    if [[ $count -eq 1 ]]; then
        symlink="parking-${role}"
    else
        symlink="parking-${role}-${count}"
    fi

    # Build rule — prefer serial number (stable across ports), fall back to USB port path
    if [[ -n "$serial" ]]; then
        rule_match="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"${vid}\", ATTRS{idProduct}==\"${pid}\", ATTRS{serial}==\"${serial}\""
        rule_comment="# ${dev} → /dev/${symlink}  [${DEV_CHIP[$dev]}, serial=${serial}]"
    else
        # Use KERNELS (USB port path) — stable if plugged into same physical port
        # Extract the USB port path from devpath: .../usb1/1-1/1-1.2/...
        usbpath=$(echo "$devpath" | grep -oP '\d+-[\d.]+(?=/\d+-[\d.]+:\d+\.\d+)' | tail -1 || true)
        if [[ -n "$usbpath" ]]; then
            rule_match="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"${vid}\", ATTRS{idProduct}==\"${pid}\", KERNELS==\"${usbpath}\""
            rule_comment="# ${dev} → /dev/${symlink}  [${DEV_CHIP[$dev]}, USB port=${usbpath}]"
            warn "${dev}: no serial number — rule uses USB port path. Keep plugged into same port."
        else
            rule_match="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"${vid}\", ATTRS{idProduct}==\"${pid}\""
            rule_comment="# ${dev} → /dev/${symlink}  [${DEV_CHIP[$dev]}, VID:PID only — plug order matters!]"
            warn "${dev}: no serial number and can't determine USB port. Rule matches by VID:PID only."
        fi
    fi

    RULES_LINES+=("$rule_comment")
    RULES_LINES+=("${rule_match}, SYMLINK+=\"${symlink}\", MODE=\"0666\", GROUP=\"dialout\"")
    RULES_LINES+=("")

    echo -e "  ${GREEN}✓${NC} /dev/${symlink} → ${dev}  [${DEV_CHIP[$dev]}]"
done

echo ""

# ── Write or dry-run ──────────────────────────────────────────────────────────
RULES_CONTENT=$(printf '%s\n' "${RULES_LINES[@]}")

if $DRY_RUN; then
    echo "─────────────────────────────────────────────────────────────────────────────"
    echo "  DRY RUN — rules that would be written to ${RULES_FILE}:"
    echo "─────────────────────────────────────────────────────────────────────────────"
    echo ""
    echo "$RULES_CONTENT"
    echo ""
    info "Re-run without --dry-run as root to apply."
else
    echo "$RULES_CONTENT" > "$RULES_FILE"
    ok "Rules written to ${RULES_FILE}"

    udevadm control --reload-rules
    udevadm trigger --subsystem-match=tty
    sleep 1

    # Verify symlinks created
    echo ""
    info "Verifying symlinks:"
    any_missing=false
    for dev in "${DEVICES[@]}"; do
        role="${ASSIGNED_ROLE[$dev]}"
        [[ "$role" == "skip" ]] && continue
        symlink="/dev/parking-${role}"
        if [[ -L "$symlink" ]]; then
            target=$(readlink -f "$symlink")
            ok "  /dev/parking-${role} → ${target}"
        else
            warn "  /dev/parking-${role} not created yet — may need replug or reboot"
            any_missing=true
        fi
    done

    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo "  Done! Use /dev/parking-* paths in your installer and booth.json."
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "  Verify anytime:   ls -la /dev/parking-*"
    echo "  Test e-money:     python scripts/emoney_diagnostic.py --device /dev/parking-emoney"
    echo "  Rules file:       ${RULES_FILE}"
    echo ""
    if $any_missing; then
        warn "Some symlinks not yet active. Replug the device or reboot, then check:"
        echo "  ls -la /dev/parking-*"
    fi
fi
