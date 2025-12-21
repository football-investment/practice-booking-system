"""
Campus Schemas
Pydantic models for Campus API requests/responses
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CampusBase(BaseModel):
    """Base campus schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Campus name (e.g., 'Buda Campus', 'Main Field')")
    venue: Optional[str] = Field(None, max_length=200, description="Venue/facility name")
    address: Optional[str] = Field(None, max_length=500, description="Full street address")
    notes: Optional[str] = Field(None, description="Additional notes about the campus")
    is_active: bool = Field(True, description="Whether this campus is currently active")


class CampusCreate(CampusBase):
    """Schema for creating a new campus"""
    pass


class CampusUpdate(BaseModel):
    """Schema for updating campus (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    venue: Optional[str] = Field(None, max_length=200)
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CampusResponse(CampusBase):
    """Schema for campus response"""
    id: int
    location_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampusWithLocation(CampusResponse):
    """Campus response with location details"""
    location_city: Optional[str] = None
    location_country: Optional[str] = None

    class Config:
        from_attributes = True
