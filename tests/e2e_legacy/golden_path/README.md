# Golden Path E2E Tests

**Purpose:** Production-critical Golden Path validation

**Status:** ✅ Active, Production Critical

---

## Overview

This directory contains the **Golden Path E2E test** - the most critical test in the entire test suite. This test validates the complete tournament lifecycle from creation to rewards distribution and serves as a **deployment blocker**.

**If this test fails, DO NOT deploy to production.**

---

## Files

### `test_golden_path_api_based.py`

**Format:** GROUP_AND_KNOCKOUT (7 players)

**What it tests:**
- Complete tournament lifecycle (10 phases)
- API-based tournament creation
- UI-based result submission
- Group Stage + Knockout hybrid workflow
- Session state management (Phase 8 fix validation)
- Query parameter restoration
- Rewards distribution

**Test Scenario:**
- 7 players (edge case: unbalanced groups)
- 9 Group Stage matches
- 3 Knockout matches (2 semis + 1 final)
- Complete tournament and distribute rewards

**Validation Status:**
- ✅ **13/13 PASSED** (3 initial + 10 extended validation)
- ✅ Phase 8 navigation fix validated
- ✅ Production ready

---

## Running Tests

### Run Golden Path Test

```bash
# By path
pytest tests/e2e/golden_path/test_golden_path_api_based.py -v

# By marker
pytest -m golden_path -v

# By directory
pytest tests/e2e/golden_path/ -v
```

### Run with Full Output

```bash
pytest tests/e2e/golden_path/test_golden_path_api_based.py -v -s
```

### Run Headless (CI)

```bash
pytest tests/e2e/golden_path/ -v --headed=false
```

---

## Test Phases

The Golden Path test validates **10 phases**:

1. **Phase 0:** Create Tournament via API
2. **Phase 1:** Enroll Participants via API (7 players)
3. **Phase 2:** Generate Sessions via API
4. **Phase 3:** Navigate to Step 4 (Enter Results) in UI
5. **Phase 4:** Submit ALL Group Stage Match Results (9 matches)
6. **Phase 5:** Finalize Group Stage
7. **Phase 6:** Submit Knockout Match Results (3 matches)
8. **Phase 7:** Navigate to Leaderboard (Step 5)
9. **Phase 7.5:** Navigate to Complete Tournament Page (Step 6)
10. **Phase 8:** Complete Tournament ← **CRITICAL FIX**
11. **Phase 9:** Verify Rewards Page Loaded (Step 7)
12. **Phase 10:** Verify Rewards Distributed

---

## Phase 8 Fix (Production Critical)

**Problem:** Query parameter restoration unconditionally overwrote `st.session_state.workflow_step`

**Fix:** Added guard to only restore if session state not already set

**File:** `streamlit_sandbox_v3_admin_aligned.py:1490`

**Commit:** `584c215`

**Validation:** 13/13 PASSED

**Details:** See [PHASE8_FIX_SUMMARY.md](../../../PHASE8_FIX_SUMMARY.md)

---

## Success Criteria

All phases must complete successfully:
- ✅ Tournament created
- ✅ 7 participants enrolled
- ✅ Sessions generated
- ✅ All 12 match results submitted (9 group + 3 knockout)
- ✅ Group stage finalized
- ✅ Knockout bracket populated
- ✅ Tournament completed
- ✅ **Navigation from Step 6 → Step 7 works** (Phase 8 fix)
- ✅ Rewards distributed
- ✅ Final state verified

---

## CI/CD Integration

### Pre-Deployment Check

**REQUIRED:** This test MUST pass before deploying to production.

```bash
# CI pipeline command
pytest tests/e2e/golden_path/ -v --maxfail=1

# If this fails, STOP deployment
```

### Smoke Test

Golden Path is also marked with `@pytest.mark.smoke` for fast regression:

```bash
pytest -m smoke -v
```

---

## Troubleshooting

### Test Fails at Phase 8

**Symptom:** Navigation from Step 6 → Step 7 doesn't work

**Check:**
1. Query param restore guard in `streamlit_sandbox_v3_admin_aligned.py:1490`
2. Session state not being overwritten
3. Logs show `workflow_step ON ENTRY: 7` (correct)

**Fix:** Ensure commit `584c215` is present

### Test Fails at Phase 4/6 (Result Submission)

**Symptom:** Match result forms not submitting

**Check:**
1. Form buttons visible
2. Network requests succeeding
3. Streamlit rerun completing

### Test Fails at Any Phase

**Debug:**
```bash
# Run with full output
pytest tests/e2e/golden_path/ -v -s

# Check screenshots (if enabled)
ls /tmp/*.png

# Check Playwright traces
ls /tmp/*_trace.zip
```

---

## Maintenance

### Updating Test

**Before modifying:**
1. Understand current test flow
2. Read [GOLDEN_PATH_STRUCTURE.md](../../../GOLDEN_PATH_STRUCTURE.md)
3. Ensure changes don't break Phase 8 navigation

**After modifying:**
1. Run 3x validation: `pytest tests/e2e/golden_path/ -v --count=3`
2. Run 10x extended validation for critical changes
3. Update documentation if flow changes

### Adding New Phases

If adding new workflow steps:
1. Insert phase in correct order
2. Update success criteria
3. Update [GOLDEN_PATH_STRUCTURE.md](../../../GOLDEN_PATH_STRUCTURE.md)
4. Run extended validation (10x)

---

## Related Documentation

- [GOLDEN_PATH_STRUCTURE.md](../../../GOLDEN_PATH_STRUCTURE.md) - Detailed phase breakdown
- [PHASE8_FIX_SUMMARY.md](../../../PHASE8_FIX_SUMMARY.md) - Phase 8 fix details
- [PHASE8_VALIDATION_REPORT.md](../../../PHASE8_VALIDATION_REPORT.md) - Validation results
- [TEST_SUITE_ARCHITECTURE.md](../../../TEST_SUITE_ARCHITECTURE.md) - Overall test architecture

---

## Markers

```python
@pytest.mark.e2e
@pytest.mark.golden_path
```

**Usage:**
```bash
pytest -m golden_path -v        # Golden Path only
pytest -m "e2e and golden_path" -v
```

---

## Contact

**Owner:** Development Team
**Critical Status:** Production Blocker
**Last Validated:** 2026-02-08 (13/13 PASSED)

---

**Author:** Claude Code (Sonnet 4.5)
**Date:** 2026-02-08
**Status:** Active, Production Critical
