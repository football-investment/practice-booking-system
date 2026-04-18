# Phase 6.3 — Stepped Ramp Capacity Report

**Generated:** 2026-04-18 16:34 local
**Protocol:** 5 levels × 300s hold, 15s cooldown
**Workers:** 4 uvicorn, 1 PostgreSQL 14, rate-limiting OFF
**Breaking point thresholds:** Browse p95>1000ms OR Enroll/Withdraw p95>2000ms OR error>5.0% OR Login 5xx>2.0%

---

## Capacity Curve

| VUs | Requests | RPS | Error% | Browse p95 | Enroll p95 | Withdraw p95 | Login p95 | slow_q Δ | Status |
|-----|----------|-----|--------|-----------|-----------|-------------|----------|---------|--------|
|  50 |    20330 |  67.8 |   0.0% |        22ms |        20ms |          0ms |      620ms |        1 | ✅ Stable |
| 100 |    40791 | 136.1 |   0.0% |        20ms |        19ms |          0ms |      630ms |        1 | ✅ Stable |
| 200 |    80459 | 268.7 |   0.0% |        37ms |        33ms |          0ms |      780ms |        5 | ✅ Stable |
| 300 |   111129 | 370.9 |   0.0% |       240ms |       250ms |          0ms |     3100ms |       13 | ✅ Stable |
| 500 |   107651 | 360.0 |   0.2% |      1300ms |      1500ms |          0ms |     1600ms |       97 | ❌ BROKEN |

---

## Breaking Point

**Breaking point: 500 VUs**
**Last stable level: 300 VUs**
**Bottleneck:** DB connection pool exhaustion (Login 5xx spike)

Threshold violations at breaking point:
- Browse p95=1300ms > 1000ms
- Login 5xx=28.8% > 2.0% (DB pool)

---

## Bottleneck Confirmation

### Latency Trend (Browse p95 across levels)

| VUs | Browse p95 | Δ from prev |
|-----|-----------|------------|
|  50 |        22ms | — |
| 100 |        20ms | +-2ms |
| 200 |        37ms | +17ms |
| 300 |       240ms | +203ms |
| 500 |      1300ms | +1060ms |

### DB Pool Signal (Login 5xx rate)

| VUs | Login reqs | Login fails | 5xx codes | 5xx% |
|-----|-----------|------------|-----------|------|
|  50 |        50 |          0 |         0 | 0.0% |
| 100 |       100 |          0 |         0 | 0.0% |
| 200 |       200 |          0 |         0 | 0.0% |
| 300 |       300 |          0 |         0 | 0.0% |
| 500 |       500 |          0 |       144 | 28.8% |

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
