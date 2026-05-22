# Printer Management

> 30 nodes · cohesion 0.10

## Key Concepts

- **printers.py** (16 connections) — `api/app/routes/printers.py`
- **Printer** (14 connections) — `api/app/models/printer.py`
- **_to_response()** (9 connections) — `api/app/routes/printers.py`
- **_paper_status()** (5 connections) — `api/app/routes/printers.py`
- **create_printer()** (4 connections) — `api/app/routes/printers.py`
- **decrement_paper()** (4 connections) — `api/app/routes/printers.py`
- **PrinterResponse** (4 connections) — `api/app/routes/printers.py`
- **get_printer()** (3 connections) — `api/app/routes/printers.py`
- **list_printers()** (3 connections) — `api/app/routes/printers.py`
- **PaperRefillRequest** (3 connections) — `api/app/routes/printers.py`
- **printer_status_summary()** (3 connections) — `api/app/routes/printers.py`
- **PrinterCreateRequest** (3 connections) — `api/app/routes/printers.py`
- **PrinterUpdateRequest** (3 connections) — `api/app/routes/printers.py`
- **refill_paper()** (3 connections) — `api/app/routes/printers.py`
- **update_printer()** (3 connections) — `api/app/routes/printers.py`
- **printer.py** (2 connections) — `api/app/models/printer.py`
- **.__repr__()** (1 connections) — `api/app/models/printer.py`
- **Printer model with paper counter tracking.** (1 connections) — `api/app/models/printer.py`
- **A thermal printer attached to a gate.** (1 connections) — `api/app/models/printer.py`
- **delete_printer()** (1 connections) — `api/app/routes/printers.py`
- **_get_db()** (1 connections) — `api/app/routes/printers.py`
- **Printer management routes — CRUD + paper counter operations.** (1 connections) — `api/app/routes/printers.py`
- **List all printers, optionally filtered by gate_id.** (1 connections) — `api/app/routes/printers.py`
- **Create a new printer.** (1 connections) — `api/app/routes/printers.py`
- **Get a single printer by ID.** (1 connections) — `api/app/routes/printers.py`
- *... and 5 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/app/models/printer.py`
- `api/app/routes/printers.py`

## Audit Trail

- EXTRACTED: 83 (86%)
- INFERRED: 13 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*