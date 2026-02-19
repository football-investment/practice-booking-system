# Frontend Testing Guide - Tournament vs Regular Session UI

**Date:** 2026-01-03
**Phase:** 2 - Frontend Component Tests
**Status:** ⚠️ Manual Testing Required

---

## Overview

This guide explains how to test the CRITICAL requirement:
- **Tournament sessions**: Show ONLY 2 attendance buttons (Present, Absent)
- **Regular sessions**: Show ALL 4 attendance buttons (Present, Absent, Late, Excused)

---

## Why Streamlit AppTest is Limited

Streamlit AppTest is designed for **full Streamlit apps**, not standalone component files. Our components:
- Use relative imports (`from api_helpers import ...`)
- Require authentication tokens
- Need database connections
- Depend on session state from parent app

**Alternative approach**: Manual UI testing + Backend validation (already done in Phase 1)

---

## 🔴 CRITICAL Manual Test Checklist

### Test 1: Tournament Session Shows 2 Buttons ⭐

**Precondition:**
1. Create a tournament semester (Admin panel → Tournaments)
2. Add at least 1 tournament session
3. Have at least 2 students enrolled
4. Login as instructor assigned to tournament

**Steps:**
1. Navigate to: **Instructor Dashboard → Tournament Check-in**
2. Select the tournament session
3. Proceed to **Step 2: Mark Attendance**

**Expected Result:** ✅
- **ONLY 2 buttons** per student:
  - ✅ Present
  - ❌ Absent
- **NO Late button** ❌
- **NO Excused button** ❌

**Visual Reference:**
```
Student Name                  [✅ Present]  [❌ Absent]
                              ^-- ONLY 2 BUTTONS --^
```

**Metrics Section:**
- Should show **3 metrics**: Present, Absent, Pending
- Should **NOT show**: Late, Excused

---

### Test 2: Regular Session Shows 4 Buttons

**Precondition:**
1. Create a regular semester (Admin panel → Semesters)
2. Add a regular session (NOT tournament)
3. Have at least 2 students booked
4. Login as instructor

**Steps:**
1. Navigate to: **Instructor Dashboard → Session Check-in**
2. Select the regular session
3. Proceed to **Step 2: Mark Attendance**

**Expected Result:** ✅
- **ALL 4 buttons** per student:
  - ✅ Present
  - ❌ Absent
  - ⏰ Late
  - 🎫 Excused

**Visual Reference:**
```
Student Name    [✅ Present]  [❌ Absent]  [⏰ Late]  [🎫 Excused]
                ^------------- ALL 4 BUTTONS ------------^
```

**Metrics Section:**
- Should show **5 metrics**: Present, Absent, Late, Excused, Pending

---

### Test 3: Backend Rejects Invalid Status

**Precondition:**
1. Have a tournament session created
2. Student is booked

**Steps:**
1. Open browser DevTools → Network tab
2. Mark student as Present (should work)
3. Try to manually send API request with status="late"

**Expected Result:** ✅
- API returns **400 Bad Request**
- Error message: "Tournaments only support 'present' or 'absent' attendance"

**How to test manually (curl):**
```bash
curl -X POST "http://localhost:8000/api/v1/attendance/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": 123,
    "user_id": 456,
    "session_id": 789,
    "status": "late"
  }'
```

**Expected response:**
```json
{
  "detail": "Tournaments only support 'present' or 'absent' attendance. Received: 'late'"
}
```

---

## 🟡 Visual Comparison Test

Take screenshots of both UIs and compare side-by-side:

| Tournament Check-in | Regular Session Check-in |
|---------------------|--------------------------|
| 2 buttons per student | 4 buttons per student |
| 3 metrics (Present, Absent, Pending) | 5 metrics (Present, Absent, Late, Excused, Pending) |
| "Tournament Mode" info banner | No special banner |
| Game type displayed (Final, Semifinal) | Session type displayed (on_site, hybrid) |

---

## 🟢 Automated Backend Validation (Already Done ✅)

Phase 1 completed:
- ✅ **73 tests passing** (63 unit + 10 integration)
- ✅ API validation: `/api/v1/attendance/` rejects late/excused for tournaments
- ✅ Service layer validation: `validate_tournament_attendance_status()`
- ✅ Database model: `AttendanceStatus` enum

**Run backend tests:**
```bash
pytest -m tournament -v
```

---

## 📋 Frontend Test Plan (Future Enhancement)

### Option 1: Playwright E2E Tests (Recommended)

**Install:**
```bash
pip install pytest-playwright
playwright install
```

**Test file:** `tests/e2e/test_tournament_checkin_e2e.py`

**Example:**
```python
def test_tournament_shows_2_buttons(page):
    # Login as instructor
    page.goto("http://localhost:8501")
    page.fill("#email", "instructor@lfa.com")
    page.fill("#password", "instructor123")
    page.click("button:has-text('Login')")

    # Navigate to tournament check-in
    page.click("text=Tournament Check-in")

    # Select session
    page.click("button:has-text('Select ➡️')")

    # Count buttons
    present_buttons = page.locator("button:has-text('✅ Present')").count()
    absent_buttons = page.locator("button:has-text('❌ Absent')").count()
    late_buttons = page.locator("button:has-text('⏰ Late')").count()
    excused_buttons = page.locator("button:has-text('🎫 Excused')").count()

    assert present_buttons > 0
    assert absent_buttons > 0
    assert late_buttons == 0  # CRITICAL
    assert excused_buttons == 0  # CRITICAL
```

### Option 2: Streamlit App Testing Framework (Beta)

**Note:** Streamlit's testing framework is still evolving. Current limitations:
- Requires full app context
- Cannot test isolated components easily
- Best for integration tests of entire pages

### Option 3: Component-Level Unit Tests (Current)

**Test files created:**
- ✅ `tests/component/tournament/test_tournament_checkin_ui.py`
- ✅ `tests/component/sessions/test_session_checkin_ui.py`

**Status:** Created but cannot run without full Streamlit app context

**To make these work:**
- Extract business logic from UI components
- Create testable helper functions
- Mock Streamlit primitives

---

## 🎯 Current Test Coverage Summary

### Phase 1 (Backend) ✅ COMPLETE
- ✅ 73 tests passing (100%)
- ✅ API endpoint validation
- ✅ Service layer validation
- ✅ Database models

### Phase 2 (Frontend) ⚠️ MANUAL TESTING REQUIRED
- ✅ Test plans created
- ✅ Test files scaffolded
- ⏳ **ACTION REQUIRED**: Manual UI testing checklist (above)
- ⏳ **FUTURE**: Playwright E2E tests

---

## 🚀 Quick Test Commands

### Backend Tests (Automated)
```bash
# All tournament tests
pytest -m tournament

# Validation tests only
pytest tests/unit/tournament/test_validation.py -v

# Integration tests
pytest tests/integration/tournament/ -v

# All Phase 1 tests
pytest tests/unit/tournament/ tests/integration/tournament/ -v
```

### Frontend Manual Tests
1. Start app: `streamlit run streamlit_app/main.py`
2. Follow manual checklist above
3. Take screenshots for documentation

### API Tests (curl)
```bash
# Test tournament attendance rejection
curl -X POST "http://localhost:8000/api/v1/attendance/" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"booking_id": 1, "user_id": 2, "session_id": 3, "status": "late"}'

# Expected: 400 Bad Request
```

---

## 📊 Success Criteria

### Backend (Done ✅)
- [x] API rejects late/excused for tournaments
- [x] Service layer validates correctly
- [x] 73 tests passing
- [x] 100% coverage of critical paths

### Frontend (To Do ⏳)
- [ ] Tournament UI shows 2 buttons (manual verification)
- [ ] Regular UI shows 4 buttons (manual verification)
- [ ] Visual differences clear and obvious
- [ ] No UI bugs or glitches

---

## 🐛 Known Issues & Limitations

### Streamlit AppTest Challenges
1. **Component Isolation**: Cannot test components in isolation easily
2. **Import Dependencies**: Relative imports fail outside app context
3. **Authentication**: Token management in tests is complex
4. **Database**: In-memory DB doesn't work with Streamlit session state

### Recommended Solution
- **Phase 2 (Current)**: Manual testing checklist
- **Phase 3 (Future)**: Playwright E2E tests for full user flows

---

## 📝 Test Report Template

When conducting manual tests, fill out this report:

```
## Tournament vs Regular Session UI Test Report

**Date:** YYYY-MM-DD
**Tester:** Name
**App Version:** X.X.X

### Test 1: Tournament Session (2 Buttons)
- [ ] Tournament UI loaded successfully
- [ ] Only 2 buttons visible per student
- [ ] No Late button present
- [ ] No Excused button present
- [ ] 3 metrics displayed (Present, Absent, Pending)
- **Screenshot:** [Attach]
- **Status:** ✅ PASS / ❌ FAIL

### Test 2: Regular Session (4 Buttons)
- [ ] Regular UI loaded successfully
- [ ] All 4 buttons visible per student
- [ ] Late button present
- [ ] Excused button present
- [ ] 5 metrics displayed
- **Screenshot:** [Attach]
- **Status:** ✅ PASS / ❌ FAIL

### Test 3: Backend Validation
- [ ] API rejected "late" status for tournament
- [ ] Error message correct
- **API Response:** [Paste]
- **Status:** ✅ PASS / ❌ FAIL

### Summary
- **Overall Result:** ✅ PASS / ❌ FAIL
- **Issues Found:** [List any issues]
- **Notes:** [Additional observations]
```

---

## 🔗 Related Documentation

- [Phase 1 Completion Summary](./PHASE_1_COMPLETION_SUMMARY.md) - Backend tests
- [Tournament Test Guide](../tests/README.md) - Unit/integration tests
- [Plan File](../.claude/plans/velvet-floating-mango.md) - Original refactoring plan

---

**Next Steps:**
1. ⏳ Conduct manual UI tests (checklist above)
2. ⏳ Document results with screenshots
3. ⏳ Consider Playwright E2E tests for Phase 3

**Prepared by:** Claude Sonnet 4.5
**Generated with:** [Claude Code](https://claude.com/claude-code)
