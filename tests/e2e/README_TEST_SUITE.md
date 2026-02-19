# E2E Test Suite Documentation

## Overview

This E2E test suite validates the complete user journey through the LFA Intern System, from user registration to tournament participation and rewards distribution.

## Architecture

### Key Principle: Sequential Execution Without Intermediate Resets

Unlike traditional test suites that reset state between tests, this suite:
- ✅ **Resets database ONCE** at the start
- ✅ **Runs tests in sequence**, each building on the previous
- ✅ **Preserves state** between tests for efficiency
- ✅ **Stops on first failure** with debug console
- ✅ **Automatic snapshots** at key milestones for quick retesting

### Benefits

1. **Realistic User Journey**: Tests mirror actual user workflows
2. **Faster Execution**: No repeated database resets
3. **Better Debugging**: State is preserved when tests fail
4. **Data Reuse**: Users created in early tests are used in later tests
5. **Quick Iteration**: Snapshot restore allows testing single tests without full suite run

## Database Snapshot System

The suite automatically creates database snapshots at key test milestones, enabling:
- **Fast retesting** of individual tests without rerunning entire suite
- **Consistent starting state** for debugging failing tests
- **Parallel test development** by restoring to different checkpoints

### Snapshot Commands

```bash
# List all available snapshots
./tests/e2e/snapshot_manager.sh list

# Save current database state
./tests/e2e/snapshot_manager.sh save <snapshot_name>

# Restore database to saved state
./tests/e2e/snapshot_manager.sh restore <snapshot_name>

# Delete a snapshot
./tests/e2e/snapshot_manager.sh delete <snapshot_name>
```

### Automatic Snapshots

The master test runner automatically creates these snapshots:

| Snapshot Name | Created After | Contains |
|--------------|---------------|----------|
| `after_registration` | 3 users registered | Admin, 3 test users (pwt.*), invitation codes consumed |
| `after_onboarding` | 3 users onboarded | Registration + LFA licenses unlocked, coupons redeemed, 50 credits each |
| `after_instructor_workflow` | Instructor assigned | Onboarding + tournament created, instructor approved & accepted |

### Run Single Test from Snapshot

Instead of rerunning the entire suite, restore a snapshot and run one test:

```bash
# Example: Test instructor workflow starting from after_onboarding
./tests/e2e/run_single_test.sh after_onboarding tests/e2e/test_ui_instructor_application_workflow.py::TestInstructorApplicationWorkflowUI::test_complete_ui_workflow

# Example: Test onboarding for user 1 starting from after_registration
./tests/e2e/run_single_test.sh after_registration tests/e2e/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user1
```

This workflow enables **rapid iteration** when fixing bugs in specific tests!

## Test Execution Order

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Database Reset                                  │
│   → scripts/reset_database_for_tests.py                 │
│   Creates: Admin, Grandmaster, Location, Campus         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Setup Invitation Codes                          │
│   → tests/e2e/setup_invitation_codes.py                 │
│   Creates: 3 invitation codes for registration          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Setup Coupons                                   │
│   → tests/e2e/setup_onboarding_coupons.py               │
│   Creates: 3 BONUS_CREDITS coupons (+50 credits)        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ TEST 1: User Registration                               │
│   → test_user_registration_with_invites.py              │
│   Creates: 3 users via UI registration flow             │
│   - pwt.k1sqx1@f1stteam.hu                              │
│   - pwt.p3t1k3@f1stteam.hu                              │
│   - pwt.V4lv3rd3jr@f1stteam.hu                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ TEST 2-4: Onboarding Workflow (3 tests, one per user)  │
│   → test_complete_onboarding_with_coupon_ui.py          │
│   Each user:                                             │
│   1. Applies coupon (+50 credits → 100 total)           │
│   2. Unlocks specialization (-100 credits → 0)          │
│   3. Completes onboarding (Position, Skills, Goals)     │
│   Result: 3 fully onboarded players with licenses       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ TEST 5: Instructor Assignment Workflow                  │
│   → test_ui_instructor_application_workflow.py          │
│   1. Admin creates tournament (via API)                 │
│   2. Instructor applies to tournament (via UI)          │
│   3. Admin approves application (via API)               │
│   4. Instructor accepts assignment (via UI)             │
│   5. Admin opens enrollment (via UI)                    │
│   6. **3 players enroll** (via UI - REUSES users!)      │
│   7. Admin starts tournament (via UI)                   │
│   8. Admin records results & distributes rewards        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ TEST 6: Tournament Enrollment Protection (future)       │
│   → test_tournament_enrollment_protection.py            │
│   Validates enrollment rules and credit handling        │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Run Complete Suite

```bash
./tests/e2e/run_all_e2e_tests.sh
```

This script:
1. Resets database
2. Creates invitation codes and coupons
3. Runs all tests in correct order
4. **Stops on first failure** and opens debug console
5. Shows colored output with progress indicators

### Run Individual Test (Manual)

⚠️ **Warning**: Running tests individually may fail if prerequisites aren't met!

```bash
# Setup (if not already done)
python scripts/reset_database_for_tests.py
python tests/e2e/setup_invitation_codes.py
python tests/e2e/setup_onboarding_coupons.py

# Run specific test
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
PYTHONPATH=/path/to/project \
pytest tests/e2e/test_user_registration_with_invites.py \
  --headed --browser firefox --slowmo 500 -v
```

## Test Data

### Users Created During Tests

| Email | Password | Created In | Credits After Onboarding | License |
|-------|----------|-----------|-------------------------|---------|
| pwt.k1sqx1@f1stteam.hu | password123 | Registration Test | 0 (spent on unlock) | LFA_FOOTBALL_PLAYER |
| pwt.p3t1k3@f1stteam.hu | password123 | Registration Test | 0 (spent on unlock) | LFA_FOOTBALL_PLAYER |
| pwt.V4lv3rd3jr@f1stteam.hu | password123 | Registration Test | 0 (spent on unlock) | LFA_FOOTBALL_PLAYER |

### Pre-existing Users (from reset script)

| Email | Password | Role | Credits | Purpose |
|-------|----------|------|---------|---------|
| admin@lfa.com | admin123 | ADMIN | 0 | Admin operations |
| grandmaster@lfa.com | GrandMaster2026! | INSTRUCTOR | 5000 | Has 21 licenses |

## Debugging Failed Tests

When a test fails, the script:
1. **Stops execution** immediately
2. **Displays error details** with colored output
3. **Opens debug console** (interactive bash shell)
4. **Preserves database state** for inspection

### Debug Console Commands

```bash
# Check users
psql $DATABASE_URL -c "SELECT id, email, credit_balance, onboarding_completed FROM users;"

# Check tournaments
psql $DATABASE_URL -c "SELECT id, name, tournament_status FROM semesters;"

# Check enrollments
psql $DATABASE_URL -c "SELECT * FROM semester_enrollments;"

# Check licenses
psql $DATABASE_URL -c "SELECT user_id, specialization_type, current_level FROM user_licenses;"

# Exit debug console
Ctrl+D
```

## Configuration

### Test Speed

Adjust `--slowmo` parameter in `run_all_e2e_tests.sh`:
- `--slowmo 0`: Fast (no delay)
- `--slowmo 500`: Medium (500ms between actions) **← Default**
- `--slowmo 1500`: Slow (1.5s between actions, good for demos)

### Browser

Change `--browser` parameter:
- `--browser firefox` **← Default**
- `--browser chromium`
- `--browser webkit` (Safari-like)

### Headless Mode

Remove `--headed` flag to run without visible browser:
```bash
PYTEST_OPTS="-v --tb=short"  # No --headed
```

## Common Issues

### Issue: "Invitation codes not found"
**Solution**: Run `python tests/e2e/setup_invitation_codes.py` before tests

### Issue: "Users already exist"
**Solution**: Reset database: `python scripts/reset_database_for_tests.py`

### Issue: "No credits to unlock specialization"
**Solution**: Ensure onboarding tests ran successfully and coupons were applied

### Issue: "Tournament not found"
**Solution**: Ensure test order is correct - instructor workflow must run before enrollment

## File Structure

```
tests/e2e/
├── README_TEST_SUITE.md                    # This file
├── run_all_e2e_tests.sh                    # Master test runner
├── setup_invitation_codes.py               # Creates invitation codes
├── setup_onboarding_coupons.py             # Creates coupon codes
├── test_user_registration_with_invites.py  # Registration test
├── test_complete_onboarding_with_coupon_ui.py  # Onboarding tests
├── test_ui_instructor_application_workflow.py  # Instructor & tournament workflow
├── test_tournament_enrollment_protection.py    # Enrollment validation
├── reward_policy_fixtures.py               # Test fixtures and helpers
└── screenshots/                            # Test failure screenshots
```

## Best Practices

1. **Always use the master script**: `run_all_e2e_tests.sh`
2. **Don't run tests individually** unless debugging specific test
3. **Reset database before full suite run** (script does this automatically)
4. **Check screenshots on failure**: `tests/e2e/screenshots/`
5. **Use debug console** to inspect state when tests fail

## Maintenance

### Adding New Tests

1. Determine where in sequence test should run
2. Add test file to `TESTS` array in `run_all_e2e_tests.sh`
3. Ensure test reuses existing data when possible
4. Update this README with test description

### Modifying Test Order

⚠️ **Be careful!** Tests depend on previous tests' data.

Requirements:
- Registration must run before onboarding
- Onboarding must run before tournament enrollment
- Tournament creation must run before player enrollment

## Performance

Full suite execution time (with `--slowmo 500`):
- Database reset: ~5 seconds
- Setup scripts: ~2 seconds
- Registration test: ~30 seconds
- Onboarding tests (3): ~90 seconds
- Instructor workflow: ~120 seconds
- **Total: ~4-5 minutes**

## Future Improvements

- [ ] Parallel test execution for independent tests
- [ ] Video recording on failure
- [ ] HTML test report generation
- [ ] Slack/email notifications on failure
- [ ] CI/CD integration
