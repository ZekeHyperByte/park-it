# POS & Frontend Rebuild — Design Document

**Date:** 2026-05-07
**Status:** Approved
**Scope:** Full frontend rebuild (POS-first, then admin pages)

---

## Problem Statement

The current POS frontend has several issues:

- **Cluttered UI** — `PaymentPanel.vue` is 866 lines switching between 4 visual states
- **Wasted space** — sidebar + header consume ~280px on a kiosk screen
- **Code duplication** — `formatCurrency()` in 3 files, duplicate CSS blocks (scoped + unscoped)
- **Store-UI coupling** — `gateStore` calls `ElMessage` directly
- **Session-scoped data** — shift counters lost on page refresh
- **No comfort focus** — dark glassmorphism prioritizes aesthetics over operator comfort

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Layout | Full kiosk mode (no sidebar/header) | 100% screen utilization for operators |
| Payment UX | Single unified view (no state switching) | Reduces cognitive load |
| Components | Small focused (< 200 lines each) | Maintainable, testable |
| UI Framework | Tailwind v4 + shadcn-vue | Lightweight, accessible, customizable |
| Theme | Dark/light mode, comfort-first | Operator comfort over aesthetics |
| Transaction flow | Single transaction at a time | Keeps it simple |
| Shift data | API-backed | Survives refreshes, device-independent |
| Migration | POS-first incremental | Fastest impact, lowest risk |

---

## Architecture

### Layout

**Kiosk layout** (`layouts/kiosk.vue`):

```
+------------------------------------------------------+
| [Gate: GOUT01]  [Online]  [Shift: 12 tx | Rp 450K]   |  <- status bar (40px)
+------------------------------------------------------+
|                                                       |
|                   MAIN CONTENT                        |
|              (full remaining height)                  |
|                                                       |
+------------------------------------------------------+
| [F1] Cash  [F2] RFID  [F3] E-Money  [Space] Open     | <- action bar (48px)
+------------------------------------------------------+
```

- No sidebar, no header — full screen
- Existing `default.vue` layout stays for admin pages during migration

### POS Page Layout

```
+-------------------------------------------------------------------+
| PosStatusBar                                                        |
+---------------------------------+---------------------------------+
|   VEHICLE INFO (left 55%)       |   PAYMENT AREA (right 45%)     |
|                                 |                                 |
|   +---------+ +---------+      |   +-----------------------+    |
|   | Entry   | | Exit    |      |   |  Tariff: Rp 5.000     |    |
|   | Photo   | | Photo   |      |   |  Duration: 2j 15m     |    |
|   +---------+ +---------+      |   +-----------------------+    |
|                                 |                                 |
|   Plate: B 1234 ABC             |   +------+ +------+ +------+  |
|   Type: Mobil                   |   | Cash | | RFID | |E-Money|  |
|   Entry: 10:30 @ GIN01         |   +------+ +------+ +------+  |
|                                 |                                 |
|   [Quick Actions if needed]     |   [Barcode scanner input]      |
|                                 |   [E-Money status inline]      |
+---------------------------------+---------------------------------+
| QuickActionBar                                                     |
+-------------------------------------------------------------------+
```

- No visual state switching — vehicle info + payment buttons always visible
- Cash/RFID open dialog modals (shadcn-vue Dialog)
- E-money status shows inline below buttons
- Barcode scanner input always visible and auto-focused

### Component Tree

```
pages/index.vue                    (~150 lines — orchestrator only)
├── components/pos/
│   ├── PosStatusBar.vue           (~80 lines)
│   ├── VehicleInfo.vue            (~120 lines)
│   ├── PhotoComparison.vue        (~100 lines)
│   ├── PaymentButtons.vue         (~60 lines)
│   ├── CashDialog.vue             (~120 lines)
│   ├── RfidDialog.vue             (~50 lines)
│   ├── EmoneyInlineStatus.vue     (~100 lines)
│   ├── QuickActions.vue           (~80 lines)
│   └── QuickActionBar.vue         (~60 lines)
├── stores/
│   ├── gate.js                    (refactored — no UI coupling)
│   ├── pos-session.js             (NEW — API-backed shift data)
│   └── website.js                 (unchanged)
├── composables/
│   ├── useApi.js                  (unchanged)
│   ├── useSound.js                (unchanged)
│   ├── useHardwareStatus.js       (refactored)
│   ├── useKeyboard.js             (NEW — centralized shortcuts)
│   └── useFormatters.js           (NEW — formatCurrency, formatDuration)
└── lib/
    └── utils.ts                   (shadcn-vue utilities)
```

### Data Flow

```
+-------------------------------------------------------------+
| POS Frontend                                                 |
|                                                              |
|  index.vue --reads--> gateStore (transaction state)          |
|     |                    |                                   |
|     |              +-----+------+                           |
|     |              |            |                            |
|     |         $ws plugin   Booth Bridge WS                   |
|     |         (gate WS)    (localhost:5678)                   |
|     |              |            |                            |
|     |              v            v                            |
|     |         Gate Daemon   Booth Bridge                     |
|     |         (Redis)       (serial)                         |
|     |                                                        |
|     +--reads--> posSessionStore (shift data via API)         |
|                                                              |
|  useApi() --> FastAPI (all HTTP calls)                       |
|  useSound() --> Web Audio (feedback tones)                   |
|  useKeyboard() --> keyboard events (shortcuts)               |
+-------------------------------------------------------------+
```

**Changes from current:**
- `gateStore` returns data, page shows toasts via shadcn-vue `Sonner`
- `posSessionStore` fetches shift data from API on mount
- E-money balance flows through `gateStore` (not separate local ref)
- `useKeyboard()` composable centralizes all keyboard shortcuts

---

## Tech Stack

- **Tailwind v4** via `@nuxtjs/tailwindcss` module
- **shadcn-vue** via `shadcn-nuxt` module
- **shadcn-vue components:** Dialog, Button, Input, Badge, Progress, Tooltip, Sonner
- **Dark/light mode:** `class` strategy on `<html>` element

### Theme Tokens

| Token | Dark Mode | Light Mode |
|-------|-----------|------------|
| Background | oklch(0.15 0.01 260) | oklch(0.98 0.005 260) |
| Surface | oklch(0.20 0.015 260) | oklch(0.95 0.01 260) |
| Text Primary | oklch(0.95 0.01 260) | oklch(0.15 0.01 260) |
| Accent | oklch(0.65 0.15 250) | oklch(0.55 0.18 250) |
| Success | oklch(0.70 0.15 145) | oklch(0.55 0.18 145) |
| Destructive | oklch(0.65 0.18 25) | oklch(0.55 0.20 25) |

- High contrast text (WCAG AA)
- No glassmorphism, no heavy gradients
- Large touch targets (min 44px)
- Payment colors: Cash = green, RFID = blue, E-Money = purple

---

## Admin Pages Migration

After POS is rebuilt, migrate admin pages in order:

1. **POS** (kiosk layout) — highest impact
2. **Login page** — first impression, simple
3. **Gate-in monitor** — real-time, similar patterns
4. **Transaction list** — most-used admin page
5. **Device management** — CRUD patterns
6. **Remaining pages** (member, reports, notifications, settings)

New `layouts/default.vue` — Tailwind-styled sidebar with shadcn-vue navigation, collapsible, dark/light aware.

---

## Out of Scope

- Backend API changes (no new endpoints except shift summary)
- WebSocket protocol changes
- Booth bridge changes
- Daemon changes
- Database schema changes

---

## Open Questions

- [ ] Should we add a `GET /api/pos/shift-summary` endpoint for API-backed shift data?
- [ ] Should theme preference persist in localStorage or user profile?
