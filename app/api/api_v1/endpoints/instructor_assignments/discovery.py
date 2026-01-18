"""
Instructor Assignment Discovery Endpoints

Available instructor discovery for admin semester planning.

Flow:
1. Instructor sets general availability: "Q3 2026, Budapest+Budaörs"
2. Admin generates semesters for specific age groups
3. System shows admins which instructors are available
4. Admin sends assignment request to instructor
5. Instructor accepts/declines specific semester assignments
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import Any, List, Dict, Optional
from datetime import datetime

from .....database import get_db
from .....dependencies import get_current_admin_user, get_current_user
from .....models.user import User, UserRole
from .....models.semester import Semester
from .....models.license import UserLicense
from .....models.instructor_assignment import (
    InstructorAvailabilityWindow,
    InstructorAssignmentRequest,
    AssignmentRequestStatus
)
from .....schemas.instructor_assignment import (
    InstructorAvailabilityWindowCreate,
    InstructorAvailabilityWindowUpdate,
    InstructorAvailabilityWindowResponse,
    InstructorAssignmentRequestCreate,
    InstructorAssignmentRequestUpdate,
    InstructorAssignmentRequestAccept,
    InstructorAssignmentRequestDecline,
    InstructorAssignmentRequestResponse,
    AvailableInstructorInfo,
    InstructorLicenseInfo,
    AvailableInstructorsQuery
)

router = APIRouter()


# ============================================================================
# Instructor Availability Window Endpoints
# ============================================================================


@router.get("/available-instructors", response_model=List[AvailableInstructorInfo])
def get_available_instructors(
    year: int = Query(..., ge=2024, le=2100),
    time_period: str = Query(..., max_length=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Find instructors available for a specific time period (Admin only).

    Location is NOT part of availability - it comes from the assignment request!
    Used by admins when creating semesters to see which instructors can be assigned.
    """
    # Authorization - only admins
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view available instructors"
        )

    # Find availability windows matching criteria (NO location filter!)
    windows = db.query(InstructorAvailabilityWindow).filter(
        InstructorAvailabilityWindow.year == year,
        InstructorAvailabilityWindow.time_period == time_period,
        InstructorAvailabilityWindow.is_available == True
    ).options(
        joinedload(InstructorAvailabilityWindow.instructor)
    ).all()

    # Group by instructor
    instructor_map = {}
    for window in windows:
        instructor_id = window.instructor_id
        if instructor_id not in instructor_map:
            # Get instructor's ACTIVE licenses only (is_active=True)
            user_licenses = db.query(UserLicense).filter(
                UserLicense.user_id == instructor_id,
                UserLicense.is_active == True
            ).all()

            # Convert to InstructorLicenseInfo objects
            license_infos = [
                InstructorLicenseInfo(
                    license_id=lic.id,
                    specialization_type=lic.specialization_type,
                    current_level=lic.current_level,
                    max_achieved_level=lic.max_achieved_level,
                    started_at=lic.started_at,
                    last_advanced_at=lic.last_advanced_at
                )
                for lic in user_licenses
            ]

            instructor_map[instructor_id] = AvailableInstructorInfo(
                instructor_id=instructor_id,
                instructor_name=window.instructor.name,
                instructor_email=window.instructor.email,
                availability_windows=[],
                licenses=license_infos
            )

        instructor_map[instructor_id].availability_windows.append(window)

    return list(instructor_map.values())
