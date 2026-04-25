# E-Parking System v2 — Slow Track Roadmap (Alternative)
> ⚠️ **NOT STANDARD OFFER** — Available by special request only  
> **Pace:** Part-Time & Flexible | **Timeline:** 6 Bulan (24 Minggu) | **Budget:** Rp 8.000.000

---

## Executive Summary

> **Standard offer:** 3 bulan @ Rp 14.000.000 — lihat `ROADMAP_MEDIUM.md` dan `OFFER_SUMMARY.md`

Timeline **alternatif part-time** untuk klien dengan budget terbatas atau sistem lama yang masih berfungsi. Pengembangan fleksibel dengan alokasi waktu yang bisa disesuaikan.

---

## Timeline Overview

```
Bulan 1–2 (Minggu 1-8):   [PHASE 1 — FOUNDATION + BACKEND CORE]
Bulan 3–4 (Minggu 9-16):   [PHASE 2 — HARDWARE PROTOCOLS + FRONTEND SPA]
Bulan 5–6 (Minggu 17-24):  [PHASE 3 — WORKERS + SETTLEMENT + DEPLOYMENT + UAT]
```

---

## Phase 1: Foundation & Backend Core (Bulan 1–2 — Minggu 1–8)

| Minggu | Modul | Detail | Estimasi Jam |
|--------|-------|--------|--------------|
| 1–2 | Project Scaffold + DB | Monorepo, Docker Compose dev, pyproject.toml, all SQLAlchemy async models, Alembic migrations, seed data | 32 |
| 2–4 | Shared Utilities + Auth + API Skeleton | config.py, redis.py, events.py, JWT httpOnly cookies, middleware, role guards, FastAPI factory, routes, exception handlers | 32 |
| 4–6 | Parking Transaction API + Gate Flow | CRUD, barcode CODE39, plate lookup, tariff calc, gate-in/out logic, transaction matching, fee calculation | 32 |
| 6–8 | E-Money + Lost Contact + Shift + Member | Deduct result processing, balance verification, TIMEOUT verification, state machine correction, shift open/close, member CRUD, area & tariff | 40 |

**Subtotal Phase 1:** 136 jam (17 jam/minggu)
**Deliverable:** Dev environment berjalan, DB migrasi lancar, auth flow tested, backend core functional
**Testing Period:** 10 hari (spread across weekends)

---

## Phase 2: Hardware Protocols, Daemons & Frontend (Bulan 3–4 — Minggu 9–16)

| Minggu | Modul | Detail | Estimasi Jam |
|--------|-------|--------|--------------|
| 9–10 | Frame + Compass + ENET + PASSTI | STX/LRC builder, command mapping, PASSTI command set | 24 |
| 10–11 | ESC/POS + Gate-In Daemon | Thermal printer commands, sensor loop, card_read event, gate coordination | 20 |
| 11–12 | Gate-Out + E-Money Reader Daemon | Exit sensor, barcode scan, serial I/O, deduct retry, LOST_CONTACT handling | 28 |
| 12–14 | Frontend Scaffold + Auth + POS | Nuxt 3 setup, Element Plus, login, silent refresh, transaction search, fee display | 24 |
| 14–15 | EmoneyPayment.vue + Gate-In UI | Full state machine UI, plate entry, vehicle type selection | 20 |
| 15–16 | Admin + Device + Members + Reports | 6 tabs settings, 5 tabs device, member CRUD, group management, e-money breakdown, snapshot gallery | 32 |

**Subtotal Phase 2:** 148 jam (~19 jam/minggu)
**Testing Period:** 14 hari (mock serial/TCP, virtual port testing, Vue Test Utils, manual testing)

---

## Phase 3: Workers, Settlement, Deployment & UAT (Bulan 5–6 — Minggu 17–24)

| Minggu | Modul | Detail | Estimasi Jam |
|--------|-------|--------|--------------|
| 17–18 | ARQ Workers + Print/Snapshot | Worker config, ESC/POS ticket, camera fetch, push dispatch | 20 |
| 18–19 | Settlement Worker + UI | Daily 02:00 generation, file format, download, bank response upload | 20 |
| 19–20 | Reports + Unresolved + Shift Snapshot | Card type breakdown, LOST_CONTACT admin view, per-shift aggregation | 16 |
| 20–22 | Docker + systemd + Nginx + Security | Multi-service compose, 5 systemd services, reverse proxy, WS headers, JWT rotation, Fernet keys | 20 |
| 22–23 | Hardware Staging | Deploy ke staging hardware, end-to-end flow validation | 16 |
| 23–24 | UAT + Bugfix + Documentation | Guided UAT, bug fixes, OpenAPI docs, operator manual | 20 |
| 24 | Buffer & Gradual Rollout | Extra buffer, phased rollout support, training operator | 8 |

**Subtotal Phase 3:** 120 jam (~15 jam/minggu)
**Testing Period:** 14+ hari (extended UAT, gradual rollout)

---

## Resource Allocation

| Role | Jumlah | Catatan |
|------|--------|---------|
| **Full-Stack Developer** | **1** | Handle semua layer: backend, frontend, hardware, deployment |
| Klien / Operator | — | Perlu available untuk testing dan UAT |

**Workload:**
- **Hari kerja:** 3–5 hari/minggu (fleksibel)
- **Jam kerja:** 4–6 jam/hari (part-time)
- **Total estimasi:** ~404 jam development + ~80 jam testing/UAT/deployment = **~484 jam total**

---

## Pricing Detail

| Item | Keterangan | Biaya (IDR) |
|------|------------|-------------|
| Development Fee | ~484 jam @ rate part-time | Rp 5.500.000 |
| Hardware Integration | 1 cycle staging, remote support | Rp 1.500.000 |
| Testing & Deployment | Basic testing, UAT support, deployment guide | Rp 800.000 |
| Extended Support | 1 bulan warranty + gradual rollout assistance | Rp 200.000 |
| **TOTAL** | | **Rp 8.000.000** |

**Pembayaran:**
- 20% di awal (Rp 1.600.000)
- 20% akhir bulan 2 — foundation + backend core (Rp 1.600.000)
- 20% akhir bulan 4 — frontend complete (Rp 1.600.000)
- 20% akhir bulan 5 — hardware + settlement (Rp 1.600.000)
- 20% saat UAT selesai (Rp 1.600.000)

---

## Keunggulan Slow Track

1. **Biaya Terendah** — Pilihan paling ekonomis untuk klien dengan budget terbatas
2. **Fleksibel** — Bisa di-pause jika ada komitmen lain
3. **Pace Santai** — Sustainable untuk jangka panjang
4. **Learning Opportunity** — Waktu lebih banyak untuk eksplorasi teknologi
5. **Rollout Bertahap** — Bisa deploy modul per modul, tidak harus big-bang

---

## Risiko Slow Track

| Risiko | Mitigasi |
|--------|----------|
| Konteks switching | Dokumentasi harian singkat, commit message yang jelas |
| Scope creep akibat timeline panjang | Milestone-based payment, freeze fitur per milestone |
| Teknologi outdated saat selesai | Gunakan LTS/stable versions, update minor dependencies rutin |
| Klien kehilangan enthusiasm | Monthly demo, progress report visual, milestone celebration |
| Klien lupa requirement awal | Document requirement di awal, sign-off per milestone |

---

*Dokumen ini merupakan roadmap alternatif. Penawaran standard adalah 3 bulan @ Rp 14.000.000.*
