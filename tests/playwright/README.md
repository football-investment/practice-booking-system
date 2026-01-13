# Playwright E2E Tests

This directory contains all Playwright end-to-end (E2E) tests for the LFA Internship System.

## 📁 Directory Structure

```
tests/playwright/
├── README.md                          # This file
├── conftest.py                        # Pytest configuration and fixtures
├── run_all_e2e_tests.sh              # Master test runner script
├── snapshot_manager.sh                # Database snapshot utility
├── run_single_test.sh                 # Run individual tests
├── utils/                             # Utility scripts and fixtures
│   ├── fixtures.py                    # Test fixtures
│   ├── reward_policy_fixtures.py      # Reward policy test fixtures
│   └── setup_onboarding_coupons.py    # Coupon setup utility
├── screenshots/                       # Test screenshots (created at runtime)
└── snapshots/                         # Database snapshots (created at runtime)
```

## 🧪 Test Files

### Core Workflow Tests

These tests form the complete user journey and should be run sequentially:

1. **`test_user_registration_with_invites.py`**
   - Tests user registration with invitation codes
   - Creates 3 test users via UI
   - Tests: `test_d1_admin_creates_three_invitation_codes`, `test_d2_first_user_registers_with_invitation`, `test_d3_second_user_registers_with_invitation`, `test_d4_third_user_registers_with_invitation`

2. **`test_complete_onboarding_with_coupon_ui.py`**
   - Tests complete onboarding workflow with coupon redemption
   - Validates age, gender, specialization selection
   - Tests: `test_complete_onboarding_user1`, `test_complete_onboarding_user2`, `test_complete_onboarding_user3`

3. **`test_ui_instructor_application_workflow.py`**
   - Complete tournament management workflow (Admin → Instructor → Player)
   - Tournament creation, instructor assignment, enrollment, results, rewards
   - Test: `TestInstructorApplicationWorkflowUI::test_complete_ui_workflow`

4. **`test_tournament_enrollment_protection.py`**
   - Validates enrollment protection (players can only enroll when admin opens enrollment)
   - Tests status transitions: `INSTRUCTOR_CONFIRMED` → `READY_FOR_ENROLLMENT`

### Demo Tests

5. **`demo_player_login.py`**
   - Simple demo for showcasing player login
   - Perfect for presentations

## 🚀 Running Tests

### Run All Tests (Master Script)

The master script runs all tests in correct order with database reset and snapshots:

```bash
./tests/playwright/run_all_e2e_tests.sh
```

**What it does:**
1. Resets database to clean state
2. Sets up required coupons
3. Runs all tests sequentially in Firefox headed mode (visible browser)
4. Saves database snapshots after key milestones
5. On failure: Opens interactive debug shell

### Run Individual Test

```bash
./tests/playwright/run_single_test.sh test_name.py
```

Or use pytest directly:

```bash
# Headed mode (visible browser) - Firefox
pytest tests/playwright/test_name.py --headed --browser firefox --slowmo 500 -v

# Headless mode (invisible browser)
pytest tests/playwright/test_name.py --browser chromium -v
```

### Run Specific Test Function

```bash
pytest tests/playwright/test_user_registration_with_invites.py::test_d1_admin_creates_three_invitation_codes --headed --browser firefox -v
```

## 🎯 Pytest Options

- `--headed`: Show browser window (for demos and debugging)
- `--browser firefox`: Use Firefox (recommended for headed mode)
- `--browser chromium`: Use Chromium (faster for headless)
- `--slowmo 500`: Add 500ms delay between actions (easier to follow)
- `-v`: Verbose output
- `--tb=short`: Short traceback on failure
- `-s`: Show print statements

## 📸 Database Snapshots

The snapshot manager allows saving and restoring database state:

```bash
# Save current database state
./tests/playwright/snapshot_manager.sh save snapshot_name

# Restore database state
./tests/playwright/snapshot_manager.sh restore snapshot_name

# List all snapshots
./tests/playwright/snapshot_manager.sh list

# Delete a snapshot
./tests/playwright/snapshot_manager.sh delete snapshot_name
```

**Automatic snapshots** are created by the master script after:
- User registration (3 users created)
- Onboarding completion (all 3 users onboarded)
- Instructor workflow (tournament with instructor assigned)

## 🛠️ Test Environment

### Required Services

Both servers must be running:

```bash
# Terminal 1: FastAPI backend
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Streamlit frontend
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  streamlit run streamlit_app/🏠_Home.py --server.port 8501 --server.address 0.0.0.0
```

### Database

- **PostgreSQL** database: `lfa_intern_system`
- **Connection**: `postgresql://postgres:postgres@localhost:5432/lfa_intern_system`
- **Reset script**: `scripts/reset_database_for_tests.py`

## 📋 Test Dependencies

All tests depend on:
- Playwright (browser automation)
- pytest-playwright (pytest integration)
- FastAPI running on port 8000
- Streamlit running on port 8501
- PostgreSQL database

## 🐛 Debugging Failed Tests

When a test fails in the master script:

1. **Browser stays open** - Inspect the UI state
2. **Servers keep running** - Check logs
3. **Interactive shell opens** - Query database

Useful debug commands:

```bash
# Check users
psql $DATABASE_URL -c "SELECT id, email, credit_balance, specialization FROM users;"

# Check tournaments
psql $DATABASE_URL -c "SELECT id, name, tournament_status FROM semesters;"

# Check enrollments
psql $DATABASE_URL -c "SELECT se.id, u.email, s.name FROM semester_enrollments se JOIN users u ON se.user_id=u.id JOIN semesters s ON se.semester_id=s.id;"

# Check screenshots
ls -lt tests/playwright/screenshots/ | head -10
```

## 📝 Writing New Tests

1. **Import fixtures** from `tests.playwright.utils.fixtures` or `tests.playwright.utils.reward_policy_fixtures`
2. **Use consistent naming**: `test_feature_name_ui.py` for UI tests
3. **Add markers**: `@pytest.mark.e2e`, `@pytest.mark.ui`
4. **Take screenshots** at critical points for debugging
5. **Use headed mode** during development: `--headed --browser firefox`

## ✅ Test Coverage

Current E2E test coverage:
- ✅ User registration with invitation codes
- ✅ Complete onboarding workflow (age, gender, specialization, license)
- ✅ Coupon redemption (bonus credits)
- ✅ Tournament creation (admin)
- ✅ Instructor assignment workflow
- ✅ Tournament enrollment protection (players can only enroll when admin opens enrollment)
- ✅ Player enrollment via UI
- ✅ Result recording and rewards distribution

## 🔗 Related Documentation

- [API Tests](../api/README.md) - Backend API integration tests
- [Security Tests](../security/README.md) - Security validation tests
- [E2E Test Suite Status](./README_TEST_SUITE.md) - Detailed test suite documentation
