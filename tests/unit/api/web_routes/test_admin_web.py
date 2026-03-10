"""
Unit tests for app/api/web_routes/admin.py

Covers:
  admin_users_page — 403 guard, success
  admin_semesters_page — success
  admin_coupons_page — empty + with coupon loop (is_valid)
  admin_invitation_codes_page — empty + with code (used_by/created_by lookup)
  admin_analytics_page — 5 count queries
  admin_payments_page — options/joinedload chain
  instructor_enrollments_page — empty semesters
  instructor_edit_student_skills_page — success GET + student not found 404
  instructor_update_student_skills — POST success
  motivation_assessment_page — success GET
  motivation_assessment_submit — POST success

Mock strategy:
  - db = MagicMock(); configure specific return chains per route
  - patch("app.api.web_routes.admin.templates") for TemplateResponse
  - patch("app.api.web_routes.admin.AuditService") for audit log calls
  - asyncio.run(endpoint(...)) calls async functions directly
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.api.web_routes.admin import (
    admin_users_page,
    admin_semesters_page,
    admin_coupons_page,
    admin_invitation_codes_page,
    admin_analytics_page,
    admin_payments_page,
    motivation_assessment_page,
    motivation_assessment_submit,
)
from app.api.web_routes.instructor_dashboard import (
    instructor_enrollments_page,
    instructor_edit_student_skills_page,
    instructor_update_student_skills,
)
from app.models.user import UserRole


_BASE = "app.api.web_routes.admin"
_INSTRUCTOR_BASE = "app.api.web_routes.instructor_dashboard"


def _admin(uid=1):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.ADMIN
    u.name = "Admin User"
    return u


def _instructor(uid=42):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.INSTRUCTOR
    u.name = "Instructor"
    return u


def _student_user(uid=99):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.STUDENT
    u.name = "Student"
    return u


def _req():
    return MagicMock()


def _run(coro):
    return asyncio.run(coro)


# ──────────────────────────────────────────────────────────────────────────────
# admin_users_page
# ──────────────────────────────────────────────────────────────────────────────

class TestAdminUsersPage:

    def test_not_admin_raises_403(self):
        user = _instructor()
        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            _run(admin_users_page(request=_req(), db=db, user=user))
        assert exc_info.value.status_code == 403

    def test_admin_renders_users_template(self):
        user = _admin()
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(admin_users_page(request=_req(), db=db, user=user))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "admin/users.html"


# ──────────────────────────────────────────────────────────────────────────────
# admin_semesters_page
# ──────────────────────────────────────────────────────────────────────────────

class TestAdminSemestersPage:

    def test_not_admin_raises_403(self):
        user = _instructor()
        with pytest.raises(HTTPException) as exc_info:
            _run(admin_semesters_page(request=_req(), db=MagicMock(), user=user))
        assert exc_info.value.status_code == 403

    def test_admin_renders_semesters_template(self):
        user = _admin()
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(admin_semesters_page(request=_req(), db=db, user=user))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "admin/semesters.html"


# ──────────────────────────────────────────────────────────────────────────────
# admin_coupons_page
# ──────────────────────────────────────────────────────────────────────────────

class TestAdminCouponsPage:

    def test_not_admin_raises_403(self):
        user = _instructor()
        with pytest.raises(HTTPException) as exc_info:
            _run(admin_coupons_page(request=_req(), db=MagicMock(), user=user))
        assert exc_info.value.status_code == 403

    def test_empty_coupons_renders_template(self):
        user = _admin()
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(admin_coupons_page(request=_req(), db=db, user=user))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "admin/coupons.html"

    def test_with_coupon_calls_is_valid(self):
        """Loop over coupons calls coupon.is_valid() for each."""
        user = _admin()
        coupon = MagicMock()
        coupon.is_valid.return_value = True
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = [coupon]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(admin_coupons_page(request=_req(), db=db, user=user))

        coupon.is_valid.assert_called_once()
        assert coupon.is_currently_valid is True


# ──────────────────────────────────────────────────────────────────────────────
# admin_invitation_codes_page
# ──────────────────────────────────────────────────────────────────────────────

class TestAdminInvitationCodesPage:

    def test_not_admin_raises_403(self):
        user = _instructor()
        with pytest.raises(HTTPException) as exc_info:
            _run(admin_invitation_codes_page(request=_req(), db=MagicMock(), user=user))
        assert exc_info.value.status_code == 403

    def test_empty_codes_renders_template(self):
        user = _admin()
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(admin_invitation_codes_page(request=_req(), db=db, user=user))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "admin/invitation_codes.html"

    def test_code_with_used_and_created_by_enriched(self):
        """Code with used_by_user_id + created_by_admin_id → user lookup queries."""
        user = _admin()
        code = MagicMock()
        code.used_by_user_id = 99
        code.created_by_admin_id = 1
        used_user = MagicMock()
        used_user.name = "Used By User"
        admin_user = MagicMock()
        admin_user.name = "Admin Creator"
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = [code]
        # Each inner db.query(User).filter().first() call → used_user, then admin_user
        db.query.return_value.filter.return_value.first.side_effect = [used_user, admin_user]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(admin_invitation_codes_page(request=_req(), db=db, user=user))

        assert code.used_by_name == "Used By User"
        assert code.created_by_name == "Admin Creator"

    def test_code_with_none_user_ids_sets_none_names(self):
        """Both IDs None → else branches: used_by_name=None, created_by_name=None."""
        user = _admin()
        code = MagicMock()
        code.used_by_user_id = None
        code.created_by_admin_id = None
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = [code]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(admin_invitation_codes_page(request=_req(), db=db, user=user))

        assert code.used_by_name is None
        assert code.created_by_name is None

    def test_code_user_lookup_returns_none(self):
        """used_by_user_id set but DB returns None → ternary False → used_by_name=None."""
        user = _admin()
        code = MagicMock()
        code.used_by_user_id = 99
        code.created_by_admin_id = None  # skip created_by branch
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = [code]
        db.query.return_value.filter.return_value.first.return_value = None  # user not found

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(admin_invitation_codes_page(request=_req(), db=db, user=user))

        assert code.used_by_name is None


# ──────────────────────────────────────────────────────────────────────────────
# admin_analytics_page
# ──────────────────────────────────────────────────────────────────────────────

class TestAdminAnalyticsPage:

    def test_not_admin_raises_403(self):
        user = _instructor()
        with pytest.raises(HTTPException) as exc_info:
            _run(admin_analytics_page(request=_req(), db=MagicMock(), user=user))
        assert exc_info.value.status_code == 403

    def test_renders_with_count_stats(self):
        """5 count queries: total_users, students, instructors, sessions, bookings."""
        user = _admin()
        db = MagicMock()
        db.query.return_value.count.return_value = 200        # total_users, total_sessions, total_bookings
        db.query.return_value.filter.return_value.count.return_value = 75  # students, instructors

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(admin_analytics_page(request=_req(), db=db, user=user))

        ctx = mock_tmpl.TemplateResponse.call_args.args[1]
        stats = ctx["stats"]
        assert stats["total_users"] == 200
        assert stats["total_students"] == 75


# ──────────────────────────────────────────────────────────────────────────────
# admin_payments_page
# ──────────────────────────────────────────────────────────────────────────────

class TestAdminPaymentsPage:

    def test_not_admin_raises_403(self):
        user = _instructor()
        with pytest.raises(HTTPException) as exc_info:
            _run(admin_payments_page(request=_req(), db=MagicMock(), user=user))
        assert exc_info.value.status_code == 403

    def test_renders_payments_template(self):
        """options/joinedload chain for invoice_requests + newcomer_licenses."""
        user = _admin()
        db = MagicMock()
        # invoice_requests: options().order_by().all()
        db.query.return_value.options.return_value.order_by.return_value.all.return_value = []
        # all_enrollments: plain .all()
        db.query.return_value.all.return_value = []
        # newcomer_licenses: options().filter().order_by().all()
        db.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = []

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(admin_payments_page(request=_req(), db=db, user=user))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "admin/payments.html"

    def test_with_active_enrollments_covers_notin_branch(self):
        """all_enrollments non-empty → enrollment_license_ids truthy → notin_ filter applied."""
        user = _admin()
        enrollment = MagicMock()
        db = MagicMock()
        # invoice_requests: options().order_by().all()
        db.query.return_value.options.return_value.order_by.return_value.all.return_value = []
        # all_enrollments: plain .all()
        db.query.return_value.all.return_value = [enrollment]
        # newcomer_licenses: options().filter().order_by().all()
        db.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = []

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(admin_payments_page(request=_req(), db=db, user=user))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "admin/payments.html"


# ──────────────────────────────────────────────────────────────────────────────
# instructor_enrollments_page
# ──────────────────────────────────────────────────────────────────────────────

class TestInstructorEnrollmentsPage:

    def test_not_instructor_raises_403(self):
        user = _student_user()
        with pytest.raises(HTTPException) as exc_info:
            _run(instructor_enrollments_page(request=_req(), db=MagicMock(), user=user))
        assert exc_info.value.status_code == 403

    def test_renders_with_empty_semesters(self):
        user = _instructor()
        db = MagicMock()
        # instructor_semesters: filter().order_by().all() → []
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        with patch(f"{_INSTRUCTOR_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(instructor_enrollments_page(request=_req(), db=db, user=user))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "instructor/enrollments.html"

    def test_with_semesters_queries_enrollments(self):
        """semester_ids non-empty → True branch → options().filter().order_by().all() called."""
        user = _instructor()
        semester = MagicMock()
        db = MagicMock()
        # instructor_semesters: filter().order_by().all() → [semester]
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [semester]
        # all_enrollments: options().filter().order_by().all() → []
        db.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = []

        with patch(f"{_INSTRUCTOR_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(instructor_enrollments_page(request=_req(), db=db, user=user))

        # Confirm the options chain was exercised (semester_ids True branch)
        db.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# instructor_edit_student_skills_page (GET)
# ──────────────────────────────────────────────────────────────────────────────

class TestInstructorEditSkillsPage:

    def test_not_instructor_raises_403(self):
        user = _student_user()
        with pytest.raises(HTTPException) as exc_info:
            _run(instructor_edit_student_skills_page(
                request=_req(), student_id=99, license_id=1, db=MagicMock(), user=user
            ))
        assert exc_info.value.status_code == 403

    def test_student_not_found_raises_404(self):
        user = _instructor()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None  # student=None

        with pytest.raises(HTTPException) as exc_info:
            _run(instructor_edit_student_skills_page(
                request=_req(), student_id=99, license_id=1, db=db, user=user
            ))
        assert exc_info.value.status_code == 404
        assert "Student not found" in exc_info.value.detail

    def test_success_renders_skills_template(self):
        user = _instructor()
        student = MagicMock()
        license_obj = MagicMock()
        license_obj.user_id = 99
        license_obj.specialization_type = "LFA_PLAYER_PRE"
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [student, license_obj]

        with patch(f"{_INSTRUCTOR_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(instructor_edit_student_skills_page(
                request=_req(), student_id=99, license_id=1, db=db, user=user
            ))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "instructor/student_skills.html"

    def test_license_user_id_mismatch_raises_404(self):
        """License found but user_id doesn't match student_id → 404."""
        user = _instructor()
        student = MagicMock()
        license_obj = MagicMock()
        license_obj.user_id = 99  # Mismatch with student_id=42
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [student, license_obj]

        with pytest.raises(HTTPException) as exc_info:
            _run(instructor_edit_student_skills_page(
                request=_req(), student_id=42, license_id=1, db=db, user=user
            ))
        assert exc_info.value.status_code == 404
        assert "License not found" in exc_info.value.detail

    def test_non_lfa_player_spec_raises_400(self):
        """License found, user_id matches, but specialization not LFA_PLAYER_ → 400."""
        user = _instructor()
        student = MagicMock()
        license_obj = MagicMock()
        license_obj.user_id = 99
        license_obj.specialization_type = "GANCUJU_PLAYER"
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [student, license_obj]

        with pytest.raises(HTTPException) as exc_info:
            _run(instructor_edit_student_skills_page(
                request=_req(), student_id=99, license_id=1, db=db, user=user
            ))
        assert exc_info.value.status_code == 400


# ──────────────────────────────────────────────────────────────────────────────
# instructor_update_student_skills (POST)
# ──────────────────────────────────────────────────────────────────────────────

class TestInstructorUpdateSkills:

    def test_not_instructor_raises_403(self):
        user = _student_user()
        with pytest.raises(HTTPException) as exc_info:
            _run(instructor_update_student_skills(
                request=_req(), student_id=99, license_id=1, db=MagicMock(), user=user,
                heading=70.0, shooting=70.0, crossing=70.0,
                passing=70.0, dribbling=70.0, ball_control=70.0,
                instructor_notes="",
            ))
        assert exc_info.value.status_code == 403

    def test_student_not_found_raises_404(self):
        user = _instructor()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            _run(instructor_update_student_skills(
                request=_req(), student_id=99, license_id=1, db=db, user=user,
                heading=70.0, shooting=70.0, crossing=70.0,
                passing=70.0, dribbling=70.0, ball_control=70.0,
                instructor_notes="",
            ))
        assert exc_info.value.status_code == 404

    def test_license_mismatch_raises_404(self):
        user = _instructor()
        student = MagicMock()
        license_obj = MagicMock()
        license_obj.user_id = 99  # Mismatch with student_id=42
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [student, license_obj]
        with pytest.raises(HTTPException) as exc_info:
            _run(instructor_update_student_skills(
                request=_req(), student_id=42, license_id=1, db=db, user=user,
                heading=70.0, shooting=70.0, crossing=70.0,
                passing=70.0, dribbling=70.0, ball_control=70.0,
                instructor_notes="",
            ))
        assert exc_info.value.status_code == 404

    def test_non_lfa_player_spec_raises_400(self):
        user = _instructor()
        student = MagicMock()
        license_obj = MagicMock()
        license_obj.user_id = 99
        license_obj.specialization_type = "GANCUJU_PLAYER"
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [student, license_obj]
        with pytest.raises(HTTPException) as exc_info:
            _run(instructor_update_student_skills(
                request=_req(), student_id=99, license_id=1, db=db, user=user,
                heading=70.0, shooting=70.0, crossing=70.0,
                passing=70.0, dribbling=70.0, ball_control=70.0,
                instructor_notes="",
            ))
        assert exc_info.value.status_code == 400

    def test_skill_out_of_range_returns_template_with_error(self):
        """Skill value > 100 → TemplateResponse with error (no raise)."""
        user = _instructor()
        student = MagicMock()
        license_obj = MagicMock()
        license_obj.user_id = 99
        license_obj.specialization_type = "LFA_PLAYER_PRE"
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [student, license_obj]

        with patch(f"{_INSTRUCTOR_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(instructor_update_student_skills(
                request=_req(), student_id=99, license_id=1, db=db, user=user,
                heading=150.0,  # out of range
                shooting=70.0, crossing=70.0,
                passing=70.0, dribbling=70.0, ball_control=70.0,
                instructor_notes="",
            ))

        ctx = mock_tmpl.TemplateResponse.call_args.args[1]
        assert ctx.get("error") is not None

    def test_success_updates_and_renders(self):
        user = _instructor()
        student = MagicMock()
        student.email = "student@test.com"
        license_obj = MagicMock()
        license_obj.user_id = 99
        license_obj.specialization_type = "LFA_PLAYER_PRE"
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [student, license_obj]

        with patch(f"{_INSTRUCTOR_BASE}.templates") as mock_tmpl, \
             patch(f"{_INSTRUCTOR_BASE}.AuditService") as mock_audit:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            mock_audit.return_value.log.return_value = None
            _run(instructor_update_student_skills(
                request=_req(), student_id=99, license_id=1, db=db, user=user,
                heading=75.0, shooting=80.0, crossing=70.0,
                passing=85.0, dribbling=90.0, ball_control=65.0,
                instructor_notes="Good progress",
            ))

        db.commit.assert_called_once()
        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "instructor/student_skills.html"
        ctx = mock_tmpl.TemplateResponse.call_args.args[1]
        assert ctx.get("success") is True


# ──────────────────────────────────────────────────────────────────────────────
# motivation_assessment_page (GET)
# ──────────────────────────────────────────────────────────────────────────────

class TestMotivationAssessmentPage:

    def test_non_admin_raises_403(self):
        user = _student_user()
        with pytest.raises(HTTPException) as exc_info:
            _run(motivation_assessment_page(
                request=_req(), student_id=99, specialization="LFA_PLAYER_PRE",
                db=MagicMock(), user=user,
            ))
        assert exc_info.value.status_code == 403

    def test_renders_assessment_template(self):
        user = _admin()
        student = MagicMock()
        license_obj = MagicMock()
        license_obj.motivation_scores = None  # No existing scores
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [student, license_obj]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(motivation_assessment_page(
                request=_req(), student_id=99, specialization="LFA_PLAYER_PRE",
                db=db, user=user,
            ))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "admin/motivation_assessment.html"
        ctx = mock_tmpl.TemplateResponse.call_args.args[1]
        assert ctx["existing_scores"] is False

    def test_student_not_found_raises_404(self):
        """student=None → 404."""
        user = _admin()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            _run(motivation_assessment_page(
                request=_req(), student_id=99, specialization="LFA_PLAYER_PRE",
                db=db, user=user,
            ))
        assert exc_info.value.status_code == 404

    def test_license_not_found_raises_404(self):
        """Student found but license=None → 404."""
        user = _admin()
        student = MagicMock()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [student, None]

        with pytest.raises(HTTPException) as exc_info:
            _run(motivation_assessment_page(
                request=_req(), student_id=99, specialization="LFA_PLAYER_PRE",
                db=db, user=user,
            ))
        assert exc_info.value.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# motivation_assessment_submit (POST)
# ──────────────────────────────────────────────────────────────────────────────

class TestMotivationAssessmentSubmit:

    def test_non_admin_raises_403(self):
        user = _student_user()
        with pytest.raises(HTTPException) as exc_info:
            _run(motivation_assessment_submit(
                request=_req(), student_id=99, specialization="LFA_PLAYER_PRE",
                goal_clarity=3, commitment_level=3, engagement=3,
                progress_mindset=3, initiative=3, notes="",
                db=MagicMock(), user=user,
            ))
        assert exc_info.value.status_code == 403

    def test_submit_valid_scores_redirects(self):
        user = _admin()
        license_obj = MagicMock()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = license_obj

        result = _run(motivation_assessment_submit(
            request=_req(), student_id=99, specialization="LFA_PLAYER_PRE",
            goal_clarity=4, commitment_level=4, engagement=3,
            progress_mindset=5, initiative=4, notes="Good",
            db=db, user=user,
        ))

        assert isinstance(result, RedirectResponse)
        assert "/admin/payments" in result.headers["location"]
        db.commit.assert_called_once()
        assert license_obj.motivation_scores is not None

    def test_invalid_score_raises_400(self):
        """Score < 1 → HTTPException 400 before any DB query."""
        user = _admin()
        db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            _run(motivation_assessment_submit(
                request=_req(), student_id=99, specialization="LFA_PLAYER_PRE",
                goal_clarity=0,  # invalid: < 1
                commitment_level=3, engagement=3,
                progress_mindset=3, initiative=3, notes="",
                db=db, user=user,
            ))
        assert exc_info.value.status_code == 400

    def test_empty_instructor_notes_skips_note_update(self):
        """instructor_notes='' → if instructor_notes.strip(): False branch (line 575->578)."""
        user = _instructor()
        student = MagicMock()
        student.email = "student@test.com"
        license_obj = MagicMock()
        license_obj.user_id = 99
        license_obj.specialization_type = "LFA_PLAYER_PRE"
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [student, license_obj]

        with patch(f"{_INSTRUCTOR_BASE}.templates") as mock_tmpl, \
             patch(f"{_INSTRUCTOR_BASE}.AuditService") as mock_audit:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            mock_audit.return_value.log.return_value = None
            _run(instructor_update_student_skills(
                request=_req(), student_id=99, license_id=1, db=db, user=user,
                heading=75.0, shooting=80.0, crossing=70.0,
                passing=85.0, dribbling=90.0, ball_control=65.0,
                instructor_notes="",  # Empty → False branch
            ))

        db.commit.assert_called_once()
        # license.instructor_notes should NOT have been set (empty notes skipped)

    def test_submit_license_not_found_raises_404(self):
        """All scores valid, but license not found → 404."""
        user = _admin()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            _run(motivation_assessment_submit(
                request=_req(), student_id=99, specialization="LFA_PLAYER_PRE",
                goal_clarity=3, commitment_level=3, engagement=3,
                progress_mindset=3, initiative=3, notes="",
                db=db, user=user,
            ))
        assert exc_info.value.status_code == 404
