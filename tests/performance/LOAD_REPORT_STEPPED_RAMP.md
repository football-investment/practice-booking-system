# Phase 6.3 — Stepped Ramp Capacity Report

**Generated:** 2026-04-18 14:25 local
**Protocol:** 5 levels × 300s hold, 15s cooldown
**Workers:** 4 uvicorn, 1 PostgreSQL 14, rate-limiting OFF
**Breaking point thresholds:** Browse p95>1000ms OR Enroll/Withdraw p95>2000ms OR error>5.0% OR Login 5xx>2.0%

---

## Capacity Curve

| VUs | Requests | RPS | Error% | Browse p95 | Enroll p95 | Withdraw p95 | Login p95 | slow_q Δ | Status |
|-----|----------|-----|--------|-----------|-----------|-------------|----------|---------|--------|
|  50 |    20048 |  67.1 |   0.0% |        34ms |        27ms |        140ms |     2100ms |        8 | ✅ Stable |
| 100 |    40210 | 134.2 |   0.0% |        32ms |        27ms |         49ms |     1900ms |        0 | ✅ Stable |
| 200 |    79280 | 264.7 |   0.1% |        54ms |        44ms |         46ms |     2400ms |        7 | ❌ BROKEN |
| 300 |    98798 | 329.5 |   1.2% |       450ms |       500ms |        270ms |     2500ms |       28 | ❌ BROKEN |
| 500 |    94954 | 316.6 |  22.0% |      1400ms |      1500ms |          0ms |     2500ms |       51 | ❌ BROKEN |

---

## Breaking Point

**Breaking point: 200 VUs**
**Last stable level: 100 VUs**
**Bottleneck:** DB connection pool exhaustion (Login 5xx spike)

Threshold violations at breaking point:
- Login 5xx=26.0% > 2.0% (DB pool)

---

## Bottleneck Confirmation

### Latency Trend (Browse p95 across levels)

| VUs | Browse p95 | Δ from prev |
|-----|-----------|------------|
|  50 |        34ms | — |
| 100 |        32ms | +-2ms |
| 200 |        54ms | +22ms |
| 300 |       450ms | +396ms |
| 500 |      1400ms | +950ms |

### DB Pool Signal (Login 5xx rate)

| VUs | Login reqs | Login fails | 5xx codes | 5xx% |
|-----|-----------|------------|-----------|------|
|  50 |        50 |          0 |         0 | 0.0% |
| 100 |       100 |          0 |         0 | 0.0% |
| 200 |       200 |          0 |        52 | 26.0% |
| 300 |       300 |         18 |       999 | 333.0% |
| 500 |       500 |         81 |     17607 | 3521.4% |

---

## Infrastructure Decision

| Decision | Recommendation | Priority |
|----------|---------------|----------|
| DB pool_size / max_overflow | pool_size=50, max_overflow=100 — current default (~5–20) exhausted below 200 VUs | CRITICAL |
| PgBouncer | YES — mandatory before production; transaction pooling mode | CRITICAL |
| Breaking point to report | 200 VUs (last stable: 100 VUs) | — |

### Next Steps

1. **Increase pool_size**: `create_engine(..., pool_size=50, max_overflow=100)` → re-run stepped ramp to validate shift in breaking point
2. **PgBouncer**: add transaction-mode pooler → allows 10× more app connections with same PG max_connections
3. **Index audit**: run `EXPLAIN ANALYZE` on Browse + Enroll under load — high p95 may indicate missing index
4. **Re-measure**: stepped ramp after each infra change to track capacity curve improvement
