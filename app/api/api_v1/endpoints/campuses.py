"""
Campus Management Endpoints
Admin-only CRUD operations for campuses within locations
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from ....dependencies import get_db, get_current_admin_user
from ....models.campus import Campus
from ....models.location import Location
from ....models.user import User
from ....schemas.campus import CampusCreate, CampusUpdate, CampusResponse

router = APIRouter()


@router.get("/locations/{location_id}/campuses", response_model=List[CampusResponse])
def get_campuses_by_location(
    location_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all campuses for a specific location (admin only)

    Query params:
    - include_inactive: Include inactive campuses (default: False)
    """
    # Verify location exists
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {location_id} not found"
        )

    # Build query
    query = db.query(Campus).filter(Campus.location_id == location_id)

    if not include_inactive:
        query = query.filter(Campus.is_active == True)

    campuses = query.order_by(Campus.name).all()
    return campuses


@router.get("/campuses", response_model=List[CampusResponse])
def get_all_campuses(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all campuses across all locations (admin only)

    Query params:
    - include_inactive: Include inactive campuses (default: False)
    """
    query = db.query(Campus).options(joinedload(Campus.location))

    if not include_inactive:
        query = query.filter(Campus.is_active == True)

    campuses = query.order_by(Campus.location_id, Campus.name).all()
    return campuses


@router.get("/campuses/{campus_id}", response_model=CampusResponse)
def get_campus(
    campus_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get specific campus by ID (admin only)"""
    campus = db.query(Campus).options(joinedload(Campus.location)).filter(Campus.id == campus_id).first()

    if not campus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campus with ID {campus_id} not found"
        )

    return campus


@router.post("/locations/{location_id}/campuses", response_model=CampusResponse, status_code=status.HTTP_201_CREATED)
def create_campus(
    location_id: int,
    campus_data: CampusCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Create new campus within a location (admin only)
    """
    # Verify location exists
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {location_id} not found"
        )

    # Check for duplicate campus name within this location
    existing = db.query(Campus).filter(
        and_(
            Campus.location_id == location_id,
            Campus.name == campus_data.name
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campus '{campus_data.name}' already exists in location '{location.city}'"
        )

    # Create campus
    campus = Campus(
        location_id=location_id,
        name=campus_data.name,
        venue=campus_data.venue,
        address=campus_data.address,
        notes=campus_data.notes,
        is_active=campus_data.is_active
    )

    db.add(campus)
    db.commit()
    db.refresh(campus)

    return campus


@router.put("/campuses/{campus_id}", response_model=CampusResponse)
def update_campus(
    campus_id: int,
    campus_data: CampusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update campus details (admin only)
    """
    campus = db.query(Campus).filter(Campus.id == campus_id).first()

    if not campus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campus with ID {campus_id} not found"
        )

    # Check for duplicate name if name is being changed
    if campus_data.name and campus_data.name != campus.name:
        existing = db.query(Campus).filter(
            and_(
                Campus.location_id == campus.location_id,
                Campus.name == campus_data.name,
                Campus.id != campus_id
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Campus '{campus_data.name}' already exists in this location"
            )

    # Update fields
    update_data = campus_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campus, field, value)

    db.commit()
    db.refresh(campus)

    return campus


@router.delete("/campuses/{campus_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campus(
    campus_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete campus (soft delete by setting is_active=False) (admin only)
    """
    campus = db.query(Campus).filter(Campus.id == campus_id).first()

    if not campus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campus with ID {campus_id} not found"
        )

    # Soft delete
    campus.is_active = False
    db.commit()

    return None


@router.patch("/campuses/{campus_id}/toggle-status", response_model=CampusResponse)
def toggle_campus_status(
    campus_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Activate or deactivate campus (admin only)
    """
    campus = db.query(Campus).filter(Campus.id == campus_id).first()

    if not campus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campus with ID {campus_id} not found"
        )

    campus.is_active = is_active
    db.commit()
    db.refresh(campus)

    return campus
