# DRAFT Status Handling in History Browser - FIXED

**Date:** 2026-01-28
**Status:** ✅ COMPLETE

## Problem

The History Browser didn't properly handle tournaments in DRAFT status. When viewing a DRAFT tournament, it would:
- Show "No leaderboard data yet" message
- Try to fetch leaderboard data that doesn't exist yet
- Not provide any useful information about the tournament state
- Not offer a way to continue the tournament setup

**User Feedback:** "nme kezeli ezt az állapotot!" (doesn't handle this state!)

## Root Cause

Both `render_step_tournament_history()` and `render_history_screen()` functions tried to fetch leaderboard data for ALL tournaments regardless of status. DRAFT tournaments don't have:
- Sessions generated
- Rankings created
- Leaderboard data

The code didn't check tournament status before attempting to display leaderboard.

## Solution

### 1. Added Status Check in Leaderboard Tab

Modified both functions ([streamlit_sandbox_v3_admin_aligned.py:1772-1827](streamlit_sandbox_v3_admin_aligned.py#L1772-L1827) and [streamlit_sandbox_v3_admin_aligned.py:2233-2288](streamlit_sandbox_v3_admin_aligned.py#L2233-L2288)) to:

**For DRAFT tournaments:**
- Show warning: "Tournament in DRAFT status"
- Show info: "Sessions need to be generated before leaderboard is available"
- Display enrolled players instead of leaderboard
- Fetch and show player enrollments with name, email, and status

**For non-DRAFT tournaments:**
- Fetch and display leaderboard as before
- Show rankings, stats, and match data

### 2. Added "Continue Setup" Button for DRAFT

Modified `render_history_screen()` ([streamlit_sandbox_v3_admin_aligned.py:2225-2268](streamlit_sandbox_v3_admin_aligned.py#L2225-L2268)) to:

**For DRAFT tournaments:**
- Show "Continue Setup" button
- Loads tournament into workflow at Step 1 (Generate Sessions)
- Allows completing tournament setup from where it was left off

**For IN_PROGRESS tournaments:**
- Keep existing "Continue Tournament" button
- Loads at Step 2 (Manage Sessions)

## Code Changes

### File: streamlit_sandbox_v3_admin_aligned.py

**Lines 1772-1827** (render_step_tournament_history):
```python
with tab1:
    # Check tournament status first
    tournament_status = tournament_detail.get('tournament_status')

    if tournament_status == 'DRAFT':
        st.warning("⚠️ Tournament in DRAFT status")
        st.info("📋 Sessions need to be generated before leaderboard is available")

        # Show enrolled players instead
        enrollments_response = requests.get(
            f"{API_BASE_URL}/semester-enrollments/?semester_id={selected_tournament_id}",
            headers=headers
        )

        # Display enrolled players table
        # ...
    else:
        # Fetch and display leaderboard for non-DRAFT tournaments
        # ...
```

**Lines 2225-2268** (render_history_screen):
```python
with col4:
    # Add "Continue Tournament" button for DRAFT and IN_PROGRESS tournaments
    if tournament_detail.get('tournament_status') == 'DRAFT':
        if st.button("▶️ Continue Setup", type="primary"):
            st.session_state.workflow_step = 1  # Generate Sessions
            # Load tournament config...
    elif tournament_detail.get('tournament_status') == 'IN_PROGRESS':
        if st.button("▶️ Continue Tournament", type="primary"):
            st.session_state.workflow_step = 2  # Manage Sessions
            # Load tournament config...
```

## User Experience Improvements

### Before:
- DRAFT tournament: "No leaderboard data yet" (unhelpful)
- No way to continue setup from History Browser
- User had to manually navigate back to workflow

### After:
- DRAFT tournament: Clear warning + enrolled players list
- "Continue Setup" button to resume workflow at correct step
- Informative message about what needs to be done next
- Enrolled players visible to verify tournament setup

## Testing Instructions

### Test DRAFT Tournament:
1. Create a tournament but don't generate sessions (leave in DRAFT)
2. Go to History Browser
3. Select the DRAFT tournament
4. **Expected:**
   - Leaderboard tab shows warning about DRAFT status
   - Shows enrolled players instead of leaderboard
   - "Continue Setup" button appears
   - Clicking button loads tournament at Step 1

### Test IN_PROGRESS Tournament:
1. Create tournament and generate sessions
2. Go to History Browser
3. Select the IN_PROGRESS tournament
4. **Expected:**
   - Leaderboard tab shows rankings
   - "Continue Tournament" button appears
   - Clicking button loads tournament at Step 2

### Test COMPLETED/REWARDS_DISTRIBUTED:
1. Complete a tournament and distribute rewards
2. Go to History Browser
3. **Expected:**
   - All tabs work normally
   - No "Continue" button (tournament is finished)

## Related Files

- [streamlit_sandbox_v3_admin_aligned.py](streamlit_sandbox_v3_admin_aligned.py) - Main UI file with fixes

## Status Flow Context

```
DRAFT → IN_PROGRESS → COMPLETED → REWARDS_DISTRIBUTED
  ↑                        ↑
  Step 1: Generate      Step 5: Distribute
  Sessions              Rewards
```

**DRAFT:** Tournament created, enrollments added, sessions NOT generated yet
**IN_PROGRESS:** Sessions generated, matches ongoing
**COMPLETED:** All matches finished, ready for reward distribution
**REWARDS_DISTRIBUTED:** Final state, rewards distributed to players
