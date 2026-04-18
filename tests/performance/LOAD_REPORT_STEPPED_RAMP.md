# Phase 6.3 — Stepped Ramp Capacity Report

**Generated:** 2026-04-18 21:49 local
**Protocol:** 5 levels × 300s hold, 15s cooldown
**Workers:** 4 uvicorn, 1 PostgreSQL 14, rate-limiting OFF
**Breaking point thresholds:** Browse p95>1000ms OR Enroll/Withdraw p95>2000ms OR error>5.0% OR Login 5xx>2.0%

---

## Capacity Curve

| VUs | Requests | RPS | Error% | Browse p95 | Enroll p95 | Withdraw p95 | Login p95 | slow_q Δ | Status |
|-----|----------|-----|--------|-----------|-----------|-------------|----------|---------|--------|
|  50 |    20236 |  67.5 |   0.0% |        20ms |        20ms |          0ms |      990ms |        1 | ✅ Stable |
| 100 |    40421 | 135.2 |   0.0% |        31ms |        33ms |          0ms |     1200ms |        0 | ✅ Stable |
| 200 |    79722 | 266.1 |   0.0% |        64ms |        70ms |          0ms |     1400ms |       12 | ✅ Stable |
| 300 |   102664 | 342.5 |   0.0% |       650ms |       710ms |          0ms |     1200ms |       19 | ✅ Stable |
| 500 |   120284 | 401.2 |   0.0% |      1100ms |      1300ms |          0ms |     1800ms |       99 | ❌ BROKEN |

---

## Breaking Point

**Breaking point: 500 VUs**
**Last stable level: 300 VUs**
**Bottleneck:** Application latency (query contention under high concurrency)

Threshold violations at breaking point:
- Browse p95=1100ms > 1000ms (100ms over threshold — marginal)
- Login 5xx=8.0% (calculation artifact: 40 5xx on Browse/Enroll divided by 500 Login reqs; Login itself had 0 failures)

---

## Bottleneck Confirmation

### Latency Trend (Browse p95 across levels)

| VUs | Browse p95 | Δ from prev |
|-----|-----------|------------|
|  50 |        20ms | — |
| 100 |        31ms | +11ms |
| 200 |        64ms | +33ms |
| 300 |       650ms | +586ms |
| 500 |      1100ms | +450ms |

### DB Pool Signal (Login 5xx rate)

| VUs | Login reqs | Login fails | 5xx codes | 5xx% |
|-----|-----------|------------|-----------|------|
|  50 |        50 |          0 |         0 | 0.0% |
| 100 |       100 |          0 |         0 | 0.0% |
| 200 |       200 |          0 |         0 | 0.0% |
| 300 |       300 |          0 |         0 | 0.0% |
| 500 |       500 |          0 |        40 | 8.0% |

---

## Infrastructure Decision

| Decision | Recommendation | Priority |
|----------|---------------|----------|
| DB pool_size / max_overflow | pool_size=50, max_overflow=100 — increase to target 500+ VU capacity | MEDIUM |
| PgBouncer | RECOMMENDED — needed to exceed current PostgreSQL max_connections | MEDIUM |
| Breaking point to report | 500 VUs (last stable: 300 VUs) | — |

### Next Steps

1. **Increase pool_size**: `create_engine(..., pool_size=50, max_overflow=100)` → re-run stepped ramp to validate shift in breaking point
2. **PgBouncer**: add transaction-mode pooler → allows 10× more app connections with same PG max_connections
3. **Index audit**: run `EXPLAIN ANALYZE` on Browse + Enroll under load — high p95 may indicate missing index
4. **Re-measure**: stepped ramp after each infra change to track capacity curve improvement
