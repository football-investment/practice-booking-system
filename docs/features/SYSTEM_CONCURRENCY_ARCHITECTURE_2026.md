# System Concurrency Architecture 2026

**Date:** 2026-02-19
**Status: STABLE REFERENCE — update on each new pipeline hardening**
**Audience:** Engineering (backend), Code review, New feature design

---

## 1. Overview

Four independent pipelines have been formally hardened against concurrency races:

| Pipeline | Sprint closed | Stable doc |
|---|---|---|
| Enrollment | 2026-02-17 | `ARCHITECTURE_FREEZE_2026-02-17.md` |
| Booking | 2026-02-18 | *(implicit, see `bk01concurr00` migration)* |
| Reward / XP | 2026-02-19 | `REWARD_XP_PIPELINE_STABLE_2026-02-19.md` |
| Skill Progression | 2026-02-19 | `SKILL_PROGRESSION_PIPELINE_STABLE_2026-02-19.md` |

All four follow the **same five-layer guard pattern** defined in Section 2.

---

## 2. Standard Guard Pattern

Every new pipeline or feature that writes shared user state MUST implement
all applicable layers before being considered production-ready.

```
┌────────────────────────────────────────────────────────────────┐
│  Layer 1 — Row-level isolation                                 │
│  SELECT … FOR UPDATE before any read-modify-write cycle        │
│  (prevents TOCTOU: two readers see same state, both write)     │
├────────────────────────────────────────────────────────────────┤
│  Layer 2 — Atomic SQL for numeric counters                     │
│  UPDATE t SET col = col + :delta RETURNING col                 │
│  (never read balance into Python, modify, write back)          │
├────────────────────────────────────────────────────────────────┤
│  Layer 3 — SAVEPOINT for insert-or-ignore semantics            │
│  sp = db.begin_nested()                                        │
│  db.add(obj); sp.commit()                                      │
│  except IntegrityError: sp.rollback(); re-query existing       │
│  (eliminates TOCTOU on check-then-insert pairs)                │
├────────────────────────────────────────────────────────────────┤
│  Layer 4 — DB unique constraints / partial indexes             │
│  Last-resort backstop — enforced even if app guards fail       │
│  (must exist for every business invariant: one badge per type, │
│   one participation per (user, semester), …)                   │
├────────────────────────────────────────────────────────────────┤
│  Layer 5 — Invariant monitor (weekly CI)                       │
│  scripts/validate_*.py                                         │
│  Detects guard failures that slip through layers 1–4           │
└────────────────────────────────────────────────────────────────┘
```

### Quick reference: which layer covers which race class

| Race class | Layer | Mechanism |
|---|---|---|
| Double-write (two concurrent writers, one overwriting the other) | 1 | FOR UPDATE |
| Lost update (read-modify-write on numeric field) | 2 | Atomic SQL |
| Double-insert (two concurrent INSERT for same logical row) | 3+4 | SAVEPOINT + unique constraint |
| Retry amplification (pipeline reruns produce duplicate rows) | 3+4 | Idempotency key + SAVEPOINT |
| Silent stat regression (JSONB last-writer-wins) | 1 | FOR UPDATE on JSONB row |
| Ordering non-determinism (concurrent inserts with same timestamp) | 1 | Stable ORDER BY (col, id) |

---

## 3. Pipeline-by-pipeline race map

### 3.1 Enrollment Pipeline

**Guard surface:** `SemesterEnrollment`, `Semester.current_enrollment_count`

| Race | Guard |
|---|---|
| Double enrollment (concurrent ENROLL for same user/tournament) | FOR UPDATE on Semester row; unique constraint `uq_user_semester_enrollment` |
| Enrollment count drift | Atomic SQL `UPDATE semesters SET current_enrollment_count = current_enrollment_count + 1` |
| Unenroll lost-update | FOR UPDATE on SemesterEnrollment; atomic decrement |
| State machine bypass | `ENROLLMENT_OPEN` precondition: `campus_id` required |

**Migration:** `bk01concurr00` (enrollment guards), `se001`/`se002` (system events index)
**Monitor:** `scripts/validate_enrollment_pipeline.py`

---

### 3.2 Booking Pipeline

**Guard surface:** `Booking`, `Session.available_spots`

| Race | Guard |
|---|---|
| Double booking (concurrent CREATE for same slot) | SAVEPOINT + unique constraint `(session_id, user_id)` |
| Spots drift | Atomic SQL decrement on `sessions.available_spots` |
| Cancel double-refund | FOR UPDATE on Booking; idempotency key on credit refund |
| Cross-slot double-book | Application-layer overlap check under FOR UPDATE |

**Migration:** `bk01concurr00`
**Monitor:** `scripts/validate_booking_pipeline.py`

---

### 3.3 Reward / XP Pipeline

**Guard surface:** `TournamentParticipation`, `TournamentBadge`, `XPTransaction`,
`CreditTransaction`, `users.xp_balance`, `users.credit_balance`

| Race | Guard |
|---|---|
| R01/R03 — double finalization | FOR UPDATE on `Semester`; `_FINALIZED_STATUSES` idempotency gate |
| R02 — double participation row | FOR UPDATE on `TournamentParticipation`; `IntegrityError → rollback + re-query` |
| R04 — football_skills JSONB overwrite | FOR UPDATE on `UserLicense` in Step 1.5 |
| R05 — double badge award | SAVEPOINT + `uq_user_tournament_badge` unique index |
| R06 — double XP/credit grant | Idempotency key + SAVEPOINT + `uq_xp_transaction_idempotency` |
| R07 — xp/credit balance lost update | Atomic SQL `UPDATE users SET xp_balance = xp_balance + :delta` |

**Migration:** `rw01concurr00`
**Monitor:** `scripts/validate_reward_pipeline.py`
**Freeze:** `REWARD_XP_PIPELINE_STABLE_2026-02-19.md`

---

### 3.4 Skill Progression Pipeline

**Guard surface:** `UserLicense.football_skills` JSONB, `TournamentParticipation.skill_rating_delta`

| Race | Guard |
|---|---|
| S01 — non-deterministic EMA replay order | `ORDER BY (achieved_at ASC, id ASC)` in all 4 history-replay queries |
| S02 — assessment ↔ tournament JSONB last-writer-wins | FOR UPDATE on `UserLicense` in `recalculate_skill_average` (assessment path) |
| S03 — float vs. dict format mismatch | `_normalise_skill_entry()` promotion loop in Step 1.5 before deep-merge; assessment writes `baseline` sub-key for dict-format entries |
| S04 — lock hold time amplification | Accepted residual risk (bounded to per-user serialisation; no cross-user impact) |
| S05 — skill_rating_delta non-idempotent on retry | Write-once guard: `if participation.skill_rating_delta is None` |
| S06 — opponent factor stale read | Accepted (reads `baseline` field, write-once at onboarding) |

**Migration:** no schema changes (application-layer guards only)
**Monitor:** `scripts/validate_skill_pipeline.py`
**Legacy debt:** `LEGACY-DEBT-001` — 14 pre-hardening licenses (remediation: `scripts/maintenance/normalise_legacy_football_skills.py`)
**Freeze:** `SKILL_PROGRESSION_PIPELINE_STABLE_2026-02-19.md`

---

## 4. Lock ordering rules (deadlock prevention)

PostgreSQL deadlocks occur when two transactions acquire locks in opposite order.
The following lock acquisition order is **mandatory** in all new code.

```
Lock order (always acquire in this sequence within a single transaction):
  1. Semester / Tournament row          (coarse — one per tournament)
  2. UserLicense row                    (mid — one per user per pipeline)
  3. TournamentParticipation row        (fine — one per user per tournament)
  4. No further FOR UPDATE in same txn  (all other reads are unlocked)
```

**Examples of conforming lock order:**

| Path | Locks acquired |
|---|---|
| `finalize()` | Semester FOR UPDATE → (no UserLicense lock in finalizer itself) |
| `distribute_rewards_for_user()` | TournamentParticipation FOR UPDATE → UserLicense FOR UPDATE |
| `recalculate_skill_average()` | UserLicense FOR UPDATE (by id) |
| `record_tournament_participation()` | TournamentParticipation (via upsert + flush, no explicit FOR UPDATE needed) |

**Anti-patterns to avoid:**

```python
# ❌ WRONG: acquiring UserLicense THEN Semester in same txn — potential deadlock
lic = db.query(UserLicense).with_for_update().first()
sem = db.query(Semester).with_for_update().first()

# ✅ CORRECT: Semester first (if both needed)
sem = db.query(Semester).with_for_update().first()
lic = db.query(UserLicense).with_for_update().first()
```

**Same-row rule:** Two transactions locking the same row via different WHERE clauses
(e.g., `WHERE id = :id` vs `WHERE (user_id, specialization_type, is_active)`) still
target the same physical row — PostgreSQL resolves this without deadlock.  This is
exactly the situation between `recalculate_skill_average` (locks by `id`) and
the tournament Step 1.5 (locks by `(user_id, specialization_type, is_active)`).

---

## 5. Mandatory checklist for new features

Before any new pipeline or write-heavy endpoint is merged, verify each item:

```
[ ] FOR UPDATE acquired before any read-modify-write on shared state
[ ] Numeric counter updates use atomic SQL (UPDATE … SET col = col + :delta)
[ ] New insert paths use SAVEPOINT pattern (or idempotency key) for retry safety
[ ] DB unique constraint exists for every business invariant
[ ] No JSONB column is written without FOR UPDATE on the owning row
[ ] ORDER BY on history-replay queries includes (timestamp, id) stable sort
[ ] Weekly invariant check added to validate_*.py (or new script)
[ ] Freeze notice added to the pipeline's STABLE doc
[ ] P0 concurrency tests written (RED → GREEN pattern)
```

---

## 6. Weekly monitoring cadence

```bash
# Monday 09:00 UTC — all four pipeline monitors
0 9 * * 1 cd /path/to/project && \
  python scripts/validate_enrollment_pipeline.py >> logs/enrollment_weekly.log 2>&1 && \
  python scripts/validate_reward_pipeline.py    >> logs/reward_weekly.log    2>&1 && \
  python scripts/validate_skill_pipeline.py     >> logs/skill_weekly.log     2>&1
```

---

## 7. Next sprint recommendations

The system is now **stable and hardened**. The following sprint directions are
ordered by expected value / risk ratio:

### Option A — Performance audit (lock contention + query efficiency)

**Motivation:** The skill pipeline's `get_skill_profile` makes O(N×M) DB queries
inside a FOR UPDATE lock scope, potentially causing serialised bottleneck for
high-tournament users.  Under batch finalization (N players, concurrent distribution),
this is amplified N-fold.

**Scope:**
1. Measure P95 lock hold time for `UserLicense FOR UPDATE` during tournament finalization
   (add `time.perf_counter` instrumentation to Step 1.5, log via `logger.debug`)
2. Profile `get_skill_profile` query count for a 64-player tournament
3. Consider pre-computing skill profile BEFORE acquiring FOR UPDATE (acceptable
   staleness: one more tournament's delta, healed on next run)
4. `_compute_opponent_factor` makes 1 DB query per opponent — batch with a single
   `WHERE user_id IN (...)` query

**Acceptance:** P95 lock hold time < 200 ms for a 64-player tournament finalization.

---

### Option B — Observability (structured logging + lock timing metrics)

**Motivation:** All four pipelines use `logger.info/debug` but without structured
fields.  Diagnosing a production race requires grepping unstructured logs.

**Scope:**
1. Add structured log fields to all FOR UPDATE acquisitions:
   ```python
   logger.info("skill_writeback.lock_acquired",
               extra={"user_id": user_id, "license_id": lic.id,
                      "lock_wait_ms": int((t1 - t0) * 1000)})
   ```
2. Add `lock_wait_ms`, `query_count`, `skills_updated` to Step 1.5 log line
3. Define a log schema (JSON) for all concurrency-critical paths
4. Add Grafana/Datadog dashboard queries for:
   - `P95(lock_wait_ms)` per pipeline
   - Error rate on `IntegrityError` rollback paths (R02/R05/R06)
   - `skill_rating_delta` null rate trend over time

**Acceptance:** All concurrency-critical paths emit structured JSON logs with
timing and outcome fields; one dashboard covers all four pipelines.

---

### Recommendation

**Option B first** (Observability), then **Option A** (Performance).

Rationale: Without structured logs and timing metrics, performance issues are
invisible until they manifest as user-facing latency.  Observability enables
data-driven prioritisation of the specific bottlenecks identified in Option A.
The lock hold time amplification in `get_skill_profile` is a known risk but
requires measurement to quantify before optimising.

---

## 8. Known residual risks (accepted)

| ID | Description | Severity | Status |
|---|---|---|---|
| LEGACY-DEBT-001 | 14 pre-hardening `current_level < 40` slots; 232 float-format entries | LOW | TRACKED — healed on next tournament finalization; one-time migration available |
| RESIDUAL-S01 | `skill_rating_delta` may be computed with incomplete EMA history for concurrent sibling tournaments | LOW | ACCEPTED — field is audit-only; `football_skills` (authoritative) is correct |
| RESIDUAL-S04 | `get_skill_profile` makes O(N×M) queries inside FOR UPDATE lock scope | LOW-MEDIUM | MONITORED — addressable in Performance sprint |

---

*End of System Concurrency Architecture 2026*
*Next revision: after Performance audit or Observability sprint.*
