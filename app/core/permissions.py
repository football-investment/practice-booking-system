from typing import List, Optional
from functools import wraps
from fastapi import HTTPException, status

from ..models.user import UserRole


class PermissionChecker:
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user_role: UserRole) -> bool:
        return user_role in self.allowed_roles


def require_roles(allowed_roles: List[UserRole]):
    """Decorator to check user roles"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This will be used in FastAPI dependencies
            return func(*args, **kwargs)
        wrapper._required_roles = allowed_roles
        return wrapper
    return decorator


def check_user_permission(current_user_role: UserRole, required_roles: List[UserRole]) -> bool:
    """Check if user has required permission"""
    return current_user_role in required_roles


def admin_required(current_user_role: UserRole) -> bool:
    """Check if user is admin"""
    return current_user_role == UserRole.ADMIN


def admin_or_instructor_required(current_user_role: UserRole) -> bool:
    """Check if user is admin or instructor"""
    return current_user_role in [UserRole.ADMIN, UserRole.INSTRUCTOR]


def is_admin_or_self(current_user_id: int, target_user_id: int, current_user_role: UserRole) -> bool:
    """Check if user is admin or accessing their own data"""
    return current_user_role == UserRole.ADMIN or current_user_id == target_user_id