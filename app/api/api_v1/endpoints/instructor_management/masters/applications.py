"""
Job Application Hiring Endpoints (Pathway B)

Master instructor hiring via job postings:
- Instructors apply to job postings
- Admin reviews and accepts application
- Creates master offer (still needs formal acceptance)
- Auto-declines other applications for same position
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.dependencies import get_current_admin_user
from app.models.instructor_assignment import (
    LocationMasterInstructor,
    MasterOfferStatus,
    PositionApplication,
    ApplicationStatus,
    PositionStatus
)
from app.schemas.instructor_management import (
    HireFromApplicationRequest,
    MasterOfferResponse
)

router = APIRouter()


@router.post("/hire-from-application", response_model=MasterOfferResponse, status_code=status.HTTP_201_CREATED)
def hire_from_application(
    data: HireFromApplicationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Admin: Accept application and create master offer (Pathway B)

    Workflow:
    1. Admin accepts application
    2. Creates OFFERED contract (instructor still must accept!)
    3. Auto-declines other PENDING applications for position
    4. Marks position as FILLED

    Business Rule: Application acceptance ≠ contract acceptance!
    Instructor applied = intent, but still must formally accept contract.
    """

    # Fetch application
    application = db.query(PositionApplication).filter(
        PositionApplication.id == data.application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {data.application_id} not found"
        )

    # Check application is PENDING
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application is {application.status.value}, cannot hire"
        )

    # Check position is master position
    position = application.position
    if not position.is_master_position:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not a master position - use assistant hiring endpoint"
        )

    # Check location has no active master
    location = position.location
    existing_master = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.location_id == location.id,
        LocationMasterInstructor.is_active == True,
        (
            (LocationMasterInstructor.offer_status == None) |
            (LocationMasterInstructor.offer_status == MasterOfferStatus.ACCEPTED)
        )
    ).first()

    if existing_master:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location {location.name} already has an active master"
        )

    # Accept application
    application.status = ApplicationStatus.ACCEPTED
    application.reviewed_at = datetime.now(timezone.utc)

    # Calculate offer deadline
    now = datetime.now(timezone.utc)
    offer_deadline = now + timedelta(days=data.offer_deadline_days)

    # Create OFFERED contract
    master = LocationMasterInstructor(
        location_id=location.id,
        instructor_id=application.applicant_id,
        contract_start=data.contract_start,
        contract_end=data.contract_end,
        is_active=False,  # Not active until accepted
        offer_status=MasterOfferStatus.OFFERED,
        offered_at=now,
        offer_deadline=offer_deadline,
        hiring_pathway='JOB_POSTING',
        source_position_id=position.id,
        availability_override=False
    )

    db.add(master)

    # Auto-decline other PENDING applications for this position
    other_applications = db.query(PositionApplication).filter(
        PositionApplication.position_id == position.id,
        PositionApplication.id != data.application_id,
        PositionApplication.status == ApplicationStatus.PENDING
    ).all()

    for other_app in other_applications:
        other_app.status = ApplicationStatus.DECLINED
        other_app.reviewed_at = now

    # Mark position as FILLED
    position.status = PositionStatus.FILLED

    db.commit()
    db.refresh(master)

    # Build response
    instructor = application.applicant
    response = MasterOfferResponse(
        id=master.id,
        location_id=master.location_id,
        instructor_id=master.instructor_id,
        contract_start=master.contract_start,
        contract_end=master.contract_end,
        offer_status=master.offer_status,
        is_active=master.is_active,
        offered_at=master.offered_at,
        offer_deadline=master.offer_deadline,
        hiring_pathway=master.hiring_pathway,
        availability_override=master.availability_override,
        availability_warnings=[],
        availability_match_score=100,
        location_name=location.name,
        location_city=location.city,
        instructor_name=instructor.name,
        instructor_email=instructor.email
    )

    return response
