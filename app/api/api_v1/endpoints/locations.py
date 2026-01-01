"""
📍 Location Management Endpoints

Admin endpoints for managing LFA Education Centers.
Only admin users can create, update, or delete locations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from ....database import get_db
from ....models.location import Location
from ....models.campus import Campus
from ....dependencies import get_current_admin_user

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class LocationCreate(BaseModel):
    """Schema for creating a new location"""
    name: str
    city: str
    postal_code: str | None = None
    country: str
    location_type: str = "CENTER"  # NEW: PARTNER or CENTER
    venue: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool = True


class LocationUpdate(BaseModel):
    """Schema for updating an existing location"""
    name: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    location_type: str | None = None  # NEW: PARTNER or CENTER
    venue: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class LocationResponse(BaseModel):
    """Schema for location response"""
    id: int
    name: str
    city: str
    postal_code: str | None
    country: str
    location_type: str  # NEW: PARTNER or CENTER
    venue: str | None
    address: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[LocationResponse])
async def get_all_locations(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """
    Get all locations.

    **Admin only**

    Query Parameters:
    - include_inactive: If True, includes inactive locations (default: False)
    """
    query = db.query(Location)

    if not include_inactive:
        query = query.filter(Location.is_active == True)

    locations = query.order_by(Location.country, Location.city, Location.name).all()
    return locations


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """
    Get a specific location by ID.

    **Admin only**
    """
    location = db.query(Location).filter(Location.id == location_id).first()

    if not location:
        raise HTTPException(status_code=404, detail=f"Location with ID {location_id} not found")

    return location


@router.post("/", response_model=LocationResponse, status_code=201)
async def create_location(
    location_data: LocationCreate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """
    Create a new LFA Education Center location.

    **Admin only**

    Example:
    ```json
    {
        "name": "LFA Education Center - Budapest",
        "city": "Budapest",
        "country": "Hungary",
        "venue": "Buda Campus",
        "address": "1011 Budapest, Fő utca 1.",
        "notes": "Main campus in Hungary",
        "is_active": true
    }
    ```
    """
    # Check if location with same name already exists
    existing = db.query(Location).filter(Location.name == location_data.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Location with name '{location_data.name}' already exists"
        )

    location = Location(
        name=location_data.name,
        city=location_data.city,
        postal_code=location_data.postal_code,
        country=location_data.country,
        location_type=location_data.location_type,  # NEW: PARTNER or CENTER
        venue=location_data.venue,
        address=location_data.address,
        notes=location_data.notes,
        is_active=location_data.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(location)
    db.commit()
    db.refresh(location)

    return location


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: int,
    location_data: LocationUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """
    Update an existing location.

    **Admin only**

    **CASCADE INACTIVATION:** If location is being set to inactive (is_active=False),
    all campuses belonging to this location will also be automatically inactivated.
    """
    location = db.query(Location).filter(Location.id == location_id).first()

    if not location:
        raise HTTPException(status_code=404, detail=f"Location with ID {location_id} not found")

    # Check if location is being inactivated
    update_data = location_data.model_dump(exclude_unset=True)
    is_being_inactivated = (
        'is_active' in update_data and
        update_data['is_active'] is False and
        location.is_active is True
    )

    # Update only provided fields
    for field, value in update_data.items():
        setattr(location, field, value)

    location.updated_at = datetime.utcnow()

    # CASCADE: If location is being inactivated, also inactivate all its campuses
    if is_being_inactivated:
        campuses = db.query(Campus).filter(Campus.location_id == location_id).all()
        for campus in campuses:
            if campus.is_active:  # Only update if currently active
                campus.is_active = False
                campus.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(location)

    return location


@router.delete("/{location_id}", status_code=204)
async def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """
    Delete a location (soft delete by setting is_active = False).

    **Admin only**

    **CASCADE INACTIVATION:** When a location is deleted (soft-deleted),
    all campuses belonging to this location will also be automatically inactivated.

    Note: This is a soft delete. The location and its campuses remain in the database
    but are marked inactive.
    """
    location = db.query(Location).filter(Location.id == location_id).first()

    if not location:
        raise HTTPException(status_code=404, detail=f"Location with ID {location_id} not found")

    # Soft delete location
    location.is_active = False
    location.updated_at = datetime.utcnow()

    # CASCADE: Also inactivate all campuses belonging to this location
    campuses = db.query(Campus).filter(Campus.location_id == location_id).all()
    for campus in campuses:
        if campus.is_active:  # Only update if currently active
            campus.is_active = False
            campus.updated_at = datetime.utcnow()

    db.commit()

    return None


@router.get("/active/list", response_model=List[LocationResponse])
async def get_active_locations(
    db: Session = Depends(get_db)
):
    """
    Get all active locations (public endpoint for dropdowns).

    Used by semester generation UI to show available locations.
    """
    locations = db.query(Location).filter(
        Location.is_active == True
    ).order_by(Location.country, Location.city, Location.name).all()

    return locations
