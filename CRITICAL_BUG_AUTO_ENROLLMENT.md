# 🚨 CRITICAL BUG: Auto-Enrollment Without User Selection

**Discovered**: 2026-02-03
**Severity**: CRITICAL
**Status**: UNDER INVESTIGATION

---

## Problem Summary

Tournaments are being executed with **0 participants enrolled** in `tournament_participations` table, YET:
- Sessions are created with 8 users
- Results are submitted for these users
- Rewards (XP, credits, skill points) are distributed
- Leaderboards show rankings

**This means the system IGNORES the UI participant selection entirely!**

---

## Evidence

### Database Query Results

```sql
SELECT
    s.id,
    s.name,
    (SELECT COUNT(*) FROM tournament_participations tp WHERE tp.semester_id = s.id) as participant_count,
    (SELECT COUNT(*) FROM xp_transactions xt WHERE xt.semester_id = s.id) as xp_tx,
    (SELECT array_agg(user_id) FROM xp_transactions xt WHERE xt.semester_id = s.id LIMIT 5) as users_who_got_xp
FROM semesters s
WHERE s.name LIKE 'UI-E2E%'
ORDER BY s.id DESC
LIMIT 3;
```

**Results**:
```
id  |                  name                  | participant_count | xp_tx |   users_who_got_xp
-----+----------------------------------------+-------------------+-------+-----------------------
 948 | UI-E2E-T4_Knockout_Ind_Time_1R-211655  |                 0 |     0 | (in progress)
 947 | UI-E2E-T3_League_Ind_Time_1R-211444    |                 0 |     8 | {6,7,13,14,15,4,5,16}
 946 | UI-E2E-T2_Knockout_Ind_Score_3R-211122 |                 0 |     8 | {5,6,7,13,14,15,4,16}
```

✅ **0 participants enrolled**
❌ **BUT 8 users received rewards!**

---

## Root Cause Analysis

### 1. **Hardcoded User Pool**

**File**: `app/services/sandbox_test_orchestrator.py` line 31

```python
# Test user pool (valid existing user IDs) with known baseline skills
TEST_USER_POOL = [4, 5, 6, 7, 13, 14, 15, 16]
```

### 2. **Auto-Enrollment Logic**

**File**: `app/services/sandbox_test_orchestrator.py` line 430-446

```python
def _enroll_participants(self, player_count: int) -> List[int]:
    """Enroll synthetic participants"""
    logger.info(f"👥 Enrolling {player_count} participants")

    # DEBUG: Log pool size vs requested count
    logger.info(f"🔍 DEBUG: TEST_USER_POOL size={len(TEST_USER_POOL)}, requested={player_count}")
    logger.info(f"🔍 DEBUG: TEST_USER_POOL={TEST_USER_POOL}")

    # Validate pool size
    if player_count > len(TEST_USER_POOL):
        raise ValueError(
            f"Cannot sample {player_count} users from pool of {len(TEST_USER_POOL)}. "
            f"Pool: {TEST_USER_POOL}"
        )

    # Select random users from test pool
    selected_users = random.sample(TEST_USER_POOL, player_count)  # ❌ BUG!
    logger.info(f"🔍 DEBUG: Selected users from pool: {selected_users}")
```

**The orchestrator ALWAYS uses TEST_USER_POOL, ignoring UI selections!**

### 3. **UI Participant Selection**

**File**: `streamlit_sandbox_v3_admin_aligned.py` line 620-656

```python
# Initialize session state for participant toggles
if "participant_toggles" not in st.session_state:
    loaded_participants = loaded_config.get('selected_users', [])
    st.session_state.participant_toggles = {
        user['id']: user['id'] in loaded_participants
        for user in user_list
    }

selected_user_ids = []

# Simple compact list with toggle switches
for user in user_list:
    user_id = user['id']
    user_email = user['email']
    user_name = user.get('name', 'N/A')
    user_role = user.get('role', 'N/A')

    col1, col2 = st.columns([5, 1])

    with col1:
        st.caption(f"{user_email} • {user_name} ({user_role})")

    with col2:
        # Toggle switch (on/off button)
        toggle_key = f"participant_{user_id}"
        is_selected = st.toggle(
            "",
            value=st.session_state.participant_toggles.get(user_id, False),
            key=toggle_key
        )
        st.session_state.participant_toggles[user_id] = is_selected

        if is_selected:
            selected_user_ids.append(user_id)

st.caption(f"✅ {len(selected_user_ids)} selected")
```

**UI collects `selected_user_ids`, BUT backend ignores it!**

---

## Impact

### 🔴 Production Risk

1. **Unauthorized Participation**:
   - Users who didn't sign up receive rewards
   - Tournament capacity limits ignored
   - Payment verification bypassed (if enrollment had costs)

2. **Data Integrity**:
   - `tournament_participations` table out of sync with actual participants
   - Leaderboard shows users who aren't officially enrolled
   - Reward distribution doesn't match enrollment records

3. **Business Logic Violation**:
   - UI selections are cosmetic only
   - No validation of participant eligibility
   - Admin cannot control who participates

### 🟡 Test Validity

All E2E tests so far have been running with **hardcoded participants**, not the UI-selected ones:
- 30+ tournaments created via UI
- All used TEST_USER_POOL [4, 5, 6, 7, 13, 14, 15, 16]
- **NONE respected UI participant selection**

---

## Investigation Questions

### Q1: Where is selected_user_ids sent to backend?

**Status**: Need to investigate

**Check**:
1. Streamlit form submission in `streamlit_sandbox_v3_admin_aligned.py`
2. API endpoint that receives tournament config
3. How config is stored and retrieved

### Q2: Does tournament creation API accept selected_users parameter?

**Status**: Need to investigate

**Check**:
1. API endpoint signature (e.g., `/api/v1/tournaments/create`)
2. Request payload schema
3. Whether `selected_users` is validated

### Q3: When does orchestrator get invoked?

**Status**: Need to investigate

**Check**:
1. Is orchestrator used for sandbox tournaments?
2. Is there a separate code path for UI-created tournaments?
3. Where is the disconnect between UI and orchestrator?

### Q4: Is tournament_participations ever populated?

**Status**: Need to investigate

**Check**:
1. Are there any tournaments with participant_count > 0?
2. What code path creates enrollment records?
3. Is enrollment a separate step or automatic?

---

## Proposed Fixes

### Option A: Pass selected_users to Orchestrator

**Modify**: `sandbox_test_orchestrator.py` line 430

```python
def _enroll_participants(self, player_count: int, selected_users: List[int] = None) -> List[int]:
    """Enroll participants (use provided list or fall back to test pool)"""

    if selected_users:
        # Use explicitly selected users from UI
        if len(selected_users) != player_count:
            raise ValueError(f"Selected {len(selected_users)} users, but tournament requires {player_count}")
        logger.info(f"👥 Using UI-selected users: {selected_users}")
        users_to_enroll = selected_users
    else:
        # Fall back to test pool for programmatic tests
        logger.info(f"👥 Using TEST_USER_POOL (no UI selection provided)")
        if player_count > len(TEST_USER_POOL):
            raise ValueError(f"Cannot sample {player_count} from pool of {len(TEST_USER_POOL)}")
        users_to_enroll = random.sample(TEST_USER_POOL, player_count)

    # ... rest of enrollment logic
```

### Option B: Create tournament_participations Records

**Add**: Enrollment step BEFORE session generation

```python
def _create_enrollment_records(self, tournament_id: int, selected_users: List[int]):
    """Create official enrollment records in tournament_participations"""
    for user_id in selected_users:
        enrollment = TournamentParticipation(
            user_id=user_id,
            semester_id=tournament_id,
            placement=None,  # Will be set after tournament completes
            xp_awarded=0,
            credits_awarded=0
        )
        self.db.add(enrollment)
    self.db.commit()
    logger.info(f"✅ Created {len(selected_users)} enrollment records")
```

### Option C: Fix UI → Backend Flow

**Investigate and fix**:
1. Ensure `selected_user_ids` is passed in tournament config
2. Backend API validates and stores selected_users
3. Orchestrator reads selected_users from config, not TEST_USER_POOL

---

## Next Steps

1. ✅ **DONE**: Identify root cause (hardcoded TEST_USER_POOL)
2. ⏳ **IN PROGRESS**: Trace UI → Backend data flow
3. ⏳ **TODO**: Implement fix (Option A + B recommended)
4. ⏳ **TODO**: Add validation: Reject tournaments with 0 enrollments
5. ⏳ **TODO**: Backfill tournament_participations for existing tournaments
6. ⏳ **TODO**: Re-run E2E tests with proper participant selection
7. ⏳ **TODO**: Add test: Verify enrollment records match participants

---

## Test Plan (After Fix)

### Unit Tests

```python
def test_orchestrator_respects_selected_users():
    """Orchestrator should use provided selected_users, not TEST_USER_POOL"""
    orchestrator = SandboxTestOrchestrator(db)
    selected = [10, 11, 12, 13, 14, 15, 16, 17]
    enrolled = orchestrator._enroll_participants(8, selected_users=selected)
    assert enrolled == selected, "Should use selected users, not TEST_USER_POOL"

def test_enrollment_records_created():
    """Should create tournament_participations records"""
    tournament_id = create_test_tournament()
    selected = [4, 5, 6, 7, 13, 14, 15, 16]
    orchestrator._create_enrollment_records(tournament_id, selected)

    count = db.query(TournamentParticipation).filter_by(semester_id=tournament_id).count()
    assert count == 8, "Should create 8 enrollment records"
```

### E2E Tests

```python
def test_ui_participant_selection():
    """UI participant selection should control who participates"""
    # Select only users [10, 11, 12]
    page.check('input[data-user-id="10"]')
    page.check('input[data-user-id="11"]')
    page.check('input[data-user-id="12"]')

    # Create tournament
    click_create_tournament()

    # Verify ONLY selected users are enrolled
    enrollments = db.query(TournamentParticipation).filter_by(semester_id=tournament_id).all()
    enrolled_user_ids = [e.user_id for e in enrollments]
    assert enrolled_user_ids == [10, 11, 12], "Only selected users should be enrolled"
```

---

## Related Files

- `app/services/sandbox_test_orchestrator.py` - Orchestrator with hardcoded pool
- `streamlit_sandbox_v3_admin_aligned.py` - UI participant selection
- `app/models/tournament_participation.py` - Enrollment model (if exists)
- `app/api/api_v1/endpoints/tournaments/...` - Tournament creation endpoints
- `tests/e2e_frontend/test_tournament_full_ui_workflow.py` - E2E tests (need fixing)

---

**Document Created**: 2026-02-03
**Last Updated**: 2026-02-03
**Status**: Root cause identified, fix in progress
