"""
Position Posting Endpoints

Master instructors can:
- Post job openings for assistant positions
- List their posted positions
- Update/close positions

All instructors can:
- View public job board (positions they can apply to)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_user, get_current_admin_user
from app.models import User, Location, InstructorPosition, PositionApplication, LocationMasterInstructor, PositionStatus
from app.schemas.instructor_management import (
    PositionCreate,
    PositionResponse,
    PositionUpdate,
    PositionListResponse,
    JobBoardPosition,
    JobBoardResponse,
    PositionStatusEnum
)

router = APIRouter()


@router.post("/", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
def create_position(
    data: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Master Instructor: Post a new position opening

    Business Rules:
    - User must be a master instructor for the location
    - Position details must be valid
    - Application deadline must be in the future
    """

    # Check if user is master instructor for this location
    master = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.location_id == data.location_id,
        LocationMasterInstructor.instructor_id == current_user.id,
        LocationMasterInstructor.is_active == True
    ).first()

    if not master:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the master instructor for this location"
        )

    # Check if location exists
    location = db.query(Location).filter(Location.id == data.location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location {data.location_id} not found"
        )

    # CRITICAL VALIDATION: Check if matching semester exists
    # Business rule: Cannot post position if no semester exists for this spec/age_group at location
    # Note: Semester uses dates, position uses year/period - we only validate spec+age_group+location
    from app.models.semester import Semester, SemesterStatus

    matching_semester = db.query(Semester).filter(
        Semester.location_id == data.location_id,
        Semester.specialization_type == data.specialization_type,
        Semester.age_group == data.age_group,
        Semester.is_active == True,
        Semester.status.in_([
            SemesterStatus.DRAFT,
            SemesterStatus.SEEKING_INSTRUCTOR,
            SemesterStatus.INSTRUCTOR_ASSIGNED,
            SemesterStatus.READY_FOR_ENROLLMENT,
            SemesterStatus.ONGOING
        ])
    ).first()

    if not matching_semester:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"No active semester found for {data.specialization_type} - {data.age_group} at this location. "
                f"Admin must create a semester for this specialization/age group before you can post positions."
            )
        )

    # Create position
    position = InstructorPosition(
        location_id=data.location_id,
        posted_by=current_user.id,
        specialization_type=data.specialization_type,
        age_group=data.age_group,
        year=data.year,
        time_period_start=data.time_period_start,
        time_period_end=data.time_period_end,
        description=data.description,
        priority=data.priority,
        application_deadline=data.application_deadline,
        status=PositionStatus.OPEN
    )

    db.add(position)
    db.commit()
    db.refresh(position)

    # Build response
    response = PositionResponse.from_orm(position)
    response.location_name = location.name
    response.master_name = current_user.name
    response.application_count = 0

    return response


@router.get("/my-positions", response_model=PositionListResponse)
def list_my_positions(
    location_id: Optional[int] = Query(None, description="Filter by location"),
    status_filter: Optional[PositionStatusEnum] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Master Instructor: List positions I've posted
    """

    query = db.query(InstructorPosition).filter(
        InstructorPosition.posted_by == current_user.id
    )

    if location_id:
        query = query.filter(InstructorPosition.location_id == location_id)

    if status_filter:
        query = query.filter(InstructorPosition.status == PositionStatus[status_filter.value])

    positions = query.order_by(InstructorPosition.created_at.desc()).all()

    # Build responses
    position_responses = []
    for pos in positions:
        response = PositionResponse.from_orm(pos)
        response.location_name = pos.location.name if pos.location else None
        response.master_name = pos.master.name if pos.master else None
        response.application_count = len(pos.applications) if hasattr(pos, 'applications') else 0
        position_responses.append(response)

    return PositionListResponse(
        total=len(position_responses),
        positions=position_responses
    )


@router.get("/job-board", response_model=JobBoardResponse)
def get_job_board(
    location_id: Optional[int] = Query(None, description="Filter by location"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    All Instructors: View public job board

    Shows OPEN positions that instructors can apply to.
    Includes flag showing if current user has already applied.
    """

    query = db.query(InstructorPosition).filter(
        InstructorPosition.status == PositionStatus.OPEN
    )

    if location_id:
        query = query.filter(InstructorPosition.location_id == location_id)

    if specialization:
        query = query.filter(InstructorPosition.specialization_type == specialization)

    positions = query.order_by(
        InstructorPosition.priority.desc(),
        InstructorPosition.application_deadline.asc()
    ).all()

    # Build job board responses
    job_board_positions = []
    for pos in positions:
        # Check if current user has applied
        user_application = db.query(PositionApplication).filter(
            PositionApplication.position_id == pos.id,
            PositionApplication.applicant_id == current_user.id
        ).first()

        job_pos = JobBoardPosition(
            id=pos.id,
            location_name=pos.location.name if pos.location else "Unknown",
            specialization_type=pos.specialization_type,
            age_group=pos.age_group,
            year=pos.year,
            period=f"{pos.time_period_start}-{pos.time_period_end}",
            description=pos.description,
            priority=pos.priority,
            application_deadline=pos.application_deadline,
            posted_by_name=pos.master.name if pos.master else "Unknown",
            created_at=pos.created_at,
            user_has_applied=user_application is not None,
            user_application_status=user_application.status if user_application else None
        )
        job_board_positions.append(job_pos)

    return JobBoardResponse(
        total=len(job_board_positions),
        positions=job_board_positions
    )


@router.get("/{position_id}", response_model=PositionResponse)
def get_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get position details

    Accessible to:
    - Master instructor who posted it
    - Any instructor (for job board viewing)
    - Admins
    """

    position = db.query(InstructorPosition).filter(
        InstructorPosition.id == position_id
    ).first()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position {position_id} not found"
        )

    # Build response
    response = PositionResponse.from_orm(position)
    response.location_name = position.location.name if position.location else None
    response.master_name = position.master.name if position.master else None
    response.application_count = len(position.applications) if hasattr(position, 'applications') else 0

    return response


@router.patch("/{position_id}", response_model=PositionResponse)
def update_position(
    position_id: int,
    data: PositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Master Instructor: Update a position

    Can update:
    - Description
    - Priority
    - Application deadline
    - Status (close/cancel position)
    """

    position = db.query(InstructorPosition).filter(
        InstructorPosition.id == position_id
    ).first()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position {position_id} not found"
        )

    # Check if user is the master who posted it
    if position.posted_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own positions"
        )

    # Update fields
    if data.description is not None:
        position.description = data.description

    if data.priority is not None:
        position.priority = data.priority

    if data.application_deadline is not None:
        position.application_deadline = data.application_deadline

    if data.status is not None:
        position.status = PositionStatus[data.status.value]

    db.commit()
    db.refresh(position)

    # Build response
    response = PositionResponse.from_orm(position)
    response.location_name = position.location.name if position.location else None
    response.master_name = position.master.name if position.master else None
    response.application_count = len(position.applications) if hasattr(position, 'applications') else 0

    return response


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Master Instructor: Delete a position

    Only allowed if:
    - Position has no applications yet
    - Or user is admin (override)
    """

    position = db.query(InstructorPosition).filter(
        InstructorPosition.id == position_id
    ).first()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position {position_id} not found"
        )

    # Check ownership (unless admin)
    is_admin = current_user.role == "ADMIN"
    if not is_admin and position.posted_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own positions"
        )

    # Check for applications
    application_count = db.query(PositionApplication).filter(
        PositionApplication.position_id == position_id
    ).count()

    if application_count > 0 and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete position with existing applications. Cancel it instead."
        )

    db.delete(position)
    db.commit()

    return None
