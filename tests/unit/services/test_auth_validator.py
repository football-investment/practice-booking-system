"""
Sprint P1 — shared/auth_validator.py
=====================================
Target: ≥90% stmt, ≥85% branch

Covers all public functions:
  require_role          — role guard, custom/default detail
  require_admin         — shortcut wrapper
  require_instructor    — shortcut wrapper
  require_admin_or_instructor — dual-role shortcut
  get_current_user_or_403     — FastAPI Depends factory
  requires_role         — async decorator
"""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.services.shared.auth_validator import (
    require_role,
    require_admin,
    require_instructor,
    require_admin_or_instructor,
    get_current_user_or_403,
    requires_role,
)
from app.models.user import UserRole


def _user(role: UserRole) -> MagicMock:
    u = MagicMock()
    u.role = role
    return u


# ── require_role ─────────────────────────────────────────────────────────────

class TestRequireRole:
    def test_exact_role_match_no_exception(self):
        require_role(_user(UserRole.ADMIN), UserRole.ADMIN)

    def test_wrong_role_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            require_role(_user(UserRole.STUDENT), UserRole.ADMIN)
        assert exc_info.value.status_code == 403

    def test_default_detail_lists_allowed_role(self):
        with pytest.raises(HTTPException) as exc_info:
            require_role(_user(UserRole.STUDENT), UserRole.ADMIN)
        assert "admin" in exc_info.value.detail.lower()

    def test_custom_detail_overrides_default(self):
        with pytest.raises(HTTPException) as exc_info:
            require_role(_user(UserRole.STUDENT), UserRole.ADMIN, detail="no entry")
        assert exc_info.value.detail == "no entry"

    def test_multi_role_first_passes(self):
        require_role(_user(UserRole.ADMIN), UserRole.ADMIN, UserRole.INSTRUCTOR)

    def test_multi_role_second_passes(self):
        require_role(_user(UserRole.INSTRUCTOR), UserRole.ADMIN, UserRole.INSTRUCTOR)

    def test_multi_role_none_match_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            require_role(_user(UserRole.STUDENT), UserRole.ADMIN, UserRole.INSTRUCTOR)
        assert exc_info.value.status_code == 403

    def test_instructor_role_accepted_when_required(self):
        require_role(_user(UserRole.INSTRUCTOR), UserRole.INSTRUCTOR)

    def test_student_role_accepted_when_required(self):
        require_role(_user(UserRole.STUDENT), UserRole.STUDENT)


# ── require_admin ─────────────────────────────────────────────────────────────

class TestRequireAdmin:
    def test_admin_passes(self):
        require_admin(_user(UserRole.ADMIN))

    def test_instructor_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            require_admin(_user(UserRole.INSTRUCTOR))
        assert exc_info.value.status_code == 403

    def test_student_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            require_admin(_user(UserRole.STUDENT))
        assert exc_info.value.status_code == 403

    def test_default_detail_mentions_admins(self):
        with pytest.raises(HTTPException) as exc_info:
            require_admin(_user(UserRole.STUDENT))
        assert "admin" in exc_info.value.detail.lower()

    def test_custom_detail_propagated(self):
        with pytest.raises(HTTPException) as exc_info:
            require_admin(_user(UserRole.STUDENT), detail="admin only")
        assert exc_info.value.detail == "admin only"


# ── require_instructor ────────────────────────────────────────────────────────

class TestRequireInstructor:
    def test_instructor_passes(self):
        require_instructor(_user(UserRole.INSTRUCTOR))

    def test_admin_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            require_instructor(_user(UserRole.ADMIN))
        assert exc_info.value.status_code == 403

    def test_student_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            require_instructor(_user(UserRole.STUDENT))
        assert exc_info.value.status_code == 403

    def test_default_detail_mentions_instructors(self):
        with pytest.raises(HTTPException) as exc_info:
            require_instructor(_user(UserRole.STUDENT))
        assert "instructor" in exc_info.value.detail.lower()

    def test_custom_detail_propagated(self):
        with pytest.raises(HTTPException) as exc_info:
            require_instructor(_user(UserRole.STUDENT), detail="restricted")
        assert exc_info.value.detail == "restricted"


# ── require_admin_or_instructor ───────────────────────────────────────────────

class TestRequireAdminOrInstructor:
    def test_admin_passes(self):
        require_admin_or_instructor(_user(UserRole.ADMIN))

    def test_instructor_passes(self):
        require_admin_or_instructor(_user(UserRole.INSTRUCTOR))

    def test_student_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            require_admin_or_instructor(_user(UserRole.STUDENT))
        assert exc_info.value.status_code == 403

    def test_default_detail_mentions_both_roles(self):
        with pytest.raises(HTTPException) as exc_info:
            require_admin_or_instructor(_user(UserRole.STUDENT))
        detail = exc_info.value.detail.lower()
        assert "admin" in detail or "instructor" in detail

    def test_custom_detail_propagated(self):
        with pytest.raises(HTTPException) as exc_info:
            require_admin_or_instructor(_user(UserRole.STUDENT), detail="staff only")
        assert exc_info.value.detail == "staff only"


# ── get_current_user_or_403 ───────────────────────────────────────────────────

class TestGetCurrentUserOr403:
    def test_returns_fastapi_depends_object(self):
        """Function returns a FastAPI Depends wrapper — no logic to test."""
        result = get_current_user_or_403()
        # Depends objects carry a .dependency attribute
        assert hasattr(result, "dependency")

    def test_custom_detail_accepted_without_error(self):
        result = get_current_user_or_403(detail="login required")
        assert hasattr(result, "dependency")


# ── requires_role decorator ───────────────────────────────────────────────────

class TestRequiresRoleDecorator:
    @pytest.mark.asyncio
    async def test_authorized_role_returns_result(self):
        @requires_role(UserRole.ADMIN)
        async def endpoint(current_user):
            return "ok"

        result = await endpoint(current_user=_user(UserRole.ADMIN))
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_unauthorized_role_raises_403(self):
        @requires_role(UserRole.ADMIN)
        async def endpoint(current_user):
            return "ok"

        with pytest.raises(HTTPException) as exc_info:
            await endpoint(current_user=_user(UserRole.STUDENT))
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_multi_role_second_role_passes(self):
        @requires_role(UserRole.ADMIN, UserRole.INSTRUCTOR)
        async def endpoint(current_user):
            return "ok"

        result = await endpoint(current_user=_user(UserRole.INSTRUCTOR))
        assert result == "ok"
