# Performance Audit Plan — Option A

**Date:** 2026-02-19
**Status: DATA COLLECTION PHASE — no optimization until metrics collected**
**Measurement window opens:** 2026-02-19 (first production deploy with lock_logger)
**Measurement window closes:** 2026-02-24 (5 days minimum)
**Decision date:** 2026-02-24 or later

---

## 1. Objective

Determine which concurrency lock paths (if any) require optimization, based on
measured production data.  **No optimization is performed before data is collected.**

The four hardened pipelines (Enrollment, Booking, Reward/XP, Skill Progression)
now emit structured `lock_released` log events via `app.utils.lock_logger`.
This plan defines:

- What to measure
- How long to collect
- Decision thresholds for each metric
- Exact optimization steps per threshold breach

---

## 2. Measurement Infrastructure

### Lock event schema (`lock_released`)

```json
{
  "event":            "lock_released",
  "pipeline":         "skill",
  "entity_type":      "UserLicense",
  "entity_id":        null,
  "caller":           "distribute_rewards_for_user.skill_writeback",
  "lock_released_at": "2026-02-24T10:15:32.456Z",
  "duration_ms":      187.3
}
```

### Instrumented call sites (5 total)

| Caller | Pipeline | Entity | Race |
|---|---|---|---|
| `TournamentFinalizer.finalize` | `reward` | `Semester` | R01/R03 |
| `distribute_rewards_for_user.idempotency_guard` | `reward` | `TournamentParticipation` | R02 |
| `distribute_rewards_for_user.skill_writeback` | `skill` | `UserLicense` | R04 |
| `FootballSkillService.recalculate_skill_average` | `skill` | `UserLicense` | S02 |
| `award_badge.duplicate_check` | `reward` | `TournamentBadge` | R05 |

### Monitoring scripts

```bash
# Daily sanity check (already in CI cron):
python scripts/validate_lock_metrics.py --log-file logs/app.log

# Full performance report (run on 2026-02-24):
python scripts/report_lock_performance.py --log-file logs/app.log --since-days 5

# JSON output for dashboard:
python scripts/report_lock_performance.py --log-file logs/app.log --json
```

---

## 3. Decision Thresholds

### 3.1 Primary — `skill` pipeline UserLicense lock

**Rationale:** `distribute_rewards_for_user.skill_writeback` acquires FOR UPDATE
on `UserLicense`, then calls `get_skill_profile(db, user_id)` which makes O(N×M)
DB queries inside the lock scope (RESIDUAL-S04 from architecture doc).  Under
batch finalization (64 players, concurrent distribution), this is amplified 64-fold.

| Metric | Value | Action |
|---|---|---|
| **P95 ≤ 200 ms** | ✅ No action needed | Continue monitoring |
| **P95 > 200 ms** | ⚠️ Threshold breached | Start batch-query optimisation (§4.1) |
| **P95 > 2 000 ms** | ❌ Critical | Escalate immediately — lock blocks concurrent users |

### 3.2 Primary — `reward` pipeline Semester lock

**Rationale:** `TournamentFinalizer.finalize` acquires FOR UPDATE on `Semester`
and holds it through the entire finalization + reward distribution cycle
(potentially several seconds for large tournaments).

| Metric | Value | Action |
|---|---|---|
| **P95 ≤ 500 ms** | ✅ No action needed | Continue monitoring |
| **P95 > 500 ms** | ⚠️ Threshold breached | Investigate commit boundary narrowing (§4.2) |
| **P95 > 2 000 ms** | ❌ Critical | Escalate immediately |

### 3.3 Global — Deadlock count

| Metric | Value | Action |
|---|---|---|
| **count = 0** | ✅ | Continue monitoring |
| **count > 0** | ❌ | **Immediate incident sprint** — review lock ordering (§4.3) |

### 3.4 Secondary — IntegrityError rate

| Metric | Value | Action |
|---|---|---|
| **rate ≤ 5 %** | ✅ | Expected from SAVEPOINT paths (R02/R05/R06) |
| **rate > 5 %** | ⚠️ | Review unique constraint coverage; possible missing index |

---

## 4. Optimization Playbook (pending measurement)

> **Do not implement any item below until §3 thresholds are breached.**

### 4.1 Batch-query optimisation — `get_skill_profile` N×M elimination

**Triggers:** `skill.UserLicense.P95 > 200 ms`
**Known cause:** `RESIDUAL-S04` — `_compute_opponent_factor` makes 1 DB query per
opponent in a player's tournament history.  For a user with 50 tournaments × 8
opponents = 400 DB round-trips inside the FOR UPDATE lock scope.

**Implementation plan (do not start before data confirms threshold breach):**

1. Pre-fetch all opponent user IDs for the target user in a single
   `WHERE user_id IN (SELECT opponent_id FROM ... WHERE user_id = :uid)` query.
2. Batch-load opponent `UserLicense` baseline fields with
   `SELECT user_id, football_skills FROM user_licenses WHERE user_id IN (:ids)`.
3. Move `get_skill_profile` call to **before** the FOR UPDATE acquisition.
   Acceptable staleness: one more tournament's delta, healed on next finalization.
4. Add instrumentation to measure `get_skill_profile` query count per call
   (`SQLAlchemy event listener` or `db.execute()` wrapper counter).
5. Acceptance criterion: `skill.UserLicense.P95 < 200 ms` for a 64-player
   tournament finalization batch.

**Files to change:**
- `app/services/skill_progression_service.py` — `_compute_opponent_factor()`
- `app/services/tournament/tournament_reward_orchestrator.py` — Step 1.5

**Pre-merge checklist:** New P0 concurrency tests (RED → GREEN), full unit suite,
lock_timer shows improved P95 in staging.

---

### 4.2 Commit boundary narrowing — `TournamentFinalizer.finalize`

**Triggers:** `reward.Semester.P95 > 500 ms`
**Known cause:** The Semester FOR UPDATE is currently held through the entire
`distribute_rewards_for_tournament()` call, which may take several seconds for
large fields (64+ players, multiple badge types).

**Investigation steps (do not start before data confirms threshold breach):**

1. Add per-user `distribute_rewards_for_user` timing to the lock log
   (already instrumented — extract from existing `lock_released` events).
2. Determine whether the Semester lock needs to be held through reward
   distribution, or whether the idempotency guard can be tightened:
   - Option A: Move `distribute_rewards_for_tournament` to **after** `db.commit()`
     (tournament status already REWARDS_DISTRIBUTED — idempotency gate holds).
   - Option B: Use a two-phase commit: `COMPLETED` commit → release Semester lock
     → `REWARDS_DISTRIBUTED` update in separate transaction.
3. Evaluate deadlock risk of each option against the lock ordering rules
   in `SYSTEM_CONCURRENCY_ARCHITECTURE_2026.md §4`.
4. Acceptance criterion: `reward.Semester.P95 < 500 ms` for a 64-player field.

**Files to change:**
- `app/services/tournament/results/finalization/tournament_finalizer.py`

---

### 4.3 Deadlock incident sprint

**Triggers:** `deadlocks > 0`
**Immediate steps:**

1. Extract the full PostgreSQL deadlock detail from logs
   (`pg_deadlock_detected` or `ERROR: deadlock detected` with full DETAIL block).
2. Map the two lock chains to the acquire-order table in
   `SYSTEM_CONCURRENCY_ARCHITECTURE_2026.md §4`.
3. Identify the violating code path (which file acquired locks in wrong order).
4. Fix: reorder to `Semester → UserLicense → TournamentParticipation`.
5. Add a regression test (mock two concurrent transactions in wrong order).

---

## 5. Measurement Timeline

```
2026-02-19  Lock logger deployed to production (commit 43cb5f4 + this sprint)
2026-02-20  Day 1 — validate_lock_metrics.py sanity check
2026-02-21  Day 2 — validate_lock_metrics.py
2026-02-22  Day 3 — validate_lock_metrics.py
2026-02-23  Day 4 — validate_lock_metrics.py
2026-02-24  Day 5 — run report_lock_performance.py --since-days 5
                    → decision on §3 thresholds
                    → if all OK: schedule next window (7 more days)
                    → if threshold breached: open optimization sprint per §4
```

---

## 6. Acceptance — "No optimization needed"

If on 2026-02-24 `report_lock_performance.py` exits 0 (all thresholds met), the
system is confirmed production-ready at current load.  The next action is:

1. Add `report_lock_performance.py` to weekly CI (Monday 09:00 UTC alongside
   the existing pipeline monitors).
2. Update `SYSTEM_CONCURRENCY_ARCHITECTURE_2026.md` with confirmed P50/P95
   baseline values.
3. Mark this plan `CLOSED — NO ACTION REQUIRED`.

---

## 7. Acceptance — "Optimization required"

If thresholds are breached, open a new sprint branch for the relevant item in §4.
Follow the exact implementation plan there.  Do not mix optimization work with
other features.

---

*End of Performance Audit Plan*
*Status update due: 2026-02-24 (after 5-day measurement window)*
