"""
Unit tests for app/api/api_v1/endpoints/attendance.py

Covers:
  create_attendance:
    regular session — no booking_id → 400
    regular session — booking not found → 404
    regular session — booking not CONFIRMED → 400
    regular session — existing attendance, update with notes
    regular session — existing attendance, update present → milestone call
    regular session — no existing, create new (absent → no milestone)
    regular session — no existing, create new (present → milestone)
    tournament session — existing attendance update

  list_attendance:
    session_id not found → 404
    session_id valid → filtered response (AttendanceWithRelations)
    no session_id → all records
    empty attendance list

  checkin:
    booking not found → 404
    booking owned by different user → 403
    booking not confirmed → 400
    too early (before window) → 400
    session ended → 400
    no existing attendance → create new
    existing attendance → update

  update_attendance:
    not found → 404
    tournament session + invalid status → 400
    tournament session + valid status → ok
    non-tournament → update

  get_instructor_attendance_overview:
    non-instructor → 403
    instructor → paginated sessions response

  _update_milestone_sessions_on_attendance:
    no active enrollments → early return
    enrollment with in-progress milestone → increment sessions_completed
    enrollment with no in-progress milestone → no-op
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.attendance import (
    create_attendance,
    list_attendance,
    checkin,
    update_attendance,
    get_instructor_attendance_overview,
    _update_milestone_sessions_on_attendance,
)
from app.models.attendance import AttendanceStatus
from app.models.booking import BookingStatus
from app.models.session import EventCategory

_BASE = "app.api.api_v1.endpoints.attendance"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin():
    u = MagicMock()
    u.id = 42
    u.role = MagicMock()
    u.role.value = "admin"
    return u


def _instructor():
    u = MagicMock()
    u.id = 42
    u.role = MagicMock()
    u.role.value = "instructor"
    return u


def _student():
    u = MagicMock()
    u.id = 99
    u.role = MagicMock()
    u.role.value = "student"
    return u


def _fq(first=None, all_=None, count=0):
    """Fluent query mock supporting .filter/.options/.with_for_update/.first/.all/.count."""
    q = MagicMock()
    q.filter.return_value = q
    q.options.return_value = q
    q.with_for_update.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.group_by.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    q.count.return_value = count
    return q


def _seq_db(*qs):
    """Sequential db mock: n-th db.query() returns qs[n]."""
    idx = [0]
    db = MagicMock()

    def _side(m):
        i = idx[0]; idx[0] += 1
        return qs[i] if i < len(qs) else _fq()

    db.query.side_effect = _side
    return db


def _attendance_data(
    session_id=1,
    user_id=99,
    booking_id=None,
    status=AttendanceStatus.present,
    notes=None,
):
    """Mock AttendanceCreate-like object."""
    d = MagicMock()
    d.session_id = session_id
    d.user_id = user_id
    d.booking_id = booking_id
    d.status = status
    d.notes = notes
    d.model_dump.return_value = {
        'session_id': session_id,
        'user_id': user_id,
        'booking_id': booking_id,
        'status': status,
        'notes': notes,
    }
    return d


def _session(is_tournament=False):
    s = MagicMock()
    s.id = 1
    s.is_tournament_game = is_tournament
    s.event_category = EventCategory.MATCH if is_tournament else EventCategory.TRAINING
    return s


def _booking(status=BookingStatus.CONFIRMED, user_id=99, session_id=1):
    b = MagicMock()
    b.id = 1
    b.user_id = user_id
    b.session_id = session_id
    b.status = status
    s = MagicMock()
    s.id = session_id
    s.date_start = datetime(2024, 6, 1, 10, 0, 0)   # timezone-naive
    s.date_end   = datetime(2024, 6, 1, 12, 0, 0)
    b.session = s
    return b


# ---------------------------------------------------------------------------
# _update_milestone_sessions_on_attendance (direct unit tests)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUpdateMilestoneSessionsOnAttendance:
    def test_no_enrollments_returns_early(self):
        db = MagicMock()
        q = _fq(all_=[])
        db.query.return_value = q
        _update_milestone_sessions_on_attendance(db, user_id=99, session_id=1)
        db.commit.assert_not_called()

    def test_with_in_progress_milestone_increments_sessions(self):
        db = MagicMock()
        enrollment = MagicMock(); enrollment.id = 10
        milestone_progress = MagicMock()
        milestone_progress.sessions_completed = 2
        milestone = MagicMock(); milestone.required_sessions = 5

        enroll_q = _fq(all_=[enrollment])
        progress_q = _fq(first=milestone_progress)
        milestone_q = _fq(first=milestone)

        idx = [0]
        def _side(m): i = idx[0]; idx[0] += 1; return [enroll_q, progress_q, milestone_q][i]
        db.query.side_effect = _side

        _update_milestone_sessions_on_attendance(db, user_id=99, session_id=1)
        assert milestone_progress.sessions_completed == 3
        db.commit.assert_called_once()

    def test_enrollment_with_no_in_progress_milestone_is_noop(self):
        db = MagicMock()
        enrollment = MagicMock(); enrollment.id = 11
        enroll_q = _fq(all_=[enrollment])
        progress_q = _fq(first=None)  # no in-progress milestone

        idx = [0]
        def _side(m): i = idx[0]; idx[0] += 1; return [enroll_q, progress_q][i]
        db.query.side_effect = _side

        _update_milestone_sessions_on_attendance(db, user_id=99, session_id=1)
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# create_attendance
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCreateAttendance:
    def test_regular_no_booking_id_returns_400(self):
        session = _session(is_tournament=False)
        db = _seq_db(_fq(first=session))
        data = _attendance_data(booking_id=None)
        with pytest.raises(HTTPException) as exc:
            create_attendance(attendance_data=data, db=db, current_user=_admin())
        assert exc.value.status_code == 400
        assert "booking_id is required" in exc.value.detail

    def test_regular_booking_not_found_returns_404(self):
        session = _session(is_tournament=False)
        db = _seq_db(
            _fq(first=session),          # session lookup
            _fq(first=None),             # booking not found
        )
        data = _attendance_data(booking_id=1)
        with pytest.raises(HTTPException) as exc:
            create_attendance(attendance_data=data, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_regular_booking_not_confirmed_returns_400(self):
        session = _session(is_tournament=False)
        booking = _booking(status=BookingStatus.WAITLISTED)
        db = _seq_db(
            _fq(first=session),
            _fq(first=booking),
        )
        data = _attendance_data(booking_id=1)
        with pytest.raises(HTTPException) as exc:
            create_attendance(attendance_data=data, db=db, current_user=_admin())
        assert exc.value.status_code == 400
        assert "confirmed" in exc.value.detail

    def test_regular_existing_attendance_updates_with_notes(self):
        session = _session(is_tournament=False)
        booking = _booking(status=BookingStatus.CONFIRMED)
        existing = MagicMock()
        existing.status = AttendanceStatus.absent
        existing.user_id = 99; existing.session_id = 1

        db = _seq_db(
            _fq(first=session),
            _fq(first=booking),
            _fq(first=existing),   # existing_attendance by booking_id
        )
        data = _attendance_data(booking_id=1, status=AttendanceStatus.present, notes="Updated")
        create_attendance(attendance_data=data, db=db, current_user=_admin())

        assert existing.status == AttendanceStatus.present
        assert existing.notes == "Updated"
        db.commit.assert_called()

    def test_regular_existing_absent_no_milestone_call(self):
        session = _session(is_tournament=False)
        booking = _booking(status=BookingStatus.CONFIRMED)
        existing = MagicMock()
        existing.status = AttendanceStatus.absent
        existing.user_id = 99; existing.session_id = 1

        db = _seq_db(
            _fq(first=session),
            _fq(first=booking),
            _fq(first=existing),
        )
        data = _attendance_data(booking_id=1, status=AttendanceStatus.absent, notes=None)
        create_attendance(attendance_data=data, db=db, current_user=_admin())
        # absent → no milestone update, only 3 queries
        assert db.query.call_count == 3

    def test_regular_no_existing_creates_new_absent(self):
        """No existing → create new; absent → milestone NOT called."""
        session = _session(is_tournament=False)
        booking = _booking(status=BookingStatus.CONFIRMED)

        db = _seq_db(
            _fq(first=session),
            _fq(first=booking),
            _fq(first=None),       # no existing attendance
        )
        data = _attendance_data(booking_id=1, status=AttendanceStatus.absent)
        result = create_attendance(attendance_data=data, db=db, current_user=_admin())
        db.add.assert_called_once()
        db.commit.assert_called_once()
        # only 3 queries (no milestone update for absent)
        assert db.query.call_count == 3

    def test_regular_no_existing_creates_new_present_triggers_milestone(self):
        """No existing → create present → _update_milestone_sessions_on_attendance called."""
        session = _session(is_tournament=False)
        booking = _booking(status=BookingStatus.CONFIRMED)

        db = _seq_db(
            _fq(first=session),
            _fq(first=booking),
            _fq(first=None),       # no existing
            _fq(all_=[]),          # _update_milestone: no active enrollments → early return
        )
        data = _attendance_data(booking_id=1, status=AttendanceStatus.present)
        create_attendance(attendance_data=data, db=db, current_user=_admin())
        db.add.assert_called_once()
        # 4th query = ProjectEnrollment lookup in milestone helper
        assert db.query.call_count >= 4

    def test_tournament_existing_attendance_updates_status(self):
        session = _session(is_tournament=True)
        existing = MagicMock()
        existing.status = AttendanceStatus.absent
        existing.user_id = 99; existing.session_id = 1

        db = _seq_db(
            _fq(first=session),
            _fq(first=existing),   # existing by user_id+session_id
        )
        data = _attendance_data(status=AttendanceStatus.present, notes=None)
        result = create_attendance(attendance_data=data, db=db, current_user=_admin())
        assert existing.status == AttendanceStatus.present


# ---------------------------------------------------------------------------
# list_attendance
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestListAttendance:
    def test_session_not_found_returns_404(self):
        db = MagicMock()
        # list_attendance: db.query(Attendance) → q; db.query(SessionTypel) → not found
        q_att = _fq()
        db.query.side_effect = [q_att, _fq(first=None)]

        with pytest.raises(HTTPException) as exc:
            list_attendance(db=db, current_user=_admin(), session_id=5)
        assert exc.value.status_code == 404

    @patch(f"{_BASE}.AttendanceList")
    @patch(f"{_BASE}.AttendanceWithRelations")
    def test_session_id_valid_returns_filtered_response(self, MockAWR, MockAL):
        from types import SimpleNamespace
        att = SimpleNamespace(
            id=1, user_id=99, session_id=1, booking_id=1,
            status=AttendanceStatus.present, notes=None,
            check_in_time=None, marked_by=42, created_at=None, updated_at=None,
        )
        att.user = MagicMock(); att.session = MagicMock()
        att.booking = MagicMock(); att.marker = MagicMock()

        db = MagicMock()
        q_att = _fq(all_=[att])
        q_session = _fq(first=MagicMock())   # session found
        db.query.side_effect = [q_att, q_session]

        MockAWR.return_value = MagicMock()
        MockAL.return_value = MagicMock(attendances=[], total=1)

        list_attendance(db=db, current_user=_admin(), session_id=1)
        MockAWR.assert_called_once()
        MockAL.assert_called_once()

    @patch(f"{_BASE}.AttendanceList")
    @patch(f"{_BASE}.AttendanceWithRelations")
    def test_no_session_id_returns_all(self, MockAWR, MockAL):
        db = MagicMock()
        q_att = _fq(all_=[])
        db.query.return_value = q_att
        MockAL.return_value = MagicMock()

        list_attendance(db=db, current_user=_admin(), session_id=None)
        MockAL.assert_called_once_with(attendances=[], total=0)

    @patch(f"{_BASE}.AttendanceList")
    @patch(f"{_BASE}.AttendanceWithRelations")
    def test_empty_list_returns_zero_total(self, MockAWR, MockAL):
        db = MagicMock()
        db.query.return_value = _fq(all_=[])
        MockAL.return_value = MagicMock()

        list_attendance(db=db, current_user=_admin(), session_id=None)
        call_kw = MockAL.call_args[1]
        assert call_kw['total'] == 0
        MockAWR.assert_not_called()


# ---------------------------------------------------------------------------
# checkin
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCheckin:
    def _checkin_data(self, notes=None):
        d = MagicMock(); d.notes = notes
        return d

    def test_booking_not_found_returns_404(self):
        db = _seq_db(_fq(first=None))
        with pytest.raises(HTTPException) as exc:
            checkin(booking_id=1, checkin_data=self._checkin_data(), db=db, current_user=_student())
        assert exc.value.status_code == 404

    def test_wrong_user_returns_403(self):
        booking = _booking(user_id=88)   # owned by user 88, not 99
        db = _seq_db(_fq(first=booking))
        user = _student(); user.id = 99
        with pytest.raises(HTTPException) as exc:
            checkin(booking_id=1, checkin_data=self._checkin_data(), db=db, current_user=user)
        assert exc.value.status_code == 403

    def test_booking_not_confirmed_returns_400(self):
        booking = _booking(status=BookingStatus.WAITLISTED, user_id=99)
        db = _seq_db(_fq(first=booking))
        user = _student(); user.id = 99
        with pytest.raises(HTTPException) as exc:
            checkin(booking_id=1, checkin_data=self._checkin_data(), db=db, current_user=user)
        assert exc.value.status_code == 400

    def test_too_early_returns_400(self):
        booking = _booking(user_id=99)
        # session starts at 10:00; window opens at 09:45; now = 09:00 (too early)
        db = _seq_db(_fq(first=booking))
        user = _student(); user.id = 99

        with patch(f"{_BASE}.time_provider") as tp:
            tp.now.return_value = datetime(2024, 6, 1, 9, 0, 0)
            with pytest.raises(HTTPException) as exc:
                checkin(booking_id=1, checkin_data=self._checkin_data(), db=db, current_user=user)
        assert exc.value.status_code == 400
        assert "15 minutes" in exc.value.detail

    def test_session_ended_returns_400(self):
        booking = _booking(user_id=99)
        # session ends at 12:00; now = 13:00 (too late)
        db = _seq_db(_fq(first=booking))
        user = _student(); user.id = 99

        with patch(f"{_BASE}.time_provider") as tp:
            tp.now.return_value = datetime(2024, 6, 1, 13, 0, 0)
            with pytest.raises(HTTPException) as exc:
                checkin(booking_id=1, checkin_data=self._checkin_data(), db=db, current_user=user)
        assert exc.value.status_code == 400
        assert "ended" in exc.value.detail

    def test_valid_checkin_no_existing_creates_attendance(self):
        booking = _booking(user_id=99)
        db = _seq_db(
            _fq(first=booking),    # booking lookup
            _fq(first=None),       # no existing attendance
        )
        user = _student(); user.id = 99

        with patch(f"{_BASE}.time_provider") as tp:
            tp.now.return_value = datetime(2024, 6, 1, 10, 30, 0)  # during session
            result = checkin(booking_id=1, checkin_data=self._checkin_data(notes="Hi"), db=db, current_user=user)
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_valid_checkin_existing_updates_attendance(self):
        booking = _booking(user_id=99)
        existing = MagicMock()
        existing.status = AttendanceStatus.absent
        db = _seq_db(
            _fq(first=booking),
            _fq(first=existing),   # existing attendance found
        )
        user = _student(); user.id = 99

        with patch(f"{_BASE}.time_provider") as tp:
            tp.now.return_value = datetime(2024, 6, 1, 10, 30, 0)
            checkin(booking_id=1, checkin_data=self._checkin_data(), db=db, current_user=user)
        assert existing.status == AttendanceStatus.present
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# update_attendance
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUpdateAttendance:
    def test_not_found_returns_404(self):
        db = _seq_db(_fq(first=None))
        update_data = MagicMock(); update_data.model_dump.return_value = {}
        with pytest.raises(HTTPException) as exc:
            update_attendance(attendance_id=99, attendance_update=update_data, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_tournament_invalid_status_returns_400(self):
        session = _session(is_tournament=True)
        attendance = MagicMock(); attendance.id = 1; attendance.session_id = 1

        db = _seq_db(
            _fq(first=attendance),   # attendance lookup
            _fq(first=session),      # session lookup
        )
        update_data = MagicMock()
        update_data.status = AttendanceStatus.late    # invalid for tournament
        update_data.model_dump.return_value = {'status': AttendanceStatus.late}

        with pytest.raises(HTTPException) as exc:
            update_attendance(attendance_id=1, attendance_update=update_data, db=db, current_user=_admin())
        assert exc.value.status_code == 400
        assert "present" in exc.value.detail or "absent" in exc.value.detail

    def test_tournament_valid_status_updates_ok(self):
        session = _session(is_tournament=True)
        attendance = MagicMock(); attendance.id = 1; attendance.session_id = 1

        db = _seq_db(
            _fq(first=attendance),
            _fq(first=session),
        )
        update_data = MagicMock()
        update_data.status = AttendanceStatus.present
        update_data.model_dump.return_value = {'status': AttendanceStatus.present}

        result = update_attendance(attendance_id=1, attendance_update=update_data, db=db, current_user=_admin())
        db.commit.assert_called_once()

    def test_non_tournament_updates_fields(self):
        session = _session(is_tournament=False)
        attendance = MagicMock(); attendance.id = 1; attendance.session_id = 1

        db = _seq_db(
            _fq(first=attendance),
            _fq(first=session),
        )
        update_data = MagicMock()
        update_data.status = AttendanceStatus.late
        update_data.model_dump.return_value = {'status': AttendanceStatus.late, 'notes': 'Arrived late'}

        update_attendance(attendance_id=1, attendance_update=update_data, db=db, current_user=_admin())
        assert attendance.status == AttendanceStatus.late
        assert attendance.notes == 'Arrived late'
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# get_instructor_attendance_overview
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetInstructorAttendanceOverview:
    def test_non_instructor_returns_403(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as exc:
            get_instructor_attendance_overview(
                db=db, current_user=_student(), page=1, size=50
            )
        assert exc.value.status_code == 403

    def test_instructor_returns_paginated_response(self):
        db = MagicMock()
        instructor = _instructor()

        session = MagicMock()
        session.id = 1
        session.title = "Test Session"
        session.description = "Desc"
        session.date_start = datetime(2024, 6, 1, 10, 0, 0)
        session.date_end   = datetime(2024, 6, 1, 12, 0, 0)
        session.location = "Pitch A"
        session.capacity = 20
        session.level = "Beginner"
        session.sport_type = "Football"
        session.created_at = datetime(2024, 1, 1, 0, 0, 0)

        q_sessions = _fq(all_=[session], count=1)
        q_sessions.filter.return_value = q_sessions
        # Simulate attendance GROUP BY result
        att_row = MagicMock(); att_row.session_id = 1; att_row.count = 3
        q_attendance = MagicMock()
        q_attendance.filter.return_value = q_attendance
        q_attendance.group_by.return_value = q_attendance
        q_attendance.all.return_value = [att_row]
        # Simulate booking GROUP BY result
        bk_row = MagicMock(); bk_row.session_id = 1; bk_row.count = 5
        q_bookings = MagicMock()
        q_bookings.filter.return_value = q_bookings
        q_bookings.group_by.return_value = q_bookings
        q_bookings.all.return_value = [bk_row]

        idx = [0]
        def _side(*args): i = idx[0]; idx[0] += 1; return [q_sessions, q_attendance, q_bookings][i]
        db.query.side_effect = _side

        result = get_instructor_attendance_overview(
            db=db, current_user=instructor, page=1, size=50
        )
        assert result['total'] == 1
        assert result['page'] == 1
        assert len(result['sessions']) == 1
        s = result['sessions'][0]
        assert s['attendance_count'] == 3
        assert s['current_bookings'] == 5

    def test_instructor_empty_sessions(self):
        db = MagicMock()
        instructor = _instructor()

        q_sessions = _fq(all_=[], count=0)
        q_att = MagicMock(); q_att.filter.return_value = q_att
        q_att.group_by.return_value = q_att; q_att.all.return_value = []
        q_bk = MagicMock(); q_bk.filter.return_value = q_bk
        q_bk.group_by.return_value = q_bk; q_bk.all.return_value = []

        idx = [0]
        def _side(*args): i = idx[0]; idx[0] += 1; return [q_sessions, q_att, q_bk][i]
        db.query.side_effect = _side

        result = get_instructor_attendance_overview(
            db=db, current_user=instructor, page=1, size=50
        )
        assert result['total'] == 0
        assert result['sessions'] == []
