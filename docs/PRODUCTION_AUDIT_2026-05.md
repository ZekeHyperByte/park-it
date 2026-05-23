# Production Readiness Audit — E-Parking v2

**Date:** 2026-05-24
**Auditor:** Senior fullstack onboarding review
**Scope:** Reliability (24/7), hardware link stability, deploy/field setup, UI/UX (operator + admin)
**Method:** Four parallel read-only investigations against `main` (HEAD `7fff28b`). File:line cites valid at audit time.

> Triage legend: **P0** = blocks go-live / data-loss / safety. **P1** = field-ops pain, will page oncall. **P2** = degraded UX/availability, fix before scaling. **P3** = polish, harden later.

---

## 0. Executive Summary

System is functional but **not 24/7 production-ready** as-is. Highest-risk clusters:

1. **Async task hygiene** — orphan `asyncio.create_task` in daemons + booth bridge swallow exceptions; gate state machine and payment flow can silently die without crashing the process. Hardest class of bug to detect in field.
2. **Hardware reconnect gaps** — TCP Compass controller, PASSTI serial, Omnikey USB all have one-shot failure modes. A single network hiccup leaves a gate dead until manual `systemctl restart`.
3. **Payment idempotency** — Redis-pending + DB read sequence in `payment.py` has a race window allowing double-deduct on concurrent booth taps. Money-handling code must be lock-free CAS or DB-row-locked end-to-end.
4. **Deploy ergonomics** — secrets default to repo values, no production validator, no timezone enforcement (Asia/Jakarta required for settlement), gunicorn worker count missing, dev deps installed in prod.
5. **Operator UX safety** — double-submit possible on cash button, F-keys leak into PIN input fields, modal escape discards in-progress payment without confirm.

**Recommendation:** Fix all P0 + P1 items below before pilot. Cold-deploying current state to a 24/7 site will burn oncall within the first week.

---

## 1. Reliability — 24/7 Program Stability

24 findings. Source: `cavecrew-investigator` over `api/app/`, `daemons/`, `workers/`, `booth_bridge/`, `shared/`.

| Sev | Location | Issue | Fix |
|---|---|---|---|
| P0 | `daemons/gate_in.py:354,369` | `asyncio.create_task(_vehicle_pass_timer / _validating_timeout)` orphaned — no exception handler, no tracking; if timer crashes the state machine wedges silently | Use `TaskGroup` or store task refs, add `add_done_callback` logging exceptions |
| P0 | `booth_bridge/websocket_server.py:244,248,254` | Fire-and-forget `create_task()` on API call + relay open; failures invisible | Same pattern: track + log; surface to operator via WS event |
| P0 | `api/app/services/event_consumer.py:89-159` | `process_emoney_result` holds `with_for_update=True` row lock with no statement timeout → blocks all payment ops if slow path | Wrap in `asyncio.timeout(5)`; set `SET LOCAL lock_timeout = '3s'` |
| P1 | `api/app/services/payment.py:394-401` | E-money: Redis pending read → DB get without re-validation → double-charge possible on concurrent booth requests | Atomic compare-and-swap on Redis (`SET NX`) OR DB-row lock spanning entire flow |
| P1 | `booth_bridge/websocket_server.py:170-177` | `serial.Serial()` opened, never closed on exception → fd leak per open_gate | `with serial.Serial(...) as s:` or `try/finally s.close()` |
| P1 | `api/app/services/event_consumer.py:103` | `AsyncSessionLocal()` not closed on exception path → connection pool leak | Use `async with` pattern throughout |
| P1 | `booth_bridge/main.py:161` | `await asyncio.Event().wait()` blocks forever → SIGTERM shutdown hangs | Bind event to signal handler, set on SIGTERM |
| P1 | `daemons/gate_in.py:462-472` | `get_arq_redis()` re-resolved every call → O(n) connection attempts | Cache pool on daemon instance |
| P2 | `api/app/services/event_consumer.py:205-314` | `asyncio.sleep(6)` blocks RFID handler → stalls 6s/card | Move to background task, return immediately |
| P2 | `daemons/gate_in.py:332` | `await asyncio.sleep(10)` in `_on_help_button` traps vehicle 10s with no escape | Use cancellable timeout + abort handler |
| P2 | `daemons/gate_in.py:201-218` | Wiegand frame parse error sets `buffer = b""` → discards good data after bad byte | Find next sync byte instead of dropping buffer |
| P2 | `booth_bridge/websocket_server.py:89-134` | No timeout on outbound HTTP POST to API → hangs forever if API down | `httpx.AsyncClient(timeout=10)` |
| P2 | `api/app/services/payment.py:335` | `calculate_transaction_fee()` crashes on NULL `vehicle_type_id` | Default to "MOBIL" tariff + log warning |
| P2 | `api/app/services/payment.py:59-86` | `_enqueue_print_receipt` swallows all exceptions silently | Re-raise after logging; surface to operator |
| P2 | `api/app/services/event_consumer.py:192` | Commit succeeds but later handler error leaves orphaned tx | Single transaction span or saga rollback |
| P3 | `shared/config.py` | `db_password='parking_secret'`, `jwt_secret='dev-secret'` defaults baked in code | Pydantic `@model_validator` rejecting defaults when `APP_ENV=production` |
| P3 | `daemons/gate_in.py:123` | `controller.connect(timeout=5.0)` blocking in async startup | `asyncio.to_thread(...)` or async TCP |
| P3 | `api/app/websocket/broadcaster.py:54-55` | Listener exception caught + dropped → broadcaster silently dies | Restart loop with backoff |
| P3 | `booth_bridge/omnikey_poller.py:135-142` | `queue.put_nowait(OSError)` lost when full → device considered alive | Drop oldest, log queue overflow |
| P3 | `daemons/base.py:196-227` | `xreadgroup(block=5000)` delays SIGTERM up to 5s | Reduce to 1s; check shutdown flag between reads |
| P3 | `shared/redis.py:193-220` | `_arq_pool` lock inside function → race on concurrent first calls | Module-level lock |

---

## 2. Hardware Link Stability

20 findings. Source: `cavecrew-investigator` over `daemons/`, `booth_bridge/`, `protocols/`, `workers/`.

| Sev | Location | Issue | Fix |
|---|---|---|---|
| P0 | `daemons/gate_in.py:206` | `_rss_listener` polls dead socket forever on TCP drop — no reconnect | Detect EOF/RST, call `_connect_controller()` with exponential backoff |
| P0 | `daemons/gate_in.py:504` | Hardcoded `sleep(1.5)` after PR3 print command masks sync — jammed printer locks state machine | Await print-complete event from worker; timeout with explicit error |
| P0 | `booth_bridge/gate_opener.py:72` | `time.sleep()` blocking sync in close-delay → no interrupt path | Convert to async; respect cancellation |
| P0 | `booth_bridge/websocket_server.py:171` | Serial write has no retry; transient write failure permanently fails open | Retry up to 3× with 200ms gap; surface failure |
| P0 | `booth_bridge/serial_manager.py:50-57` | `send()` fails immediately on peripheral offline → no reconnect | Wrap in reconnect loop with backoff cap 5s |
| P0 | `protocols/passti/transport.py:76-102` | Timeout loop never exits on partial frame → next payment blocked | Strict deadline; flush buffer on timeout |
| P1 | `daemons/gate_in.py:195-200` | `_setup_rss` failure not retried → daemon runs with RSS disabled | Retry on connect callback |
| P1 | `daemons/gate_in.py:179-193` | Heartbeat catches exception but never reconnects → dead socket passes `is_connected()` | Call `_connect_controller()` on heartbeat failure |
| P1 | `daemons/base.py:228` | `xack()` after handler runs but handler crash → command lost (no retry) | ACK only after successful side-effect commit |
| P1 | `booth_bridge/omnikey_poller.py:144` | USB replug race loses buffered card number on `OSError` | Cleanly reset device, replay last frame |
| P1 | `protocols/compass/protocol.py:227-235` | `is_connected()` false positive on half-open TCP — `getpeername()` doesn't detect RST | Send 0-byte probe or check `socket.recv(1, MSG_PEEK)` |
| P2 | `daemons/gate_in.py:212` | Tight `sleep(0.1)` spin on disconnected controller | Exponential backoff 1s→30s |
| P2 | `workers/critical/print_worker.py:314` | `Retry(defer=job_try * 5)` no cap → only ARQ `max_tries=3` saves it | Explicit cap + dead-letter queue |
| P2 | `booth_bridge/main.py:147-154` | Poller restart leaves old `loop.add_reader(dev.fd)` → fd leak | `remove_reader()` in cleanup |
| P2 | `booth_bridge/api_client.py:36,51` | No retry on API timeout → 1-second API blip rejects RFID exit | Retry 3× with 500ms backoff |
| P2 | `booth_bridge/websocket_server.py:243-248` | `gate_opener.open()` fire-and-forget → WS returns success before barrier opens | Await result; emit `barrier_opened` event |
| P3 | `protocols/passti/frame.py:108-131` | `parse_response` no bounds check → OOB on malformed frame | Validate `len(payload) >= expected` per branch |
| P3 | `daemons/base.py:68-70` | TCP keepalive interval == heartbeat interval (30s) | De-tune (keepalive 15s, heartbeat 30s) |
| P3 | `booth_bridge/omnikey_poller.py:115` | `list_devices()` blocks loop 100ms+ on USB busy | `asyncio.to_thread` |
| P3 | `booth_bridge/gate_opener.py:36-45` | `_decode_hex` falls back to `.encode()` on invalid hex → garbage to relay | Raise `ValueError` on non-hex |

---

## 3. Deploy / Field Setup / Ops

31 findings. Source: `cavecrew-investigator` over `install.sh`, `systemd/`, `docker-compose.yml`, `alembic`, `scripts/`, `shared/config.py`.

| Sev | Location | Issue | Fix |
|---|---|---|---|
| P0 | `install.sh:120` | `DB_PASSWORD` passed via `sed` → visible in `ps` during install | `.env` template, perms 0600 |
| P0 | `install.sh:121` | Installer warns about JWT_SECRET but doesn't enforce non-default | Validate length ≥32; refuse to proceed if matches default |
| P0 | `.env.example` | Default credentials shipped (DB_PASSWORD=parking_secret) | Add big banner README; refuse boot on defaults in production |
| P0 | `systemd/parking-api.service:14` | Gunicorn lacks worker config — single worker handles all payment requests | `--workers=4 --max-requests=1000 --worker-class=uvicorn.workers.UvicornWorker` |
| P0 | `install.sh:132` | Postgres wait only checks `pg_isready`, not actual connectivity post-migrations | `alembic upgrade head` inside wait loop; fail hard on timeout |
| P0 | `api/migrations/versions/914e5fe1c754_initial_schema.py:downgrade()` | Empty downgrade → no rollback path | Add `op.drop_table()` for all created tables |
| P0 | `systemd/parking-api.service` | No `After=docker.service` → race on reboot | `After=docker.service`, `Wants=docker.service` |
| P1 | `install.sh:110` | `pip install -e ".[dev]"` installs dev deps in production | Split `.[prod]` extras; only `.[dev]` in dev/test |
| P1 | `docker-compose.yml:52` | Redis `maxmemory-policy allkeys-lru` evicts ARQ streams + settlement keys under pressure | `noeviction`, or separate Redis for streams |
| P1 | `systemd/parking-daemon-gate-in@.service:17` | `RestartSec=10` too slow for gate recovery | `RestartSec=1`, exponential backoff in code |
| P1 | `systemd/parking-api.service:4` | `Wants=redis.service postgresql.service` but those are Docker, not systemd units | `After=network-online.target` + health-check polling pre-ExecStart |
| P1 | `install.sh` | No timezone enforcement — settlement files demand Asia/Jakarta (WIB) | `timedatectl set-timezone Asia/Jakarta`; assert in API boot |
| P1 | `docker-compose.yml:71-72` | Hardcoded `DB_PASSWORD` overrides `.env` | Use `env_file:` only |
| P1 | `systemd/booth-bridge.service:11` | `/etc/parking/booth.json` referenced but installer never creates it | `ExecStartPre=/usr/bin/test -f ...`; template in installer |
| P2 | `shared/config.py:105-112` | No validator rejecting default secrets in production | `@model_validator(mode="after")` + `app_env` check |
| P2 | `api/app/main.py:52` | `debug=settings.debug` honored in production | Force `False` if `app_env=='production'` |
| P2 | `docker-compose.yml:18-22` | Postgres healthcheck uses `pg_isready` only — doesn't validate query path | Add `psql -c 'SELECT 1'` |
| P2 | `scripts/backup_database.sh:25` | `PGPASSWORD` in env → visible in `ps` | `.pgpass` file mode 0600 |
| P2 | `systemd/parking-backup.timer:5` | No `OnBootSec` → misses backup if boot after 01:00 | `OnBootSec=10m` |
| P2 | `install.sh:88` | `usermod -aG ... \|\| true` swallows group-add failure | Log + fail if `docker`/`dialout` missing |
| P2 | `install.sh:96-98` | rsync `--delete` keeps stale `.env` | `--exclude='.env'` |
| P2 | `api/app/routes/health.py:53` | Health opens new Redis connection per request | Singleton client |
| P2 | `install.sh:156` | `npm install --no-audit` skips audit | Run `npm audit --audit-level=moderate` |
| P2 | `install.sh:195-201` | `$gid` passed to systemctl without validation | Regex `^[A-Z0-9_-]+$` |
| P3 | `systemd/*.service` | No `TimeoutStartSec`/`TimeoutStopSec` | `TimeoutStartSec=120 TimeoutStopSec=30` |
| P3 | `systemd/*.service` | No `LimitNOFILE`, `MemoryMax`, `CPUQuota` | Set per service profile |
| P3 | `docker-compose.yml:95` | `:/app:cached` bind mount in dev breaks consistency | Document dev-only; remove from field profile |
| P3 | `.env.example` | No `SNAPSHOT_DIR`, `SETTLEMENT_DIR`, `LOG_DIR` → disk-fill risk on `/var` | Variable + mount-point doc |
| P3 | `install.sh:58,72` | `systemctl enable --now docker pcscd` assumes presence | Check unit-file existence first |
| P3 | `systemd/parking-backup.timer:6` | `Persistent=true` but no cold-archive | Cron-style archive rotation |
| P3 | `.env.example:35` | JWT_SECRET comment says 64-char, example is 68 | `JWT_SECRET=<openssl rand -base64 48>` |

**Cross-cutting gaps:**
- No Prometheus scrape config bundled (`prometheus-client` in pyproject but metrics endpoint not surfaced in nginx).
- No alert rules (gate-down, daemon-restarted, payment-fail-rate).
- No structured-log centralization recipe in `OPERATIONS_RUNBOOK.md`.

---

## 4. UI/UX — Operator POS + Admin

35 findings. Source: `cavecrew-investigator` over `frontend/`.

### Operator (high-pressure cashier flow)

| Sev | Location | Issue | Fix |
|---|---|---|---|
| P0 | `frontend/pages/pos.vue:226-247` | Gate-disconnect toast spams on network churn; no debounce, no per-booth filter | 500ms debounce, persistent banner, dismiss per-session |
| P0 | `frontend/pages/pos.vue:320-345` | F2/F3 fallback shortcuts silently no-op if state wrong | Toast `"Pembayaran tidak tersedia"` when rejected |
| P0 | `frontend/components/pos/CashDialog.vue:112-124` | Focus lost after Enter confirms → next barcode scan misses input | `await nextTick()` then focus barcode |
| P0 | `frontend/pages/pos.vue:418-454` | E-money deduct silently dropped if `selectedGate`/`boothWs` falsy | Explicit guard + visible error |
| P0 | `frontend/composables/useKeyboard.js:24-26` | F1-F4 fire while typing in PIN input | Skip when `input[type=password]` or `inputmode=numeric` focused |
| P1 | `frontend/pages/pos.vue:150-169` | Double-submit guard is `ref` only — buttons remain clickable | `:disabled="isPaymentProcessing"` on all payment buttons |
| P1 | `frontend/pages/pos.vue:470-496` | Booth-offline path emits conflicting toasts | Single error path: check `boothConnected` first, single toast |
| P1 | `frontend/components/pos/PosErrorView.vue:44-96` | LOST_CONTACT + insufficient-balance combo missing "Bayar Cash" button | Add cash fallback CTA |
| P1 | `frontend/components/pos/CashDialog.vue:1-70` | Backdrop click closes mid-entry, no confirm | `@click.self` no-op, or confirm-discard |
| P1 | `frontend/pages/pos.vue:114-125` | Worker check-in dialog has no timeout → stuck operator | 60s inactivity timeout + admin override |
| P1 | `frontend/pages/pos.vue:195-205` | Timeout-ring overlay missing z-index → hidden under view | `z-10` + visual test |
| P1 | `frontend/pages/personnel.vue:54-92,55-73` | PIN input truncates silently at maxlength; Enter outside input doesn't save | Show `4/4` counter; `@keydown.enter` on input |

### Admin

| Sev | Location | Issue | Fix |
|---|---|---|---|
| P1 | `frontend/pages/transaksi.vue:48-59` | Filters reset on pagination | Persist filters in URL query params |
| P1 | `frontend/pages/setting.vue:67-85` | Inline blur-save with no validation → invalid timeout saves silently | `type=number min=1` + reject toast |
| P1 | `frontend/pages/report.vue:136-146` | Export 500 → generic toast, no retry, no progress | Progress bar; retry button; copy error to clipboard |
| P2 | `frontend/pages/device.vue:38-54` | Gate cards lack "last heartbeat" timestamp | `updated 12s ago`, refresh 5s |
| P2 | `frontend/pages/gate-in.vue:4-51` | No photo preview on gate-in cards | Thumbnail from latest snapshot |
| P2 | `frontend/stores/gate.js:343` | E-money success auto-clears after 3s mid-receipt review | Manual "Next Vehicle" or 10s |
| P2 | `frontend/components/pos/WorkerHandoverDialog.vue:174-185` | Keyboard hints only on `pending` step | Context-aware hints per step |
| P2 | `frontend/pages/personnel.vue:6` | Subtitle copy-pasted from settings page | Fix to "Kelola pengguna dan PIN shift" |
| P3 | `frontend/composables/useApi.js:43-50` | Network failure → no `error.status` | `error.status = 0`, surface "Network error" |
| P3 | `frontend/components/DataTable.vue` | 10k-row reports lag — no virtual scroll | `vue-virtual-scroller` + server-side pagination >500 |
| P3 | `frontend/pages/pos.vue:287` | Snapshot URL construction can double-slash | `new URL(path, baseURL)` |

### Cross-cutting

| Sev | Area | Issue | Fix |
|---|---|---|---|
| P2 | a11y | No focus-trap on modals; tab cycles to background | Use `focus-trap-vue` or shadcn-vue dialog primitives |
| P2 | i18n | Indonesian/English mix in labels ("Bayar Tunai" + "Print receipt") | One pass for Bahasa Indonesia consistency |
| P2 | error boundaries | No top-level `onErrorCaptured` — Vue render error blanks POS | Add error boundary with "Reload booth" CTA |
| P3 | responsive | POS designed desktop-first; admin not tested on tablet | Test 1024×768 booth tablet + 1920×1080 desktop |

---

## 5. Recommended Punch-List Order (Pre-Pilot)

**Week 1 (P0 reliability + hardware):**
1. Task lifecycle: replace orphan `create_task` with tracked tasks across daemons + booth bridge.
2. Compass TCP reconnect loop in `_rss_listener`; half-open detection.
3. PASSTI transport timeout + partial-frame flush.
4. Payment idempotency: Redis CAS or row-lock spanning entire e-money flow.
5. Serial fd-leak fix in `websocket_server.py`.

**Week 2 (P0 deploy + UI safety):**
6. Production secrets validator (`shared/config.py`).
7. Gunicorn worker config + systemd `After=docker.service`.
8. Timezone enforcement Asia/Jakarta.
9. POS double-submit disable + F-key input guard.
10. Operator gate-disconnect debounce + per-booth filter.

**Week 3 (P1 sweep):**
11. Heartbeat→reconnect wiring; ACK-after-side-effect.
12. Booth bridge HTTP retry/backoff.
13. Worker check-in timeout + handover dialog UX.
14. Admin filter persistence + setting validation.
15. Print worker retry cap + dead-letter queue.

**Week 4 (observability + drill):**
16. Prometheus scrape config bundled, nginx route added.
17. Alert rules (gate-down, payment-fail-rate, daemon-restart-count).
18. Field install dry-run on clean Debian box, follow `install.sh` end-to-end.
19. 24h soak test on staging with synthetic traffic + chaos (kill daemons, drop network).

---

## 6. Not Audited (Out of Scope This Pass)

- Settlement file format correctness vs `Format File Settlement Multibank v1.3.txt`
- ESC/POS receipt rendering on real Bixolon/Epson hardware
- License plate ML model (`license_plate_detector.pt`) accuracy / inference latency
- Load testing — see `tests/load/` if present
- Penetration testing / OWASP scan on API surface

---

## 7. Tooling Notes

- `graphify-out/GRAPH_REPORT.md` was instrumental — community hubs map directly onto subsystem audit axes (Gate Daemon Core, Payment & Transaction, Booth Bridge, Hardware Config). Keep `graphify update .` in CI after large refactors.
- All findings have file:line citations; please verify against current `main` before fixing — branches diverge fast.
