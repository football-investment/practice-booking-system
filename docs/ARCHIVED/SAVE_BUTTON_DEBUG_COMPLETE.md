# Save Button Debug Instrumentation - COMPLETE

**Date**: 2025-12-14 21:00
**Status**: 🔍 COMPREHENSIVE DEBUG ACTIVE

---

## Problem

User clicks "💾 Save Changes" button but credit_cost doesn't save:
- Frontend shows credit_cost=10 ✅
- User clicks Save Changes button ✅
- Backend receives ZERO PATCH requests ❌
- Database still shows credit_cost=1 ❌

**Root Cause Suspected**: Save Changes button handler NOT executing or failing silently.

---

## Debug Instrumentation Added

### 1. Session State Persistence (NEW!)

**Purpose**: Store save attempt details that survive `st.rerun()`

**Location**: [unified_workflow_dashboard.py:3597-3606](unified_workflow_dashboard.py#L3597-L3606)

```python
# Store in session_state IMMEDIATELY when button is clicked
st.session_state.last_save_attempt = {
    'session_id': session_id,
    'credit_cost': int(edit_credit_cost),
    'capacity': int(edit_capacity),
    'timestamp': datetime.now().isoformat()
}
```

**What this does**:
- Captures values the MOMENT user clicks Save Changes
- Stores in `st.session_state` which persists across reruns
- Proves the button click handler IS executing

---

### 2. Persistent Debug Display (NEW!)

**Purpose**: Show save attempt results that remain visible after page reload

**Location**: [unified_workflow_dashboard.py:3288-3310](unified_workflow_dashboard.py#L3288-L3310)

```python
# 🔍 PERSISTENT DEBUG: Show last save attempt result
if 'last_save_attempt' in st.session_state and st.session_state.last_save_attempt:
    attempt = st.session_state.last_save_attempt
    if attempt.get('success'):
        st.success(f"✅ Last save successful - Session {attempt.get('session_id')} updated!")
        st.json({"saved_values": {
            "credit_cost": attempt.get('credit_cost'),
            "capacity": attempt.get('capacity'),
            "timestamp": attempt.get('timestamp')
        }})
    elif 'error' in attempt:
        st.error(f"❌ Last save FAILED - Session {attempt.get('session_id')}")
        st.error(f"Error: {attempt.get('error')}")
        st.json({"attempted_values": {
            "credit_cost": attempt.get('credit_cost'),
            "capacity": attempt.get('capacity'),
            "timestamp": attempt.get('timestamp')
        }})
```

**What to look for**:
- After clicking Save Changes, you'll see EITHER:
  - ✅ Success message with saved values
  - ❌ Error message with attempted values and error details

---

### 3. Frontend Terminal Logging (NEW!)

**Purpose**: Print debug to terminal/console that runs streamlit

**Location**: [unified_workflow_dashboard.py:3621-3624](unified_workflow_dashboard.py#L3621-L3624)

```python
# 🔍 DEBUG: Log to backend terminal
print(f"🟢 FRONTEND: Attempting PATCH to session {session_id}")
print(f"   Payload credit_cost: {update_payload['credit_cost']}")
print(f"   Payload capacity: {update_payload['capacity']}")
```

**What to look for** (in streamlit terminal):
```
🟢 FRONTEND: Attempting PATCH to session 209
   Payload credit_cost: 10
   Payload capacity: 8
```

If you see this, the button handler IS executing!

---

### 4. Error Capture in Session State (NEW!)

**Purpose**: Catch ALL exceptions and store in session_state for display

**Location**: [unified_workflow_dashboard.py:3644-3647](unified_workflow_dashboard.py#L3644-L3647)

```python
except Exception as e:
    st.session_state.last_save_attempt['success'] = False
    st.session_state.last_save_attempt['error'] = str(e)
    print(f"🔴 FRONTEND ERROR: {str(e)}")
```

**What this catches**:
- Network errors (timeout, connection refused)
- JSON serialization errors
- Authentication errors
- Any Python exceptions

---

### 5. Backend Debug Logging (EXISTING)

**Location**: [app/api/api_v1/endpoints/sessions.py:447-485](app/api/api_v1/endpoints/sessions.py#L447-L485)

**Three Checkpoints**:

**A. Received:**
```python
print(f"🔍 BACKEND DEBUG - Session {session_id} PATCH received:")
print(f"   credit_cost in update_data: {update_data.get('credit_cost', 'NOT_IN_PAYLOAD')}")
print(f"   capacity in update_data: {update_data.get('capacity', 'NOT_IN_PAYLOAD')}")
```

**B. After setattr:**
```python
print(f"🔍 BACKEND DEBUG - After setattr loop:")
print(f"   session.credit_cost = {session.credit_cost}")
print(f"   session.capacity = {session.capacity}")
```

**C. After commit:**
```python
print(f"🔍 BACKEND DEBUG - After commit + refresh:")
print(f"   session.credit_cost = {session.credit_cost}")
print(f"   session.capacity = {session.capacity}")
```

---

## How to Test

### Step 1: Refresh Dashboard

Navigate to: **Instructor Dashboard → Tab 4: 📚 My Sessions**

**Expected**: You should now see a persistent debug box at the top (if you've attempted a save before)

---

### Step 2: Check for Previous Save Attempt

If you see:
```
✅ Last save successful - Session 209 updated!
{
  "saved_values": {
    "credit_cost": 10,
    "capacity": 8,
    "timestamp": "2025-12-14T21:00:00"
  }
}
```

Then the save DID work! Check the session list to verify.

If you see:
```
❌ Last save FAILED - Session 209
Error: Connection refused
{
  "attempted_values": {
    "credit_cost": 10,
    "capacity": 8,
    "timestamp": "2025-12-14T21:00:00"
  }
}
```

Then we know exactly why it failed!

---

### Step 3: Attempt a New Save

1. Click **✏️ Edit** on GānFoottenis session
2. Change **💳 Credit Cost** from 1 to 10
3. Watch real-time debug: `⚠️ 🔍 DEBUG - Current values: capacity=8, credit_cost=10`
4. Click **💾 Save Changes**

---

### Step 4: Check All Debug Outputs

**A. Streamlit Terminal** (where you run `streamlit run unified_workflow_dashboard.py`):
```
🟢 FRONTEND: Attempting PATCH to session 209
   Payload credit_cost: 10
   Payload capacity: 8
```

If you see this, the button handler executed! ✅

If you DON'T see this, the button click didn't trigger the handler! ❌

**B. Backend Terminal** (where you run `uvicorn app.main:app`):
```
🔍 BACKEND DEBUG - Session 209 PATCH received:
   credit_cost in update_data: 10
   capacity in update_data: 8
```

If you see this, the request reached the backend! ✅

If you DON'T see this, the request never left the frontend! ❌

**C. Dashboard Persistent Debug** (top of sessions tab):

After page reload, you should see EITHER:
- ✅ Success message
- ❌ Error message with specific error

---

## Diagnostic Decision Tree

### Scenario 1: No "🟢 FRONTEND" message in streamlit terminal

**Problem**: Button handler NOT executing
**Possible Causes**:
- Streamlit button not registering clicks
- Button key collision (duplicate keys)
- Streamlit session state issue

**Next Steps**: Add `st.write("BUTTON CLICKED!")` as first line in button handler

---

### Scenario 2: "🟢 FRONTEND" appears BUT no backend message

**Problem**: Request not reaching backend
**Possible Causes**:
- `API_BASE_URL` is wrong
- Network timeout
- Backend not running
- Authentication failure (wrong token)

**Debug**: The error should appear in persistent debug box!

---

### Scenario 3: Both frontend and backend messages appear BUT credit_cost still = 1

**Problem**: Database not saving
**Possible Causes**:
- DB trigger overriding value
- SQLAlchemy event listener
- Column constraint/default

**Debug**: Check "After commit" backend log - does it show credit_cost=1 or credit_cost=10?

---

### Scenario 4: Persistent debug shows success BUT session list shows credit_cost=1

**Problem**: UI not refreshing or fetching stale data
**Possible Causes**:
- GET /api/v1/sessions returning cached data
- Browser cache
- Streamlit not re-fetching after rerun

**Debug**: Manually refresh page (F5) and check if credit_cost updates

---

## Expected Full Debug Output

### If Everything Works ✅

**Streamlit Terminal**:
```
🟢 FRONTEND: Attempting PATCH to session 209
   Payload credit_cost: 10
   Payload capacity: 8
```

**Backend Terminal**:
```
🔍 BACKEND DEBUG - Session 209 PATCH received:
   credit_cost in update_data: 10
   capacity in update_data: 8
🔍 BACKEND DEBUG - After setattr loop:
   session.credit_cost = 10
   session.capacity = 8
🔍 BACKEND DEBUG - After commit + refresh:
   session.credit_cost = 10
   session.capacity = 8
INFO:     127.0.0.1:50372 - "PATCH /api/v1/sessions/209 HTTP/1.1" 200 OK
```

**Dashboard (after reload)**:
```
✅ Last save successful - Session 209 updated!
{
  "saved_values": {
    "credit_cost": 10,
    "capacity": 8,
    "timestamp": "2025-12-14T21:00:00"
  }
}
```

**Session List**:
```
💳 Credit Cost: 10 credits  ← Changed from 1!
```

---

### If Button Handler Not Executing ❌

**Streamlit Terminal**: (nothing)
**Backend Terminal**: (nothing)
**Dashboard**: (no new debug message after clicking Save)

**This means**: The `if st.button(...)` block is NOT running!

---

### If Network Error ❌

**Streamlit Terminal**:
```
🟢 FRONTEND: Attempting PATCH to session 209
   Payload credit_cost: 10
   Payload capacity: 8
🔴 FRONTEND ERROR: HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded
```

**Backend Terminal**: (nothing - request never arrived)

**Dashboard**:
```
❌ Last save FAILED - Session 209
Error: HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded
{
  "attempted_values": {
    "credit_cost": 10,
    "capacity": 8,
    "timestamp": "2025-12-14T21:00:00"
  }
}
```

**This means**: Backend is not running or not accessible!

---

## Files Modified

1. ✅ [unified_workflow_dashboard.py:3288-3310](unified_workflow_dashboard.py#L3288-L3310) - Persistent debug display
2. ✅ [unified_workflow_dashboard.py:3597-3606](unified_workflow_dashboard.py#L3597-L3606) - Session state capture
3. ✅ [unified_workflow_dashboard.py:3621-3624](unified_workflow_dashboard.py#L3621-L3624) - Frontend terminal logging
4. ✅ [unified_workflow_dashboard.py:3633-3647](unified_workflow_dashboard.py#L3633-L3647) - Result storage and error capture

---

## Key Improvements Over Previous Debug

### Before:
- Debug output disappeared on `st.rerun()`
- No way to see what happened after page reload
- Couldn't tell if button handler executed
- No error capture

### Now:
- ✅ Persistent debug survives page reload
- ✅ Terminal logging proves button execution
- ✅ All errors captured and displayed
- ✅ Exact timestamp of save attempt
- ✅ Can compare attempted values vs database values
- ✅ Clear diagnostic decision tree

---

**Status**: ✅ COMPREHENSIVE DEBUG COMPLETE
**Ready for**: User to test and report what they see
**Next Step**: Based on debug output, identify exact failure point and implement fix

