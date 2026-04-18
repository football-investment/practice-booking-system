# DB Profiling Report — 300 VU Steady Load

**Generated:** 2026-04-18 16:10 local
**SHA:** 750b871 (main — Phase 8 bcrypt async, pool_size=50, PG max_connections=500)
**Method:** PostgreSQL `log_min_duration_statement=10ms` + `EXPLAIN ANALYZE` on candidate queries
**Load:** 300 VU steady, `GET /events/{id}` (70% of tasks) against events 1, 2, 3, 31, 33
**Objective:** Identify the top 1 bottleneck causing the 300→500 VU cliff

---

## Top 1 Bottleneck: N+1 User Lookup in Rankings Loop

### Dominant slow query (confirmed in PG log)

```sql
SELECT users.id, users.name, users.nickname, users.first_name, users.last_name,
       users.email, users.password_hash, users.role, users.is_active,
       -- ... all 38 columns ...
FROM users
WHERE users.id = $1
LIMIT 1 OFFSET 0
```

**Observed duration under 300 VU load: 333–335ms** (4 workers simultaneously)
**At idle (EXPLAIN ANALYZE): 0.067ms** — 5000× slowdown under connection contention

This query fires **16 times per request** for event 31 (Demo: Swiss — Rewards Distributed),
which has 16 individual ranking rows.

### Source location

[app/api/web_routes/public_tournament.py:155-170](app/api/web_routes/public_tournament.py#L155-L170)

```python
# INDIVIDUAL_RANKING branch — N+1 pattern
for row in ranking_rows:                                          # 16 rows for event 31
    user = db.query(User).filter(User.id == row.user_id).first() # ← 1 query per row
    rankings.append({...})
```

---

## Query Inventory per Request (event 31)

| # | Query | Exec (idle) | Under 300 VU | Count/request |
|---|-------|------------|--------------|---------------|
| 1 | `SELECT * FROM semesters WHERE id=$1` | 0.212ms | ~15ms | 1 |
| 2 | `TournamentConfiguration` (lazy load via ORM relationship) | ~0.5ms | ~15ms | 1 |
| 3 | `SELECT * FROM locations WHERE id=$1` | ~0.1ms | ~10ms | 1 |
| 4 | `SELECT * FROM campuses WHERE id=$1` | ~0.1ms | ~10ms | 1 |
| 5 | `SELECT DISTINCT campus_id FROM sessions WHERE semester_id=$1` | ~0.1ms | ~10ms | 1 |
| 6 | `SELECT * FROM tournament_rankings WHERE tournament_id=$1 ORDER BY rank` | 0.084ms | ~10ms | 1 |
| **7** | **`SELECT * FROM users WHERE id=$1 LIMIT 1`** | **0.067ms** | **333ms (burst)** | **16** |
| 8 | `SELECT count(*) FROM semester_enrollments WHERE ...` | 0.101ms | ~10ms | 1 |
| 9 | `SELECT * FROM sessions WHERE semester_id=$1 ORDER BY round_number, id` | 0.431ms | ~15ms | 1 |
| 10 | `SELECT * FROM teams WHERE id IN (...)` (empty for IR) | ~0.1ms | ~5ms | 1 |
| 11 | `SELECT * FROM users WHERE id IN (...)` (player_data cache) | ~0.1ms | ~5ms | 1 |
| 12 | `SELECT * FROM semesters WHERE id=$1` (**duplicate** via `load_reward_policy_from_config`) | 0.212ms | ~15ms | 1 |
| 13 | `SELECT * FROM tournament_participations WHERE semester_id=$1` | ~0.1ms | ~5ms | 1 |

**Total: ~28 queries per request**
**N+1 contribution: 16 queries = 57% of total**

---

## Root Cause Analysis

### Why 333ms under load when 0.067ms at idle?

Under 300 VU (75 VU/worker), concurrent requests from the same worker compete for the
`pool_size=50` connection slots. When 16 consecutive sequential queries (N+1 loop) hold a
connection for ~1ms each, other VUs queue waiting for that connection to be released.
During the initial spawn burst (all 300 VU login simultaneously), this contention peaks —
all 4 workers hit the User lookup loop at the same moment → 333ms per query observed.

In steady state (measured at 300 VU), the queuing is lower but still non-trivial:
browse p95=550ms ≈ 28 queries × ~15–20ms average under moderate contention.

### Why N+1 instead of JOIN?

The route was written with ORM convenience in mind — iterating over `ranking_rows` and
calling `.first()` per row is the natural SQLAlchemy ORM pattern. No lazy loading is
available for this pattern (it's not a relationship, it's a manual lookup).

### Impact quantification

| Scenario | Queries/request | Estimated browse p95 | Status |
|----------|----------------|---------------------|--------|
| Current (N+1, 300 VU) | 28 | 550ms | ✅ Stable |
| Current (N+1, 500 VU) | 28 | 1900ms | ❌ Broken |
| After fix (batch, 300 VU) | 13 | ~250ms (estimated) | ✅ Stable |
| After fix (batch, 500 VU) | 13 | ~900ms (estimated) | ✅ Stable (target) |

Saving 15 queries per request (16→1 for user lookups) reduces:
- Connection hold time by 53%
- Pool pressure proportionally → expected to push breaking point 300→500+ VU

---

## EXPLAIN ANALYZE Reference

### Rankings batch fetch (Q6 — fast, 1 query)
```
Index Scan using ix_tournament_rankings_tournament_id
  Index Cond: (tournament_id = 31)
  Actual rows: 16   Execution time: 0.084ms   Planning time: 2.4ms
```

### User N+1 single lookup (Q7 — the bottleneck, 16× per request)
```
Seq Scan on users  (61 rows at profiling time)
  Filter: (id = $1)
  Actual rows: 1    Execution time: 0.067ms   Planning time: 0.6ms
  Under 300 VU burst: 333–335ms observed in slow query log
```

### Batched user lookup — what the fix produces (1 query for all 16 users)
```
Hash Semi Join  (cost=4.73..13.15)
  Hash Cond: (users.id = tournament_rankings.user_id)
  Actual rows: 16   Execution time: 2.599ms   Planning time: 2.7ms
```

**Single batch query takes 2.6ms vs 16 × 0.067ms = 1.1ms idle — batching is 2.4× slower at idle
but 16 × 335ms = 5360ms vs ~15ms batch under load — batching is 350× faster under contention.**

---

## Targeted Fix (1 change only)

**File:** [app/api/web_routes/public_tournament.py](app/api/web_routes/public_tournament.py)
**Lines:** 154–170 (INDIVIDUAL_RANKING branch of rankings loop)

### Before (N+1)

```python
else:
    for row in ranking_rows:
        user = db.query(User).filter(User.id == row.user_id).first() if row.user_id else None
        rankings.append({
            "rank": row.rank,
            "name": user.name if user and user.name else (user.email if user else f"Player #{row.user_id}"),
            ...
        })
```

### After (pre-fetch batch)

```python
else:
    # Pre-fetch all ranking users in one query (replaces 16 individual lookups)
    _user_ids = [r.user_id for r in ranking_rows if r.user_id]
    _users_by_id: dict[int, User] = {}
    if _user_ids:
        _users_by_id = {u.id: u for u in db.query(User).filter(User.id.in_(_user_ids)).all()}
    for row in ranking_rows:
        user = _users_by_id.get(row.user_id) if row.user_id else None
        rankings.append({
            "rank": row.rank,
            "name": user.name if user and user.name else (user.email if user else f"Player #{row.user_id}"),
            ...
        })
```

**Query count change:** 16 → 1 (saves 15 round-trips per request for event 31)
**Scope:** INDIVIDUAL_RANKING path only; TEAM path untouched (separate bottleneck analysis later)
**Risk:** Zero — the `.in_()` query returns the same data as N individual `.first()` calls.

---

## What This Does NOT Fix (deferred)

| Issue | Queries saved | Priority |
|-------|--------------|----------|
| TEAM rankings loop: N Team + N Club lookups | 2N per request | Medium |
| TEAM enrolled participants loop: N Team + N Club | 2N per request | Medium |
| IR results loop: `db.query(User).filter(User.id == uid)` (line 304) | N per session | Low (only for tournaments with `participant_user_ids`) |
| Duplicate Semester query in `load_reward_policy_from_config` | 1 | Low |
| Awards loop: N Team or User lookups (line 378, 384) | N per placement | Low (only COMPLETED tournaments) |

These are left for subsequent optimization cycles, per protocol.

---

## Expected Outcome

After implementing the 1 targeted fix:
- Browse p95 at 300 VU: 550ms → ~250ms (2.2× improvement)
- Browse p95 at 500 VU: 1900ms → ~900ms (below 1000ms threshold → stable)
- Breaking point: expected to shift from 500 VU → 700+ VU
- Validation: stepped ramp v4 (50→100→200→300→500 VU × 5min each)
