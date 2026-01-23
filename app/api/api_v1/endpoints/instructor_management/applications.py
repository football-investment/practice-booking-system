"""
Application Management Endpoints

Instructors can:
- Apply to positions
- View their applications

Master instructors can:
- View applications to their positions
- Accept/decline applications
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, InstructorPosition, PositionApplication, ApplicationStatus, PositionStatus
from app.schemas.instructor_management import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
    ApplicationListResponse,
    ApplicationStatusEnum
)

router = APIRouter()


@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    data: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Instructor: Apply to a position

    Business Rules:
    - Position must be OPEN
    - Instructor can only apply once per position
    - Application deadline must not have passed
    """

    # Check if position exists
    position = db.query(InstructorPosition).filter(
        InstructorPosition.id == data.position_id
    ).first()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position {data.position_id} not found"
        )

    # Check if position is OPEN
    if position.status != PositionStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position is not accepting applications"
        )

    # Check deadline
    if position.application_deadline < datetime.now(position.application_deadline.tzinfo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application deadline has passed"
        )

    # Check for duplicate application
    existing = db.query(PositionApplication).filter(
        PositionApplication.position_id == data.position_id,
        PositionApplication.applicant_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied to this position"
        )

    # CRITICAL VALIDATION: Check instructor availability (PATHWAY B - Job Posting)
    # Business rule: Instructor can ONLY apply if they marked themselves as available
    from app.models.instructor_availability import InstructorSpecializationAvailability
    from app.models.location import Location

    # Get location city for matching
    location = db.query(Location).filter(Location.id == position.location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Position location not found"
        )

    # Check if instructor has availability record for this spec/year/period/location
    availability = db.query(InstructorSpecializationAvailability).filter(
        InstructorSpecializationAvailability.instructor_id == current_user.id,
        InstructorSpecializationAvailability.specialization_type == position.specialization_type,
        InstructorSpecializationAvailability.year == position.year,
        InstructorSpecializationAvailability.time_period_code == position.time_period_start,  # Assume start period
        InstructorSpecializationAvailability.location_city == location.city,
        InstructorSpecializationAvailability.is_available == True
    ).first()

    if not availability:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"You cannot apply to this position because you have not marked yourself as available "
                f"for {position.specialization_type} in {location.city} during {position.year} {position.time_period_start}. "
                f"Please update your availability settings first in your profile."
            )
        )

    # VALIDATION 6: Check if instructor has required LICENSE
    # Business rule: Instructor must have active license for this specialization
    from app.models.license import UserLicense

    required_license = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id,
        UserLicense.specialization_type == position.specialization_type,
        UserLicense.is_active == True,
        UserLicense.current_level >= 1  # Minimum level 1 required
    ).first()

    if not required_license:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"You do not have an active {position.specialization_type} license. "
                f"Only instructors with verified licenses can apply to positions."
            )
        )

    # VALIDATION 7: Check if instructor is already a MASTER instructor elsewhere
    # Business rule: Cannot be master at multiple locations simultaneously
    from app.models.instructor_assignment import LocationMasterInstructor

    existing_master = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.instructor_id == current_user.id,
        LocationMasterInstructor.is_active == True,
        LocationMasterInstructor.location_id != position.location_id  # Different location
    ).first()

    if existing_master:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"You are already serving as Master Instructor at another location. "
                f"You must terminate that position before applying to new positions."
            )
        )

    # VALIDATION 8: Check for TIME CONFLICTS with other assignments
    # Business rule: Cannot teach at multiple locations in the same time period
    from app.models.instructor_assignment import InstructorAssignment

    conflicting_assignment = db.query(InstructorAssignment).filter(
        InstructorAssignment.instructor_id == current_user.id,
        InstructorAssignment.is_active == True,
        InstructorAssignment.year == position.year,
        InstructorAssignment.time_period_start == position.time_period_start,
        InstructorAssignment.age_group == position.age_group,
        InstructorAssignment.specialization_type == position.specialization_type
    ).first()

    if conflicting_assignment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"You already have an active assignment for {position.specialization_type} - {position.age_group} "
                f"during {position.year} {position.time_period_start}. "
                f"You cannot apply to multiple positions in the same time period."
            )
        )

    # Create application
    application = PositionApplication(
        position_id=data.position_id,
        applicant_id=current_user.id,
        application_message=data.application_message,
        status=ApplicationStatus.PENDING
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    # Build response
    response = ApplicationResponse.from_orm(application)
    response.applicant_name = current_user.name
    response.applicant_email = current_user.email
    response.position_title = f"{position.specialization_type}/{position.age_group} {position.time_period_start}-{position.time_period_end}"

    return response


@router.get("/my-applications", response_model=ApplicationListResponse)
def list_my_applications(
    status_filter: Optional[ApplicationStatusEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Instructor: List my applications
    """

    query = db.query(PositionApplication).filter(
        PositionApplication.applicant_id == current_user.id
    )

    if status_filter:
        query = query.filter(PositionApplication.status == ApplicationStatus[status_filter.value])

    applications = query.order_by(PositionApplication.created_at.desc()).all()

    # Build responses
    app_responses = []
    for app in applications:
        response = ApplicationResponse.from_orm(app)
        response.applicant_name = current_user.name
        response.applicant_email = current_user.email
        if app.position:
            response.position_title = f"{app.position.specialization_type}/{app.position.age_group} {app.position.time_period_start}-{app.position.time_period_end}"
        app_responses.append(response)

    return ApplicationListResponse(
        total=len(app_responses),
        applications=app_responses
    )


@router.get("/for-position/{position_id}", response_model=ApplicationListResponse)
def list_applications_for_position(
    position_id: int,
    status_filter: Optional[ApplicationStatusEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Master Instructor: View applications for my posted position
    """

    # Check if position exists and user is the poster
    position = db.query(InstructorPosition).filter(
        InstructorPosition.id == position_id
    ).first()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position {position_id} not found"
        )

    if position.posted_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view applications for your own positions"
        )

    # Get applications
    query = db.query(PositionApplication).filter(
        PositionApplication.position_id == position_id
    )

    if status_filter:
        query = query.filter(PositionApplication.status == ApplicationStatus[status_filter.value])

    applications = query.order_by(PositionApplication.created_at.asc()).all()

    # Build responses
    app_responses = []
    for app in applications:
        response = ApplicationResponse.from_orm(app)
        if app.applicant:
            response.applicant_name = app.applicant.name
            response.applicant_email = app.applicant.email
        response.position_title = f"{position.specialization_type}/{position.age_group} {position.time_period_start}-{position.time_period_end}"
        app_responses.append(response)

    return ApplicationListResponse(
        total=len(app_responses),
        applications=app_responses
    )


@router.patch("/{application_id}", response_model=ApplicationResponse)
def review_application(
    application_id: int,
    data: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Master Instructor: Accept or decline an application
    """

    application = db.query(PositionApplication).filter(
        PositionApplication.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )

    # Check if user is the master who posted the position
    if application.position.posted_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only review applications for your own positions"
        )

    # Check current status
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application has already been {application.status.value.lower()}"
        )

    # Update application
    application.status = ApplicationStatus[data.status.value]
    application.reviewed_at = datetime.now()

    db.commit()
    db.refresh(application)

    # Build response
    response = ApplicationResponse.from_orm(application)
    if application.applicant:
        response.applicant_name = application.applicant.name
        response.applicant_email = application.applicant.email
    if application.position:
        response.position_title = f"{application.position.specialization_type}/{application.position.age_group} {application.position.time_period_start}-{application.position.time_period_end}"

    return response


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get application details

    Accessible to:
    - The applicant
    - The master instructor who posted the position
    """

    application = db.query(PositionApplication).filter(
        PositionApplication.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )

    # Check access
    is_applicant = application.applicant_id == current_user.id
    is_master = application.position.posted_by == current_user.id if application.position else False

    if not (is_applicant or is_master):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this application"
        )

    # Build response
    response = ApplicationResponse.from_orm(application)
    if application.applicant:
        response.applicant_name = application.applicant.name
        response.applicant_email = application.applicant.email
    if application.position:
        response.position_title = f"{application.position.specialization_type}/{application.position.age_group} {application.position.time_period_start}-{application.position.time_period_end}"

    return response
