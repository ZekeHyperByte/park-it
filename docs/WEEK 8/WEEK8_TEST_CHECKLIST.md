# Week 8 — Test Checklist

## Settlement File Generator
- [x] Filename format correct (date + MID + TID + version + batch + .txt)
- [x] MID left-padded to 16 chars
- [x] TID left-padded to 8 chars
- [x] Batch number zero-padded to 3 digits
- [x] Header: count(3) + amount(10)
- [x] Body: raw hex + LF per transaction

## Settlement Worker
- [x] Groups transactions by reader_id
- [x] Skips readers without MID/TID
- [x] Creates EmoneySettlement record
- [x] Links transactions to settlement
- [x] Writes file to disk
- [x] Computes SHA256 hash

## Settlement Uploader
- [x] .OK response parser handles accepted transactions
- [x] .OK response parser handles mixed statuses
- [x] .NOK response parser works

## Settlement Routes
- [x] GET /api/settlements returns list
- [x] POST /api/settlements/trigger runs worker

## Simulators
- [x] Compass simulator responds to STAT
- [x] Compass simulator logs commands
- [x] PASSTI simulator parses frames
- [x] PASSTI simulator returns SUCCESS

## E2E Tests
- [x] Settlement generation with 3 transactions
- [x] File format verified against spec
- [x] DB state verified
- [x] No files generated when no transactions

## Frontend
- [x] Settlement tab renders
- [x] Manual trigger button works
- [x] Build succeeds

## Regression
- [x] All 296 existing tests pass
- [x] No circular imports
- [x] 69 FastAPI routes loaded
- [x] Frontend production build successful

## Summary

| Category | Status |
|----------|--------|
| Backend unit tests | 296/296 passing |
| Frontend build | Pass |
| Simulators | 4/4 passing |
| E2E tests | 2/2 passing |
| Overall | COMPLETE |

*End of Week 8 Test Checklist*
