# Load Testing

## Prerequisites

Ensure the full stack is running:

```bash
docker compose up -d
python scripts/seed.py
```

## Run Load Tests

```bash
locust -f tests/load/locustfile.py --host http://localhost:8000
```

Open http://localhost:8089 and set:
- Number of users: 50
- Spawn rate: 5
- Duration: 5 minutes

## Expected Results

- Median response time < 100ms for health check
- Median response time < 300ms for transaction list
- 0% error rate at 50 concurrent users
