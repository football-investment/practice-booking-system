# E2E Test Strategy: Smoke Test vs Golden Path UI Test

**Created:** 2026-02-05
**File:** `tests/e2e_frontend/test_group_knockout_7_players.py`

---

## 📋 Overview

This document explains the difference between two E2E test approaches for Group+Knockout tournaments:

1. **CI Smoke Test** - Fast deterministic regression test
2. **Golden Path UI Test** - Full user journey validation

---

## 🔥 CI Smoke Test (Fast Regression)

### Test Function
```python
@pytest.mark.smoke
@pytest.mark.group_knockout
def test_group_knockout_7_players_smoke(page: Page)
```

### Purpose
Fast deterministic test for CI pipeline - validates final match auto-population logic works correctly.

### Test Method
- ✅ Uses **API shortcuts** for tournament creation
- ✅ Uses **API shortcuts** for result submission
- ✅ Uses **direct URL navigation** to Step 4
- ✅ Validates final match visibility in UI

### What It Tests
- ✅ Backend auto-population logic (Final match generation)
- ✅ Phase-aware UI rendering
- ✅ Final match visibility after semifinals

### What It Does NOT Test
- ❌ User button navigation flow
- ❌ Complete UI workflow
- ❌ End-to-end user journey
- ❌ UI state transitions between steps

### Execution Time
~15 seconds (fast for CI)

### When to Use
- ✅ CI pipeline regression testing
- ✅ Quick validation after backend changes
- ✅ Smoke test before deploying to production
- ✅ Fast feedback loop during development

### Example Run
```bash
# Fast smoke test
pytest tests/e2e_frontend/test_group_knockout_7_players.py::test_group_knockout_7_players_smoke -v
```

---

## 🏆 Golden Path UI Test (Complete User Journey)

### Test Function
```python
@pytest.mark.e2e
@pytest.mark.group_knockout
@pytest.mark.golden_path
def test_group_knockout_7_players_golden_path_ui(page: Page)
```

### Purpose
Validates complete end-to-end user workflow through UI button navigation - ensures real users can complete tournament workflow successfully.

### Test Method
- ✅ 100% **UI-driven** (button clicks only)
- ❌ NO API shortcuts
- ❌ NO direct URL navigation
- ❌ NO deep links

### Complete User Journey (16 Steps)

1. **Navigate to Sandbox home screen**
2. **Click "Start Workflow" button**
3. **Verify on Step 1 (Configuration)**
4. **Select preset:** "Group+Knockout (7 players)" via selectbox
5. **Click "Create Tournament" button**
6. **Navigate Step 1 → Step 2:** Click "Continue to Session Management"
7. **Navigate Step 2 → Step 3:** Click "Continue to Attendance"
8. **Navigate Step 3 → Step 4:** Click "Continue to Enter Results"
9. **Submit Group Stage results:** 9 matches via UI forms
10. **Click "Finalize Group Stage" button** (triggers knockout auto-population)
11. **Verify phase auto-transition** to Knockout Stage
12. **Submit Semifinal results:** 2 matches via UI forms
13. **Verify Final match appears in UI** (CRITICAL VALIDATION)
14. **Submit Final result** via UI form
15. **Navigate to Step 5:** Click "Continue to Completion"
16. **Click "Complete Tournament" button**
17. **Navigate to Step 6:** Click "Continue to Rewards"
18. **Click "Distribute Rewards" button**
19. **Verify reward distribution success message**

### What It Tests
- ✅ Real user workflow through button navigation
- ✅ UI state transitions between all workflow steps
- ✅ Phase-aware UI (Group → Knockout)
- ✅ Tournament creation form validation
- ✅ Result submission forms for HEAD_TO_HEAD format
- ✅ Group Stage finalization button behavior
- ✅ Final match auto-population and visibility
- ✅ Complete tournament lifecycle (create → results → complete → rewards)
- ✅ All "Continue" button navigation
- ✅ Success message visibility
- ✅ Form interactions (selectboxes, number inputs, buttons)

### What It Does NOT Do
- ❌ Does NOT use API shortcuts for setup
- ❌ Does NOT use direct URL navigation
- ❌ Does NOT skip workflow steps
- ❌ Does NOT bypass UI validation

### Execution Time
~2-3 minutes (comprehensive validation)

### When to Use
- ✅ **Pre-release validation** (manual QA replacement)
- ✅ **Production readiness** verification
- ✅ **User acceptance testing** (UAT)
- ✅ **Critical feature releases**
- ✅ **Nightly test runs** (not every commit)
- ✅ **Before major deployments**

### Example Run
```bash
# Full UI-driven E2E test
pytest tests/e2e_frontend/test_group_knockout_7_players.py::test_group_knockout_7_players_golden_path_ui -v

# Run in headed mode to watch the test
HEADED=1 BROWSER=firefox pytest tests/e2e_frontend/test_group_knockout_7_players.py::test_group_knockout_7_players_golden_path_ui -v
```

---

## 🔀 When to Use Which Test?

### Use Smoke Test When:
- ✅ Running in CI pipeline (every commit)
- ✅ Need fast feedback (< 20 seconds)
- ✅ Testing specific backend logic (knockout auto-population)
- ✅ Validating bug fixes in isolation
- ✅ Running 100+ tests in parallel

### Use Golden Path Test When:
- ✅ Preparing for production release
- ✅ Validating complete user workflow
- ✅ Manual QA replacement
- ✅ Testing UI state management
- ✅ Verifying button navigation works end-to-end
- ✅ Running nightly comprehensive test suite
- ✅ Before major feature releases

---

## 📊 Comparison Table

| Aspect | Smoke Test | Golden Path UI Test |
|--------|-----------|-------------------|
| **Purpose** | Fast regression | Complete validation |
| **Method** | API + URL | 100% UI buttons |
| **Duration** | ~15 seconds | ~2-3 minutes |
| **CI Frequency** | Every commit | Nightly / Pre-release |
| **API Usage** | ✅ Yes | ❌ No |
| **Deep Links** | ✅ Yes | ❌ No |
| **Button Navigation** | ❌ No | ✅ Yes |
| **Complete Workflow** | ❌ No | ✅ Yes |
| **User Journey** | ❌ No | ✅ Yes |
| **Form Validation** | ❌ No | ✅ Yes |
| **State Transitions** | ❌ No | ✅ Yes |

---

## 🎯 Test Markers

### Smoke Test Markers
```python
@pytest.mark.smoke          # CI smoke test
@pytest.mark.group_knockout # Feature flag
```

**Run smoke tests only:**
```bash
pytest -m smoke
```

### Golden Path Test Markers
```python
@pytest.mark.e2e            # Full E2E test
@pytest.mark.group_knockout # Feature flag
@pytest.mark.golden_path    # Golden path user journey
```

**Run golden path tests only:**
```bash
pytest -m golden_path
```

**Run all E2E tests (excluding smoke):**
```bash
pytest -m "e2e and not smoke"
```

---

## 🚀 CI/CD Pipeline Integration

### Recommended Pipeline Stages

#### Stage 1: Fast Feedback (Every Commit)
```yaml
test_smoke:
  script:
    - pytest -m smoke --maxfail=1
  timeout: 5 minutes
```

#### Stage 2: Comprehensive Validation (Nightly / Pre-release)
```yaml
test_golden_path:
  script:
    - pytest -m golden_path
  timeout: 30 minutes
  when: manual  # Or scheduled nightly
```

#### Stage 3: Full E2E Suite (Before Production)
```yaml
test_full_e2e:
  script:
    - pytest -m e2e
  timeout: 60 minutes
  when: manual  # Manual trigger before deployment
```

---

## 📝 Key Takeaways

1. **Smoke Test = Speed** → Fast CI feedback
2. **Golden Path = Confidence** → Production readiness
3. **Both are necessary** → Different purposes
4. **Smoke test does NOT replace Golden Path** → Complementary approaches
5. **Golden Path is the source of truth** → Real user validation

---

## 🔧 Implementation Status

- ✅ **Smoke Test:** Implemented (`test_group_knockout_7_players_smoke`)
- ✅ **Golden Path UI Test:** Implemented (`test_group_knockout_7_players_golden_path_ui`)
- ⏳ **CI Integration:** Pending
- ⏳ **Nightly Schedule:** Pending

---

## 📚 Related Documentation

- [PLAYWRIGHT_TEST_SUITE_READY.md](PLAYWRIGHT_TEST_SUITE_READY.md) - Full test suite overview
- [UI_TESTING_CONTRACT.md](UI_TESTING_CONTRACT.md) - UI testing standards
- [E2E_FINAL_SUCCESS_6_OF_6_PASS.md](E2E_FINAL_SUCCESS_6_OF_6_PASS.md) - E2E test results

---

## ✅ Validation Checklist

### Before Running Smoke Test:
- [ ] Backend server running (localhost:8000)
- [ ] Frontend server running (localhost:8501)
- [ ] Database accessible (localhost:5432)
- [ ] Test data cleaned up

### Before Running Golden Path Test:
- [ ] Backend server running
- [ ] Frontend server running
- [ ] Database accessible
- [ ] Test data cleaned up
- [ ] Streamlit app fully loaded (no cache issues)
- [ ] Preset data exists (Group+Knockout 7 players)

---

**End of Document**
