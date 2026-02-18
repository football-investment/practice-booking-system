# Technical Debt & Known Limitations

This document tracks technical debt, known limitations, and workarounds in the codebase.

---

## API Limitations

### Tournament Lifecycle API - Incomplete Tournament Field Support

**Status**: 🟡 Known Limitation
**Impact**: E2E tests must use direct SQL INSERT instead of production API
**Severity**: Medium
**Date Identified**: 2026-01-27

**Description**:
The Tournament Lifecycle API (`POST /api/v1/tournaments/`) does not support tournament-specific fields that are required for creating fully-configured tournament records.

**Missing Fields**:
- `format` (HEAD_TO_HEAD, INDIVIDUAL_RANKING)
- `scoring_type` (PLACEMENT, SCORE)
- `tournament_type_id` (foreign key to tournament_types table)
- `number_of_rounds` (for multi-round tournaments)

**Current Workaround**:
E2E test scripts ([test_league_api.sh](../tests/tournament_types/test_league_api.sh), [test_multi_round_api.sh](../tests/tournament_types/test_multi_round_api.sh)) use direct SQL INSERT statements with all required fields, including:
- `created_at` and `updated_at` timestamps for production-compatible data structure
- All tournament-specific configuration fields

**Impact**:
- ✅ E2E tests work correctly with SQL INSERT approach
- ✅ Data structure is production-compatible (includes timestamps)
- ⚠️ E2E tests bypass production API, reducing API test coverage
- ⚠️ Tournament creation via API is limited to basic fields only

**Recommended Fix** (Future):
Extend `TournamentCreateRequest` schema and `create_tournament()` endpoint in [lifecycle.py](../app/api/api_v1/endpoints/tournaments/lifecycle.py) to accept optional tournament-specific fields:

```python
class TournamentCreateRequest(BaseModel):
    # ... existing fields ...

    # Tournament-specific fields (optional)
    format: Optional[str] = Field(None, description="Tournament format")
    scoring_type: Optional[str] = Field(None, description="Scoring type")
    tournament_type_id: Optional[int] = Field(None, description="Tournament type ID")
    number_of_rounds: Optional[int] = Field(None, description="Number of rounds")
```

**Effort Estimate**: 2-4 hours
**Priority**: P3 (Enhancement - not blocking current functionality)

---

## Test Infrastructure

### Test Suite State Isolation Issue – Cascading Delete Tests

**Status**: 🟡 Known Limitation
**Impact**: 2 tests fail when run as part of the full suite but pass in isolation
**Severity**: Low
**Date Identified**: 2026-02-18

**Description**:
Two tests in `tests/unit/tournament/test_core.py` exhibit state pollution when run as part of the full test suite (`pytest tests/`), but pass individually or in their own module:

- `TestDeleteTournament::test_delete_tournament_cascades_to_sessions`
- `TestDeleteTournament::test_delete_tournament_cascades_to_bookings`

Confirmed pre-existing: `git stash` + `pytest tests/` on clean branch (pre-refactor) exhibits the same failures, ruling out any relation to the refactoring work done in this sprint.

**Likely Root Causes** (in order of probability):
1. **Non-rollbacking fixture** — a test earlier in the suite inserts rows without rolling back, leaving the DB in a dirty state that causes the cascade delete assertions to fail (unexpected row count or FK constraint violation)
2. **Shared DB session** — test fixtures share a `Session` object across test modules; side-effects accumulate
3. **Global in-memory cache** — a module-level dict or list (e.g. tournament registry, mock store) is mutated by earlier tests and not reset between test classes

**Current Workaround**:
Run the failing tests in isolation when their result is needed:
```bash
pytest tests/unit/tournament/test_core.py::TestDeleteTournament -v
```

**Impact**:
- ✅ Failing tests pass in isolation — logic is correct
- ✅ No production code is affected — purely a test harness problem
- ⚠️ Full-suite run shows 2 red tests, which can mask real regressions
- ⚠️ CI pipelines that use `pytest tests/` without isolation may report false failures

**Recommended Fix** (Future):
1. Audit `conftest.py` fixtures for missing `db.rollback()` / `transaction` scope
2. Add `autouse=True` session-scoped or function-scoped rollback fixture
3. If a global cache is involved, reset it in a `pytest_runtest_setup` hook

**Effort Estimate**: 2–4 hours
**Priority**: P3 (Non-blocker — investigate before next major test-suite expansion)

---

---

## Refactoring Sprint Log

### Sprint 2026-02-18 — Tournament Endpoint File-Size Refactoring

**Status**: ✅ Completed
**Branch**: `feature/performance-card-option-a`

Two large files were split to improve maintainability and reduce cognitive load per module.

#### Split 1: `generator.py` (2475 lines) → `generator.py` + `ops_scenario.py`

| File | Before | After |
|---|---|---|
| `generator.py` | 2475 lines | 885 lines (−64%) |
| `ops_scenario.py` | — | ~1615 lines (new) |

**Boundary**: Line 886 (`# OPS SCENARIO ENDPOINT` comment).
`generator.py` retains: tournament CRUD + instructor schema endpoints.
`ops_scenario.py` contains: OPS simulation infrastructure, all `_simulate_*()` helpers, `OpsScenarioRequest/Response` schemas, `run_ops_scenario()` endpoint.

**External import changes**:
- 3 test files updated: `test_real_user_integration.py`, `test_async_production_readiness.py`, `test_scale_1024_real_structure.py`
- Import path: `...generator` → `...ops_scenario` for `_simulate_tournament_results`

**Exported symbol `record_status_change`**: N/A for this split.

---

#### Split 2: `lifecycle.py` (1133 lines) → `lifecycle.py` + `lifecycle_instructor.py` + `lifecycle_updates.py`

| File | Before | After |
|---|---|---|
| `lifecycle.py` | 1133 lines | 543 lines (−52%) |
| `lifecycle_instructor.py` | — | ~269 lines (new) |
| `lifecycle_updates.py` | — | ~291 lines (new) |

**Boundaries**:
- `lifecycle.py` retains: CREATE (`POST /`), STATUS TRANSITION (`PATCH /{id}/status`), STATUS HISTORY (`GET /{id}/status-history`), `record_status_change()` helper
- `lifecycle_instructor.py`: Cycle 2 instructor assignment (`POST /{id}/assign-instructor`, `POST /{id}/instructor/accept`, `POST /{id}/instructor/decline`)
- `lifecycle_updates.py`: Admin update endpoint (`PATCH /{id}` — 15+ fields, auto-session triggers)

**External import compatibility**:
- `rewards.py` (3 occurrences) and `rewards_v2.py` (1 occurrence) import `record_status_change` from `lifecycle.py` — **unchanged**, helper stays in `lifecycle.py`
- No test files import directly from `lifecycle.py` — zero test changes required

**Route count**: 71 (unchanged across both splits)
**Unit test baseline**: 347 passed, 2 failed (pre-existing cascade delete state pollution — see entry above)

---

### Known Remaining Large Files (post-sprint audit)

Files still above 500 lines in `app/api/api_v1/endpoints/tournaments/` that may warrant future splitting:

| File | Lines | Candidate split |
|---|---|---|
| `ops_scenario.py` | ~1615 | Could extract simulation helpers to `app/services/tournament/simulation/` |
| `instructor_assignment.py` | ~1130 | Could split apply-flow vs approve-flow |
| `rewards.py` | (not audited) | Legacy — consider deprecating in favour of `rewards_v2.py` |

---

## Template for New Entries

```markdown
### [Component Name] - [Issue Title]

**Status**: 🔴 Critical / 🟡 Known Limitation / 🟢 Enhancement
**Impact**: [Brief description of impact]
**Severity**: High/Medium/Low
**Date Identified**: YYYY-MM-DD

**Description**:
[Detailed description of the technical debt or limitation]

**Current Workaround**:
[How we're currently handling this]

**Impact**:
- [Impact point 1]
- [Impact point 2]

**Recommended Fix** (Future):
[Proposed solution]

**Effort Estimate**: [Hours/Days]
**Priority**: [P0-P4]
```
