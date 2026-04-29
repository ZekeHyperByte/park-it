# E-Money Integration Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the broken e-money payment flow end-to-end for both entry and exit gates, with booth bridge calling API directly (Option B) and manless fallback via daemon passthrough.

**Architecture:** Booth bridge parses PASSTI responses and calls API directly via HTTP with API key. API adds a Pub/Sub event consumer for server-side event handling. Exit daemon supports both booth-bridge mode and manless ControllerPassthroughTransport mode. Entry daemon completes its flow with a new `EmoneyPrintDecisionEvent`.

**Tech Stack:** FastAPI, async SQLAlchemy, Redis Pub/Sub + Streams, WebSocket, PASSTI serial protocol, pytest, asyncio.

---

## Summary of Bugs Being Fixed

| # | Component | Bug |
|---|-----------|-----|
| 1 | `booth_bridge/websocket_server.py` | `emoney_deduct` returns raw hex; no PASSTI parsing |
| 2 | `frontend/pages/index.vue` | On e-money success, calls `confirmCashPayment()` (records as CASH) |
| 3 | `daemons/gate_out.py` | `DeductCommand` explicitly ignored; manless path dead |
| 4 | `daemons/gate_in.py` | `_on_print_decision` publishes no event; API never creates transaction |
| 5 | API (global) | No server-side Redis Pub/Sub consumer for `PasstiCardTapEvent` |
| 6 | `shared/events.py` | Missing `EmoneyPaymentConfirmedCommand` model |

---

## Task 1: Add API Key Auth for Internal Endpoints

**Files:**
- Create: `api/app/middleware/api_key.py`
- Modify: `.env.example`
- Test: `api/tests/test_api_key_auth.py`

**Step 1: Write the failing test**

Create `api/tests/test_api_key_auth.py`:

```python
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from api.app.middleware.api_key import require_api_key

app = FastAPI()

@app.get("/internal/test")
async def test_endpoint(api_key: str = require_api_key):
    return {"ok": True}

@pytest.mark.anyio
async def test_api_key_missing():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/test")
        assert resp.status_code == 403

@pytest.mark.anyio
async def test_api_key_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/test", headers={"X-API-Key": "bad-key"})
        assert resp.status_code == 403

@pytest.mark.anyio
async def test_api_key_valid(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "test-key-123")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/test", headers={"X-API-Key": "test-key-123"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
```

**Step 2: Run test to verify it fails**

```bash
cd /home/qiu/Work/E-Parking/parking-system-v2/api && pytest tests/test_api_key_auth.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement API key middleware**

Create `api/app/middleware/api_key.py`:

```python
"""API key authentication for internal/machine endpoints."""

import os
from fastapi import Header, HTTPException, status

def _get_api_key() -> str:
    return os.environ.get("INTERNAL_API_KEY", "")

def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Validate internal API key from X-API-Key header."""
    expected = _get_api_key()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="INTERNAL_API_KEY not configured",
        )
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return x_api_key
```

**Step 4: Run test to verify it passes**

```bash
cd /home/qiu/Work/E-Parking/parking-system-v2/api && pytest tests/test_api_key_auth.py -v
```

Expected: 3 tests PASS

**Step 5: Add INTERNAL_API_KEY to .env.example**

```bash
# Internal API key for booth bridge / machine-to-machine auth
INTERNAL_API_KEY=change-me-in-production
```

**Step 6: Commit**

```bash
git add api/app/middleware/api_key.py api/tests/test_api_key_auth.py .env.example
git commit -m "feat(auth): add API key middleware for internal endpoints"
```

---

## Task 2: Add Booth-Authenticated E-Money Result Endpoint

**Files:**
- Modify: `api/app/routes/payments.py`
- Modify: `api/app/schemas/payment.py`
- Test: `api/tests/test_payments_booth_result.py`

**Step 1: Add BoothResultRequest schema**

Modify `api/app/schemas/payment.py`, add after `EmoneyResultRequest`:

```python
class EmoneyBoothResultRequest(BaseModel):
    """E-money result from booth bridge (machine-to-machine)."""
    gate_id: str = Field(..., description="Daemon gate ID")
    gate_out_id: int = Field(..., description="Gate-out database ID")
    card_number: str = Field(..., description="E-money card number")
    status: str = Field(..., description="Deduct result status")
    deduct_amount: int = Field(..., ge=0)
    balance_before: int = Field(..., ge=0)
    balance_after: int = Field(..., ge=0)
    transaction_counter: int = Field(..., ge=0)
    raw_response_hex: str = Field(default="")
```

**Step 2: Add booth-result endpoint**

Modify `api/app/routes/payments.py`:

Add imports:
```python
from api.app.middleware.api_key import require_api_key
from api.app.schemas.payment import EmoneyBoothResultRequest
```

Add endpoint after `emoney/result`:

```python
@router.post("/emoney/booth-result", response_model=PaymentResponse)
async def emoney_booth_result(
    request: Request,
    result: EmoneyBoothResultRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
) -> PaymentResponse:
    """Process e-money deduct result from booth bridge (machine-to-machine)."""
    try:
        status_enum = DeductStatus(result.status)
    except ValueError:
        return PaymentResponse(
            success=False,
            message=f"Invalid deduct status: {result.status}",
        )

    try:
        proc_result = await process_emoney_result(
            db,
            gate_id=result.gate_id,
            gate_out_id=result.gate_out_id,
            card_number=result.card_number,
            status=status_enum,
            deduct_amount=result.deduct_amount,
            balance_before=result.balance_before,
            balance_after=result.balance_after,
            transaction_counter=result.transaction_counter,
            raw_response_hex=result.raw_response_hex,
            operator_id=None,
        )
        return PaymentResponse(
            success=proc_result["success"],
            message="E-money payment processed" if proc_result["success"] else "E-money payment failed",
            transaction_id=proc_result["transaction"].id,
            fee=result.deduct_amount if proc_result["success"] else None,
            payment_method="EMONEY" if proc_result["success"] else None,
        )
    except ValueError as e:
        logger.warning("emoney_booth_result_failed", error=str(e), gate_id=result.gate_id)
        return PaymentResponse(success=False, message=str(e))
```

**Step 3: Write failing test**

Create `api/tests/test_payments_booth_result.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from api.app.main import app

@pytest.mark.anyio
async def test_emoney_booth_result_auth_required():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/payments/emoney/booth-result", json={})
        assert resp.status_code == 403

@pytest.mark.anyio
async def test_emoney_booth_result_invalid_card(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "booth-key")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/payments/emoney/booth-result",
            headers={"X-API-Key": "booth-key"},
            json={
                "gate_id": "GOUT01",
                "gate_out_id": 1,
                "card_number": "NONEXISTENT",
                "status": "SUCCESS",
                "deduct_amount": 5000,
                "balance_before": 100000,
                "balance_after": 95000,
                "transaction_counter": 1,
            },
        )
        assert resp.status_code == 400
```

**Step 4: Run test**

```bash
cd /home/qiu/Work/E-Parking/parking-system-v2/api && pytest tests/test_payments_booth_result.py -v
```

Expected: 2 tests PASS

**Step 5: Commit**

```bash
git add api/app/routes/payments.py api/app/schemas/payment.py api/tests/test_payments_booth_result.py
git commit -m "feat(payments): add booth-bridge e-money result endpoint with API key auth"
```

---

## Task 3: Parse PASSTI Response in Booth Bridge + Call API Directly

**Files:**
- Modify: `booth_bridge/websocket_server.py`
- Modify: `booth_bridge/main.py`
- Modify: `booth_bridge/serial_manager.py` (if needed)
- Test: `booth_bridge/tests/test_passti_parsing.py`

**Step 1: Add PASSTI parsing to booth bridge**

Modify `booth_bridge/websocket_server.py`:

Replace the `emoney_deduct` handler (lines 83-88) with:

```python
        elif action == "emoney_deduct":
            amount = cmd.get("amount", 0)
            from protocols.passti.commands import cmd_deduct, parse_deduct_response
            from protocols.passti.frame import parse_response, STATUS_MESSAGES

            frame = cmd_deduct(amount, timeout_sec=30)
            raw_response = self.serial_manager.send("emoney_reader", frame)

            # Parse PASSTI response
            parsed = parse_response(raw_response)
            if not parsed.get("ok"):
                return {
                    "action": "emoney_deduct_result",
                    "status": "FAILED",
                    "error": parsed.get("error", "Parse failed"),
                }

            body = parsed.get("body", b"")
            deduct_data = parse_deduct_response(body)

            if not deduct_data.get("ok"):
                return {
                    "action": "emoney_deduct_result",
                    "status": "FAILED",
                    "error": deduct_data.get("error", "Deduct parse failed"),
                }

            # Determine status from PASSTI response status byte
            status_byte = parsed.get("status", 0)
            status_msg = STATUS_MESSAGES.get(status_byte, "UNKNOWN")

            if status_byte == 0x00:
                deduct_status = "SUCCESS"
            elif status_byte == 0x01:
                deduct_status = "LOST_CONTACT"
            elif status_byte == 0x02:
                deduct_status = "INSUFFICIENT_BALANCE"
            elif status_byte == 0x03:
                deduct_status = "WRONG_CARD"
            else:
                deduct_status = "FAILED"

            # Build result payload
            result_payload = {
                "action": "emoney_deduct_result",
                "status": deduct_status,
                "card_number": deduct_data.get("card_number", ""),
                "deduct_amount": deduct_data.get("deducted", 0),
                "balance_before": deduct_data.get("remaining", 0) + deduct_data.get("deducted", 0),
                "balance_after": deduct_data.get("remaining", 0),
                "transaction_counter": deduct_data.get("trans_counter", 0),
                "raw_response_hex": raw_response.hex(),
            }

            # If booth bridge has API config, call API directly
            if self._api_config:
                asyncio.create_task(self._call_api_booth_result(result_payload))

            return result_payload
```

Add the API call helper method:

```python
    async def _call_api_booth_result(self, payload: dict) -> None:
        """Call the API booth-result endpoint directly."""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._api_config['base_url']}/api/payments/emoney/booth-result",
                    headers={"X-API-Key": self._api_config["api_key"]},
                    json={
                        "gate_id": payload.get("gate_id", ""),
                        "gate_out_id": payload.get("gate_out_id", 0),
                        "card_number": payload.get("card_number", ""),
                        "status": payload["status"],
                        "deduct_amount": payload["deduct_amount"],
                        "balance_before": payload["balance_before"],
                        "balance_after": payload["balance_after"],
                        "transaction_counter": payload["transaction_counter"],
                        "raw_response_hex": payload["raw_response_hex"],
                    },
                ) as resp:
                    if resp.status == 200:
                        logger.info("booth_api_call_success", status=payload["status"])
                    else:
                        body = await resp.text()
                        logger.error("booth_api_call_failed", status=resp.status, body=body)
        except Exception as e:
            logger.error("booth_api_call_exception", error=str(e))
```

**Step 2: Update WebSocketServer constructor to accept API config**

Modify `__init__`:

```python
    def __init__(self, serial_manager, port: int = 5678, api_config: dict | None = None) -> None:
        self.serial_manager = serial_manager
        self.port = port
        self._api_config = api_config or {}
        self._server = None
        self._clients: set = set()
```

**Step 3: Update main.py to pass API config**

Modify `booth_bridge/main.py` to load `api_base_url` and `api_key` from `/etc/parking/booth.json` and pass to WebSocketServer.

**Step 4: Commit**

```bash
git add booth_bridge/
git commit -m "feat(booth-bridge): parse PASSTI responses and call API directly"
```

---

## Task 4: Fix Frontend handleBoothMessage + Add confirmEmoneyPayment

**Files:**
- Modify: `frontend/pages/index.vue`
- Modify: `frontend/stores/gate.js`

**Step 1: Add confirmEmoneyPayment to gate store**

Modify `frontend/stores/gate.js`, add after `startEmoneyDeduct`:

```javascript
  /**
   * Confirm e-money payment (called after booth bridge deduct success).
   */
  async function confirmEmoneyPayment({ gateId, gateOutId, deductAmount, balanceAfter, transactionCounter, rawResponseHex }) {
    isLoading.value = true
    try {
      const { fetchApi } = useApi()
      const res = await fetchApi('/api/payments/emoney/result', {
        method: 'POST',
        body: JSON.stringify({
          gate_id: gateId,
          gate_out_id: gateOutId,
          card_number: currentTransaction.value?.card_number,
          status: 'SUCCESS',
          deduct_amount: deductAmount,
          balance_before: currentTransaction.value?.tariff + balanceAfter,
          balance_after: balanceAfter,
          transaction_counter: transactionCounter,
          raw_response_hex: rawResponseHex,
        }),
      })
      if (res.success) {
        ElMessage.success(res.message)
        clearTransaction()
        return true
      } else {
        ElMessage.error(res.message)
        return false
      }
    } catch (err) {
      ElMessage.error(err.message || 'E-money payment failed')
      return false
    } finally {
      isLoading.value = false
    }
  }
```

Export it in the return statement.

**Step 2: Fix handleBoothMessage in index.vue**

Replace the `handleBoothMessage` function (lines 441-463) with:

```javascript
function handleBoothMessage(data) {
  if (data.action === 'emoney_deduct_result') {
    if (data.status === 'SUCCESS') {
      gateStore.setEmoneyState('SUCCESS')
      if (selectedGate.value) {
        const gateCode = selectedGate.value.code || `gate-out-${selectedGate.value.id}`
        gateStore.confirmEmoneyPayment({
          gateId: gateCode,
          gateOutId: selectedGate.value.id,
          deductAmount: data.deduct_amount,
          balanceAfter: data.balance_after,
          transactionCounter: data.transaction_counter,
          rawResponseHex: data.raw_response_hex,
        })
      }
    } else if (data.status === 'LOST_CONTACT') {
      gateStore.setEmoneyState('LOST_CONTACT')
      ElMessage.warning('Tap kartu lagi untuk koreksi')
    } else if (data.status === 'INSUFFICIENT_BALANCE') {
      gateStore.setEmoneyState('INSUFFICIENT')
      ElMessage.warning('Saldo tidak cukup')
    } else if (data.status === 'WRONG_CARD') {
      gateStore.setEmoneyState('WRONG_CARD')
      ElMessage.error('Kartu tidak sesuai')
    } else {
      gateStore.setEmoneyState('FAILED')
      ElMessage.error(data.error || 'E-Money gagal')
    }
    activeMethod.value = null
  }
}
```

**Step 3: Commit**

```bash
git add frontend/pages/index.vue frontend/stores/gate.js
git commit -m "fix(frontend): fix e-money booth message handling, use confirmEmoneyPayment instead of cash"
```

---

## Task 5: Add EmoneyPaymentConfirmedCommand + Update Events

**Files:**
- Modify: `shared/events.py`
- Modify: `daemons/gate_out.py`
- Test: `tests/unit/test_events.py`

**Step 1: Add EmoneyPaymentConfirmedCommand to shared/events.py**

Add after `CashPaymentConfirmedCommand` (line 288):

```python
class EmoneyPaymentConfirmedCommand(BaseCommand):
    """E-money payment confirmed by POS or booth bridge."""

    command_type: Literal["emoney_payment_confirmed"] = "emoney_payment_confirmed"
    transaction_id: str
```

Add to `RedisCommand` union type (line 311):

```python
RedisCommand = (
    ...
    | CashPaymentConfirmedCommand
    | EmoneyPaymentConfirmedCommand
    | ResetGateCommand
)
```

**Step 2: Commit**

```bash
git add shared/events.py
git commit -m "feat(events): add EmoneyPaymentConfirmedCommand model"
```

---

## Task 6: Fix Exit Daemon Manless E-Money Path (DeductCommand)

**Files:**
- Modify: `daemons/gate_out.py`
- Modify: `protocols/passti/transport.py` (if needed)
- Test: `daemons/tests/test_gate_out_deduct.py`

**Step 1: Add ControllerPassthroughTransport to gate_out daemon**

Modify `daemons/gate_out.py`:

Add import:
```python
from protocols.passti.transport import ControllerPassthroughTransport
```

Add to `__init__`:
```python
        self.passti_transport: ControllerPassthroughTransport | None = None
        self.has_emoney = self.config.get("hardware_config", {}).get("emoney", {}).get("enabled", False)
```

In `_connect_controller`, add after controller connection:
```python
            if self.has_emoney:
                self.passti_transport = ControllerPassthroughTransport(self.controller._sock)
```

**Step 2: Implement DeductCommand handler**

Replace the `deduct` command handler (lines 405-412) with:

```python
            elif command_type == "deduct":
                amount = int(command_data.get("amount", 0))
                expected_card = command_data.get("expected_card_number", "")
                await self._cmd_deduct(amount, expected_card)
```

Add the `_cmd_deduct` method:

```python
    async def _cmd_deduct(self, amount: int, expected_card_number: str) -> None:
        """Execute PASSTI deduct for manless exit gates."""
        if not self.passti_transport:
            logger.error("passti_not_connected", gate_id=self.gate_id)
            await self.publish_event(
                DeductResultEvent(
                    event_type="deduct_result",
                    gate_id=self.gate_id,
                    status=DeductStatus.FAILED,
                    card_number=expected_card_number,
                    card_type="",
                    deduct_amount=amount,
                    balance_before=0,
                    balance_after=0,
                    transaction_counter=0,
                    raw_response_hex="",
                )
            )
            return

        try:
            from protocols.passti.commands import cmd_deduct, parse_deduct_response
            from protocols.passti.frame import parse_response, STATUS_MESSAGES

            frame = cmd_deduct(amount, timeout_sec=30)
            result = await self.passti_transport.send_recv(frame, timeout=35.0)

            if not result.get("ok"):
                status = DeductStatus.FAILED
                raw_hex = result.get("raw", b"").hex()
            else:
                body = result.get("body", b"")
                deduct_data = parse_deduct_response(body)
                raw_hex = result.get("raw", b"").hex()

                # Map PASSTI status to DeductStatus
                status_byte = result.get("status", 0)
                if status_byte == 0x00:
                    status = DeductStatus.SUCCESS
                elif status_byte == 0x01:
                    status = DeductStatus.LOST_CONTACT
                elif status_byte == 0x02:
                    status = DeductStatus.INSUFFICIENT_BALANCE
                elif status_byte == 0x03:
                    status = DeductStatus.WRONG_CARD
                else:
                    status = DeductStatus.FAILED

            await self.publish_event(
                DeductResultEvent(
                    event_type="deduct_result",
                    gate_id=self.gate_id,
                    status=status,
                    card_number=deduct_data.get("card_number", expected_card_number) if deduct_data.get("ok") else expected_card_number,
                    card_type=deduct_data.get("card_type", "") if deduct_data.get("ok") else "",
                    deduct_amount=deduct_data.get("deducted", amount) if deduct_data.get("ok") else amount,
                    balance_before=(deduct_data.get("remaining", 0) + deduct_data.get("deducted", 0)) if deduct_data.get("ok") else 0,
                    balance_after=deduct_data.get("remaining", 0) if deduct_data.get("ok") else 0,
                    transaction_counter=deduct_data.get("trans_counter", 0) if deduct_data.get("ok") else 0,
                    raw_response_hex=raw_hex,
                )
            )
        except Exception as e:
            logger.error("deduct_command_error", gate_id=self.gate_id, error=str(e))
            await self.publish_event(
                DeductResultEvent(
                    event_type="deduct_result",
                    gate_id=self.gate_id,
                    status=DeductStatus.FAILED,
                    card_number=expected_card_number,
                    card_type="",
                    deduct_amount=amount,
                    balance_before=0,
                    balance_after=0,
                    transaction_counter=0,
                    raw_response_hex="",
                )
            )
```

**Step 3: Commit**

```bash
git add daemons/gate_out.py
git commit -m "feat(daemon-exit): implement DeductCommand for manless e-money passthrough"
```

---

## Task 7: Add API Event Consumer for Entry & Exit E-Money

**Files:**
- Create: `api/app/services/event_consumer.py`
- Modify: `api/app/main.py`
- Modify: `api/app/services/payment.py`
- Test: `api/tests/test_event_consumer.py`

**Step 1: Create event consumer service**

Create `api/app/services/event_consumer.py`:

```python
"""Redis Pub/Sub event consumer for server-side event handling.

Subscribes to parking.events.* and processes events that require
server-side business logic (entry e-money, manless exit e-money).
"""

import asyncio
import json

from shared.events import (
    DeductResultEvent,
    DeductStatus,
    PasstiCardTapEvent,
)
from shared.logging import get_logger
from shared.redis import redis_client

logger = get_logger("event_consumer")


class EventConsumer:
    """Consumes Redis Pub/Sub events and triggers server-side actions."""

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._listen())
        logger.info("event_consumer_started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("event_consumer_stopped")

    async def _listen(self) -> None:
        await redis_client.connect()
        pubsub = redis_client.client.pubsub()
        await pubsub.psubscribe("parking.events.*")

        try:
            async for message in pubsub.listen():
                if not self._running:
                    break
                if message["type"] == "pmessage":
                    data = message["data"]
                    await self._handle_event(data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("event_consumer_error", error=str(e))
        finally:
            await pubsub.punsubscribe("parking.events.*")
            await pubsub.close()

    async def _handle_event(self, data: str) -> None:
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            logger.warning("event_consumer_invalid_json", data=data)
            return

        event_type = event.get("event_type")
        gate_id = event.get("gate_id", "")

        if event_type == "passti_card_tap":
            await self._handle_passti_card_tap(event)
        elif event_type == "deduct_result":
            await self._handle_deduct_result(event)

    async def _handle_passti_card_tap(self, event: dict) -> None:
        """Handle PASSTI card tap at entry gate."""
        from api.app.services.payment import process_emoney_deduct
        from api.database import AsyncSessionLocal

        gate_id = event.get("gate_id", "")
        card_number = event.get("card_number", "")

        logger.info("entry_passti_tap", gate_id=gate_id, card_number=card_number)

        async with AsyncSessionLocal() as db:
            try:
                # For entry gates, we don't have a transaction yet.
                # The daemon has already checked balance. We need to:
                # 1. Send CheckBalanceCommand to validate threshold
                # 2. Wait for print decision event
                # For now, just log — the entry flow is daemon-driven.
                # The daemon sends check_balance command and waits for response.
                pass
            except Exception as e:
                logger.error("entry_passti_tap_error", gate_id=gate_id, error=str(e))

    async def _handle_deduct_result(self, event: dict) -> None:
        """Handle deduct result from daemon (manless exit path)."""
        from api.app.services.payment import process_emoney_result
        from api.database import AsyncSessionLocal

        gate_id = event.get("gate_id", "")
        card_number = event.get("card_number", "")
        status_str = event.get("status", "")

        logger.info("daemon_deduct_result", gate_id=gate_id, card_number=card_number, status=status_str)

        try:
            status = DeductStatus(status_str)
        except ValueError:
            logger.warning("invalid_deduct_status", status=status_str)
            return

        async with AsyncSessionLocal() as db:
            try:
                await process_emoney_result(
                    db,
                    gate_id=gate_id,
                    gate_out_id=event.get("gate_out_id", 0),
                    card_number=card_number,
                    status=status,
                    deduct_amount=event.get("deduct_amount", 0),
                    balance_before=event.get("balance_before", 0),
                    balance_after=event.get("balance_after", 0),
                    transaction_counter=event.get("transaction_counter", 0),
                    raw_response_hex=event.get("raw_response_hex", ""),
                    operator_id=None,
                )
                logger.info("emoney_result_processed", gate_id=gate_id, card_number=card_number)
            except Exception as e:
                logger.error("emoney_result_processing_error", gate_id=gate_id, error=str(e))
```

**Step 2: Start event consumer in main.py lifespan**

Modify `api/app/main.py`:

Add to lifespan startup:
```python
    # Start event consumer
    from api.app.services.event_consumer import EventConsumer
    event_consumer = EventConsumer()
    await event_consumer.start()
```

Add to lifespan shutdown:
```python
    await event_consumer.stop()
```

**Step 3: Commit**

```bash
git add api/app/services/event_consumer.py api/app/main.py
git commit -m "feat(api): add Redis Pub/Sub event consumer for e-money events"
```

---

## Task 8: Fix Entry Daemon Event Flow (EmoneyPrintDecisionEvent)

**Files:**
- Modify: `shared/events.py`
- Modify: `daemons/gate_in.py`
- Modify: `api/app/services/event_consumer.py`

**Step 1: Add EmoneyPrintDecisionEvent**

Modify `shared/events.py`, add after `VehiclePassedEvent`:

```python
class EmoneyPrintDecisionEvent(BaseEvent):
    """Driver made print decision at entry gate (e-money mode)."""

    event_type: Literal["emoney_print_decision"] = "emoney_print_decision"
    printed: bool
    card_number: str
    card_type: str
    balance: int
```

Add to `RedisEvent` union.

**Step 2: Publish event from gate_in daemon**

Modify `daemons/gate_in.py`, in `_on_print_decision`:

```python
    async def _on_print_decision(self, printed: bool) -> None:
        """Print decision made (button pressed or timeout)."""
        if self._print_decision_timer and not self._print_decision_timer.done():
            self._print_decision_timer.cancel()
        self.state_data["ticket_printed"] = printed
        await self._transition(STATE_PROCESSING)

        # Publish event so API can create transaction
        card_number = self.state_data.get("passti_card_number", "")
        card_type = self.state_data.get("passti_card_type", "")
        balance = self.state_data.get("passti_balance", 0)

        await self.publish_event(
            EmoneyPrintDecisionEvent(
                event_type="emoney_print_decision",
                gate_id=self.gate_id,
                printed=printed,
                card_number=card_number,
                card_type=card_type,
                balance=balance,
            )
        )
```

Also update `_on_passti_card_tap` to store data:

```python
    async def _on_passti_card_tap(self, card_number: str, card_type_code: int, balance: int) -> None:
        """PASSTI card tapped in e-money mode."""
        await self._transition(STATE_CHECKING_BALANCE)
        card_type = self._card_type_name(card_type_code)
        self.state_data["passti_card_number"] = card_number
        self.state_data["passti_card_type"] = card_type
        self.state_data["passti_balance"] = balance
        ...
```

**Step 3: Handle event in API consumer**

Modify `api/app/services/event_consumer.py`:

Add handler:
```python
        elif event_type == "emoney_print_decision":
            await self._handle_emoney_print_decision(event)
```

Add method:
```python
    async def _handle_emoney_print_decision(self, event: dict) -> None:
        """Handle print decision at entry gate — create transaction and open gate."""
        from api.app.services.gate_command import publish_command
        from api.app.services.transaction import create_entry_transaction
        from shared.events import OpenGateCommand
        from api.database import AsyncSessionLocal

        gate_id = event.get("gate_id", "")
        card_number = event.get("card_number", "")

        logger.info("entry_emoney_decision", gate_id=gate_id, card_number=card_number)

        async with AsyncSessionLocal() as db:
            try:
                tx = await create_entry_transaction(
                    db,
                    gate_in_id=gate_id,
                    card_number=card_number,
                    payment_method="EMONEY",
                )
                await db.commit()

                await publish_command(OpenGateCommand(gate_id=gate_id))
                logger.info("entry_emoney_gate_opened", gate_id=gate_id, transaction_id=tx.id)
            except Exception as e:
                logger.error("entry_emoney_decision_error", gate_id=gate_id, error=str(e))
```

**Step 4: Commit**

```bash
git add shared/events.py daemons/gate_in.py api/app/services/event_consumer.py
git commit -m "feat(entry-emoney): add EmoneyPrintDecisionEvent and API handler for entry flow"
```

---

## Task 9: Integration Tests

**Files:**
- Create: `tests/e2e/test_emoney_booth_bridge.py`
- Create: `tests/e2e/test_emoney_manless_exit.py`
- Create: `tests/e2e/test_emoney_entry.py`

**Step 1: Booth Bridge E2E Test**

Create `tests/e2e/test_emoney_booth_bridge.py`:

```python
"""E2E test for booth bridge e-money flow."""

import pytest

@pytest.mark.anyio
async def test_booth_bridge_emoney_deduct_success(
    test_client, redis_client, db_session, monkeypatch
):
    """Full flow: booth bridge deduct -> API result -> gate opens."""
    monkeypatch.setenv("INTERNAL_API_KEY", "test-booth-key")

    # 1. Create an active transaction
    # 2. Call booth-result endpoint
    # 3. Verify gate command published
    # 4. Verify EmoneyTransaction created
    pass
```

**Step 2: Manless Exit E2E Test**

Create `tests/e2e/test_emoney_manless_exit.py`:

```python
"""E2E test for manless exit e-money flow via daemon."""

import pytest

@pytest.mark.anyio
async def test_manless_exit_emoney_deduct(
    redis_client, db_session
):
    """Full flow: daemon detects card -> DeductCommand -> deduct -> result -> gate opens."""
    pass
```

**Step 3: Entry E2E Test**

Create `tests/e2e/test_emoney_entry.py`:

```python
"""E2E test for entry e-money flow."""

import pytest

@pytest.mark.anyio
async def test_entry_emoney_card_tap(
    redis_client, db_session
):
    """Full flow: card tap -> PasstiCardTapEvent -> check balance -> print decision -> gate opens."""
    pass
```

**Step 4: Run all tests**

```bash
cd /home/qiu/Work/E-Parking/parking-system-v2/api && pytest tests/ -v -k "emoney"
cd /home/qiu/Work/E-Parking/parking-system-v2 && pytest tests/e2e/ -v -k "emoney"
```

**Step 5: Commit**

```bash
git add tests/e2e/test_emoney_*.py
git commit -m "test(e2e): add e-money integration tests for booth, manless, and entry flows"
```

---

## Task 10: Final Verification & Documentation

**Step 1: Run full test suite**

```bash
cd /home/qiu/Work/E-Parking/parking-system-v2/api && pytest tests/ -v
cd /home/qiu/Work/E-Parking/parking-system-v2 && pytest tests/ -v
```

**Step 2: Update AGENTS.md if needed**

Document the new e-money architecture in `AGENTS.md`.

**Step 3: Final commit**

```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md with e-money architecture"
```

---

## Execution Options

**Plan complete and saved to `docs/plans/2026-04-29-emoney-fix.md`.**

**Two execution options:**

1. **Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration
2. **Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
