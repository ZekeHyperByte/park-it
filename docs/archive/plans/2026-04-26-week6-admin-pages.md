# Week 6 — Admin Pages + Device Management Implementation Plan

> **Date:** 26 April 2026
> **Scope:** Full CRUD admin dashboard for 6 pages + backend APIs
> **Approach:** Page-by-page vertical slices with reusable components

---

## Phase 0: Foundation (Reusable Components + Patterns)

### Frontend Components

| File | Purpose |
|------|---------|
| `frontend/components/DataTable.vue` | Sortable, paginated table with search and actions |
| `frontend/components/CrudModal.vue` | Dynamic form modal driven by field schema |
| `frontend/components/ConfirmDialog.vue` | Delete confirmation dialog |

### Backend Pattern

| File | Purpose |
|------|---------|
| `api/app/utils/pagination.py` | Generic paginated list helper |

---

## Phase 1: Settings Page (`/setting`)

### New APIs

| Route | Methods | Entity |
|-------|---------|--------|
| `/api/vehicle-types` | GET, POST, PATCH, DELETE | VehicleType |
| `/api/shifts` | GET, POST, PATCH, DELETE | Shift |
| `/api/areas` | GET, POST, PATCH, DELETE | AreaParkir |

### Frontend Tabs
1. **General Settings** — uses existing `/api/settings`
2. **Vehicle Types** — CRUD table
3. **Shifts** — CRUD table
4. **Areas** — CRUD table

---

## Phase 2: Device Page (`/device`)

### New APIs

| Route | Methods | Entity |
|-------|---------|--------|
| `/api/emoney-readers` | GET, POST, PATCH, DELETE | EmoneyReader |

### Frontend Tabs
1. **Gate In** — uses existing `/api/gates/in`
2. **Gate Out** — uses existing `/api/gates/out`
3. **E-Money Readers** — CRUD table

---

## Phase 3: Member Page (`/member`)

### New APIs

| Route | Methods | Entity |
|-------|---------|--------|
| `/api/members` | GET, POST, PATCH, DELETE | Member |
| `/api/member-groups` | GET, POST, PATCH, DELETE | MemberGroup |

### Frontend Tabs
1. **Members** — CRUD table
2. **Member Groups** — CRUD table

---

## Phase 4: Transaksi Page (`/transaksi`)

### New APIs

| Route | Methods | Entity |
|-------|---------|--------|
| `/api/transactions` | GET | ParkingTransaction (list with filters) |
| `/api/manual-open-logs` | GET | ManualOpenLog (list) |
| `/api/abandoned-vehicle-logs` | GET | AbandonedVehicleLog (list) |

### Frontend Tabs
1. **Transactions** — searchable list
2. **Manual Open Logs** — list
3. **Abandoned Vehicles** — list

---

## Phase 5: Report Page (`/report`)

### New APIs

| Route | Methods | Purpose |
|-------|---------|---------|
| `/api/reports/summary` | GET | Date-range summary stats |
| `/api/reports/emoney` | GET | E-money breakdown |

### Frontend
- Date range picker
- Summary statistic cards
- Data tables

---

## Phase 6: Notification Page (`/notification`)

### Frontend Tabs
1. **Unresolved E-Money** — queries existing endpoints
2. **Settlement Status** — queries existing endpoints
3. **Recent Alerts** — queries existing endpoints

No new backend APIs needed.

---

## Testing Strategy

1. **Backend:** One test file per new route
2. **Frontend:** `npm run build` after each page
3. **Integration:** Manual verification checklist

---

## Execution Order

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5  →  Phase 6  →  Tests
(components) (settings) (device)   (member)   (transaksi) (report)   (notification)
```

---

*Plan created: 26 April 2026*
