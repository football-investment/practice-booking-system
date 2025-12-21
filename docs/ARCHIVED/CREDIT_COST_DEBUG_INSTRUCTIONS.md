# Credit Cost Debug Instructions

**Date**: 2025-12-14 20:15
**Status**: 🔍 DEBUG MODE ENABLED

---

## Problem

Capacity updates work ✅ but credit_cost updates don't ❌

**Expected**: When instructor changes credit_cost from 1 → 10, it should save as 10
**Actual**: It saves as 1 (unchanged)

---

## Debug Instrumentation Added

### 1. Frontend Real-Time Debug (VISIBLE BEFORE SAVE)

**Location**: [unified_workflow_dashboard.py:3561](unified_workflow_dashboard.py#L3561)

```python
st.warning(f"🔍 DEBUG - Current values: capacity={edit_capacity}, credit_cost={edit_credit_cost}")
```

**What to look for**:
- This WARNING box appears IMMEDIATELY when in edit mode
- Shows the CURRENT values of capacity and credit_cost inputs
- Updates in REAL-TIME as you change the number inputs

**Expected when you set credit_cost to 10**:
```
⚠️ 🔍 DEBUG - Current values: capacity=8, credit_cost=10
```

---

### 2. Frontend Request Debug (SHOWS AFTER CLICKING SAVE)

**Location**: [unified_workflow_dashboard.py:3607-3608](unified_workflow_dashboard.py#L3607-L3608)

```python
st.info(f"🔍 DEBUG: Sending credit_cost = {int(edit_credit_cost)} (type: {type(int(edit_credit_cost)).__name__})")
st.json(update_payload)
```

**What to look for**:
- Shows the exact value being sent to backend
- Shows the JSON payload

**Expected**:
```
ℹ️ 🔍 DEBUG: Sending credit_cost = 10 (type: int)
{
  "title": "👟🎾 GānFoottenis",
  "capacity": 8,
  "credit_cost": 10,
  ...
}
```

---

### 3. Backend Debug Logs (IN TERMINAL)

**Location**: [app/api/api_v1/endpoints/sessions.py:447-485](app/api/api_v1/endpoints/sessions.py#L447-L485)

**Three checkpoints**:

**A. What backend received:**
```
🔍 BACKEND DEBUG - Session 209 PATCH received:
   credit_cost in update_data: 10
   capacity in update_data: 8
   Full update_data: {'title': '...', 'capacity': 8, 'credit_cost': 10, ...}
```

**B. After setattr loop:**
```
🔍 BACKEND DEBUG - After setattr loop:
   session.credit_cost = 10
   session.capacity = 8
```

**C. After DB commit:**
```
🔍 BACKEND DEBUG - After commit + refresh:
   session.credit_cost = 10  ← Should be 10, NOT 1!
   session.capacity = 8
```

---

## How to Test

### Step 1: Ensure Backend is Running in Terminal

Backend must be running in a terminal where you can see the output:

```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
source venv/bin/activate
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**IMPORTANT**: Don't run in background! You need to SEE the print statements!

---

### Step 2: Refresh Dashboard

Navigate to: **Instructor Dashboard → Tab 4: 📚 My Sessions**

---

### Step 3: Enter Edit Mode

1. Click **✏️ Edit** button on the GānFoottenis session
2. **IMMEDIATELY look for the yellow warning box**:
   ```
   ⚠️ 🔍 DEBUG - Current values: capacity=8, credit_cost=1
   ```

---

### Step 4: Change Credit Cost

1. Change **💳 Credit Cost** from 1 to 10
2. **Watch the yellow warning box update in real-time**:
   ```
   ⚠️ 🔍 DEBUG - Current values: capacity=8, credit_cost=10
   ```

If the warning box shows `credit_cost=10`, the frontend has the correct value! ✅

---

### Step 5: Click Save Changes

1. Click **💾 Save Changes** button
2. **Look for the blue info box** showing what's being sent:
   ```
   ℹ️ 🔍 DEBUG: Sending credit_cost = 10 (type: int)
   ```
3. **Look for the JSON payload** showing:
   ```json
   {
     "credit_cost": 10,
     "capacity": 8,
     ...
   }
   ```

If JSON shows `"credit_cost": 10`, the frontend is sending the correct value! ✅

---

### Step 6: Check Backend Terminal

**Switch to the terminal where backend is running**

Look for the three debug checkpoints:

**Checkpoint A - Received:**
```
🔍 BACKEND DEBUG - Session 209 PATCH received:
   credit_cost in update_data: 10
   capacity in update_data: 8
```

If this shows `credit_cost: 10`, the backend RECEIVED the correct value! ✅

**Checkpoint B - After setattr:**
```
🔍 BACKEND DEBUG - After setattr loop:
   session.credit_cost = 10
   session.capacity = 8
```

If this shows `credit_cost = 10`, the model was UPDATED correctly! ✅

**Checkpoint C - After commit:**
```
🔍 BACKEND DEBUG - After commit + refresh:
   session.credit_cost = 10
   session.capacity = 8
```

If this shows `credit_cost = 1`, we found the bug! The database is NOT saving it! ❌

---

## Diagnostic Decision Tree

### If Real-Time Warning Shows `credit_cost=1` (Not 10)
**Problem**: Streamlit number_input not capturing the change
**Possible causes**:
- Browser cache issue
- Streamlit widget state issue
- Input validation blocking the value

---

### If JSON Payload Shows `"credit_cost": 1` (Not 10)
**Problem**: Frontend not sending the correct value
**Possible causes**:
- `edit_credit_cost` variable not reading from widget
- Type conversion issue
- Variable scope issue

---

### If Backend Checkpoint A Shows `credit_cost: NOT_IN_PAYLOAD`
**Problem**: Backend didn't receive credit_cost in the request
**Possible causes**:
- Frontend excluded it from payload
- Network layer stripped it out (unlikely)

---

### If Backend Checkpoint A Shows `credit_cost: 10` BUT Checkpoint B Shows `session.credit_cost = 1`
**Problem**: `setattr` is not applying the value
**Possible causes**:
- Session model has property/setter that's blocking updates
- SQLAlchemy relationship or hybrid_property issue

---

### If Backend Checkpoint B Shows `credit_cost = 10` BUT Checkpoint C Shows `credit_cost = 1`
**Problem**: Database is reverting the value on commit
**Possible causes**:
- Database trigger resetting value
- SQLAlchemy event listener overriding value
- Database constraint or default value

---

## Expected Outcome

**If everything works**:
```
Frontend Real-Time: credit_cost=10 ✅
Frontend JSON: "credit_cost": 10 ✅
Backend Received: credit_cost: 10 ✅
Backend After setattr: credit_cost = 10 ✅
Backend After commit: credit_cost = 10 ✅
```

**Actual current behavior** (suspected):
```
Frontend Real-Time: credit_cost=10 ✅
Frontend JSON: "credit_cost": 10 ✅
Backend Received: credit_cost: 10 ✅
Backend After setattr: credit_cost = 10 ✅
Backend After commit: credit_cost = 1 ❌ ← BUG IS HERE
```

---

## Files Modified

1. ✅ [unified_workflow_dashboard.py:3561](unified_workflow_dashboard.py#L3561) - Real-time debug warning
2. ✅ [app/api/api_v1/endpoints/sessions.py:447-450](app/api/api_v1/endpoints/sessions.py#L447-L450) - Received debug
3. ✅ [app/api/api_v1/endpoints/sessions.py:475-477](app/api/api_v1/endpoints/sessions.py#L475-L477) - After setattr debug
4. ✅ [app/api/api_v1/endpoints/sessions.py:483-485](app/api/api_v1/endpoints/sessions.py#L483-L485) - After commit debug

---

**Status**: ✅ DEBUG INSTRUMENTATION COMPLETE
**Ready for**: User to test and provide debug output
**Next Step**: Identify exactly where credit_cost value is being lost/reverted

