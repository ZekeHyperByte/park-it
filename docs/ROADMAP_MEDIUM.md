# E-Parking System v2 — Standard Roadmap
> **Pace:** Focused & Sustainable | **Timeline:** 3 Bulan (12 Minggu) | **Budget:** Rp 14.000.000
> **Type:** Solo Full-Stack Development

---

## Executive Summary

Roadmap pengembangan **3 bulan** dengan pace fokus dan sustainable. Alokasi waktu dirancang untuk menghasilkan kualitas tinggi: testing hardware yang matang, UAT yang menyeluruh, dan dokumentasi lengkap — tanpa mengorbankan kesehatan developer atau kualitas deliverable.

---

## Timeline Overview

```
Bulan 1 (Minggu 1-4):   [PHASE 1 — FOUNDATION + BACKEND CORE]
Bulan 2 (Minggu 5-8):   [PHASE 2 — HARDWARE DAEMONS + FRONTEND SPA]
Bulan 3 (Minggu 9-12):  [PHASE 3 — WORKERS + SETTLEMENT + DEPLOYMENT + UAT]
```

---

## Phase 1: Foundation & Backend Core (Bulan 1 — Minggu 1–4)

| Minggu | Modul | Detail | Estimasi Jam |
|--------|-------|--------|--------------|
| 1–2 | Project Scaffold + DB | Monorepo, Docker Compose, all SQLAlchemy models, Alembic migrations | 32 |
| 2–3 | Shared + Auth + API Skeleton | config.py, redis.py, events.py, JWT httpOnly cookies, middleware, FastAPI factory | 32 |
| 3–4 | Parking Transaction API + Gate Flow | CRUD, barcode CODE39, plate lookup, tariff calc, gate-in/out logic | 32 |
| 4 | E-Money + Lost Contact + Shift | Deduct result processing, balance verification, TIMEOUT verification, state machine, shift open/close | 40 |

**Subtotal Phase 1:** 136 jam (~34 jam/minggu)
**Deliverable:** Dev environment berjalan, DB migrasi lancar, auth flow tested, backend core functional
**Testing Period:** 7 hari (unit tests semua business logic, mock Redis Pub/Sub)

---

## Phase 2: Hardware Protocols, Daemons & Frontend (Bulan 2 — Minggu 5–8)

| Minggu | Modul | Detail | Estimasi Jam |
|--------|-------|--------|--------------|
| 5–6 | Frame + Compass + ENET + PASSTI | STX/LRC builder, command mapping, PASSTI command set, response parsing | 28 |
| 6 | ESC/POS Protocol | Thermal printer commands, barcode, cut, status query | 12 |
| 6–7 | Gate-In + Gate-Out Daemon | Sensor loop, card_read event, ticket print, gate coordination, exit flow | 32 |
| 7–8 | E-Money Reader Daemon | Serial I/O, deduct retry, LOST_CONTACT handling, GetLastTransaction verification | 28 |
| 5–6 | Frontend Scaffold + Auth + POS | Nuxt 3, Element Plus, Pinia, login, silent refresh, transaction search, fee display | 24 |
| 7–8 | EmoneyPayment.vue + Gate-In UI | Full state machine UI, plate entry, vehicle type, CRUD | 24 |
| 8 | Admin Settings + Device Mgmt | 6 tabs settings, 5 tabs device (termasuk E-Money Readers), member CRUD | 24 |

**Subtotal Phase 2:** 172 jam (~43 jam/minggu)
**Testing Period:** 10 hari (mock serial/TCP, protocol fuzzing, daemon integration, Vue Test Utils)

---

## Phase 3: Workers, Settlement, Deployment & UAT (Bulan 3 — Minggu 9–12)

| Minggu | Modul | Detail | Estimasi Jam |
|--------|-------|--------|--------------|
| 9 | Reports + Notifications + WebSocket | E-money breakdown, snapshot gallery, settlement status, WS reconnect | 24 |
| 9–10 | ARQ Workers + Print/Snapshot | Worker config, ESC/POS ticket, camera fetch, push dispatch | 24 |
| 10–11 | Settlement Worker + UI + Unresolved | Daily 02:00 generation, file format, download, bank response upload, LOST_CONTACT admin view | 32 |
| 11 | Shift Snapshot + Polish | Per-shift per-card-type aggregation, extra polish | 16 |
| 11–12 | Docker + systemd + Nginx + Security | Multi-service compose, 5 systemd services, reverse proxy, WS headers, JWT rotation, Fernet keys | 24 |
| 12 | Hardware Staging + UAT | Deploy ke staging hardware, end-to-end flow validation, guided UAT, bug fixes | 24 |

**Subtotal Phase 3:** 144 jam (~36 jam/minggu)
**Testing Period:** 14 hari (UAT, performance validation, security review, hardware integration final check)

---

## Resource Allocation

| Role | Jumlah | Catatan |
|------|--------|---------|
| **Full-Stack Developer** | **1** | Handle semua layer: backend, frontend, hardware, deployment |
| Klien / Operator | — | Perlu available untuk UAT dan feedback milestone |

**Workload:**
- **Hari kerja:** Senin–Sabtu (6 hari/minggu)
- **Jam kerja:** 8–10 jam/hari (fokus, sustainable)
- **Total estimasi:** ~452 jam development + ~100 jam testing/UAT/deployment = **~552 jam total**

---

## Pricing Detail

| Item | Keterangan | Biaya (IDR) |
|------|------------|-------------|
| Development Fee | ~552 jam @ rate standar | Rp 10.000.000 |
| Hardware Integration | 2 cycle staging, debugging perangkat keras | Rp 2.000.000 |
| Testing & QA | Unit test, integration test, E2E, UAT support | Rp 1.500.000 |
| Deployment & Docs | systemd, Nginx, dokumentasi, operator manual | Rp 500.000 |
| **TOTAL** | | **Rp 14.000.000** |

**Pembayaran:**
- 30% down payment di awal project — Rp 4.200.000
- 30% mid payment saat backend core + daemons functional — Rp 4.200.000
- 40% final payment saat UAT selesai & production deploy — Rp 5.600.000

---

## Support & Warranty

- **Full support** — termasuk maintenance dan bug fixes selama masa pengembangan
- **Future feature requests** — tidak dikenakan biaya tambahan
- **Warranty** — 30 hari post-deployment untuk bug fixes

---

## Keunggulan Standard Track

1. **Kualitas Terjamin** — Waktu testing 30+ hari untuk menangkap edge cases
2. **Hardware Matang** — 2 cycle staging dengan perangkat keras nyata
3. **Pace Sustainable** — 8–10 jam/hari, tidak mengorbankan kualitas
4. **Dokumentasi Lengkap** — API docs, deployment guide, operator manual
5. **UAT Nyaman** — Klien punya waktu 1+ minggu untuk UAT tanpa terburu-buru
6. **Buffer Fleksibel** — Buffer 3–5 hari untuk unforeseen issues

---

## Risiko & Mitigasi

| Risiko | Mitigasi |
|--------|----------|
| Klien slow response | SLA feedback 48 jam dalam SOW |
| Hardware delay | Buffer 1 minggu di akhir, mock testing berjalan paralel |
| Scope creep | Freeze fitur di minggu 6, perubahan di-quote terpisah |
| Force majeure | Commit harian ke GitHub, dokumentasi progress mingguan, buffer waktu |

---

*Dokumen ini merupakan roadmap internal untuk pengembangan E-Parking System v2. Penawaran resmi untuk klien ada di `OFFER_SUMMARY.md`.*
