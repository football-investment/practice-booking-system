# 📘 E2E Testing Complete Guide

**Self-Contained, Fixture-Based E2E Testing Pattern**

---

## 🎯 Philosophy

E2E tests MUST be:
1. **Self-contained** - Create their own test data
2. **Isolated** - Don't depend on manual setup
3. **Clean** - Automatically cleanup after themselves
4. **Role-based** - Test different user perspectives
5. **Reproducible** - Run anywhere, anytime

**❌ WRONG:** "Please create tournament data in Admin Dashboard before running tests"
**✅ RIGHT:** Test creates data via API, runs, cleans up automatically

---

## 📁 File Structure

```
tests/e2e/
├── conftest.py                          # Playwright configuration
├── fixtures.py                          # ⭐ API-based test data fixtures
├── test_tournament_attendance_complete.py  # ⭐ Reference implementation
├── test_regular_session_attendance.py   # TODO: Follow same pattern
└── README.md                            # This guide
```

---

## 🔧 Core Components

### 1. Fixtures (`tests/e2e/fixtures.py`)

**Purpose:** Create test data via API calls, not manual UI interaction

**Key Fixtures:**

#### `admin_token`
```python
@pytest.fixture
def admin_token() -> str:
    """Get admin authentication for API calls."""
    # Returns JWT token for admin user
```

**Usage:** Required by most other fixtures for API calls

---

#### `test_instructor`
```python
@pytest.fixture
def test_instructor(admin_token: str) -> Dict:
    """
    Creates a test instructor user.

    Returns: {"id": 123, "email": "test@...", "password": "..."}
    Cleanup: Automatically deletes user after test
    """
```

**Usage:**
```python
def test_something(page, test_instructor):
    # Login with instructor
    page.fill("input[aria-label='Email']", test_instructor["email"])
    page.fill("input[aria-label='Password']", test_instructor["password"])
```

---

#### `test_students`
```python
@pytest.fixture
def test_students(admin_token: str) -> List[Dict]:
    """
    Creates 5 test student users.

    Returns: List of user dicts with email/password
    Cleanup: Automatically deletes all students
    """
```

---

#### `tournament_with_session`
```python
@pytest.fixture
def tournament_with_session(
    admin_token,
    test_instructor,
    test_students
) -> Dict:
    """
    Complete tournament setup:
    - Tournament semester
    - Tournament session (today)
    - Instructor assigned
    - 5 student bookings

    Returns: {
        "semester": {...},
        "session": {...},
        "instructor": {...},
        "students": [{...}, ...],
        "bookings": [{...}, ...]
    }

    Cleanup: Deletes semester (cascades to sessions/bookings)
    """
```

**This is the GOLDEN fixture** - use it as a template!

---

### 2. Reference Test (`test_tournament_attendance_complete.py`)

**Complete, production-ready E2E test demonstrating:**

✅ Fixture usage
✅ Login flow
✅ Navigation pattern
✅ Explicit assertions
✅ Debug aids (screenshots, print statements)
✅ Automatic cleanup

**Read this file FIRST before writing new tests!**

---

## 🚀 How to Write a New E2E Test

### Step 1: Identify What You're Testing

Ask yourself:
- **Business rule:** What rule am I validating? (e.g., "Tournament sessions show 2 buttons")
- **User flow:** What path does the user take? (e.g., "Instructor marks attendance")
- **Role:** Which user type? (instructor, admin, student)

### Step 2: Create or Reuse Fixtures

**Check if fixture exists:**
- Look in `tests/e2e/fixtures.py`
- Can you reuse `tournament_with_session`?
- Do you need regular sessions instead? Create `regular_session_with_bookings`

**Create new fixture if needed:**
```python
# tests/e2e/fixtures.py

@pytest.fixture
def regular_session_with_bookings(
    admin_token,
    test_instructor,
    test_students
) -> Dict:
    """Create regular (non-tournament) session."""
    # Similar to tournament_with_session but:
    # - is_tournament_game = False
    # - session_type can be HYBRID/VIRTUAL
    # - Returns same structure
    pass
```

### Step 3: Write Test Following the Pattern

```python
# tests/e2e/test_your_feature.py

import pytest
from playwright.sync_api import Page, expect
from tests.e2e.fixtures import tournament_with_session  # or your fixture
import os

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")


@pytest.mark.e2e
@pytest.mark.your_category  # e.g., @pytest.mark.tournament
class TestYourFeature:
    """
    E2E tests for [describe feature].

    Validates: [business rule]
    """

    def test_specific_behavior(
        self,
        page: Page,
        tournament_with_session: dict  # Use appropriate fixture
    ):
        """
        Test that [specific behavior].

        Test Flow:
        1. Setup: [what fixture creates]
        2. Login: [as which role]
        3. Navigate: [to which page]
        4. Action: [what user does]
        5. Assert: [what you verify]
        """

        # Extract test data
        instructor = tournament_with_session["instructor"]
        students = tournament_with_session["students"]

        print(f"\n🧪 Testing: [feature name]")

        # ============================================================
        # STEP 1: Login
        # ============================================================
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page.fill("input[aria-label='Email']", instructor["email"])
        page.fill("input[aria-label='Password']", instructor["password"])
        page.click("button:has-text('Login')")
        page.wait_for_timeout(3000)

        expect(page.locator("text=Dashboard")).to_be_visible()
        print("✅ Login successful")

        # ============================================================
        # STEP 2: Navigate to target page
        # ============================================================
        page.goto(f"{STREAMLIT_URL}/Your_Page")
        page.wait_for_timeout(2000)

        expect(page.locator("text=Your Page Title")).to_be_visible()
        print("✅ Navigated to target page")

        # ============================================================
        # STEP 3: Perform actions
        # ============================================================
        # Click something
        page.click("button:has-text('Action Button')")
        page.wait_for_timeout(1000)

        # Fill a form
        page.fill("input[placeholder='Enter value']", "test value")

        print("✅ Actions performed")

        # ============================================================
        # STEP 4: Make assertions
        # ============================================================
        result_elements = page.locator(".result-class")

        # Count elements
        assert result_elements.count() == expected_count, \
            f"Expected {expected_count}, got {result_elements.count()}"

        # Check visibility
        expect(page.locator("text=Success Message")).to_be_visible()

        # Take screenshot for evidence
        page.screenshot(path="docs/screenshots/your_test_result.png")

        print("✅ ✅ ✅ TEST PASSED!")

        # Cleanup happens automatically via fixture
```

### Step 4: Run and Debug

```bash
# Run your specific test
PYTHONPATH=. pytest tests/e2e/test_your_feature.py::TestYourFeature::test_specific_behavior -v

# Run with browser visible (for debugging)
PYTHONPATH=. pytest tests/e2e/test_your_feature.py::TestYourFeature::test_specific_behavior -v --headed --slowmo 500

# Run all E2E tests
PYTHONPATH=. pytest tests/e2e/ -m e2e -v
```

---

## 🎭 Role-Based Testing Patterns

### Pattern 1: Same Feature, Different Roles

```python
@pytest.mark.e2e
class TestAttendanceMarking:
    """Test attendance from different role perspectives."""

    def test_instructor_can_mark_attendance(
        self,
        page,
        tournament_with_session
    ):
        instructor = tournament_with_session["instructor"]
        # Login as instructor
        # Verify can mark attendance
        pass

    def test_admin_can_view_attendance(
        self,
        page,
        tournament_with_session
    ):
        # Login as admin
        # Verify can VIEW but maybe not EDIT
        pass

    def test_student_cannot_mark_others_attendance(
        self,
        page,
        tournament_with_session
    ):
        student = tournament_with_session["students"][0]
        # Login as student
        # Verify CANNOT mark other students' attendance
        pass
```

### Pattern 2: Permission Boundaries

```python
def test_instructor_without_session_sees_empty_state(
    page,
    test_instructor  # No session assigned!
):
    """Instructor without sessions sees appropriate empty state."""
    # Login
    # Navigate to check-in
    # Verify empty state message
    pass
```

---

## 📊 Fixture Design Patterns

### Pattern 1: Minimal Fixture

```python
@pytest.fixture
def minimal_tournament(admin_token):
    """Just semester + 1 session, no bookings."""
    semester = create_tournament_semester(admin_token)
    session = create_tournament_session(...)

    yield {"semester": semester, "session": session}

    cleanup_semester(admin_token, semester["id"])
```

**Use when:** Testing session display, not attendance

---

### Pattern 2: Time-Based Fixtures

```python
@pytest.fixture
def tournament_multiple_dates(admin_token, test_instructor):
    """Sessions in past, today, future."""
    # Create 3 sessions with different dates
    # Useful for date filtering tests
    pass
```

**Use when:** Testing "Today & Upcoming" logic

---

### Pattern 3: State-Based Fixtures

```python
@pytest.fixture
def tournament_partially_attended(admin_token, test_instructor, test_students):
    """Some students marked present, others pending."""
    # Create session
    # Mark 2/5 students as present
    # Leave 3/5 pending
    # Useful for testing incomplete states
    pass
```

---

## 🛠️ Helper Function Patterns

### API Call Helpers

```python
def create_tournament_semester(token: str) -> Dict:
    """
    Create semester via API.

    Returns: Semester data dict
    Raises: HTTPError if API call fails
    """
    response = requests.post(
        f"{API_BASE_URL}/api/v1/semesters",
        headers={"Authorization": f"Bearer {token}"},
        json={...}
    )
    response.raise_for_status()
    return response.json()
```

**Pattern:**
- Clear name (`create_X`, `delete_X`)
- Take `token` as first parameter
- Return parsed JSON
- Raise exceptions (let pytest handle)

---

### Cleanup Helpers

```python
def cleanup_semester(token: str, semester_id: int):
    """Delete semester via API (cascades to sessions/bookings)."""
    try:
        requests.delete(...)
    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")
        # Don't fail test on cleanup errors
```

**Pattern:**
- Try/except with warning (don't fail test)
- Cascade deletes when possible
- Log failures for debugging

---

## 🐛 Debugging Tips

### 1. Add Print Statements

```python
def test_something(page, tournament_with_session):
    session = tournament_with_session["session"]

    print(f"\n🧪 Testing session {session['id']}")
    print(f"   Date: {session['date_start']}")
    print(f"   Instructor: {tournament_with_session['instructor']['email']}")

    # ... test steps with print after each
    print("✅ Step 1 complete")
    print("✅ Step 2 complete")
```

### 2. Take Screenshots

```python
# After critical steps
page.screenshot(path=f"docs/screenshots/debug_{step_name}.png")
```

### 3. Run with --headed --slowmo

```bash
# See what's happening in real browser
PYTHONPATH=. pytest tests/e2e/your_test.py -v --headed --slowmo 1000
```

### 4. Use Playwright Inspector

```bash
# Pause execution and inspect state
PWDEBUG=1 PYTHONPATH=. pytest tests/e2e/your_test.py -v
```

### 5. Check Fixture Data

```python
def test_something(page, tournament_with_session):
    import json
    print(json.dumps(tournament_with_session, indent=2, default=str))
    # See exactly what fixture created
```

---

## ✅ Checklist for New E2E Test

Before considering your E2E test "done":

- [ ] Uses fixture from `tests/e2e/fixtures.py`
- [ ] Creates test data via API (not manual UI)
- [ ] Cleanup happens automatically (via fixture teardown)
- [ ] Login flow is explicit and role-appropriate
- [ ] Navigation steps are clear and commented
- [ ] Assertions use `expect()` or explicit `assert`
- [ ] Screenshots saved for key states
- [ ] Print statements show test progress
- [ ] Test can run in isolation (`pytest tests/e2e/test_X.py::test_Y`)
- [ ] Test passes when run multiple times (no state pollution)
- [ ] Docstring explains WHAT is tested and WHY

---

## 🎯 Reference Implementation

**ALWAYS refer to:** `tests/e2e/test_tournament_attendance_complete.py`

This file demonstrates:
- ✅ Complete fixture usage
- ✅ Proper assertions
- ✅ Debug aids
- ✅ Clear structure
- ✅ Role-based testing

**Copy this file as a starting point for new tests!**

---

## 📚 Further Reading

- [Playwright Best Practices](https://playwright.dev/python/docs/best-practices)
- [Pytest Fixtures Guide](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- Backend test fixtures: `tests/conftest.py` (similar patterns)

---

## 🚀 Quick Start for New Developer

1. **Read reference test:**
   ```bash
   cat tests/e2e/test_tournament_attendance_complete.py
   ```

2. **Run reference test:**
   ```bash
   source venv/bin/activate
   PYTHONPATH=. pytest tests/e2e/test_tournament_attendance_complete.py -v --headed --slowmo 500
   ```

3. **Copy and modify:**
   ```bash
   cp tests/e2e/test_tournament_attendance_complete.py tests/e2e/test_your_feature.py
   # Edit test_your_feature.py
   ```

4. **Add fixtures if needed:**
   ```python
   # In tests/e2e/fixtures.py
   @pytest.fixture
   def your_custom_setup(...):
       # Create data
       yield data
       # Cleanup
   ```

5. **Run your test:**
   ```bash
   PYTHONPATH=. pytest tests/e2e/test_your_feature.py -v
   ```

---

**Questions? Check the reference implementation first!**
**`tests/e2e/test_tournament_attendance_complete.py`**
