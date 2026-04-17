# Phase 6.3 — Load Baseline & Bottleneck Analysis
## Practice Booking System

**Authored**: 2026-04-17
**SHA baseline**: f9acabd (Phase 6.1 + 6.2 complete)
**Tool**: Locust 2.17.0 + uvicorn 4 workers
**VU peak (local)**: 1 000  |  **VU peak (CI)**: 50

---

## 1. Static Code Audit — Ranked Bottlenecks

Code audit performed prior to any load run. Rankings based on expected impact at 500+ VUs.

| Rank | Location | Type | Row-Locked? | Impact |
|------|----------|------|-------------|--------|
| 1 | `app/services/semester_service.py` — per-session capacity loop | N × ROW LOCK (SELECT FOR UPDATE per session) | ✅ | **HIGH** — serialises all concurrent enroll threads |
| 2 | `app/api/web_routes/programs.py:202-210` — credit deduction `WHERE credit_balance >= cost` | Single-row hot-spot per user | ✅ | **HIGH** — enroll throughput limited by row contention |
| 3 | `app/api/web_routes/tournaments.py:110-117` — browse list | 1 + 3N queries for N tournaments | ❌ | **MEDIUM** — 61 queries for 20 events |
| 4 | Missing index: `sessions(auto_generated)` | Full table scan on every enroll | — | **MEDIUM** — scanned per enrollment |
| 5 | `app/dependencies.py` — `get_current_user_web` = 1 DB query per request, no cache | Repeated lookup | — | **LOW–MED** — 1 extra query on every authenticated endpoint |
| 6 | Missing composite index: `semester_enrollments(user_id, semester_id)` | Seq-scan on withdraw/re-enroll check | — | **LOW** — worst at high-cardinality enrollment tables |

### 1.1 DB Pool Math

```
pool_size    = 20
max_overflow = 30
─────────────────
connections  = 50 per uvicorn worker

4 workers × 50 = 200 total PostgreSQL connections

PostgreSQL default: max_connections = 100
                                      ^^^
                 Pool will saturate PG at 2+ workers unless PG is reconfigured.
```

**Action**: set `max_connections = 300` in `postgresql.conf` (or add PgBouncer).

### 1.2 Rate-Limiting Notes

- IP-based limit (100 req / 60 s) — **functional**.
- Per-user limit (200 req / 60 s) — **dead**: `security.py:_get_user_id()` returns `None` (JWT decode is a TODO stub — see FINDING-01 / GitHub issue #52).
- Load tests run with `ENABLE_RATE_LIMITING=false` — tests the app layer, not the limiter.

---

## 2. Expected Scaling Behaviour (Pre-Fix Estimates)

| VU Count | Browse p95 | Enroll p95 | Expected behaviour |
|----------|-----------|-----------|-------------------|
| 50 | ≤ 80 ms | ≤ 250 ms | No contention; all requests complete cleanly |
| 100 | ≤ 120 ms | ≤ 400 ms | Light row contention on credit_balance; pool headroom OK |
| 200 | ≤ 200 ms | ≤ 700 ms | N+1 browse noticeable; capacity lock loop visible in slow_queries |
| 500 | ≤ 500 ms | ≤ 1 500 ms | Pool near saturation (50 connections/worker × 4 workers hits PG limit); 503s possible |
| 1 000 | > 1 000 ms | > 3 000 ms | **Breaking point**: pool exhausted; 5xx rate rises > 5%; p99 > 5 s |
| 5 000 | N/A | N/A | Not achievable without PgBouncer + index fixes |

> These are **static estimates**. Actual numbers will be populated by `LOAD_REPORT_{YYYYMMDD}.md` after a live run.

---

## 3. Concrete Optimisations

### 3.1 Index: `sessions(auto_generated)`

Every enrollment currently scans all sessions to find `auto_generated=True` ones for the semester.

```sql
-- Migration: add to a new Alembic revision
CREATE INDEX CONCURRENTLY ix_sessions_auto_generated
    ON sessions (semester_id, auto_generated)
    WHERE auto_generated = TRUE;
```

**Expected gain**: enroll latency −30–50% at 200+ VUs.

---

### 3.2 Composite Index: `semester_enrollments(user_id, semester_id, is_active)`

Withdraw and re-enroll checks scan by `(user_id, semester_id)` without a covering index.

```sql
CREATE INDEX CONCURRENTLY ix_sem_enroll_user_sem_active
    ON semester_enrollments (user_id, semester_id, is_active);
```

**Expected gain**: withdraw p95 −20% at 500+ VUs.

---

### 3.3 Fix N+1: `tournaments.py:110-117`

Replace individual per-tournament queries with a single `joinedload`:

```python
# Before (1 + 3N queries):
semesters = db.query(Semester).filter(...).all()
for s in semesters:
    s.enrollment_count  # lazy → N queries
    s.master_instructor  # lazy → N queries
    s.active_teams       # lazy → N queries

# After (1 query):
from sqlalchemy.orm import joinedload, selectinload
semesters = (
    db.query(Semester)
    .options(
        joinedload(Semester.master_instructor),
        selectinload(Semester.semester_enrollments),
    )
    .filter(...)
    .all()
)
```

**Expected gain**: browse p95 −60% at 200+ VUs (from 61 → 2 queries for 20 events).

---

### 3.4 Capacity Check: Replace Per-Session Loop with GROUP BY

Current code in `semester_service.py` loops over sessions and issues a `SELECT … FOR UPDATE` per session.

```sql
-- Replace N individual FOR UPDATE queries with a single aggregate:
SELECT
    s.id                                         AS session_id,
    COUNT(*) FILTER (WHERE b.status = 'CONFIRMED') AS confirmed_count,
    s.capacity
FROM sessions s
LEFT JOIN bookings b ON b.session_id = s.id
WHERE s.semester_id = :semester_id
  AND s.auto_generated = TRUE
GROUP BY s.id, s.capacity;
```

Then lock only the rows that actually need updating (confirmed_count approaching capacity).

**Expected gain**: enroll p95 −40% at 500+ VUs.

---

### 3.5 Auth Cache: `get_current_user_web`

Currently issues 1 DB query per authenticated request.

```python
# Option A — LRU cache (simple, per-process, 5-min TTL)
from functools import lru_cache
import time

_AUTH_CACHE: dict = {}
_AUTH_TTL = 300  # 5 minutes

def _cached_user(db, user_id: int):
    now = time.monotonic()
    cached = _AUTH_CACHE.get(user_id)
    if cached and now - cached[0] < _AUTH_TTL:
        return cached[1]
    user = db.query(User).filter(User.id == user_id).first()
    _AUTH_CACHE[user_id] = (now, user)
    return user

# Option B — Redis session store (recommended for multi-worker)
# Store serialised user dict in Redis with 5-min TTL on login;
# get_current_user_web reads Redis first, falls back to DB.
```

**Expected gain**: all authenticated endpoint p95 −10–20% (1 fewer DB round-trip).

---

### 3.6 PostgreSQL `max_connections` / PgBouncer

```ini
# postgresql.conf
max_connections = 300         # up from default 100

# OR add PgBouncer in transaction-pool mode:
# pool_mode = transaction
# max_client_conn = 1000
# default_pool_size = 50
```

**Expected gain**: eliminates 503 errors at 500+ VUs with 4 uvicorn workers.

---

## 4. Scaling Limit Estimates (After Fixes)

| Fix Applied | Estimated Max VUs (p95 < 1 s) |
|-------------|-------------------------------|
| Baseline (no fixes) | ~150–200 VUs |
| + N+1 browse fix (#3.3) | ~400 VUs (browse); write still limited |
| + sessions index (#3.1) + capacity GROUP BY (#3.4) | ~600 VUs |
| + PgBouncer + `max_connections=300` (#3.6) | ~2 000 VUs |
| + auth cache (#3.5) + composite index (#3.2) | ~3 000+ VUs |

---

## 5. Mitigation Checklist

- [ ] `CREATE INDEX ix_sessions_auto_generated` (§3.1)
- [ ] `CREATE INDEX ix_sem_enroll_user_sem_active` (§3.2)
- [ ] Fix N+1 in `tournaments.py` browse list (§3.3)
- [ ] Replace per-session capacity FOR UPDATE loop with GROUP BY (§3.4)
- [ ] Add auth cache in `get_current_user_web` (§3.5)
- [ ] Increase `max_connections = 300` or add PgBouncer (§3.6)
- [ ] Implement JWT decode in `security.py:_get_user_id()` — FINDING-01 / issue #52

---

## 6. Live Run Results (Populated After Gate Run)

> This section is populated automatically by `scripts/run_phase63_load.sh` → `analyze_load_results.py`.
> See `tests/performance/LOAD_REPORT_{YYYYMMDD}.md` for the versioned per-run report.

| Metric | Value |
|--------|-------|
| Run date | _TBD_ |
| Git SHA | _TBD_ |
| Peak VUs (local) | _TBD_ |
| Browse p95 | _TBD_ |
| Browse p99 | _TBD_ |
| Enroll p95 | _TBD_ |
| Enroll p99 | _TBD_ |
| Withdraw p95 | _TBD_ |
| 429 rate | _TBD_ |
| 5xx rate | _TBD_ |
| Breaking point VU | _TBD_ |
| slow_queries delta | _TBD_ |
| invariant_violations | _TBD_ |
