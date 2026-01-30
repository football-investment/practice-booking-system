# Playwright E2E Test Plan - Continue Tournament Fix

## 🎯 Test Scenarios

| Test # | Scenario | Tournament Type | Expected Behavior | Verifies |
|--------|----------|----------------|-------------------|----------|
| **1** | Home → Open History → Select Tournament → Continue | DRAFT | Navigate to workflow, no crash | reward_config None handling |
| **2** | Home → Open History → Select Tournament → Continue | IN_PROGRESS | Navigate to workflow, no crash | reward_config None handling |
| **3** | Home → Open History → Select Tournament → View Tabs | ANY | Tabs load, no crash on tab switch | Leaderboard/Results/Rewards tabs |
| **4** | Home → Open History → Multiple Tournament Selection | MULTIPLE | Select 3+ different tournaments | Dropdown state loading |
| **5** | Home → Open History → Check Error Messages | ANY | No AttributeError or NoneType errors visible | Overall error detection |

---

## 📋 Detailed Test Cases

### Test 1: DRAFT Tournament - Continue Setup
**File**: `test_01_draft_continue.py`

**Steps**:
1. Navigate to http://localhost:8501
2. Wait for Home screen load
3. Click "📊 Open History" button
4. Wait for tournament list
5. Find and select DRAFT tournament from dropdown
6. Click "▶️ Continue Setup" button
7. **Assert**: No error message appears
8. **Assert**: Navigation to workflow step occurs

**Expected Tournament**: Any tournament with status `DRAFT`

---

### Test 2: IN_PROGRESS Tournament - Continue Tournament
**File**: `test_02_in_progress_continue.py`

**Steps**:
1. Navigate to http://localhost:8501
2. Wait for Home screen load
3. Click "📊 Open History" button
4. Wait for tournament list
5. Find and select IN_PROGRESS tournament from dropdown
6. Click "▶️ Continue Tournament" button
7. **Assert**: No error message appears
8. **Assert**: Navigation to workflow step occurs (Step 2 or Step 6)

**Expected Tournament**: Tournament with status `IN_PROGRESS`, `reward_config = None`

---

### Test 3: Tournament History Tabs Navigation
**File**: `test_03_history_tabs.py`

**Steps**:
1. Navigate to http://localhost:8501
2. Click "📊 Open History" button
3. Select any tournament
4. Click "📊 Leaderboard" tab
5. **Assert**: No crash
6. Click "🎯 Match Results" tab
7. **Assert**: No crash, date fields display correctly
8. Click "🎁 Rewards" tab
9. **Assert**: No crash

**Expected Tournament**: Any IN_PROGRESS or REWARDS_DISTRIBUTED tournament

---

### Test 4: Multiple Tournament Selection
**File**: `test_04_multiple_selection.py`

**Steps**:
1. Navigate to http://localhost:8501
2. Click "📊 Open History" button
3. Select Tournament A
4. Wait for detail load
5. **Assert**: No error
6. Select Tournament B
7. Wait for detail load
8. **Assert**: No error
9. Select Tournament C
10. Wait for detail load
11. **Assert**: No error

**Expected**: Rapidly switching between tournaments doesn't cause crash

---

### Test 5: Error Detection Scan
**File**: `test_05_error_scan.py`

**Steps**:
1. Navigate to http://localhost:8501
2. Click "📊 Open History" button
3. For each tournament in dropdown:
   - Select tournament
   - Wait 2 seconds
   - Scan page for error messages
   - **Assert**: No "Error:" text
   - **Assert**: No "'NoneType' object has no attribute" text
   - **Assert**: No red error boxes

**Expected**: Zero errors across all tournaments

---

## 🎬 Test Execution Plan

### Phase 1: Individual Tests (Headed Mode)
Run each test separately to visually verify:

```bash
# Test 1: DRAFT
python test_01_draft_continue.py

# Test 2: IN_PROGRESS
python test_02_in_progress_continue.py

# Test 3: Tabs
python test_03_history_tabs.py

# Test 4: Multiple Selection
python test_04_multiple_selection.py

# Test 5: Error Scan
python test_05_error_scan.py
```

### Phase 2: Full Suite (Headed Mode)
Run all tests together:

```bash
pytest tests_e2e/ --headed --slowmo=800 -v -s
```

### Phase 3: Headless Verification
Run all tests in headless mode for CI:

```bash
pytest tests_e2e/ -v -s
```

---

## ✅ Success Criteria

**All tests MUST pass with**:
- ✅ Zero crashes
- ✅ Zero "NoneType" errors
- ✅ Zero "AttributeError" messages
- ✅ All navigation transitions work
- ✅ All tabs load without errors
- ✅ Date fields display 'N/A' instead of crashing

---

## 📊 Tournament Selection Strategy

To ensure we test different scenarios:

1. **DRAFT Tournaments**: Target tournaments with `tournament_status = 'DRAFT'`
2. **IN_PROGRESS Tournaments**: Target tournaments with `tournament_status = 'IN_PROGRESS'`
3. **With None reward_config**: Specifically test Tournament ID 156, 174 (known to have None reward_config)
4. **With None final_standings**: Test IN_PROGRESS tournaments (final_standings exists as key but value is None)

---

## 🔍 What We're Testing

### Primary Fix Verification:
```python
# This pattern must NOT crash anymore:
"skills_to_test": [
    s['skill']
    for s in (tournament_detail.get('reward_config') or {}).get('skill_mappings', [])
    if s.get('enabled', True)
]
```

### Secondary Verifications:
- Date slicing: `(obj.get('date_start') or 'N/A')[:10] if obj.get('date_start') else 'N/A'`
- Leaderboard None handling
- Sessions None handling
- Chained `.get()` safety

---

**Generated**: 2026-01-29
**Purpose**: Comprehensive E2E testing for Continue Tournament fix
