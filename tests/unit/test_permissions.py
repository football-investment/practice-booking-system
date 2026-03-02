"""
Unit tests for app/core/permissions.py

5 pure authorization functions — zero DB, zero I/O.
Tests document every decision boundary and invariant.
"""
import pytest
from app.core.permissions import (
    PermissionChecker,
    check_user_permission,
    admin_required,
    admin_or_instructor_required,
    is_admin_or_self,
)
from app.models.user import UserRole


# ============================================================================
# PermissionChecker
# ============================================================================

@pytest.mark.unit
class TestPermissionChecker:
    """PermissionChecker callable class — membership check against allowed list."""

    def test_role_in_allowed_list_returns_true(self):
        checker = PermissionChecker([UserRole.ADMIN, UserRole.INSTRUCTOR])
        assert checker(UserRole.ADMIN) is True

    def test_non_admin_role_in_allowed_list_returns_true(self):
        checker = PermissionChecker([UserRole.INSTRUCTOR, UserRole.STUDENT])
        assert checker(UserRole.STUDENT) is True

    def test_role_not_in_allowed_list_returns_false(self):
        checker = PermissionChecker([UserRole.ADMIN])
        assert checker(UserRole.STUDENT) is False

    def test_empty_allowed_list_always_returns_false(self):
        checker = PermissionChecker([])
        for role in UserRole:
            assert checker(role) is False

    def test_all_roles_in_list_all_return_true(self):
        all_roles = list(UserRole)
        checker = PermissionChecker(all_roles)
        for role in UserRole:
            assert checker(role) is True


# ============================================================================
# check_user_permission
# ============================================================================

@pytest.mark.unit
class TestCheckUserPermission:
    """check_user_permission — thin wrapper around role membership."""

    def test_admin_role_allowed_returns_true(self):
        assert check_user_permission(UserRole.ADMIN, [UserRole.ADMIN]) is True

    def test_student_not_in_admin_only_returns_false(self):
        assert check_user_permission(UserRole.STUDENT, [UserRole.ADMIN]) is False

    def test_instructor_in_multi_role_list_returns_true(self):
        assert check_user_permission(
            UserRole.INSTRUCTOR, [UserRole.ADMIN, UserRole.INSTRUCTOR]
        ) is True

    def test_student_in_multi_role_list_returns_true(self):
        assert check_user_permission(
            UserRole.STUDENT, [UserRole.ADMIN, UserRole.INSTRUCTOR, UserRole.STUDENT]
        ) is True

    def test_empty_required_list_always_false(self):
        assert check_user_permission(UserRole.ADMIN, []) is False


# ============================================================================
# admin_required
# ============================================================================

@pytest.mark.unit
class TestAdminRequired:
    """admin_required — ADMIN role only."""

    def test_admin_returns_true(self):
        assert admin_required(UserRole.ADMIN) is True

    def test_student_returns_false(self):
        assert admin_required(UserRole.STUDENT) is False

    def test_instructor_returns_false(self):
        assert admin_required(UserRole.INSTRUCTOR) is False

    def test_exhaustive_only_admin_passes(self):
        """Invariant: exactly one role satisfies admin_required."""
        passing = [r for r in UserRole if admin_required(r)]
        assert passing == [UserRole.ADMIN]


# ============================================================================
# admin_or_instructor_required
# ============================================================================

@pytest.mark.unit
class TestAdminOrInstructorRequired:
    """admin_or_instructor_required — ADMIN or INSTRUCTOR only."""

    def test_admin_returns_true(self):
        assert admin_or_instructor_required(UserRole.ADMIN) is True

    def test_instructor_returns_true(self):
        assert admin_or_instructor_required(UserRole.INSTRUCTOR) is True

    def test_student_returns_false(self):
        assert admin_or_instructor_required(UserRole.STUDENT) is False

    def test_exhaustive_exactly_two_roles_pass(self):
        """Invariant: exactly ADMIN and INSTRUCTOR satisfy this function."""
        passing = {r for r in UserRole if admin_or_instructor_required(r)}
        assert passing == {UserRole.ADMIN, UserRole.INSTRUCTOR}


# ============================================================================
# is_admin_or_self
# ============================================================================

@pytest.mark.unit
class TestIsAdminOrSelf:
    """
    is_admin_or_self — ADMIN may access any resource;
    non-admin may access only their own.
    """

    def test_admin_accessing_another_user_returns_true(self):
        assert is_admin_or_self(current_user_id=1, target_user_id=99, current_user_role=UserRole.ADMIN) is True

    def test_admin_accessing_own_resource_returns_true(self):
        assert is_admin_or_self(current_user_id=5, target_user_id=5, current_user_role=UserRole.ADMIN) is True

    def test_student_accessing_own_resource_returns_true(self):
        assert is_admin_or_self(current_user_id=7, target_user_id=7, current_user_role=UserRole.STUDENT) is True

    def test_instructor_accessing_own_resource_returns_true(self):
        assert is_admin_or_self(current_user_id=3, target_user_id=3, current_user_role=UserRole.INSTRUCTOR) is True

    def test_student_accessing_another_user_returns_false(self):
        assert is_admin_or_self(current_user_id=7, target_user_id=42, current_user_role=UserRole.STUDENT) is False

    def test_instructor_accessing_another_user_returns_false(self):
        assert is_admin_or_self(current_user_id=3, target_user_id=9, current_user_role=UserRole.INSTRUCTOR) is False

    def test_admin_privilege_independent_of_user_id_match(self):
        """INVARIANT: admin role alone grants access regardless of ID comparison."""
        for other_id in [0, 1, 999, 10000]:
            assert is_admin_or_self(
                current_user_id=1,
                target_user_id=other_id,
                current_user_role=UserRole.ADMIN,
            ) is True

    def test_non_admin_access_depends_solely_on_id_equality(self):
        """INVARIANT: non-admin access iff current_user_id == target_user_id."""
        for non_admin in [UserRole.STUDENT, UserRole.INSTRUCTOR]:
            assert is_admin_or_self(10, 10, non_admin) is True
            assert is_admin_or_self(10, 11, non_admin) is False
            assert is_admin_or_self(10, 9, non_admin) is False
