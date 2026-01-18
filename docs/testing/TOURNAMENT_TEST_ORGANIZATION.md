# Tournament Test Organization

## 📋 Overview

This document describes the organization and structure of all tournament-related tests in the LFA Intern System.

**Last Updated**: 2026-01-16
**Status**: ✅ Reorganized and consolidated

---

## 🎯 Master E2E Test Suite

### Location
`tests/e2e/run_all_e2e_tests.sh`

### Purpose
Runs the complete end-to-end user journey in sequence:
1. **Admin creates invitation codes** (UI)
2. **Users register with invitations** (UI)
3. **Users complete onboarding** (UI)
4. **Tournament instructor workflow** (UI) ← **Now uses UI-based tournament creation!**

### Test Execution Order
```bash
1. test_d1_admin_creates_three_invitation_codes
2. test_d2_first_user_registers_with_invitation
3. test_d3_second_user_registers_with_invitation
4. test_d4_third_user_registers_with_invitation
5. test_complete_onboarding_user1
6. test_complete_onboarding_user2
7. test_complete_onboarding_user3
8. test_complete_ui_workflow  ← TOURNAMENT WORKFLOW
```

### Key Features
- ✅ **No database reset between tests** - tests build on each other
- ✅ **DB snapshots** saved after registration, onboarding, and tournament workflow
- ✅ **Debug mode** on failure with interactive shell
- ✅ **UI-first approach** - tournament creation now via UI, not API

---

## 🏆 Tournament Test Files

### 1. **Main Tournament Workflow Test**
**File**: `tests/e2e/test_ui_instructor_application_workflow.py`
**Status**: ✅ **ACTIVE - MASTER TEST**

**What it tests**:
- ✅ **Step 0 (NEW!)**: Admin creates tournament via UI
  - Fills all form fields
  - Selects location, campus, age group
  - Sets tournament type and assignment type (APPLICATION_BASED)
- ✅ **Step 1**: Instructor logs in and browses open tournaments
- ✅ **Step 2**: Instructor applies to tournament
- ✅ **Step 3**: Admin approves application (API)
- ✅ **Step 4**: Instructor accepts assignment (UI)
- ✅ **Step 5**: Admin opens enrollment (UI)
- ✅ **Steps 6-7**: Players enroll (UI loop, 5 players)
- ✅ **Step 8**: Admin transitions to IN_PROGRESS (UI)
- ✅ **Step 9**: Instructor records results (UI)
- ✅ **Step 10**: Instructor marks COMPLETED (UI)
- ✅ **Step 11**: Admin distributes rewards (UI)
- ✅ **Step 12**: Player views results (UI)

**Workflow Coverage**: COMPLETE lifecycle (creation → rewards distribution)

**Used By**: Master script `run_all_e2e_tests.sh`

---

### 2. **Refactored Admin Tournament Creation**
**File**: `tests/e2e/test_admin_create_tournament_refactored.py`
**Status**: ✅ ACTIVE

**What it tests**:
- Admin creates tournament using NEW TournamentType system
- Verifies creation in UI and backend API
- **Standalone test** (not part of master workflow)

**When to use**: Testing tournament creation UI in isolation

---

### 3. **Tournament Enrollment Tests**
**Files**:
- `tests/playwright/test_tournament_enrollment_application_based.py`
- `tests/playwright/test_tournament_enrollment_open_assignment.py`
- `tests/e2e/test_tournament_enrollment_protection.py`

**What they test**:
- Player enrollment for APPLICATION_BASED tournaments
- Player enrollment for OPEN_ASSIGNMENT tournaments
- Enrollment status protection (INSTRUCTOR_CONFIRMED → READY_FOR_ENROLLMENT)

---

### 4. **Tournament Game Types Test**
**File**: `tests/playwright/test_tournament_game_types.py`
**Status**: ✅ ACTIVE

**What it tests**:
- Admin creates games for all 4 types:
  - League Match
  - King of Court
  - Group Stage
  - Elimination

---

### 5. **Tournament API Tests**
**Files**:
- `tests/api/test_tournament_enrollment.py` - Enrollment protection rules (API-only)
- `tests/e2e/test_tournament_creation_cycle.py` - Status transitions (API-only)
- `tests/e2e/test_tournament_workflow_happy_path.py` - Complete lifecycle (mostly API)

**When to use**: Testing backend logic without UI

---

### 6. **Attendance Tests**
**Files**:
- `tests/e2e/test_tournament_attendance_complete.py` - 2-button rule (Present/Absent only)
- `tests/integration/tournament/test_api_attendance.py` - API attendance recording
- `tests/integration/tournament/test_api_attendance_validation.py` - Attendance validation rules

---

### 7. **Unit Tests**
**Location**: `tests/unit/tournament/`

**Files**:
- `test_core.py` - CRUD operations
- `test_validation.py` - Validation logic
- `test_team_service.py` - Team operations
- `test_leaderboard_service.py` - Leaderboard generation
- `test_tournament_xp_service.py` - XP/points system
- `test_stats_service.py` - Statistics calculation

---

## 🗑️ Deleted/Archived Files

### Recently Deleted (2026-01-16)
1. ❌ `tests/e2e/test_instructor_tournament_flow.py`
   **Reason**: Redundant - functionality now in `test_ui_instructor_application_workflow.py`

2. ❌ `tests/playwright/test_ui_instructor_application_workflow.py`
   **Reason**: Exact duplicate of e2e version

### Archived
1. 📦 `tests/.archive/test_admin_create_tournament.py`
   **Reason**: Obsolete - uses old template-based system, replaced by refactored version

---

## 🔄 Recent Changes (2026-01-16)

### ✅ What Changed
1. **Tournament creation in master workflow now uses UI** instead of API
   - Location: `test_ui_instructor_application_workflow.py`
   - Benefit: True end-to-end testing of tournament creation form

2. **Consolidated duplicate tests**
   - Deleted redundant `test_instructor_tournament_flow.py`
   - Deleted duplicate playwright version

3. **Archived obsolete tests**
   - Moved old template-based test to `.archive/`

### 📊 Impact
- **Fewer test files** (3 deleted, 1 archived)
- **Clearer test organization**
- **Better UI coverage** (tournament creation now tested end-to-end)
- **No functionality lost** - all features still tested

---

## 🚀 Running Tests

### Run Master E2E Suite
```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
./tests/e2e/run_all_e2e_tests.sh
```

### Run Single Tournament Workflow Test
```bash
pytest tests/e2e/test_ui_instructor_application_workflow.py::TestInstructorApplicationWorkflowUI::test_complete_ui_workflow --headed --browser firefox --slowmo 500 -v
```

### Run Tournament Creation Test (Standalone)
```bash
pytest tests/e2e/test_admin_create_tournament_refactored.py --headed --browser firefox --slowmo 500 -v
```

---

## 📝 Test Development Guidelines

### When to Create a New Tournament Test

**DO create a new test when**:
- Testing a new tournament feature that doesn't fit existing tests
- Testing a specific edge case or failure scenario
- Testing a new tournament type or game type

**DON'T create a new test when**:
- The functionality is already covered by existing tests
- You can extend an existing test instead
- It would duplicate existing test coverage

### Test Organization Principles

1. **Master workflow** (`run_all_e2e_tests.sh`) covers the happy path
2. **Standalone tests** cover specific features or edge cases
3. **API tests** cover backend logic without UI overhead
4. **Unit tests** cover service layer logic

### Naming Conventions
- `test_{area}_{feature}_{type}.py`
- Examples:
  - `test_tournament_enrollment_protection.py`
  - `test_tournament_creation_cycle.py`
  - `test_admin_create_tournament_refactored.py`

---

## 🔍 Troubleshooting

### Test Fails in Master Workflow

1. **Check which step failed** - the script shows clear output
2. **Inspect browser** - Firefox window stays open on failure
3. **Check database state** - debug commands shown in output
4. **Review screenshots** - saved in `tests/e2e/screenshots/`
5. **Check DB snapshots** - use `snapshot_manager.sh` to restore

### Tournament Not Visible to Instructor

**Possible causes**:
- Tournament status not SEEKING_INSTRUCTOR
- Instructor missing LFA_COACH license
- Instructor's coach level too low for age group
- Session state caching issue (cleared by fresh login)

**Fix**:
- Check `get_instructor_coach_level()` in `tournament_helpers.py`
- Verify no session state caching in view files

---

## 📚 Related Documentation

- [E2E Test Suite README](../../tests/e2e/README_TEST_SUITE.md)
- [Playwright Test README](../../tests/playwright/README.md)
- [API Test README](../../tests/api/README.md)
- [Tournament E2E Tests Summary](../TOURNAMENT_E2E_TESTS_SUMMARY.md)

---

## ✨ Summary

The tournament test suite is now **streamlined and organized**:
- ✅ **Master workflow** covers complete UI journey
- ✅ **No duplicate tests**
- ✅ **Clear file organization**
- ✅ **UI-first testing** for tournament creation
- ✅ **Comprehensive coverage** from creation to reward distribution

**Total Active Tournament Tests**: ~15 files
**Total Lines Deleted**: ~1,500
**Test Coverage**: Unchanged (all features still tested)
