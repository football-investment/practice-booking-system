"""
Role-Based Access Control (RBAC) Utilities

Provides helper functions for validating resource ownership and permissions.
Used across all API endpoints to ensure users can only access/modify their own data
(unless they have admin privileges).
"""

from fastapi import HTTPException, status
from app.models.user import User, UserRole
from sqlalchemy.orm import Session
from sqlalchemy import text


def validate_license_ownership(
    db: Session,
    current_user: User,
    license_id: int,
    license_table: str
) -> bool:
    """
    Validate that the current user owns the specified license

    Args:
        db: Database session
        current_user: Current authenticated user
        license_id: License ID to check
        license_table: Table name (e.g., 'lfa_player_licenses', 'gancuju_licenses')

    Returns:
        bool: True if user owns the license or is admin

    Raises:
        HTTPException: 403 if user doesn't own license and is not admin
        HTTPException: 404 if license doesn't exist
    """
    # Admin can access any license
    if current_user.role == UserRole.ADMIN:
        return True

    # Instructor can access any student's license
    if current_user.role == UserRole.INSTRUCTOR:
        return True

    # Check if license exists and belongs to current user (students can only access own)
    result = db.execute(
        text(f"SELECT user_id FROM {license_table} WHERE id = :license_id AND is_active = true"),
        {"license_id": license_id}
    ).fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License not found or inactive"
        )

    license_user_id = result[0]

    if license_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this license"
        )

    return True


def validate_can_modify_user_data(
    current_user: User,
    target_user_id: int,
    operation: str = "modify"
) -> bool:
    """
    Validate that current user can modify target user's data

    Args:
        current_user: Current authenticated user
        target_user_id: User ID whose data is being modified
        operation: Operation description (for error message)

    Returns:
        bool: True if allowed

    Raises:
        HTTPException: 403 if user cannot modify target user's data
    """
    # Admin can modify anyone
    if current_user.role == UserRole.ADMIN:
        return True

    # Users can only modify their own data
    if current_user.id != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to {operation} another user's data"
        )

    return True


def validate_instructor_can_modify_student(
    db: Session,
    current_user: User,
    student_user_id: int,
    operation: str = "modify student data"
) -> bool:
    """
    Validate that an instructor can modify a specific student's data

    Instructors can only modify students who are enrolled in their sessions.
    Admins can modify anyone.

    Args:
        db: Database session
        current_user: Current authenticated user (must be INSTRUCTOR or ADMIN)
        student_user_id: Student user ID
        operation: Operation description

    Returns:
        bool: True if allowed

    Raises:
        HTTPException: 403 if instructor cannot modify this student
    """
    # Admin can modify anyone
    if current_user.role == UserRole.ADMIN:
        return True

    # Only instructors can use this validation
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can perform this operation"
        )

    # Check if instructor has any sessions with this student
    # (This is a simplified check - in production you'd check active enrollments)
    result = db.execute(
        text("""
            SELECT COUNT(*)
            FROM sessions s
            JOIN bookings b ON s.id = b.session_id
            WHERE s.instructor_id = :instructor_id
            AND b.user_id = :student_id
            AND b.status IN ('confirmed', 'attended')
        """),
        {"instructor_id": current_user.id, "student_id": student_user_id}
    ).scalar()

    if result == 0:
        # Instructor has no sessions with this student
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to {operation} for this student"
        )

    return True


def require_role(current_user: User, required_roles: list[UserRole], operation: str = "access this resource"):
    """
    Require user to have one of the specified roles

    Args:
        current_user: Current authenticated user
        required_roles: List of allowed roles
        operation: Operation description (for error message)

    Raises:
        HTTPException: 403 if user doesn't have required role
    """
    if current_user.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions to {operation}. Required role: {', '.join([r.value for r in required_roles])}"
        )


def validate_admin_only(current_user: User, operation: str = "perform this operation"):
    """
    Require user to be admin

    Args:
        current_user: Current authenticated user
        operation: Operation description

    Raises:
        HTTPException: 403 if user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin privileges required to {operation}"
        )


def validate_admin_or_instructor(current_user: User, operation: str = "perform this operation"):
    """
    Require user to be admin or instructor

    Args:
        current_user: Current authenticated user
        operation: Operation description

    Raises:
        HTTPException: 403 if user is neither admin nor instructor
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Instructor or Admin privileges required to {operation}"
        )
