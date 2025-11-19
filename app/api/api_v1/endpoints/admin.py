"""
Admin Dashboard API Endpoints
=============================

Admin-only endpoints for dashboard statistics and management.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ....database import get_db
from ....models.user import User, UserRole
from ....models.booking import Booking
from ....models.session import Session as SessionModel
from ....models.user_progress import SpecializationProgress
from ....models.license import UserLicense
from ....dependencies import get_current_admin_user


router = APIRouter()


@router.get("/stats", response_model=Dict[str, Any])
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get admin dashboard statistics

    Returns:
        {
            'total_users': int,
            'active_users': int,
            'total_students': int,
            'total_instructors': int,
            'total_sessions': int,
            'total_bookings': int,
            'total_progress_records': int,
            'total_licenses': int
        }

    Permissions:
        - ADMIN role required
    """
    try:
        # User statistics
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
        total_students = db.query(func.count(User.id)).filter(User.role == UserRole.STUDENT).scalar() or 0
        total_instructors = db.query(func.count(User.id)).filter(User.role == UserRole.INSTRUCTOR).scalar() or 0

        # Session and booking statistics
        total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
        total_bookings = db.query(func.count(Booking.id)).scalar() or 0

        # Progress and license statistics
        total_progress_records = db.query(func.count(SpecializationProgress.id)).scalar() or 0
        total_licenses = db.query(func.count(UserLicense.id)).scalar() or 0

        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_students': total_students,
            'total_instructors': total_instructors,
            'total_sessions': total_sessions,
            'total_bookings': total_bookings,
            'total_progress_records': total_progress_records,
            'total_licenses': total_licenses
        }
    except Exception as e:
        # Return zeros on error
        return {
            'total_users': 0,
            'active_users': 0,
            'total_students': 0,
            'total_instructors': 0,
            'total_sessions': 0,
            'total_bookings': 0,
            'total_progress_records': 0,
            'total_licenses': 0,
            'error': str(e)
        }
