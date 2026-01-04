# Tests

This directory contains all test files organized by type.

## 🎯 Tournament Refactoring Test Suite (NEW!)

**Phase 1 - Backend Unit + Integration Tests** for the modular tournament system refactoring.

### Quick Start - Tournament Tests

```bash
# Run all tournament tests
pytest -m tournament

# Run tournament validation tests only
pytest tests/unit/tournament/test_validation.py -v

# Run tournament core CRUD tests
pytest tests/unit/tournament/test_core.py -v

# Run with coverage for tournament modules
pytest -m tournament --cov=app/services/tournament --cov-report=html
```

**Test Files:**
- ✅ `tests/unit/tournament/test_validation.py` - 25+ validation tests
- ✅ `tests/unit/tournament/test_core.py` - 30+ CRUD tests
- 🔄 `tests/unit/tournament/test_instructor_service.py` - WIP
- 🔄 `tests/unit/tournament/test_enrollment_service.py` - WIP
- 🔄 `tests/integration/tournament/test_api_attendance.py` - WIP (CRITICAL: 2 vs 4 button validation)

**Key Test Scenarios:**
- ✅ Age category validation (PRE, YOUTH, AMATEUR, PRO)
- ✅ Tournament attendance: ONLY present/absent (NO late/excused)
- ✅ Tournament session type: ONLY on_site (NO hybrid/virtual)
- ✅ Enrollment deadline validation (1 hour before start)
- ✅ Tournament semester creation (SEEKING_INSTRUCTOR → READY_FOR_ENROLLMENT)
- ✅ Cascade deletion (semester → sessions → bookings)

See detailed documentation: [Tournament Test Guide](#tournament-test-guide) (below)

---

## Directory Structure

### `/unit`
Unit tests for individual components and functions.

**Tournament Tests (NEW):**
- `tournament/test_validation.py` - Business logic validation
- `tournament/test_core.py` - CRUD operations
- `tournament/test_instructor_service.py` - Instructor assignment
- `tournament/test_enrollment_service.py` - Student enrollment

### `/integration`
Integration tests for API endpoints, database operations, and multi-component workflows.

**Key Files:**
- `test_*.py` - Integration tests for various features
- `test_api_integration.py` - API endpoint integration tests
- `test_complete_quiz_workflow.py` - Quiz workflow testing
- `test_semester_e2e.py` - Semester end-to-end tests
- `test_lfa_coach_service.py` - Coach service tests
- `test_lfa_internship_service.py` - Internship service tests
- `test_lfa_player_service.py` - Player service tests
- `test_license_authorization.py` - License authorization tests
- `test_session_rules_comprehensive.py` - Session rules testing

### `/e2e`
End-to-end tests simulating complete user journeys using Playwright.

**Key Files:**
- `test_reward_policy_distribution.py` - Reward distribution E2E test
- `reward_policy_fixtures.py` - Tournament fixtures for reward testing
- `conftest.py` - Playwright configuration and browser setup

**⚠️ IMPORTANT: E2E Test Limitations**

The current E2E tests use a **SIMPLIFIED FLOW** that does NOT represent production:

**Missing Components (Not Implemented):**
- ❌ Instructor Dashboard UI
- ❌ Instructor assignment workflow
- ❌ Session attendance tracking
- ❌ Instructor-submitted rankings

**Current Test Scope:**
- ✅ Admin tournament creation with reward policies
- ✅ Player enrollment
- ✅ Reward distribution backend logic (XP/Credits calculation)
- ✅ Transaction audit trail

**Simplified Flow Used:**
1. Admin creates tournament (SEEKING_INSTRUCTOR)
2. ⚠️ Manual status change → READY_FOR_ENROLLMENT (bypasses instructor)
3. Players enroll
4. ⚠️ Direct SQL ranking insertion (bypasses attendance)
5. Mark as COMPLETED
6. Admin distributes rewards

**Production Flow (Should Be):**
1. Admin creates tournament
2. Instructor accepts assignment → READY_FOR_ENROLLMENT
3. Players enroll
4. Instructor marks attendance for each session
5. Instructor submits rankings based on results
6. Mark as COMPLETED
7. Admin distributes rewards

**Production Readiness:** 🔴 NOT READY
- Backend reward logic: ✅ Working
- Instructor workflow: ❌ Not implemented
- See: `docs/backend/instructor_workflow.md` for implementation plan

### `/scenarios`
Scenario-based tests for specific business cases.

**Currently:** To be populated with scenario tests.

### `/performance`
Performance and load testing results.

**Key Files:**
- `*_test_report_*.json` - Test result reports from various runs
- `session_rules_test_report_*.json` - Session rules test results
- `journey_test_report_*.json` - Journey test results

---

## Running Tests

### All Integration Tests
```bash
pytest tests/integration/ -v
```

### Specific Test File
```bash
pytest tests/integration/test_api_integration.py -v
```

### With Coverage
```bash
pytest tests/integration/ --cov=app --cov-report=html
```

### Run Test Dashboard (Interactive)
```bash
./scripts/startup/start_session_rules_dashboard.sh
```

---

## Test Reports

Performance test reports are stored in `/performance` directory with timestamps.

View latest test results:
```bash
ls -lt tests/performance/*.json | head -5
```

---

## Navigation

- Project Root: `../`
- Documentation: `../docs/`
- Scripts: `../scripts/`
- Application Code: `../app/`

---

## Tournament Test Guide

### 📖 Overview

The tournament refactoring introduced a modular architecture with strict separation between tournament and regular sessions. The test suite validates this separation and ensures business rules are enforced.

### 🔑 Key Differences: Tournament vs Regular Sessions

| Feature | Tournament | Regular Session |
|---------|-----------|-----------------|
| **Attendance Statuses** | ONLY Present, Absent | Present, Absent, Late, Excused |
| **Session Type** | ONLY on_site | on_site, hybrid, virtual |
| **Enrollment** | Auto-approved | Requires payment |
| **Master Instructor** | Required | Optional |
| **Duration** | 1-day event | Multi-week semester |

### 🧪 Test Fixtures

Common fixtures available in tournament tests (via `conftest.py`):

```python
# Database & API
test_db                  # SQLite in-memory database
client                   # FastAPI TestClient

# Users
admin_user              # Admin with token
instructor_user         # Instructor with token
student_user           # Student with token
student_users          # List of 10 students

# Tournament Data
tournament_date                          # Date 7 days from now
tournament_semester                      # Status: SEEKING_INSTRUCTOR
tournament_semester_with_instructor      # Status: READY_FOR_ENROLLMENT
tournament_sessions                      # 3 sessions at 09:00, 11:00, 14:00
tournament_session_with_bookings         # Session with 5 bookings
instructor_assignment_request            # Pending instructor request
```

### ✅ Critical Test Scenarios

#### 1. Attendance Status Validation (MOST IMPORTANT)

**Why:** This prevents tournaments from accepting "late" or "excused" attendance.

```python
def test_tournament_attendance_only_2_statuses():
    """Tournament sessions ONLY accept present/absent."""
    # ✅ Present - should work
    # ✅ Absent - should work
    # ❌ Late - should FAIL
    # ❌ Excused - should FAIL
```

**Run:** `pytest tests/unit/tournament/test_validation.py::TestValidateTournamentAttendanceStatus -v`

#### 2. Age Category Rules

**Why:** YOUTH can "move up" to AMATEUR, but NOT to PRO.

```python
def test_youth_can_enroll_in_amateur():
    """YOUTH players can enroll in AMATEUR tournaments."""
    is_valid, error = validate_tournament_enrollment_age("YOUTH", "AMATEUR")
    assert is_valid is True

def test_youth_cannot_enroll_in_pro():
    """YOUTH players CANNOT enroll in PRO tournaments."""
    is_valid, error = validate_tournament_enrollment_age("YOUTH", "PRO")
    assert is_valid is False
    assert "not PRO" in error
```

**Run:** `pytest tests/unit/tournament/test_validation.py::TestValidateTournamentEnrollmentAge -v`

#### 3. Enrollment Deadline

**Why:** Tournament enrollment closes 1 hour before start time.

```python
def test_enrollment_closed_59_minutes_before():
    """Enrollment is closed 59 minutes before start."""
    first_session_start = datetime.utcnow() + timedelta(minutes=59)
    is_valid, error = validate_enrollment_deadline(first_session_start)
    assert is_valid is False
    assert "Enrollment closed" in error
```

**Run:** `pytest tests/unit/tournament/test_validation.py::TestValidateEnrollmentDeadline -v`

### 🎯 Running Tests

#### Run all tournament tests

```bash
pytest -m tournament
```

#### Run validation tests only

```bash
pytest tests/unit/tournament/test_validation.py
```

#### Run with coverage

```bash
pytest -m tournament --cov=app/services/tournament --cov-report=html
open htmlcov/index.html
```

#### Run specific test

```bash
pytest tests/unit/tournament/test_validation.py::TestValidateTournamentAttendanceStatus::test_late_is_invalid -v
```

### 📊 Current Coverage

**Phase 1 Status:**
- ✅ Validation logic: 100% covered (25+ tests)
- ✅ Core CRUD: 95% covered (30+ tests)
- 🔄 Instructor service: 0% (WIP)
- 🔄 Enrollment service: 0% (WIP)
- 🔄 API integration: 0% (WIP)

**Next Steps:**
1. Complete instructor_service unit tests
2. Complete enrollment_service unit tests
3. Add API integration tests for critical paths
4. Add Streamlit AppTest component tests (Phase 2)
5. Add Playwright E2E tests (Phase 3)

### 🐛 Common Test Failures

#### ImportError: No module named 'app'

**Solution:** Run pytest from project root:
```bash
cd /path/to/practice_booking_system
pytest
```

#### Fixture 'test_db' not found

**Solution:** Ensure `conftest.py` exists in tests/ directory.

#### Database constraint errors

**Solution:** Test database is in-memory and auto-clears. If persistent DB used:
```bash
rm test.db
```

### 📝 Writing New Tests

#### Unit Test Template

```python
import pytest
from app.services.tournament.validation import validate_tournament_attendance_status

@pytest.mark.unit
@pytest.mark.tournament
@pytest.mark.validation
def test_my_validation_rule():
    """Test description."""
    # Arrange
    status = "late"

    # Act
    is_valid, error = validate_tournament_attendance_status(status)

    # Assert
    assert is_valid is False
    assert "Invalid tournament attendance status" in error
```

#### Integration Test Template (TBD)

```python
import pytest

@pytest.mark.integration
@pytest.mark.tournament
@pytest.mark.api
def test_tournament_attendance_api(client, instructor_token, tournament_session_with_bookings):
    """Test tournament attendance API endpoint."""
    session_id = tournament_session_with_bookings.id

    # Try to mark as "late" (should fail for tournaments)
    response = client.post(
        f"/api/v1/sessions/{session_id}/attendance",
        json={"user_id": 1, "status": "late"},
        headers={"Authorization": f"Bearer {instructor_token}"}
    )

    assert response.status_code == 400
    assert "Tournaments only support" in response.json()["detail"]
```

### 🚦 Test Markers

Use markers to filter tests:

```bash
# Run only unit tests
pytest -m unit

# Run only tournament tests
pytest -m tournament

# Run validation tests
pytest -m validation

# Run slow tests only
pytest -m slow

# Exclude slow tests
pytest -m "not slow"

# Combine markers
pytest -m "tournament and unit"
```

### 📈 Success Metrics

**Phase 1 Goals:**
- [x] 50+ unit tests created
- [ ] 80%+ code coverage for tournament modules
- [ ] 0 test failures
- [ ] All critical paths tested

**Current Status:**
- Unit tests: **55+** (validation + core)
- Integration tests: **0** (WIP)
- E2E tests: **0** (Phase 3)
- Coverage: **Run `pytest --cov` to check**

---

**Created:** 2026-01-02
**Last Updated:** 2026-01-02
**Phase:** 1 - Backend Unit + Integration Tests
