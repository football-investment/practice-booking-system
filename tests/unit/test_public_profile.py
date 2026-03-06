"""
Unit tests for app/api/api_v1/endpoints/public_profile.py

Coverage targets:
  get_lfa_player_profile() — GET /users/{user_id}/profile/lfa-player
    - 404: user not found (fetchone returns None)
    - 404: no active LFA Player license (second fetchone returns None)
    - happy path: returns all expected fields
    - DOB-based age_group: PRE (<7), YOUTH (7-14), AMATEUR (15+)
    - no DOB → defaults to AMATEUR
    - motivation_scores dict → position_preference extracted
    - no motivation_scores → position_preference "Unknown"
    - assessments list populated from fetchall

  get_basic_profile() — GET /users/{user_id}/profile/basic
    - 404: user not found
    - happy path: returns user + licenses list
    - empty licenses list returns empty array

  get_instructor_profile() — GET /users/{user_id}/profile/instructor
    - 404: user not found (db.query(User).first() returns None)
    - happy path: licenses list with belt info
    - PLAYER specialization: belt_name and belt_emoji present
    - COACH specialization: belt_name and belt_emoji present
    - INTERNSHIP specialization: belt_name and belt_emoji present
    - unknown specialization: generic belt_name "Level X"
    - availability_windows_count returned

Mock strategy:
  get_lfa_player_profile / get_basic_profile: db.execute().fetchone.side_effect
  get_instructor_profile: sequential db.query() calls
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date, datetime
from fastapi import HTTPException

from app.api.api_v1.endpoints.public_profile import (
    get_lfa_player_profile,
    get_basic_profile,
    get_instructor_profile,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user_row(user_id=10, name="Test User", dob=None, nationality="HU", credits=100):
    """Simulates a raw SQL row for the users table (index-based access)."""
    row = MagicMock()
    row.__getitem__ = lambda self, i: [user_id, f"u{user_id}@test.com", name, dob, nationality, credits][i]
    row.__bool__ = lambda self: True
    return row


def _license_row(level=3, max_level=5, heading=75.0, overall=72.0, motivation=None):
    """Simulates a raw SQL row for the lfa_player_licenses join query (index-based)."""
    from datetime import datetime as dt
    created = dt(2024, 1, 1)
    row = MagicMock()
    # Indices: 0=id, 1=age_group, 2=credit_balance, 3=heading, 4=shooting,
    #          5=crossing, 6=passing, 7=dribbling, 8=ball_control, 9=defending,
    #          10=overall, 11=created_at, 12=current_level, 13=max_level, 14=motivation
    values = [1, "AMATEUR", 0, heading, heading, heading, heading, heading, heading, heading,
              overall, created, level, max_level, motivation]
    row.__getitem__ = lambda self, i: values[i]
    row.__bool__ = lambda self: True
    return row


def _assessment_row(skill="heading", pct=80.0):
    """Simulates a raw SQL row for football_skill_assessments."""
    from datetime import datetime as dt
    row = MagicMock()
    values = [skill, 8, 10, pct, dt(2024, 6, 1), "Coach Name"]
    row.__getitem__ = lambda self, i: values[i]
    return row


def _execute_db(fetchone_values=None, fetchall_value=None):
    """db.execute().fetchone.side_effect + fetchall."""
    db = MagicMock()
    ex = MagicMock()
    ex.fetchone.side_effect = list(fetchone_values or [])
    ex.fetchall.return_value = fetchall_value or []
    db.execute.return_value = ex
    return db


def _q(first=None, all_=None, count_=0):
    q = MagicMock()
    q.filter.return_value = q
    q.all.return_value = all_ or []
    q.first.return_value = first
    q.count.return_value = count_
    return q


def _profile_db(user=None, licenses=None, avail_count=0):
    """Sequential db for get_instructor_profile: q1=User, q2=UserLicense, q3=AvailabilityWindow."""
    db = MagicMock()
    db.query.side_effect = [
        _q(first=user),
        _q(all_=licenses or []),
        _q(count_=avail_count),
    ] + [MagicMock()] * 3
    return db


# ── get_lfa_player_profile ────────────────────────────────────────────────────

class TestGetLfaPlayerProfile:

    def test_404_when_user_not_found(self):
        db = _execute_db(fetchone_values=[None])
        with pytest.raises(HTTPException) as exc:
            get_lfa_player_profile(user_id=99, db=db)
        assert exc.value.status_code == 404

    def test_404_when_no_active_license(self):
        user = _user_row()
        db = _execute_db(fetchone_values=[user, None])
        with pytest.raises(HTTPException) as exc:
            get_lfa_player_profile(user_id=10, db=db)
        assert exc.value.status_code == 404

    def test_happy_path_returns_expected_fields(self):
        user = _user_row(dob=None)
        lic = _license_row()
        db = _execute_db(fetchone_values=[user, lic], fetchall_value=[])
        result = get_lfa_player_profile(user_id=10, db=db)
        assert result["user_id"] == 10
        assert "skills" in result
        assert "overall_rating" in result
        assert "age_group" in result
        assert "level" in result

    def test_age_group_pre_for_child_under_7(self):
        today = datetime.today()
        dob = MagicMock()
        dob.year = today.year - 5
        dob.month = 1
        dob.day = 1
        dob.isoformat.return_value = f"{today.year - 5}-01-01"
        user = _user_row(dob=dob)
        lic = _license_row()
        db = _execute_db(fetchone_values=[user, lic], fetchall_value=[])
        result = get_lfa_player_profile(user_id=10, db=db)
        assert result["age_group"] == "PRE"

    def test_age_group_youth_for_child_7_to_14(self):
        today = datetime.today()
        dob = MagicMock()
        dob.year = today.year - 10
        dob.month = 1
        dob.day = 1
        dob.isoformat.return_value = f"{today.year - 10}-01-01"
        user = _user_row(dob=dob)
        lic = _license_row()
        db = _execute_db(fetchone_values=[user, lic], fetchall_value=[])
        result = get_lfa_player_profile(user_id=10, db=db)
        assert result["age_group"] == "YOUTH"

    def test_age_group_amateur_for_adult(self):
        today = datetime.today()
        dob = MagicMock()
        dob.year = today.year - 20
        dob.month = 1
        dob.day = 1
        dob.isoformat.return_value = f"{today.year - 20}-01-01"
        user = _user_row(dob=dob)
        lic = _license_row()
        db = _execute_db(fetchone_values=[user, lic], fetchall_value=[])
        result = get_lfa_player_profile(user_id=10, db=db)
        assert result["age_group"] == "AMATEUR"

    def test_no_dob_defaults_to_amateur(self):
        user = _user_row(dob=None)
        lic = _license_row()
        db = _execute_db(fetchone_values=[user, lic], fetchall_value=[])
        result = get_lfa_player_profile(user_id=10, db=db)
        assert result["age_group"] == "AMATEUR"

    def test_position_from_motivation_scores(self):
        motivation = {"preferred_position": "Striker"}
        user = _user_row(dob=None)
        lic = _license_row(motivation=motivation)
        db = _execute_db(fetchone_values=[user, lic], fetchall_value=[])
        result = get_lfa_player_profile(user_id=10, db=db)
        assert result["position"] == "Striker"

    def test_position_unknown_when_no_motivation(self):
        user = _user_row(dob=None)
        lic = _license_row(motivation=None)
        db = _execute_db(fetchone_values=[user, lic], fetchall_value=[])
        result = get_lfa_player_profile(user_id=10, db=db)
        assert result["position"] == "Unknown"

    def test_assessments_populated_from_fetchall(self):
        user = _user_row(dob=None)
        lic = _license_row()
        a1 = _assessment_row("heading", 80.0)
        a2 = _assessment_row("shooting", 65.0)
        db = _execute_db(fetchone_values=[user, lic], fetchall_value=[a1, a2])
        result = get_lfa_player_profile(user_id=10, db=db)
        assert len(result["recent_assessments"]) == 2
        assert result["recent_assessments"][0]["skill_name"] == "heading"


# ── get_basic_profile ─────────────────────────────────────────────────────────

class TestGetBasicProfile:

    def _lic_row(self, spec="LFA_PLAYER_PRE", level=1):
        row = MagicMock()
        from datetime import datetime as dt
        values = [spec, level, level + 2, dt(2024, 1, 1)]
        row.__getitem__ = lambda self, i: values[i]
        return row

    def test_404_when_user_not_found(self):
        db = _execute_db(fetchone_values=[None])
        with pytest.raises(HTTPException) as exc:
            get_basic_profile(user_id=99, db=db)
        assert exc.value.status_code == 404

    def test_happy_path_returns_user_and_licenses(self):
        user = _user_row()
        lic = self._lic_row()
        ex = MagicMock()
        ex.fetchone.return_value = user
        ex.fetchall.return_value = [lic]
        db = MagicMock()
        db.execute.return_value = ex
        result = get_basic_profile(user_id=10, db=db)
        assert result["user_id"] == 10
        assert len(result["licenses"]) == 1
        assert result["licenses"][0]["specialization"] == "LFA_PLAYER_PRE"

    def test_empty_licenses_returns_empty_list(self):
        user = _user_row()
        ex = MagicMock()
        ex.fetchone.return_value = user
        ex.fetchall.return_value = []
        db = MagicMock()
        db.execute.return_value = ex
        result = get_basic_profile(user_id=10, db=db)
        assert result["licenses"] == []

    def test_response_has_credit_balance(self):
        user = _user_row(credits=250)
        ex = MagicMock()
        ex.fetchone.return_value = user
        ex.fetchall.return_value = []
        db = MagicMock()
        db.execute.return_value = ex
        result = get_basic_profile(user_id=10, db=db)
        assert result["credit_balance"] == 250


# ── get_instructor_profile ────────────────────────────────────────────────────

class TestGetInstructorProfile:

    def _lic(self, spec="PLAYER", level=3):
        lic = MagicMock()
        lic.id = 1
        lic.specialization_type = spec
        lic.current_level = level
        lic.max_achieved_level = level + 1
        lic.started_at = None
        lic.last_advanced_at = None
        lic.is_active = True
        lic.expires_at = None
        lic.last_renewed_at = None
        lic.renewal_cost = 0
        return lic

    def _inst_user(self, user_id=42):
        u = MagicMock()
        u.id = user_id
        u.name = "Instructor A"
        u.email = f"inst{user_id}@lfa.hu"
        u.nationality = "HU"
        u.date_of_birth = None
        u.credit_balance = 0
        u.is_active = True
        u.created_at = None
        return u

    def test_404_when_user_not_found(self):
        db = _profile_db(user=None)
        with pytest.raises(HTTPException) as exc:
            get_instructor_profile(user_id=99, db=db)
        assert exc.value.status_code == 404

    def test_happy_path_returns_profile_fields(self):
        u = self._inst_user()
        db = _profile_db(user=u, licenses=[], avail_count=3)
        result = get_instructor_profile(user_id=42, db=db)
        assert result["user_id"] == 42
        assert result["availability_windows_count"] == 3
        assert "licenses" in result

    def test_player_specialization_has_belt_name(self):
        u = self._inst_user()
        lic = self._lic(spec="PLAYER", level=1)
        db = _profile_db(user=u, licenses=[lic])
        result = get_instructor_profile(user_id=42, db=db)
        assert result["licenses"][0]["belt_name"] == "Bamboo Student (White)"
        assert result["licenses"][0]["belt_emoji"] == "🤍"

    def test_coach_specialization_has_belt_name(self):
        u = self._inst_user()
        lic = self._lic(spec="COACH", level=2)
        db = _profile_db(user=u, licenses=[lic])
        result = get_instructor_profile(user_id=42, db=db)
        assert result["licenses"][0]["belt_name"] == "LFA PRE Head"
        assert result["licenses"][0]["belt_emoji"] == "👨‍🏫"

    def test_internship_specialization_has_belt_name(self):
        u = self._inst_user()
        lic = self._lic(spec="INTERNSHIP", level=3)
        db = _profile_db(user=u, licenses=[lic])
        result = get_instructor_profile(user_id=42, db=db)
        assert result["licenses"][0]["belt_name"] == "Senior Intern"

    def test_unknown_specialization_uses_generic_belt_name(self):
        u = self._inst_user()
        lic = self._lic(spec="LFA_PLAYER_PRE", level=4)
        db = _profile_db(user=u, licenses=[lic])
        result = get_instructor_profile(user_id=42, db=db)
        assert result["licenses"][0]["belt_name"] == "Level 4"
        assert result["licenses"][0]["belt_emoji"] == "🎓"

    def test_license_count_matches_licenses_list(self):
        u = self._inst_user()
        lics = [self._lic(spec="PLAYER"), self._lic(spec="COACH")]
        db = _profile_db(user=u, licenses=lics)
        result = get_instructor_profile(user_id=42, db=db)
        assert result["license_count"] == 2
        assert len(result["licenses"]) == 2
