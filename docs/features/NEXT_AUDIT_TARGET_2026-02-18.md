# Next Audit Target — 2026-02-18

## Decision: Tournament State Machine + Enrollment Pipeline

**Target modules:**
- `app/services/tournament/status_validator.py` (189 lines) — full state machine
- `app/api/api_v1/endpoints/tournaments/lifecycle.py` (543 lines) — HTTP status transitions
- `app/services/tournament/enrollment_service.py` (80 lines) — enrollment logic
- `app/api/api_v1/endpoints/tournaments/enroll.py` (479 lines) — enrollment API

**Why over scoring pipeline continuation?**
The scoring pipeline is now stable (BUG-01, BUG-02, BUG-03, DEBT-01 fixed; 74 tests).
The next highest-risk, lowest-coverage area is the **tournament lifecycle state machine**:
it controls every status transition (DRAFT → … → COMPLETED) and has **0 dedicated unit tests**
for `validate_status_transition()`.

---

## State Machine Coverage Gap

Current state: `tests/unit/tournament/test_multi_campus_round_robin.py`
covers 4 tests for the ENROLLMENT_OPEN campus precondition only. Zero coverage of:

| Transition | Precondition | Tested? |
|---|---|---|
| NULL → DRAFT | New tournament | ✗ |
| DRAFT → SEEKING_INSTRUCTOR | - | ✗ |
| SEEKING_INSTRUCTOR → PENDING_INSTRUCTOR_ACCEPTANCE | - | ✗ |
| PENDING_INSTRUCTOR_ACCEPTANCE → INSTRUCTOR_CONFIRMED | - | ✗ |
| INSTRUCTOR_CONFIRMED → ENROLLMENT_OPEN | campus_id required | ✗ |
| ENROLLMENT_OPEN → ENROLLMENT_CLOSED | - | ✗ |
| ENROLLMENT_CLOSED → IN_PROGRESS | sessions generated? | ✗ |
| IN_PROGRESS → COMPLETED | all sessions finalized? | ✗ |
| IN_PROGRESS → ENROLLMENT_CLOSED | admin rollback (unusual) | ✗ |
| COMPLETED → REWARDS_DISTRIBUTED | - | ✗ |
| ANY → CANCELLED | - | ✗ |

---

## Enrollment Pipeline Coverage Gap

`enrollment_service.py` wraps enrollment business rules but has **no dedicated unit tests**.
`test_validation.py` tests age/category rules (37 tests) but not the enrollment service layer.

Known decision points not tested:
- What happens when `enrollment_deadline` passes?
- Can a player enroll in a CANCELLED tournament?
- Double-enroll prevention
- Capacity overflow handling

---

## Suggested Audit Sequence

### Phase A — Read-only audit (1 sprint)
1. Map all state transitions + preconditions (status_validator.py)
2. Map enrollment_service.py decision branches
3. Identify bugs / edge cases not covered
4. Document in `docs/features/STATE_MACHINE_AUDIT_2026-02-XX.md`

### Phase B — P0 test hardening
1. Unit tests for every `validate_status_transition()` branch (DB-free, SimpleNamespace)
2. Unit tests for `enrollment_service.py` edge cases
3. xfail markers for any bugs found

### Phase C — Fix + P1 consolidation
1. Fix confirmed bugs
2. Remove xfail markers once bugs are fixed

---

## Why NOT enrollment pipeline continuation as primary?

**Scoring pipeline** was chosen over enrollment in this sprint because:
- Scoring has live production bugs (BUG-01/02 = wrong ranking order for users)
- Enrollment bugs would be caught earlier in the flow and are more visible to admins

Now that scoring is stable, enrollment pipeline is the next highest-risk area.
State machine is preferred over enrollment service specifically because:
- Incorrect state transition = tournament stuck (no recovery path)
- The `IN_PROGRESS → ENROLLMENT_CLOSED` rollback edge is non-obvious and untested
- Campus precondition on ENROLLMENT_OPEN is new (2026-02-17) and has only shallow coverage

---

## Not chosen this round

- XP calculation service (medium complexity, medium risk)
- Scheduler / background jobs (hard to test, lower blast radius)
- Checkin seeding (already 25+ tests from campus infrastructure sprint)
