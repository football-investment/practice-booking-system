# GROUP_AND_KNOCKOUT Tournament E2E Tests

**Purpose:** Validate GROUP_AND_KNOCKOUT hybrid format

**Status:** ✅ Active

---

## Overview

This directory contains E2E tests for **GROUP_AND_KNOCKOUT tournaments** - hybrid format combining Group Stage (round-robin) with Knockout (elimination bracket).

**Key Characteristics:**
- **Format:** Group Stage + Knockout hybrid
- **Workflow:** 2-phase (Group finalization → Knockout)
- **Edge Cases:** Odd player counts, unbalanced groups
- **Test Type:** Sandbox workflow validation

---

## Files

### `test_group_knockout_7_players.py`

**What it tests:**
- 7 players (ODD count - edge case)
- Unbalanced groups: [3, 4] players
- Group Stage: 9 matches
- Knockout Stage: 2 semis + 1 final
- Final match auto-population after semifinals

**Test Types:**
1. **Smoke Test** (`test_group_knockout_7_players_smoke`) - Fast CI regression
2. **Golden Path UI** (`test_group_knockout_7_players_golden_path_ui`) - Full UI workflow

**Status:**
- ✅ Smoke test: Active (API-based + direct URL)
- ✅ Golden Path UI: Active (full sandbox workflow)

---

### `test_group_stage_only.py`

**What it tests:**
- GROUP_STAGE_ONLY format (no knockout phase)
- Group stage finalization without advancing to knockout
- Partial workflow validation

**Status:** ✅ Active

---

## Running Tests

### Run All GROUP_KNOCKOUT Tests

```bash
# By marker
pytest -m group_knockout -v

# By directory
pytest tests/e2e_frontend/group_knockout/ -v
```

### Run Specific Test

```bash
# Smoke test (fast)
pytest tests/e2e_frontend/group_knockout/test_group_knockout_7_players.py::test_group_knockout_7_players_smoke -v

# Golden Path UI (slow)
pytest tests/e2e_frontend/group_knockout/test_group_knockout_7_players.py::test_group_knockout_7_players_golden_path_ui -v

# Group stage only
pytest tests/e2e_frontend/group_knockout/test_group_stage_only.py -v
```

### Run Smoke Tests Only (CI)

```bash
pytest -m smoke -v
```

---

## Test Workflow

### 7 Players Edge Case

**Scenario:**
- 7 players (ODD count)
- Group distribution: [3, 4] (unbalanced)
- Top 2 per group advance (4 total qualifiers)

**Phases:**

#### **Phase 1: Group Stage (9 matches)**
- Group A: 3 players → 3 matches (3×2/2)
- Group B: 4 players → 6 matches (4×3/2)
- Total: 9 matches

#### **Phase 2: Finalize Group Stage**
- Determine top 2 from each group
- 4 qualifiers advance to knockout
- Backend populates knockout bracket

#### **Phase 3: Knockout Stage (3 matches)**
- Semi-final 1: Group A #1 vs Group B #2
- Semi-final 2: Group B #1 vs Group A #2
- Final: Semi-final winners
- Bronze match: Semi-final losers (optional)

**Success Criteria:**
- ✅ All 7 players enrolled (100%)
- ✅ Groups unbalanced [3, 4] (edge case handled)
- ✅ All 9 group matches submittable
- ✅ Group stage finalization successful
- ✅ 2 semifinals generated
- ✅ **Final match appears in UI** after semifinals (critical)
- ✅ Final match submittable

---

## Smoke Test vs Golden Path UI

### Smoke Test (`test_group_knockout_7_players_smoke`)

**Purpose:** Fast CI regression test

**Approach:**
- API-based tournament creation
- API-based result submission
- Direct URL navigation
- Fast validation (~30-60 seconds)

**What it does:**
- Creates tournament via API
- Submits results via API
- Uses direct URL to Step 4
- Validates final match visibility

**What it does NOT:**
- Does NOT test button navigation
- Does NOT test complete UI workflow
- Does NOT validate end-to-end user journey

**Use Case:** CI pipeline, fast regression

---

### Golden Path UI (`test_group_knockout_7_players_golden_path_ui`)

**Purpose:** Full UI workflow validation

**Approach:**
- 100% UI-driven
- Sandbox workflow
- User-like interaction
- Complete validation (~5-10 minutes)

**What it does:**
- Tests complete sandbox workflow
- Validates all button clicks
- Tests user navigation flow
- Comprehensive UI validation

**Use Case:** Pre-release validation, comprehensive testing

---

## Architecture

### Sandbox Workflow

**What is Sandbox?**
- Streamlit app for tournament testing
- Preset-based tournament creation
- Instructor workflow simulation
- Step-by-step wizard interface

**Workflow Steps:**
1. Navigate to sandbox
2. Click "New Tournament" → "Start Instructor Workflow"
3. Step 1: Select preset (Group+Knockout, 7 players)
4. Step 2: Review & Confirm → Create Tournament
5. Step 3: Attendance (skip if auto-enrolled)
6. Step 4: Enter Results
   - Submit all 9 group matches
   - Click "Finalize Group Stage"
   - Submit 2 semifinal matches
   - **Verify final match appears** (critical validation)
   - Submit 1 final match

---

## Critical Validation: Final Match Auto-Population

**Problem (Historical):**
- Final match did NOT appear in UI after semifinals
- `participant_user_ids` was NULL
- UI determinism bug

**Root Cause:**
- Backend didn't populate final match participants immediately
- Knockout forms require valid `participant_user_ids`

**Fix:**
- Backend now populates final match after semifinals complete
- UI renders forms when `participant_user_ids` is valid

**Validation:**
- Smoke test checks final match visibility
- Golden Path UI validates full workflow
- Both tests MUST pass for production

---

## Shared Helpers

**Imports from:** `tests/e2e_frontend/shared/streamlit_helpers.py`

**Uses:**
- `submit_head_to_head_result_via_ui()` - UI result submission
- `wait_for_streamlit_rerun()` - Streamlit rerun wait

**Note:** GROUP_KNOCKOUT uses sandbox-specific helpers, not shared workflow

---

## Troubleshooting

### Test Fails at Group Finalization

**Symptom:** "Finalize Group Stage" button doesn't work

**Check:**
1. All 9 group matches submitted
2. No missing results
3. API call to `/finalize-group-stage` succeeded

### Test Fails: Final Match Not Visible

**Symptom:** Final match doesn't appear after semifinals

**Check:**
1. Both semifinals submitted
2. Backend populated final match `participant_user_ids`
3. No knockout heading appears

**Debug:**
```bash
# Check screenshot
ls /tmp/debug_no_knockout_forms.png

# Check database
psql -c "SELECT id, participant_user_ids FROM sessions WHERE tournament_phase = 'KNOCKOUT'"
```

### Test Fails at Result Submission

**Symptom:** UI form doesn't submit

**Check:**
1. Form button visible
2. Input fields filled
3. Streamlit rerun completed
4. No JavaScript errors

---

## Edge Cases Tested

### Odd Player Count (7)

**Challenge:** Cannot divide evenly into groups

**Solution:** Unbalanced groups [3, 4]

**Validation:** Test ensures both groups work correctly

---

### Unbalanced Groups

**Challenge:** Different group sizes affect match counts

**Group A:** 3 players → 3 matches
**Group B:** 4 players → 6 matches

**Validation:** All matches submittable, finalization works

---

### Top 2 per Group

**Challenge:** Determine qualifiers correctly

**Validation:**
- Correct ranking within each group
- Top 2 from each group advance
- 4 total qualifiers

---

## Markers

```python
@pytest.mark.smoke          # Smoke test only
@pytest.mark.group_knockout # Both tests
@pytest.mark.golden_path    # Golden Path UI only
```

**Usage:**
```bash
pytest -m group_knockout -v        # All GROUP_KNOCKOUT tests
pytest -m smoke -v                 # Smoke test only
pytest -m "group_knockout and golden_path" -v  # Golden Path UI only
```

---

## Related Tests

### Golden Path (Production Critical)

**Location:** `tests/e2e/golden_path/test_golden_path_api_based.py`

**Difference:**
- Golden Path: 7 players GROUP_AND_KNOCKOUT (API-based creation)
- This directory: Edge case validation (Sandbox workflow)

**Both test similar scenarios but different workflows.**

---

## Related Documentation

- [TEST_SUITE_ARCHITECTURE.md](../../../TEST_SUITE_ARCHITECTURE.md) - Overall test architecture
- [NAVIGATION_GUIDE.md](../../NAVIGATION_GUIDE.md) - Test navigation
- [tests/e2e/golden_path/README.md](../../e2e/golden_path/README.md) - Production Golden Path
- [shared/streamlit_helpers.py](../shared/streamlit_helpers.py) - Shared helpers

---

## Future Work

### P1 - High Priority

1. **Additional Player Counts**
   - 8 players (balanced groups [4, 4])
   - 9 players (3 groups of 3)
   - 12 players (3 groups of 4)

2. **Knockout Format Variants**
   - Include bronze match (3rd place)
   - Different advancement rules (top 1 per group)

### P2 - Medium Priority

3. **Error Recovery Tests**
   - Test invalid group results
   - Test mid-tournament cancellation
   - Test re-finalization attempts

4. **UI Navigation Tests**
   - Test back button navigation
   - Test step skipping prevention
   - Test workflow state persistence

---

**Author:** Claude Code (Sonnet 4.5)
**Date:** 2026-02-08
**Status:** Active (Smoke + Golden Path UI)
