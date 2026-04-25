# E-Parking System v2 — Proposal
> **Prepared for:** [Client Name]  
> **Prepared by:** [Your Name / Company]  
> **Date:** 24 April 2026  
> **Subject:** Modernization & E-Money Integration

---

## 1. Executive Summary

Your current E-Parking System (v1) has served well, but the parking industry has evolved. **Cash-only operations create bottlenecks**, **manual settlement consumes hours of admin time daily**, and the **existing architecture carries security risks** that grow costlier to fix the longer they remain.

This proposal outlines a **complete rebuild** — not just an upgrade — to a modern, secure, and fully integrated E-Parking System v2 with native **PASSTI e-money support**, **real-time architecture**, and **zero-downtime hardware coordination**.

---

## 2. The Problem: Your Current System (v1)

```
┌─────────────────────────────────────────────────────────────┐
│  BEFORE — v1 Architecture                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Nuxt 3 Frontend                                           │
│        ↕ HTTP + WebSocket                                   │
│   Laravel 11 Backend  ⚠️  Token in localStorage = XSS risk │
│        ↕ HTTP API calls (Bearer token)                      │
│   Python Daemons  ⚠️  Call backend directly = fragile      │
│        ↕ TCP/Serial                                         │
│   Physical Hardware                                         │
│                                                             │
│   Pain Points:                                              │
│   ❌ No e-money support — cash-only bottleneck             │
│   ❌ 5+ duplicate gate scripts — maintenance nightmare     │
│   ❌ Manual settlement — hours of admin work daily         │
│   ❌ Daemons die on backend restart                        │
│   ❌ Token theft vulnerability                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. The Solution: E-Parking System v2

```
┌─────────────────────────────────────────────────────────────┐
│  AFTER — v2 Architecture                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Nuxt 3 Frontend (SPA)                                     │
│        ↕ JWT httpOnly Cookies  ✅  XSS-proof               │
│        ↕ WebSocket /ws/  ✅  Native, no Pusher cost        │
│   FastAPI Backend  ✅  Async, high-performance             │
│        ↕ Redis Pub/Sub  ✅  Survives restarts              │
│   Python Daemons  ✅  Clean libraries, zero duplication    │
│        ↕ Serial | TCP | ESC/POS                            │
│   Physical Hardware + PASSTI E-Money Readers               │
│                                                             │
│   Wins:                                                     │
│   ✅ 9 e-money card types + QR Payment supported           │
│   ✅ Auto-deduct at gate-out — no operator intervention    │
│   ✅ Auto settlement file generation — bank-ready          │
│   ✅ LOST_CONTACT recovery — no hanging transactions       │
│   ✅ Runs as non-root user — principle of least privilege  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Before vs After — Feature Comparison

| Capability | v1 (Current) | v2 (Proposed) | Business Impact |
|------------|-------------|---------------|-----------------|
| **E-Money Payments** | ❌ Not supported | ✅ PASSTI full integration (9 card types + QR) | Customers pay without cash. Faster throughput, shorter queues. |
| **Auto-Deduct Gate-Out** | ❌ Manual only | ✅ Tap same card → auto-deduct, gate opens | Eliminates payment bottleneck at exit. Operators focus on exceptions only. |
| **Settlement Reporting** | ❌ Manual / none | ✅ Auto-generated bank-ready files at 02:00 daily | Admin saves hours daily. Upload-ready format reduces reconciliation errors. |
| **Lost Contact Recovery** | ❌ Transactions hang | ✅ Auto-retry + auto-correction state machine | Zero lost revenue from connection drops. Customer experience protected. |
| **Daemon Resilience** | ❌ Dies on backend restart | ✅ Redis Pub/Sub — survives independently | No more gate downtime during backend updates. |
| **Authentication Security** | ⚠️ Token in localStorage | ✅ JWT via httpOnly cookies | XSS attacks cannot steal session tokens. Compliance-ready. |
| **Hardware Protocols** | ⚠️ 5+ duplicate scripts | ✅ Single clean library per protocol | Maintenance cost drops. One fix applies everywhere. |
| **Shift Reconciliation** | By gate-in time | ✅ By gate-out + per-card-type snapshot | Accurate per-shift financial accountability. |
| **Real-Time Updates** | Pusher-dependent | ✅ Native WebSocket, no third-party cost | Lower latency, no subscription fees, full control. |

---

## 5. New Features in v2

| Feature | What It Does | Why It Matters |
|---------|-------------|----------------|
| **PASSTI E-Money Reader** | Supports LUMINOS, MANDIRI, BRIZZI, TAPCASH, FLAZZ, JAKCARD, NOBU, MEGACASH, QR_PAYMENT | One system accepts every major e-money card in Indonesia. |
| **Auto-Deduct Gate-Out** | Same card used for entry is auto-deducted on exit | Exit time drops from 30–60s to 5–10s. Queue length reduced dramatically. |
| **LOST_CONTACT Recovery** | Connection drop during payment → auto-retry + correction | No transaction ever hangs. No manual rescue needed. |
| **Settlement File Generation** | Daily auto-generated file in bank format (`yyyyMMddHHmmss{MID}{TID}...`) | Admin uploads one file. No spreadsheet work. No human error. |
| **Bank Response Tracking** | Upload .OK/.NOK files → track PENDING → ACCEPTED/REJECTED | Full visibility into settlement status. No guessing. |
| **Per-Shift E-Money Snapshot** | Report per shift, per card type: count + total amount | Operator accountability per shift. Disputes resolved with data. |
| **Unresolved Transactions View** | Admin dashboard for LOST_CONTACT / CORRECTION_FAILED | Nothing falls through cracks. Every anomaly has a resolution path. |
| **Manual Override Audit** | Every manual correction logged with note + timestamp | Full compliance trail. Auditors see exactly who did what and when. |
| **TIMEOUT Verification** | Triple-check (card + amount + counter) before confirming deduct | Fraud prevention. No double-charge risk. |
| **POS State Machine UI** | Clear visual: WAITING_CARD → PROCESSING → SUCCESS/FAILED | Operators always know system state. No confusion, no mistakes. |

---

## 6. The Offer

### Standard Package — 3 Months Full Delivery

| Item | Detail |
|------|--------|
| **Timeline** | 3 months (12 weeks) |
| **Investment** | **Rp 14.000.000** |
| **Scope** | Full v2 system: backend, frontend, hardware daemons, workers, deployment |
| **Support** | **Full support included** — any future feature requests at **no additional charge** |
| **Warranty** | 30 days post-deployment bug fixes |

### What's Included

✅ Full source code ownership (MIT license)  
✅ PostgreSQL database design + Alembic migrations  
✅ FastAPI async backend  
✅ Nuxt 3 frontend SPA with Element Plus  
✅ Hardware protocol libraries (compass, enet, passti, escpos, frame)  
✅ 3 hardware daemons (gate_in, gate_out, emoney_reader)  
✅ 4 ARQ background workers (print, snapshot, settlement, notification)  
✅ Redis Pub/Sub IPC between backend and daemons  
✅ Native WebSocket real-time updates  
✅ JWT authentication with httpOnly cookies  
✅ Docker Compose development environment  
✅ Production deployment config (systemd + Nginx)  
✅ Unit & integration test suites  
✅ API documentation (OpenAPI/Swagger)  
✅ Operator manual & deployment guide  

### What's Not Included

❌ Hardware procurement (gate controllers, PASSTI readers, printers, cameras, sensors)  
❌ Cloud hosting / VPS subscription  
❌ SSL certificates  
❌ SMS gateway service  
❌ Mobile app (iOS/Android)  
❌ Data migration from v1 (available as separate engagement)  

---

## 7. Payment Terms

| Milestone | Timing | Amount | Percentage |
|-----------|--------|--------|------------|
| **Down Payment** | Project kickoff | Rp 4.200.000 | 30% |
| **Mid Payment** | Backend core + daemons functional | Rp 4.200.000 | 30% |
| **Final Payment** | UAT complete + production deployment | Rp 5.600.000 | 40% |
| **TOTAL** | | **Rp 14.000.000** | **100%** |

---

## 8. 3-Month Delivery Timeline

```
Bulan 1 (Minggu 1–4)     ████████████████████   Foundation + Backend Core
                          • Project scaffold, DB, auth
                          • Parking transactions, gate flow
                          • E-money logic, shift management

Bulan 2 (Minggu 5–8)      ████████████████████   Hardware + Frontend
                          • Protocol libraries (PASSTI, ESC/POS, ENET)
                          • Gate-in/out + e-money daemons
                          • Nuxt 3 frontend, POS UI, admin dashboard

Bulan 3 (Minggu 9–12)     ████████████████████   Workers + Deployment + UAT
                          • ARQ workers (print, snapshot, settlement)
                          • Settlement UI & reporting
                          • Docker/systemd/Nginx production setup
                          • Hardware staging, UAT, documentation
```

**UAT Window:** 1+ minggu untuk klien melakukan acceptance testing tanpa terburu-buru.

---

## 9. Why This Matters — The Numbers

| Metric | v1 (Current) | v2 (After) | Improvement |
|--------|-------------|------------|-------------|
| Exit transaction time | 30–60 seconds | 5–10 seconds | **~80% faster** |
| Daily settlement prep | 1–2 hours manual | 5 minutes upload | **~95% time saved** |
| Hardware downtime on update | Full restart required | Zero downtime | **100% uptime** |
| Security audit risk | High (XSS, root execution) | Low (httpOnly, non-root) | **Risk eliminated** |
| E-money card support | 0 types | 9+ types + QR | **Full coverage** |

---

## 10. Next Steps

1. **Review & approve** this proposal
2. **Sign SOW** (Statement of Work) with milestones and payment terms
3. **Hardware inventory** — confirm available devices or procurement timeline
4. **Access provisioning** — repository, staging environment, VPN (if needed)
5. **Kickoff meeting** — align communication cadence and demo schedule

---

## 11. Contact

| | |
|---|---|
| **Developer** | [Your Name] |
| **Company** | [Your Company / Freelance] |
| **Location** | Indonesia |
| **Email** | [your@email.com] |
| **Phone** | [+62 ...] |
| **Stack** | FastAPI, SQLAlchemy, Nuxt 3, Vue 3, Python, PostgreSQL, Redis |

---

*This proposal is valid for 30 days from the date of issue.*

*Generated: 24 April 2026*
