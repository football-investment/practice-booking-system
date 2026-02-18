# Tournament State Machine Architecture

> Status: **AUDITED + TEST-COVERED** — 2026-02-18
> Test coverage: 212 unit tests, all GREEN, 0.21s runtime
> Source: `app/services/tournament/status_validator.py`

---

## 1. State Transition Diagram

```
                         ┌─────────────────────────────────────────────────────┐
                         │                 TOURNAMENT LIFECYCLE                  │
                         └─────────────────────────────────────────────────────┘

    (creation)
    NULL ──────────────────────────────────────────────────────────► DRAFT
                                                                       │
                               ┌───────────────────────────────────────┤
                               ▼                                       ▼
                           CANCELLED ◄───────────────── [any pre-COMPLETED state]
                               │
                               ▼
                           ARCHIVED (terminal)

    ─────────────────── MAIN FORWARD PATH ───────────────────────────────────

    DRAFT
      │  guard: sessions∧name∧start_date∧end_date
      ▼
    SEEKING_INSTRUCTOR
      │  guard: master_instructor_id
      ▼
    PENDING_INSTRUCTOR_ACCEPTANCE
      │  (no guard — instructor confirms externally)
      │  ◄─── can revert to SEEKING_INSTRUCTOR
      ▼
    INSTRUCTOR_CONFIRMED
      │  guard: master_instructor_id ∧ max_players ∧ campus_id
      ▼
    ENROLLMENT_OPEN
      │  guard: active_enrollments ≥ min_players
      ▼
    ENROLLMENT_CLOSED ◄─────────────────────────────────── IN_PROGRESS (rollback)
      │  guard: master_instructor_id ∧ active_enrollments ≥ min_players
      ▼
    IN_PROGRESS
      │  guard: sessions non-empty
      ▼
    COMPLETED
      │  (pass-through)
      ▼
    REWARDS_DISTRIBUTED
      │
      ▼
    ARCHIVED (terminal)
```

---

## 2. Full Transition Table

| Source | Target | Guard conditions |
|---|---|---|
| NULL | DRAFT | — (creation only) |
| DRAFT | SEEKING_INSTRUCTOR | sessions.len > 0, name, start_date, end_date set |
| DRAFT | CANCELLED | — |
| SEEKING_INSTRUCTOR | PENDING_INSTRUCTOR_ACCEPTANCE | master_instructor_id set |
| SEEKING_INSTRUCTOR | CANCELLED | — |
| PENDING_INSTRUCTOR_ACCEPTANCE | INSTRUCTOR_CONFIRMED | — |
| PENDING_INSTRUCTOR_ACCEPTANCE | SEEKING_INSTRUCTOR | — |
| PENDING_INSTRUCTOR_ACCEPTANCE | CANCELLED | — |
| INSTRUCTOR_CONFIRMED | ENROLLMENT_OPEN | master_instructor_id, max_players, campus_id all set |
| INSTRUCTOR_CONFIRMED | CANCELLED | — |
| ENROLLMENT_OPEN | ENROLLMENT_CLOSED | active_enrollments ≥ min_players (default: 2) |
| ENROLLMENT_OPEN | CANCELLED | — |
| ENROLLMENT_CLOSED | IN_PROGRESS | master_instructor_id, active_enrollments ≥ min_players |
| ENROLLMENT_CLOSED | CANCELLED | — |
| IN_PROGRESS | COMPLETED | sessions.len > 0 |
| IN_PROGRESS | CANCELLED | — |
| **IN_PROGRESS** | **ENROLLMENT_CLOSED** | **[ROLLBACK] active_enrollments ≥ min_players ← SM-BUG-01** |
| COMPLETED | REWARDS_DISTRIBUTED | — (pass-through) |
| COMPLETED | ARCHIVED | — |
| REWARDS_DISTRIBUTED | ARCHIVED | — |
| CANCELLED | ARCHIVED | — |
| ARCHIVED | — | **TERMINAL — no exits** |

**Total: 11 states, 20 allowed edges, 1 rollback edge**

---

## 3. Guard Conditions (Detail)

### G-01: sessions present
```python
if not tournament.sessions or len(tournament.sessions) == 0:
    return False, "Cannot seek instructor: No sessions defined..."
```
Used by: `DRAFT → SEEKING_INSTRUCTOR`, `IN_PROGRESS → COMPLETED`

### G-02: basic info
```python
if not tournament.name or not tournament.start_date or not tournament.end_date:
    return False, "Cannot seek instructor: Missing basic tournament information..."
```
Used by: `DRAFT → SEEKING_INSTRUCTOR`

### G-03: instructor assigned
```python
if not tournament.master_instructor_id:
    return False, "Cannot move to pending acceptance: No instructor assigned"
```
Used by: `SEEKING_INSTRUCTOR → PENDING_INSTRUCTOR_ACCEPTANCE`, `INSTRUCTOR_CONFIRMED → ENROLLMENT_OPEN`, `ENROLLMENT_CLOSED → IN_PROGRESS`

### G-04: max_players configured
```python
if not hasattr(tournament, 'max_players') or tournament.max_players is None:
    return False, "Cannot open enrollment: Max participants not configured"
```
Used by: `INSTRUCTOR_CONFIRMED → ENROLLMENT_OPEN`

### G-05: campus_id set (campus precondition)
```python
if not getattr(tournament, 'campus_id', None):
    return False, "Cannot open enrollment: No campus assigned. Set campus_id via PATCH..."
```
Used by: `INSTRUCTOR_CONFIRMED → ENROLLMENT_OPEN`
Added: 2026-02-17 (campus infrastructure sprint)

### G-06: player count ≥ min_players
```python
active_enrollments = [e for e in enrollments if e.is_active]
player_count = len(active_enrollments)
min_players_required = 2  # or from TournamentType.min_players if type set
if player_count < min_players_required:
    return False, f"Cannot close enrollment: Minimum {min_players_required}..."
```
Used by: `ENROLLMENT_OPEN → ENROLLMENT_CLOSED`, `ENROLLMENT_CLOSED → IN_PROGRESS`
**Also applies to the rollback edge — SM-BUG-01**

---

## 4. Invariants

| ID | Invariant | Verified by |
|---|---|---|
| **SM-INV-01** | NULL can only create DRAFT | SM-01 (10 tests) |
| **SM-INV-02** | Every allowed edge returns `(True, None)` when all guards satisfied | SM-02 (11 tests) |
| **SM-INV-03** | Every edge not in VALID_TRANSITIONS returns `(False, str)` | SM-03 (~101 tests) |
| **SM-INV-04** | SEEKING_INSTRUCTOR guard: sessions ∧ name ∧ dates | SM-04 (6 tests) |
| **SM-INV-05** | ENROLLMENT_OPEN guard: instructor ∧ max_players ∧ campus_id | SM-06 (7 tests) |
| **SM-INV-06** | campus_id=None/0/missing blocks ENROLLMENT_OPEN | SM-06 campus tests |
| **SM-INV-07** | Only active enrollments count toward min_players | SM-07 (7 tests) |
| **SM-INV-08** | REWARDS_DISTRIBUTED has no active guard (pass-through) | SM-10 (2 tests) |
| **SM-INV-09** | ARCHIVED is the only terminal state | SM-11 |
| **SM-INV-10** | CANCELLED is reachable from every pre-COMPLETED state | SM-15 (11 tests) |
| **SM-INV-11** | CANCELLED is NOT reachable from COMPLETED/REWARDS_DISTRIBUTED/CANCELLED/ARCHIVED | SM-15 |
| **SM-INV-12** | VALID_TRANSITIONS has exactly 20 edges | SM-16 |
| **SM-INV-13** | All target states in graph are also source states | SM-16 |

---

## 5. Known Issue

### SM-BUG-01 — Rollback guard collision (P2)

`IN_PROGRESS → ENROLLMENT_CLOSED` shares the player-count guard with
the forward `ENROLLMENT_OPEN → ENROLLMENT_CLOSED` path. If active
enrollment count drops below `min_players` while the tournament is
`IN_PROGRESS`, the admin rollback edge is blocked.

**Fix:** Bifurcate the guard on `current_status` — skip player count check
for `current_status == "IN_PROGRESS"`. See:
`docs/bugs/SM-BUG-01_rollback_guard_collision.md`

---

## 6. DB-level Audit Trail

Every status transition is recorded via `record_status_change()`:

```python
app/api/api_v1/endpoints/tournaments/lifecycle.py:95
→ INSERT INTO tournament_status_history (tournament_id, old_status, new_status, ...)
```

The `tournament_status_history` table is the canonical audit log.
`validate_status_transition()` runs BEFORE the DB write — rejections leave
no trace in the history table.

---

## 7. Files Reference

| File | Role |
|---|---|
| `app/services/tournament/status_validator.py` | Core validator (VALID_TRANSITIONS + guards) |
| `app/api/api_v1/endpoints/tournaments/lifecycle.py` | HTTP endpoints (create + status transition) |
| `app/api/api_v1/endpoints/tournaments/lifecycle_instructor.py` | Instructor-specific lifecycle |
| `app/api/api_v1/endpoints/tournaments/lifecycle_updates.py` | Lifecycle update helpers |
| `tests/unit/tournament/test_state_machine.py` | 212 unit tests covering full graph |
