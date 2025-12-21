# Frontend Cache Debug - Current Status

**Date**: 2025-12-15 07:53
**Status**: 🔍 ADDITIONAL DEBUG ADDED

---

## Current Situation

### Database State ✅
```sql
SELECT id, title, credit_cost, capacity FROM sessions WHERE id = 209;
```

**Result**:
```
 id  |      title      | credit_cost | capacity
-----+-----------------+-------------+----------
 209 | 👟🎾 GānFoottenis |           5 |        8
```

**Database is correct!** credit_cost = 5

---

### User Reports ❌

Frontend dashboard still shows:
```
📋 Existing Sessions (1)
...
💳 Credit Cost: 1 credits  ← WRONG! Should be 5!
```

Even after:
- Modifying from 10 → 7 in edit mode
- Clicking Save Changes
- Clearing browser cookies
- Hard browser refresh (Ctrl+Shift+R)

---

## Debug Instrumentation Added

### 1. Frontend Fetch Debug (NEW!)

**Location**: [unified_workflow_dashboard.py:3343-3344](unified_workflow_dashboard.py#L3343-L3344)

```python
# 🔍 DEBUG: Verify we're fetching fresh data
print(f"🟢 FETCHING SESSIONS - semester_id={selected_semester_id}, cache_bust={cache_bust}")
```

**Purpose**: Verify that sessions fetch is actually executing on every page load.

---

### 2. Response Data Debug (NEW!)

**Location**: [unified_workflow_dashboard.py:3361-3368](unified_workflow_dashboard.py#L3361-L3368)

```python
# 🔍 DEBUG: Log what we got
if sessions_response.status_code == 200:
    temp_data = sessions_response.json()
    temp_sessions = temp_data.get('sessions', []) if isinstance(temp_data, dict) else temp_data
    print(f"🟢 RECEIVED {sessions_response.status_code} - {len(temp_sessions)} sessions")
    # Log credit_cost of first session for debugging
    if temp_sessions:
        print(f"   First session: id={temp_sessions[0].get('id')}, title={temp_sessions[0].get('title')}, credit_cost={temp_sessions[0].get('credit_cost')}")
```

**Purpose**: Log exactly what credit_cost value the API is returning.

---

### 3. Existing Debug Features

**A. Real-Time Edit Debug** (Line 3598):
```python
st.warning(f"🔍 DEBUG - Current values: capacity={edit_capacity}, credit_cost={edit_credit_cost}")
```

**B. Save Attempt Persistence** (Lines 3635-3640):
```python
st.session_state.last_save_attempt = {
    'session_id': session_id,
    'credit_cost': int(edit_credit_cost),
    'capacity': int(edit_capacity),
    'timestamp': datetime.now().isoformat()
}
```

**C. Frontend Terminal Logging** (Lines 3658-3660):
```python
print(f"🟢 FRONTEND: Attempting PATCH to session {session_id}")
print(f"   Payload credit_cost: {update_payload['credit_cost']}")
print(f"   Payload capacity: {update_payload['capacity']}")
```

---

## Expected Debug Output

### When Dashboard Loads

**Streamlit terminal should show**:
```
🟢 FETCHING SESSIONS - semester_id=167, cache_bust=1734248373456
🟢 RECEIVED 200 - 1 sessions
   First session: id=209, title=👟🎾 GānFoottenis, credit_cost=5
```

**If credit_cost shows 5 here** → API is returning correct data, problem is in frontend display
**If credit_cost shows 1 here** → API is returning wrong data, problem is in backend query

---

### When User Clicks Save

**Streamlit terminal should show**:
```
🟢 FRONTEND: Attempting PATCH to session 209
   Payload credit_cost: 7
   Payload capacity: 8
```

**Backend terminal should show**:
```
🔍 BACKEND DEBUG - Session 209 PATCH received:
   credit_cost in update_data: 7
   capacity in update_data: 8
```

---

## Diagnostic Tree

### Scenario A: Fetch shows credit_cost=5 BUT display shows credit_cost=1

**Root Cause**: Frontend is displaying from wrong data source.

**Possible Issues**:
1. The `session` variable in the loop is from a different/cached list
2. Multiple sessions fetch happening, one cached, one not
3. Streamlit component caching

**Fix**: Ensure the VIEW mode displays from the freshly fetched `sessions` list.

---

### Scenario B: Fetch shows credit_cost=1 (same as database shows 5)

**Root Cause**: API endpoint is returning stale data despite database being correct.

**Possible Issues**:
1. SQLAlchemy query caching
2. Backend response serialization issue
3. Different database connection pool returning stale data

**Fix**: Add backend query debugging to see what SQL query returns.

---

### Scenario C: Fetch not showing at all (no debug output)

**Root Cause**: Streamlit not re-executing the fetch code after rerun.

**Possible Issues**:
1. Code is inside a conditional that's not being met
2. Exception being silently caught
3. Tab not being re-rendered

**Fix**: Move fetch outside of conditional blocks.

---

## Next Steps for User

1. **Restart Streamlit Dashboard** (to load new debug code):
   ```bash
   # Kill existing streamlit process
   pkill -f "streamlit run unified_workflow_dashboard"

   # Start fresh
   cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
   source venv/bin/activate
   streamlit run unified_workflow_dashboard.py --server.port 8501
   ```

2. **Watch Streamlit Terminal Output**

3. **Navigate to Instructor Dashboard → 📚 My Sessions tab**

4. **Look for debug output**:
   - Should see: `🟢 FETCHING SESSIONS - semester_id=...`
   - Should see: `🟢 RECEIVED 200 - 1 sessions`
   - Should see: `First session: id=209, ... credit_cost=?`

5. **Report the credit_cost value shown in terminal**

---

## Files Modified

1. ✅ [unified_workflow_dashboard.py:3343-3344](unified_workflow_dashboard.py#L3343-L3344) - Fetch debug
2. ✅ [unified_workflow_dashboard.py:3361-3368](unified_workflow_dashboard.py#L3361-L3368) - Response debug
3. ✅ [check_api_session_209.py](check_api_session_209.py) - Diagnostic script

---

**Status**: ✅ ENHANCED DEBUG READY
**Ready for**: User to restart dashboard and report debug output
**Next**: Based on debug output, identify whether problem is in frontend display or backend API

