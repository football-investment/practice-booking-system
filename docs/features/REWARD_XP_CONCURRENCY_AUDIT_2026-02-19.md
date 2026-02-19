# Reward/XP Pipeline — Concurrency Audit (Phase A: Read-Only Race Map)

**Date:** 2026-02-19
**Status: PHASE A COMPLETE — fixes pending (Phase B/C/D)**
**Methodology:** same as enrollment (ENROLLMENT_CONCURRENCY_AUDIT_2026-02-18.md) and booking (BOOKING_CONCURRENCY_AUDIT_2026-02-19.md) audits

---

## 1. Scope

Files audited (read-only pass):

| File | Lines | Role |
|---|---|---|
| `app/services/tournament/tournament_reward_orchestrator.py` | 630 | Main orchestration: `distribute_rewards_for_user`, `distribute_rewards_for_tournament` |
| `app/services/tournament/results/finalization/tournament_finalizer.py` | 330 | `TournamentFinalizer.finalize()` — status mutation + auto-reward trigger |
| `app/services/tournament/tournament_participation_service.py` | ~350 | `record_tournament_participation` — XP/credit/skill writes |
| `app/services/tournament/tournament_badge_service.py` | ~400 | `award_badge`, `award_placement_badges`, `award_participation_badge`, `check_and_award_milestone_badges` |
| `app/models/tournament_achievement.py` | ~176 | `TournamentParticipation`, `TournamentBadge` ORM models + constraints |

---

## 2. Current DB Constraints — Reward Tables

### `tournament_participations` table

```
PRIMARY KEY: id
UNIQUE: uq_user_semester_participation (user_id, semester_id)
FOREIGN KEY: user_id → users.id
FOREIGN KEY: semester_id → semesters.id
```

**`uq_user_semester_participation` provides partial protection against double-INSERT** — but because it is not paired with a `SELECT FOR UPDATE` idempotency guard, a concurrent duplicate INSERT raises an **uncaught `IntegrityError`** (→ HTTP 500, not a graceful 409).

### `tournament_badges` table

```
PRIMARY KEY: id
INDEX (non-unique): ix_tournament_badges_id
FOREIGN KEY: user_id → users.id
FOREIGN KEY: semester_id → semesters.id
```

**No unique constraint on `(user_id, semester_id, badge_type)`.** The `award_badge` function has an application-layer check (`existing_badge = query().first()`) but **without `FOR UPDATE`** — a TOCTOU window exists and duplicate badges can be DB-committed if two concurrent calls both see `None`.

### `xp_transactions` table

```
PRIMARY KEY: id
```

**No idempotency key.** Multiple `XPTransaction` rows with identical `(user_id, semester_id, transaction_type)` are DB-level possible.

### `credit_transactions` table (reward grants)

```
PRIMARY KEY: id
UNIQUE: ix_credit_transactions_idempotency_key (idempotency_key)  ← enrollment path only
```

The enrollment pipeline uses `idempotency_key`. **The reward distribution path (`record_tournament_participation`) creates `CreditTransaction` rows without setting `idempotency_key`** — no DB-level deduplication on reward credits.

### `users` table (balance columns)

```
xp_balance: INTEGER (no CHECK, no atomic increment guard)
credit_balance: INTEGER (CHECK: chk_credit_balance_non_negative)
```

Balance updates are done as read-modify-write: `user.xp_balance = current_balance + bonus_xp`. No `FOR UPDATE` on the `User` row before reading balances.

---

## 3. Race Condition Register

### RACE-R01: Tournament Finalization TOCTOU

**Location:** `tournament_finalizer.py:289` (`finalize()`)
**Risk:** HIGH

**Pattern:**
```
Thread A (POST /tournaments/42/finalize)      Thread B (POST /tournaments/42/finalize)
tournament = SELECT Semester WHERE id=42      tournament = SELECT Semester WHERE id=42
→ tournament_status = "IN_PROGRESS"           → tournament_status = "IN_PROGRESS"
  (Thread A flush not visible to Thread B       (Thread A flush not visible to Thread B
   — separate SQLAlchemy sessions)              — separate SQLAlchemy sessions)
update_tournament_rankings_table(42, ...)    update_tournament_rankings_table(42, ...)
tournament.tournament_status = "COMPLETED"   tournament.tournament_status = "COMPLETED"
db.flush()                                   db.flush()
distribute_rewards_for_tournament(42)        distribute_rewards_for_tournament(42)
  → iterates all rankings, distributes…         → iterates all rankings, distributes…
db.commit()                                  db.commit()
```

**Result:** Both threads fully execute the finalization pipeline — double reward distribution triggered for every participant.
**DB protection:** None (no `SELECT FOR UPDATE` on tournament row before status mutation).
**Impact:** HIGH — each participant may receive double XP, credits, and badges (constrained partially by `uq_user_semester_participation` → one thread gets IntegrityError → HTTP 500 midway).

---

### RACE-R02: Idempotency Guard TOCTOU (Reward Distribution)

**Location:** `tournament_reward_orchestrator.py:226–233` (`distribute_rewards_for_user`)
**Risk:** HIGH

**Pattern:**
```
Thread A (distribute user U, tournament T)     Thread B (distribute user U, tournament T)
existing_participation = SELECT                existing_participation = SELECT
  TournamentParticipation                        TournamentParticipation
  WHERE user_id=U, semester_id=T               WHERE user_id=U, semester_id=T
→ None (not committed yet)                     → None (not committed yet)
[pass guard]                                   [pass guard]
record_tournament_participation(U, T, …)      record_tournament_participation(U, T, …)
  ↳ INSERT TournamentParticipation               ↳ INSERT TournamentParticipation
  ↳ INSERT XPTransaction                         ↳ INSERT XPTransaction
  ↳ UPDATE users.xp_balance                      ↳ UPDATE users.xp_balance
  ↳ INSERT CreditTransaction                     ↳ INSERT CreditTransaction
  ↳ UPDATE users.credit_balance                  ↳ UPDATE users.credit_balance
db.commit()  ← succeeds                       db.commit()  ← IntegrityError
                                                 (uq_user_semester_participation)
                                                 UNCAUGHT → HTTP 500
```

**Result:** Thread A commits cleanly; Thread B raises `IntegrityError` from `uq_user_semester_participation` — not caught anywhere in the call stack → the caller receives HTTP 500.
**If Thread B's commit fails:** its XP/credit inserts are rolled back (no double financial side-effect in this specific sub-case), but the partial failure is opaque to the admin — the distribution appears partially complete.
**DB protection:** `uq_user_semester_participation` acts as a last-line backstop but produces HTTP 500 rather than a graceful 409.
**Impact:** HIGH — concurrent bulk distributions (RACE-R01 / RACE-R03) trigger this for every participant.

---

### RACE-R03: Dual Trigger — Auto-Finalize + Manual Admin

**Location:** `tournament_finalizer.py:297` (auto path) + admin reward endpoint (manual trigger)
**Risk:** HIGH

**Pattern:**
```
Thread A: finalize() → auto distribute_rewards_for_tournament(42)
Thread B: admin POST /tournaments/42/distribute-rewards → distribute_rewards_for_tournament(42)
```

Both call the same function concurrently with no inter-process lock. The idempotency guard in `distribute_rewards_for_tournament` (lines 491–500) is also a plain SELECT without FOR UPDATE — identical TOCTOU to RACE-R02.

**Result:** Same as RACE-R01 — double distribution, IntegrityError on second thread, partial 500 responses.
**DB protection:** None (no tournament-level lock, no "distribution_in_progress" flag).
**Impact:** HIGH — this is the most operationally likely race: admin triggers manual distribution moments after auto-finalize fires.

---

### RACE-R04: Skill Write-Back Race (JSONB Last-Writer-Wins)

**Location:** `tournament_reward_orchestrator.py:295–327`
**Risk:** MEDIUM

**Pattern:**
```
Thread A                                       Thread B
active_license = SELECT UserLicense            active_license = SELECT UserLicense
  WHERE user_id=U …                             WHERE user_id=U …
→ football_skills = {passing: {lvl:5}}        → football_skills = {passing: {lvl:5}}
  (Thread A's participation flush visible)       (Thread A's participation flush not visible if
                                                  separate db session at time of query)
skill_profile = get_skill_profile(db, U)      skill_profile = get_skill_profile(db, U)
updated_skills = merge(football_skills, …)    updated_skills = merge(football_skills, …)
→ {passing: {current_level: 6}}              → {passing: {current_level: 6}} or stale 5
active_license.football_skills = updated      active_license.football_skills = updated
flag_modified(active_license, "football_skills")
db.commit()                                   db.commit()
```

**Result:** Last writer wins. If Thread B's `get_skill_profile` was computed from stale data (before Thread A's TournamentParticipation was visible), Thread B writes back a stale skill level — silently reverting Thread A's update.
**DB protection:** None (JSONB field, no row-level lock, no optimistic locking / version column).
**Impact:** MEDIUM — skill deltas are corrupted silently; `tournament_delta` and `current_level` display incorrect values on performance card until next distribution.

---

### RACE-R05: Badge Double-Award TOCTOU

**Location:** `tournament_badge_service.py:185–192` (`award_badge`)
**Risk:** MEDIUM

**Pattern:**
```
Thread A (award CHAMPION badge, user U)        Thread B (award CHAMPION badge, user U)
existing_badge = SELECT TournamentBadge        existing_badge = SELECT TournamentBadge
  WHERE user_id=U, semester_id=T,               WHERE user_id=U, semester_id=T,
    badge_type=CHAMPION                            badge_type=CHAMPION
→ None                                         → None (Thread A not committed)
badge = TournamentBadge(…)                     badge = TournamentBadge(…)
db.add(badge)                                  db.add(badge)
[commit from orchestrator]                     [commit from orchestrator]
```

**Result:** Two `CHAMPION` badge rows for user U in tournament T.
**DB protection:** None — `tournament_badges.__table_args__` has only `{'extend_existing': True}`, no `UniqueConstraint` on `(user_id, semester_id, badge_type)`.
**Impact:** MEDIUM — UI displays duplicate badges; badge counting (`Veteran`, `Legend` milestone triggers) returns inflated counts; badge leaderboards corrupted.

---

### RACE-R06: XP/Credit Double Transaction (No Idempotency Key)

**Location:** `tournament_participation_service.py:270–310` (inside `record_tournament_participation`)
**Risk:** HIGH (conditional on RACE-R01/R02/R03 firing)

**Pattern:**
```
If RACE-R02 allows two threads to both enter record_tournament_participation for user U:

Thread A: INSERT XPTransaction(user=U, type=TOURNAMENT_SKILL_BONUS, amount=200)
Thread B: INSERT XPTransaction(user=U, type=TOURNAMENT_SKILL_BONUS, amount=200)
→ Two XP transaction rows, user.xp_balance inflated by 400 instead of 200

Thread A: INSERT CreditTransaction(user=U, type=TOURNAMENT_REWARD, amount=100)
Thread B: INSERT CreditTransaction(user=U, type=TOURNAMENT_REWARD, amount=100)
→ Two credit rows (no idempotency_key on reward path), credit_balance inflated by 200
```

**Note:** Thread B's `db.commit()` will be caught by `uq_user_semester_participation` (RACE-R02), rolling back the duplicate transactions — BUT only if the commit happens after Thread A has committed. If both threads flush before either commits (autoflush / explicit flush), both XP and credit rows may be visible to the other thread before the rollback, and `user.xp_balance` may be transiently wrong.
**DB protection:** `uq_user_semester_participation` provides eventual cleanup via rollback; no idempotency key on XP/credit transactions themselves.
**Impact:** HIGH (in the concurrent window) — financial side-effect visible to observers between flush and rollback.

---

### RACE-R07: XP/Credit Balance Read-Modify-Write

**Location:** `tournament_participation_service.py:276–292` (XP), `tournament_participation_service.py:303–318` (credits)
**Risk:** MEDIUM

**Pattern:**
```python
# No FOR UPDATE on User row before this sequence:
current_balance = user.xp_balance or 0       # READ
new_balance = current_balance + bonus_xp     # COMPUTE
user.xp_balance = new_balance                # WRITE
```

If two concurrent distributions for **different** tournaments both reward user U simultaneously:
```
Thread A (tournament T1): reads xp_balance=1000; new = 1200; writes 1200
Thread B (tournament T2): reads xp_balance=1000; new = 1050; writes 1050  ← LOST UPDATE
```

**Result:** Thread A's XP increment is silently lost; T1's XP transaction row says +200 but balance only reflects +50.
**DB protection:** None (no `SELECT FOR UPDATE` on `users` row, no `UPDATE users SET xp_balance = xp_balance + N`).
**Impact:** MEDIUM — XP balance drift, discrepancy between `xp_transactions` sum and `users.xp_balance`.

---

## 4. Risk Summary

| ID | Description | Location | Risk | DB Protection |
|---|---|---|---|---|
| RACE-R01 | Finalization TOCTOU — concurrent finalize() → double distribution | `tournament_finalizer.py:289` | HIGH | None |
| RACE-R02 | Idempotency guard TOCTOU — concurrent distribute_rewards_for_user | `orchestrator.py:226–233` | HIGH | `uq_user_semester_participation` (raises 500, not 409) |
| RACE-R03 | Dual trigger — auto-finalize + manual admin | `finalizer.py:297` + admin API | HIGH | None |
| RACE-R04 | Skill write-back race — JSONB last-writer-wins | `orchestrator.py:295–327` | MEDIUM | None |
| RACE-R05 | Badge double-award TOCTOU | `badge_service.py:185–192` | MEDIUM | None |
| RACE-R06 | XP/credit double transaction (no idempotency key) | `participation_service.py:270–310` | HIGH | None (idempotency_key not set on reward path) |
| RACE-R07 | XP/credit balance read-modify-write | `participation_service.py:276–292` | MEDIUM | None |

**Audit-time:** 4 HIGH + 3 MEDIUM. `uq_user_semester_participation` is the only existing DB guard; it is partial (prevents duplicate TournamentParticipation rows but produces uncaught IntegrityError).

---

## 5. Idempotency Model Analysis

### What exists

| Guard | Location | Type | Concurrent-safe? |
|---|---|---|---|
| `existing_participation` check | `orchestrator.py:226` | SELECT (no lock) | ❌ TOCTOU |
| `existing_participation` upsert in service | `participation_service.py:238` | SELECT (no lock) + upsert | ❌ TOCTOU |
| `existing_badge` check | `badge_service.py:185` | SELECT (no lock) | ❌ TOCTOU |
| `uq_user_semester_participation` | DB constraint | UNIQUE (last-line) | ✅ Backstop only — uncaught IntegrityError |
| `force_redistribution=True` bypass | `orchestrator.py:231` | Flag | N/A — admin-controlled |

### What is missing

| Gap | Impact |
|---|---|
| `SELECT FOR UPDATE` on TournamentParticipation in orchestrator | Allows RACE-R02 and RACE-R03 |
| `SELECT FOR UPDATE` on tournament row before `finalize()` status mutation | Allows RACE-R01 |
| `IntegrityError` handler on `uq_user_semester_participation` | 500 instead of graceful 409 on concurrent distribution |
| `UniqueConstraint` on `(user_id, semester_id, badge_type)` in `tournament_badges` | Allows RACE-R05 |
| Idempotency key on `XPTransaction` / `CreditTransaction` (reward path) | Allows RACE-R06 |
| `SELECT FOR UPDATE` on `User` before balance update | Allows RACE-R07 |
| Tournament-level "distribution_in_progress" flag / lock | No mutex on the bulk distribution operation |

### Idempotency comparison with enrollment pipeline

| Attribute | Enrollment | Reward/XP |
|---|---|---|
| Check-then-act guard | FOR UPDATE + atomic UPDATE | SELECT only (TOCTOU) |
| DB unique constraint | `uq_active_enrollment` | `uq_user_semester_participation` (partial cover) |
| Financial idempotency key | ✅ `idempotency_key` on credit_transactions | ❌ Missing on reward CreditTransaction |
| XP idempotency key | N/A | ❌ Missing on XPTransaction |
| Graceful IntegrityError handler | ✅ HTTP 409 | ❌ Uncaught → HTTP 500 |

---

## 6. Side-Effect Dependency Diagram

```
finalize(tournament)
│
├── update_tournament_rankings_table()      [per-user upsert loop, no lock]
│   └── TournamentRanking: upsert/insert
│
├── tournament.tournament_status = COMPLETED [no FOR UPDATE on tournament row]
├── db.flush()
│
└── distribute_rewards_for_tournament()
    │
    ├── [idempotency check — SELECT, no FOR UPDATE]
    │   └── if existing → skip; else:
    │
    └── distribute_rewards_for_user() — per-user, commits inside loop
        │
        ├── STEP 1: PARTICIPATION REWARDS
        │   ├── calculate_skill_points_for_placement()  [read-only, safe]
        │   ├── convert_skill_points_to_xp()            [read-only, safe]
        │   ├── record_tournament_participation()        ← ⚠️ TOCTOU + no idempotency key
        │   │   ├── update_skill_assessments()           [UPDATE, not locked]
        │   │   ├── [upsert TournamentParticipation]     ← last-line: uq_user_semester_participation
        │   │   ├── db.flush()
        │   │   ├── compute_single_tournament_skill_delta()
        │   │   ├── INSERT XPTransaction                 ← ⚠️ no idempotency key
        │   │   ├── UPDATE users.xp_balance              ← ⚠️ read-modify-write (RACE-R07)
        │   │   ├── INSERT CreditTransaction             ← ⚠️ no idempotency key on reward path
        │   │   └── UPDATE users.credit_balance          ← ⚠️ read-modify-write (RACE-R07)
        │   │
        │   └── STEP 1.5: skill write-back
        │       ├── SELECT UserLicense (no lock)
        │       ├── get_skill_profile()                  [reads TournamentParticipation]
        │       ├── merge football_skills JSONB           ← ⚠️ last-writer-wins (RACE-R04)
        │       └── flag_modified(active_license, "football_skills")
        │
        ├── STEP 2: BADGE REWARDS
        │   ├── award_placement_badges()
        │   │   └── award_badge()                        ← ⚠️ TOCTOU, no unique constraint (RACE-R05)
        │   ├── award_participation_badge()
        │   │   └── award_badge()                        ← ⚠️ same
        │   └── check_and_award_milestone_badges()
        │       └── award_badge()                        ← ⚠️ same
        │
        └── db.commit()   ← single commit per user
            └── uq_user_semester_participation fires on race → IntegrityError → HTTP 500 (uncaught)
```

**Atomic boundary:** Each `distribute_rewards_for_user` call commits in a single transaction. Side effects within one user's distribution are atomic together. However:
- Skill write-back failure is caught and swallowed (non-fatal) — possible TournamentParticipation committed but football_skills not updated.
- Badge award failure is NOT caught — if `award_badge` raises, the entire user distribution rolls back silently (no error to caller, no retry signal).

---

## 7. Comparison with Previous Pipelines

| Metric | Enrollment | Booking | Reward/XP |
|---|---|---|---|
| Races found | 4 | 7 | 7 |
| DB protection at audit start | None | None | `uq_user_semester_participation` (partial) |
| Idempotency mechanism | `FOR UPDATE` + atomic SQL | `FOR UPDATE` + IntegrityError → 409 | SELECT-only guard → IntegrityError → 500 |
| Financial transaction idempotency key | ✅ on enrollment credit | N/A | ❌ missing on XP + reward credit |
| Badge/attendance duplicate protection | N/A | `uq_booking_attendance` (after C-phase) | ❌ missing on TournamentBadge |
| Dual trigger risk | Low | Low | HIGH (auto-finalize + manual admin) |

---

## 8. Proposed Fix Candidates (Phase B/C input)

| Race | Application-layer fix | DB-level fix |
|---|---|---|
| RACE-R01 | `SELECT FOR UPDATE` on tournament row in `finalize()` before status mutation; re-read status after lock; if already COMPLETED → skip | — (status already unique per tournament) |
| RACE-R02 | `SELECT FOR UPDATE` on TournamentParticipation in `distribute_rewards_for_user` idempotency guard; `IntegrityError` → graceful 409 | `uq_user_semester_participation` already exists; add handler |
| RACE-R03 | Tournament-level advisory lock or "distribution_in_progress" DB flag; OR check tournament status before distributing | Flag column: `rewards_distribution_started_at TIMESTAMP` |
| RACE-R04 | `SELECT FOR UPDATE` on `UserLicense` before skill write-back | — (JSONB merge; constraint impractical) |
| RACE-R05 | `SELECT FOR UPDATE` on badge check in `award_badge`; `IntegrityError` → return existing | `UniqueConstraint('user_id', 'semester_id', 'badge_type')` on `tournament_badges` |
| RACE-R06 | Ensure only one `record_tournament_participation` per (user, tournament) reaches the INSERT path (RACE-R02 fix is prerequisite); add idempotency key on XP/credit transactions in reward path | Unique partial index on `(user_id, semester_id, transaction_type)` in xp_transactions WHERE type=TOURNAMENT_SKILL_BONUS |
| RACE-R07 | `UPDATE users SET xp_balance = xp_balance + :delta WHERE id = :user_id` (atomic increment); same for credit_balance | — (constraint impractical at DB level) |

---

## 9. Phase B/C/D Sprint Plan

### Phase B — P0 Test Hardening

Write `tests/unit/reward/test_reward_concurrency_p0.py`:
- `test_race_r01_concurrent_finalize_double_distribution` — mock two finalize() calls, assert distribute called once
- `test_race_r02_idempotency_guard_toctou` — two concurrent `distribute_rewards_for_user`, assert single TournamentParticipation insert
- `test_race_r03_dual_trigger_auto_and_manual` — mock auto + admin trigger, assert single distribution
- `test_race_r04_skill_write_back_last_writer_wins` — concurrent UserLicense JSONB writes, assert deterministic result
- `test_race_r05_badge_double_award` — concurrent `award_badge`, assert single badge row
- `test_race_r06_double_xp_transaction` — assert no duplicate XP/credit transactions
- `test_race_r07_xp_balance_lost_update` — assert atomic balance update

### Phase C — DB-Level Guards + Application Fixes

New migration `rw01_reward_concurrency_guards`:
```sql
-- C-01: Prevent duplicate badge awards
CREATE UNIQUE INDEX uq_user_tournament_badge
  ON tournament_badges (user_id, semester_id, badge_type);

-- C-02: XP transaction deduplication (reward path)
CREATE UNIQUE INDEX uq_xp_transaction_reward
  ON xp_transactions (user_id, semester_id, transaction_type)
  WHERE transaction_type = 'TOURNAMENT_SKILL_BONUS';
```

Application-layer fixes:
```python
# RACE-R01: Lock tournament row in finalize()
tournament = db.query(Semester).filter(
    Semester.id == tournament.id
).with_for_update().one()
if tournament.tournament_status in ("REWARDS_DISTRIBUTED", "COMPLETED_DISTRIBUTING"):
    return {"success": False, "message": "Already finalized"}

# RACE-R02: Lock TournamentParticipation check in distribute_rewards_for_user
existing_participation = db.query(TournamentParticipation).filter(
    TournamentParticipation.user_id == user_id,
    TournamentParticipation.semester_id == tournament_id
).with_for_update().first()
# + IntegrityError handler → graceful 409

# RACE-R04: Lock UserLicense before skill write-back
active_license = db.query(UserLicense).filter(
    UserLicense.user_id == user_id, …
).with_for_update().first()

# RACE-R05: Lock badge check in award_badge
existing_badge = db.query(TournamentBadge).filter(
    TournamentBadge.user_id == user_id,
    TournamentBadge.semester_id == tournament_id,
    TournamentBadge.badge_type == badge_type
).with_for_update().first()
# + IntegrityError handler → return existing

# RACE-R07: Atomic balance increment
db.execute(
    text("UPDATE users SET xp_balance = xp_balance + :delta WHERE id = :user_id"),
    {"delta": bonus_xp, "user_id": user_id}
)
# Same for credit_balance (only additive — non-negative CHECK still holds)
```

### Phase D — Invariant Monitoring

`scripts/validate_reward_pipeline.py`:
- INV-R01: No user with >1 TournamentParticipation per (user_id, semester_id) — should be 0 due to unique constraint
- INV-R02: No user with >1 badge of same type per (user_id, semester_id, badge_type) — catches pre-constraint duplicates
- INV-R03: No XP balance drift — `users.xp_balance` vs `SUM(xp_transactions.amount)` discrepancy
- INV-R04: No credit balance drift for reward credits — `SUM(CreditTransaction WHERE type=TOURNAMENT_REWARD)` vs participation records
- INV-R05: All tournament REWARDS_DISTRIBUTED entries have ≥1 TournamentParticipation per enrolled user
- INV-R06: `uq_user_tournament_badge` and `uq_xp_transaction_reward` constraints live in pg_indexes (post-migration)

---

## 10. Files to Touch in Phase B/C

| File | Change |
|---|---|
| `app/services/tournament/results/finalization/tournament_finalizer.py` | FOR UPDATE on tournament row (R01); COMPLETED status re-check after lock |
| `app/services/tournament/tournament_reward_orchestrator.py` | FOR UPDATE on TournamentParticipation (R02/R03); FOR UPDATE on UserLicense (R04); IntegrityError → 409 handler |
| `app/services/tournament/tournament_badge_service.py` | FOR UPDATE on badge check (R05); IntegrityError → return existing |
| `app/services/tournament/tournament_participation_service.py` | Atomic `UPDATE ... SET xp_balance = xp_balance + N` (R07); idempotency key on XP/credit transactions (R06) |
| `alembic/versions/rw01_reward_concurrency_guards.py` | C-01 `uq_user_tournament_badge`, C-02 `uq_xp_transaction_reward` |
| `tests/unit/reward/test_reward_concurrency_p0.py` | 7+ P0 tests (new file) |
| `tests/unit/reward/__init__.py` | new empty init |
| `scripts/validate_reward_pipeline.py` | INV-R01…R06 weekly monitor (new file) |

---

**Next audit target after Phase D closure:**
Skill progression service (`app/services/skill_progression_service.py`) —
EMA delta computation reads all TournamentParticipation rows per user; write-back races
with the orchestrator's skill write-back (RACE-R04 cascade).
