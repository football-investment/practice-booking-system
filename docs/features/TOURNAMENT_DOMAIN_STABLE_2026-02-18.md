# Tournament Domain — Stable Core Declaration

**Date:** 2026-02-18
**Status: STABLE CORE — freeze + monitor**

---

## What "Stable Core" means

The tournament domain core has passed two full audit+hardening sprints:
1. **Scoring pipeline** (P0 + P1, commits `db03b42` → `83bf04a`)
2. **State machine** (SM audit, commit `f36df65`)

"Stable Core" means:
- All known HIGH/MEDIUM bugs are fixed or formally tracked with P2 tickets
- Every critical code path has dedicated unit tests (DB-free, fast)
- Production refactoring requires a new audit sprint — not ad-hoc changes
- Changes to stable modules need a test-first approach (RED → GREEN)

---

## Covered and stabilized modules

| Module | Tests | Status |
|---|---|---|
| `app/services/tournament/ranking/strategies/` | 51 P0 tests | ✅ STABLE |
| `app/services/tournament/ranking/ranking_service.py` | P0+P1 | ✅ STABLE |
| `app/services/tournament/results/finalization/session_finalizer.py` | P0+P1 | ✅ STABLE |
| `app/services/tournament/results/finalization/tournament_finalizer.py` | P1 | ✅ STABLE |
| `app/services/tournament/results/finalization/group_stage_finalizer.py` | P1 | ✅ STABLE |
| `app/services/tournament/status_validator.py` | 212 SM tests | ✅ STABLE |
| `app/services/tournament/session_generation/` | campus tests | ✅ STABLE |

---

## Open bugs (tracked, not blocking stable status)

| ID | Priority | Description | Fix designed? |
|---|---|---|---|
| SM-BUG-01 | P2 | Rollback guard collision (IN_PROGRESS→ENROLLMENT_CLOSED blocked when enrollments purged) | ✅ Option A designed |
| BUG-TC01 | LOW | test_core.py ordering contamination via MatchStructure backref | ✅ migration fix documented |
| BUG-04 | MEDIUM | wins_rankings always empty in legacy format | ❌ |
| BUG-05 | MEDIUM | H2H pathway bypasses RankingService | ❌ |
| BUG-06 | LOW | GROUP_KNOCKOUT: hardcoded top-2 advancement | ❌ |
| BUG-07 | LOW | measurement_unit ignored in wins_rankings | ❌ |
| BUG-08 | LOW | GroupStageFinalizer: undefined tiebreaker | ❌ |
| BUG-09 | LOW | check_all_sessions_finalized: confusing semester_id alias | ❌ |
| DEBT-02 | INFO | RankingAggregator class still in codebase | ❌ |

---

## Total test coverage (tournament domain)

| Suite | Tests | Runtime |
|---|---|---|
| Scoring pipeline P0 | 51 | ~0.3s |
| Scoring pipeline P1 | 23 | ~0.3s |
| State machine | 212 | ~0.2s |
| Campus scope guard | 25 | ~0.7s |
| Check-in seeding | ~30 | ~0.5s |
| Validation | 37 | ~0.1s |
| Core CRUD | ~30 | ~0.7s |
| **Total** | **~408** | **~3s** |

---

## Next high-risk area: Enrollment Pipeline

**Decision: Enrollment concurrency + booking pipeline**

### Why enrollment concurrency?

The enrollment pipeline (`app/api/api_v1/endpoints/tournaments/enroll.py`,
479 lines + `app/services/tournament/enrollment_service.py`, 80 lines) has:

1. **No dedicated unit tests** for the service layer
2. **No concurrency protection** visible in the enrollment endpoint:
   - Two simultaneous POST `/enroll` requests for the same tournament
   - Both check `active_count < max_players` → both pass → tournament overenrolled
   - Classic TOCTOU (time-of-check to time-of-use) race condition
3. **No idempotency guard** against double-enroll for the same player+tournament
4. **Booking pipeline** (`app/api/api_v1/endpoints/tournaments/enroll.py`)
   has no cancellation rollback tests

### Risk level

| Risk | Impact |
|---|---|
| Double-enroll (same player) | Data corruption — player counted twice |
| Over-enrollment (concurrent) | Tournament capacity violated |
| Cancel without refund logic | Financial inconsistency |
| Enrollment without active tournament | Invalid state creation |

### Recommended sprint sequence

**Phase A — Read-only audit (next sprint):**
1. Map all enrollment transitions (PENDING → ACTIVE → CANCELLED → ...)
2. Identify all capacity/concurrency check points
3. Enumerate missing idempotency guards
4. Document in `docs/features/ENROLLMENT_AUDIT_2026-02-XX.md`

**Phase B — P0 test hardening:**
1. Unit tests: double-enroll prevention
2. Unit tests: capacity limit enforcement
3. Unit tests: enrollment in wrong tournament status
4. Concurrency test (two threads, shared mock DB)

**Phase C — Fix + P1:**
1. Add DB-level unique constraint on (user_id, tournament_id, is_active=True)
2. Add `SELECT FOR UPDATE` or optimistic locking on capacity check
3. Add idempotency guard at service layer

---

## Freeze notice for stable modules

The following modules are FROZEN until the next dedicated audit sprint:

```
app/services/tournament/ranking/strategies/    ← scoring pipeline
app/services/tournament/results/finalization/  ← scoring pipeline
app/services/tournament/status_validator.py    ← state machine
```

**Rule:** Any PR touching these files must include a failing test first,
then the fix. No refactoring without a corresponding test proving the
current behavior is preserved.
