"""
Instructor Assignment Availability Endpoints

Instructor availability management for demand-driven assignment workflow.

Flow:
1. Instructor sets general availability: "Q3 2026, Budapest+Budaörs"
2. Admin generates semesters for specific age groups
3. System shows admins which instructors are available
4. Admin sends assignment request to instructor
5. Instructor accepts/declines specific semester assignments
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User, UserRole
from .....models.instructor_assignment import (
    InstructorAvailabilityWindow
)
from .....schemas.instructor_assignment import (
    InstructorAvailabilityWindowCreate,
    InstructorAvailabilityWindowUpdate,
    InstructorAvailabilityWindowResponse
)

router = APIRouter()


# ============================================================================
# Instructor Availability Window Endpoints
# ============================================================================


@router.post("/availability", response_model=InstructorAvailabilityWindowResponse, status_code=status.HTTP_201_CREATED)
def create_availability_window(
    availability: InstructorAvailabilityWindowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new availability window.

    Instructors can only create for themselves, admins can create for anyone.
    """
    # Authorization
    if current_user.role != UserRole.ADMIN:
        if current_user.id != availability.instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only set your own availability"
            )

    # Verify instructor exists and has instructor role
    instructor = db.query(User).filter(
        User.id == availability.instructor_id,
        User.role == UserRole.INSTRUCTOR
    ).first()
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instructor not found"
        )

    # Check for duplicate
    existing = db.query(InstructorAvailabilityWindow).filter(
        InstructorAvailabilityWindow.instructor_id == availability.instructor_id,
        InstructorAvailabilityWindow.year == availability.year,
        InstructorAvailabilityWindow.time_period == availability.time_period
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability window already exists for this instructor/year/period"
        )

    # Create
    db_availability = InstructorAvailabilityWindow(**availability.model_dump())
    db.add(db_availability)
    db.commit()
    db.refresh(db_availability)

    return db_availability


@router.get("/availability/instructor/{instructor_id}", response_model=List[InstructorAvailabilityWindowResponse])
def get_instructor_availability_windows(
    instructor_id: int,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all availability windows for a specific instructor"""
    # Authorization
    if current_user.role != UserRole.ADMIN:
        if current_user.id != instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own availability"
            )

    query = db.query(InstructorAvailabilityWindow).filter(
        InstructorAvailabilityWindow.instructor_id == instructor_id
    )

    if year:
        query = query.filter(InstructorAvailabilityWindow.year == year)

    windows = query.order_by(
        InstructorAvailabilityWindow.year.desc(),
        InstructorAvailabilityWindow.time_period
    ).all()

    return windows


@router.patch("/availability/{window_id}", response_model=InstructorAvailabilityWindowResponse)
def update_availability_window(
    window_id: int,
    update_data: InstructorAvailabilityWindowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an availability window"""
    # Get the window
    window = db.query(InstructorAvailabilityWindow).filter(
        InstructorAvailabilityWindow.id == window_id
    ).first()

    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability window not found"
        )

    # Authorization
    if current_user.role != UserRole.ADMIN:
        if current_user.id != window.instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own availability"
            )

    # Update
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(window, field, value)

    window.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(window)

    return window


@router.delete("/availability/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability_window(
    window_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an availability window"""
    # Get the window
    window = db.query(InstructorAvailabilityWindow).filter(
        InstructorAvailabilityWindow.id == window_id
    ).first()

    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability window not found"
        )

    # Authorization
    if current_user.role != UserRole.ADMIN:
        if current_user.id != window.instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own availability"
            )

    db.delete(window)
    db.commit()

    return None


# ============================================================================
# Assignment Request Endpoints
# ============================================================================

