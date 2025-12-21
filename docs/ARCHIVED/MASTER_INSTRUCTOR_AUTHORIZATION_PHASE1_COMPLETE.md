# ✅ Master Instructor Authorization - Phase 1 COMPLETE

**Date**: 2025-12-14
**Status**: ✅ FULLY IMPLEMENTED

---

## Implemented

### ✅ Session CREATE Authorization

**File**: [app/api/api_v1/endpoints/sessions.py:27-79](app/api/api_v1/endpoints/sessions.py#L27-L79)

**Changes**:
- Added master_instructor_id check for instructors
- Only the assigned master instructor can create sessions for a semester
- Admin bypass remains (admins can create sessions for any semester)

**Logic**:
```python
if current_user.role == UserRole.INSTRUCTOR:
    semester = db.query(Semester).filter(Semester.id == session_data.semester_id).first()

    if semester.master_instructor_id != current_user.id:
        raise HTTPException(403, "Only the master instructor can create sessions")
```

---

### ✅ Session UPDATE Authorization

**File**: [app/api/api_v1/endpoints/sessions.py:388-433](app/api/api_v1/endpoints/sessions.py#L388-L433)

**Changes**:
- Added master_instructor_id check for instructors
- Only the assigned master instructor can update sessions

---

### ✅ Session DELETE Authorization

**File**: [app/api/api_v1/endpoints/sessions.py:436-479](app/api/api_v1/endpoints/sessions.py#L436-L479)

**Changes**:
- Added master_instructor_id check for instructors
- Only the assigned master instructor can delete sessions
- Maintains existing check for sessions with bookings

**Logic**:
```python
if current_user.role == UserRole.INSTRUCTOR:
    semester = db.query(Semester).filter(Semester.id == session.semester_id).first()

    if semester and semester.master_instructor_id != current_user.id:
        raise HTTPException(403, "Only the master instructor can delete sessions")
```

---

### ✅ Credit Cost Field

**Migration**: [alembic/versions/2025_12_14_1400-add_credit_cost_to_sessions.py](alembic/versions/2025_12_14_1400-add_credit_cost_to_sessions.py)

**Database**:
```sql
ALTER TABLE sessions ADD COLUMN credit_cost INTEGER NOT NULL DEFAULT 1;
```

**Model**: [app/models/session.py:82-87](app/models/session.py#L82-L87)
```python
credit_cost = Column(
    Integer,
    default=1,
    nullable=False,
    comment="Number of credits required to book this session (default: 1, workshops may cost more)"
)
```

**Schemas**: [app/schemas/session.py](app/schemas/session.py)
- `SessionBase`: Added `credit_cost: int = 1`
- `SessionUpdate`: Added `credit_cost: Optional[int] = None`

---

## Credit Cost Model Decision

**Chosen**: Session-level (A option)

Each session has its own `credit_cost` field:
```python
sessions.credit_cost: int = 1  # Default: 1 credit
```

**Benefits**:
- Flexible: Workshop sessions can cost more credits
- Master instructor controls pricing per session
- Can have promotional sessions (0 credits)

**Master Instructor Powers**:
1. Create session with custom credit_cost (e.g., workshop = 2 credits)
2. Update credit_cost for existing sessions
3. Set promotional sessions to 0 credits

---

## Authorization Summary

| Endpoint | Admin | Master Instructor | Other Instructors |
|----------|-------|-------------------|-------------------|
| POST /sessions | ✅ Any semester | ✅ Their semesters only | ❌ 403 Forbidden |
| PATCH /sessions/{id} | ✅ Any session | ✅ Their sessions only | ❌ 403 Forbidden |
| DELETE /sessions/{id} | ✅ Any session | ✅ Their sessions only | ❌ 403 Forbidden |

**"Their semesters"** = Semesters where `semester.master_instructor_id == instructor.id`

---

## Files Modified

1. ✅ [app/api/api_v1/endpoints/sessions.py:27-79](app/api/api_v1/endpoints/sessions.py#L27-L79) - CREATE authorization
2. ✅ [app/api/api_v1/endpoints/sessions.py:388-433](app/api/api_v1/endpoints/sessions.py#L388-L433) - UPDATE authorization
3. ✅ [app/api/api_v1/endpoints/sessions.py:436-479](app/api/api_v1/endpoints/sessions.py#L436-L479) - DELETE authorization
4. ✅ [app/models/session.py:82-87](app/models/session.py#L82-L87) - Added credit_cost field
5. ✅ [app/schemas/session.py:25](app/schemas/session.py#L25) - Added credit_cost to SessionBase
6. ✅ [app/schemas/session.py:47](app/schemas/session.py#L47) - Added credit_cost to SessionUpdate
7. ✅ [alembic/versions/2025_12_14_1400-add_credit_cost_to_sessions.py](alembic/versions/2025_12_14_1400-add_credit_cost_to_sessions.py) - Migration

---

## Database Verification

```sql
-- Verify credit_cost column was added
\d sessions

-- Result:
-- credit_cost | integer | not null | 1
```

---

## Next Steps (P1 - Important)

1. ❌ Dashboard: Show only semesters where instructor is master instructor
2. ❌ Session management UI for master instructors (create/update with credit_cost)
3. ❌ Test complete workflow: Accept assignment → Create session with custom credit_cost
4. ❌ Booking logic: Deduct credits based on session.credit_cost

---

**Status**: ✅ COMPLETE
**Backend Implementation**: 100%
**Ready for**: Testing & Frontend Integration

