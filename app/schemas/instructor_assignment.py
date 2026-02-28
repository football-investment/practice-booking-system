"""
Pydantic schemas for Instructor Assignment Request System
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional
from enum import Enum

class AssignmentRequestStatusEnum(str, Enum):
    """Status of instructor assignment request"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


# ============================================================================
# InstructorAvailabilityWindow Schemas
# ============================================================================

class InstructorAvailabilityWindowBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Base schema for availability window - NO LOCATION (comes from assignment request)"""
    year: int = Field(..., ge=2024, le=2100, description="Year (e.g., 2026)")
    time_period: str = Field(..., max_length=10, description="Q1, Q2, Q3, Q4 or M01-M12")
    is_available: bool = Field(default=True, description="True if instructor is available")
    notes: Optional[str] = Field(None, description="Optional notes from instructor")

    @field_validator('time_period')
    @classmethod
    def validate_time_period(cls, v: str) -> str:
        """Validate time period format"""
        if not re.match(r'^(Q[1-4]|M(0[1-9]|1[0-2]))$', v):
            raise ValueError('time_period must be Q1-Q4 or M01-M12')
        return v


class InstructorAvailabilityWindowCreate(InstructorAvailabilityWindowBase):
    """Schema for creating availability window"""
    instructor_id: int = Field(..., description="Instructor setting availability")


class InstructorAvailabilityWindowUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for updating availability window"""
    is_available: Optional[bool] = None
    notes: Optional[str] = None


class InstructorAvailabilityWindowResponse(InstructorAvailabilityWindowBase):
    """Schema for availability window response"""
    id: int
    instructor_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# InstructorAssignmentRequest Schemas
# ============================================================================

class InstructorAssignmentRequestBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Base schema for assignment request"""
    request_message: Optional[str] = Field(None, description="Message from admin to instructor")
    priority: int = Field(default=0, ge=0, le=10, description="Priority 0-10")


class InstructorAssignmentRequestCreate(InstructorAssignmentRequestBase):
    """Schema for creating assignment request"""
    semester_id: int = Field(..., description="Semester needing an instructor")
    instructor_id: int = Field(..., description="Instructor receiving the request")
    expires_at: Optional[datetime] = Field(None, description="Request expiration (optional)")


class InstructorAssignmentRequestUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for updating assignment request"""
    status: Optional[AssignmentRequestStatusEnum] = None
    response_message: Optional[str] = None


class InstructorAssignmentRequestAccept(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for instructor accepting request"""
    response_message: Optional[str] = Field(None, description="Optional message from instructor")


class InstructorAssignmentRequestDecline(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for instructor declining request"""
    response_message: str = Field(..., min_length=1, description="Reason for declining (required)")


class InstructorAssignmentRequestResponse(InstructorAssignmentRequestBase):
    """Schema for assignment request response"""
    id: int
    semester_id: int
    instructor_id: int
    requested_by: Optional[int]
    status: AssignmentRequestStatusEnum
    created_at: datetime
    responded_at: Optional[datetime]
    expires_at: Optional[datetime]
    response_message: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Helper Schemas
# ============================================================================

class InstructorLicenseInfo(BaseModel):
    """Detailed license information for instructor"""
    license_id: int
    specialization_type: str
    current_level: int
    max_achieved_level: int
    started_at: datetime
    last_advanced_at: Optional[datetime] = None


class AvailableInstructorInfo(BaseModel):
    """Info about available instructor for a time period/location"""
    instructor_id: int
    instructor_name: str
    instructor_email: str
    availability_windows: list[InstructorAvailabilityWindowResponse]
    licenses: list[InstructorLicenseInfo] = Field(default_factory=list, description="Instructor's licenses with belt/level info")


class AvailableInstructorsQuery(BaseModel):
    """Query parameters for finding available instructors"""
    year: int = Field(..., ge=2024, le=2100)
    time_period: str = Field(..., max_length=10)
    location_city: str = Field(..., max_length=100)

    @field_validator('time_period')
    @classmethod
    def validate_time_period(cls, v: str) -> str:
        """Validate time period format"""
        if not re.match(r'^(Q[1-4]|M(0[1-9]|1[0-2]))$', v):
            raise ValueError('time_period must be Q1-Q4 or M01-M12')
        return v
