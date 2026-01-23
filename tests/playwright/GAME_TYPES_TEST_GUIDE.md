# 🎮 Tournament Game Types - Playwright Test Guide

**Test File**: `test_tournament_game_types.py`
**Browser**: Firefox (headed mode)
**Test Count**: 5 tests (4 individual + 1 comprehensive)

---

## 📋 Test Overview

This test suite validates all 4 game types implemented in the tournament system:

1. **League Match** (LEAGUE category)
2. **King of the Court** (SPECIAL category)
3. **Group Stage + Placement Matches** (GROUP_STAGE category)
4. **Elimination Bracket** (KNOCKOUT category)

---

## 🧪 Test Cases

### Test 1: `test_game_type_league_match`

**Validates**: League Match game type

**Tournament Settings:**
- Max Players: 20
- Price: 300 credits
- Assignment Type: APPLICATION_BASED

**Game Settings:**
- Type: League Match
- Title: "Round 1 - League Match"
- Duration: 5 minutes

**Verification:**
- ✅ Tournament created successfully
- ✅ Game added successfully
- ✅ Game appears in list with correct type

---

### Test 2: `test_game_type_king_of_court`

**Validates**: King of the Court game type

**Tournament Settings:**
- Max Players: 12
- Price: 250 credits
- Assignment Type: OPEN_ASSIGNMENT

**Game Settings:**
- Type: King of the Court
- Title: "Challenge Round 1"
- Duration: 3 minutes

**Verification:**
- ✅ Tournament created successfully
- ✅ Game added successfully
- ✅ Game appears in list with correct type

---

### Test 3: `test_game_type_group_stage_placement`

**Validates**: Group Stage + Placement Matches game type

**Tournament Settings:**
- Max Players: 16
- Price: 400 credits
- Assignment Type: APPLICATION_BASED

**Game Settings:**
- Type: Group Stage + Placement Matches
- Title: "Group A - Match 1"
- Duration: 5 minutes

**Verification:**
- ✅ Tournament created successfully
- ✅ Game added successfully
- ✅ Game appears in list with correct type

---

### Test 4: `test_game_type_elimination_bracket`

**Validates**: Elimination Bracket game type

**Tournament Settings:**
- Max Players: 8
- Price: 500 credits
- Assignment Type: OPEN_ASSIGNMENT

**Game Settings:**
- Type: Elimination Bracket
- Title: "Quarterfinal 1"
- Duration: 3 minutes

**Verification:**
- ✅ Tournament created successfully
- ✅ Game added successfully
- ✅ Game appears in list with correct type

---

### Test 5: `test_all_game_types_comprehensive`

**Validates**: All 4 game types in a single tournament

**Tournament Settings:**
- Max Players: 24
- Price: 350 credits
- Assignment Type: APPLICATION_BASED

**Games Added:**
1. League Match - "Round 1 - League" (5 min)
2. King of the Court - "Challenge Round" (3 min)
3. Group Stage + Placement - "Group Stage A" (5 min)
4. Elimination Bracket - "Quarterfinal" (3 min)

**Verification:**
- ✅ Tournament created successfully
- ✅ All 4 games added successfully
- ✅ All games appear in list with correct types

---

## 🚀 How to Run Tests

### Prerequisites

1. **Start Backend**
   ```bash
   cd /path/to/practice_booking_system
   source venv/bin/activate
   DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start Streamlit**
   ```bash
   cd /path/to/practice_booking_system
   source venv/bin/activate
   streamlit run streamlit_app/Home.py --server.port 8501
   ```

3. **Database Snapshot**
   ```bash
   cd tests/playwright
   ./snapshot_manager.sh restore after_onboarding
   ```

---

### Run All Game Type Tests

```bash
cd /path/to/practice_booking_system
source venv/bin/activate

pytest tests/playwright/test_tournament_game_types.py \
  --headed \
  --browser firefox \
  --slowmo 1000 \
  -v -s
```

---

### Run Individual Tests

**Test 1: League Match**
```bash
pytest tests/playwright/test_tournament_game_types.py::test_game_type_league_match \
  --headed --browser firefox --slowmo 1000 -v -s
```

**Test 2: King of the Court**
```bash
pytest tests/playwright/test_tournament_game_types.py::test_game_type_king_of_court \
  --headed --browser firefox --slowmo 1000 -v -s
```

**Test 3: Group Stage + Placement**
```bash
pytest tests/playwright/test_tournament_game_types.py::test_game_type_group_stage_placement \
  --headed --browser firefox --slowmo 1000 -v -s
```

**Test 4: Elimination Bracket**
```bash
pytest tests/playwright/test_tournament_game_types.py::test_game_type_elimination_bracket \
  --headed --browser firefox --slowmo 1000 -v -s
```

**Test 5: Comprehensive (All Types)**
```bash
pytest tests/playwright/test_tournament_game_types.py::test_all_game_types_comprehensive \
  --headed --browser firefox --slowmo 1000 -v -s
```

---

## 📸 Screenshots

Screenshots are automatically taken at key points:
- Admin logged in
- Tournament created
- Manage Games page loaded
- Each game added
- Final verification

**Location**: `tests/e2e/screenshots/`

**Naming Convention**: `{action}_{timestamp}.png`

---

## 🐛 Troubleshooting

### Issue: Selector timeout on "Add New Game" button

**Solution**: Ensure tournament is selected in "Manage Games" tab
```python
page.get_by_text("Select Tournament").click()
page.get_by_role("option", name=tournament_name).click()
```

---

### Issue: Game Type dropdown not visible

**Solution**: Verify game type is in GAME_TYPE_OPTIONS list
```python
# In streamlit_app/components/admin/tournaments_tab.py
GAME_TYPE_OPTIONS = [
    "League Match",
    "King of the Court",
    "Group Stage + Placement Matches",
    "Elimination Bracket"
]
```

---

### Issue: Tournament creation fails

**Solution**: Check database constraints
- Location and Campus must exist
- Date must be in the future
- Max players > 0
- Price >= 0

---

## ✅ Expected Results

### Success Criteria

**All 5 tests pass:**
```
tests/playwright/test_tournament_game_types.py::test_game_type_league_match PASSED
tests/playwright/test_tournament_game_types.py::test_game_type_king_of_court PASSED
tests/playwright/test_tournament_game_types.py::test_game_type_group_stage_placement PASSED
tests/playwright/test_tournament_game_types.py::test_game_type_elimination_bracket PASSED
tests/playwright/test_tournament_game_types.py::test_all_game_types_comprehensive PASSED

============================= 5 passed in XXs =============================
```

---

## 📊 Test Coverage

| Game Type | Tournament Settings | Game Settings | Verification |
|-----------|---------------------|---------------|--------------|
| League Match | ✅ | ✅ | ✅ |
| King of the Court | ✅ | ✅ | ✅ |
| Group Stage + Placement | ✅ | ✅ | ✅ |
| Elimination Bracket | ✅ | ✅ | ✅ |

**Coverage**: 100% of game types

---

## 🔄 Test Maintenance

### Adding New Game Types

When adding a new game type:

1. **Update code**:
   ```python
   # streamlit_app/components/admin/tournaments_tab.py
   GAME_TYPE_OPTIONS.append("NEW_GAME_TYPE")
   ```

2. **Add test**:
   ```python
   # tests/playwright/test_tournament_game_types.py
   def test_game_type_new_type(page: Page):
       # Follow existing test structure
       pass
   ```

3. **Update documentation**:
   - Add test case to this file
   - Update GAME_TYPES_SPECIFICATION.md
   - Update test coverage table

---

## 📚 Related Documentation

- [Game Types Specification](../../docs/workflows/GAME_TYPES_SPECIFICATION.md)
- [Game Types Implementation Summary](../../docs/workflows/GAME_TYPES_IMPLEMENTATION_SUMMARY.md)
- [Playwright Tests README](./README.md)

---

**Last Updated**: 2026-01-12
**Test Status**: ✅ Ready for Execution
