"""
Unit tests for app/services/tournament/pitch_instructor_service.py

PITCH-01: direct assign success (DIRECT mode, non-master)
PITCH-02: license mismatch → 422
PITCH-03: instructor role mismatch → 422
PITCH-04: accept → session.instructor_id batch update (is_master=True)
PITCH-05: master uniqueness guard → 409 when active master already exists
PITCH-06: decline → status=DECLINED, notes appended
PITCH-07: accept wrong instructor → 403
PITCH-08: get_eligible_instructors filters ACTIVE assignments
"""
import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import HTTPException

_SVC = "app.services.tournament.pitch_instructor_service"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_pitch(pitch_id=1, is_active=True):
    p = MagicMock()
    p.id = pitch_id
    p.is_active = is_active
    return p


def _make_user(user_id=10, role="INSTRUCTOR"):
    from app.models.user import UserRole
    u = MagicMock()
    u.id = user_id
    u.name = f"User_{user_id}"
    u.email = f"user{user_id}@test.com"
    u.is_active = True
    u.role = UserRole.INSTRUCTOR if role == "INSTRUCTOR" else UserRole.STUDENT
    return u


def _make_assignment(
    assignment_id=100,
    pitch_id=1,
    instructor_id=10,
    semester_id=None,
    is_master=False,
    status="PENDING",
):
    from app.models.pitch_instructor_assignment import PitchAssignmentStatus
    a = MagicMock()
    a.id = assignment_id
    a.pitch_id = pitch_id
    a.instructor_id = instructor_id
    a.semester_id = semester_id
    a.is_master = is_master
    a.status = status
    a.notes = None
    return a


def _simple_db(first_returns: list, all_returns=None):
    """DB mock that returns values from `first_returns` in sequence per query() call."""
    call_n = [0]
    db = MagicMock()

    def side(*args):
        n = call_n[0]
        call_n[0] += 1
        q = MagicMock()
        q.filter.return_value = q
        q.filter_by.return_value = q
        q.join.return_value = q
        q.order_by.return_value = q
        q.subquery.return_value = MagicMock()
        # all() returns provided list or empty
        all_val = (all_returns[n] if all_returns and n < len(all_returns) else [])
        q.all.return_value = all_val
        # first() returns from sequence
        first_val = first_returns[n] if n < len(first_returns) else None
        q.first.return_value = first_val
        return q

    db.query.side_effect = side
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock(side_effect=lambda x: x)
    return db


# ─────────────────────────────────────────────────────────────────────────────
# PITCH-01: direct assign success (non-master)
# ─────────────────────────────────────────────────────────────────────────────

def test_PITCH_01_direct_assign_success():
    from app.services.tournament.pitch_instructor_service import assign_instructor_to_pitch_direct

    pitch = _make_pitch(pitch_id=1)
    instructor = _make_user(user_id=10, role="INSTRUCTOR")

    # Query sequence: Pitch lookup, User lookup, (no license check since required_license_type=None)
    db = _simple_db(first_returns=[pitch, instructor])

    result = assign_instructor_to_pitch_direct(
        db=db,
        pitch_id=1,
        instructor_id=10,
        assigned_by_id=99,
        semester_id=None,
        is_master=False,
    )

    db.add.assert_called_once()
    db.commit.assert_called_once()
    added = db.add.call_args[0][0]
    assert added.pitch_id == 1
    assert added.instructor_id == 10
    assert added.assigned_by == 99
    assert added.status == "PENDING"
    assert added.assignment_type == "DIRECT"
    assert added.is_master is False


# ─────────────────────────────────────────────────────────────────────────────
# PITCH-02: license mismatch → 422
# ─────────────────────────────────────────────────────────────────────────────

def test_PITCH_02_license_mismatch_raises_422():
    from app.services.tournament.pitch_instructor_service import assign_instructor_to_pitch_direct

    pitch = _make_pitch()
    instructor = _make_user()

    # Query sequence: Pitch, User, InstructorSpecialization (not found → None)
    db = _simple_db(first_returns=[pitch, instructor, None])

    with pytest.raises(HTTPException) as exc:
        assign_instructor_to_pitch_direct(
            db=db,
            pitch_id=1,
            instructor_id=10,
            assigned_by_id=99,
            required_license_type="LFA_FOOTBALL_PLAYER",
        )

    assert exc.value.status_code == 422
    assert "specialization" in exc.value.detail.lower()


# ─────────────────────────────────────────────────────────────────────────────
# PITCH-03: non-instructor role → 422
# ─────────────────────────────────────────────────────────────────────────────

def test_PITCH_03_non_instructor_role_raises_422():
    from app.services.tournament.pitch_instructor_service import assign_instructor_to_pitch_direct

    pitch = _make_pitch()
    student = _make_user(user_id=20, role="STUDENT")

    db = _simple_db(first_returns=[pitch, student])

    with pytest.raises(HTTPException) as exc:
        assign_instructor_to_pitch_direct(
            db=db,
            pitch_id=1,
            instructor_id=20,
            assigned_by_id=99,
        )

    assert exc.value.status_code == 422
    assert "not an instructor" in exc.value.detail.lower()


# ─────────────────────────────────────────────────────────────────────────────
# PITCH-04: accept with is_master=True → session batch update
# ─────────────────────────────────────────────────────────────────────────────

def test_PITCH_04_accept_master_batch_updates_sessions():
    from app.services.tournament.pitch_instructor_service import accept_pitch_assignment
    from app.models.pitch_instructor_assignment import PitchAssignmentStatus

    assignment = _make_assignment(
        assignment_id=100,
        pitch_id=1,
        instructor_id=10,
        semester_id=5,
        is_master=True,
        status="PENDING",
    )

    # Mock sessions to be updated
    session_1 = MagicMock()
    session_1.instructor_id = None
    session_2 = MagicMock()
    session_2.instructor_id = None

    # Query sequence:
    # 1. PitchInstructorAssignment (get assignment by id)
    # 2. PitchInstructorAssignment (uniqueness guard — no existing active master)
    # 3. SessionModel (batch assign — returns 2 sessions)
    db = _simple_db(
        first_returns=[assignment, None],
        all_returns=[None, None, [session_1, session_2]],
    )

    result = accept_pitch_assignment(db=db, assignment_id=100, instructor_id=10)

    # Assignment status updated
    assert assignment.status == "ACTIVE"
    # Sessions got instructor_id set
    assert session_1.instructor_id == 10
    assert session_2.instructor_id == 10
    assert result._sessions_updated == 2


# ─────────────────────────────────────────────────────────────────────────────
# PITCH-05: master uniqueness guard → 409
# ─────────────────────────────────────────────────────────────────────────────

def test_PITCH_05_master_uniqueness_guard_raises_409():
    from app.services.tournament.pitch_instructor_service import assign_instructor_to_pitch_direct

    pitch = _make_pitch()
    instructor = _make_user()
    existing_master = _make_assignment(assignment_id=50, is_master=True, status="ACTIVE")

    # Query sequence: Pitch, User, existing_master (uniqueness check finds one)
    db = _simple_db(first_returns=[pitch, instructor, existing_master])

    with pytest.raises(HTTPException) as exc:
        assign_instructor_to_pitch_direct(
            db=db,
            pitch_id=1,
            instructor_id=10,
            assigned_by_id=99,
            is_master=True,
        )

    assert exc.value.status_code == 409
    assert "active master" in exc.value.detail.lower()


# ─────────────────────────────────────────────────────────────────────────────
# PITCH-06: decline → status=DECLINED + notes appended
# ─────────────────────────────────────────────────────────────────────────────

def test_PITCH_06_decline_sets_status_and_appends_reason():
    from app.services.tournament.pitch_instructor_service import decline_pitch_assignment

    assignment = _make_assignment(assignment_id=100, instructor_id=10, status="PENDING")
    assignment.notes = "initial note"

    db = _simple_db(first_returns=[assignment])

    result = decline_pitch_assignment(
        db=db,
        assignment_id=100,
        instructor_id=10,
        reason="Scheduling conflict",
    )

    assert assignment.status == "DECLINED"
    assert "DECLINED" in assignment.notes
    assert "Scheduling conflict" in assignment.notes
    db.commit.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# PITCH-07: accept by wrong instructor → 403
# ─────────────────────────────────────────────────────────────────────────────

def test_PITCH_07_accept_wrong_instructor_raises_403():
    from app.services.tournament.pitch_instructor_service import accept_pitch_assignment

    # Assignment belongs to instructor 10, but instructor 99 tries to accept
    assignment = _make_assignment(assignment_id=100, instructor_id=10, status="PENDING")
    db = _simple_db(first_returns=[assignment])

    with pytest.raises(HTTPException) as exc:
        accept_pitch_assignment(db=db, assignment_id=100, instructor_id=99)

    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# PITCH-08: get_eligible_instructors excludes already-active
# ─────────────────────────────────────────────────────────────────────────────

def test_PITCH_08_eligible_instructors_excludes_active():
    from app.services.tournament.pitch_instructor_service import get_eligible_instructors_for_pitch
    from app.models.user import UserRole

    instructor_a = _make_user(user_id=10)
    instructor_b = _make_user(user_id=11)

    # Query sequence:
    # 1. already_active subquery (PitchInstructorAssignment.instructor_id)
    # 2. User query (returns instructor_b only — instructor_a excluded by subquery mock)
    already_active_q = MagicMock()
    already_active_q.filter.return_value = already_active_q
    already_active_q.subquery.return_value = MagicMock()

    eligible_q = MagicMock()
    eligible_q.filter.return_value = eligible_q
    eligible_q.join.return_value = eligible_q
    eligible_q.order_by.return_value = eligible_q
    eligible_q.all.return_value = [instructor_b]

    call_n = [0]
    db = MagicMock()

    def side(*args):
        n = call_n[0]
        call_n[0] += 1
        return already_active_q if n == 0 else eligible_q

    db.query.side_effect = side

    result = get_eligible_instructors_for_pitch(db=db, pitch_id=1, semester_id=5)

    assert result == [instructor_b]
