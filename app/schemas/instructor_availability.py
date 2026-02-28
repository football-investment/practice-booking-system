"""
Instructor Specialization Availability Schemas

Pydantic schemas for instructor availability preferences.
"""

from pydantic import BaseModel, ConfigDict, Field, validator
from typing import Optional
from datetime import datetime
import re


class InstructorAvailabilityBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Base schema for instructor availability"""
    specialization_type: str = Field(..., description="LFA_PLAYER_PRE, LFA_PLAYER_YOUTH, LFA_PLAYER_AMATEUR, LFA_PLAYER_PRO")
    time_period_code: str = Field(..., description="Q1-Q4 for quarterly, M01-M12 for monthly")
    year: int = Field(..., ge=2024, le=2100, description="Year for which this availability applies")
    location_city: Optional[str] = Field(None, description="City where this availability applies")
    is_available: bool = Field(True, description="True if instructor is available for this specialization in this time period")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes from instructor")

    @validator('time_period_code')
    def validate_time_period_code(cls, v):
        """Validate time_period_code format: Q1-Q4 or M01-M12"""
        pattern = r'^(Q[1-4]|M(0[1-9]|1[0-2]))$'
        if not re.match(pattern, v):
            raise ValueError('time_period_code must be Q1-Q4 for quarterly or M01-M12 for monthly')
        return v

    @validator('specialization_type')
    def validate_specialization_type(cls, v):
        """Validate specialization type"""
        valid_types = [
            'LFA_PLAYER_PRE',
            'LFA_PLAYER_YOUTH',
            'LFA_PLAYER_AMATEUR',
            'LFA_PLAYER_PRO'
        ]
        if v not in valid_types:
            raise ValueError(f'specialization_type must be one of: {", ".join(valid_types)}')
        return v


class InstructorAvailabilityCreate(InstructorAvailabilityBase):
    """Schema for creating instructor availability"""
    instructor_id: int = Field(..., description="Instructor who sets this availability preference")


class InstructorAvailabilityUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for updating instructor availability"""
    is_available: Optional[bool] = Field(None, description="True if instructor is available")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes from instructor")


class InstructorAvailabilityResponse(InstructorAvailabilityBase):
    """Schema for instructor availability response"""
    id: int
    instructor_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstructorAvailabilityBulkUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for bulk updating instructor availability for a specific instructor/year/location"""
    instructor_id: int
    year: int
    location_city: Optional[str] = None
    availabilities: list[dict[str, bool]] = Field(
        ...,
        description="List of {specialization_type: is_available} mappings for each time period",
        example=[
            {"LFA_PLAYER_PRE": True, "LFA_PLAYER_YOUTH": True, "LFA_PLAYER_AMATEUR": False, "LFA_PLAYER_PRO": False}
        ]
    )


class InstructorAvailabilityMatrix(BaseModel):
    """
    Matrix view of instructor availability for a specific year/location.

    Example:
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
            "Q2": {...},
            "Q3": {...},
            "Q4": {...}
        }
    }
    """
    instructor_id: int
    year: int
    location_city: Optional[str] = None
    matrix: dict[str, dict[str, bool]] = Field(
        ...,
        description="Nested dict: {time_period_code: {specialization_type: is_available}}"
    )
    notes: Optional[dict[str, dict[str, Optional[str]]]] = Field(
        None,
        description="Optional notes: {time_period_code: {specialization_type: note}}"
    )
