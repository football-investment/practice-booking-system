"""
Pydantic schemas for semester enrollment endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class EnrollmentCreate(BaseModel):
    """Request to create a new semester enrollment"""
    user_id: int = Field(..., ge=1, description="Student user ID (must be positive)")
    semester_id: int = Field(..., ge=1, description="Semester ID (must be positive)")
    user_license_id: int = Field(..., ge=1, description="UserLicense ID (must be positive)")


class EnrollmentUpdate(BaseModel):
    """Request to update enrollment"""
    payment_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class EnrollmentResponse(BaseModel):
    """Enrollment response with related data"""
    id: int
    user_id: int
    user_email: str
    user_name: str
    semester_id: int
    semester_code: str
    semester_name: str
    specialization_type: str
    user_license_id: int
    payment_verified: bool
    payment_verified_at: Optional[datetime]
    is_active: bool
    request_status: str  # APPROVED, PENDING, REJECTED, WITHDRAWN
    enrolled_at: datetime


class EnrollmentRejection(BaseModel):
    """Request to reject an enrollment with optional reason"""
    reason: Optional[str] = Field(None, max_length=1000, description="Optional rejection reason")


class CategoryOverride(BaseModel):
    """Request to override age category for a student enrollment"""
    age_category: Literal["PRE", "YOUTH", "AMATEUR", "PRO"] = Field(
        ...,
        description="New age category (PRE, YOUTH, AMATEUR, PRO)"
    )
