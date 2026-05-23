# POS Operator Redesign — Design Brief

> Audience: external/internal product designer. You do not need to know our codebase. This document gives you everything required to redesign the operator POS screen of an Indonesian parking exit lane.

---

## 1. Product context

**Product:** E-Parking v2 — parking management system for Indonesian parking facilities (malls, hospitals, office buildings, government buildings). Currently in production at multiple sites.

**Screen being redesigned:** The **operator POS** — a full-screen, kiosk-style web application running on a dedicated PC at an exit booth. One screen per exit lane. An operator (kasir / petugas parkir) sits at this PC and processes every vehicle leaving the facility.

**Why redesign now:**
- The current screen evolved feature-by-feature. It works, but feels engineering-driven, dense, and visually flat.
- Operators are not technical. We want a screen a new hire can run on day one with under 30 minutes of training.
- The screen handles multiple payment methods (cash, e-money tap, RFID member card) and multiple error states (timeout, wrong card, insufficient balance, lost card contact). Today these flows feel inconsistent.
- We want to project a more polished, modern product to facility owners — the screen is also seen by management during site visits.

---

## 2. The operator (primary user)

- Indonesian, often female, ages 20–45.
- High school education, sometimes vocational diploma. Limited English.
- Sits at booth for an 8–12 hour shift. Hot, noisy, often distracted by drivers honking.
- Trained on the job; turnover is moderate (months, not years).
- Hands stay near the keyboard (barcode scanner emulates keyboard input). Mouse is secondary.
- Will memorize 3–5 keyboard shortcuts but no more.
- Cares about: not making drivers angry, not losing money on cash mistakes, finishing the shift cleanly.

**Operator does NOT care about:** internal payment states, network status details, the difference between WebSocket and HTTP. We will surface tech status discreetly, not prominently.

---

## 3. Hardware context (relevant to layout)

- **Screen:** 1366×768 or 1920×1080, landscape, 15"–22" monitor. Often touched or smudged. We do **not** support touch input — keyboard + mouse only.
- **Barcode scanner:** USB, emulates keyboard. Always-on focus on a hidden/visible text input.
- **Thermal receipt printer:** prints receipts automatically after successful payment.
- **E-money reader (PASSTI):** physical card tap pad next to the operator. Communicates via a local "booth bridge" service.
- **RFID member-card reader (Omnikey 5427):** detects member cards automatically.
- **Gate barrier:** opens via serial relay command. **Cash payments do NOT auto-open the gate** — operator must press Space (or button) after handing change. RFID and e-money do auto-open.
- **CCTV cameras:** 1–2 MJPEG feeds showing the exit lane vehicle. Used to verify plate number matches the system.

---

## 4. The exit flow (golden path)

This is what 90% of transactions look like. The redesign must make this flow effortless.

1. Vehicle approaches exit lane. Camera shows the car. Loop detector fires.
2. System receives `vehicle_detected` event. Plate number, entry time, duration auto-load on screen.
3. Operator sees: plate number, vehicle photo (entry + live exit), parking fee.
4. Driver hands over: cash, an e-money card (Mandiri eMoney, BRI Brizzi, BNI TapCash, BCA Flazz), or taps a member RFID card.
5. Operator either:
   - Presses **F1** → cash dialog → enters amount → confirms → receipt prints → hands change → presses **Space** to open gate.
   - Tells driver to tap e-money on reader → screen shows processing → success → gate opens automatically.
   - (RFID member cards are usually auto-detected; operator just confirms.)
6. Screen clears. Wait for next vehicle.

**Target:** under 15 seconds per cash transaction. Under 5 seconds per e-money/RFID.

---

## 5. Non-golden paths (must be handled)

The current screen swaps to a dedicated **ERROR** view for these. The redesign should make recovery obvious without scaring the operator.

| State | Trigger | What operator must do |
|-------|---------|----------------------|
| **Timeout** | Vehicle waited too long (default 120s) without payment | Choose: pay cash / open gate manually / mark vehicle as left without paying |
| **E-money insufficient balance** | Card has less than the fee | Fall back to cash or RFID |
| **E-money wrong card** | Tapped card differs from entry card | Retry with correct card, or fall back to cash |
| **E-money lost contact** | Card lifted mid-debit | Tap again to recover (critical: never charge twice), or cancel and use cash |
| **E-money generic failure** | Reader error | Retry or fall back to cash |
| **Barcode/plate lookup fails** | Operator typed plate number, no match | Show "not found" toast, allow retry |
| **No worker checked in** | Booth is unattended | Show blocking check-in dialog (worker selects name, enters PIN) |
| **Shift handover** | Outgoing worker about to leave, incoming worker arriving | Multi-step dialog: outgoing PIN → incoming PIN → confirm |
| **Booth bridge disconnected** | Local hardware service down | Discreet status indicator turns red; operator escalates to admin |

---

## 6. Information the screen must show

Group A — **always visible, glanceable in <1 second:**
- Gate name / lane name (e.g. "Exit Lane 2")
- Current shift name (e.g. "Shift Pagi")
- Worker on duty (name)
- Clock (HH:MM:SS)
- Hardware status (booth bridge, e-money reader, printer, gate-in daemons) — small dots, not loud
- Current state ("Waiting for vehicle", "Vehicle detected", "Processing payment", "Press Space to open gate")

Group B — **visible when a transaction is active:**
- Plate number (biggest element on screen — operator reads this aloud to verify)
- Entry time + duration parked
- Vehicle type (auto-detected for single-lane gates, dropdown for mixed lane; can be overridden with shortcuts C = Mobil / M = Motor)
- **Fee in Rupiah** (second biggest element)
- Entry photo (proof car came in)
- Live exit camera (proof car is at the gate now)
- Timeout countdown bar (yellow at 70%, red at 90%)

Group C — **visible during specific sub-flows:**
- E-money: card type detected, masked card number, balance after debit
- Cash: change amount due
- Gate-open: giant green button + Space hint
- Error: clear error title, explanation, 2–3 recovery buttons ranked by likelihood

---

## 7. Current screen anatomy (what exists today)

Three horizontal regions in a kiosk layout (no browser chrome, fullscreen):

```
┌──────────────────────────────────────────────────────────────────────┐
│ STATUS BAR (h=48px)                                                  │
│ [Gates: ●GIN-01 ●GOUT-01]  [Devices: ●Booth ●Emoney ●Printer]  HH:MM │
├──────────────────────────────────────────────────────────────────────┤
│ MAIN AREA (flexible)                                                 │
│ ┌────────┬─────────────────────────────────────────────────────────┐ │
│ │        │                                                         │ │
│ │ Camera │            Plate: B 1234 XYZ                            │ │
│ │ feed 1 │            Durasi  |  Masuk  |  Jenis                   │ │
│ │        │                                                         │ │
│ │ Camera │            Total Parkir: Rp 5.000                       │ │
│ │ feed 2 │                                                         │ │
│ │        │            [E-money inline status if active]            │ │
│ │ (288px │            [Timeout progress bar if waiting]            │ │
│ │  wide) │                                                         │ │
│ │        │            [Barcode input — always visible]             │ │
│ │        │            [BAYAR TUNAI button — F1]                    │ │
│ └────────┴─────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│ ACTION BAR (h=44px)                                                  │
│ Gate name | Shift | [C Mobil] [M Motor] [F1 Tunai] [Space Buka]  ●State│
└──────────────────────────────────────────────────────────────────────┘
```

Three transient view replacements swap into the MAIN AREA:
- **GATE_OPEN view:** giant green "Buka Palang" button + change amount.
- **ERROR view:** centered icon, title, description, 2–4 recovery buttons.
- **UNIFIED view (default):** what's diagrammed above.

Modals: Cash dialog (denomination grid + manual input), RFID dialog (card number input), Worker Check-in dialog (worker picker + PIN), Worker Handover dialog (multi-step, used at shift change).

---

## 8. Known pain points to solve

These come from operator feedback and observation:

1. **Plate number is not big enough.** Operators lean toward the screen to read it. We want it to feel like a billboard.
2. **Fee is not big enough.** Drivers ask "berapa?" and operators want to read it without squinting.
3. **The barcode input is visible but operators forget about it.** Most lookups happen automatically via vehicle detection — manual lookup is rare but critical when auto-detection fails. Today the input is the same size as a normal form field.
4. **Hardware status dots are too prominent during normal operation.** They should fade into the background and only assert themselves when something is wrong.
5. **The cash button is the only payment CTA on the main screen.** E-money and RFID happen "automatically" through the booth bridge, but operators sometimes want a manual fallback button and don't know where it is (it's hidden behind F2/F3 shortcuts).
6. **The error view feels jarring.** Background flips to red/yellow, operator panics. We want errors to feel calm and recoverable.
7. **No visual hierarchy between "waiting for car" and "car is here."** Both states look similar except one has data filled in. A new operator can't tell at a glance if the system is busy.
8. **Gate-open state is great** (giant green button) but happens too fast — operators sometimes miss it because they're handing change. Could be more persistent.
9. **The worker badge is small.** During shift handover it should feel like an event, not a tiny click target.
10. **Camera feeds occupy 288px on the left.** They're useful but rarely actively watched. Could be smaller or repositioned.

---

## 9. Constraints & non-goals

**Must keep:**
- Indonesian language (Bahasa Indonesia) for all operator-facing copy.
- Keyboard-first interaction. Every primary action must have a shortcut: F1 = cash, Space = open gate, Esc = cancel, C/M = vehicle type.
- The `kiosk` layout (status bar / main / action bar) is structurally sound — designer may rebalance heights but should not introduce browser-like chrome (no tabs, no nav menu, no breadcrumbs).
- Light theme + dark theme (we use Tailwind CSS 4; design tokens are already defined). Designer should design dark mode as the **primary** mode — booths are dim, screens stay on 24/7.
- Tailwind-friendly. Designer doesn't need to write classes but should pick spacing/sizing from a standard scale (4/8/12/16/24/32/48/64...).

**Out of scope for this redesign:**
- Admin pages (reports, settings, personnel, shifts) — separate redesign later.
- Entry-gate monitoring page (`gate-in.vue`).
- Mobile / tablet layouts — POS is desktop only.
- Touch interaction — keyboard + mouse only.
- Multi-language — Indonesian only for now.

**Brand:**
- Product name: Park-It. No strict brand book yet.
- Tone: confident, calm, professional. Not playful. Not "consumer app."
- Color: we currently use Tailwind semantic tokens (`primary`, `success`, `warning`, `destructive`, `surface`, `muted`). Designer is free to propose a refined palette — keep semantic naming.

---

## 10. Deliverables we'd like from the designer

1. **High-fidelity mocks** for these states (dark mode + light mode for at least the IDLE and ACTIVE states):
   - IDLE (no transaction, waiting for vehicle)
   - ACTIVE — vehicle detected, awaiting payment
   - ACTIVE — e-money processing
   - ACTIVE — timeout warning (70%/90%)
   - GATE_OPEN (post-payment, awaiting Space)
   - ERROR — e-money insufficient balance
   - ERROR — timeout
   - Cash payment modal
   - Worker check-in modal
   - Worker handover modal (at least one of the 3 steps)
2. **Component inventory** — buttons, badges, status dots, info items, modals — with states (hover, focus, disabled, loading).
3. **Typography scale** with rationale for the giant plate number and fee.
4. **Color tokens** (semantic, mappable to Tailwind variables).
5. **Spacing / layout grid** documented.
6. **Motion notes** — what animates, how long, ease curves. Keep motion minimal; this is a workhorse screen.
7. **One short Loom / Figma prototype** showing a happy-path cash transaction (vehicle detected → F1 → cash dialog → confirm → gate open → cleared).

Source files in Figma. We will translate to Vue 3 + Tailwind 4 in-house.

---

## 11. Reference material (in this repo)

If the designer wants to see the current implementation:

- Layout shell: `frontend/layouts/kiosk.vue`
- Main page: `frontend/pages/pos.vue`
- Default view: `frontend/components/pos/PosUnifiedView.vue`
- Error view: `frontend/components/pos/PosErrorView.vue`
- Gate-open view: `frontend/components/pos/PosGateOpenView.vue`
- Status bar: `frontend/components/pos/PosStatusBar.vue`
- Action bar: `frontend/components/pos/QuickActionBar.vue`
- Camera column: `frontend/components/pos/CameraColumn.vue`
- Cash modal: `frontend/components/pos/CashDialog.vue`
- E-money inline status: `frontend/components/pos/EmoneyInlineStatus.vue`
- Worker badge: `frontend/components/pos/WorkerBadge.vue`
- Worker check-in modal: `frontend/components/pos/WorkerCheckInDialog.vue`
- Worker handover modal: `frontend/components/pos/WorkerHandoverDialog.vue`

We can also share screen recordings of the live system on request.

---

## 12. Open questions for the designer

Things we'd love the designer to take a position on:

- Should the camera feed be the **hero** of the screen (operator visually verifies the car) or a **secondary** element (camera as proof, plate number as hero)?
- Should we keep three separate views (UNIFIED / GATE_OPEN / ERROR) or unify into one canvas where the central card morphs between states?
- Is there a better metaphor for "waiting for vehicle" than an empty form? Some products use ambient illustration or a clock; others go fully dark.
- How should we communicate the difference between "system handling this automatically" (e-money tap) vs "operator must act" (cash payment)? Today both look identical until the operator presses F1.
- The action bar at the bottom doubles as both shortcut legend and state indicator. Should these split?

---

## 13. Success criteria

We will consider the redesign a success when:

- A new operator can complete a cash transaction within their first 10 minutes on the screen, unassisted, after a 2-minute demo.
- Existing operators report less squinting / leaning toward the screen.
- Facility owners describe the screen as "modern" or "professional" without prompting during site visits.
- Error states never make the operator panic — recovery is one button away.
- The screen looks coherent in both dark and light mode without per-mode tweaks beyond color tokens.
