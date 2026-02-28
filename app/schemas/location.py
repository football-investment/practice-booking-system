"""
Location Schemas
Pydantic models for Location API requests/responses
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class LocationBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Base location schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Location name (legacy field)")
    city: str = Field(..., min_length=1, max_length=100, description="City name (primary identifier)")
    postal_code: Optional[str] = Field(None, max_length=20, description="ZIP/Postal code")
    country: str = Field(..., min_length=1, max_length=100, description="Country name")
    country_code: Optional[str] = Field(None, max_length=2, description="ISO country code (e.g., HU, AT, SK)")
    location_code: Optional[str] = Field(None, max_length=10, description="Unique location code (e.g., BDPST, VIE)")
    address: Optional[str] = Field(None, max_length=500, description="General city address info")
    notes: Optional[str] = Field(None, description="Additional notes about the location")
    is_active: bool = Field(True, description="Whether this location is currently active")
    location_type: str = Field("PARTNER", description="Location capability: PARTNER or CENTER")


class LocationCreate(LocationBase):
    """Schema for creating a new location"""
    pass


class LocationUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for updating location (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    country_code: Optional[str] = Field(None, max_length=2)
    location_code: Optional[str] = Field(None, max_length=10)
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    location_type: Optional[str] = None


class LocationResponse(LocationBase):
    """Schema for location response"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
