# E2E Headless CI-Ready Test Plan

**Date**: 2026-02-10
**Objective**: Convert existing Playwright E2E tests to headless CI-ready mode
**Philosophy**: Reuse existing tests, minimize new code, maximize automation

---

## Current State Analysis

### Headless Status Audit

| Test File | Browser | Headless? | Slow Mo | CI-Ready? | Action Needed |
|-----------|---------|-----------|---------|-----------|---------------|
| `test_champion_badge_regression.py` | Chromium | ✅ Yes | No | ✅ Yes | **READY** |
| `test_00_genesis_clean_db_full_flow.py` | Chromium | ✅ Yes | No | ✅ Yes | **READY** |
| `test_01_quick_test_full_flow.py` | Firefox | ❌ No | 1200ms | ❌ No | Convert to headless |
| `test_01_create_new_tournament.py` | Firefox | ❌ No | 1200ms | ❌ No | Convert to headless |
| `test_02_draft_continue.py` | Firefox | ❌ No | 1200ms | ❌ No | Convert to headless |
| `test_03_in_progress_continue.py` | Chromium | ❌ No | 1200ms | ❌ No | Convert to headless |
| `test_04_history_tabs.py` | Chromium | ❌ No | 1200ms | ❌ No | Convert to headless |
| `test_05_multiple_selection.py` | Chromium | ❌ No | 1200ms | ❌ No | Convert to headless |
| `test_06_error_scan.py` | Chromium | ❌ No | 1200ms | ❌ No | Convert to headless |
| `test_quick_test_e2e_final.py` | Firefox | ❌ No | 1200ms | ❌ No | Convert to headless |
| `test_00_screenshot.py` | Chromium | ❌ No | 1000ms | ❌ No | Skip (debug only) |
| `test_debug_*.py` (3 files) | Various | ❌ No | Yes | ❌ No | Skip (debug only) |

**Summary**:
- ✅ **2 tests CI-ready** (champion_badge_regression, genesis)
- ❌ **8 tests need headless conversion**
- 🚫 **4 tests are debug-only** (exclude from CI)

---

## Coverage Analysis: Existing Tests

### Test 1: `test_champion_badge_regression.py` ✅ CI-READY

**Coverage**:
- Login flow
- Navigation to Player Dashboard
- CHAMPION badge display verification
- **Regression guard**: "No ranking data" detection

**Runtime**: ~20-30 seconds
**Markers**: `@pytest.mark.golden_path`, `@pytest.mark.e2e`, `@pytest.mark.smoke`
**Headless**: ✅ Yes (line 198)

**Verdict**: **KEEP AS-IS** - Already production-ready

---

### Test 2: `test_01_quick_test_full_flow.py` ⚠️ NEEDS CONVERSION

**Coverage**:
- Home screen load
- "New Tournament" button click
- Tournament configuration form fill
- Quick Test mode selection
- Tournament creation
- Results screen verification

**Runtime**: ~30-40 seconds
**Headless**: ❌ No (headed Firefox with 1200ms slow_mo)
**Issue**: Hard-coded `headless=False` on line 44

**Action Required**:
```python
# BEFORE (line 43-46)
browser = p.firefox.launch(
    headless=False,
    slow_mo=1200,
)

# AFTER (environment-aware)
import os
HEADLESS = os.environ.get("PYTEST_HEADLESS", "true").lower() == "true"
SLOW_MO = 0 if HEADLESS else 1200

browser = p.firefox.launch(
    headless=HEADLESS,
    slow_mo=SLOW_MO,
)
```

**Coverage Value**: HIGH - Full tournament creation flow

---

### Test 3-8: `test_0X_*.py` (Draft, In-Progress, History, etc.) ⚠️ NEEDS CONVERSION

All follow same pattern:
- Hard-coded `headless=False`
- `slow_mo=1200ms` for visibility
- Firefox or Chromium

**Action Required**: Same environment-aware conversion as Test 2

**Coverage Value**: MEDIUM - Specific workflows (draft continuation, history tabs, etc.)

---

### Test 9: `test_00_genesis_clean_db_full_flow.py` ✅ CI-READY

**Coverage**:
- Clean DB setup
- Migration execution
- Seed data creation
- DB integrity verification
- API badge_metadata serialization verification
- UI CHAMPION badge display

**Runtime**: ~60 seconds
**Headless**: ✅ Yes (line 557)
**Markers**: `@pytest.mark.genesis`, `@pytest.mark.critical`, `@pytest.mark.slow`

**Verdict**: **KEEP AS-IS** - Already production-ready

---

## Recommendation: Pragmatic Approach

### Phase 1: Quick Win - Make Existing Tests Headless-Ready (30 min)

Create a **shared conftest.py** with browser fixture:

```python
# tests_e2e/conftest.py
import os
import pytest
from playwright.sync_api import sync_playwright

@pytest.fixture(scope="function")
def browser_config():
    """
    Central browser configuration for all E2E tests.
    Environment variables:
    - PYTEST_HEADLESS=true (default) | false
    - PYTEST_BROWSER=chromium (default) | firefox | webkit
    - PYTEST_SLOW_MO=0 (default) | <milliseconds>
    """
    return {
        "headless": os.environ.get("PYTEST_HEADLESS", "true").lower() == "true",
        "slow_mo": int(os.environ.get("PYTEST_SLOW_MO", "0")),
        "browser_type": os.environ.get("PYTEST_BROWSER", "chromium"),
    }

@pytest.fixture(scope="function")
def browser(browser_config):
    """
    Playwright browser instance with environment-aware config.
    """
    with sync_playwright() as p:
        browser_type = getattr(p, browser_config["browser_type"])
        browser = browser_type.launch(
            headless=browser_config["headless"],
            slow_mo=browser_config["slow_mo"],
        )
        yield browser
        browser.close()
```

### Phase 2: Update Existing Tests to Use Fixture (10 min per test)

**Before**:
```python
def test_quick_test_full_flow():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, slow_mo=1200)
        page = browser.new_page()
        # ... test logic ...
        browser.close()
```

**After**:
```python
def test_quick_test_full_flow(browser):
    page = browser.new_page()
    # ... test logic ...
    # browser.close() handled by fixture
```

### Phase 3: CI Integration (5 min)

**pytest.ini** (already exists):
```ini
[pytest]
markers =
    golden_path: Production critical Golden Path tests (DO NOT SKIP)
    smoke: Fast smoke tests for CI regression checks
    e2e: End-to-end tests with Playwright
    slow: Tests >30 seconds runtime
```

**GitHub Actions** (example):
```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium

      - name: Start services
        run: |
          docker-compose up -d  # PostgreSQL
          uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          streamlit run streamlit_app/🏠_Home.py --server.port 8501 &
          sleep 10

      - name: Run smoke tests (fast CI regression)
        run: pytest -m smoke --tb=short
        env:
          PYTEST_HEADLESS: "true"
          PYTEST_BROWSER: "chromium"

      - name: Run golden path tests (build blockers)
        run: pytest -m golden_path --tb=short
        env:
          PYTEST_HEADLESS: "true"

      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: e2e-screenshots
          path: tests_e2e/screenshots/
```

---

## Proposed Test Suite for CI

### Tier 1: Smoke Tests (Fast, every commit)

```bash
# Runtime: ~2-3 minutes
pytest -m smoke --tb=short
```

**Includes**:
- `test_champion_badge_regression.py` (CHAMPION badge guard)
- `test_06_error_scan.py` (after conversion - page error detection)

**Rationale**: Fast regression detection, catches UI crashes

---

### Tier 2: Golden Path (Build blocker, every PR)

```bash
# Runtime: ~5-8 minutes
pytest -m golden_path --tb=short
```

**Includes**:
- `test_champion_badge_regression.py`
- `test_01_quick_test_full_flow.py` (after conversion - full tournament flow)

**Rationale**: Critical user flows must pass before merge

---

### Tier 3: Full E2E Suite (Nightly/pre-release)

```bash
# Runtime: ~15-20 minutes
pytest -m e2e --tb=short
```

**Includes**: All converted E2E tests (8-10 tests)

**Rationale**: Comprehensive coverage before deployment

---

### Tier 4: Clean DB Genesis (Weekly/major releases)

```bash
# Runtime: ~1 minute
pytest -m genesis --tb=short
```

**Includes**: `test_00_genesis_clean_db_full_flow.py`

**Rationale**: Verify clean DB → working system (migration testing)

---

## Gap Analysis: Do We Need New Tests?

### ✅ COVERED by Existing Tests

| Flow | Test Coverage |
|------|---------------|
| User login | `test_champion_badge_regression.py` |
| Tournament creation | `test_01_quick_test_full_flow.py` |
| Tournament execution | `test_01_quick_test_full_flow.py` |
| Badge display | `test_champion_badge_regression.py` |
| Draft continuation | `test_02_draft_continue.py` |
| In-progress continuation | `test_03_in_progress_continue.py` |
| History navigation | `test_04_history_tabs.py` |
| Error detection | `test_06_error_scan.py` |
| Clean DB setup | `test_00_genesis_clean_db_full_flow.py` |

### ❌ NOT COVERED (Real Gaps)

| Flow | Coverage Gap | Priority | Action |
|------|--------------|----------|--------|
| User onboarding | No test exists | LOW | Defer to future sprint |
| Tournament ranking calculation | No DB verification | MEDIUM | Add DB query to `test_01_quick_test_full_flow.py` |
| XP/Credits award | No verification | LOW | Defer to future sprint |
| API contract testing | No direct API calls | MEDIUM | Already covered by `test_00_genesis_clean_db_full_flow.py` |

**Recommendation**: **NO NEW TESTS NEEDED** for immediate CI-readiness.

**Enhancements** (optional):
1. Add DB verification to `test_01_quick_test_full_flow.py` (check `tournament_rankings` table)
2. Add API response assertion to `test_champion_badge_regression.py` (optional)

---

## Implementation Plan

### Step 1: Create `conftest.py` (5 min)

```bash
touch tests_e2e/conftest.py
# Paste browser_config and browser fixtures from Phase 1 above
```

### Step 2: Convert Tests to Use Fixture (60 min total)

**Priority Order**:
1. ✅ `test_champion_badge_regression.py` - Already headless, verify fixture works
2. ✅ `test_01_quick_test_full_flow.py` - HIGH value, tournament creation flow
3. `test_06_error_scan.py` - Fast smoke test
4. `test_02_draft_continue.py` - Draft workflow
5. `test_03_in_progress_continue.py` - In-progress workflow
6. `test_04_history_tabs.py` - Navigation test
7. `test_05_multiple_selection.py` - Selection test

### Step 3: Test Locally (10 min)

```bash
# Headless mode (CI simulation)
PYTEST_HEADLESS=true pytest tests_e2e/test_champion_badge_regression.py -v -s

# Headed mode (debugging)
PYTEST_HEADLESS=false PYTEST_SLOW_MO=1000 pytest tests_e2e/test_01_quick_test_full_flow.py -v -s

# Full smoke suite
pytest -m smoke --tb=short
```

### Step 4: Update pytest.ini Markers (2 min)

Ensure markers are correctly assigned:
```python
# test_champion_badge_regression.py
@pytest.mark.golden_path
@pytest.mark.e2e
@pytest.mark.smoke
def test_champion_badge_no_ranking_data_regression():
    ...

# test_01_quick_test_full_flow.py
@pytest.mark.golden_path
@pytest.mark.e2e
def test_quick_test_full_flow(browser):
    ...
```

### Step 5: CI Integration (Optional, 15 min)

- Create `.github/workflows/e2e-tests.yml`
- Configure service startup (PostgreSQL, FastAPI, Streamlit)
- Run smoke tests on every push
- Run golden_path tests on PR merge

---

## Estimated Effort

| Task | Time | Who |
|------|------|-----|
| Create conftest.py | 5 min | Dev |
| Convert test_01_quick_test_full_flow.py | 10 min | Dev |
| Convert test_06_error_scan.py | 10 min | Dev |
| Convert remaining 5 tests | 50 min | Dev |
| Local testing & validation | 15 min | Dev |
| CI integration (optional) | 15 min | DevOps |
| **TOTAL** | **1h 45min** | |

---

## Success Metrics

After implementation:

1. ✅ All 8 core E2E tests run in headless mode
2. ✅ `pytest -m smoke` runs in <3 minutes
3. ✅ `pytest -m golden_path` runs in <8 minutes
4. ✅ Tests can run locally with `PYTEST_HEADLESS=false` for debugging
5. ✅ CI pipeline runs E2E tests on every commit
6. ✅ No new test architecture needed - existing tests reused

---

## Key Decisions

### Decision 1: Reuse Existing Tests ✅

**Rationale**: Existing tests already cover critical flows. Converting them to headless is faster and less risky than writing new tests.

### Decision 2: Environment-Aware Configuration ✅

**Rationale**: Single codebase for both local debugging (headed) and CI (headless). No code duplication.

### Decision 3: Defer New Tests ✅

**Rationale**: Coverage gaps (user onboarding, XP/credits) are LOW priority. Focus on making existing tests CI-ready first.

### Decision 4: Keep Genesis Test Separate ✅

**Rationale**: Genesis test is slow (~60s) and destructive (drops DB). Run separately from smoke/golden_path suites.

---

## Next Steps

1. **Create conftest.py** with browser fixture
2. **Convert test_01_quick_test_full_flow.py** to use fixture (proof of concept)
3. **Test locally** with headless=true
4. **Convert remaining 7 tests** if POC succeeds
5. **Run full suite** with `pytest -m e2e --tb=short`
6. **Document results** and share with team

---

## Questions & Answers

**Q**: Why not just change `headless=False` to `headless=True` in each test?

**A**: Hard-coding loses flexibility. With environment variables, devs can debug headed mode locally while CI runs headless automatically.

---

**Q**: Do we need the Genesis test if we have other E2E tests?

**A**: Yes. Genesis test is the **only test that verifies clean DB → working system**. Other tests assume DB already has data. Genesis test catches migration bugs and seed script issues.

---

**Q**: Can we run all tests in parallel to speed up CI?

**A**: Partially. Tests that don't mutate shared DB state (like `test_champion_badge_regression.py`) can run in parallel. Tests that create tournaments should run serially to avoid race conditions. Use pytest-xdist with `--dist loadscope` for safe parallelization.

---

## Summary

**Current State**: 2/10 tests CI-ready (20%)
**After Conversion**: 8/10 tests CI-ready (80%)
**Estimated Effort**: ~2 hours
**New Tests Needed**: 0 (existing tests sufficient)
**Architecture Changes**: Minimal (add conftest.py, update test signatures)

**Recommendation**: **Proceed with conversion plan**. Existing tests provide excellent coverage; they just need headless mode enabled for CI automation.
