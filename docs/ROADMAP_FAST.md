# E-Parking System v2 — Fast Track Roadmap (Alternative)
> ⚠️ **NOT STANDARD OFFER** — Available by special request only  
> **Pace:** Maximum Speed | **Timeline:** 1 Bulan (4 Minggu) | **Budget:** Rp 22.000.000

---

## Executive Summary

> **Standard offer:** 3 bulan @ Rp 14.000.000 — lihat `ROADMAP_MEDIUM.md` dan `OFFER_SUMMARY.md`

Timeline **alternatif ekstrem** untuk situasi deadline sangat ketat. Pengembangan super intensif dengan scope dikompresi ke MVP. Fitur non-kritis diiterasi setelah go-live.

---

## Timeline Overview

```
Minggu 1:   [PHASE 1 — FOUNDATION + BACKEND CORE + HARDWARE PROTOCOLS]
Minggu 2:   [PHASE 2 — BACKEND COMPLETE + DAEMONS + FRONTEND SCAFFOLD]
Minggu 3:   [PHASE 3 — FRONTEND COMPLETE + WORKERS + SETTLEMENT]
Minggu 4:   [PHASE 4 — INTEGRATION + DEPLOYMENT + UAT]
```

---

## Phase 1: Foundation, Backend Core & Hardware Protocols (Minggu 1)

| Hari | Modul | Detail | Estimasi Jam |
|------|-------|--------|--------------|
| 1–2 | Project Scaffold + DB | Monorepo, Docker Compose, all SQLAlchemy async models, Alembic migrations, seed data | 24 |
| 2–3 | Shared + Auth + API Skeleton | config.py, redis.py, events.py, JWT httpOnly cookies, middleware, FastAPI factory | 20 |
| 3–5 | Parking Transaction API + Gate Flow | CRUD, barcode CODE39, plate lookup, tariff calc, gate-in/out logic | 24 |
| 5–7 | E-Money + Lost Contact | Deduct result processing, TIMEOUT verification, state machine correction | 20 |
| 5–7 | Frame + Compass + ENET + PASSTI | STX/LRC builder, command mapping, PASSTI command set, response parsing | 20 |

**Subtotal Phase 1:** 108 jam (~15 jam/hari)

---

## Phase 2: Daemons & Frontend Scaffold (Minggu 2)

| Hari | Modul | Detail | Estimasi Jam |
|------|-------|--------|--------------|
| 8–10 | ESC/POS + Gate-In/Out Daemon | Thermal printer commands, sensor loop, card_read event, gate coordination, exit flow | 28 |
| 10–12 | E-Money Reader Daemon | Serial I/O, deduct retry, LOST_CONTACT handling, GetLastTransaction verification | 24 |
| 10–12 | Frontend Scaffold + Auth + POS | Nuxt 3 setup, Element Plus, Pinia, login, silent refresh, transaction search, fee display | 28 |
| 12–14 | EmoneyPayment.vue + Gate-In UI | Full state machine UI, plate entry, vehicle type, CRUD | 24 |

**Subtotal Phase 2:** 104 jam (~15 jam/hari)

---

## Phase 3: Frontend Complete, Workers & Settlement (Minggu 3)

| Hari | Modul | Detail | Estimasi Jam |
|------|-------|--------|--------------|
| 15–17 | Admin Settings + Device Mgmt | 6 tabs settings, 5 tabs device (termasuk E-Money Readers), member CRUD | 28 |
| 17–19 | Reports + Notifications + WebSocket | E-money breakdown, snapshot gallery, settlement status, WS reconnect | 24 |
| 17–19 | ARQ Workers | Worker config, print/snapshot/notification/settlement jobs | 24 |
| 19–21 | Settlement Worker + UI | Daily 02:00 generation, file format, download, bank response upload | 24 |

**Subtotal Phase 3:** 100 jam (~14 jam/hari)

---

## Phase 4: Integration, Deployment & UAT (Minggu 4)

| Hari | Modul | Detail | Estimasi Jam |
|------|-------|--------|--------------|
| 22–24 | Unresolved + Shift Snapshot + Docker/systemd/Nginx | LOST_CONTACT admin view, per-shift aggregation, deployment config | 32 |
| 24–26 | Hardware Staging + Load Test | Deploy ke staging hardware, end-to-end validation, concurrent simulation | 24 |
| 26–28 | UAT + Bugfix + Documentation | Guided UAT, bug fixes, regression, OpenAPI docs, operator manual | 32 |

**Subtotal Phase 4:** 88 jam (~13 jam/hari)

---

## Resource Allocation

| Role | Jumlah | Catatan |
|------|--------|---------|
| **Full-Stack Developer** | **1** | Handle semua layer: backend, frontend, hardware, deployment |
| Klien / Operator | — | Perlu available untuk UAT dan testing hardware |

**Workload:**
- **Hari kerja:** Senin–Minggu (7 hari/minggu)
- **Jam kerja:** 12–14 jam/hari
- **Total estimasi:** ~400 jam development + ~60 jam testing/UAT/deployment = **~460 jam total**

> **Catatan:** Scope dikompresi ke MVP — fitur non-kritis dapat diiterasi setelah go-live.

---

## Pricing Detail

| Item | Keterangan | Biaya (IDR) |
|------|------------|-------------|
| Development Fee | ~460 jam @ rate intensif | Rp 16.000.000 |
| Hardware Integration | On-site support, debugging perangkat keras | Rp 2.500.000 |
| Overtime Intensive Premium | Weekend, jam malam, pace sangat tinggi | Rp 2.000.000 |
| Testing & Deployment | UAT support, dokumentasi, deployment, staging | Rp 1.500.000 |
| **TOTAL** | | **Rp 22.000.000** |

**Pembayaran:**
- 40% di awal (Rp 8.800.000)
- 30% saat backend + POS berfungsi (Rp 6.600.000)
- 30% saat UAT selesai & production deploy (Rp 6.600.000)

---

## Risiko Fast Track

| Risiko | Mitigasi |
|--------|----------|
| **Fatigue / health risk** | Jadwalkan micro-break setiap 2 jam; 1 hari istirahat penuh di tengah (hari 14) |
| **Sick leave = delay kritis** | Buffer 2–3 hari di akhir; klien diinformasikan risiko ini |
| **Bug terlewat** | Prioritaskan critical path (gate-in/out + e-money); fitur minor iterasi setelah live |
| **Hardware delay** | Mulai dengan mock serial/virtual port; integrasi hardware di minggu 4 |
| **Scope creep** | Freeze fitur di minggu 2; perubahan di-quote terpisah |

---

## Kapan Fast Track Tersedia?

- Deadline sangat ketat (sistem lama akan expired/break dalam 1 bulan)
- Klien sangat kooperatif (feedback dalam 12 jam)
- Hardware sudah tersedia di minggu pertama
- Developer sudah familiar dengan semua teknologi (tidak ada learning curve)
- Siap kerja 12–14 jam/hari selama 1 bulan penuh

---

*Dokumen ini merupakan roadmap alternatif. Penawaran standard adalah 3 bulan @ Rp 14.000.000.*
