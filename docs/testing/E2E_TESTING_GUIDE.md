## 🎭 End-to-End (E2E) Testing Guide - Playwright

**Date:** 2026-01-03
**Phase:** 3 - Playwright E2E Tests
**Status:** ✅ READY TO RUN

---

## Overview

This guide explains how to run automated E2E tests using Playwright to validate the CRITICAL 2-button vs 4-button rule in a real browser environment.

**What is E2E Testing?**
- Tests run against the **live Streamlit application**
- Uses **real browser** (Chromium)
- Simulates **actual user interactions** (click, type, navigate)
- Validates **visual rendering** and **user workflows**

---

## Quick Start

### 1. Prerequisites

**Before running E2E tests:**

```bash
# 1. Start Streamlit app
streamlit run streamlit_app/main.py

# 2. Start backend API (if separate)
uvicorn app.main:app --reload
```

**Database requirements:**
- Tournament semester created
- Tournament session with 2+ enrolled students
- Regular semester created
- Regular session with 2+ enrolled students
- Test users exist (admin, instructor, student)

### 2. Run E2E Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run ALL E2E tests
pytest tests/e2e/ -v

# Run tournament E2E tests only
pytest tests/e2e/tournament/ -v

# Run regular session E2E tests only
pytest tests/e2e/sessions/ -v

# Run with headed browser (see what's happening)
pytest tests/e2e/ -v --headed

# Run with slow motion (500ms delay per action)
pytest tests/e2e/ -v --headed --slowmo 500
```

---

## Test Files Structure

```
tests/e2e/
├── __init__.py
├── conftest.py                           # Fixtures & helpers
├── tournament/
│   ├── __init__.py
│   └── test_tournament_checkin_e2e.py    # 10 E2E tests ⭐
└── sessions/
    ├── __init__.py
    └── test_session_checkin_e2e.py       # 7 E2E tests
```

**Total:** 17 automated E2E tests

---

## Critical Tests

### Test 1: Tournament Shows 2 Buttons ⭐ CRITICAL

**File:** `test_tournament_checkin_e2e.py::TestTournamentCheckinE2E::test_tournament_shows_only_2_attendance_buttons`

**What it does:**
1. Login as instructor
2. Navigate to Tournament Check-in
3. Select tournament session
4. Go to attendance marking page
5. **Verify:** ONLY 2 buttons per student (Present, Absent)
6. **Verify:** NO Late or Excused buttons

**How to run:**
```bash
pytest tests/e2e/tournament/test_tournament_checkin_e2e.py::TestTournamentCheckinE2E::test_tournament_shows_only_2_attendance_buttons -v
```

**Expected output:**
```
PASSED tests/e2e/tournament/test_tournament_checkin_e2e.py::TestTournamentCheckinE2E::test_tournament_shows_only_2_attendance_buttons
Screenshot saved: docs/screenshots/tournament_2_buttons_verified_e2e.png
```

---

### Test 2: Regular Session Shows 4 Buttons

**File:** `test_session_checkin_e2e.py::TestRegularSessionCheckinE2E::test_regular_session_shows_all_4_attendance_buttons`

**What it does:**
1. Login as instructor
2. Navigate to Session Check-in (regular)
3. Select regular session
4. Go to attendance marking page
5. **Verify:** ALL 4 buttons per student (Present, Absent, Late, Excused)

**How to run:**
```bash
pytest tests/e2e/sessions/test_session_checkin_e2e.py::TestRegularSessionCheckinE2E::test_regular_session_shows_all_4_attendance_buttons -v
```

---

### Test 3: Side-by-Side Comparison

**File:** `test_session_checkin_e2e.py::TestRegularVsTournamentComparison::test_button_count_difference`

**What it does:**
1. Navigate to regular session → Count buttons → Should have Late/Excused
2. Navigate to tournament session → Count buttons → Should NOT have Late/Excused
3. **Verify:** Regular has MORE buttons than tournament

**How to run:**
```bash
pytest tests/e2e/sessions/test_session_checkin_e2e.py::TestRegularVsTournamentComparison::test_button_count_difference -v
```

---

## Test Configuration

### Environment Variables

Configure test behavior via environment variables:

```bash
# App URL
export STREAMLIT_URL="http://localhost:8501"

# Test credentials
export TEST_INSTRUCTOR_EMAIL="instructor@lfa.com"
export TEST_INSTRUCTOR_PASSWORD="instructor123"

export TEST_ADMIN_EMAIL="admin@lfa.com"
export TEST_ADMIN_PASSWORD="admin123"

export TEST_STUDENT_EMAIL="student@lfa.com"
export TEST_STUDENT_PASSWORD="student123"
```

Or create a `.env` file:

```env
# .env
STREAMLIT_URL=http://localhost:8501
TEST_INSTRUCTOR_EMAIL=instructor@lfa.com
TEST_INSTRUCTOR_PASSWORD=instructor123
```

### Pytest Options

**pytest.ini** configuration:

```ini
[pytest]
markers =
    e2e: End-to-end tests (Playwright, full user flows)
    tournament: Tournament-specific tests
    ui: UI/frontend tests
    slow: Slow tests (> 1 second)
```

**Command-line options:**

```bash
# Run in headed mode (see browser)
pytest tests/e2e/ --headed

# Run with slow motion (500ms delay)
pytest tests/e2e/ --slowmo 500

# Run specific browser (default: chromium)
pytest tests/e2e/ --browser firefox
pytest tests/e2e/ --browser webkit

# Take video on failure
pytest tests/e2e/ --video on --video-dir test-results/

# Take screenshots
pytest tests/e2e/ --screenshot on --screenshot-dir test-results/

# Parallel execution (faster)
pytest tests/e2e/ -n 4  # 4 parallel workers
```

---

## Test Fixtures & Helpers

### Authentication Fixtures

Located in `tests/e2e/conftest.py`:

```python
# Auto-login fixtures
def test_something(instructor_page: Page):
    # Already logged in as instructor
    instructor_page.goto(STREAMLIT_URL + "/some-page")
    # ...

def test_admin_flow(admin_page: Page):
    # Already logged in as admin
    admin_page.click("text=Admin Panel")
    # ...
```

**Available fixtures:**
- `instructor_page` - Logged in as instructor
- `admin_page` - Logged in as admin
- `student_page` - Logged in as student

### Navigation Helpers

```python
from tests.e2e.conftest import navigate_to_tournament_checkin

def test_tournament(instructor_page: Page):
    navigate_to_tournament_checkin(instructor_page)
    # Now on tournament check-in page
```

**Available helpers:**
- `navigate_to_tournament_checkin(page)`
- `navigate_to_session_checkin(page)`

### Assertion Helpers

```python
from tests.e2e.conftest import (
    assert_button_count,
    assert_no_button_with_label,
    take_screenshot
)

def test_buttons(instructor_page: Page):
    # Assert 2 Present buttons
    assert_button_count(instructor_page, "Present", 2)

    # Assert NO Late buttons
    assert_no_button_with_label(instructor_page, "Late")

    # Take screenshot
    take_screenshot(instructor_page, "my_test_screenshot")
```

---

## Running Tests

### All E2E Tests

```bash
# Run all E2E tests (may take 2-5 minutes)
pytest tests/e2e/ -v
```

**Expected output:**
```
tests/e2e/tournament/test_tournament_checkin_e2e.py::TestTournamentCheckinE2E::test_tournament_shows_only_2_attendance_buttons PASSED
tests/e2e/tournament/test_tournament_checkin_e2e.py::TestTournamentCheckinE2E::test_tournament_shows_only_3_metrics PASSED
...
tests/e2e/sessions/test_session_checkin_e2e.py::TestRegularSessionCheckinE2E::test_regular_session_shows_all_4_attendance_buttons PASSED
...

======================== 17 passed in 120.45s ========================
```

### Tournament Tests Only

```bash
pytest tests/e2e/tournament/ -v
```

**Expected:** 10 tests passing

### Regular Session Tests Only

```bash
pytest tests/e2e/sessions/ -v
```

**Expected:** 7 tests passing

### With Visual Debugging

```bash
# Headed mode + slow motion
pytest tests/e2e/ -v --headed --slowmo 500
```

This will:
- Open a real browser window
- Run tests at slow speed (500ms between actions)
- Allow you to watch the tests execute

---

## Troubleshooting

### Issue: "Application not running"

**Error:**
```
playwright._impl._errors.TimeoutError: Timeout 10000ms exceeded.
```

**Solution:**
1. Ensure Streamlit app is running:
   ```bash
   streamlit run streamlit_app/main.py
   ```

2. Check app URL:
   ```bash
   echo $STREAMLIT_URL
   # Should output: http://localhost:8501
   ```

3. Verify app is accessible:
   ```bash
   curl http://localhost:8501
   ```

---

### Issue: "Login failed"

**Error:**
```
AssertionError: Login failed - Dashboard not found
```

**Solution:**
1. Check test credentials match database users
2. Verify users exist:
   ```sql
   SELECT email, role FROM users WHERE email IN ('instructor@lfa.com', 'admin@lfa.com');
   ```

3. Update environment variables:
   ```bash
   export TEST_INSTRUCTOR_EMAIL="your_instructor_email"
   export TEST_INSTRUCTOR_PASSWORD="your_password"
   ```

---

### Issue: "No tournament session found"

**Error:**
```
pytest.skip: No tournament session available
```

**Solution:**
Create tournament test data:

```sql
-- Create tournament semester
INSERT INTO semesters (code, name, start_date, end_date, is_active, status, specialization_type)
VALUES ('TOURN-20260110', 'Test Tournament', '2026-01-10', '2026-01-10', true, 'READY_FOR_ENROLLMENT', 'LFA_PLAYER_YOUTH');

-- Create tournament session
INSERT INTO sessions (title, date_start, date_end, session_type, capacity, is_tournament_game, game_type, semester_id)
VALUES ('Test Final', '2026-01-10 10:00:00', '2026-01-10 11:30:00', 'on_site', 20, true, 'Final', <semester_id>);

-- Enroll students
INSERT INTO bookings (user_id, session_id, status)
VALUES (2, <session_id>, 'CONFIRMED'), (3, <session_id>, 'CONFIRMED');
```

Or use admin UI:
1. Login as admin
2. Create tournament semester
3. Add tournament session
4. Enroll test students

---

### Issue: "Tests are slow"

**Optimization tips:**

1. **Run in parallel:**
   ```bash
   pip install pytest-xdist
   pytest tests/e2e/ -n 4  # 4 parallel workers
   ```

2. **Run headless (default):**
   ```bash
   pytest tests/e2e/ -v  # Don't use --headed
   ```

3. **Skip slow tests:**
   ```bash
   pytest tests/e2e/ -v -m "not slow"
   ```

4. **Run critical tests only:**
   ```bash
   pytest tests/e2e/ -v -k "2_buttons or 4_buttons"
   ```

---

## Screenshot & Video Capture

### Automatic Screenshots

E2E tests automatically capture screenshots at key points:

```python
# In test file
take_screenshot(page, "tournament_2_buttons_verified_e2e")
```

**Screenshots saved to:** `docs/screenshots/`

**Files created:**
- `tournament_2_buttons_verified_e2e.png`
- `regular_4_buttons_verified_e2e.png`
- `tournament_attendance_page_e2e.png`

### Video on Failure

Configure pytest to record video on test failure:

```bash
pytest tests/e2e/ --video on --video-dir test-results/
```

**Videos saved to:** `test-results/`

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium

      - name: Start Streamlit app
        run: |
          streamlit run streamlit_app/main.py &
          sleep 10

      - name: Run E2E tests
        run: |
          pytest tests/e2e/ -v --video on --screenshot on

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test-results/
```

---

## Test Coverage Summary

### E2E Tests Created

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_tournament_checkin_e2e.py` | 10 tests | ✅ READY |
| `test_session_checkin_e2e.py` | 7 tests | ✅ READY |
| **Total** | **17 tests** | **✅ READY** |

### Critical Paths Covered

- [x] Tournament shows 2 buttons (Present, Absent)
- [x] Tournament shows 3 metrics (Present, Absent, Pending)
- [x] Tournament has NO Late/Excused buttons
- [x] Regular session shows 4 buttons (Present, Absent, Late, Excused)
- [x] Regular session shows 5 metrics
- [x] Button click functionality works
- [x] Page loads within 5 seconds
- [x] Attendance marking responds within 2 seconds

---

## Next Steps

### 1. Run E2E Tests (NOW) ⏳

```bash
# Start app
streamlit run streamlit_app/main.py

# In new terminal:
source venv/bin/activate
pytest tests/e2e/ -v --headed --slowmo 500
```

### 2. Fix Any Failures

If tests fail:
1. Check error message
2. Refer to Troubleshooting section above
3. Update selectors if UI changed
4. Verify test data exists

### 3. Add to CI/CD Pipeline

Once tests pass locally:
1. Add GitHub Actions workflow
2. Run on every PR
3. Require E2E tests to pass before merge

---

## Comparison: Phase 1, 2, 3

| Phase | Type | Tests | Status | Automation |
|-------|------|-------|--------|------------|
| **Phase 1** | Backend (API, validation) | 73 tests | ✅ PASSING | ✅ Automated |
| **Phase 2** | Frontend (Component tests) | 15 test cases | ⏳ Manual | ❌ Scaffolded only |
| **Phase 3** | E2E (Playwright) | 17 tests | ✅ READY | ✅ Automated |

**Total:** 105 test cases across 3 layers

---

## Resources

- **Playwright Docs:** https://playwright.dev/python/
- **Pytest-Playwright:** https://github.com/microsoft/playwright-pytest
- **Streamlit Testing:** https://docs.streamlit.io/develop/concepts/app-testing

---

**Prepared by:** Claude Sonnet 4.5
**Generated with:** [Claude Code](https://claude.com/claude-code)
