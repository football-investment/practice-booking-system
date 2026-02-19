"""
Authentication and authorization validation utilities

Provides reusable helpers for role-based access control,
eliminating 15+ duplicated authorization checks across endpoints.

Usage:
    from app.services.shared.auth_validator import require_role, require_admin

    # In endpoint:
    require_admin(current_user)  # Raises 403 if not admin
    require_role(current_user, UserRole.INSTRUCTOR)  # Raises 403 if not instructor
"""

from fastapi import HTTPException, status, Depends
from typing import List, Optional
from functools import wraps

from ...models.user import User, UserRole
from ...dependencies import get_current_user


def require_role(
    current_user: User,
    *allowed_roles: UserRole,
    detail: Optional[str] = None
) -> None:
    """
    Validate that current user has one of the allowed roles.

    Args:
        current_user: The authenticated user
        *allowed_roles: One or more UserRole enum values
        detail: Optional custom error message

    Raises:
        HTTPException(403): If user doesn't have required role

    Examples:
        >>> require_role(current_user, UserRole.ADMIN)
        >>> require_role(current_user, UserRole.ADMIN, UserRole.INSTRUCTOR)
    """
    if current_user.role not in allowed_roles:
        role_names = ", ".join([role.value for role in allowed_roles])
        error_detail = detail or f"User must have one of these roles: {role_names}"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_detail
        )


def require_admin(current_user: User, detail: Optional[str] = None) -> None:
    """
    Validate that current user is an admin.

    Args:
        current_user: The authenticated user
        detail: Optional custom error message

    Raises:
        HTTPException(403): If user is not admin

    Example:
        >>> require_admin(current_user)
    """
    require_role(
        current_user,
        UserRole.ADMIN,
        detail=detail or "Only admins can perform this action"
    )


def require_instructor(current_user: User, detail: Optional[str] = None) -> None:
    """
    Validate that current user is an instructor.

    Args:
        current_user: The authenticated user
        detail: Optional custom error message

    Raises:
        HTTPException(403): If user is not instructor

    Example:
        >>> require_instructor(current_user)
    """
    require_role(
        current_user,
        UserRole.INSTRUCTOR,
        detail=detail or "Only instructors can perform this action"
    )


def require_admin_or_instructor(current_user: User, detail: Optional[str] = None) -> None:
    """
    Validate that current user is either admin or instructor.

    Args:
        current_user: The authenticated user
        detail: Optional custom error message

    Raises:
        HTTPException(403): If user is neither admin nor instructor

    Example:
        >>> require_admin_or_instructor(current_user)
    """
    require_role(
        current_user,
        UserRole.ADMIN,
        UserRole.INSTRUCTOR,
        detail=detail or "Only admins or instructors can perform this action"
    )


def get_current_user_or_403(
    detail: str = "Authentication required"
) -> User:
    """
    Dependency that ensures user is authenticated.

    This is a convenience wrapper around get_current_user that provides
    a clearer error message for 403 scenarios.

    Args:
        detail: Custom error message for unauthenticated requests

    Returns:
        Authenticated User instance

    Raises:
        HTTPException(401): If authentication fails

    Usage:
        @router.post("/tournaments")
        def create_tournament(
            current_user: User = Depends(get_current_user_or_403())
        ):
            require_admin(current_user)
            ...
    """
    return Depends(get_current_user)


# ============================================================================
# DECORATOR-BASED APPROACH (Optional - for cleaner syntax)
# ============================================================================

def requires_role(*allowed_roles: UserRole):
    """
    Decorator that enforces role-based access control on FastAPI endpoints.

    Note: This is an alternative approach to the helper functions above.
    Use whichever style fits your codebase better.

    Args:
        *allowed_roles: One or more UserRole enum values

    Example:
        @router.post("/tournaments")
        @requires_role(UserRole.ADMIN)
        async def create_tournament(
            current_user: User = Depends(get_current_user),
            ...
        ):
            # No need for manual role check - decorator handles it
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User, **kwargs):
            require_role(current_user, *allowed_roles)
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


# Export main helper functions
__all__ = [
    "require_role",
    "require_admin",
    "require_instructor",
    "require_admin_or_instructor",
    "get_current_user_or_403",
    "requires_role",
]
