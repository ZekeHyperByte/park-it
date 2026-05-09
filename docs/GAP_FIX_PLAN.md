# Park-It v2 — Gap Fix Plan

This document is the canonical fix plan derived from the gap analysis of Park-It v2 against three reference documents:

1. **COMPASS User Manual** — functional reference for parking ops (Indonesian).
2. **Command Protocol Reader PASSTI v1.12** — binary serial protocol for the e-money reader.
3. **Format File Settlement Multibank v1.3** — bank settlement file format.

Every task below is self-contained: an executing agent should be able to read one task and produce a correct PR without reopening the source PDFs. Tasks include file paths, line numbers, exact code, test commands, and acceptance criteria.

---

## How to use this document

- Tasks are grouped by **phase** (1 = blocking, 6 = polish). Execute phases in order; within a phase, dependent tasks are explicit.
- Each task has the form `[ID] Title` with a fixed schema:
  - **Severity** — blocker / high / medium / low
  - **Files** — absolute paths within `parking-system-v2/`
  - **Problem** — what's wrong, with exact line refs
  - **Fix** — exact code to apply (drop-in or diff)
  - **Tests** — pytest / vitest commands plus new test cases
  - **Acceptance** — what "done" looks like
- Always run `ruff check .`, `mypy .`, and the relevant test suite before declaring a task done.
- Never fix more than one task per commit unless the PR description groups related tasks (e.g. C1+C2+C3 in one PR is fine; mixing C-class with F-class is not).
- All times in user-facing timestamps and settlement files are **Asia/Jakarta** (`zoneinfo.ZoneInfo("Asia/Jakarta")`). Database stores UTC.

---

## Conventions

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0 async, Pydantic v2. Linter: `ruff` (line-length 100). Type checker: `mypy` strict.
- **Frontend:** Nuxt 3 (Vue 3 SPA), Tailwind v4, shadcn-vue, Pinia. Lint: ESLint via `npm run lint`.
- **Tests:** pytest (backend) and vitest (frontend). All new code requires tests.
- **Commits:** conventional-commit style: `fix(passti): correct BCD timeout encoding (C3)`.

---

## Phase 1 — Blocking bugs (must fix before any live pilot)

### [C1] Settlement transaction lines must contain only `cardtype..CardLog`, not the full PASSTI frame

**Severity:** blocker (bank will reject every settlement)
**Files:**
- `parking-system-v2/api/app/models/emoney_transaction.py`
- `parking-system-v2/api/app/migrations/` (new Alembic migration)
- `parking-system-v2/daemons/gate_out.py`
- `parking-system-v2/api/app/routes/payments.py`
- `parking-system-v2/api/app/services/payment.py`
- `parking-system-v2/api/app/services/event_consumer.py`
- `parking-system-v2/api/app/schemas/payment.py`
- `parking-system-v2/workers/background/settlement_worker.py`
- `parking-system-v2/workers/background/settlement_file.py`
- `parking-system-v2/workers/tests/test_settlement_file.py`

**Problem:**
`raw_response_hex` currently stores the entire PASSTI response frame (`STX | LEN-H | LEN-L | RespCode | StatusCode(3) | body | LRC`). Per Multibank v1.3 §I, each settlement transaction line must be only the deduct response **body starting from cardtype through CardLog Transaction**. Writing the full frame produces lines like `02XXYY00000001…<CardLog>ZZ` where `02 XX YY 00 00 00` (STX + LEN + RespCode + Status) and the trailing `ZZ` (LRC) are extraneous.

Source pointers:
- `daemons/gate_out.py:539,559,575` — passes `result.get("raw", "")` instead of body hex
- `workers/background/settlement_file.py:36-39` — writes the value verbatim
- Multibank v1.3 §I "Settlement data Transaction" → `Response data from command deduct (start from cardtype until CardLog Transaction)`

**Fix:**

1. Add a new column `settlement_payload_hex` to `EmoneyTransaction`:

```python
# api/app/models/emoney_transaction.py — add near raw_response_hex
settlement_payload_hex: Mapped[str | None] = mapped_column(Text, nullable=True)
"""Hex of deduct response body from cardtype through CardLog (Multibank v1.3)."""
```

2. Generate Alembic migration:

```bash
cd api && alembic revision -m "add settlement_payload_hex to emoney_transactions"
```

In the migration:
```python
def upgrade() -> None:
    op.add_column(
        "emoney_transactions",
        sa.Column("settlement_payload_hex", sa.Text(), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("emoney_transactions", "settlement_payload_hex")
```

3. Update `protocols/passti/frame.py` `parse_response` to additionally return `body_hex`:

```python
# In parse_response(...) just before the return statement, add:
body_hex = body.hex().upper()
# Then in the returned dict:
return {
    "ok": ok,
    "resp_code": resp_code,
    "status": status,
    "status_msg": STATUS_MESSAGES.get(status, f"Unknown {bytes(status).hex()}"),
    "body": body,
    "body_hex": body_hex,
    "raw": raw.hex(),
}
```

4. Update `daemons/gate_out.py` to send body hex on the success branch:

```python
# daemons/gate_out.py — replace the success-branch DeductResultEvent (around line 575)
await self.publish_event(
    DeductResultEvent(
        event_type="deduct_result",
        gate_id=self.gate_id,
        status=DeductStatus.SUCCESS,
        card_number=deduct_data.get("card_number", ""),
        card_type=deduct_data.get("card_type", ""),
        deduct_amount=deduct_data.get("deducted", 0),
        balance_before=deduct_data.get("remaining", 0) + deduct_data.get("deducted", 0),
        balance_after=deduct_data.get("remaining", 0),
        transaction_counter=deduct_data.get("trans_counter", 0),
        raw_response_hex=result.get("raw", ""),                      # keep for debugging
        settlement_payload_hex=result.get("body_hex", ""),           # NEW: spec-compliant
    )
)
```

Failure branches keep `raw_response_hex` populated and set `settlement_payload_hex=""`.

5. Add `settlement_payload_hex: str = Field(default="")` to `shared/events.py::DeductResultEvent` and to `api/app/schemas/payment.py` (both request and response models that already carry `raw_response_hex`).

6. In `api/app/services/event_consumer.py` and `api/app/services/payment.py`, persist `settlement_payload_hex` alongside `raw_response_hex` whenever an `EmoneyTransaction` row is created.

7. Update `workers/background/settlement_worker.py:111`:

```python
tx_dicts = [
    {"settlement_payload_hex": tx.settlement_payload_hex or ""}
    for tx in transactions
]
```

8. Update `workers/background/settlement_file.py`:

```python
def build_settlement_content(
    transactions: list[dict],
    total_amount: int,
) -> str:
    """Build settlement file content per Multibank v1.3 §I.

    Header: TrxCount(3) + TrxAmount(10) + LF
    Body: each transaction's deduct-response body (cardtype..CardLog) hex + LF
    """
    trx_count = len(transactions)
    header = f"{trx_count:03d}{total_amount:010d}\n"
    body_lines = [f"{tx.get('settlement_payload_hex', '')}\n" for tx in transactions]
    return header + "".join(body_lines)
```

**Tests:**

`workers/tests/test_settlement_file.py` — replace/add cases that assert against the V1.12 appendix vector:

```python
def test_settlement_line_uses_body_hex_only(tmp_path):
    """Multibank v1.3 §I: each line is cardtype..CardLog, no STX/LEN/Resp/Status/LRC."""
    # Vector from Command Protocol Reader V1.12 §III.C "Detail Response":
    # cardtype=01, MID=02034567890ABCDE, TID=87654321,
    # datetime=10122017121550, card=5710120620170005,
    # deducted=00000001, remaining=0001D0CC, trans_counter=00000001,
    # CardLog=CDDDF8D374...B9B4
    body_hex = (
        "01"
        "02034567890ABCDE"
        "87654321"
        "10122017121550"
        "5710120620170005"
        "00000001"
        "0001D0CC"
        "00000001"
        "CDDDF8D374178432ECDC02FA9E616476DC7D3341B24FCDA12352546FF45B5ADA79F23"
        "87FB6800990EBDAD1EDBCDD3CBA5998E7A746048523759750178AE62DA5355C9CB17"
        "AF5F34DFF35865FAF960AF4194C5F2B622CCABC9BB09538B076B7F56344ACC65BC7B9B4"
    )
    content = build_settlement_content(
        transactions=[{"settlement_payload_hex": body_hex}],
        total_amount=1,
    )
    lines = content.split("\n")
    assert lines[0] == "001" + "0000000001"  # header
    assert lines[1] == body_hex
    assert not lines[1].startswith("02")  # must not start with STX
```

Run: `pytest workers/tests/test_settlement_file.py -v`

**Acceptance:**
- New column populated for all new SUCCESS transactions.
- Settlement files contain lines that start with the cardtype byte (no `02` prefix).
- The full frame is still preserved in `raw_response_hex` for debugging.
- All existing tests still pass.

**Backfill note:** Existing rows have `settlement_payload_hex = NULL`. Either (a) re-derive from `raw_response_hex` with a one-shot script (slice off first 4 bytes after STX/LEN and last 1 byte LRC), or (b) accept those rows are pre-fix and leave them out of settlement until cleared. Pick (a) if you have unsettled rows in prod.

---

### [C2] Exclude QR Payment (cardtype 09) from settlement

**Severity:** blocker
**Files:**
- `parking-system-v2/workers/background/settlement_worker.py`
- `parking-system-v2/api/app/models/emoney_transaction.py` (add `card_type_code`)
- `parking-system-v2/api/app/services/payment.py`
- `parking-system-v2/api/app/services/event_consumer.py`
- `parking-system-v2/workers/tests/test_settlement_worker.py`

**Problem:**
Multibank v1.3 §I, Settlement data Transaction Note: *"Cardtype 09 (QR Payment) doesn't need to settled"*. The current query in `workers/background/settlement_worker.py:74-83` selects all `status == "SUCCESS"` rows with no card-type filter, so QR transactions get bundled into bank settlement, which the bank will reject (status `01` Invalid Format).

`EmoneyTransaction.card_type` stores the **string name** (e.g. `"QR Payment"`, `"Mandiri eMoney"`), so comparing against the spec code is fragile. Add an integer `card_type_code` field for unambiguous matching.

**Fix:**

1. Schema: add `card_type_code` to `EmoneyTransaction`:

```python
# api/app/models/emoney_transaction.py
card_type_code: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
"""PASSTI card type code (0x01-0x09 per V1.12 §V)."""
```

Migration:
```python
op.add_column(
    "emoney_transactions",
    sa.Column("card_type_code", sa.Integer(), nullable=True, index=True),
)
```

2. Populate it everywhere `EmoneyTransaction(...)` is constructed. Source: PASSTI deduct response body byte 0 (already exposed as `card_type_code` in `parse_deduct_response`).

3. Filter in `workers/background/settlement_worker.py`:

```python
from sqlalchemy import or_

tx_result = await db.execute(
    select(EmoneyTransaction)
    .where(
        EmoneyTransaction.settlement_batch_id.is_(None),
        EmoneyTransaction.status == "SUCCESS",
        EmoneyTransaction.emoney_reader_id == reader_id,
        # Multibank v1.3: QR Payment (0x09) is settled separately by the QR provider
        or_(
            EmoneyTransaction.card_type_code != 0x09,
            EmoneyTransaction.card_type_code.is_(None),  # legacy rows w/o code
        ),
    )
    .order_by(EmoneyTransaction.created_at)
)
```

For legacy rows (`card_type_code IS NULL`) with `card_type == "QR Payment"`, exclude by string fallback or backfill the code via a one-shot script.

**Tests:**

```python
# workers/tests/test_settlement_worker.py
async def test_settlement_excludes_qr_payment(db_session):
    reader = make_reader(mid="...", tid="...")
    make_emoney_tx(card_type_code=0x02, amount=5000, status="SUCCESS")  # eMoney
    make_emoney_tx(card_type_code=0x09, amount=3000, status="SUCCESS")  # QR
    await db_session.commit()

    result = await generate_settlement_file({"redis": fake_redis()}, db=db_session)
    assert result["files_generated"] == 1
    assert result["total_transactions"] == 1  # QR excluded
    # Inspect file → only one trx line, header total = 5000
```

**Acceptance:**
- Generated settlement files never contain a transaction line whose first byte is `09`.
- QR transactions remain SUCCESS in DB but never get a `settlement_batch_id`.
- A separate process can later be added for QR reconciliation if the QR provider asks for one.

---

### [C3] Fix BCD timeout encoding in PASSTI commands

**Severity:** blocker (non-conformant frames)
**Files:**
- `parking-system-v2/protocols/passti/frame.py`
- `parking-system-v2/protocols/passti/commands.py`
- `parking-system-v2/protocols/tests/test_passti_frame.py`

**Problem:**
`protocols/passti/frame.py:68-70` and `commands.py:24-26` both define:

```python
def _bcd_timeout(sec: int) -> bytes:
    return bytes([sec // 100, sec % 100])
```

This is a **binary** encoding, not BCD. For `sec=10` it produces `0x00 0x0A`, but Command Protocol Reader V1.12 §III.B example states `0x00 0x10 = 10 seconds` (BCD: high nibble `1`, low nibble `0`). For `sec=99` the function gives `0x00 0x63` instead of `0x00 0x99`. The reader may silently misinterpret or reject these frames.

**Fix:**

Replace both copies with a single canonical implementation in `frame.py`, and import it from `commands.py`:

```python
# protocols/passti/frame.py
def _bcd_timeout(sec: int) -> bytes:
    """Encode a timeout (0-9999 seconds) as 2-byte BCD per V1.12 §III.B.

    Examples: 10 → b"\\x00\\x10", 99 → b"\\x00\\x99", 1234 → b"\\x12\\x34".
    """
    if not 0 <= sec <= 9999:
        raise ValueError(f"Timeout must be 0..9999 seconds, got {sec}")
    return _to_bcd(f"{sec:04d}")
```

Delete the duplicate in `commands.py` and `from protocols.passti.frame import _bcd_timeout`.

**Tests:**

```python
# protocols/tests/test_passti_frame.py
import pytest
from protocols.passti.frame import _bcd_timeout

@pytest.mark.parametrize("sec, expected", [
    (0,    b"\x00\x00"),
    (1,    b"\x00\x01"),
    (10,   b"\x00\x10"),  # V1.12 §III.B example
    (99,   b"\x00\x99"),
    (100,  b"\x01\x00"),
    (1234, b"\x12\x34"),
    (9999, b"\x99\x99"),
])
def test_bcd_timeout(sec, expected):
    assert _bcd_timeout(sec) == expected

def test_bcd_timeout_rejects_out_of_range():
    with pytest.raises(ValueError):
        _bcd_timeout(-1)
    with pytest.raises(ValueError):
        _bcd_timeout(10000)
```

Also add a frame-level golden test that asserts `cmd_check_balance(10)` produces a frame ending in `... 00 10 LRC`.

Run: `pytest protocols/tests/test_passti_frame.py -v`

**Acceptance:**
- Both copies of `_bcd_timeout` deleted; only one canonical function exists.
- Existing PASSTI integration tests still pass.
- New parametric test covers V1.12 §III.B example exactly.

---

## Phase 2 — Settlement pipeline (must fix before going live with a bank)

### [H1] Implement real SFTP upload for settlement files

**Severity:** high
**Files:**
- `parking-system-v2/workers/background/settlement_uploader.py`
- `parking-system-v2/shared/config.py` (new env vars)
- `parking-system-v2/.env.example`
- `parking-system-v2/workers/tests/test_settlement_uploader.py`
- `parking-system-v2/pyproject.toml` (add `asyncssh` dep)

**Problem:**
`workers/background/settlement_uploader.py:63-87` `upload_settlement_file` is a stub: logs and returns `True` without actually transferring. The block in the docstring (`asyncssh.connect`/`sftp.put`) is commented out.

**Fix:**

1. Add `asyncssh ^2.18.0` to `pyproject.toml` under `[project.dependencies]`. Run `pip install -e .[dev]`.

2. Add settings:

```python
# shared/config.py — within Settings class
settlement_sftp_host: str = ""
settlement_sftp_port: int = 22
settlement_sftp_username: str = ""
settlement_sftp_key_path: str = ""
settlement_sftp_known_hosts_path: str = ""  # use "" for strict, None for accept-all (NOT prod)
settlement_sftp_remote_dir: str = "/incoming"
settlement_sftp_connect_timeout: int = 30
```

Mirror in `.env.example`.

3. Replace the stub:

```python
# workers/background/settlement_uploader.py
import asyncssh
import os
from pathlib import Path

async def upload_settlement_file(
    file_path: str,
    *,
    host: str,
    port: int,
    username: str,
    key_path: str,
    known_hosts: str | None,
    remote_dir: str = "/",
    connect_timeout: int = 30,
) -> bool:
    """Upload a settlement file via SFTP. Returns True on success.

    Raises asyncssh exceptions on connection/auth failure so the caller
    (ARQ retry) can decide whether to retry.
    """
    if not Path(file_path).is_file():
        logger.error("settlement_upload_no_file", file_path=file_path)
        return False

    remote_name = os.path.basename(file_path)
    logger.info(
        "settlement_upload_start",
        file_path=file_path,
        host=host,
        remote=f"{remote_dir}/{remote_name}",
    )

    async with asyncssh.connect(
        host=host,
        port=port,
        username=username,
        client_keys=[key_path],
        known_hosts=known_hosts if known_hosts else None,
        connect_timeout=connect_timeout,
    ) as conn:
        async with conn.start_sftp_client() as sftp:
            # Upload to .partial then rename — atomic delivery
            tmp_remote = f"{remote_dir}/{remote_name}.partial"
            final_remote = f"{remote_dir}/{remote_name}"
            await sftp.put(file_path, tmp_remote)
            await sftp.rename(tmp_remote, final_remote)

    logger.info("settlement_upload_complete", file_path=file_path)
    return True
```

4. Wire into the ARQ job: after `generate_settlement_file` writes the file, enqueue an upload job with retry policy `max_tries=5, retry_delay=60s`.

5. Add a fallback "manual upload" CLI script (`scripts/upload_settlement.py`) that takes a filename and uses the same function — for ops to retry by hand.

**Tests:**
Use `asyncssh` test server (or `aioftp`/mocked sftp). At minimum:

```python
async def test_upload_writes_then_renames(monkeypatch):
    """Verify atomic .partial → rename pattern."""
    captured = []
    class FakeSftp:
        async def put(self, src, dst): captured.append(("put", src, dst))
        async def rename(self, a, b): captured.append(("rename", a, b))
    # ... patch asyncssh.connect to yield a fake conn
    await upload_settlement_file(...)
    assert captured == [
        ("put", "/tmp/foo.txt", "/incoming/foo.txt.partial"),
        ("rename", "/incoming/foo.txt.partial", "/incoming/foo.txt"),
    ]
```

**Acceptance:**
- SFTP upload works end-to-end against a real test server.
- Failed uploads raise (so ARQ retries); they don't silently return False.
- Atomic delivery: bank polling never sees a half-written file.

---

### [H2] Implement response file (.OK / .NOK) polling and per-transaction reconciliation

**Severity:** high
**Files:**
- `parking-system-v2/workers/background/settlement_uploader.py`
- `parking-system-v2/api/app/models/emoney_settlement.py`
- `parking-system-v2/api/app/models/emoney_transaction.py`
- `parking-system-v2/workers/background/settlement_response_worker.py` (new)
- `parking-system-v2/workers/settings.py`
- `parking-system-v2/workers/tests/test_settlement_response.py`

**Problem:**
`poll_for_response` (`settlement_uploader.py:90-114`) sleeps for hours then returns `(None, None)`. Bank `.OK` / `.NOK` acknowledgements are never read, so per-transaction status (`02 Duplicate`, `04 Amount mismatch`, etc.) is never reconciled. `parse_ok_response` exists but is unreachable.

**Fix:**

1. Schema additions:

```python
# api/app/models/emoney_settlement.py — add
response_received_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
response_extension: Mapped[str | None] = mapped_column(String(4), nullable=True)  # "OK" or "NOK"
response_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
# status enum: GENERATED, UPLOADED, ACKED_OK, ACKED_NOK, FAILED, PARTIAL

# api/app/models/emoney_transaction.py — add
bank_response_status: Mapped[str | None] = mapped_column(String(2), nullable=True)
"""Bank response code from .OK file: 00 Accepted, 02 Duplicate, 04 Amount mismatch, etc."""
bank_response_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

Migrate.

2. New ARQ job `poll_settlement_response` that runs every 5 minutes (cron in `workers/settings.py`):

```python
# workers/background/settlement_response_worker.py
async def poll_settlement_responses(ctx) -> dict:
    """For every UPLOADED EmoneySettlement, poll the bank SFTP for .OK/.NOK.

    On match: parse, set per-transaction bank_response_status, update settlement status.
    """
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        pending = await db.execute(
            select(EmoneySettlement)
            .where(
                EmoneySettlement.status == "UPLOADED",
                EmoneySettlement.uploaded_at >= datetime.now(timezone.utc) - timedelta(days=7),
            )
            .order_by(EmoneySettlement.uploaded_at)
        )
        async with asyncssh.connect(...) as conn:
            async with conn.start_sftp_client() as sftp:
                for settlement in pending.scalars():
                    base = settlement.filename.removesuffix(".txt")
                    for ext in ("OK", "NOK"):
                        remote = f"{settings.settlement_sftp_remote_dir}/{base}.{ext}"
                        try:
                            local = f"/tmp/{base}.{ext}"
                            await sftp.get(remote, local)
                        except (asyncssh.SFTPNoSuchFile, FileNotFoundError):
                            continue
                        await _process_response(db, settlement, ext, local)
                        break
        await db.commit()
```

3. `_process_response` function reads file, calls existing `parse_ok_response`, and for each line matches by transaction-payload hex back to `EmoneyTransaction.settlement_payload_hex`, then sets `bank_response_status` and `bank_response_at`. Settlement status becomes `ACKED_OK` if all `00`, `ACKED_NOK` if all non-`00`, else `PARTIAL`.

4. Add to ARQ cron (`workers/settings.py`):

```python
class WorkerSettings:
    cron_jobs = [
        ...,
        cron(poll_settlement_responses, minute={0, 15, 30, 45}),
    ]
```

**Tests:**
Mock SFTP get to return a known `.OK` body; assert per-transaction status updates.

**Acceptance:**
- Settlement status transitions: `GENERATED → UPLOADED → ACKED_OK | ACKED_NOK | PARTIAL`.
- Each transaction gets `bank_response_status` filled.
- `PARTIAL` settlements surface in the admin UI for manual investigation.

---

### [H3] Enforce 999-transactions-per-file split

**Severity:** high
**Files:**
- `parking-system-v2/workers/background/settlement_worker.py`
- `parking-system-v2/workers/tests/test_settlement_worker.py`

**Problem:**
Multibank v1.3 §I — `Trx Count` field is 3 digits, max `999`. *"Max 999 (>999 create new file settlement with increasing batch No)."* Current code emits one file per reader regardless of size.

**Fix:**

In `workers/background/settlement_worker.py`, after gathering `transactions`, chunk into 999-row groups and emit one file each, incrementing `batch_number`:

```python
MAX_TRX_PER_FILE = 999

# inside the per-reader loop, replace single-file logic:
chunks = [
    transactions[i : i + MAX_TRX_PER_FILE]
    for i in range(0, len(transactions), MAX_TRX_PER_FILE)
]

for chunk in chunks:
    # Reserve next batch number atomically
    batch_number = await _next_batch_number(redis, reader_id)
    chunk_total = sum(tx.amount_deducted for tx in chunk)
    filename = generate_filename(now, reader.mid, reader.tid, batch_number)
    tx_dicts = [{"settlement_payload_hex": tx.settlement_payload_hex or ""} for tx in chunk]
    content = build_settlement_content(tx_dicts, chunk_total)
    # write file, create EmoneySettlement, link transactions...
```

Extract `_next_batch_number(redis, reader_id) -> int` that uses Redis `INCR` on key `settlement:batch:{reader_id}:{date_jakarta}` for atomic increments.

**Tests:**

```python
async def test_settlement_splits_at_999():
    # Seed 1500 SUCCESS transactions for one reader
    for _ in range(1500):
        make_emoney_tx(...)
    result = await generate_settlement_file({"redis": fake_redis()}, db=db)
    assert result["files_generated"] == 2
    assert result["total_transactions"] == 1500
    # File 1: batch 001, 999 trx; file 2: batch 002, 501 trx
```

**Acceptance:**
- A reader with 1500 unsettled SUCCESS rows produces 2 files (batches 001 + 002).
- Each file's header `TrxCount` ≤ 999.

---

### [H4] Use Asia/Jakarta timezone consistently for settlement filenames + batch keys

**Severity:** high
**Files:**
- `parking-system-v2/workers/background/settlement_worker.py`
- `parking-system-v2/shared/config.py`

**Problem:**
`settlement_worker.py:101` does `datetime.now(timezone.utc)` for the filename timestamp, but `:93` does `date.today().isoformat()` (server's local) for the batch key. Late-evening Jakarta-time settlements will get filename date `D+1` while the batch counter is keyed under `D`. Two files generated within the same wall-clock day can end up sharing batch number 1.

**Fix:**

```python
# top of settlement_worker.py
from zoneinfo import ZoneInfo
JAKARTA = ZoneInfo("Asia/Jakarta")

# inside the worker
now_jkt = datetime.now(JAKARTA)
date_jkt = now_jkt.date()
batch_key = f"settlement:batch:{reader_id}:{date_jkt.isoformat()}"
filename = generate_filename(now_jkt, reader.mid, reader.tid, batch_number)
```

Add `app_timezone: str = "Asia/Jakarta"` to `shared/config.py` so the zone is configurable per-deployment, and use `ZoneInfo(get_settings().app_timezone)` at call sites.

**Tests:**
Freeze time around 23:30 UTC on `2026-05-08` (which is `06:30 +07 on 2026-05-09`). Assert filename starts with `20260509...` AND batch key contains `2026-05-09`.

**Acceptance:**
- Filename date and batch key date always agree.
- All settlement timestamps are recorded in Asia/Jakarta in user-facing UI.

---

## Phase 3 — Backend feature gaps vs COMPASS

### [B1] Member monthly usage cap

**Severity:** medium
**Files:**
- `parking-system-v2/api/app/models/member.py`
- `parking-system-v2/api/app/migrations/...`
- `parking-system-v2/api/app/services/payment.py` (RFID validation path)
- `parking-system-v2/api/app/routes/members.py`
- `parking-system-v2/api/app/schemas/member.py`
- `parking-system-v2/api/tests/test_member_monthly_cap.py`

**Problem:**
COMPASS Bab 6 "Master Kartu Member" has `Batas Pakai Bulanan` (monthly use cap, e.g. max 30 entries per month). v2's `Member` model has no equivalent. Current code lets members enter unlimited times.

**Fix:**

1. Schema:
```python
# api/app/models/member.py
monthly_cap: Mapped[int | None] = mapped_column(
    Integer, nullable=True
)
"""Max entries per calendar month. NULL = unlimited."""
```
Migration: add nullable column, default NULL.

2. Calculate "this month's entry count" via a query:
```python
from sqlalchemy import extract

async def member_entries_this_month(db: AsyncSession, member_id: int) -> int:
    now_jkt = datetime.now(JAKARTA)
    stmt = select(func.count(ParkingTransaction.id)).where(
        ParkingTransaction.member_id == member_id,
        extract("year", ParkingTransaction.entry_time) == now_jkt.year,
        extract("month", ParkingTransaction.entry_time) == now_jkt.month,
    )
    return (await db.execute(stmt)).scalar() or 0
```

3. In RFID member validation flow (`api/app/services/payment.py` — find the function that approves a member tap), reject if cap exceeded:
```python
if member.monthly_cap is not None:
    used = await member_entries_this_month(db, member.id)
    if used >= member.monthly_cap:
        return MemberValidationResult(
            ok=False,
            reason="MONTHLY_CAP_EXCEEDED",
            message=f"Member sudah menggunakan {used}/{member.monthly_cap} kali bulan ini",
        )
```

4. Expose in member schema / route. Add field to CRUD modal in `frontend/pages/member.vue`.

**Tests:** member with cap=2 already has 2 entries this month → tap rejected with `MONTHLY_CAP_EXCEEDED`.

**Acceptance:** member with cap reaches limit → tap rejected with Indonesian message; admin UI shows current usage / cap.

---

### [B2] Tiered tariff matrix (`Jam > Biaya`)

**Severity:** medium
**Files:**
- `parking-system-v2/api/app/models/vehicle_type.py` or new `tariff_tier.py`
- `parking-system-v2/api/app/services/tariff.py`
- `parking-system-v2/api/app/routes/vehicle_types.py`
- `parking-system-v2/frontend/pages/setting.vue` (tariff editor UI)

**Problem:**
`api/app/services/tariff.py` does `hours × hourly_rate, capped at daily_cap`. COMPASS supports arbitrary tiers (e.g. "0–6h flat Rp 6,000; 7th h +1,000; 24h cap Rp 100,000"). Indonesian malls commonly use this exact structure.

**Fix:**

1. Add `TariffTier` model (one-to-many with `VehicleType`):

```python
class TariffTier(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "tariff_tiers"

    vehicle_type_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vehicle_types.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    from_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    """Lower bound (inclusive). Example: 0, 6, 7, 24."""
    fee: Mapped[int] = mapped_column(Integer, nullable=False)
    """Fee in Rupiah at this hour (cumulative model — see calculate_tariff_tiered)."""
```

2. New calculator:

```python
def calculate_tariff_tiered(
    duration_hours: int,
    tiers: list[TariffTier],
    grace_minutes: int = 0,
) -> int:
    """Tier resolution per COMPASS Bab 6 'Master Tarif Parkir':

    Tiers stored as (from_hour, fee) sorted ascending. The fee for `n` hours
    is the fee whose `from_hour` is the largest <= n.

    Example tiers: [(0, 6000), (6, 7000), (7, 8000), (24, 100000)]
       1h → 6000  (matches from_hour=0)
       6h → 7000  (matches from_hour=6)
       7h → 8000  (matches from_hour=7)
       24h → 100000 (matches from_hour=24)
       30h → 100000 + 6000 (24h cap + a fresh "first tier" cycle)
                  ↑ implementation choice — see tests
    """
    sorted_tiers = sorted(tiers, key=lambda t: t.from_hour)
    if duration_hours <= 0:
        return 0
    if grace_minutes and duration_hours * 60 <= grace_minutes:
        return 0
    # Find the tier
    fee = 0
    for t in sorted_tiers:
        if t.from_hour <= duration_hours:
            fee = t.fee
        else:
            break
    return fee
```

Decide explicitly with the client whether tariffs **roll over after 24h** (cap + new cycle) or stay capped. Document the choice in the function docstring.

3. Backwards compatibility: if `vehicle_type.tariff_tiers` is empty, fall back to `hourly_rate × hours, capped at daily_cap` (existing logic). This keeps existing deployments working.

4. Service flag: `vehicle_type.use_tiered_tariff: bool` (default False).

5. Admin UI: in `frontend/pages/setting.vue`, when editing a Vehicle Type, show a tier table editor (rows of `from_hour | fee | delete`). Save together with the vehicle type.

**Tests:** the four examples from the docstring above as parametric cases.

**Acceptance:** mall client can configure flat-rate-then-stepped-then-capped pricing entirely through UI.

---

### [B3] Lost-ticket fine flow with full identity capture

**Severity:** medium
**Files:**
- `parking-system-v2/api/app/models/lost_ticket_record.py` (new)
- `parking-system-v2/api/app/routes/lost_ticket.py` (new)
- `parking-system-v2/api/app/services/payment.py`
- `parking-system-v2/frontend/pages/pos.vue` + new `frontend/components/pos/LostTicketDialog.vue`
- `parking-system-v2/api/tests/test_lost_ticket.py`

**Problem:**
`is_lost_ticket` boolean and `vehicle_type.lost_ticket_penalty` exist, but there's no flow for the cashier to:
1. Capture driver's STNK (vehicle ID), KTP (national ID), name, address, RT/RW, kelurahan, kecamatan, kota.
2. Apply the `lost_ticket_penalty` as the fee.
3. Print a denda receipt.
4. Open the gate.

COMPASS Bab 5 "Denda Tiket Hilang" describes exactly this form.

**Fix:**

1. Model:
```python
class LostTicketRecord(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "lost_ticket_records"

    parking_transaction_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("parking_transactions.id"), nullable=True
    )
    plate_number: Mapped[str] = mapped_column(String(20), nullable=False)
    driver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    driver_id_number: Mapped[str] = mapped_column(String(32), nullable=False)
    driver_id_type: Mapped[str] = mapped_column(String(20), default="KTP")  # KTP, SIM, Passport
    address: Mapped[str | None] = mapped_column(Text)
    rt: Mapped[str | None] = mapped_column(String(10))
    rw: Mapped[str | None] = mapped_column(String(10))
    kelurahan: Mapped[str | None] = mapped_column(String(100))
    kecamatan: Mapped[str | None] = mapped_column(String(100))
    kota: Mapped[str | None] = mapped_column(String(100))
    penalty_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    paid_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    operator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    receipt_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
```

2. Endpoint `POST /api/lost-tickets`:
```python
# api/app/routes/lost_ticket.py
@router.post("", response_model=LostTicketResponse, status_code=201)
async def create_lost_ticket(
    data: LostTicketCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_operator),
) -> LostTicketResponse:
    """Process lost-ticket fine, create transaction, open gate, print receipt."""
```

3. POS integration: add a "TIKET HILANG" button in `QuickActionBar` that opens `LostTicketDialog.vue`. After save, the regular gate-open flow runs.

4. Receipt print: extend `workers/critical/print_worker.py` with a `print_lost_ticket_receipt` template that mirrors COMPASS layout (header + form fields + total + signature block).

**Acceptance:**
- Cashier can press "Tiket Hilang", fill driver identity form, charge `lost_ticket_penalty`, gate opens, receipt prints, record persists.
- Admin can browse lost-ticket records by date in the transaksi page (new tab).

---

### [B4] Free-out / "Parkir Gratis" exit flow

**Severity:** medium
**Files:**
- `parking-system-v2/api/app/services/payment.py`
- `parking-system-v2/api/app/routes/payments.py`
- `parking-system-v2/frontend/pages/pos.vue`
- `parking-system-v2/frontend/components/pos/QuickActionBar.vue`

**Problem:**
COMPASS Bab 5 "Pembayaran Parkir Free Parking" — operator can mark a ticket free-out without payment (validation, comp, etc.). v2 has no such operation.

**Fix:**

1. Add endpoint `POST /api/payments/free-out` that takes `{transaction_id, reason}`, creates a transaction with `payment_method="FREE_OUT"`, `fee=0`, `paid_amount=0`, links to operator, then opens the gate.

2. Add "FREE OUT" button in POS (keyboard shortcut `F4`). Require a reason from a configurable dropdown (Validation Voucher, Manager Comp, Staff, Damaged Equipment).

3. Reports filter: free-outs visible separately from cash/RFID/emoney.

4. RBAC: only operators with role `supervisor`/`admin` can free-out (require_role check).

**Acceptance:** supervisor can free-out a ticket; reason and operator are recorded; reports show free-outs distinctly.

---

### [B5] Reprint ticket (entrance)

**Severity:** medium
**Files:**
- `parking-system-v2/daemons/gate_in.py`
- `parking-system-v2/api/app/routes/gates_unified.py`
- `parking-system-v2/frontend/pages/gate-in.vue`

**Problem:**
COMPASS entrance app has a "REPRINT TICKET" button. v2 entrance daemon has `cmd_pr4` available but no operator-triggered reprint endpoint.

**Fix:**

1. Endpoint `POST /api/gates/{gate_id}/reprint-last-ticket` (admin/operator).

2. Daemon command handler `reprint_last_ticket` → fetch the last `ParkingTransaction` for this gate, regenerate ESC/POS, send via `cmd_pr4`.

3. Gate-in monitoring page: add a "Reprint Ticket Terakhir" button next to the gate status.

**Acceptance:** clicking the button reprints the ticket from the last entry at that gate.

---

### [B6] Configurable ticket header/footer text masters

**Severity:** medium
**Files:**
- `parking-system-v2/api/app/models/setting.py` (already exists for general settings)
- `parking-system-v2/daemons/gate_in.py`
- `parking-system-v2/workers/critical/print_worker.py`
- `parking-system-v2/frontend/pages/setting.vue`

**Problem:**
COMPASS has masters `Berita Tiket Masuk` (entry-ticket footer text, multi-line) and `Berita Bukti Bayar` (payment-receipt footer). v2 hardcodes ticket text in `daemons/gate_in.py:553-563`.

**Fix:**

1. Add settings keys (in existing Setting table, group=`print`):
   - `ticket_header_lines` — JSON array of strings, e.g. `["TIKET PARKIR", "MALL ABC"]`
   - `ticket_footer_lines` — array.
   - `receipt_header_lines` — array.
   - `receipt_footer_lines` — array.

2. Refactor ESC/POS builder in `gate_in.py` and `print_worker.py` to read these settings (cached via `useWebsiteStore` server-side equivalent — already exists in `shared/config.py`-pattern).

3. Admin UI: a "Print Templates" tab in `setting.vue` with multi-line text areas for each.

**Acceptance:** changing footer text in admin UI takes effect at the next print without restarting any service.

---

### [B7] Shift close with cash reconciliation report

**Severity:** medium
**Files:**
- `parking-system-v2/api/app/models/shift_close.py` (new)
- `parking-system-v2/api/app/routes/shift_close.py` (new)
- `parking-system-v2/workers/critical/print_worker.py` (new template)
- `parking-system-v2/frontend/pages/pos.vue` + new dialog
- `parking-system-v2/frontend/pages/setting.vue` (close history list)

**Problem:**
COMPASS Bab 5 "Penutupan Shift dan Pelaporan Pendapatan" — at end of shift, cashier counts physical cash, system computes expected cash from shift transactions, prints a closing report, resets POS counters. v2's `/api/shifts` is just CRUD over shift definitions.

**Fix:**

1. Model `ShiftClose`:
   - `shift_id`, `operator_id`, `closed_at`, `expected_cash`, `actual_cash`, `variance`, `transaction_count`, `revenue_breakdown` (JSONB), `notes`, `printed_receipt_path`.

2. Endpoint `POST /api/shift-closes`:
   - Sum cash transactions assigned to operator since last close.
   - Sum free-outs, lost-ticket fines, RFID, e-money for the report.
   - Compute variance = `actual_cash - expected_cash`.
   - Create `ShiftClose`, update operator session, enqueue print job.

3. POS UI: "Tutup Shift" button (keyboard `F12`). Dialog: shows expected, asks for actual, confirms, prints receipt.

**Acceptance:** end-to-end shift close from POS prints a Berita-Acara-style report; close records persist; admin can review history.

---

### [B8] CSV import for members and tariffs

**Severity:** medium
**Files:**
- `parking-system-v2/api/app/routes/members.py` (`POST /api/members/import-csv`)
- `parking-system-v2/api/app/routes/vehicle_types.py` (`POST /api/vehicle-types/{id}/tariff-tiers/import-csv`)
- `parking-system-v2/frontend/pages/member.vue` (Import button)
- `parking-system-v2/frontend/pages/setting.vue`

**Problem:**
COMPASS Bab 6 "Import Data Dari File" supports CSV upload for member master and tariff masters. v2 has no import.

**Fix:**

1. Endpoint accepts `multipart/form-data` with `file: UploadFile`. Parse with `csv.DictReader`, validate per-row, return `{imported: n, errors: [{row, message}]}`.

2. Member CSV columns (per COMPASS spec):
   - `id_kartu` (text, max 10, required)
   - `kode_tag_kartu` (hex text, max 24)
   - `nama` (text, max 50, required)
   - `bagian` (text, max 50)
   - `berlaku_hingga` (date dd-mm-yyyy, optional)
   - `batas_pakai_bulanan` (int, optional)

3. Validation: skip rows with missing required fields (collect errors), upsert by `card_number`.

4. Frontend: "Import CSV" button on member page → file picker → progress modal → result toast.

**Acceptance:** uploading the COMPASS-format CSV creates/updates members in one transaction; errors are surfaced clearly.

---

### [B9] Extra reports (gate activity, log akses, log tamu, foto akses)

**Severity:** medium
**Files:**
- `parking-system-v2/api/app/routes/reports.py`
- `parking-system-v2/api/app/services/report_export.py`
- `parking-system-v2/frontend/pages/report.vue`

**Problem:**
COMPASS Bab 6 has 9 report types. v2 has summary/daily/weekly/monthly/emoney/shift (4 distinct kinds). Missing: gate-activity counts, per-gate access log, guest access log, member access log, member roster, photo browse.

**Fix:**
Add endpoints:
- `GET /api/reports/gate-activity?date_from&date_to` — count of entries/exits per gate
- `GET /api/reports/access-log?gate_id&date_from&date_to` — every transaction at a gate
- `GET /api/reports/guest-log?date_from&date_to` — `member_id IS NULL` transactions
- `GET /api/reports/member-log?member_id&date_from&date_to`
- `GET /api/reports/member-roster?is_active=&group_id=`
- `GET /api/reports/photo-access?date_from&date_to&card_number=` — paginated thumbnails of `entry_snapshot` + `exit_snapshot`

Each gets a CSV/PDF/XLSX export via `report_export.py`.

Frontend: extend `report.vue` with new report-type chips and filters.

**Acceptance:** all 9 COMPASS reports have at least one endpoint and a way to view in admin UI.

---

## Phase 4 — PASSTI protocol completeness

### [P1] Implement Mifare commands (UID / Read / Write)

**Severity:** low
**Files:**
- `parking-system-v2/protocols/passti/commands.py`
- `parking-system-v2/protocols/tests/test_passti_mifare.py`

**Problem:**
V1.12 §III.F defines `EF 01 07` with sub-commands `00` (Get UID), `01` (Read Block), `02` (Write Block). Not implemented in `commands.py`. Required only for Luminos/proprietary card writeback.

**Fix:**

```python
# protocols/passti/commands.py
def cmd_mifare_uid(timeout_sec: int) -> bytes:
    return build_frame(CMD_MIFARE, bytes([0x00]) + _bcd_timeout(timeout_sec))

def cmd_mifare_read(block: int, key_type: int, key: bytes, timeout_sec: int) -> bytes:
    if not 0 <= block <= 0x3F:
        raise ValueError(f"Block must be 0..63, got {block}")
    if key_type not in (0x0A, 0x0B):
        raise ValueError(f"Key type must be 0x0A or 0x0B, got {key_type:#x}")
    if len(key) != 6:
        raise ValueError(f"Key must be 6 bytes, got {len(key)}")
    return build_frame(
        CMD_MIFARE,
        bytes([0x01, block, key_type]) + key + _bcd_timeout(timeout_sec),
    )

def cmd_mifare_write(block: int, data: bytes, timeout_sec: int) -> bytes:
    if not 0 <= block <= 0x3F:
        raise ValueError(f"Block must be 0..63, got {block}")
    if len(data) != 16:
        raise ValueError(f"Data must be 16 bytes, got {len(data)}")
    return build_frame(
        CMD_MIFARE,
        bytes([0x02, block]) + data + _bcd_timeout(timeout_sec),
    )

def parse_mifare_uid_response(body: bytes) -> dict:
    if len(body) < 8:
        return {"ok": False, "error": "Body too short"}
    return {
        "ok": True,
        "card_type_byte": body[0],  # 0x41 'A' or 0x4D 'M'
        "uid": body[1:8].hex().upper(),
    }

def parse_mifare_data_response(body: bytes) -> dict:
    if len(body) < 16:
        return {"ok": False, "error": "Body too short"}
    return {"ok": True, "data": body[:16]}
```

**Tests:** parameterized against V1.12 §IV "11. Command Mifare" example vectors.

**Acceptance:** all three mifare commands available; tests pass.

---

### [P2] Implement GetReaderInfo and use it for adaptive display

**Severity:** low
**Files:**
- `parking-system-v2/protocols/passti/commands.py`
- `parking-system-v2/protocols/passti/transport.py`

**Problem:**
V1.12 §III.I defines `EF 01 0C`. Currently `cmd_display` (`commands.py:73-79`) hardcodes 16-char width — wrong for readers with bigger LCDs.

**Fix:**

1. Add command + parser:
```python
def cmd_get_reader_info() -> bytes:
    return build_frame(CMD_GET_READER_INFO)

def parse_reader_info_response(body: bytes) -> dict:
    """Returns {device_type, sn, version, display_info: {lines, chars_per_line, ...}}."""
    # Parse fixed-length prefix (1+20+3) + TLV (A1/A2/A3/A4) per V1.12 §III.I
    ...
```

2. Cache reader info on transport connect; expose via `transport.reader_info`.

3. Update `cmd_display(text)` to truncate/pad to `transport.reader_info.chars_per_line` instead of hardcoded 16.

**Acceptance:** `cmd_display` adapts to each reader's actual width.

---

### [P3] Capture variable-length CardLog in deduct response parser

**Severity:** low (informational; settlement uses body hex which is correct after C1)
**Files:**
- `parking-system-v2/protocols/passti/commands.py`

**Problem:**
`parse_deduct_response` (commands.py:103-118) caps at `body[:40]` and discards `nBytes Card Log transaction`. The card log is needed for any future BRI-debug correlation.

**Fix:**

```python
def parse_deduct_response(body: bytes) -> dict:
    if len(body) < 40:
        return {"ok": False, "error": "Body too short"}
    return {
        "ok": True,
        "card_type_code": body[0],
        "card_type": CARD_TYPES.get(body[0], f"Unknown({body[0]:02X})"),
        "mid": body[1:9].hex().upper(),
        "tid": body[9:13].hex().upper(),
        "datetime_bcd": body[13:20].hex(),
        "card_number": body[20:28].hex().upper(),
        "deducted": int.from_bytes(body[28:32], "big"),
        "remaining": int.from_bytes(body[32:36], "big"),
        "trans_counter": int.from_bytes(body[36:40], "big"),
        "card_log": body[40:].hex().upper(),  # NEW
    }
```

**Acceptance:** card_log field populated; tests verify against V1.12 §IV appendix vector.

---

### [P4] Fix DirectSerialTransport response read

**Severity:** low (only affects deployments using direct serial, not controller passthrough)
**Files:**
- `parking-system-v2/protocols/passti/transport.py`

**Problem:**
`DirectSerialTransport.send_recv` (`transport.py:154`):
```python
raw = self._serial.read_until(expected=bytes([frame[-1]]))
```
This terminates on the LRC byte of the **command** frame, not the response. The response LRC differs whenever `cmd != response data`, so this routinely truncates or over-reads.

**Fix:**

```python
async def send_recv(self, frame: bytes, timeout: float = 10.0) -> dict[str, Any]:
    import serial
    if self._serial is None:
        self._serial = serial.Serial(port=self._port, baudrate=self._baudrate, timeout=timeout)

    self._serial.write(frame)

    # Read response by length prefix (PASSTI frame: STX | LEN-H | LEN-L | data | LRC)
    header = self._serial.read(3)
    if len(header) != 3 or header[0] != 0x02:
        return {"ok": False, "error": "No STX or short read", "raw": header.hex()}
    payload_len = (header[1] << 8) | header[2]
    rest = self._serial.read(payload_len + 1)  # payload + LRC
    raw = header + rest

    from protocols.passti.frame import parse_response
    return parse_response(raw)
```

**Acceptance:** direct-serial deployments respond reliably; the controller-passthrough path is untouched.

---

## Phase 5 — Frontend bugs

### [F1] Fix faked pagination total in transaksi page

**Severity:** high (silent data correctness issue for admins)
**Files:**
- `parking-system-v2/api/app/routes/transactions.py`
- `parking-system-v2/api/app/utils/pagination.py`
- `parking-system-v2/api/app/schemas/common.py`
- `parking-system-v2/frontend/composables/useApi.js` (or equivalent)
- `parking-system-v2/frontend/pages/transaksi.vue`
- `parking-system-v2/frontend/components/DataTable.vue`

**Problem:**
`frontend/pages/transaksi.vue:172-174` fakes total because `GET /api/transactions` returns a bare array. Real total never reaches the UI.

**Fix:**

1. Define a generic paginated response schema in `api/app/schemas/common.py`:

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int

    @property
    def has_more(self) -> bool:
        return self.skip + len(self.items) < self.total
```

2. Update `paginated_list` (or its callers) to return `(items, total)`. In `routes/transactions.py`, change the list endpoint:

```python
@router.get("", response_model=PaginatedResponse[TransactionResponse])
async def list_transactions(
    pagination: PaginationParams = Depends(),
    ...
) -> PaginatedResponse[TransactionResponse]:
    base_stmt = select(ParkingTransaction)
    # ...filters...
    total_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await db.execute(total_stmt)).scalar_one()

    items_stmt = base_stmt.offset(pagination.skip).limit(pagination.limit)
    rows = (await db.execute(items_stmt)).scalars().all()

    return PaginatedResponse(
        items=[TransactionResponse.model_validate(r) for r in rows],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )
```

3. Frontend `transaksi.vue:loadTransactions`:

```js
const result = await fetchApi(`/api/transactions?${qs.toString()}`)
transactions.value = result.items
transactionTotal.value = result.total
```

Remove the `.length === pageSize ? +1 : ...` hack.

4. Repeat the schema migration for any other list endpoint the FE paginates against (members, manual-open-logs, abandoned-vehicle-logs, etc.).

**Tests:**
- Backend: `pytest api/tests/test_transactions.py -k paginat` — assert response shape.
- Frontend: vitest mock returning `{items: [...], total: 250}` — assert DataTable's pagination shows correct page count.

**Acceptance:** UI shows accurate "Page 1 of 13" etc; jumping to page 13 returns the right rows; no client-side total faking remains anywhere.

---

### [F2] Toast on CRUD errors in admin pages

**Severity:** high (silent failure erodes trust)
**Files:**
- `parking-system-v2/frontend/composables/useCrud.js`
- `parking-system-v2/frontend/composables/useApi.js`
- `parking-system-v2/frontend/pages/setting.vue`
- `parking-system-v2/frontend/pages/member.vue`
- `parking-system-v2/frontend/pages/transaksi.vue`
- `parking-system-v2/frontend/plugins/toast.client.js` (verify exists)

**Problem:**
Every admin CRUD handler ends `catch (e) { console.error(e) }`. The user gets no feedback. POS uses `vue-sonner` correctly but admin pages don't import it.

**Fix:**

1. Ensure a global `useToast()` composable wrapping vue-sonner exists (it likely already does — `useNuxtApp().$toast`). If not, wrap once.

2. Update `useCrud` to toast on error by default:

```js
// composables/useCrud.js
import { toast } from 'vue-sonner'

export function useCrud(endpoint) {
  const { fetchApi } = useApi()

  async function list(params) {
    try {
      return await fetchApi(`${endpoint}${params ? '?' + new URLSearchParams(params) : ''}`)
    } catch (e) {
      toast.error(`Gagal memuat data: ${e.message || 'unknown'}`)
      throw e
    }
  }

  async function create(data) {
    try {
      const result = await fetchApi(endpoint, { method: 'POST', body: JSON.stringify(data) })
      toast.success('Data berhasil dibuat')
      return result
    } catch (e) {
      toast.error(`Gagal menyimpan: ${e.message || 'unknown'}`)
      throw e
    }
  }

  // similarly update, remove
  return { list, create, update, remove }
}
```

3. Remove `console.error` boilerplate from page-level handlers; let `useCrud` handle messaging.

**Tests:** vitest with mocked `vue-sonner`; trigger a 500 response and assert `toast.error` was called.

**Acceptance:** any CRUD failure on admin pages produces a visible Indonesian toast; success states also confirm.

---

### [F3] Lazy-load admin tabs

**Severity:** medium
**Files:**
- `parking-system-v2/frontend/pages/transaksi.vue`
- `parking-system-v2/frontend/pages/setting.vue`
- `parking-system-v2/frontend/pages/member.vue`

**Problem:**
`transaksi.vue:onMounted` loads all 3 tabs upfront; only one is visible. Wastes 2 round-trips per page visit.

**Fix:**

```js
// Replace the eager onMounted with watcher-based lazy-loading
const loaded = reactive({ transactions: false, 'manual-opens': false, abandoned: false })

watch(activeTab, (tab) => {
  if (loaded[tab]) return
  if (tab === 'transactions') loadTransactions()
  if (tab === 'manual-opens') loadManualOpens()
  if (tab === 'abandoned') loadAbandoned()
  loaded[tab] = true
}, { immediate: true })
```

Apply same pattern to setting.vue and member.vue.

**Acceptance:** opening the page issues exactly one API call; switching tabs lazily loads.

---

## Phase 6 — Frontend structure

### [F4] Extract `useCrudPage` composable + split admin pages

**Severity:** medium
**Files:**
- `parking-system-v2/frontend/composables/useCrudPage.js` (new)
- `parking-system-v2/frontend/components/admin/CrudTab.vue` (new)
- `parking-system-v2/frontend/pages/setting.vue` (split)
- `parking-system-v2/frontend/pages/member.vue` (split)

**Problem:**
`setting.vue` is 221 lines packing 5 tabs of CRUD; `member.vue` is similar. The boilerplate (`load* / open*Modal / save* / confirmDelete*`) repeats 3-5×.

**Fix:**

1. New composable `useCrudPage(endpoint, { columns, fields })`:

```js
// composables/useCrudPage.js
import { ref, computed } from 'vue'
export function useCrudPage(endpoint, { fields, columns }) {
  const crud = useCrud(endpoint)
  const items = ref([])
  const loading = ref(false)
  const modalVisible = ref(false)
  const editing = ref(false)
  const form = ref({})
  const submitting = ref(false)
  const deleteDialog = ref({ visible: false, target: null })

  async function load() { loading.value = true; try { items.value = await crud.list() } finally { loading.value = false } }
  function openCreate() { editing.value = false; form.value = {}; modalVisible.value = true }
  function openEdit(row) { editing.value = true; form.value = { ...row }; modalVisible.value = true }
  async function save(data) {
    submitting.value = true
    try {
      if (editing.value) await crud.update(data.id, data)
      else await crud.create(data)
      modalVisible.value = false
      await load()
    } finally { submitting.value = false }
  }
  function confirmDelete(row) { deleteDialog.value = { visible: true, target: row } }
  async function executeDelete() {
    submitting.value = true
    try { await crud.remove(deleteDialog.value.target.id); deleteDialog.value.visible = false; await load() }
    finally { submitting.value = false }
  }

  return { items, loading, modalVisible, editing, form, submitting, deleteDialog,
           load, openCreate, openEdit, save, confirmDelete, executeDelete,
           fields, columns }
}
```

2. New component `<CrudTab>` that takes a `useCrudPage` return value and renders DataTable + CrudModal + ConfirmDialog wired up.

3. Split `setting.vue` tabs into separate components:
   - `frontend/components/admin/SettingsSiteInfo.vue`
   - `frontend/components/admin/SettingsGeneral.vue`
   - `frontend/components/admin/SettingsVehicleTypes.vue`
   - `frontend/components/admin/SettingsShifts.vue`
   - `frontend/components/admin/SettingsAreas.vue`
   - `frontend/components/admin/SettingsTariffTiers.vue` (new — for B2)
   - `frontend/components/admin/SettingsPrintTemplates.vue` (new — for B6)

4. `setting.vue` becomes a tab-switcher only.

**Acceptance:**
- `setting.vue` and `member.vue` are < 60 lines each.
- New admin features (B1-B9) drop in as new components, not page edits.

---

### [F5] Sidebar navigation in default layout

**Severity:** medium
**Files:**
- `parking-system-v2/frontend/layouts/default.vue`
- `parking-system-v2/frontend/components/admin/Sidebar.vue` (new)

**Problem:**
Admin user has to backtrack to dashboard between sections. No persistent nav.

**Fix:**

1. Build `<AdminSidebar>` with collapsible sections (Operasional / Master Data / Laporan / Sistem). Use Lucide icons.

2. Layout becomes:

```vue
<template>
  <div class="flex h-screen">
    <AdminSidebar :collapsed="collapsed" @toggle="collapsed = !collapsed" />
    <div class="flex-1 flex flex-col overflow-hidden">
      <AdminTopbar />
      <main class="flex-1 overflow-y-auto p-6"><slot /></main>
    </div>
  </div>
</template>
```

3. Active route highlighting via `useRoute()`.

4. Admin-only items hidden via `authStore.isAdmin`.

**Acceptance:** any admin page → click sidebar item → navigate without trip to /.

---

### [F6] Field grouping in `<CrudModal>`

**Severity:** medium
**Files:**
- `parking-system-v2/frontend/components/CrudModal.vue`

**Problem:**
Once entities (Member with monthly cap + lost-ticket identity capture + receipt prefs) get 12+ fields, a flat modal gets unwieldy.

**Fix:**

Extend the `fields` prop to accept either a flat array (current) or a grouped form:

```js
fields: [
  { group: 'Identitas', items: [
    { prop: 'name', label: 'Nama', type: 'text', required: true },
    { prop: 'card_number', label: 'Nomor Kartu', type: 'text', required: true },
  ]},
  { group: 'Kontak', items: [
    { prop: 'phone', label: 'Telepon', type: 'text' },
    ...
  ]},
]
```

Render groups as `<fieldset>` with `<legend>` styled as section header.

For complex entities, escalate to full-page edit (`/member/:id/edit`) — not a modal.

**Acceptance:** CrudModal can render grouped forms; no entity exceeds 6 fields per group.

---

### [F7] Replace inline SVG strings with lucide-vue components

**Severity:** low
**Files:**
- `parking-system-v2/frontend/pages/index.vue`

**Problem:**
`index.vue:78-86` defines 7 SVGs as raw strings. `lucide-vue-next` is already a dep.

**Fix:**

```vue
<script setup>
import {
  ArrowRightCircle, FileText, Users, BarChart, Bell, Settings, Cpu,
} from 'lucide-vue-next'

const allModules = [
  { to: '/gate-in', title: 'Gate In Monitor', ..., icon: ArrowRightCircle },
  { to: '/transaksi', title: 'Transaksi', ..., icon: FileText },
  // ... etc.
]
</script>
```

Update `<DashboardModuleTile>` to render `<component :is="icon" />` instead of `v-html`.

**Acceptance:** no `v-html` for icons anywhere; consistent stroke widths and theming.

---

## Phase 7 — Frontend polish

### [F8] DateRangePicker with presets

**Severity:** medium
**Files:**
- `parking-system-v2/frontend/components/ui/date-range-picker/` (new)
- `parking-system-v2/frontend/pages/transaksi.vue`
- `parking-system-v2/frontend/pages/report.vue`

**Problem:** Native `<input type="date">` is slow for date-range workflows.

**Fix:** build (or vendor from shadcn-vue calendar) a popover with preset chips: Hari Ini / Kemarin / 7 Hari Terakhir / Minggu Ini / Bulan Ini / Bulan Lalu / Custom. Returns `{from, to}` ISO strings.

Replace native date inputs in `transaksi.vue` and `report.vue`.

**Acceptance:** common date ranges chosen with one click; custom range still possible.

---

### [F9] Empty states + skeleton loaders

**Severity:** medium
**Files:**
- `parking-system-v2/frontend/components/DataTable.vue`
- `parking-system-v2/frontend/components/ui/empty-state/EmptyState.vue` (new)
- `parking-system-v2/frontend/components/ui/skeleton/Skeleton.vue` (new)

**Problem:** No empty/skeleton states; users see nothing or a spinner.

**Fix:**
- `<Skeleton>` mirrors row shape during initial load.
- `<EmptyState>` accepts `icon`, `title`, `description`, `cta`. Render in DataTable when `data.length === 0 && !loading`.

Apply to all DataTable consumers.

**Acceptance:** every list view has either skeleton (loading) or illustrated empty state with CTA.

---

### [F10] POS idle-state warmth

**Severity:** low
**Files:**
- `parking-system-v2/frontend/components/pos/PosUnifiedView.vue`

**Problem:** IDLE shows `---` plate at 30% opacity — silent.

**Fix:** in the empty-state branch, swap the placeholder for:
- A gentle pulsing parking icon
- "Menunggu kendaraan berikutnya"
- Gate name + shift name
- Hint: "Scan barcode atau ketik nomor plat untuk mulai"

Test pulse animation (`animate-pulse` Tailwind class) doesn't tank performance on low-end booth PCs.

**Acceptance:** IDLE state feels intentional, not blank.

---

### [F11] Bulk actions in DataTable

**Severity:** medium
**Files:**
- `parking-system-v2/frontend/components/DataTable.vue`
- `parking-system-v2/frontend/components/admin/BulkActionBar.vue` (new)

**Problem:** No multi-select; everything is row-by-row.

**Fix:**
1. Add optional `selectable` prop to `<DataTable>`.
2. When enabled: prepend a checkbox column, header has select-all.
3. `<BulkActionBar>` slides up when `selected.length > 0`, exposes actions: Hapus, Aktifkan, Non-aktifkan, Export Selected.

API endpoints accept `{ids: number[]}` for bulk operations:
- `DELETE /api/members/bulk?ids=1,2,3`
- `PATCH /api/members/bulk-status?status=inactive` body: `{ids: [...]}`

**Acceptance:** admin can select 50 expired members → "Non-aktifkan" → confirm → all updated in a single API call.

---

### [F12] PIN/numeric login mode

**Severity:** low
**Files:**
- `parking-system-v2/frontend/pages/login.vue`
- `parking-system-v2/api/app/routes/auth.py` (add PIN field on User if needed)

**Problem:** Booth tablets don't always have keyboards; password typing is slow.

**Fix:**
1. Toggle button on login page: "Login PIN".
2. PIN mode: shows numeric keypad (Tailwind grid), 6-digit PIN input, Login button.
3. Backend: optional `pin_hash` on User, separate `POST /api/auth/login-pin` endpoint, audit-logged.

**Acceptance:** cashier can log in entirely via touchscreen.

---

### [F13] Keyboard shortcuts in admin pages

**Severity:** low
**Files:**
- `parking-system-v2/frontend/composables/useKeyboard.js`
- All admin pages

**Problem:** Only POS uses `useKeyboard`.

**Fix:** add to admin pages:
- `/` → focus search box
- `n` (or `Insert`) → open New modal
- `r` → refresh
- `Esc` → close modal (likely already works)
- `Enter` in search → submit

**Acceptance:** admin can navigate and create rows entirely via keyboard.

---

### [F14] Theme switcher / forced night mode

**Severity:** low
**Files:**
- `parking-system-v2/frontend/composables/useColorMode.js` (new)
- `parking-system-v2/frontend/assets/css/tailwind.css`
- `parking-system-v2/frontend/components/admin/ThemeToggle.vue`

**Problem:** Semantic tokens suggest dark-mode wired up, but no toggle visible.

**Fix:**
1. Verify tailwind.css has `.dark { ... }` overrides for CSS vars.
2. `useColorMode` reads/writes `localStorage` and toggles the `dark` class on `<html>`.
3. Auto-night-mode option: read sunset time for the site's lat/long (or just 18:00–06:00 local).

**Acceptance:** theme persists across reloads; auto-night option works for 24/7 booths.

---

### [F15] Reports filter expansion

**Severity:** medium (depends on B9)
**Files:**
- `parking-system-v2/frontend/pages/report.vue`

**Problem:** Reports page is thin; filters are limited.

**Fix:** Once B9 lands, `report.vue` exposes:
- Date range (F8 component)
- Gate selector (multi-select)
- Operator selector
- Vehicle type
- Payment method
- Member group

Each report kind shows the relevant filter subset. Export buttons (CSV/PDF/XLSX) per report.

**Acceptance:** admin can pivot any report by gate/operator/vehicle type without leaving the page.

---

## Suggested execution order

If staffing one engineer:

| Sprint | Tasks | Why |
|---|---|---|
| Sprint 1 | C1, C2, C3 | One PR — blocks bank certification. All in `protocols/` and `workers/`. |
| Sprint 2 | H1, H2, H3, H4 | Settlement pipeline complete. |
| Sprint 3 | F1, F2, F3 | Frontend correctness — pagination, errors, lazy load. |
| Sprint 4 | F4, F5 | Frontend structure — refactor before adding more features. |
| Sprint 5 | B1, B2, B3 | Highest-value backend gaps (member cap, tariff tiers, lost-ticket). |
| Sprint 6 | B4, B5, B6, B7 | Remaining ops flows (free-out, reprint, templates, shift close). |
| Sprint 7 | B8, B9, F8, F9, F11 | Imports, reports, polish. |
| Sprint 8 | P1, P2, P3, P4, F6, F7, F10, F12, F13, F14, F15 | Tail items. |

---

## Verification checklist before each release

- [ ] `pytest -x -q` (all green)
- [ ] `ruff check .` (0 errors)
- [ ] `mypy .` (0 errors)
- [ ] `cd frontend && npm run lint && npm run test`
- [ ] Settlement file generated against the V1.12 §IV appendix vector matches expected hex byte-for-byte (C1 + C3 regression test)
- [ ] QR transaction excluded from settlement (C2 regression test)
- [ ] SFTP upload + response polling tested against staging bank server (H1 + H2)
- [ ] One full happy-path manual smoke: cash entry → cash exit, RFID member entry → exit, e-money entry → e-money exit
- [ ] One unhappy-path manual smoke: lost-contact mid-deduct → recovery
- [ ] Lost-ticket flow end-to-end (B3) once shipped
- [ ] Shift close prints reconciliation receipt (B7) once shipped

---

## Reference document index

| Spec | Location | Used by tasks |
|---|---|---|
| Command Protocol Reader V1.12 (PASSTI) | `parking-system/card-emoney-doc/`, `docs/Command Protocol Reader V1.12 ENG.txt` | C1, C3, P1, P2, P3, P4 |
| Format File Settlement Multibank v1.3 | `docs/Format File Settlement Multibank v1.3.txt` | C1, C2, H1, H2, H3, H4 |
| COMPASS User Manual | external PDF (request from client if needed) | B1–B9, F8, F12 |

---

*End of fix plan.*
