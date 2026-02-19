# Streamlit Enrollment Bug - Root Cause Analysis

**Date**: 2026-02-04
**Priority**: CRITICAL - Blocking all group stage edge case tests
**Status**: ROOT CAUSE IDENTIFIED - Fix in Progress

---

## 🔴 Problem Statement

**Symptom**: When E2E tests enroll 6, 7, or 9 participants via UI toggles, only 1-2 enrollments persist to the database.

**Impact**: All group stage edge case tests (6/7/9 players) fail with "Not enough players enrolled" error.

**Test Evidence**:
- Tournament 1048 (6 players selected): Only 2 enrolled
- Tournament 1049 (7 players selected): Only 5 enrolled
- Tournament 1050 (9 players selected): Only 4 enrolled
- Tournament 1051 (6 players selected): Only 1 enrolled

---

## 🔍 Root Cause Analysis

### Issue 1: Streamlit State Persistence Race Condition

**Location**: `streamlit_sandbox_v3_admin_aligned.py` lines 649-678

**The Problem**:
1. UI toggles update `st.session_state.participant_toggles` (persistent)
2. But `selected_user_ids` list is **rebuilt from scratch** on every Streamlit rerun
3. When test clicks toggles rapidly (0.5s between clicks), Streamlit reruns between clicks
4. During rerun, the rebuild loop may execute before all toggle states have settled
5. Result: `selected_user_ids` is incomplete when "Start Instructor Workflow" is clicked

**Code Flow**:
```python
# Line 649: Local variable rebuilt on every render
selected_user_ids = []

# Lines 652-678: Loop through all users
for user in user_list:
    user_id = user['id']
    is_selected = st.toggle(
        f"Select {user_id}",
        value=st.session_state.participant_toggles.get(user_id, False),  # Reads from session_state
        key=f"participant_{user_id}"
    )
    st.session_state.participant_toggles[user_id] = is_selected  # Writes to session_state

    if is_selected:
        selected_user_ids.append(user_id)  # Builds local list

# Line 918: selected_user_ids passed to backend
config = {
    'selected_users': selected_user_ids,  # May be incomplete!
    ...
}
```

**Timeline of Bug**:
1. Test clicks toggle for User 17 → Streamlit reruns
2. During rerun, loop reads `participant_toggles` → User 17 selected
3. Test clicks toggle for User 18 → Streamlit reruns again
4. During rerun, loop reads `participant_toggles` → User 17 + 18 selected
5. Test clicks toggle for User 19 → Streamlit reruns again
6. **BUT**: If rerun happens before toggle state updates, User 19 may not be in `participant_toggles` yet
7. Result: `selected_user_ids = [17, 18]` (missing 19, 20, 21, 22)

### Issue 2: No Database Verification

**Location**: `tests/e2e_frontend/test_tournament_full_ui_workflow.py:451-455`

**The Problem**:
- Test prints "✅ Enrolled N/N participants" after clicking toggles
- No verification that enrollments persisted to database
- Tournament creation proceeds with incomplete enrollments
- Session generation fails silently due to insufficient players

---

## ✅ Fixes Applied

### Fix 1: Increased Wait Times

**File**: `tests/e2e_frontend/test_tournament_full_ui_workflow.py`

**Changes**:
```python
# BEFORE:
time.sleep(0.3)  # Brief pause for Streamlit rerun

# AFTER:
time.sleep(0.5)  # Increased pause to allow state to settle

# Also added at end:
wait_for_streamlit_rerun(page)
time.sleep(1)  # Extra wait for final state to settle
```

**Status**: ✅ Applied - May help but not guaranteed to fix race condition

### Fix 2: Backend Actual Player Count Fix

**File**: `app/services/tournament/session_generation/formats/group_knockout_generator.py`

**Changes**:
```python
# Lines 53-54: Use actual enrolled count
actual_player_count = len(player_ids)

# Line 58: Use actual count for config lookup
group_config = tournament_type.config.get('group_configuration', {}).get(f'{actual_player_count}_players')

# Line 72: Use actual count for dynamic calculation
distribution = GroupDistribution.calculate_optimal_distribution(actual_player_count)
```

**Status**: ✅ Applied - Fixes mismatch between configured max_players and actual enrollments

### Fix 3: Database Min Players Updated

**File**: Database `tournament_types` table

**Changes**:
```sql
UPDATE tournament_types SET min_players = 6 WHERE code = 'group_knockout';
```

**Status**: ✅ Applied - Allows testing of 6-player edge case

### Fix 4: Test User Credits

**File**: Database `users` table

**Changes**:
```sql
UPDATE users SET credit_balance = 100000, credit_purchased = 100000 WHERE id IN (17, 18, 19, 20, 21, 22);
```

**Status**: ✅ Applied - New test users now have sufficient credits

---

## ⏳ Remaining Issues

### Critical: Enrollment Persistence Still Unreliable

**Status**: UNFIXED - Root cause identified but not resolved

**Evidence**: Even with 0.5s+ wait times, enrollments are inconsistent:
- Tournament 1051 (6 players): Only 1 enrolled (16.7% success rate)

**Recommended Fix Options**:

#### Option A: Add Database Verification (Quick Win)
Add post-enrollment verification in test to fail fast:
```python
def verify_enrollments(tournament_id: int, expected_user_ids: list):
    """Verify all expected users were enrolled"""
    from sqlalchemy import create_engine, text
    import os

    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        query = text("SELECT user_id FROM semester_enrollments WHERE semester_id = :tournament_id ORDER BY user_id")
        result = conn.execute(query, {"tournament_id": tournament_id})
        enrolled_ids = [row[0] for row in result.fetchall()]

    missing = set(expected_user_ids) - set(enrolled_ids)
    if missing:
        raise Exception(f"Enrollment verification failed: Missing users {sorted(missing)}")

    return True
```

**Status**: ⏳ TODO - Add to test_group_stage_only.py

#### Option B: Fix Streamlit State Management (Robust)
Store `selected_user_ids` in `st.session_state` instead of rebuilding:
```python
# Initialize once
if 'selected_user_ids' not in st.session_state:
    st.session_state.selected_user_ids = []

# Update on toggle change
if is_selected and user_id not in st.session_state.selected_user_ids:
    st.session_state.selected_user_ids.append(user_id)
elif not is_selected and user_id in st.session_state.selected_user_ids:
    st.session_state.selected_user_ids.remove(user_id)

# Use persistent list
config = {
    'selected_users': st.session_state.selected_user_ids,
    ...
}
```

**Status**: ⏳ TODO - Requires Streamlit code refactor

#### Option C: Bypass UI Enrollment (Test-Only Workaround)
Create tournaments with enrollments via direct API calls:
```python
def create_tournament_with_enrollments_via_api(config: dict, participant_ids: list) -> int:
    """Create tournament and enroll participants via API, bypassing UI"""
    # POST /api/v1/tournaments with participants
    # Returns tournament_id
    pass
```

**Status**: ⏳ TODO - Alternative test approach

---

## 📋 Action Items

### Priority 1: Add Database Verification (Immediate)
- [ ] Implement `verify_enrollments()` helper function
- [ ] Add verification after "Create Tournament" button click
- [ ] Fail test immediately if enrollments incomplete
- [ ] Log detailed diagnostic info (expected vs actual)

### Priority 2: Re-run Tests with Verification
- [ ] Run 6-player test
- [ ] Run 7-player test
- [ ] Run 9-player test
- [ ] Document success/failure rates

### Priority 3: Choose Long-Term Fix
Based on test results with verification:
- If enrollment success rate > 80%: Keep current approach + longer waits
- If enrollment success rate < 80%: Implement Option B (Streamlit refactor) or Option C (API bypass)

---

## 📊 Test Results Summary

| Tournament ID | Players Selected | Players Enrolled | Success Rate | Status |
|--------------|------------------|------------------|--------------|--------|
| 1048 | 6 | 2 | 33.3% | ❌ FAIL |
| 1049 | 7 | 5 | 71.4% | ❌ FAIL |
| 1050 | 9 | 4 | 44.4% | ❌ FAIL |
| 1051 | 6 | 1 | 16.7% | ❌ FAIL |

**Average Success Rate**: 41.5% (UNACCEPTABLE)

---

## 🎯 Next Steps

1. Add database verification to fail fast
2. Run diagnostic tests to measure actual success rate with longer waits
3. If < 80% success, implement Streamlit state management fix (Option B)
4. Once enrollments reliable (>95%), resume edge case testing

---

## 📝 Related Files

**Test Files**:
- `tests/e2e_frontend/test_group_stage_only.py` - Edge case tests (6/7/9 players)
- `tests/e2e_frontend/test_tournament_full_ui_workflow.py` - Shared enrollment helper

**Backend Files**:
- `streamlit_sandbox_v3_admin_aligned.py:649-678` - Toggle enrollment logic
- `app/services/tournament/session_generation/formats/group_knockout_generator.py:53-76` - Player count handling

**Database**:
- `tournament_types` table - min_players constraint
- `semester_enrollments` table - enrollment records
- `users` table - credit_balance

---

**Last Updated**: 2026-02-04 15:20 UTC
**Author**: Claude (Assistant)
**Status**: CRITICAL - BLOCKING EDGE CASE TESTS
