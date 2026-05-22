# Week 9 — Test Checklist

## E2E Orchestration Tests
- [x] Gate-in Cash flow: vehicle detected → gate closes → button press → events published
- [x] Gate-in E-Money flow: vehicle detected → tap → balance check → events published
- [x] Gate-out Cash flow: vehicle detected → POS command → gate opens
- [x] Gate-out RFID flow: vehicle detected → Wiegand read → gate opens
- [x] Gate-out E-Money flow: vehicle detected → PASSTI tap → events published
- [x] Gate-out timeout flow: vehicle detected → wait → alert → timeout event published

## Prometheus Metrics
- [x] /metrics endpoint returns Prometheus format
- [x] http_requests_total counter incremented per method/endpoint/status
- [x] http_request_duration_seconds histogram recorded
- [x] payment_attempts_total labeled by method (cash/rfid/emoney)
- [x] payment_success_total labeled by method

## Health Checks
- [x] GET /api/health returns ok
- [x] GET /api/health?detailed=true includes database check
- [x] GET /api/health?detailed=true includes redis check
- [x] Returns degraded when dependency is down

## Load Testing
- [x] Locustfile compiles without errors
- [x] README documents how to run load tests

## CI/CD
- [x] Workflow file syntax valid
- [x] Workflow runs on push to main/develop
- [x] Workflow runs on PR to main
- [x] PostgreSQL service configured
- [x] Redis service configured
- [x] Migrations step included
- [x] Test step included
- [x] Circular import check included
- [x] Route count verification included
