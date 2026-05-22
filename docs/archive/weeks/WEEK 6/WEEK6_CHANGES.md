# Week 6 — Changes & Build Log

> **Date:** 26 April 2026
> **Scope:** Admin Pages + Device Management
> **Depends on:** Week 1–5 (Foundation, Auth, Frontend, Daemons, Protocols, Payment API)

---

## What Was Built

### Phase 0: Reusable Components & Patterns

#### Frontend Components

| File | Purpose |
|------|---------|
| `frontend/components/DataTable.vue` | Sortable, paginated table with search bar, action column (edit/delete), boolean/enum/formatter support |
| `frontend/components/CrudModal.vue` | Dynamic form modal driven by field schema array — supports text, number, textarea, select, switch, time, password |
| `frontend/components/ConfirmDialog.vue` | Delete confirmation dialog with loading state |

#### Backend Pattern

| File | Purpose |
|------|---------|
| `api/app/utils/pagination.py` | Generic `paginated_list()` helper with `PaginationParams` dependency — used by all list endpoints |

---

### Phase 1: Settings Page (`/setting`)

#### New APIs

| Route | Methods | Entity | Access |
|-------|---------|--------|--------|
| `/api/vehicle-types` | GET, POST, PATCH, DELETE | VehicleType | admin |
| `/api/shifts` | GET, POST, PATCH, DELETE | Shift | admin |
| `/api/areas` | GET, POST, PATCH, DELETE | AreaParkir | admin |

#### Frontend Tabs
1. **General Settings** — editable settings table using existing `/api/settings`
2. **Vehicle Types** — full CRUD with tariff configuration
3. **Shifts** — full CRUD with time picker
4. **Areas** — full CRUD with capacity tracking

#### Schemas
- `api/app/schemas/vehicle_type.py` — VehicleTypeCreate, Update, Response
- `api/app/schemas/shift.py` — ShiftCreate, Update, Response
- `api/app/schemas/area.py` — AreaCreate, Update, Response

---

### Phase 2: Device Page (`/device`)

#### New APIs

| Route | Methods | Entity | Access |
|-------|---------|--------|--------|
| `/api/emoney-readers` | GET, POST, PATCH, DELETE | EmoneyReader | admin |

#### Frontend Tabs
1. **Gate In** — full CRUD using existing `/api/gates/in`
2. **Gate Out** — full CRUD using existing `/api/gates/out`
3. **E-Money Readers** — full CRUD with serial config

#### Schemas
- `api/app/schemas/emoney_reader.py` — EmoneyReaderCreate, Update, Response

---

### Phase 3: Member Page (`/member`)

#### New APIs

| Route | Methods | Entity | Access |
|-------|---------|--------|--------|
| `/api/members` | GET, POST, PATCH, DELETE | Member | admin |
| `/api/member-groups` | GET, POST, PATCH, DELETE | MemberGroup | admin |

#### Frontend Tabs
1. **Members** — full CRUD with card number, plate, validity dates
2. **Member Groups** — full CRUD

#### Schemas
- `api/app/schemas/member.py` — MemberCreate, Update, Response (with vehicle_type_name, member_group_name)
- `api/app/schemas/member_group.py` — MemberGroupCreate, Update, Response

---

### Phase 4: Transaksi Page (`/transaksi`)

#### New APIs

| Route | Methods | Purpose | Access |
|-------|---------|---------|--------|
| `/api/transactions` | GET | ParkingTransaction list with filters (date, status, payment_method, search) | operator |
| `/api/transactions/{id}` | GET | Single transaction detail | operator |
| `/api/manual-open-logs` | GET | ManualOpenLog list | operator |
| `/api/abandoned-vehicle-logs` | GET | AbandonedVehicleLog list | operator |

#### Frontend Tabs
1. **Transaksi Parkir** — searchable list with date range + status filters
2. **Buka Manual** — log list
3. **Kendaraan Ditinggal** — log list

#### Schemas
- `api/app/schemas/transaction.py` — TransactionListItem with duration calculation

---

### Phase 5: Report Page (`/report`)

#### New APIs

| Route | Methods | Purpose | Access |
|-------|---------|---------|--------|
| `/api/reports/summary` | GET | Date-range summary: total transactions, revenue by method, averages | admin |
| `/api/reports/emoney` | GET | E-money breakdown: success/failed/lost_contact counts, settlement status | admin |

#### Frontend
- Date range picker
- Summary statistic cards (8 metrics per tab)
- Color-coded values (green=success, red=failed, yellow=warning)

#### Schemas
- `api/app/schemas/report.py` — SummaryReport, EmoneyReport

---

### Phase 6: Notification Page (`/notification`)

**No new backend APIs** — uses existing endpoints.

#### Frontend Tabs
1. **E-Money Unresolved** — queries `/api/transactions?status=LOST_CONTACT`
2. **Transaksi Aktif** — queries `/api/transactions?status=ACTIVE`
3. **Alert Terbaru** — merges `/api/manual-open-logs` + `/api/abandoned-vehicle-logs`

---

## Route Registry

Total FastAPI routes after Week 6: **66** (up from ~25 in Week 5)

New routes added:
- `/api/vehicle-types` (+5)
- `/api/shifts` (+5)
- `/api/areas` (+5)
- `/api/emoney-readers` (+5)
- `/api/members` (+5)
- `/api/member-groups` (+5)
- `/api/transactions` (+2)
- `/api/manual-open-logs` (+1)
- `/api/abandoned-vehicle-logs` (+1)
- `/api/reports/summary` (+1)
- `/api/reports/emoney` (+1)

---

## Verification Results

| Test | Result |
|------|--------|
| Existing backend tests (Weeks 1–5) | **190/190 passed** — 0 regressions |
| Frontend production build | **5.56 MB** — 0 compilation errors |
| FastAPI route loading | **66 routes** — all import correctly |
| No circular imports | ✅ Verified |

---

## Decisions Made

1. **Reusable component pattern:** `DataTable` + `CrudModal` + `ConfirmDialog` power all 6 admin pages. Adding a new CRUD page requires only: schema definition, route file, and a ~50-line frontend tab.

2. **PaginationParams dependency:** All list endpoints use the same `skip/limit/q` query parameters via a FastAPI dependency. Consistent API surface across all resources.

3. **Frontend time picker for shifts:** `el-time-picker` with `HH:mm` format stores values as `HH:mm:ss` strings, matching the database `Time` column.

4. **Date filter on transactions:** Date range uses `date_from`/`date_to` query params with inclusive start, exclusive end — standard pattern for range queries.

5. **Report aggregation in SQL:** Reports use `func.sum()`, `func.count()` with GROUP BY for efficient database-level aggregation rather than fetching all rows.

6. **Notification page frontend-only:** No new backend needed — creatively combines existing list endpoints with client-side merging and sorting.

---

## Files Created/Modified

**Created:** 28+ new files
- `frontend/components/DataTable.vue`
- `frontend/components/CrudModal.vue`
- `frontend/components/ConfirmDialog.vue`
- `api/app/utils/pagination.py`
- `api/app/schemas/vehicle_type.py`
- `api/app/schemas/shift.py`
- `api/app/schemas/area.py`
- `api/app/schemas/emoney_reader.py`
- `api/app/schemas/member.py`
- `api/app/schemas/member_group.py`
- `api/app/schemas/transaction.py`
- `api/app/schemas/report.py`
- `api/app/routes/vehicle_types.py`
- `api/app/routes/shifts.py`
- `api/app/routes/areas.py`
- `api/app/routes/emoney_readers.py`
- `api/app/routes/members.py`
- `api/app/routes/member_groups.py`
- `api/app/routes/transactions.py`
- `api/app/routes/manual_open_logs.py`
- `api/app/routes/abandoned_vehicles.py`
- `api/app/routes/reports.py`
- `frontend/pages/setting.vue`
- `frontend/pages/device.vue`
- `frontend/pages/member.vue`
- `frontend/pages/transaksi.vue`
- `frontend/pages/report.vue`
- `frontend/pages/notification.vue`
- `docs/plans/2026-04-26-week6-admin-pages.md`
- `docs/WEEK 6/WEEK6_CHANGES.md`
- `docs/WEEK 6/WEEK6_TEST_CHECKLIST.md`

**Modified:**
- `api/app/main.py` — registered 11 new routers

**Total lines of code:** ~3,500+ (backend + frontend)

---

## Week 6 Exit Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Settings page has 4 tabs (General, Vehicle Types, Shifts, Areas) | ✅ |
| 2 | Device page has 3 tabs (Gate In, Gate Out, E-Money Readers) | ✅ |
| 3 | Member page has 2 tabs (Members, Member Groups) | ✅ |
| 4 | Transaksi page has 3 tabs (Transactions, Manual Open, Abandoned) | ✅ |
| 5 | Report page has 2 tabs (Summary, E-Money) with date picker | ✅ |
| 6 | Notification page has 3 tabs using existing APIs | ✅ |
| 7 | All 190 existing tests pass | ✅ |
| 8 | Frontend builds without errors | ✅ |
| 9 | All 66 FastAPI routes load correctly | ✅ |
| 10 | Reusable components (DataTable, CrudModal, ConfirmDialog) work | ✅ |
| 11 | Pagination helper used by all list endpoints | ✅ |
| 12 | Documentation written | ✅ |

---

## Looking Ahead to Week 7

**Week 7 scope:** System Hardening & Polish
- Input validation hardening on all admin CRUD endpoints
- Frontend form validation improvements
- Error handling and loading states refinement
- Performance optimization (query plans, caching)
- Integration testing between frontend and backend
- Deployment configuration (systemd, nginx)

*End of Week 6 Build Log*
