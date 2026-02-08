# Phase 8 Fix: Query Param Restore Bug

## Problem Summary

**Symptom:** Phase 8 "Complete Tournament" button click did not navigate to Step 7 (View Rewards). The page remained on Step 6 despite the form callback executing successfully.

**Impact:** Golden Path E2E test failed at Phase 9, preventing full tournament lifecycle validation.

## Root Cause

The query parameter restore logic in `streamlit_sandbox_v3_admin_aligned.py` **unconditionally overwrote** `st.session_state.workflow_step` with the URL parameter `?step=` value on **every script run**.

### Timeline of Bug

1. User clicks "Complete Tournament" button (Step 6)
2. Form callback executes:
   - Sets `st.session_state.workflow_step = 7` ✅
   - Calls `st.rerun()` ✅
3. **New script run starts**
4. Query param restore logic runs **first**:
   - Reads URL: `?step=6` (still has old value)
   - **Overwrites** `st.session_state.workflow_step = 6` ❌
5. Page renders Step 6 again (instead of Step 7)

### Evidence from Logs

**Before fix:**
```
🔥 DEBUG: Setting workflow_step=7
🔥 DEBUG: Calling st.rerun()
🔍 [LOAD] workflow_step ON ENTRY: 7  ← Session state WAS correct!
🔍 [QUERY RESTORE] Query param step=6, current workflow_step=7
⚠️  [QUERY RESTORE] OVERWRITING workflow_step: 7 → 6  ← BUG!
```

**After fix:**
```
🔥 DEBUG: Setting workflow_step=7
🔥 DEBUG: Calling st.rerun()
🔍 [LOAD] workflow_step ON ENTRY: 7  ← Session state preserved!
(No OVERWRITING log - restore skipped)
```

## Solution

**File:** `streamlit_sandbox_v3_admin_aligned.py`
**Line:** ~1490

### Change

```python
# BEFORE (unconditional restore):
if "step" in query_params:
    desired_step = int(query_params["step"])
    if st.session_state.get("workflow_step") != desired_step:
        st.session_state.workflow_step = desired_step
        state_changed = True

# AFTER (initialize-only restore):
if "step" in query_params and "workflow_step" not in st.session_state:
    desired_step = int(query_params["step"])
    st.session_state.workflow_step = desired_step
    state_changed = True
```

### Principle

**Session state = single source of truth**

- URL query params are **only** used for initial page load (deep linking)
- Once `workflow_step` exists in session state, it is **never** overwritten by URL
- Form callbacks and navigation logic control session state directly

## Validation

### Stability Testing

**3 consecutive runs:**
- ✅ 3/3 passed
- ✅ 0 query param overwrites detected
- ✅ All runs reached Phase 9 (Step 7 View Rewards)

### Regression Checks

1. **Deep linking still works:** `?step=6` correctly initializes workflow on first load
2. **Session state persistence:** `workflow_step=7` survives `st.rerun()`
3. **No unexpected overwrites:** Query restore logs show only initialization, no overwrites

## Impact

### Before Fix
- Golden Path E2E: **FAILED** at Phase 8
- Success rate: **0%** (deterministic failure)

### After Fix
- Golden Path E2E: **PASSED** consistently
- Success rate: **100%** (3/3 runs validated)
- No regressions detected

## Files Changed

1. `streamlit_sandbox_v3_admin_aligned.py` - Query param restore logic (1 line guard added)

## Future Considerations

- URL and session state sync could be improved with bidirectional update
- Consider using `st.query_params` API (Streamlit 1.30+) for cleaner URL management
- Current fix is minimal-risk, production-safe approach

---

**Date:** 2026-02-08
**Validated by:** Claude Code with Playwright E2E testing
**Status:** ✅ Production-ready
