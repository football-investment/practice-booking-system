# Instructor Workflow Implementation Plan

**Status:** 🔴 NOT IMPLEMENTED (TODO)

**Priority:** HIGH (Required for production-ready tournament system)

**Estimated Effort:** 2-3 days (Backend + Frontend)

---

## Overview

The instructor workflow is a **critical missing component** in the tournament lifecycle. Currently, tournaments can bypass instructor assignment, which is NOT production-ready.

### Current Limitations

❌ No instructor assignment workflow (tournaments have `master_instructor_id = NULL`)
❌ No session attendance tracking (no UI/API for instructors to mark attendance)
❌ No instructor-submitted rankings (rankings inserted via direct SQL in tests)
❌ Reward distribution does NOT validate instructor presence or attendance records
❌ No Instructor Dashboard UI (instructors cannot interact with tournaments)

---

## Production Tournament Lifecycle (Should Be)

```
1. ADMIN: Create tournament
   └─> Status: SEEKING_INSTRUCTOR
   └─> API: POST /api/v1/tournaments/generate

2. INSTRUCTOR: Accept assignment
   ├─> Validates: Instructor has LFA_COACH license
   ├─> Updates: semester.master_instructor_id = instructor.id
   ├─> Updates: semester.status = READY_FOR_ENROLLMENT
   └─> API: POST /api/v1/tournaments/{id}/instructor-assignment/accept

3. PLAYERS: Enroll in tournament
   ├─> Validates: Tournament status = READY_FOR_ENROLLMENT
   ├─> Validates: Player has LFA_FOOTBALL_PLAYER license
   └─> API: POST /api/v1/tournaments/{id}/enroll

4. INSTRUCTOR: Mark attendance for each session
   ├─> For each session: Mark present/absent/excused
   ├─> Creates: Attendance records in database
   └─> API: POST /api/v1/sessions/{session_id}/attendance/bulk

5. INSTRUCTOR: Submit final rankings
   ├─> Validates: All participants have at least 1 attendance record
   ├─> Validates: Instructor is master_instructor for tournament
   ├─> Creates: TournamentRanking records
   └─> API: POST /api/v1/tournaments/{id}/rankings/submit

6. ADMIN/INSTRUCTOR: Mark tournament COMPLETED
   ├─> Validates: Rankings exist
   ├─> Validates: Attendance records exist
   ├─> Updates: semester.status = COMPLETED
   └─> API: PATCH /api/v1/semesters/{id} {"status": "COMPLETED"}

7. ADMIN: Distribute rewards
   ├─> Validates: semester.master_instructor_id IS NOT NULL
   ├─> Validates: Attendance records exist
   ├─> Distributes: XP and Credits based on rankings
   └─> API: POST /api/v1/tournaments/{id}/distribute-rewards
```

---

## Required Backend Implementation

### 1. Instructor Assignment Endpoint

**File:** `app/api/api_v1/endpoints/tournaments/instructor.py` (NEW)

```python
@router.post("/{tournament_id}/instructor-assignment/accept")
def accept_instructor_assignment(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Instructor accepts tournament assignment.

    Authorization: INSTRUCTOR role only

    Validations:
    - User is INSTRUCTOR
    - User has active LFA_COACH license
    - Tournament status is SEEKING_INSTRUCTOR

    Actions:
    - Update semester.master_instructor_id = current_user.id
    - Update semester.status = READY_FOR_ENROLLMENT
    - Update all sessions.instructor_id = current_user.id

    Returns:
    - Tournament details
    - Session list
    """
```

### 2. Session Attendance Bulk Endpoint

**File:** `app/api/api_v1/endpoints/sessions.py` (MODIFY)

```python
@router.post("/{session_id}/attendance/bulk")
def mark_session_attendance_bulk(
    session_id: int,
    attendance_list: List[AttendanceRecordCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Instructor marks attendance for multiple participants in a session.

    Authorization: INSTRUCTOR (must be session.instructor_id)

    Validations:
    - Session exists
    - Current user is session instructor
    - All user_ids are enrolled in tournament

    Body Example:
    [
        {"user_id": 1, "status": "PRESENT"},
        {"user_id": 2, "status": "ABSENT"},
        {"user_id": 3, "status": "EXCUSED"}
    ]

    Returns:
    - Attendance summary (total present, absent, excused)
    """
```

### 3. Tournament Rankings Submission Endpoint

**File:** `app/api/api_v1/endpoints/tournaments/rankings.py` (NEW)

```python
@router.post("/{tournament_id}/rankings/submit")
def submit_tournament_rankings(
    tournament_id: int,
    rankings: List[RankingSubmissionCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Instructor submits final tournament rankings.

    Authorization: INSTRUCTOR (must be master_instructor)

    Validations:
    - User is master instructor for tournament
    - All user_ids have at least 1 attendance record
    - All user_ids are enrolled in tournament
    - Ranks are unique and valid (1, 2, 3, 4...)

    Body Example:
    [
        {"user_id": 1, "rank": 1, "points": 15, "wins": 5, "draws": 0, "losses": 0},
        {"user_id": 2, "rank": 2, "points": 12, "wins": 4, "draws": 0, "losses": 1},
        ...
    ]

    Returns:
    - Ranking summary
    """
```

### 4. Enhanced Validation in `distribute_rewards()`

**File:** `app/services/tournament/tournament_xp_service.py` (MODIFY)

```python
def distribute_rewards(db: Session, tournament_id: int):
    """
    Distribute rewards with STRICT production validations.
    """
    semester = db.query(Semester).filter(Semester.id == tournament_id).first()

    # ✅ PRODUCTION VALIDATION 1: Instructor must be assigned
    if not semester.master_instructor_id:
        raise ValueError(
            f"Tournament {tournament_id} cannot distribute rewards: "
            f"No instructor assigned. Instructor assignment is required."
        )

    # ✅ PRODUCTION VALIDATION 2: Attendance records must exist
    from app.models import Attendance, Session as SessionModel
    attendance_count = db.query(Attendance).join(SessionModel).filter(
        SessionModel.semester_id == tournament_id
    ).count()

    if attendance_count == 0:
        raise ValueError(
            f"Tournament {tournament_id} cannot distribute rewards: "
            f"No attendance records found. Instructor must mark attendance first."
        )

    # ... rest of reward distribution logic
```

---

## Required Frontend Implementation

### 1. Instructor Dashboard Page

**File:** `streamlit_app/pages/Instructor_Dashboard.py` (NEW)

```python
import streamlit as st

st.set_page_config(page_title="Instructor Dashboard", page_icon="🏆")

st.title("🏆 Instructor Dashboard")

# Tab 1: Pending Assignments
# Tab 2: My Tournaments
# Tab 3: Session Management
```

**Features:**
- List tournaments with status SEEKING_INSTRUCTOR
- "Accept Assignment" button → calls instructor assignment API
- View assigned tournaments
- Session attendance UI (checkboxes for present/absent/excused)
- Ranking submission form

### 2. Session Attendance Component

**File:** `streamlit_app/components/instructor/session_attendance.py` (NEW)

```python
def render_session_attendance(session_id: int, instructor_token: str):
    """
    Render attendance marking UI for a session.

    Features:
    - Display enrolled players
    - Checkboxes: Present / Absent / Excused
    - "Submit Attendance" button
    - Real-time attendance summary
    """
```

### 3. Ranking Submission Component

**File:** `streamlit_app/components/instructor/tournament_rankings.py` (NEW)

```python
def render_ranking_submission(tournament_id: int, instructor_token: str):
    """
    Render ranking submission UI for a tournament.

    Features:
    - Display participants with attendance records
    - Ranking form: Rank, Points, Wins, Draws, Losses
    - Validation: Only users with attendance can be ranked
    - "Submit Rankings" button
    """
```

---

## Database Models (Already Exist)

### Attendance Model
**Table:** `attendance`
**Columns:** `id`, `session_id`, `user_id`, `status` (PRESENT/ABSENT/EXCUSED), `marked_by`, `marked_at`

**Status:** ✅ Model exists, but NO UI/API endpoints to create records

### TournamentRanking Model
**Table:** `tournament_rankings`
**Columns:** `id`, `tournament_id`, `user_id`, `participant_type`, `rank`, `points`, `wins`, `draws`, `losses`

**Status:** ✅ Model exists, but NO API endpoint for instructor submission (only direct SQL insert in tests)

---

## Implementation Roadmap

### Phase 1: Backend Foundation (1 day)
- [ ] Create `app/api/api_v1/endpoints/tournaments/instructor.py`
- [ ] Implement `POST /{tournament_id}/instructor-assignment/accept`
- [ ] Implement `POST /sessions/{session_id}/attendance/bulk`
- [ ] Implement `POST /{tournament_id}/rankings/submit`
- [ ] Uncomment validation code in `distribute_rewards()`

### Phase 2: Frontend UI (1 day)
- [ ] Create `Instructor_Dashboard.py` page
- [ ] Implement pending assignments list
- [ ] Implement session attendance UI
- [ ] Implement ranking submission form

### Phase 3: Testing & Integration (0.5 day)
- [ ] Create `test_instructor_workflow.py` E2E test
- [ ] Update `reward_policy_fixtures.py` with instructor fixture
- [ ] Test full lifecycle: Assignment → Attendance → Rankings → Rewards

### Phase 4: Documentation (0.5 day)
- [ ] Update API documentation
- [ ] Update user guide for instructors
- [ ] Remove "⚠️ SIMPLIFIED" warnings from test files

---

## Workaround for Testing (Current State)

**Until instructor workflow is implemented, tests use:**

1. **Manual status change:** PATCH semester.status → READY_FOR_ENROLLMENT (bypasses instructor)
2. **Direct SQL ranking insert:** Direct INSERT into tournament_rankings (bypasses attendance)
3. **Disabled validations:** `distribute_rewards()` does NOT check instructor or attendance

**This is ONLY acceptable for:**
- Development testing
- Backend logic validation
- Reward calculation testing

**NOT acceptable for:**
- Production use
- Full E2E testing
- User acceptance testing

---

## Priority Justification

**Why HIGH Priority:**

1. **Data Integrity:** Rankings should be based on actual attendance, not arbitrary SQL inserts
2. **Audit Trail:** Attendance records are required for accountability and disputes
3. **Role Separation:** Instructors should manage tournaments, not admins doing everything
4. **User Experience:** Instructors need a proper UI to perform their duties
5. **Production Readiness:** Current system is NOT production-ready without this workflow

**Business Risk if NOT Implemented:**

- ⚠️ Fraudulent rankings (no attendance verification)
- ⚠️ Manual SQL manipulation required for every tournament
- ⚠️ No instructor accountability
- ⚠️ Poor user experience for instructors
- ⚠️ Cannot scale to production use

---

## Related Documentation

- [Tournament System Architecture](../architecture/tournament_system.md) (TODO)
- [Reward Policy System](../backend/reward_policy_system.md) (TODO)
- [E2E Testing Limitations](../testing/e2e_limitations.md) (TODO)

---

**Last Updated:** 2026-01-04
**Author:** Development Team
**Status:** Planning Phase (Not Started)
