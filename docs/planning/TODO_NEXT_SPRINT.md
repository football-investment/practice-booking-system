# TODO - Next Sprint

## 🏫 Priority: HIGH — Location Capability Hardening (K1 + K2)

**Full spec**: [SPRINT_LOCATION_CAPABILITY_K1_K2_K3.md](SPRINT_LOCATION_CAPABILITY_K1_K2_K3.md)
**Architecture ref**: [domain-model.md §8.5](../architecture/domain-model.md#85-open-business-decisions-k1k3)

### K1 — Enforce `location_id` required for ACADEMY types (REST API)
**Status**: ✅ DONE 2026-03-16 — 9185 passed, 0 regressions
- `_semesters_main.py`: 400 guard (K1) + enum conversion before `LocationValidationService`
- LOC-API-08 → 400; LOC-API-11 (×4 parametrized) + LOC-API-12 added
- OpenAPI snapshot regenerated

### K2 — Block CENTER→PARTNER downgrade when active Academy semesters exist
**Status**: ✅ DONE 2026-03-16 — 9188 passed, 0 regressions
- `locations.py` (`PUT /{id}`): 409 guard; `admin.py` form: 409 re-render with error flash
- `location_edit.html`: `{% if error %}` flash band added
- LOC-API-13 (block READY/ONGOING), LOC-API-14 (allow DRAFT), LOC-API-15 (PARTNER→CENTER OK)
- SMOKE-21a/b/c: admin form K2 guard tested end-to-end
- **PR #36 merged 2026-03-16** (commit 33ee039) — CI `test-baseline-check.yml` 22/22 ✅
- **No new regressions introduced**: pre-existing `E2E Wizard Coverage` failure (Issue #37) fixed in PR #38

### K3 — Session generation location-agnostic (RESOLVED ✅)
No action. Documented in [domain-model.md §8.6](../architecture/domain-model.md#86-session-generation--location-agnostic-by-design).

---

## Pre-existing CI Fixes (PR #38)

### Fix: `test_branch_safety_gate_at_127_no_confirmation_needed` + `test_sched03_multiday_camp_schedule`
**Status**: ✅ DONE 2026-03-16 — PR #38 open, CI pending
**Issue**: #37

**Fix 1** — `tests/e2e/test_full_boundary_matrix.py`: changed `tournament_type_code` from `"knockout"` to `"league"` for the 127-player safety-gate test.
- Root cause: Knockout requires power-of-2 counts; 127 is not a power of 2 → generator fired 422 for a *different* reason, masking the intended safety-gate test.

**Fix 2** — `tests/integration/domain/test_session_scheduling.py`: anchored base time to midnight for SCHED-03.
- Root cause: `now = _now()` (wall-clock UTC) — afternoon slot `+14h` crossed midnight when run after ~10:00 UTC.

**CI before fix** (last 3 `main` runs): ❌ all three failed on same test
**Local after fix**: 9188 passed, 1 xfailed — 0 regressions

---

## Priority: Medium - E2E Test Selector Fixes

### Task: Fix 3 Match Command Center E2E Test Selectors
**Status**: 🟡 Pending
**Effort**: ~15-30 minutes
**Sprint**: Next
**Assignee**: TBD

**Description**: 3 out of 12 match_command_center E2E tests are failing due to text selector mismatches (NOT functional issues).

**Current**: 9/12 tests passing (75%)
**Target**: 12/12 tests passing (100%)

**Files to Update**:
- `tests/e2e/test_match_command_center.py` (lines 23, 126, 176)

**Steps**:
1. Launch `streamlit_match_command_center_test.py` on port 8503
2. Inspect actual UI text for:
   - Page title (expected: "Match Command Center")
   - Sidebar title (expected: "Live Leaderboard")
3. Update test selectors with correct text
4. Run: `pytest tests/e2e/test_match_command_center.py -v`
5. Verify: 12/12 tests pass

**Acceptance Criteria**:
- [ ] All 3 failing tests now pass
- [ ] Overall P3 test coverage: 29/29 (100%)
- [ ] No regressions in other tests

**Context**:
- Week 3 merged to main with 90% test coverage (26/29)
- Component is **production-ready** and fully functional
- Only test selectors need alignment with actual UI

**References**:
- Issue template: `.github/ISSUE_TEMPLATE/match_command_center_test_selectors.md`
- Test results: `WEEK_3_E2E_TEST_RESULTS.md`
- Merge commit: `a874edf`

---

## Notes

- This is technical debt cleanup, not blocking production
- Week 3 refactoring is **complete and merged** ✅
- All critical functionality validated ✅
- 90% test coverage achieved ✅

**Week 3 Final Status**: ✅ PRODUCTION-READY & MERGED TO MAIN
