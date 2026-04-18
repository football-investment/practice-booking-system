# Phase 9 — Stepped Ramp v4: N+1 Fix Report

**Generated:** 2026-04-18 16:34 local
**SHA:** 9095997 (main)
**Fix:** Batched User lookup in INDIVIDUAL rankings loop — `WHERE id IN (...)` replaces N × `WHERE id = $1`
**Configuration:** pool_size=50, max_overflow=100, PG max_connections=500, bcrypt async (all Phase 7+8 changes retained)
**Protocol:** 5 levels × 300s hold, 15s cooldown
**Comparison baseline:** v3 (LOAD_REPORT_STEPPED_RAMP_V3_BCRYPT_ASYNC.md — SHA 750b871)

---

## Capacity Curve — v4 (N+1 fix)

| VUs | Requests | RPS | Error% | Browse p95 | Enroll p95 | Login p95 | slow_q Δ | Status |
|-----|----------|-----|--------|-----------|-----------|----------|---------|--------|
|  50 |    20330 |  67.8 |   0.0% |        22ms |        20ms |      620ms |        1 | ✅ Stable |
| 100 |    40791 | 136.1 |   0.0% |        20ms |        19ms |      630ms |        1 | ✅ Stable |
| 200 |    80459 | 268.7 |   0.0% |        37ms |        33ms |      780ms |        5 | ✅ Stable |
| 300 |   111129 | 370.9 |   0.0% |       240ms |       250ms |     3100ms |       13 | ✅ Stable |
| 500 |   107651 | 360.0 |   0.2% |      1300ms |      1500ms |     1600ms |       97 | ❌ BROKEN |

**Breaking point: 500 VUs** (same as v3)
**Last stable level: 300 VUs** (same as v3)
**invariant_violations Δ = 0** at all levels — no data integrity issues

---

## Fix Impact vs v3 Baseline

### Browse p95 improvement (key metric)

| VUs | v3 Browse p95 | v4 Browse p95 | Improvement |
|-----|--------------|--------------|-------------|
|  50 |         29ms |         22ms | **1.3×** |
| 100 |         29ms |         20ms | **1.5×** |
| 200 |         72ms |         37ms | **1.9×** |
| 300 |        550ms |        240ms | **2.3×** ← matches profiling prediction (250ms) |
| 500 |       1900ms |       1300ms | **1.5×** |

### Throughput improvement

| VUs | v3 RPS | v4 RPS | Change |
|-----|--------|--------|--------|
| 200 | 262.6 | 268.7 | +2.3% |
| 300 | 320.8 | **370.9** | **+15.5%** |
| 500 | 281.4 | **360.0** | **+27.9%** |

### Failure rate improvement

| VUs | v3 Failures | v4 Failures | Change |
|-----|------------|------------|--------|
| 500 | 813 (1.0%) | **169 (0.2%)** | **4.8× fewer** |

### slow_queries Δ improvement

| VUs | v3 slow_q Δ | v4 slow_q Δ | Change |
|-----|------------|------------|--------|
| 300 | 61 | **13** | **4.7× fewer** |
| 500 | 101 | 97 | similar |

---

## Profiling Prediction Accuracy

The DB_PROFILING_300VU.md report predicted:
- Browse p95 at 300 VU after fix: ~250ms → **Actual: 240ms (96% accurate)**
- Browse p95 at 500 VU after fix: ~900ms → **Actual: 1300ms (off by 44%)**

The 300 VU prediction was accurate. At 500 VU, the remaining N+1 loops (TEAM rankings,
participant lookups, enroll endpoint queries) keep latency above the 1000ms threshold.

---

## 500 VU Gap Analysis

Browse p95=1300ms is 30% above the 1000ms stability threshold. The 169 failures at 0.2%
indicate the system is borderline, not catastrophically broken (v3 had 1.0% failures).

**Remaining slow_queries Δ=97 at 500 VU** — the batched ranking fix saved slow_q at 300 VU
(Δ=61→13), but at 500 VU the improvement is marginal (Δ=101→97). This means:

1. At 300 VU: the N+1 User lookups were the dominant source of slow queries → fixed ✅
2. At 500 VU: a different set of queries becomes slow — likely from concurrent enroll requests,
   the programs.py browse route (5 queries), or remaining N+1 loops in other code paths

**Candidates for next optimization** (not acted on yet, per protocol):

| Code location | Pattern | Queries/request | Impact |
|---------------|---------|----------------|--------|
| `public_tournament.py:185-191` | TEAM enrolled participants loop: N Team + N Club | 2N | Medium |
| `public_tournament.py:378,384` | Awards loop: N Team/User lookups per placement | N | Low |
| `public_tournament.py:302-308` | IR results loop: N User lookups per session | N×M | Low |
| `tournament_reward_orchestrator.py:110` | Duplicate Semester query (also done at line 51) | 1 | Low |

---

## Phase Progression Summary

| Phase | Change | Last Stable | Break VU | Browse p95 @ 300VU | Browse p95 @ 500VU | Failures @ 500VU |
|-------|--------|------------|----------|-------------------|-------------------|-----------------|
| v1 | baseline (pool 20/30, PG 100) | **100 VU** | **200 VU** | ~450ms | N/A | 22% |
| v2 | Phase 7: pool 50/100, PG 500 | **300 VU** | **500 VU** | 550ms | 1700ms | 0.9% |
| v3 | Phase 8: bcrypt asyncio.to_thread | **300 VU** | **500 VU** | 550ms | 1900ms | 1.0% |
| v4 | Phase 9: N+1 batch fix | **300 VU** | **500 VU** | **240ms** | **1300ms** | **0.2%** |

Key progression:
- v1→v2: infrastructure scaling doubled stable ceiling (100→300 VU)
- v2→v3: login p95 fixed (6600ms→2100ms), no ceiling change
- v3→v4: **browse p95 at 300 VU cut by 2.3×**, **failures at 500 VU cut 5×**; ceiling unchanged

---

## Decision per Protocol

- 500 VU NOT stable → **document new state, do NOT optimize immediately**
- PgBouncer: NOT needed (Login err=0%, pool not exhausted)
- The fix is confirmed effective at 300 VU (prediction validated)
- 500 VU is borderline (0.2% errors, Browse p95=1300ms vs 1000ms threshold)

**The 500 VU cliff is now a latency cliff, not a failure cliff** (0.2% error rate is near-zero).
Further optimization of remaining N+1 loops (TEAM participants, awards) may close the 300ms gap.

---

## Conclusion

Phase 9 objective **achieved**: N+1 fix validated, production-representative improvement.

- **Browse p95 at 300 VU: 550ms → 240ms (2.3×)** — prediction confirmed
- **RPS at 300 VU: 320 → 371 (+16%)** — better throughput at stable operating point
- **Failures at 500 VU: 1.0% → 0.2% (5× fewer)** — system much closer to stable
- **slow_queries Δ at 300 VU: 61 → 13 (4.7× fewer slow queries)**
- Breaking point technically unchanged (500 VU), but system behavior at 500 VU improved significantly

*Next: analyze remaining slow_queries at 500 VU to identify second N+1 candidate.*
