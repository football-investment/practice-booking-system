"""
Instructor Specialization Availability API Endpoints

Allows instructors (especially Grandmasters) to manage their teaching availability:
- Choose which time periods they want to work
- Choose which age groups they want to teach in specific periods

Example use case:
- Grandmaster wants to teach only PRE and YOUTH in Q3
- Can deactivate AMATEUR and PRO for Q3 period
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.instructor_availability import InstructorSpecializationAvailability
from app.models.user import User, UserRole
from app.schemas.instructor_availability import (
    InstructorAvailabilityCreate,
    InstructorAvailabilityUpdate,
    InstructorAvailabilityResponse,
    InstructorAvailabilityMatrix
)
from app.dependencies import get_current_user

router = APIRouter()


@router.get("/matrix/{instructor_id}/{year}", response_model=InstructorAvailabilityMatrix)
def get_instructor_availability_matrix(
    instructor_id: int,
    year: int,
    location_city: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get instructor availability as a matrix for easier visualization.

    Returns:
    {
        "instructor_id": 1,
        "year": 2025,
        "location_city": "Budapest",
        "matrix": {
            "Q1": {
                "LFA_PLAYER_PRE": true,
                "LFA_PLAYER_YOUTH": true,
                "LFA_PLAYER_AMATEUR": false,
                "LFA_PLAYER_PRO": false
            },
            ...
        }
    }
    """
    # Authorization: instructors can only see their own availability, admins can see all
    if current_user.role != UserRole.ADMIN:
        if current_user.id != instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own availability"
            )

    # Verify instructor exists
    instructor = db.query(User).filter(
        User.id == instructor_id,
        User.role == UserRole.INSTRUCTOR
    ).first()
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instructor not found"
        )

    # Get all availability records for this instructor/year/location
    query = db.query(InstructorSpecializationAvailability).filter(
        InstructorSpecializationAvailability.instructor_id == instructor_id,
        InstructorSpecializationAvailability.year == year
    )
    if location_city:
        query = query.filter(InstructorSpecializationAvailability.location_city == location_city)

    availabilities = query.all()

    # Build matrix
    matrix = {}
    notes_dict = {}

    # Determine time periods based on specialization types
    # PRE uses monthly (M01-M12), others use quarterly (Q1-Q4)
    time_periods = set()
    spec_types = set()

    for avail in availabilities:
        time_periods.add(avail.time_period_code)
        spec_types.add(avail.specialization_type)

    # If no data, create default structure based on common patterns
    if not time_periods:
        # Default to quarterly for most specializations
        time_periods = {'Q1', 'Q2', 'Q3', 'Q4'}
    if not spec_types:
        spec_types = {'LFA_PLAYER_PRE', 'LFA_PLAYER_YOUTH', 'LFA_PLAYER_AMATEUR', 'LFA_PLAYER_PRO'}

    # Initialize matrix with all periods and specs
    for period in sorted(time_periods):
        matrix[period] = {}
        notes_dict[period] = {}
        for spec in sorted(spec_types):
            # Default to True (available) if no record exists
            matrix[period][spec] = True
            notes_dict[period][spec] = None

    # Fill in actual values
    for avail in availabilities:
        matrix[avail.time_period_code][avail.specialization_type] = avail.is_available
        if avail.notes:
            notes_dict[avail.time_period_code][avail.specialization_type] = avail.notes

    return InstructorAvailabilityMatrix(
        instructor_id=instructor_id,
        year=year,
        location_city=location_city,
        matrix=matrix,
        notes=notes_dict
    )


@router.post("/", response_model=InstructorAvailabilityResponse, status_code=status.HTTP_201_CREATED)
def create_instructor_availability(
    availability: InstructorAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new instructor availability record"""
    # Authorization: instructors can only create for themselves, admins can create for anyone
    if current_user.role != UserRole.ADMIN:
        if current_user.id != availability.instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only set your own availability"
            )

    # Check for duplicate
    existing = db.query(InstructorSpecializationAvailability).filter(
        InstructorSpecializationAvailability.instructor_id == availability.instructor_id,
        InstructorSpecializationAvailability.specialization_type == availability.specialization_type,
        InstructorSpecializationAvailability.time_period_code == availability.time_period_code,
        InstructorSpecializationAvailability.year == availability.year,
        InstructorSpecializationAvailability.location_city == availability.location_city
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability record already exists for this instructor/specialization/period/year/location"
        )

    # Create new record
    db_availability = InstructorSpecializationAvailability(**availability.model_dump())
    db.add(db_availability)
    db.commit()
    db.refresh(db_availability)

    return db_availability


@router.patch("/{availability_id}", response_model=InstructorAvailabilityResponse)
def update_instructor_availability(
    availability_id: int,
    availability_update: InstructorAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing instructor availability record"""
    # Get the record
    db_availability = db.query(InstructorSpecializationAvailability).filter(
        InstructorSpecializationAvailability.id == availability_id
    ).first()

    if not db_availability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability record not found"
        )

    # Authorization: instructors can only update their own, admins can update anyone's
    if current_user.role != UserRole.ADMIN:
        if current_user.id != db_availability.instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own availability"
            )

    # Update fields
    update_data = availability_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_availability, field, value)

    db.commit()
    db.refresh(db_availability)

    return db_availability


@router.post("/bulk-upsert", response_model=dict)
def bulk_upsert_instructor_availability(
    instructor_id: int,
    year: int,
    location_city: Optional[str],
    matrix: dict[str, dict[str, bool]],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk upsert instructor availability from a matrix.

    Request body:
    {
        "instructor_id": 1,
        "year": 2025,
        "location_city": "Budapest",
        "matrix": {
            "Q1": {"LFA_PLAYER_PRE": true, "LFA_PLAYER_YOUTH": true, ...},
            "Q2": {...},
            ...
        }
    }
    """
    # Authorization
    if current_user.role != UserRole.ADMIN:
        if current_user.id != instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only set your own availability"
            )

    created_count = 0
    updated_count = 0

    for time_period_code, spec_dict in matrix.items():
        for specialization_type, is_available in spec_dict.items():
            # Check if record exists
            existing = db.query(InstructorSpecializationAvailability).filter(
                InstructorSpecializationAvailability.instructor_id == instructor_id,
                InstructorSpecializationAvailability.specialization_type == specialization_type,
                InstructorSpecializationAvailability.time_period_code == time_period_code,
                InstructorSpecializationAvailability.year == year,
                InstructorSpecializationAvailability.location_city == location_city
            ).first()

            if existing:
                # Update
                existing.is_available = is_available
                existing.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create
                new_record = InstructorSpecializationAvailability(
                    instructor_id=instructor_id,
                    specialization_type=specialization_type,
                    time_period_code=time_period_code,
                    year=year,
                    location_city=location_city,
                    is_available=is_available
                )
                db.add(new_record)
                created_count += 1

    db.commit()

    return {
        "message": "Bulk upsert completed successfully",
        "created": created_count,
        "updated": updated_count,
        "total": created_count + updated_count
    }


@router.delete("/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instructor_availability(
    availability_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an instructor availability record"""
    # Get the record
    db_availability = db.query(InstructorSpecializationAvailability).filter(
        InstructorSpecializationAvailability.id == availability_id
    ).first()

    if not db_availability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability record not found"
        )

    # Authorization
    if current_user.role != UserRole.ADMIN:
        if current_user.id != db_availability.instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own availability"
            )

    db.delete(db_availability)
    db.commit()

    return None


@router.get("/instructor/{instructor_id}", response_model=List[InstructorAvailabilityResponse])
def get_instructor_availabilities(
    instructor_id: int,
    year: Optional[int] = None,
    location_city: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all availability records for a specific instructor"""
    # Authorization
    if current_user.role != UserRole.ADMIN:
        if current_user.id != instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own availability"
            )

    query = db.query(InstructorSpecializationAvailability).filter(
        InstructorSpecializationAvailability.instructor_id == instructor_id
    )

    if year:
        query = query.filter(InstructorSpecializationAvailability.year == year)
    if location_city:
        query = query.filter(InstructorSpecializationAvailability.location_city == location_city)

    availabilities = query.all()
    return availabilities
