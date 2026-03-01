"""
⚠️ Enrollment Conflict Check API Endpoints
==========================================
REST API for checking enrollment conflicts before user signs up

Endpoints:
- GET /enrollments/{semester_id}/check-conflicts - Check conflicts for a specific semester
- GET /enrollments/my-schedule - Get user's complete schedule across all enrollments
- POST /enrollments/validate - Validate enrollment request with full conflict analysis
"""
from typing import Any, Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User
from .....models.semester import Semester
from .....services.enrollment_conflict_service import EnrollmentConflictService

router = APIRouter()


@router.get("/{semester_id}/check-conflicts")
def check_enrollment_conflicts(
    semester_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Check if enrolling in this semester would create conflicts with user's existing enrollments.

    Returns conflict warnings but does NOT block enrollment.

    Response:
    {
        "semester": {...},
        "has_conflict": bool,
        "conflicts": [...],
        "warnings": [...],
        "can_enroll": true  # Always true - conflicts are warnings only
    }
    """
    # Verify semester exists
    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if not semester:
        raise HTTPException(
            status_code=404,
            detail="Semester not found"
        )

    # Check for conflicts
    conflict_result = EnrollmentConflictService.check_session_time_conflict(
        user_id=current_user.id,
        semester_id=semester_id,
        db=db
    )

    return {
        "semester": {
            "id": semester.id,
            "name": semester.name,
            "code": semester.code,
            "specialization_type": semester.specialization_type,
            "start_date": semester.start_date.isoformat(),
            "end_date": semester.end_date.isoformat()
        },
        "has_conflict": conflict_result["has_conflict"],
        "conflicts": conflict_result["conflicts"],
        "warnings": conflict_result["warnings"],
        "can_enroll": True,  # Always allowed, conflicts are just warnings
        "conflict_summary": {
            "total_conflicts": len(conflict_result["conflicts"]),
            "blocking_conflicts": len([c for c in conflict_result["conflicts"] if c["severity"] == "blocking"]),
            "warning_conflicts": len([c for c in conflict_result["conflicts"] if c["severity"] == "warning"])
        }
    }


@router.get("/my-schedule")
def get_my_schedule(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD). Defaults to today."),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD). Defaults to start_date + 90 days."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get complete schedule for current user across all enrollment types.

    Shows all sessions from:
    - Tournaments
    - Mini Seasons
    - Academy Seasons

    Query params:
    - start_date: Start date (YYYY-MM-DD). Defaults to today.
    - end_date: End date (YYYY-MM-DD). Defaults to start_date + 90 days.

    Response:
    {
        "enrollments": [
            {
                "enrollment_id": int,
                "semester_name": str,
                "enrollment_type": "TOURNAMENT" | "MINI_SEASON" | "ACADEMY_SEASON",
                "sessions": [...]
            }
        ],
        "total_sessions": int,
        "date_range": {...}
    }
    """
    # Parse dates
    if start_date:
        try:
            start = date.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid start_date format. Use YYYY-MM-DD."
            )
    else:
        start = date.today()

    if end_date:
        try:
            end = date.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid end_date format. Use YYYY-MM-DD."
            )
    else:
        end = start + timedelta(days=90)

    # Validate date range
    if end < start:
        raise HTTPException(
            status_code=400,
            detail="end_date must be >= start_date"
        )

    # Get schedule
    schedule = EnrollmentConflictService.get_user_schedule(
        user_id=current_user.id,
        start_date=start,
        end_date=end,
        db=db
    )

    return schedule


@router.post("/validate")
def validate_enrollment(
    semester_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Full validation for enrollment request.

    Combines:
    - Conflict detection
    - Business rule validation
    - Recommendations

    Returns:
    {
        "allowed": true,  # Always true - enrollment is never blocked
        "conflicts": [...],
        "warnings": [...],
        "recommendations": [...]
    }
    """
    # Verify semester exists
    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if not semester:
        raise HTTPException(
            status_code=404,
            detail="Semester not found"
        )

    # Validate enrollment
    validation_result = EnrollmentConflictService.validate_enrollment_request(
        user_id=current_user.id,
        semester_id=semester_id,
        db=db
    )

    return {
        "semester": {
            "id": semester.id,
            "name": semester.name,
            "code": semester.code,
            "specialization_type": semester.specialization_type.value
        },
        "allowed": validation_result["allowed"],
        "conflicts": validation_result["conflicts"],
        "warnings": validation_result["warnings"],
        "recommendations": validation_result["recommendations"],
        "summary": {
            "total_conflicts": len(validation_result["conflicts"]),
            "total_warnings": len(validation_result["warnings"]),
            "has_blocking_conflicts": any(
                c["severity"] == "blocking"
                for c in validation_result["conflicts"]
            )
        }
    }
