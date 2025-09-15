import pytest

from ..core.permissions import (
    PermissionChecker, check_user_permission, admin_required,
    admin_or_instructor_required, is_admin_or_self
)
from ..models.user import UserRole


def test_permission_checker():
    """Test PermissionChecker class"""
    # Test admin-only checker
    admin_checker = PermissionChecker([UserRole.ADMIN])
    assert admin_checker(UserRole.ADMIN) == True
    assert admin_checker(UserRole.INSTRUCTOR) == False
    assert admin_checker(UserRole.STUDENT) == False
    
    # Test admin/instructor checker
    admin_instructor_checker = PermissionChecker([UserRole.ADMIN, UserRole.INSTRUCTOR])
    assert admin_instructor_checker(UserRole.ADMIN) == True
    assert admin_instructor_checker(UserRole.INSTRUCTOR) == True
    assert admin_instructor_checker(UserRole.STUDENT) == False


def test_check_user_permission():
    """Test check_user_permission function"""
    # Test admin access
    assert check_user_permission(UserRole.ADMIN, [UserRole.ADMIN]) == True
    assert check_user_permission(UserRole.ADMIN, [UserRole.INSTRUCTOR]) == False
    
    # Test instructor access
    assert check_user_permission(UserRole.INSTRUCTOR, [UserRole.ADMIN, UserRole.INSTRUCTOR]) == True
    assert check_user_permission(UserRole.INSTRUCTOR, [UserRole.ADMIN]) == False
    
    # Test student access
    assert check_user_permission(UserRole.STUDENT, [UserRole.STUDENT]) == True
    assert check_user_permission(UserRole.STUDENT, [UserRole.ADMIN]) == False


def test_admin_required():
    """Test admin_required function"""
    assert admin_required(UserRole.ADMIN) == True
    assert admin_required(UserRole.INSTRUCTOR) == False
    assert admin_required(UserRole.STUDENT) == False


def test_admin_or_instructor_required():
    """Test admin_or_instructor_required function"""
    assert admin_or_instructor_required(UserRole.ADMIN) == True
    assert admin_or_instructor_required(UserRole.INSTRUCTOR) == True
    assert admin_or_instructor_required(UserRole.STUDENT) == False


def test_is_admin_or_self():
    """Test is_admin_or_self function"""
    # Test admin accessing any user
    assert is_admin_or_self(1, 2, UserRole.ADMIN) == True
    assert is_admin_or_self(1, 1, UserRole.ADMIN) == True
    
    # Test instructor accessing own data
    assert is_admin_or_self(1, 1, UserRole.INSTRUCTOR) == True
    assert is_admin_or_self(1, 2, UserRole.INSTRUCTOR) == False
    
    # Test student accessing own data
    assert is_admin_or_self(1, 1, UserRole.STUDENT) == True
    assert is_admin_or_self(1, 2, UserRole.STUDENT) == False