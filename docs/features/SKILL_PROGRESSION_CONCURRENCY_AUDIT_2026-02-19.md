# Skill Progression Service — Concurrency Audit (Phase A)

**Date:** 2026-02-19
**Status: PHASE A — read-only audit, no changes yet**
**Author:** Engineering / Concurrency Hardening Sprint
**Target file:** `app/services/skill_progression_service.py` (1 061 lines)
**Write-back file:** `app/services/tournament/tournament_reward_orchestrator.py` (Step 1.5)

---

## 1. Scope

This audit covers the EMA-based skill progression pipeline from tournament
finalization through to the persisted `UserLicense.football_skills` JSONB.

It is a **read-only Phase A** document.  No code is modified here.

### Files examined

| File | Role |
|---|---|
| `app/services/skill_progression_service.py` | EMA formula, full history replay, `get_skill_profile` |
| `app/services/tournament/tournament_reward_orchestrator.py:289–348` | Step 1.5 — JSONB write-back with FOR UPDATE |
| `app/services/tournament/tournament_participation_service.py:237–268` | Phase 1 flush + `compute_single_tournament_skill_delta` call |
| `app/services/football_skill_service.py:92–127` | `recalculate_skill_average` — assessment path |
| `app/models/tournament_achievement.py:61` | `achieved_at = server_default=func.now()` |

### Previous concurrency work (already closed)

| Sprint | Status |
|---|---|
| Enrollment pipeline (RACE-01..04) | ✅ Hardened Core |
| Booking pipeline (RACE-B01..B07) | ✅ Hardened Core |
| Reward/XP pipeline (RACE-R01..R07) | ✅ Hardened Core — `rw01concurr00` migration live |

The Reward/XP sprint added `FOR UPDATE` on `UserLicense` in Step 1.5 (RACE-R04).
That guard serialises concurrent tournament skill write-backs for the **same user**,
but leaves several races open that are identified below.

---

## 2. Data-flow summary

```
finalize(tournament)
  └─ distribute_rewards_for_user(db, user_id, tournament_id, ...)   [1 DB transaction]
       │
       ├─ Phase 1: record_tournament_participation(db, user_id, ...)
       │     ├─ upsert TournamentParticipation row (db.flush)
       │     ├─ compute_single_tournament_skill_delta(db, user_id, tournament_id)
       │     │     └─ replays ALL of user's TournamentParticipation rows
       │     │          ordered by achieved_at ASC  (no lock, READ COMMITTED)
       │     │          → writes skill_rating_delta to participation row
       │     └─ XP / credit atomic updates (R06/R07 guards, already closed)
       │
       └─ Step 1.5: persist skill deltas to UserLicense.football_skills
             ├─ SELECT UserLicense FOR UPDATE   ← R04 guard (already closed)
             ├─ get_skill_profile(db, user_id)
             │     └─ calculate_tournament_skill_contribution(...)
             │           ├─ get_baseline_skills(db, user_id)  [reads UserLicense.football_skills]
             │           └─ iterates ALL TournamentParticipation rows  (no lock on Participation)
             └─ deep-merge computed skills into football_skills dict → flag_modified → commit
```

**Assessment path (separate endpoint / transaction):**
```
FootballSkillService.recalculate_skill_average(user_license_id, skill_name)
  ├─ SELECT AVG(percentage) from FootballSkillAssessment
  ├─ SELECT UserLicense by id  ← NO FOR UPDATE
  ├─ football_skills[skill_name] = float_average
  └─ flag_modified → (commit on caller)
```

---

## 3. Race condition register

### RACE-S01 — `compute_single_tournament_skill_delta`: EMA history ordering with concurrent sibling flush

| Field | Value |
|---|---|
| Location | `skill_progression_service.py:552–558` + `tournament_participation_service.py:267` |
| Pattern | TOCTOU — read without snapshot isolation |
| Severity | **LOW** (affects `skill_rating_delta` only; `football_skills` write-back is correct) |
| Closure | PARTIALLY MITIGATED by R04 |

**Description:**

`compute_single_tournament_skill_delta` reads ALL `TournamentParticipation` rows for a
user ordered by `achieved_at ASC` (line 553–558, no `FOR UPDATE`):

```python
participations = (
    db.query(TournamentParticipation)
    .filter(TournamentParticipation.user_id == user_id)
    .order_by(TournamentParticipation.achieved_at.asc())
    .all()
)
```

Under PostgreSQL `READ COMMITTED`, each query sees the **committed** snapshot at the
moment of execution.  When two concurrent `distribute_rewards_for_user` calls for the
**same user** (tournaments A and B) both flush their participation rows but haven't
committed yet, neither sees the other's uncommitted flush:

```
Thread-A (tournament A):                Thread-B (tournament B):
  flush participation_A                   flush participation_B
  compute_single_tournament_skill_delta   compute_single_tournament_skill_delta
    → reads [prior_committed + A-flush]     → reads [prior_committed + B-flush]
    → delta_A computed as "A is latest"     → delta_B computed as "B is latest"
                                            (B never saw A's flush)
  acquire FOR UPDATE on UserLicense
    (A wins the lock)
  get_skill_profile → [prior + A]
  write football_skills with A's profile
  COMMIT

                                          acquire FOR UPDATE on UserLicense
                                            (B was blocking; now acquires)
                                          get_skill_profile → [prior + A(committed) + B-flush]
                                          write football_skills with A+B profile  ← CORRECT
                                          COMMIT
```

**Impact:**
- `UserLicense.football_skills` (dashboard source of truth): **CORRECT** — B's write uses
  the full committed history including A.
- `TournamentParticipation.skill_rating_delta` for B: **WRONG** — B's delta was computed
  without A's history.  B's EMA starts from the wrong baseline if B actually came after A.
  The error is bounded (~EMA step × 1 tournament) and is an **audit-only inaccuracy**.

**Additional sub-race (timestamp ordering):**

`achieved_at` uses `server_default=func.now()` (PostgreSQL `NOW()` at INSERT time).
Two participations inserted within the same transaction clock tick receive identical
`achieved_at` values.  `ORDER BY achieved_at ASC` between them is **non-deterministic**
— the replay order could differ between the two sessions.  This adds a second source
of non-determinism to `skill_rating_delta` for concurrent tournaments.

---

### RACE-S02 — Assessment ↔ tournament finalization: JSONB last-writer-wins

| Field | Value |
|---|---|
| Location | `football_skill_service.py:117–126` vs orchestrator `lines 302–334` |
| Pattern | TOCTOU — concurrent JSONB column overwrite |
| Severity | **HIGH** — silent stat regression (reputational risk) |
| Closure | **NOT CLOSED** |

**Description:**

Two independent code paths write to `UserLicense.football_skills`:

| Path | Lock | Write strategy |
|---|---|---|
| Tournament finalization (orchestrator Step 1.5) | FOR UPDATE on UserLicense | Updates all skills' `current_level`/`tournament_delta` fields (dict-merge) |
| Assessment (`recalculate_skill_average`) | **No lock** | Writes ONE key as a scalar float |

Both paths do a Python-level read → modify → write of the **entire JSONB column**.
PostgreSQL does not support atomic partial-key update for JSONB without a SQL expression
like `jsonb_set`.

Concurrent scenario:

```
Time    Assessment txn (session B)          Tournament txn (session A)
 T1     SELECT UserLicense (no lock)
 T2                                          SELECT UserLicense FOR UPDATE (A wins)
 T3                                          get_skill_profile → compute all current_levels
 T4                                          football_skills = merged_dict (all 29 skills)
 T5                                          COMMIT + release lock
 T6     football_skills["passing"] = 75.3
        (B's copy is the T1 snapshot —
         stale for all keys except "passing")
 T7     COMMIT  ← OVERWRITES A's 28-skill update with a 29-key stale dict
                  (only "passing" gets the assessment value; all others revert to T1 state)
```

The window is between T1 (B's read) and T7 (B's commit).  B loads the pre-A snapshot at
T1, so it will write all 29 keys from T1 — including undoing every `current_level` that
A just updated for the other 28 skills.

**Conditions that trigger this:**
1. A tournament finalizes for user U.
2. An instructor submits a skill assessment for user U's license.
3. Assessment transaction starts BEFORE the tournament transaction commits.
4. Assessment transaction commits AFTER the tournament transaction commits.

Under this timing the entire tournament's `current_level` update is silently reverted.
The user's dashboard shows pre-finalization skill levels indefinitely.

---

### RACE-S03 — Format mismatch: float vs. dict in `football_skills`

| Field | Value |
|---|---|
| Location | `football_skill_service.py:122` + orchestrator `lines 319–322` |
| Pattern | Design invariant violation — two independent write formats |
| Severity | **MEDIUM** — silent stat omission for assessment-first users |
| Closure | **NOT CLOSED** |

**Description:**

`recalculate_skill_average` (assessment path) stores skill values as **scalars**:
```python
license.football_skills[skill_name] = average  # float, e.g. 75.3
```

The orchestrator's deep-merge loop (Step 1.5) expects **dict-format** entries:
```python
entry = updated_skills[skill_key]
if not isinstance(entry, dict):
    continue          # ← SILENTLY SKIPS float-format entries
entry["current_level"] = sdata["current_level"]
```

For any user whose `football_skills` contains float-format entries (e.g., assessment-only
users, or users whose onboarding used the V1 flat format), every tournament finalization
silently skips writing `current_level`, `tournament_delta`, etc. for those skills.

**Effect:**

The dashboard for such users displays the onboarding float value forever, regardless of
how many tournaments they complete.  No error is raised; the `logger.info` at line 335
reports `X skills updated` but excludes skipped skills from `changed`.

The root cause is that `football_skills` JSONB has two valid formats:
- V1 / assessment: `{"passing": 75.3}` (scalar)
- V2 / tournament: `{"passing": {"baseline": 70.0, "current_level": 78.2, ...}}` (dict)

These formats coexist and the write paths are not coordinated.

---

### RACE-S04 — `get_skill_profile` inside FOR UPDATE scope: N+1 query amplification

| Field | Value |
|---|---|
| Location | `skill_progression_service.py:398–523` + orchestrator `line 310` |
| Pattern | Lock hold time amplification |
| Severity | **LOW-MEDIUM** — performance / contention risk under load |
| Closure | **NOT CLOSED** |

**Description:**

Under the FOR UPDATE lock on `UserLicense`, the orchestrator calls `get_skill_profile`,
which triggers `calculate_tournament_skill_contribution`.  This function makes:

1. One query: all `TournamentParticipation` rows for the user
2. Per participation (N):
   - One query: total player count for that tournament (`db.query(TournamentParticipation).filter(...).count()`)
   - One query: `_extract_tournament_skills` → may query `TournamentSkillMapping`
   - One per-opponent query inside `_compute_opponent_factor`: per opponent a `UserLicense` query
3. One final query for `get_baseline_skills`: `UserLicense` (already locked, fast)

For a user with 20 tournament participations, each in an 8-player tournament:
- ~20 count queries
- ~20 × 7 opponent `UserLicense` queries = 140 queries
- Total ≈ 160+ DB round-trips **while holding the FOR UPDATE lock**

This lock is per `UserLicense` row (i.e., per user), so it only serializes concurrent
distributions for the **same user**.  However, if one user is in 3 tournaments that all
finalize simultaneously, threads 2 and 3 block on the FOR UPDATE for the entire duration
of thread 1's `get_skill_profile` computation (potentially hundreds of milliseconds).

Under a batch tournament finalization (N-player tournament with concurrent distribution),
this creates a **sequential bottleneck** for each user who appeared in multiple
simultaneously-finalizing tournaments.

---

### RACE-S05 — `skill_rating_delta` is not idempotent on retry

| Field | Value |
|---|---|
| Location | `tournament_participation_service.py:266–268` |
| Pattern | Stateful recomputation — retry changes stored value |
| Severity | **LOW** — audit record drift on retried distributions |
| Closure | **NOT CLOSED** |

**Description:**

If `distribute_rewards_for_user` is retried for the same (user, tournament) pair (e.g.,
after a transient failure), `record_tournament_participation` upserts the existing
participation and recomputes `skill_rating_delta`:

```python
rating_delta = compute_single_tournament_skill_delta(db, user_id, tournament_id) or None
participation.skill_rating_delta = rating_delta
```

`compute_single_tournament_skill_delta` replays the full history at the time of the retry.
If a **new** tournament for the same user committed between the original run and the retry,
the replayed history now includes that new tournament, and the delta for the target
tournament changes.

**Result:** `skill_rating_delta` stored on the participation row is overwritten with a
different value on each retry.  The `football_skills` write-back remains correct (full
replay from current committed state), but the `skill_rating_delta` audit field is
non-deterministic under retries.

---

### RACE-S06 — `_compute_opponent_factor` reads opponents' `football_skills` without lock (low impact)

| Field | Value |
|---|---|
| Location | `skill_progression_service.py:74–78` |
| Pattern | Non-serialised concurrent read |
| Severity | **VERY LOW** — bounded impact by design |
| Closure | **ACCEPTABLE AS-IS** |

**Description:**

`_compute_opponent_factor` reads each opponent's `UserLicense.football_skills` to compute
their baseline average:

```python
lic = db.query(UserLicense).filter(
    UserLicense.user_id == opp.user_id,
    ...
).first()   # no FOR UPDATE
```

A concurrent finalization could be mid-write on an opponent's `UserLicense` JSONB.
However, the function specifically reads `football_skills[key].get("baseline", ...)` —
the **baseline** field, which is written once at onboarding and never modified by
tournament processing.  JSONB column writes are atomic at the row level in PostgreSQL
(old or new, never partial), so the worst case is reading the pre-update version —
which contains the same baseline regardless.

**Verdict:** Not actionable.  The design correctly avoids circular dependency by using
baseline (not current_level) for opponent strength computation.

---

## 4. Idempotency model

| Operation | Idempotent? | Notes |
|---|---|---|
| `football_skills` write-back (Step 1.5) | ✅ Yes | Full replay from committed state; FOR UPDATE prevents double-write |
| `skill_rating_delta` computation | ❌ No | Recomputed on each call; changes if new tournaments committed since last run |
| Assessment write (`recalculate_skill_average`) | ✅ Yes | Reads all assessments and recomputes average (pure function of assessment rows) |
| `get_skill_profile` result | ✅ Deterministic | Given the same committed TournamentParticipation set, returns the same values |
| `compute_single_tournament_skill_delta` ordering | ❌ Non-deterministic | `achieved_at` ties → non-deterministic ORDER BY for concurrent participations |

---

## 5. Side-effect dependency diagram

```
Tournament A finalizes for user U
│
├─ (1) flush TournamentParticipation (in-session, not committed)
├─ (2) compute_single_tournament_skill_delta
│       ├─ reads TournamentParticipation (committed + in-session) — no lock
│       └─ writes skill_rating_delta to participation row
├─ (3) XP atomic update (closed: R07)
├─ (4) XP/credit transaction insert (closed: R06)
├─ (5) badge award (closed: R05)
├─ (6) FOR UPDATE on UserLicense  ←── serialisation point
│       ├─ get_skill_profile(db, user_id)
│       │     └─ reads ALL TournamentParticipation — no lock on Participation
│       └─ deep-merge → football_skills update  ←── potential collision with:
│
├─ RACE-S02 ──→ Assessment txn (concurrent, no lock):
│                reads football_skills at T1 (stale)
│                writes football_skills[skill] = float at T7
│                overwrites all of Step 1.5 changes ← HIGH RISK
│
└─ RACE-S03 ──→ If football_skills entries are float (assessment format):
                 Step 1.5 silently skips all such skills ← SILENT OMISSION
```

---

## 6. Proposed Phase B race resolution

Priority order (highest impact first):

### P1 — RACE-S02: Close assessment ↔ tournament JSONB collision

**Option A (recommended): FOR UPDATE in assessment path**

In `FootballSkillService.recalculate_skill_average`, acquire FOR UPDATE on `UserLicense`
before reading `football_skills`:

```python
license = self.db.query(UserLicense).filter(
    UserLicense.id == user_license_id
).with_for_update().first()
```

This serialises assessment writes with tournament finalizations for the same row.
The window that allows stale-read + overwrite is eliminated.

**Option B: SQL JSONB expression update**

Replace Python-level dict overwrite with a PostgreSQL JSONB merge:
```sql
UPDATE user_licenses
SET football_skills = football_skills || jsonb_build_object(:key, :value::float)
WHERE id = :id
```

This is atomic at the DB level and requires no application-level lock.
Downside: more complex ORM integration, does not compose with multiple key updates.

**Chosen approach for Phase B:** Option A (FOR UPDATE) — consistent with existing pattern.

---

### P2 — RACE-S03: Standardise `football_skills` write format

Add a format-normalisation step in the orchestrator before the deep-merge loop:

```python
for sk, val in updated_skills.items():
    if not isinstance(val, dict):
        # Upgrade float-format entry to dict-format
        updated_skills[sk] = {
            "baseline": float(val),
            "current_level": float(val),
            "tournament_delta": 0.0,
            "total_delta": 0.0,
            "tournament_count": 0,
        }
```

This one-time promotion happens inside the FOR UPDATE lock, so it is race-safe.
Subsequent iterations will find dict-format entries and update them normally.

Also add a matching guard in `recalculate_skill_average`:
```python
if isinstance(license.football_skills.get(skill_name), dict):
    license.football_skills[skill_name]["baseline"] = average
else:
    license.football_skills[skill_name] = average  # legacy path (unchanged)
```

---

### P3 — RACE-S01: Tie-break `achieved_at` ordering for concurrent participations

For the `skill_rating_delta` accuracy issue under concurrent inserts:

Add `id` as a secondary sort key in `compute_single_tournament_skill_delta` and all
other history-replay queries:

```python
.order_by(
    TournamentParticipation.achieved_at.asc(),
    TournamentParticipation.id.asc()       # tiebreaker: insertion order
)
```

Since `id` is a SERIAL/BIGSERIAL, it is always monotonically increasing within a single
PostgreSQL instance.  Two participations inserted in the same clock tick are still ordered
deterministically by insertion order.

This does not close the "sibling tournament's flush invisible" race, but it eliminates
the non-deterministic ordering when both are committed.

---

### P4 — RACE-S05: Idempotency for `skill_rating_delta`

Once `skill_rating_delta` is written and non-null, do not recompute on retry:

```python
if not participation.skill_rating_delta:
    rating_delta = compute_single_tournament_skill_delta(db, user_id, tournament_id) or None
    participation.skill_rating_delta = rating_delta
```

This makes the field write-once — the first successful computation is preserved.
Trades accuracy (retry could compute a more correct delta with more history) for
determinism (audit record does not drift on retries).

**Trade-off:** A retry after a long delay (during which other tournaments committed) would
preserve the original delta rather than the more complete one.  Acceptable for an audit
field.

---

### P5 — RACE-S04: Reduce lock hold time in `get_skill_profile`

Pre-compute the skill profile BEFORE acquiring FOR UPDATE, then acquire the lock only
for the actual write:

```python
# Outside lock: compute (may be slightly stale — acceptable)
skill_profile = skill_progression_service.get_skill_profile(db, user_id)
computed = skill_profile.get("skills", {})

# Lock only for the write
active_license = db.query(UserLicense).filter(...).with_for_update().first()

if active_license and active_license.football_skills and participation_record and computed:
    updated_skills = dict(active_license.football_skills)
    for skill_key, sdata in computed.items():
        ...
    active_license.football_skills = updated_skills
    flag_modified(active_license, "football_skills")
```

**Note:** This introduces a small time gap between profile computation and lock acquisition
during which another finalization could commit.  Since the profile is a full replay from
committed state at read time, and the lock serialises the write, the worst case is that
one more committed tournament is missed in the profile — but that tournament's own
finalization will write a corrected profile anyway.

For Phase B this is optional; P1 and P2 provide the highest value.

---

## 7. Monitoring additions (Phase D)

Add to `scripts/validate_skill_pipeline.py` (new script):

| Check | Invariant |
|---|---|
| INV-S01 | No user has `football_skills` with any key where `current_level < baseline - 1.0` (impossible by EMA formula for placement ≤ total_players) |
| INV-S02 | No user has `football_skills` entries that are bare floats in > 10% of their skills (format mismatch indicator) |
| INV-S03 | `skill_rating_delta` on TournamentParticipation: null rate ≤ 20% of records with non-null placement (high null rate suggests compute_single failure) |
| INV-S04 | `football_skills.current_level` for any skill is within [40.0, 99.0] for all users with active licenses |

---

## 8. Phase B/C/D sprint plan

| Phase | Deliverable | Priority |
|---|---|---|
| B (tests) | P0 RED tests for RACE-S01/S02/S03/S05 | High |
| C (application) | FOR UPDATE in assessment path (P1); format normalisation (P2); tie-break sort (P3); write-once delta (P4) | High |
| D (monitoring) | `scripts/validate_skill_pipeline.py` with INV-S01..S04 | Medium |
| D (docs) | `SKILL_PROGRESSION_PIPELINE_STABLE_2026-02-19.md` after all GREEN | Medium |

**Estimated scope:**
- 1 new migration (no DB-schema changes needed; P1–P4 are application-layer only)
- ~10 new P0 tests
- 2 files modified: `football_skill_service.py` (P1), `tournament_reward_orchestrator.py` (P2/P5)
- 3 files modified for P3/P4: `skill_progression_service.py`, `tournament_participation_service.py`

---

## 9. Files in Hardened Core freeze (Reward/XP — do not change without new audit)

Per `REWARD_XP_PIPELINE_STABLE_2026-02-19.md`:

- `app/services/tournament/results/finalization/tournament_finalizer.py`
- `app/services/tournament/tournament_reward_orchestrator.py` ← **also touched in P2/P5**
- `app/services/tournament/tournament_badge_service.py`
- `app/services/tournament/tournament_participation_service.py` ← **also touched in P3/P4**
- `app/models/tournament_achievement.py`
- `app/models/xp_transaction.py`

Phase B changes to `tournament_reward_orchestrator.py` and `tournament_participation_service.py`
must pass the full existing reward concurrency test suite (`tests/unit/reward/test_reward_concurrency_p0.py`)
before merging.

---

*End of Phase A Audit — `skill_progression_service.py`*
