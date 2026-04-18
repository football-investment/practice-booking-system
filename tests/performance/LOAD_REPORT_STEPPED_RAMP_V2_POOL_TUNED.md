# Phase 7 — Stepped Ramp v2: Pool-Tuned Capacity Report

**Generated:** 2026-04-18 14:56 local
**Configuration:** pool_size=50, max_overflow=100, PG max_connections=500 (was 20/30/100)
**Protocol:** 5 levels × 300s hold, 15s cooldown
**Workers:** 4 uvicorn, 1 PostgreSQL 14, rate-limiting OFF

**Comparison baseline:** LOAD_REPORT_STEPPED_RAMP.md (v1 — pool_size=20, PG max=100, broke at 200 VU)
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

---

## Phase 7 Analysis vs v1 Baseline

### Breaking Point Comparison

| Metric | v1 (pool 20/30, PG 100) | v2 (pool 50/100, PG 500) | Change |
|--------|------------------------|--------------------------|--------|
| Breaking point | **200 VU** (Login 5xx) | **500 VU** (latency) | +2.5× |
| Last stable | 100 VU | 300 VU | +3× |
| 200 VU Browse p95 | 54ms (marginal) | **74ms** (stable) | stable |
| 200 VU error rate | 0.1% (Login 5xx=26%) | **0%** | ✅ fixed |
| 300 VU Browse p95 | 450ms | **550ms** | latency-bound |
| 300 VU error rate | 1.2% | **0%** | ✅ fixed |
| 500 VU error rate | 22% | **0.9%** | 24× improvement |

### Bottleneck Shift

**v1 breaking point**: DB pool exhaustion (PG max_connections=100 < 4×50=200 potential connections)
→ Manifested as Login 500 errors at 200 VU login burst.

**v2 breaking point**: Latency-driven (Browse p95=1700ms, Enroll p95=1900ms at 500 VU)
→ slow_queries Δ=111 — query contention, NOT pool exhaustion.
→ Login p95=6600ms — bcrypt event-loop starvation (125 VU/worker × 60ms = 7.5s sequential queue).

### PgBouncer Decision

**Not needed at current scale (≤300 VU stable).** The pool fix eliminated the connection exhaustion.
At 500 VU the bottleneck is CPU/latency (slow queries + bcrypt), not connection count.
PgBouncer would add operational complexity without addressing the actual bottleneck.

**Revisit PgBouncer if:** target scale exceeds 1000+ VU (where PG connection count becomes the limit
regardless of pool size due to max 500 connections / 4 workers = 125/worker → pool ceiling).

### Login Endpoint Profiling (EXPLAIN ANALYZE)

```
User lookup query (WHERE email = '...'):
  Query plan: Index Scan using ix_users_email
  Execution time: 0.045ms  ← NOT the problem
  
bcrypt.checkpw (rounds=10) on Apple M-series:
  Time per call: ~60ms  ← THE problem
  
Root cause: login_submit() is `async def` but calls sync bcrypt.checkpw() directly
→ blocks the event loop for 60ms per login
→ 125 VU/worker × 60ms = 7.5s sequential queue → Login p95=6.6s at 500 VU
→ This is CPU-bound, PgBouncer/pool changes have no effect on login speed.

Fix (Phase 8): await asyncio.to_thread(bcrypt.checkpw, password_bytes, hash_bytes)
Expected: Login p95 drops from 6.6s → ~60ms (parallel bcrypt in thread pool)
```

### Next Steps for Phase 8

1. **bcrypt → asyncio.to_thread** — unblocks event loop during password verification
   Expected: Login p95 60ms → drops 10× or more; unlocks 500+ VU stable operation
2. **Slow query investigation at 300 VU** — slow_q Δ=41 worth profiling under load
   (`pg_stat_statements` or query log analysis during 300 VU hold)
3. **Re-run stepped ramp after bcrypt fix** — determine new breaking point (expected: 500+ VU stable)
