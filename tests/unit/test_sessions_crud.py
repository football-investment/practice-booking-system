"""
Unit tests for app/api/api_v1/endpoints/sessions/crud.py

Coverage targets:
  create_session()  — POST /
    - 404: semester not found
    - 403: instructor is not master instructor
    - 403: instructor lacks teaching qualification for target_specialization
    - 400: session start_date before semester start_date
    - 400: session end_date after semester end_date
    - happy path: admin creates session

  get_session()     — GET /{session_id}
    - 404: session not found
    - happy path: SessionWithStats returned with correct stats

  update_session()  — PATCH /{session_id}
    - 404: session not found
    - 403: instructor is not master instructor
    - 400: start_date before semester start_date
    - 400: end_date after semester end_date
    - happy path: admin updates fields

  delete_session()  — DELETE /{session_id}
    - 404: session not found
    - 403: instructor is not master instructor
    - 400: has bookings
    - 400: has attendance records
    - 400: has feedback submissions
    - 400: has project associations
    - happy path: no relationships → deleted

Patch paths:
  _BASE  = "app.api.api_v1.endpoints.sessions.crud"
  _STATS = f"{_BASE}.SessionWithStats"
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from datetime import date, datetime

from app.api.api_v1.endpoints.sessions.crud import (
    create_session,
    get_session,
    update_session,
    delete_session,
)
from app.models.user import UserRole

_BASE  = "app.api.api_v1.endpoints.sessions.crud"
_STATS = f"{_BASE}.SessionWithStats"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user(role=UserRole.ADMIN, user_id=42):
    u = MagicMock()
    u.role = role
    u.id = user_id
    return u


def _instructor(user_id=42):
    return _user(role=UserRole.INSTRUCTOR, user_id=user_id)


def _semester(start=date(2026, 4, 1), end=date(2026, 5, 31), master_id=42):
    sem = MagicMock()
    sem.start_date = start
    sem.end_date = end
    sem.master_instructor_id = master_id
    return sem


def _session_mock(semester_id=1, session_id=10):
    s = MagicMock()
    s.id = session_id
    s.semester_id = semester_id
    return s


def _session_data(
    semester_id=1,
    start=date(2026, 4, 15),
    end=date(2026, 5, 15),
):
    sd = MagicMock()
    sd.semester_id = semester_id
    sd.date_start = MagicMock()
    sd.date_start.date.return_value = start
    sd.date_end = MagicMock()
    sd.date_end.date.return_value = end
    sd.model_dump.return_value = {}
    return sd


def _q(first=None, scalar_=0, all_=None):
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.join.return_value = q
    q.first.return_value = first
    q.scalar.return_value = scalar_
    q.all.return_value = all_ or []
    q.delete.return_value = 0
    return q


def _db_seq(*qs):
    """Sequential db.query() mock."""
    db = MagicMock()
    db.query.side_effect = list(qs) + [MagicMock()] * 4
    return db


# ── create_session ─────────────────────────────────────────────────────────────

class TestCreateSession:

    def test_404_semester_not_found(self):
        db = _db_seq(_q(first=None))
        sd = _session_data()
        with pytest.raises(HTTPException) as exc:
            create_session(sd, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_instructor_not_master(self):
        sem = _semester(master_id=99)
        db = _db_seq(_q(first=sem))
        sd = _session_data()
        with pytest.raises(HTTPException) as exc:
            create_session(sd, db=db, current_user=_instructor(user_id=42))
        assert exc.value.status_code == 403
        assert "master instructor" in exc.value.detail.lower()

    def test_403_instructor_lacks_specialization(self):
        sem = _semester(master_id=42)
        db = _db_seq(_q(first=sem))
        sd = _session_data()
        sd.target_specialization = "LFA_PLAYER"  # truthy specialization
        u = _instructor(user_id=42)
        u.can_teach_specialization.return_value = False
        with pytest.raises(HTTPException) as exc:
            create_session(sd, db=db, current_user=u)
        assert exc.value.status_code == 403
        assert "qualification" in exc.value.detail.lower()

    def test_400_start_date_before_semester_start(self):
        sem = _semester(start=date(2026, 4, 1))
        db = _db_seq(_q(first=sem))
        # session starts March 1, semester starts April 1
        sd = _session_data(start=date(2026, 3, 1), end=date(2026, 4, 15))
        with pytest.raises(HTTPException) as exc:
            create_session(sd, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "start date" in exc.value.detail.lower()

    def test_400_end_date_after_semester_end(self):
        sem = _semester(end=date(2026, 5, 31))
        db = _db_seq(_q(first=sem))
        # session ends June 15, semester ends May 31
        sd = _session_data(start=date(2026, 4, 15), end=date(2026, 6, 15))
        with pytest.raises(HTTPException) as exc:
            create_session(sd, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "end date" in exc.value.detail.lower()

    def test_admin_happy_path_adds_and_commits(self):
        sem = _semester()
        db = _db_seq(_q(first=sem))
        sd = _session_data()  # valid dates within semester
        create_session(sd, db=db, current_user=_user(role=UserRole.ADMIN))
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_instructor_as_master_with_no_specialization_succeeds(self):
        sem = _semester(master_id=42)
        db = _db_seq(_q(first=sem))
        sd = _session_data()
        sd.target_specialization = None   # falsy → specialization check skipped
        u = _instructor(user_id=42)
        u.can_teach_specialization.return_value = True
        create_session(sd, db=db, current_user=u)
        db.add.assert_called_once()


# ── get_session ────────────────────────────────────────────────────────────────

class TestGetSession:

    def test_404_session_not_found(self):
        db = _db_seq(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            get_session(session_id=1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_happy_path_returns_stats_via_session_with_stats(self):
        session = _session_mock()
        db = _db_seq(
            _q(first=session),  # q1: session lookup
            _q(scalar_=5),      # q2: total booking count
            _q(scalar_=3),      # q3: confirmed bookings
            _q(scalar_=2),      # q4: waitlisted
            _q(scalar_=8),      # q5: attendance count
            _q(scalar_=4.5),    # q6: avg rating
        )
        with patch(_STATS) as MockStats:
            MockStats.return_value = {"mocked": True}
            result = get_session(session_id=10, db=db, current_user=_user())
        assert MockStats.called
        kw = MockStats.call_args[1]
        assert kw["booking_count"] == 5
        assert kw["confirmed_bookings"] == 3
        assert kw["waitlist_count"] == 2
        assert kw["attendance_count"] == 8
        assert abs(kw["average_rating"] - 4.5) < 0.01

    def test_happy_path_no_avg_rating_returns_none(self):
        session = _session_mock()
        db = _db_seq(
            _q(first=session),
            _q(scalar_=0),
            _q(scalar_=0),
            _q(scalar_=0),
            _q(scalar_=0),
            _q(scalar_=None),   # avg_rating = None
        )
        with patch(_STATS) as MockStats:
            MockStats.return_value = {}
            get_session(session_id=10, db=db, current_user=_user())
        kw = MockStats.call_args[1]
        assert kw["average_rating"] is None


# ── update_session ─────────────────────────────────────────────────────────────

class TestUpdateSession:

    def test_404_session_not_found(self):
        db = _db_seq(_q(first=None))
        su = MagicMock(); su.model_dump.return_value = {}
        with pytest.raises(HTTPException) as exc:
            update_session(1, su, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_instructor_not_master(self):
        session = _session_mock(semester_id=1)
        sem = _semester(master_id=99)
        db = _db_seq(_q(first=session), _q(first=sem))
        su = MagicMock(); su.model_dump.return_value = {}
        with pytest.raises(HTTPException) as exc:
            update_session(1, su, db=db, current_user=_instructor(user_id=42))
        assert exc.value.status_code == 403

    def test_400_start_date_before_semester(self):
        session = _session_mock(semester_id=1)
        sem = _semester(start=date(2026, 4, 1))
        db = _db_seq(_q(first=session), _q(first=sem))
        su = MagicMock()
        su.model_dump.return_value = {"date_start": datetime(2026, 3, 1)}  # before semester start
        with pytest.raises(HTTPException) as exc:
            update_session(1, su, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "start date" in exc.value.detail.lower()

    def test_400_end_date_after_semester(self):
        session = _session_mock(semester_id=1)
        sem = _semester(end=date(2026, 5, 31))
        # session.date_start.date() needed as fallback when date_start not in update_data
        session.date_start = MagicMock()
        session.date_start.date.return_value = date(2026, 4, 15)
        db = _db_seq(_q(first=session), _q(first=sem))
        su = MagicMock()
        su.model_dump.return_value = {"date_end": datetime(2026, 6, 15)}  # after semester end
        with pytest.raises(HTTPException) as exc:
            update_session(1, su, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "end date" in exc.value.detail.lower()

    def test_admin_happy_path_sets_fields_and_commits(self):
        session = _session_mock()
        db = _db_seq(_q(first=session))
        su = MagicMock()
        su.model_dump.return_value = {"capacity": 30, "credit_cost": 5}
        result = update_session(1, su, db=db, current_user=_user(role=UserRole.ADMIN))
        assert session.capacity == 30
        assert session.credit_cost == 5
        db.commit.assert_called_once()


# ── delete_session ─────────────────────────────────────────────────────────────

class TestDeleteSession:
    """All 4 count queries always execute before the relationship check fires."""

    def _delete_db(self, session, bookings=0, attendance=0, feedback=0, projects=0):
        return _db_seq(
            _q(first=session),   # q1: session lookup
            _q(scalar_=bookings),   # q2: booking count
            _q(scalar_=attendance), # q3: attendance count
            _q(scalar_=feedback),   # q4: feedback count
            _q(scalar_=projects),   # q5: project session count
        )

    def test_404_session_not_found(self):
        db = _db_seq(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            delete_session(1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_instructor_not_master(self):
        session = _session_mock(semester_id=1)
        sem = _semester(master_id=99)
        db = _db_seq(_q(first=session), _q(first=sem))
        with pytest.raises(HTTPException) as exc:
            delete_session(1, db=db, current_user=_instructor(user_id=42))
        assert exc.value.status_code == 403

    def test_400_has_bookings(self):
        session = _session_mock()
        db = self._delete_db(session, bookings=2)
        with pytest.raises(HTTPException) as exc:
            delete_session(1, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "bookings" in exc.value.detail.lower()

    def test_400_has_attendance_records(self):
        session = _session_mock()
        db = self._delete_db(session, attendance=3)
        with pytest.raises(HTTPException) as exc:
            delete_session(1, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "attendance" in exc.value.detail.lower()

    def test_400_has_feedback_submissions(self):
        session = _session_mock()
        db = self._delete_db(session, feedback=1)
        with pytest.raises(HTTPException) as exc:
            delete_session(1, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "feedback" in exc.value.detail.lower()

    def test_400_has_project_associations(self):
        session = _session_mock()
        db = self._delete_db(session, projects=4)
        with pytest.raises(HTTPException) as exc:
            delete_session(1, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "project" in exc.value.detail.lower()

    def test_happy_path_no_relationships_deletes_and_commits(self):
        session = _session_mock()
        db = self._delete_db(session, bookings=0, attendance=0, feedback=0, projects=0)
        result = delete_session(1, db=db, current_user=_user())
        db.delete.assert_called_once_with(session)
        db.commit.assert_called_once()
        assert result["message"] == "Session deleted successfully"

    def test_multiple_relationships_all_listed_in_detail(self):
        session = _session_mock()
        db = self._delete_db(session, bookings=2, attendance=3, feedback=1, projects=0)
        with pytest.raises(HTTPException) as exc:
            delete_session(1, db=db, current_user=_user())
        detail = exc.value.detail
        assert "bookings" in detail.lower()
        assert "attendance" in detail.lower()
