# Phase 6.3 — Stepped Ramp Capacity Report

**Generated:** 2026-04-18 14:56 local
**Protocol:** 5 levels × 300s hold, 15s cooldown
**Workers:** 4 uvicorn, 1 PostgreSQL 14, rate-limiting OFF
**Breaking point thresholds:** Browse p95>1000ms OR Enroll/Withdraw p95>2000ms OR error>5.0% OR Login 5xx>2.0%

---

## Capacity Curve

| VUs | Requests | RPS | Error% | Browse p95 | Enroll p95 | Withdraw p95 | Login p95 | slow_q Δ | Status |
|-----|----------|-----|--------|-----------|-----------|-------------|----------|---------|--------|
|  50 |    20077 |  67.0 |   0.0% |        29ms |        23ms |          0ms |     1600ms |        0 | ✅ Stable |
| 100 |    40147 | 134.0 |   0.0% |        29ms |        23ms |          0ms |     1900ms |        2 | ✅ Stable |
| 200 |    78292 | 261.3 |   0.0% |        74ms |        67ms |          0ms |     2100ms |        6 | ✅ Stable |
| 300 |    95010 | 317.9 |   0.0% |       550ms |       610ms |          0ms |     2300ms |       41 | ✅ Stable |
| 500 |    85546 | 286.0 |   0.9% |      1700ms |      1900ms |          0ms |     6600ms |      111 | ❌ BROKEN |

---

## Breaking Point

**Breaking point: 500 VUs**
**Last stable level: 300 VUs**
**Bottleneck:** DB connection pool exhaustion (Login 5xx spike)

Threshold violations at breaking point:
- Browse p95=1700ms > 1000ms
- Login 5xx=147.8% > 2.0% (DB pool)

---

## Bottleneck Confirmation

### Latency Trend (Browse p95 across levels)

| VUs | Browse p95 | Δ from prev |
|-----|-----------|------------|
|  50 |        29ms | — |
| 100 |        29ms | +0ms |
| 200 |        74ms | +45ms |
| 300 |       550ms | +476ms |
| 500 |      1700ms | +1150ms |

### DB Pool Signal (Login 5xx rate)

| VUs | Login reqs | Login fails | 5xx codes | 5xx% |
|-----|-----------|------------|-----------|------|
|  50 |        50 |          0 |         0 | 0.0% |
| 100 |       100 |          0 |         0 | 0.0% |
| 200 |       200 |          0 |         0 | 0.0% |
| 300 |       300 |          0 |         0 | 0.0% |
| 500 |       500 |          0 |       739 | 147.8% |

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
