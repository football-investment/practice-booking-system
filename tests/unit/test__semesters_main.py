"""
Unit tests for app/api/api_v1/endpoints/_semesters_main.py

Coverage targets:
  create_semester()      — POST /
    - 400: code already exists
    - 400: location validation fails
    - happy path: no tournament config fields
    - happy path: with tournament config → TournamentConfiguration created

  list_semesters()       — GET /
    - admin: all semesters
    - student: filtered semesters
    - instructor: filtered semesters
    - empty list
    - stats calculated per semester (location_type, master_instructor_name)
    - no location / no instructor → None

  get_active_semester()  — GET /active
    - 404: no active semester
    - happy path

  get_semester()         — GET /{semester_id}
    - 404: semester not found
    - happy path: SemesterWithStats with correct stats

  update_semester()      — PATCH /{semester_id}
    - 404: semester not found
    - 400: code already exists
    - same code → no uniqueness check
    - different code + unique → updated

  delete_semester()      — DELETE /{semester_id}
    - 404: semester not found
    - no enrollments → cascade delete + commit
    - with enrollment → refund credits + flush
    - enrollment_cost = None → defaults to 500
    - user not found in refund loop → skip
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints._semesters_main import (
    create_semester,
    list_semesters,
    get_active_semester,
    get_semester,
    update_semester,
    delete_semester,
)
from app.models.user import UserRole

_SEM = "app.api.api_v1.endpoints._semesters_main"
_SWS = f"{_SEM}.SemesterWithStats"
_SLS = f"{_SEM}.SemesterList"
_LVS = f"{_SEM}.LocationValidationService"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user(role=UserRole.ADMIN, user_id=42):
    u = MagicMock()
    u.role = role
    u.id = user_id
    return u


def _q(first=None, all_=None, count_=0, scalar_=0):
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.join.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.first.return_value = first
    q.count.return_value = count_
    q.scalar.return_value = scalar_
    q.all.return_value = all_ or []
    q.delete.return_value = 0
    return q


def _db_seq(*qs):
    db = MagicMock()
    db.query.side_effect = list(qs) + [MagicMock()] * 10
    return db


def _semester_mock():
    s = MagicMock()
    s.id = 1
    s.name = "Test Semester"
    s.code = "SEM-2026-01"
    s.enrollment_cost = 500
    s.location = None
    s.master_instructor = None
    return s


def _semester_data(**overrides):
    sd = MagicMock()
    sd.location_id = None   # explicitly None → skip location validation
    sd.code = "SEM-2026-01"
    sd.specialization_type = "LFA_PLAYER"
    dump = {
        "assignment_type": None,
        "max_players": None,
        "tournament_type_id": None,
        "scoring_type": None,
        "measurement_unit": None,
        "ranking_direction": None,
        "location_city": None,
        "location_venue": None,
        "location_address": None,
        "format": None,
    }
    dump.update(overrides)
    sd.model_dump.return_value = dump
    return sd


# ── create_semester ─────────────────────────────────────────────────────────────

class TestCreateSemester:

    def test_400_code_already_exists(self):
        existing = MagicMock()
        db = _db_seq(_q(first=existing))
        with pytest.raises(HTTPException) as exc:
            create_semester(_semester_data(), db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "code" in exc.value.detail.lower()

    def test_400_location_validation_fails(self):
        db = _db_seq(_q(first=None))
        sd = _semester_data()
        sd.location_id = 5          # triggers location check
        with patch(_LVS) as MockLVS:
            MockLVS.can_create_semester_at_location.return_value = {
                "allowed": False,
                "reason": "PARTNER locations only",
                "location_type": "CENTER",
            }
            with pytest.raises(HTTPException) as exc:
                create_semester(sd, db=db, current_user=_user())
        assert exc.value.status_code == 400

    def test_happy_path_no_tournament_config(self):
        db = _db_seq(_q(first=None))
        sd = _semester_data()       # all config fields None → any() is False
        with patch(f"{_SEM}.Semester") as MockSem:
            MockSem.return_value = MagicMock()
            create_semester(sd, db=db, current_user=_user())
        db.add.assert_called()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_happy_path_with_tournament_config_creates_config(self):
        db = _db_seq(_q(first=None))
        sd = _semester_data(assignment_type="OPEN_ASSIGNMENT", max_players=20)
        with patch(f"{_SEM}.Semester") as MockSem, \
             patch("app.models.tournament_configuration.TournamentConfiguration") as MockTC:
            MockSem.return_value = MagicMock()
            MockTC.return_value = MagicMock()
            create_semester(sd, db=db, current_user=_user())
        # semester + tournament_config both added
        assert db.add.call_count >= 2


# ── list_semesters ──────────────────────────────────────────────────────────────

class TestListSemesters:

    def _stats_db(self, semesters, groups=0, sessions=0, bookings=0, active=0):
        qs = [_q(all_=semesters)]
        for _ in semesters:
            qs += [_q(scalar_=groups), _q(scalar_=sessions),
                   _q(scalar_=bookings), _q(scalar_=active)]
        return _db_seq(*qs)

    def test_admin_sees_all_semesters(self):
        sem = _semester_mock()
        db = self._stats_db([sem], groups=2, sessions=5, bookings=10, active=3)
        with patch(_SWS) as MockSWS, patch(_SLS) as MockSLS:
            MockSWS.return_value = MagicMock()
            MockSLS.return_value = MagicMock()
            list_semesters(db=db, current_user=_user(role=UserRole.ADMIN))
        assert MockSWS.call_count == 1
        kw = MockSWS.call_args[1]
        assert kw["total_groups"] == 2
        assert kw["total_sessions"] == 5
        assert kw["total_bookings"] == 10
        assert kw["active_users"] == 3

    def test_student_sees_filtered_semesters(self):
        sem = _semester_mock()
        db = self._stats_db([sem])
        with patch(_SWS) as MockSWS, patch(_SLS) as MockSLS:
            MockSWS.return_value = MagicMock()
            MockSLS.return_value = MagicMock()
            list_semesters(db=db, current_user=_user(role=UserRole.STUDENT))
        assert MockSWS.call_count == 1

    def test_instructor_sees_filtered_semesters(self):
        sem = _semester_mock()
        db = self._stats_db([sem])
        with patch(_SWS) as MockSWS, patch(_SLS) as MockSLS:
            MockSWS.return_value = MagicMock()
            MockSLS.return_value = MagicMock()
            list_semesters(db=db, current_user=_user(role=UserRole.INSTRUCTOR))
        assert MockSWS.call_count == 1

    def test_empty_list_skips_stats_loop(self):
        db = _db_seq(_q(all_=[]))
        with patch(_SWS) as MockSWS, patch(_SLS) as MockSLS:
            MockSWS.return_value = MagicMock()
            MockSLS.return_value = MagicMock()
            list_semesters(db=db, current_user=_user(role=UserRole.ADMIN))
        assert MockSWS.call_count == 0

    def test_location_type_and_instructor_name_populated(self):
        sem = _semester_mock()
        sem.location = MagicMock()
        sem.location.location_type.value = "CENTER"
        sem.master_instructor = MagicMock()
        sem.master_instructor.name = "Coach Smith"
        sem.master_instructor.email = "coach@test.com"
        db = self._stats_db([sem])
        with patch(_SWS) as MockSWS, patch(_SLS) as MockSLS:
            MockSWS.return_value = MagicMock()
            MockSLS.return_value = MagicMock()
            list_semesters(db=db, current_user=_user(role=UserRole.ADMIN))
        kw = MockSWS.call_args[1]
        assert kw["location_type"] == "CENTER"
        assert kw["master_instructor_name"] == "Coach Smith"
        assert kw["master_instructor_email"] == "coach@test.com"

    def test_no_location_yields_none_fields(self):
        sem = _semester_mock()
        sem.location = None
        sem.master_instructor = None
        db = self._stats_db([sem])
        with patch(_SWS) as MockSWS, patch(_SLS) as MockSLS:
            MockSWS.return_value = MagicMock()
            MockSLS.return_value = MagicMock()
            list_semesters(db=db, current_user=_user(role=UserRole.ADMIN))
        kw = MockSWS.call_args[1]
        assert kw["location_type"] is None
        assert kw["master_instructor_name"] is None
        assert kw["master_instructor_email"] is None


# ── get_active_semester ─────────────────────────────────────────────────────────

class TestGetActiveSemester:

    def test_404_no_active_semester(self):
        db = _db_seq(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            get_active_semester(db=db, current_user=_user())
        assert exc.value.status_code == 404
        assert "active" in exc.value.detail.lower()

    def test_happy_path_returns_semester(self):
        sem = _semester_mock()
        db = _db_seq(_q(first=sem))
        result = get_active_semester(db=db, current_user=_user())
        assert result is sem


# ── get_semester ────────────────────────────────────────────────────────────────

class TestGetSemester:

    def test_404_semester_not_found(self):
        db = _db_seq(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            get_semester(semester_id=1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_happy_path_returns_stats(self):
        sem = _semester_mock()
        db = _db_seq(
            _q(first=sem),      # q1: semester lookup
            _q(scalar_=3),      # q2: total_groups
            _q(scalar_=7),      # q3: total_sessions
            _q(scalar_=15),     # q4: total_bookings
            _q(scalar_=6),      # q5: active_users
        )
        with patch(_SWS) as MockSWS:
            MockSWS.return_value = {"stats": True}
            result = get_semester(semester_id=1, db=db, current_user=_user())
        kw = MockSWS.call_args[1]
        assert kw["total_groups"] == 3
        assert kw["total_sessions"] == 7
        assert kw["total_bookings"] == 15
        assert kw["active_users"] == 6


# ── update_semester ─────────────────────────────────────────────────────────────

class TestUpdateSemester:

    def test_404_semester_not_found(self):
        db = _db_seq(_q(first=None))
        su = MagicMock()
        su.code = "NEW-CODE"
        su.model_dump.return_value = {}
        with pytest.raises(HTTPException) as exc:
            update_semester(1, su, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_400_code_already_exists(self):
        sem = _semester_mock()
        sem.code = "OLD-CODE"
        db = _db_seq(_q(first=sem), _q(first=MagicMock()))  # q2: code conflict
        su = MagicMock()
        su.code = "NEW-CODE"
        su.model_dump.return_value = {}
        with pytest.raises(HTTPException) as exc:
            update_semester(1, su, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "code" in exc.value.detail.lower()

    def test_same_code_skips_uniqueness_check(self):
        sem = _semester_mock()
        sem.code = "SAME-CODE"
        db = _db_seq(_q(first=sem))     # no q2 needed
        su = MagicMock()
        su.code = "SAME-CODE"
        su.model_dump.return_value = {"capacity": 30}
        update_semester(1, su, db=db, current_user=_user())
        db.commit.assert_called_once()

    def test_happy_path_updates_fields_and_commits(self):
        sem = _semester_mock()
        sem.code = "OLD-CODE"
        db = _db_seq(_q(first=sem), _q(first=None))     # q2: no conflict
        su = MagicMock()
        su.code = "NEW-CODE"
        su.model_dump.return_value = {"name": "Updated Name"}
        update_semester(1, su, db=db, current_user=_user())
        assert sem.name == "Updated Name"
        db.commit.assert_called_once()


# ── delete_semester ─────────────────────────────────────────────────────────────

class TestDeleteSemester:

    def _delete_db(self, semester, enrollments=None):
        enr_list = enrollments or []
        qs = [
            _q(first=semester),     # q1: Semester lookup
            _q(all_=enr_list),      # q2: SemesterEnrollment query
        ]
        for enr in enr_list:
            qs.append(_q(first=enr._user_obj))   # User lookup per enrollment
        for _ in range(6):
            qs.append(_q())                       # 6 cascade delete queries
        return _db_seq(*qs)

    def _enrollment(self, user_id=42, user_license_id=10, balance=1000):
        e = MagicMock()
        e.user_id = user_id
        e.user_license_id = user_license_id
        u = MagicMock()
        u.id = user_id
        u.credit_balance = balance
        e._user_obj = u
        return e

    def test_404_semester_not_found(self):
        db = _db_seq(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            delete_semester(1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_no_enrollments_cascade_deletes_and_commits(self):
        sem = _semester_mock()
        db = self._delete_db(sem, enrollments=[])
        result = delete_semester(1, db=db, current_user=_user())
        db.delete.assert_called_once_with(sem)
        db.commit.assert_called_once()
        assert "deleted" in result["message"].lower()
        assert result["refunded_users"] == 0

    def test_with_enrollment_refunds_user_credits(self):
        sem = _semester_mock()
        sem.enrollment_cost = 300
        enr = self._enrollment(user_id=42, balance=1000)
        db = self._delete_db(sem, enrollments=[enr])
        result = delete_semester(1, db=db, current_user=_user())
        assert enr._user_obj.credit_balance == 1300   # 1000 + 300 refunded
        assert result["refunded_users"] == 1
        assert result["refund_amount_per_user"] == 300
        db.flush.assert_called()

    def test_enrollment_cost_defaults_to_500_when_none(self):
        sem = _semester_mock()
        sem.enrollment_cost = None
        enr = self._enrollment(balance=0)
        db = self._delete_db(sem, enrollments=[enr])
        result = delete_semester(1, db=db, current_user=_user())
        assert result["refund_amount_per_user"] == 500
        assert enr._user_obj.credit_balance == 500

    def test_user_not_found_in_loop_skips_refund(self):
        sem = _semester_mock()
        sem.enrollment_cost = 200
        enr = self._enrollment()
        enr._user_obj = None    # User query returns None → no refund
        db = self._delete_db(sem, enrollments=[enr])
        result = delete_semester(1, db=db, current_user=_user())
        assert result["refunded_users"] == 0
