"""
Legacy Endpoints (Backward Compatibility)

Older master instructor management endpoints for backward compatibility:
- Create master instructor (immediate active, no offer workflow)
- Get master for location
- List all masters
- Update master instructor contract
- Terminate master instructor contract
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_admin_user
from app.models import User, Location
from app.models.instructor_assignment import LocationMasterInstructor
from app.schemas.instructor_management import (
    MasterInstructorCreate,
    MasterInstructorResponse,
    MasterInstructorUpdate,
    MasterInstructorListResponse
)
from app.services.semester_status_service import transition_to_instructor_assigned

router = APIRouter()


@router.post("/", response_model=MasterInstructorResponse, status_code=status.HTTP_201_CREATED)
def create_master_instructor_legacy(
    data: MasterInstructorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Admin: Hire master instructor (LEGACY - immediate active, no offer workflow)

    DEPRECATED: Use /direct-hire for new hiring with offer workflow
    Kept for backward compatibility with existing code
    """

    location = db.query(Location).filter(Location.id == data.location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location {data.location_id} not found"
        )

    instructor = db.query(User).filter(User.id == data.instructor_id).first()
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instructor {data.instructor_id} not found"
        )

    existing_master = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.location_id == data.location_id,
        LocationMasterInstructor.is_active == True
    ).first()

    if existing_master:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location {location.name} already has an active master instructor"
        )

    # Create legacy immediate-active contract (offer_status = NULL)
    master = LocationMasterInstructor(
        location_id=data.location_id,
        instructor_id=data.instructor_id,
        contract_start=data.contract_start,
        contract_end=data.contract_end,
        is_active=True,
        offer_status=None,  # NULL = legacy immediate-active
        hiring_pathway='DIRECT'
    )

    db.add(master)
    db.commit()
    db.refresh(master)

    # Trigger semester transition
    transition_to_instructor_assigned(
        db=db,
        location_city=location.city,
        master_instructor_id=data.instructor_id
    )

    response = MasterInstructorResponse.from_orm(master)
    response.location_name = location.name
    response.instructor_name = instructor.name
    response.instructor_email = instructor.email

    return response


@router.get("/{location_id}", response_model=MasterInstructorResponse)
def get_master_for_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Admin: Get current master instructor for a location
    """

    master = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.location_id == location_id,
        LocationMasterInstructor.is_active == True
    ).first()

    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active master instructor found for location {location_id}"
        )

    response = MasterInstructorResponse.from_orm(master)
    response.location_name = master.location.name if master.location else None
    response.instructor_name = master.instructor.name if master.instructor else None
    response.instructor_email = master.instructor.email if master.instructor else None

    return response


@router.get("/", response_model=MasterInstructorListResponse)
def list_all_masters(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Admin: List all master instructors
    """

    query = db.query(LocationMasterInstructor)

    if not include_inactive:
        query = query.filter(LocationMasterInstructor.is_active == True)

    masters = query.all()

    master_responses = []
    for master in masters:
        response = MasterInstructorResponse.from_orm(master)
        response.location_name = master.location.name if master.location else None
        response.instructor_name = master.instructor.name if master.instructor else None
        response.instructor_email = master.instructor.email if master.instructor else None
        master_responses.append(response)

    return MasterInstructorListResponse(
        total=len(master_responses),
        masters=master_responses
    )


@router.patch("/{master_id}", response_model=MasterInstructorResponse)
def update_master_instructor(
    master_id: int,
    data: MasterInstructorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Admin: Update master instructor contract
    """

    master = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.id == master_id
    ).first()

    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master instructor {master_id} not found"
        )

    if data.contract_end is not None:
        master.contract_end = data.contract_end

    if data.is_active is not None:
        if data.is_active == False and master.is_active == True:
            master.is_active = False
            master.terminated_at = datetime.now()
        elif data.is_active == True and master.is_active == False:
            existing_active = db.query(LocationMasterInstructor).filter(
                LocationMasterInstructor.location_id == master.location_id,
                LocationMasterInstructor.is_active == True,
                LocationMasterInstructor.id != master_id
            ).first()

            if existing_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another master is already active for this location"
                )

            master.is_active = True
            master.terminated_at = None

    db.commit()
    db.refresh(master)

    response = MasterInstructorResponse.from_orm(master)
    response.location_name = master.location.name if master.location else None
    response.instructor_name = master.instructor.name if master.instructor else None
    response.instructor_email = master.instructor.email if master.instructor else None

    return response


@router.delete("/{master_id}", status_code=status.HTTP_204_NO_CONTENT)
def terminate_master_instructor(
    master_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Admin: Terminate master instructor contract
    """

    master = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.id == master_id
    ).first()

    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master instructor {master_id} not found"
        )

    if not master.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Master instructor is already terminated"
        )

    master.is_active = False
    master.terminated_at = datetime.now()

    db.commit()

    return None
