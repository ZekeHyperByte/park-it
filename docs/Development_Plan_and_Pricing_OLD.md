# E-Parking System v2 — Development Plan & Pricing

> Based on: EParking_System_v2_Design.docx (Sections 1–5 Locked)

---

## Executive Summary

This document outlines a realistic development plan for the E-Parking System v2, a comprehensive parking management solution integrating FastAPI backend, Nuxt 3 frontend, hardware controllers (gates, e-money readers, printers, cameras), and real-time communication via Redis Pub/Sub and WebSockets.

**Total Estimated Scope:** ~2,500–3,000 engineering hours (full implementation)

---

## 1. Workload Breakdown by Phase

### Phase 1: Foundation & Infrastructure (Weeks 1–2)

| Module | Tasks | Est. Hours | Testing Focus |
|--------|-------|------------|---------------|
| Project Scaffolding | Monorepo setup, pyproject.toml, dependency layers, Docker Compose dev environment | 24h | Build verification, dependency resolution |
| Database Layer | SQLAlchemy async models (all 20+ tables), Alembic migrations, initial seed data | 40h | Migration roll-forward/rollback, model constraints, foreign keys |
| Shared Utilities | `config.py` (pydantic-settings), `redis.py` (client + pub/sub helpers), `logging.py`, `events.py` (Pydantic IPC schemas) | 24h | Config validation, Redis connectivity, event serialization round-trip |
| Auth Foundation | JWT httpOnly cookie flow, login/logout/refresh, password hashing, middleware, role-based guards | 24h | Cookie security headers, token expiry, role access matrix, XSS prevention |
| API Skeleton | FastAPI app factory, route registration, exception handlers, CORS, health checks | 16h | Endpoint discovery, CORS preflight, error format consistency |
| **Phase 1 Total** | | **128h** | |

**Testing Period:** 3 days (integration tests for auth flow, migration dry-run on fresh DB)

---

### Phase 2: Backend Core — Parking & Transactions (Weeks 3–5)

| Module | Tasks | Est. Hours | Testing Focus |
|--------|-------|------------|---------------|
| Parking Transaction API | CRUD, barcode generation (CODE39), plate lookup, status lifecycle | 32h | CRUD operations, barcode uniqueness, status transitions |
| Gate-In Logic | Vehicle detection handler, ticket vs. e-money mode, transaction creation with partial unique index enforcement | 24h | Concurrent card tap simulation, unique constraint validation |
| Gate-Out Logic | Transaction matching (card_number / barcode / plate), fee calculation, shift assignment by gate_out_time | 32h | Matching accuracy, cross-shift rules, fee edge cases |
| E-Money Transaction API | Deduct result processing, EmoneyTransaction CRUD, balance verification, TIMEOUT verification logic | 40h | Timeout simulation, deduct result state machine, balance validation |
| Lost Contact Correction | State machine implementation (NORMAL → LOST_CONTACT → AUTO_CORRECTION → CORRECTION_FAILED), manual override | 24h | State transition coverage, manual override audit trail |
| Shift & Reconciliation | Shift open/close, operator attendance, snapshot generation per card_type | 24h | Shift boundary calculations, snapshot aggregation accuracy |
| Member & Vehicle Management | Member CRUD, vehicle linking, renewal tracking, group pricing | 24h | Renewal date logic, group discount calculations |
| Area & Tariff Configuration | Zone management, vehicle type pricing, dynamic tariff rules | 16h | Tariff calculation edge cases, zone capacity |
| **Phase 2 Total** | | **216h** | |

**Testing Period:** 5 days (unit tests for all business logic, integration tests for gate in/out flows, mock Redis Pub/Sub)

---

### Phase 3: Hardware Protocols & Daemons (Weeks 5–7)

| Module | Tasks | Est. Hours | Testing Focus |
|--------|-------|------------|---------------|
| Frame Protocol (`frame.py`) | STX/LRC frame builder/parser, checksum validation, byte stuffing | 16h | Frame integrity, corruption detection, edge cases (empty payload, max size) |
| Compass Protocol | Gate controller command/response mapping (open/close/sensor/status) | 16h | Command encoding, response parsing, error code handling |
| ENET Protocol | ENET controller integration, TCP socket management, heartbeat | 16h | TCP reconnection, heartbeat timeout, command retry |
| PASSTI Protocol | E-money reader command set (INIT, DEDUCT, GET_LAST_TRANSACTION, CANCEL_CORRECTION), response parsing | 40h | Command sequence correctness, response field extraction, encryption handling |
| ESC/POS Protocol | Thermal printer command generation (text, barcode, cut, buzzer), printer status query | 16h | Byte stream correctness, barcode formatting, error status |
| Gate-In Daemon (`gate_in.py`) | IN1/IN2/IN3 sensor loop, card_read event publishing, ticket print command, gate open/close coordination | 32h | Sensor state machine simulation, event timing, gate safety logic |
| Gate-Out Daemon (`gate_out.py`) | Exit sensor handling, barcode scan integration, gate control, display updates | 24h | Exit flow coordination, display message timing |
| E-Money Reader Daemon (`emoney_reader.py`) | Serial port I/O, PASSTI command orchestration, deduct retry logic, LOST_CONTACT handling, GetLastTransaction verification | 48h | Serial timeout simulation, deduct retry exhaustion, LOST_CONTACT → correction flow |
| **Phase 3 Total** | | **224h** | |

**Testing Period:** 7 days (unit tests with mocked serial/TCP, protocol fuzzing, daemon integration with FastAPI via Redis)

---

### Phase 4: Frontend — Nuxt 3 SPA (Weeks 6–9)

| Module | Tasks | Est. Hours | Testing Focus |
|--------|-------|------------|---------------|
| Frontend Scaffold | Nuxt 3 setup, Element Plus integration, Pinia stores, $fetch config with credentials, Vue Router guards | 24h | Build output, route guards, store hydration |
| Auth Pages | Login.vue, silent refresh interceptor, logout, role-based navigation | 16h | Cookie handling, 401 interception, role redirect |
| POS / Gate-Out Screen | Transaction search (barcode/plate), fee display, payment method selection, gate control buttons, camera snapshot | 40h | Search accuracy, fee display correctness, gate command confirmation |
| EmoneyPayment.vue | Full state machine UI (WAITING_CARD → PROCESSING → LOST_CONTACT → WRONG_CARD → INSUFFICIENT → SUCCESS/FAILED), cancel/retry/override actions | 32h | State transition rendering, WebSocket event handling, user action feedback |
| Gate-In Screen | Plate entry, vehicle type selection, gate selection, transaction creation | 16h | Form validation, gate availability, duplicate prevention |
| Transactions Page | Transaction CRUD, ManualOpenLog audit, filtering, export | 24h | Filter performance, audit trail completeness |
| Admin Settings | 6 tabs: General, Vehicle Types, Users, Shifts, Areas, Backup — CRUD for each | 40h | CRUD operations, form validation, backup/restore |
| Device Management | 5 tabs: Cameras, Printers, POS, Gate Out, Gate In, E-Money Readers — device pairing, status monitoring, test actions | 32h | Device connectivity status, test command feedback |
| Members Page | Member CRUD, group management, renewals, income reports | 24h | Renewal calculations, report accuracy |
| Reports & Notifications | Date-range reports, e-money breakdown, snapshot gallery, attendance logs, settlement status, unresolved transactions | 32h | Report data accuracy, date range boundaries, filter combinations |
| WebSocket Plugin | Connection management, exponential backoff reconnect, heartbeat, disconnection indicator | 16h | Reconnect behavior, message ordering, connection leak prevention |
| **Phase 4 Total** | | **296h** | |

**Testing Period:** 7 days (component tests with Vue Test Utils, E2E with Playwright for critical paths: login → gate-in → gate-out → payment)

---

### Phase 5: Settlement, Workers & Advanced Features (Weeks 8–10)

| Module | Tasks | Est. Hours | Testing Focus |
|--------|-------|------------|---------------|
| ARQ Worker Setup | Worker configuration, job registration, retry policies, dead letter handling | 16h | Job enqueue/dequeue, retry exhaustion, worker crash recovery |
| Print Worker (`print.py`) | Ticket receipt generation (ESC/POS), ARQ job processing, printer error handling | 16h | ESC/POS byte stream verification, printer offline retry |
| Snapshot Worker (`snapshot.py`) | Camera HTTP fetch, image storage, ARQ job processing | 16h | HTTP timeout, image format validation, storage path |
| Settlement Worker (`settlement.py`) | Daily scheduled settlement generation (02:00), file format (yyyyMMddHHmmss{MID}{TID}{version}{batch}.txt), batch limits (999 txns) | 24h | File format compliance, batch splitting, date boundary correctness |
| Notification Worker (`notification.py`) | Push/email notification generation, queue-based dispatch | 16h | Notification delivery, template rendering |
| Settlement UI | Download generated files, upload bank response (.OK/.NOK), status tracking (PENDING → UPLOADED → ACCEPTED/REJECTED) | 16h | File upload validation, status transition accuracy |
| E-Money Reports | Card type breakdown, date range filtering, settlement status filtering, export to Excel/PDF | 16h | Aggregation accuracy, filter combination correctness |
| Unresolved Transactions | Admin view for LOST_CONTACT/CORRECTION_FAILED, manual override workflow, correction note recording | 16h | Filtering by status, override audit trail |
| Shift E-Money Snapshot | Per-shift, per-card-type aggregation, report generation, shift lock enforcement | 16h | Aggregation math, shift lock after close |
| **Phase 5 Total** | | **168h** | |

**Testing Period:** 5 days (ARQ job integration tests, settlement file verification against spec, snapshot storage)

---

### Phase 6: Deployment, Performance & UAT (Weeks 10–12)

| Module | Tasks | Est. Hours | Testing Focus |
|--------|-------|------------|---------------|
| Docker Compose Production | Multi-service compose, volume management, network isolation, secrets | 16h | Service startup order, network connectivity, volume persistence |
| systemd Services | 5 service definitions (api, worker, 3 daemons), user/dialout permissions, logrotate | 16h | Service restart behavior, log rotation, permission correctness |
| Nginx Configuration | Reverse proxy, WebSocket upgrade headers, SSL termination, proxy_read_timeout 3600s, static file serving | 16h | WS keepalive, SSL handshake, static asset caching |
| Environment & Secrets | JWT_SECRET_KEY rotation, EMONEY_INIT_KEY_SECRET Fernet generation, DB credentials, .env templates | 8h | Key rotation procedure, secret injection |
| Load Testing | Concurrent gate-in/out simulation, Redis Pub/Sub saturation, WebSocket connection limits | 16h | Throughput benchmarks, connection stability, memory leaks |
| Security Audit | Cookie security, JWT library review (PyJWT), dependency CVE scan, serial port permission audit | 16h | Penetration test basics, CVE database scan |
| Hardware Staging | Deploy to staging hardware (gate controllers, e-money reader, printer), end-to-end flow validation | 32h | Real sensor integration, printer output verification, card tap timing |
| Documentation | API docs (OpenAPI), deployment guide, operator manual, troubleshooting runbook | 24h | Doc completeness, accuracy against implementation |
| User Acceptance Testing (UAT) | Guided UAT with operators, bug fixes, regression testing, sign-off | 40h | UAT checklist coverage, bug fix verification |
| **Phase 6 Total** | | **184h** | |

**Testing Period:** 10 days (UAT, performance validation, security review, hardware integration final check)

---

## 2. Timeline Summary

| Phase | Duration | Cumulative | Testing Period | Deliverables |
|-------|----------|------------|----------------|--------------|
| 1. Foundation | 2 weeks | Week 2 | 3 days | Dev environment, DB schema, auth, API skeleton |
| 2. Backend Core | 3 weeks | Week 5 | 5 days | Parking transactions, e-money logic, shift mgmt |
| 3. Hardware/Daemons | 2 weeks | Week 7 | 7 days | Protocols, 3 daemons, hardware IPC |
| 4. Frontend | 3 weeks | Week 9 | 7 days | Nuxt 3 SPA, POS, admin, WebSockets |
| 5. Settlement/Workers | 2 weeks | Week 10 | 5 days | ARQ workers, settlement, reports |
| 6. Deploy/UAT | 2 weeks | Week 12 | 10 days | Production deploy, load test, UAT sign-off |
| **Total** | **14 weeks** | | **~37 days** | |

> **Note:** Phases 2–5 have overlap (frontend can begin once backend API contracts are stable ~week 4). Hardware daemon development can begin once protocol specs are finalized ~week 3. This overlap is accounted for in the cumulative timeline.

---

## 3. Resource Requirements

### Team Composition (Standard)

| Role | Count | Responsibilities |
|------|-------|----------------|
| Senior Backend Engineer | 1 | FastAPI architecture, business logic, database design, review |
| Mid Backend Engineer | 1 | API endpoints, ARQ workers, testing, documentation |
| Senior Frontend Engineer | 1 | Nuxt 3 architecture, POS state machine, WebSocket integration |
| Mid Frontend Engineer | 1 | UI components, admin pages, reports, testing |
| Hardware/IoT Engineer | 1 | Protocol implementation, daemon development, hardware staging |
| DevOps Engineer | 0.5 | Docker, systemd, Nginx, deployment scripts (shared across projects) |
| QA Engineer | 0.5 | Test planning, automation, UAT coordination (ramping up in Phase 4) |
| Project Manager | 0.25 | Client communication, sprint planning, status reporting |

**Total FTE:** ~5.25 engineers

---

## 4. Pricing Options

Pricing is based on:
- Estimated engineering hours (1,216h development + ~300h testing/QA + ~200h management/buffer = ~1,716h total)
- Team composition and seniority
- Urgency multiplier (fast-track requires overtime, weekend work, and opportunity cost)
- Hardware integration complexity (requires specialist expertise)

### Option A: Fast Track — Maximum Priority (24/7 Development)

**Timeline:** 1 month (4 weeks — 24/7 rotating shifts, parallel workstreams)

**Approach:**
- Two fully dedicated teams working in rotating shifts (day/night) for continuous development
- All phases run in parallel where possible (backend + frontend + hardware simultaneously)
- Daily client sync, immediate feedback loops
- Overtime and weekend work expected
- Requires immediate access to hardware for staging (shipped to dev team or on-site setup in days 1–3)

**Team:**
- 2× Senior Backend Engineers (rotating)
- 2× Senior Frontend Engineers (rotating)
- 1× Hardware/IoT Engineer (dedicated)
- 1× DevOps Engineer (dedicated)
- 1× QA Engineer (dedicated, night shift testing)
- 1× Project Manager (dedicated)

**Pricing:**

| Item | Details | Cost (USD) |
|------|---------|------------|
| Development (1,716h @ premium rate) | 24/7 shifts, overtime, weekend multiplier | $95,000 |
| Hardware Integration Premium | Specialist on-call, immediate hardware support | $12,000 |
| Infrastructure & DevOps | Dedicated staging environment, CI/CD, monitoring setup | $8,000 |
| UAT Acceleration | Compressed UAT window, on-site support if needed | $5,000 |
| Risk Buffer (10%) | Contingency for scope adjustments | $12,000 |
| **Total** | | **$132,000** |

**Payment Schedule:**
- 40% upfront ($52,800)
- 30% at midpoint — backend API + frontend POS functional ($39,600)
- 30% at delivery — UAT signed off, production deployed ($39,600)

---

### Option B: Medium Track — Balanced Speed (Standard Pace with Focus)

**Timeline:** 3 months (12 weeks — business hours + moderate overtime)

**Approach:**
- Single dedicated team working standard hours with 1–2 planned overtime sprints
- Phases overlap strategically (frontend starts after backend contract freeze)
- Weekly client demos, bi-weekly milestone reviews
- Hardware staging in week 8–9 (allows buffer for procurement/delivery)
- 1+ week UAT window included

**Team:**
- 1× Senior Backend Engineer
- 1× Mid Backend Engineer
- 1× Senior Frontend Engineer
- 1× Mid Frontend Engineer
- 1× Hardware/IoT Engineer
- 0.5× DevOps Engineer
- 0.5× QA Engineer (ramping to 1.0 in Phase 4)
- 0.25× Project Manager

**Pricing:**

| Item | Details | Cost (USD) |
|------|---------|------------|
| Development (1,716h @ standard rate) | Business hours, focused sprints | $58,000 |
| Hardware Integration | Standard hardware support, 2 staging cycles | $6,000 |
| Infrastructure & DevOps | Shared staging, standard CI/CD | $4,000 |
| UAT & Support | Standard 1+ week UAT, remote support | $3,000 |
| Risk Buffer (8%) | Contingency for scope adjustments | $5,680 |
| **Total** | | **$76,680** |

**Payment Schedule:**
- 30% upfront ($23,004)
- 25% at Phase 3 complete — backend core + daemons functional ($19,170)
- 25% at Phase 5 complete — frontend complete, settlement working ($19,170)
- 20% at delivery — UAT signed off ($15,336)

---

### Option C: Slow Track — Extended Timeline (Part-Time / Relaxed)

**Timeline:** 6 months (24 weeks — part-time allocation, shared resources)

**Approach:**
- Small team working part-time or with significant gaps between sprints
- Shared resources (engineers may be allocated to other projects simultaneously)
- Monthly client reviews, flexible milestone dates
- Hardware integration scheduled after significant development buffer
- Extended UAT window (2+ weeks), gradual rollout support
- Best suited for: budget-constrained projects, non-urgent replacements, or teams with internal capacity to supplement

**Team:**
- 1× Backend Engineer (0.6 FTE)
- 1× Frontend Engineer (0.6 FTE)
- 1× Hardware/IoT Engineer (0.4 FTE, as needed)
- 0.25× DevOps Engineer (as needed)
- 0.25× QA Engineer (sporadic)
- 0.1× Project Manager (monthly check-ins)

**Pricing:**

| Item | Details | Cost (USD) |
|------|---------|------------|
| Development (stretched over 6 months) | Part-time rates, shared resources | $32,000 |
| Hardware Integration | As-needed support, 1 staging cycle | $3,000 |
| Infrastructure & DevOps | Minimal setup, reuse existing infrastructure | $2,000 |
| Extended UAT & Support | 2+ weeks UAT, gradual rollout assistance | $2,000 |
| Risk Buffer (5%) | Lower contingency due to flexible timeline | $1,950 |
| **Total** | | **$40,950** |

**Payment Schedule:**
- 20% upfront ($8,190)
- 20% at month 2 — foundation + DB complete ($8,190)
- 20% at month 4 — backend + frontend core complete ($8,190)
- 20% at month 5 — hardware integration + settlement complete ($8,190)
- 20% at delivery — UAT complete, 30-day warranty starts ($8,190)

---

## 5. What’s Included / Not Included

### Included in All Options
- Full source code ownership (MIT or client-preferred license)
- Database schema design + Alembic migrations
- FastAPI backend with async SQLAlchemy
- Nuxt 3 frontend SPA with Element Plus
- Hardware protocol libraries (compass, enet, passti, escpos, frame)
- 3 hardware daemons (gate_in, gate_out, emoney_reader)
- 4 ARQ workers (print, snapshot, settlement, notification)
- Redis Pub/Sub IPC implementation
- WebSocket real-time integration
- JWT auth with httpOnly cookies
- Docker Compose development environment
- systemd + Nginx production deployment configuration
- Unit and integration test suites
- API documentation (OpenAPI/Swagger)
- Operator manual and deployment guide
- 30-day warranty period (bug fixes post-deployment)

### Not Included (Available as Add-ons)
- **Hardware procurement** — Gate controllers, PASSTI readers, printers, cameras, sensors (client provides or we source at cost + 15%)
- **Cloud hosting** — VPS/cloud server costs (AWS, DigitalOcean, etc.)
- **SSL certificates** — Let's Encrypt (free) or purchased certs
- **SMS gateway** — If notification worker requires SMS (Twilio, etc.)
- **Bank SFTP integration** — Settlement auto-upload to bank (marked as "planned for future" in design doc)
- **Mobile app** — iOS/Android companion app
- **Extended warranty** — Beyond 30 days (available: $500/month)
- **On-site deployment** — Travel costs for on-site installation/training (if required)
- **Data migration** — Migrating historical data from v1 system (requires v1 schema analysis)

---

## 6. Assumptions & Risks

### Key Assumptions
1. **Hardware availability** — Client provides or procures gate controllers, e-money readers, printers, and cameras by Phase 3 start.
2. **PASSTI protocol documentation** — Full command/response specification for the specific e-money reader model is available.
3. **V1 data migration** — Not in scope unless explicitly added. Fresh start assumed.
4. **Client feedback loop** — Design decisions requiring client input receive response within 12h (Fast), 48h (Medium), 1 week (Slow).
5. **Single deployment target** — One server (Linux) with local PostgreSQL + Redis. Cluster/multi-server deployment is a separate engagement.

### Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hardware delivery delay | High (blocks Phase 3) | Start with protocol simulation; use virtual serial ports for daemon testing |
| PASSTI protocol ambiguity | High (blocks e-money integration) | Allocate 16h buffer for reverse engineering; request vendor support early |
| Scope creep (new features mid-project) | Medium | Strict change control; new features quoted separately |
| Performance under load (500+ concurrent gates) | Medium | Load testing in Phase 6; architectural scaling review if needed |
| Browser compatibility for POS (older machines) | Low | Target Chrome/Edge latest; Element Plus handles most compatibility |

---

## 7. Recommendation

**For most clients, Option B (Medium Track — 3 months, ~$77k) offers the best balance:**
- Fast enough to capture operational benefits quickly
- Realistic timeline for quality hardware integration
- Sufficient testing and UAT period to catch edge cases
- Sustainable team pace without burnout or excessive overtime costs

**Option A (Fast Track) is recommended only if:**
- There is a hard deadline (regulatory, contractual, or competitive)
- Hardware is already on-site and fully documented
- Client can dedicate 2–4 hours daily for immediate feedback
- Budget allows for the 70% premium

**Option C (Slow Track) is recommended only if:**
- Budget is strictly constrained
- There is no urgency (existing system functional)
- Client has internal technical capacity to supplement development
- Timeline flexibility of 6 months is acceptable

---

## 8. Next Steps

1. **Review & approve** this plan and pricing option
2. **Sign SOW (Statement of Work)** with selected option and payment terms
3. **Hardware inventory** — Confirm available hardware or procurement timeline
4. **Access provisioning** — Repository access, staging server, VPN (if needed)
5. **Kickoff meeting** — Align on communication cadence, demo schedule, and escalation path
6. **Design doc Section 6** — Finalize API endpoint design (currently marked as "next design session" in original doc)

---

*Document generated: 2026-04-22*
*Based on: EParking_System_v2_Design.docx (Sections 1–5)*
