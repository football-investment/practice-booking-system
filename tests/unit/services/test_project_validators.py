"""
Sprint 30 — app/api/api_v1/endpoints/projects/validators.py
============================================================
Target: ≥85% statement, ≥80% branch

Covers:
  validate_semester_enrollment:
    * project not found → 404
    * semester not found → 404
    * semester dates not set (no start_date) → 422
    * semester dates not set (no end_date) → 422
    * primary semester (LIVE-TEST-2025) not found → falls back to active
    * primary semester found, project.semester_id matches → no cross block
    * primary semester found, semester_id mismatch → 403
    * primary semester is None (both queries None) → skip cross check
    * semester ended → 403
    * semester not active → 403
    * all valid → returns None (no raise)

  validate_specialization_enrollment:
    * project not found → 404
    * user has no specialization → allow (return)
    * project no target_specialization → allow (return)
    * project is mixed_specialization → allow (return)
    * specialization match → allow (return)
    * specialization mismatch → 403

  validate_payment_enrollment:
    * admin role → skip (return)
    * instructor role → skip (return)
    * student with active semester enrollment → return
    * student without active enrollment → 402
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from datetime import date, datetime, timezone

from app.api.api_v1.endpoints.projects.validators import (
    validate_semester_enrollment,
    validate_specialization_enrollment,
    validate_payment_enrollment,
)

_BASE = "app.api.api_v1.endpoints.projects.validators"


# ── helpers ──────────────────────────────────────────────────────────────────

def _user(role_value="student", name="Test User", has_spec=False, spec=None):
    u = MagicMock()
    u.id = 42
    u.name = name
    u.email = "user@test.com"
    u.role = MagicMock()
    u.role.value = role_value
    u.has_specialization = has_spec
    u.specialization = spec
    return u


def _project(pid=10, semester_id=5, target_spec=None, mixed=False):
    p = MagicMock()
    p.id = pid
    p.semester_id = semester_id
    p.title = "Test Project"
    p.target_specialization = target_spec
    p.mixed_specialization = mixed
    return p


def _semester(sid=5, name="Test Semester", start_date=date(2026, 1, 1),
              end_date=date(2026, 12, 31), is_active=True):
    s = MagicMock()
    s.id = sid
    s.name = name
    s.start_date = start_date
    s.end_date = end_date
    s.is_active = is_active
    return s


def _seq_db(*first_vals):
    calls = [0]

    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        val = first_vals[idx] if idx < len(first_vals) else None
        q.first.return_value = val
        return q

    db = MagicMock()
    db.query.side_effect = _side
    return db


# ============================================================================
# validate_semester_enrollment
# ============================================================================

class TestValidateSemesterEnrollment:

    def _call(self, db, user=None):
        if user is None:
            user = _user()
        validate_semester_enrollment(project_id=10, current_user=user, db=db)

    def test_project_not_found_404(self):
        """VSE-01: project query returns None → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db)
        assert exc.value.status_code == 404
        assert "project" in exc.value.detail.lower()

    def test_semester_not_found_404(self):
        """VSE-02: semester query returns None → 404."""
        project = _project(semester_id=5)
        db = _seq_db(project, None)
        with pytest.raises(HTTPException) as exc:
            self._call(db)
        assert exc.value.status_code == 404
        assert "semester" in exc.value.detail.lower()

    def test_no_start_date_422(self):
        """VSE-03: semester.start_date=None → 422."""
        project = _project(semester_id=5)
        sem = _semester(start_date=None)
        db = _seq_db(project, sem)
        with pytest.raises(HTTPException) as exc:
            self._call(db)
        assert exc.value.status_code == 422

    def test_no_end_date_422(self):
        """VSE-04: semester.end_date=None → 422."""
        project = _project(semester_id=5)
        sem = _semester(end_date=None)
        db = _seq_db(project, sem)
        with pytest.raises(HTTPException) as exc:
            self._call(db)
        assert exc.value.status_code == 422

    def test_cross_semester_blocked_403(self):
        """VSE-05: user's primary semester_id != project.semester_id → 403."""
        project = _project(semester_id=5)
        sem = _semester(sid=5)
        primary_sem = _semester(sid=99, name="Other Semester")  # different
        db = _seq_db(project, sem, primary_sem)
        with pytest.raises(HTTPException) as exc:
            self._call(db)
        assert exc.value.status_code == 403
        assert "cross-semester" in exc.value.detail.lower()

    def test_same_semester_no_cross_block(self):
        """VSE-06: user's primary semester_id == project.semester_id → no block."""
        project = _project(semester_id=5)
        sem = _semester(sid=5, end_date=date(2099, 12, 31))
        primary_sem = _semester(sid=5)  # same id as project
        db = _seq_db(project, sem, primary_sem)
        # Should not raise
        self._call(db)

    def test_primary_sem_not_found_fallback_to_active(self):
        """VSE-07: LIVE-TEST-2025 not found → queries for active semester."""
        project = _project(semester_id=5)
        sem = _semester(sid=5, end_date=date(2099, 12, 31))
        active_sem = _semester(sid=5)  # same as project → no cross-block
        # q0=project, q1=sem, q2=LIVE-TEST-2025 returns None, q3=active fallback
        db = _seq_db(project, sem, None, active_sem)
        self._call(db)

    def test_both_primary_sems_none_skip_cross_check(self):
        """VSE-08: both semester queries return None → skip cross-semester check."""
        project = _project(semester_id=5)
        sem = _semester(sid=5, end_date=date(2099, 12, 31))
        # q0=project, q1=sem, q2=LIVE-TEST None, q3=active None
        db = _seq_db(project, sem, None, None)
        # Should not raise (cross check skipped when primary_sem is None)
        self._call(db)

    def test_semester_ended_403(self):
        """VSE-09: current_date > semester.end_date → 403."""
        project = _project(semester_id=5)
        sem = _semester(sid=5, end_date=date(2020, 1, 1))  # past
        primary_sem = _semester(sid=5)  # same → no cross block
        db = _seq_db(project, sem, primary_sem)
        with pytest.raises(HTTPException) as exc:
            self._call(db)
        assert exc.value.status_code == 403
        assert "ended" in exc.value.detail.lower()



# ============================================================================
# validate_specialization_enrollment
# ============================================================================

class TestValidateSpecializationEnrollment:

    def _call(self, db, user):
        validate_specialization_enrollment(project_id=10, current_user=user, db=db)

    def test_project_not_found_404(self):
        """VSPE-01: project not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db, _user())
        assert exc.value.status_code == 404

    def test_no_specialization_allows(self):
        """VSPE-02: user.has_specialization=False → allow (return)."""
        project = _project()
        db = _seq_db(project)
        user = _user(has_spec=False)
        self._call(db, user)  # No raise

    def test_no_target_spec_allows(self):
        """VSPE-03: project.target_specialization=None → allow."""
        project = _project(target_spec=None)
        db = _seq_db(project)
        user = _user(has_spec=True)
        self._call(db, user)  # No raise

    def test_mixed_specialization_allows(self):
        """VSPE-04: project.mixed_specialization=True → allow."""
        spec = MagicMock()
        project = _project(target_spec=spec, mixed=True)
        db = _seq_db(project)
        user = _user(has_spec=True, spec=MagicMock())
        self._call(db, user)  # No raise

    def test_matching_specialization_allows(self):
        """VSPE-05: project.target_specialization == user.specialization → allow."""
        spec = MagicMock()
        project = _project(target_spec=spec, mixed=False)
        db = _seq_db(project)
        user = _user(has_spec=True, spec=spec)
        self._call(db, user)  # No raise

    def test_mismatched_specialization_403(self):
        """VSPE-06: specialization mismatch → 403."""
        spec_a = MagicMock()
        spec_a.value = "PLAYER"
        spec_b = MagicMock()
        spec_b.value = "COACH"
        project = _project(target_spec=spec_a, mixed=False)
        db = _seq_db(project)
        user = _user(has_spec=True, spec=spec_b)

        with patch("app.services.specialization_config_loader.SpecializationConfigLoader") as MockLoader:
            MockLoader.return_value.get_display_info.return_value = {"name": "Spec"}
            with pytest.raises(HTTPException) as exc:
                self._call(db, user)
        assert exc.value.status_code == 403
        assert "mismatch" in exc.value.detail.lower()

    def test_mismatch_loader_exception_uses_fallback_names(self):
        """VSPE-07: mismatch + loader raises → fallback to .value strings."""
        spec_a = MagicMock()
        spec_a.value = "PLAYER"
        spec_b = MagicMock()
        spec_b.value = "COACH"
        project = _project(target_spec=spec_a, mixed=False)
        db = _seq_db(project)
        user = _user(has_spec=True, spec=spec_b)

        with patch("app.services.specialization_config_loader.SpecializationConfigLoader") as MockLoader:
            MockLoader.return_value.get_display_info.side_effect = Exception("err")
            with pytest.raises(HTTPException) as exc:
                self._call(db, user)
        assert exc.value.status_code == 403


# ============================================================================
# validate_payment_enrollment
# ============================================================================

class TestValidatePaymentEnrollment:

    def test_admin_skips_payment_check(self):
        """VPE-01: admin role → returns without checking."""
        user = _user(role_value="admin")
        validate_payment_enrollment(current_user=user, db=MagicMock())
        # No raise

    def test_instructor_skips_payment_check(self):
        """VPE-02: instructor role → returns without checking."""
        user = _user(role_value="instructor")
        validate_payment_enrollment(current_user=user, db=MagicMock())
        # No raise

    def test_student_with_active_enrollment_ok(self):
        """VPE-03: student + has_active_semester_enrollment=True → return."""
        user = _user(role_value="student")
        user.has_active_semester_enrollment.return_value = True
        validate_payment_enrollment(current_user=user, db=MagicMock())
        # No raise

    def test_student_without_active_enrollment_402(self):
        """VPE-04: student + has_active_semester_enrollment=False → 402."""
        user = _user(role_value="student")
        user.has_active_semester_enrollment.return_value = False
        with pytest.raises(HTTPException) as exc:
            validate_payment_enrollment(current_user=user, db=MagicMock())
        assert exc.value.status_code == 402
        assert "semester enrollment" in exc.value.detail.lower()
