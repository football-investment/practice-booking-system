# Sandbox Tournament ID Validation Fix

## Problem
The sandbox workflow had a critical bug where `st.session_state.tournament_id` could contain invalid IDs (e.g., session IDs instead of tournament IDs) from previous test runs. This caused:

1. **Leaderboard showing "Unknown" players** - API couldn't fetch user data with invalid tournament_id
2. **"0.00" scores** - No data returned from leaderboard API
3. **Reward distribution failures** - Invalid tournament_id prevented proper finalization

## Root Cause
- Session state persisted between workflow runs
- No validation that `tournament_id` was actually a valid tournament
- UI displayed session ID (e.g., 1417) but stored it as tournament_id, when actual tournament_id was different (e.g., 216)

## Solution Implemented

### 1. New Helper Function: `validate_and_fix_tournament_id()`
**Location**: `sandbox_helpers.py:174-204`

This function:
- Validates that a given ID is actually a tournament ID
- Attempts to recover if it's a session ID
- Returns `None` if ID is invalid
- Provides clear error messages to guide users

```python
def validate_and_fix_tournament_id(tournament_id: int) -> Optional[int]:
    """
    Validate tournament_id and fix if it's actually a session_id.
    Returns valid tournament_id or None if not found.
    """
```

### 2. Updated All Helper Functions
**Modified functions**:
- `fetch_leaderboard()` - Now validates tournament_id before API call
- `fetch_tournament_sessions()` - Now validates tournament_id before API call
- `render_mini_leaderboard()` - Now validates and shows clear error if invalid

### 3. Updated All Workflow Steps
**Modified steps** in `sandbox_workflow.py`:
- Step 2: `render_step_manage_sessions()` - Validates and auto-fixes tournament_id
- Step 3: `render_step_track_attendance()` - Validates and auto-fixes tournament_id
- Step 4: `render_step_enter_results()` - Validates and auto-fixes tournament_id
- Step 5: `render_step_view_leaderboard()` - Validates and auto-fixes tournament_id
- Step 6: `render_step_distribute_rewards()` - **CRITICAL FIX** - Validates before reward distribution

Each step now:
1. Checks if `tournament_id` is valid
2. Auto-corrects `st.session_state.tournament_id` if wrong
3. Shows clear error messages if tournament cannot be found
4. Provides "Back to Home" button to restart workflow

### 4. Enhanced Reward Distribution
**Location**: `sandbox_workflow.py:631-709`

Additional improvements:
- Better error handling for already-finalized sessions
- Clear progress toasts for each step
- Proper validation before attempting finalization
- Handles edge cases gracefully

## Testing
To test the fix:

1. **Clean start**: Create new tournament → should work normally
2. **Session state persistence**: Refresh page mid-workflow → should auto-correct invalid IDs
3. **Manual ID manipulation**: Manually set wrong ID in session_state → should detect and show error
4. **Reward distribution**: Complete full workflow → rewards should distribute successfully

## Benefits
✅ **Robust**: Handles invalid tournament IDs gracefully
✅ **User-friendly**: Clear error messages guide users
✅ **Auto-recovery**: Automatically fixes tournament_id when possible
✅ **Prevents crashes**: No more silent failures or "Unknown" data
✅ **Production-ready**: Ready for real instructor usage without data corruption

## Files Modified
1. `sandbox_helpers.py` - Added validation function, updated 3 helper functions
2. `sandbox_workflow.py` - Updated 5 workflow step functions
3. `SANDBOX_TOURNAMENT_ID_FIX.md` - This documentation

## Migration Notes
- Existing tournaments will continue to work
- No database changes required
- No API changes required
- Streamlit session state auto-corrects on next page load
