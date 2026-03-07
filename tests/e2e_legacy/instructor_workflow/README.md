# Instructor Workflow E2E Tests

**Purpose:** End-to-end validation of the complete instructor workflow

**Status:** ✅ Active, part of E2E test suite

---

## 📋 Overview

These tests validate the instructor's complete workflow from tournament creation to reward distribution, ensuring all steps work correctly together.

---

## 🧪 Tests

### test_instructor_workflow_e2e.py
**Purpose:** Complete instructor workflow validation

**Workflow Steps:**
1. **Create Tournament** - Create a new tournament via UI
2. **Manage Sessions** - Generate and manage tournament sessions
3. **Track Attendance** - Mark participant attendance
4. **Enter Results** - Submit match results
5. **View Leaderboard** - Verify tournament rankings
6. **Distribute Rewards** - Distribute rewards to participants
7. **View Rewards** - Verify distributed rewards

**Run:**
```bash
# Run instructor workflow test
pytest tests/e2e/instructor_workflow/ -v

# Run with markers
pytest -m instructor_workflow -v

# Run in headless mode
pytest tests/e2e/instructor_workflow/ -v --headed=false
```

---

## 🎯 Test Scenarios

### Happy Path
- Complete workflow from start to finish
- All steps execute successfully
- Rewards distributed correctly

### Edge Cases
- Tournament with minimum participants
- Tournament with maximum participants
- Multiple session types

---

## ⚙️ Requirements

**Running Services:**
- Streamlit app on `http://localhost:8501`
- FastAPI backend on `http://localhost:8000`
- PostgreSQL database configured

**Browser:**
- Firefox (default in headless mode)
- Can be changed in `tests/e2e/conftest.py`

---

## 📊 Test Data

**Participants:**
- Minimum: 4 participants (for head-to-head)
- Typical: 7-8 participants (for group/knockout)
- Maximum: Varies by tournament type

**Tournament Types Covered:**
- GROUP_AND_KNOCKOUT
- HEAD_TO_HEAD
- INDIVIDUAL_RANKING

---

## 🔧 Debugging

### View Browser (Headed Mode)
```bash
# Temporarily edit tests/e2e/conftest.py:
# Change: "headless": True → "headless": False
pytest tests/e2e/instructor_workflow/ -v
```

### Slow Down Execution
```bash
# Edit tests/e2e/conftest.py:
# Change: "slow_mo": 0 → "slow_mo": 500
pytest tests/e2e/instructor_workflow/ -v
```

### Capture Screenshots
```python
# Add to test:
page.screenshot(path="debug_screenshot.png")
```

---

## 📈 Success Criteria

- ✅ Tournament created successfully
- ✅ Sessions generated
- ✅ Attendance tracked
- ✅ Results submitted
- ✅ Leaderboard displays correctly
- ✅ Rewards distributed
- ✅ Rewards viewable

---

## 📚 See Also

- [tests/e2e/golden_path/README.md](../golden_path/README.md) - Golden Path test
- [tests/e2e_frontend/](../../e2e_frontend/) - Frontend E2E tests
- [tests/NAVIGATION_GUIDE.md](../../NAVIGATION_GUIDE.md) - Test navigation

---

**Last Updated:** 2026-02-08
**Status:** ✅ Active, E2E test suite
