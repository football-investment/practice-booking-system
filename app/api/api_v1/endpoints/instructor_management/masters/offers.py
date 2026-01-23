"""
Offer Management Endpoints

Master instructor offer handling:
- Respond to offers (accept/decline)
- View my offers (instructor)
- View pending offers (admin)
- Cancel offers (admin)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.database import get_db
from app.dependencies import get_current_user, get_current_admin_user
from app.models import User
from app.models.instructor_assignment import (
    LocationMasterInstructor,
    MasterOfferStatus
)
from app.schemas.instructor_management import (
    MasterOfferResponse,
    MasterOfferAction,
    MasterInstructorResponse
)
from app.services.availability_service import (
    check_instructor_has_active_master_position,
    get_instructor_active_master_location
)
from app.services.semester_status_service import transition_to_instructor_assigned

router = APIRouter()


@router.patch("/offers/{offer_id}/respond", response_model=MasterInstructorResponse)
def respond_to_offer(
    offer_id: int,
    action: MasterOfferAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Instructor: Accept or decline master instructor offer

    Business Rules:
    - Offer must belong to current user
    - Offer must be in OFFERED status
    - Offer deadline must not have passed
    - When accepting:
      - Instructor cannot have another active master position
      - All other OFFERED contracts for this instructor auto-decline
      - Semesters transition: DRAFT → INSTRUCTOR_ASSIGNED
    """

    # Fetch offer
    master = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.id == offer_id
    ).first()

    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {offer_id} not found"
        )

    # Verify offer belongs to current user
    if master.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This offer does not belong to you"
        )

    # Check offer is in OFFERED status
    if master.offer_status != MasterOfferStatus.OFFERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Offer is {master.offer_status.value}, cannot respond"
        )

    # Check deadline not passed
    now = datetime.now(timezone.utc)
    if master.offer_deadline and master.offer_deadline < now:
        # Auto-expire
        master.offer_status = MasterOfferStatus.EXPIRED
        master.declined_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer has expired"
        )

    # Process action
    if action.action == "ACCEPT":
        # Check instructor has no other active master position
        if check_instructor_has_active_master_position(current_user.id, db):
            active_location = get_instructor_active_master_location(current_user.id, db)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You are already master at {active_location}. Cannot accept multiple master positions."
            )

        # Accept offer
        master.offer_status = MasterOfferStatus.ACCEPTED
        master.is_active = True
        master.accepted_at = now

        # Auto-decline all other OFFERED contracts for this instructor
        other_offers = db.query(LocationMasterInstructor).filter(
            LocationMasterInstructor.instructor_id == current_user.id,
            LocationMasterInstructor.id != offer_id,
            LocationMasterInstructor.offer_status == MasterOfferStatus.OFFERED
        ).all()

        for other_offer in other_offers:
            other_offer.offer_status = MasterOfferStatus.DECLINED
            other_offer.declined_at = now

        db.commit()
        db.refresh(master)

        # Trigger semester status transition
        transition_to_instructor_assigned(
            db=db,
            location_city=master.location.city,
            master_instructor_id=current_user.id
        )

    elif action.action == "DECLINE":
        # Decline offer
        master.offer_status = MasterOfferStatus.DECLINED
        master.declined_at = now
        db.commit()
        db.refresh(master)

    # Build response
    response = MasterInstructorResponse.from_orm(master)
    response.location_name = master.location.name if master.location else None
    response.instructor_name = master.instructor.name if master.instructor else None
    response.instructor_email = master.instructor.email if master.instructor else None

    return response


@router.get("/my-offers", response_model=List[MasterOfferResponse])
def get_my_master_offers(
    status: Optional[str] = None,
    include_expired: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Instructor: View all master offers sent to me

    Query Params:
    - status: Filter by offer_status (OFFERED, ACCEPTED, DECLINED, EXPIRED)
    - include_expired: Include expired offers (default False)
    """

    query = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.instructor_id == current_user.id,
        LocationMasterInstructor.offer_status != None  # Exclude legacy contracts
    )

    # Filter by status
    if status:
        try:
            status_enum = MasterOfferStatus[status.upper()]
            query = query.filter(LocationMasterInstructor.offer_status == status_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Valid: OFFERED, ACCEPTED, DECLINED, EXPIRED"
            )

    # Exclude expired if requested
    if not include_expired:
        query = query.filter(LocationMasterInstructor.offer_status != MasterOfferStatus.EXPIRED)

    offers = query.all()

    # Build responses
    responses = []
    now = datetime.now(timezone.utc)
    for offer in offers:
        days_remaining = (offer.offer_deadline - now).days if offer.offer_deadline else 0

        response = MasterOfferResponse(
            id=offer.id,
            location_id=offer.location_id,
            instructor_id=offer.instructor_id,
            contract_start=offer.contract_start,
            contract_end=offer.contract_end,
            offer_status=offer.offer_status,
            is_active=offer.is_active,
            offered_at=offer.offered_at,
            offer_deadline=offer.offer_deadline,
            hiring_pathway=offer.hiring_pathway,
            availability_override=offer.availability_override,
            availability_warnings=[],
            availability_match_score=100,  # Not calculated for list view
            location_name=offer.location.name if offer.location else None,
            location_city=offer.location.city if offer.location else None,
            instructor_name=offer.instructor.name if offer.instructor else None,
            instructor_email=offer.instructor.email if offer.instructor else None
        )

        responses.append(response)

    return responses


@router.get("/pending-offers", response_model=List[MasterOfferResponse])
def get_pending_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Admin: View all pending master offers across all locations
    """

    pending = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.offer_status == MasterOfferStatus.OFFERED
    ).all()

    responses = []
    now = datetime.now(timezone.utc)

    for offer in pending:
        days_remaining = (offer.offer_deadline - now).days if offer.offer_deadline else 0

        response = MasterOfferResponse(
            id=offer.id,
            location_id=offer.location_id,
            instructor_id=offer.instructor_id,
            contract_start=offer.contract_start,
            contract_end=offer.contract_end,
            offer_status=offer.offer_status,
            is_active=offer.is_active,
            offered_at=offer.offered_at,
            offer_deadline=offer.offer_deadline,
            hiring_pathway=offer.hiring_pathway,
            availability_override=offer.availability_override,
            availability_warnings=[],
            availability_match_score=100,
            location_name=offer.location.name if offer.location else None,
            location_city=offer.location.city if offer.location else None,
            instructor_name=offer.instructor.name if offer.instructor else None,
            instructor_email=offer.instructor.email if offer.instructor else None
        )

        responses.append(response)

    return responses


@router.delete("/offers/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Admin: Cancel pending offer before instructor responds
    """

    offer = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.id == offer_id
    ).first()

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {offer_id} not found"
        )

    if offer.offer_status != MasterOfferStatus.OFFERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only cancel OFFERED contracts, this is {offer.offer_status.value}"
        )

    # Mark as declined (cancelled by admin)
    offer.offer_status = MasterOfferStatus.DECLINED
    offer.declined_at = datetime.now(timezone.utc)

    db.commit()

    return None
