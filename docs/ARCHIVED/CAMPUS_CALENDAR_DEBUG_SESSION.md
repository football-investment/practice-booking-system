# Campus Calendar Debug Session - 2025-12-14

**Status**: 🔍 DEBUGGING IN PROGRESS

---

## Problem

The Campus Calendar view is not showing the session that exists in the database:

**Database Reality**:
```sql
SELECT s.id, s.title, sem.location_city, sem.location_venue
FROM sessions s
JOIN semesters sem ON s.semester_id = sem.id;

Result:
id  | title              | location_city | location_venue
209 | 👟🎾 GānFoottenis   | Budaörs       | Budaörs Campus
```

**UI Shows**: `📍 LFA Education Center - Budaörs - Budaörs (0 sessions)`

---

## Changes Made (2025-12-14 19:45)

### 1. Fixed Performance Issue ✅

**Before**: Fetching semesters inside the location loop (multiple API calls)
**After**: Fetch semesters once before the loop (line 2736-2748)

```python
# Fetch semesters ONCE (not inside location loop)
semesters_response = requests.get(
    f"{API_BASE_URL}/api/v1/semesters",
    headers={"Authorization": f"Bearer {st.session_state.admin_token}"},
    timeout=10
)

all_semesters = []
semester_lookup = {}
if semesters_response.status_code == 200:
    semesters_data = semesters_response.json()
    all_semesters = semesters_data if isinstance(semesters_data, list) else []
    semester_lookup = {s['id']: s for s in all_semesters if isinstance(s, dict)}
```

**Location**: [unified_workflow_dashboard.py:2736-2748](unified_workflow_dashboard.py#L2736-L2748)

---

### 2. Added Debug Output ✅

**A. Top-level debug** (line 2751):
```python
st.info(f"🔍 DEBUG: Fetched {len(all_sessions)} sessions and {len(all_semesters)} semesters")
```

**B. Campus-level debug** (line 2797):
```python
st.code(f"Campus matching: city='{campus_city}' venue='{campus_venue}'")
```

**C. Session-level debug** (lines 2800-2805):
```python
with st.expander("🔍 DEBUG: All sessions", expanded=False):
    for session in all_sessions:
        if isinstance(session, dict):
            semester_id = session.get('semester_id')
            semester = semester_lookup.get(semester_id, {})
            st.code(f"Session {session.get('id')}: '{session.get('title')}' | semester_id={semester_id} | sem_city='{semester.get('location_city', '')}' | sem_venue='{semester.get('location_venue', '')}'")
```

**D. Campus expanders set to expanded=True** (line 2792):
```python
with st.expander(f"📍 {campus_name} - {campus_city} ({len(campus_sessions)} sessions)", expanded=True):
```

---

## How to Debug

### Step 1: Refresh Dashboard

Navigate to: **Admin Dashboard → Tab 5: 📅 Campus Calendar**

### Step 2: Check Top Debug Line

Look for:
```
🔍 DEBUG: Fetched X sessions and Y semesters
```

**Expected**:
- X >= 1 (at least session 209)
- Y >= 1 (at least the semester containing session 209)

**If X = 0**: Session is not being fetched from API
**If Y = 0**: Semesters are not being fetched from API

---

### Step 3: Check Campus Matching

Look at the Budaörs campus box:

```
📍 LFA Education Center - Budaörs - Budaörs (0 sessions)
  Venue: Budaörs Campus
  Address: ...

  Campus matching: city='Budaörs' venue='Budaörs Campus'
```

**Expected Values**:
- city = 'Budaörs'
- venue = 'Budaörs Campus'

---

### Step 4: Check Session Details

Expand: **🔍 DEBUG: All sessions**

Look for session 209:
```
Session 209: '👟🎾 GānFoottenis' | semester_id=X | sem_city='Budaörs' | sem_venue='Budaörs Campus'
```

**Check**:
1. Does session 209 appear in the list?
2. What is its semester_id?
3. What are sem_city and sem_venue values?
4. Do they match the campus values?

---

## Possible Root Causes

### A. Session Not Fetched
- API filtered it out (specialization_filter issue?)
- Session doesn't exist in database
- API error

### B. Semester Lookup Failed
- semester_id in session doesn't match any semester.id
- Semester data not in API response
- semester_lookup dictionary not built correctly

### C. String Matching Failed
- Case sensitivity: 'Budaörs' vs 'budaörs'
- Whitespace: 'Budaörs ' vs 'Budaörs'
- Encoding: 'Budaörs' (ö) vs 'Budaors' (o)
- Empty strings: '' == '' might match incorrectly

### D. API Response Format
- sessions_data might be in unexpected format
- semesters_data might be in unexpected format
- location_city/location_venue might be None instead of ''

---

## Matching Logic (Current)

**Location**: [unified_workflow_dashboard.py:2772-2789](unified_workflow_dashboard.py#L2772-L2789)

```python
for session in all_sessions:
    if isinstance(session, dict):
        semester_id = session.get('semester_id')
        semester = semester_lookup.get(semester_id, {})

        # Match by location_city or location_venue
        semester_city = semester.get('location_city', '')
        semester_venue = semester.get('location_venue', '')

        # DEBUG: Show matching attempt
        match_city = semester_city == campus_city
        match_venue = (semester_venue == campus_venue and campus_venue)

        if match_city or match_venue:
            campus_sessions.append({
                'session': session,
                'semester': semester
            })
```

**Logic**:
- Match if `semester.location_city == campus.city`
- OR match if `semester.location_venue == campus.venue` (and venue is not empty)

---

## Next Steps

### 1. Analyze Debug Output
- User refreshes dashboard
- User shares debug output from browser

### 2. Identify Root Cause
- Based on debug output, determine why session 209 is not matching

### 3. Fix Matching Logic
- Implement fix (e.g., case-insensitive matching, strip whitespace, etc.)

### 4. Remove Debug Code
- Once working, remove all debug expanders
- Set expanders back to `expanded=False`

---

## Files Modified

1. ✅ [unified_workflow_dashboard.py:2736-2748](unified_workflow_dashboard.py#L2736-L2748) - Moved semester fetch outside loop
2. ✅ [unified_workflow_dashboard.py:2751](unified_workflow_dashboard.py#L2751) - Added top-level debug
3. ✅ [unified_workflow_dashboard.py:2792](unified_workflow_dashboard.py#L2792) - Set expanders to expanded=True
4. ✅ [unified_workflow_dashboard.py:2797](unified_workflow_dashboard.py#L2797) - Added campus matching debug
5. ✅ [unified_workflow_dashboard.py:2800-2805](unified_workflow_dashboard.py#L2800-L2805) - Added session-level debug

---

**Date**: 2025-12-14 19:45
**Status**: Waiting for user to refresh dashboard and provide debug output
**Ready for**: Debug analysis

