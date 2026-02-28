"""
Pydantic schemas for Two-Tier Instructor Management System

Handles:
- Master instructor contracts (location-level) with hybrid hiring pathways
- Position postings by masters (assistant + master openings)
- Applications from instructors
- Instructor assignments (supports co-instructors)
"""

from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, validator
from enum import Enum


# ============================================================================
# Enums
# ============================================================================


class MasterOfferStatusEnum(str, Enum):
    """Status of master instructor offer"""
    OFFERED = "OFFERED"      # Offer sent, awaiting instructor response
    ACCEPTED = "ACCEPTED"    # Instructor accepted offer
    DECLINED = "DECLINED"    # Instructor declined offer
    EXPIRED = "EXPIRED"      # Offer deadline passed without response


class HiringPathwayEnum(str, Enum):
    """Hiring pathway for master instructors"""
    DIRECT = "DIRECT"              # Admin directly invites instructor
    JOB_POSTING = "JOB_POSTING"    # Admin posts job, instructor applies


class PositionStatusEnum(str, Enum):
    """Status of instructor position posting"""
    OPEN = "OPEN"
    FILLED = "FILLED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class ApplicationStatusEnum(str, Enum):
    """Status of position application"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


# ============================================================================
# Master Instructor Schemas
# ============================================================================


class MasterInstructorBase(BaseModel):


    """Base schema for master instructor"""
    location_id: int = Field(..., description="Location ID")
    instructor_id: int = Field(..., description="Instructor user ID")
    contract_start: datetime = Field(..., description="Contract start date")
    contract_end: datetime = Field(..., description="Contract end date")

    @validator('contract_end')
    def validate_contract_period(cls, v, values):
        """Ensure contract_end is after contract_start"""
        if 'contract_start' in values and v <= values['contract_start']:
            raise ValueError("Contract end date must be after start date")
        return v


class MasterInstructorCreate(MasterInstructorBase):
    """Schema for creating master instructor contract"""


class MasterInstructorUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for updating master instructor contract"""
    contract_end: Optional[datetime] = Field(None, description="New contract end date")
    is_active: Optional[bool] = Field(None, description="Active status")


class MasterInstructorResponse(MasterInstructorBase):
    """Schema for master instructor response"""
    id: int
    is_active: bool
    created_at: datetime
    terminated_at: Optional[datetime] = None

    # Offer workflow fields
    offer_status: Optional[MasterOfferStatusEnum] = None
    offered_at: Optional[datetime] = None
    offer_deadline: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None

    # Hiring pathway metadata
    hiring_pathway: HiringPathwayEnum = HiringPathwayEnum.DIRECT
    source_position_id: Optional[int] = None
    availability_override: bool = False

    # Nested data (populated by API)
    location_name: Optional[str] = None
    instructor_name: Optional[str] = None
    instructor_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Position Posting Schemas
# ============================================================================


class PositionBase(BaseModel):


    """Base schema for position posting"""
    location_id: int = Field(..., description="Location ID")
    specialization_type: str = Field(..., description="Specialization (e.g., LFA_PLAYER)")
    age_group: str = Field(..., description="Age group (PRE, YOUTH, AMATEUR, PRO)")
    year: int = Field(..., description="Year (e.g., 2026)", ge=2020, le=2100)
    time_period_start: str = Field(..., description="Start period code (M01, Q1, etc.)")
    time_period_end: str = Field(..., description="End period code (M06, Q2, etc.)")
    description: str = Field(..., min_length=10, max_length=5000, description="Job description")
    priority: int = Field(5, ge=1, le=10, description="Priority (1=low, 10=high)")
    application_deadline: datetime = Field(..., description="Application deadline")

    @validator('application_deadline')
    def validate_deadline(cls, v):
        """Ensure deadline is in the future"""
        if v <= datetime.now(v.tzinfo):
            raise ValueError("Application deadline must be in the future")
        return v


class PositionCreate(PositionBase):
    """Schema for creating position posting"""


class PositionUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for updating position posting"""
    description: Optional[str] = Field(None, min_length=10, max_length=5000)
    priority: Optional[int] = Field(None, ge=1, le=10)
    application_deadline: Optional[datetime] = None
    status: Optional[PositionStatusEnum] = None


class PositionResponse(PositionBase):
    """Schema for position posting response"""
    id: int
    posted_by: int
    status: PositionStatusEnum
    created_at: datetime
    updated_at: datetime

    # Nested data
    location_name: Optional[str] = None
    master_name: Optional[str] = None
    application_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Application Schemas
# ============================================================================


class ApplicationBase(BaseModel):


    """Base schema for position application"""
    position_id: int = Field(..., description="Position ID")
    application_message: str = Field(
        ...,
        min_length=50,
        max_length=2000,
        description="Cover letter / application message"
    )


class ApplicationCreate(ApplicationBase):
    """Schema for creating application"""


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for updating application (master reviews)"""
    status: ApplicationStatusEnum = Field(..., description="ACCEPTED or DECLINED")


class ApplicationResponse(ApplicationBase):
    """Schema for application response"""
    id: int
    applicant_id: int
    status: ApplicationStatusEnum
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    # Nested data
    applicant_name: Optional[str] = None
    applicant_email: Optional[str] = None
    position_title: Optional[str] = None  # e.g., "LFA_PLAYER/PRE M01-M06"

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Instructor Assignment Schemas
# ============================================================================


class AssignmentBase(BaseModel):


    """Base schema for instructor assignment"""
    location_id: int = Field(..., description="Location ID")
    instructor_id: int = Field(..., description="Assigned instructor ID")
    specialization_type: str = Field(..., description="Specialization")
    age_group: str = Field(..., description="Age group")
    year: int = Field(..., ge=2020, le=2100, description="Year")
    time_period_start: str = Field(..., description="Start period code")
    time_period_end: str = Field(..., description="End period code")
    is_master: bool = Field(False, description="Is this the master instructor?")


class AssignmentCreate(AssignmentBase):
    """Schema for creating instructor assignment"""


class AssignmentUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for updating instructor assignment"""
    is_active: Optional[bool] = Field(None, description="Active status")


class AssignmentResponse(AssignmentBase):
    """Schema for assignment response"""
    id: int
    assigned_by: Optional[int] = None
    is_active: bool
    created_at: datetime
    deactivated_at: Optional[datetime] = None

    # Nested data
    instructor_name: Optional[str] = None
    instructor_email: Optional[str] = None
    location_name: Optional[str] = None
    assigner_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Bulk/List Response Schemas
# ============================================================================


class MasterInstructorListResponse(BaseModel):
    """List of master instructors"""
    total: int
    masters: List[MasterInstructorResponse]


class PositionListResponse(BaseModel):
    """List of positions"""
    total: int
    positions: List[PositionResponse]


class ApplicationListResponse(BaseModel):
    """List of applications"""
    total: int
    applications: List[ApplicationResponse]


class AssignmentListResponse(BaseModel):
    """List of assignments"""
    total: int
    assignments: List[AssignmentResponse]


# ============================================================================
# Smart Matrix Integration Schemas
# ============================================================================


class CellInstructorInfo(BaseModel):
    """Instructor info for a specific matrix cell"""
    instructor_id: int
    instructor_name: str
    is_master: bool
    is_co_instructor: bool  # True if multiple instructors for same period
    period_coverage: str  # e.g., "M01-M06", "Q1-Q2"


class MatrixCellInstructors(BaseModel):
    """All instructors for a matrix cell (spec/age/year)"""
    specialization_type: str
    age_group: str
    year: int
    location_id: int
    instructors: List[CellInstructorInfo]
    total_coverage_months: int  # Total months covered by all instructors
    required_months: int  # Total months needed (12 for PRE, 12 for YOUTH, 12 for AMATEUR/PRO)
    coverage_percentage: float  # Percentage covered


# ============================================================================
# Job Board Schemas
# ============================================================================


class JobBoardPosition(BaseModel):
    """Position as shown on job board (instructor view)"""
    id: int
    location_name: str
    specialization_type: str
    age_group: str
    year: int
    period: str  # e.g., "M01-M06", "Q1-Q2"
    description: str
    priority: int
    application_deadline: datetime
    posted_by_name: str
    created_at: datetime

    # User-specific flags
    user_has_applied: bool = False
    user_application_status: Optional[ApplicationStatusEnum] = None


class JobBoardResponse(BaseModel):
    """Job board listing"""
    total: int
    positions: List[JobBoardPosition]


# ============================================================================
# Hybrid Master Hiring Schemas
# ============================================================================


class MasterDirectHireCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for creating direct hire offer (Pathway A)"""
    location_id: int = Field(..., description="Location ID")
    instructor_id: int = Field(..., description="Instructor user ID")
    contract_start: datetime = Field(..., description="Contract start date")
    contract_end: datetime = Field(..., description="Contract end date")
    offer_deadline_days: int = Field(14, ge=1, le=90, description="Days until offer expires (default 14)")
    override_availability: bool = Field(False, description="Send offer even if availability doesn't match")

    @validator('contract_end')
    def validate_contract_period(cls, v, values):
        """Ensure contract_end is after contract_start"""
        if 'contract_start' in values and v <= values['contract_start']:
            raise ValueError("Contract end date must be after start date")
        return v


class MasterOfferResponse(BaseModel):
    """Schema for master offer response (includes availability warnings)"""
    id: int
    location_id: int
    instructor_id: int
    contract_start: datetime
    contract_end: datetime
    offer_status: MasterOfferStatusEnum
    is_active: bool
    offered_at: datetime
    offer_deadline: datetime
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    hiring_pathway: HiringPathwayEnum
    availability_override: bool

    # Availability analysis
    availability_warnings: List[str] = Field(default_factory=list)
    availability_match_score: int = Field(0, ge=0, le=100, description="Percentage match (0-100)")

    # Nested data
    location_name: Optional[str] = None
    location_city: Optional[str] = None
    instructor_name: Optional[str] = None
    instructor_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MasterOfferAction(BaseModel):
    """Schema for instructor responding to offer"""
    action: Literal["ACCEPT", "DECLINE"] = Field(..., description="Accept or decline the offer")


class HireFromApplicationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for hiring from job application (Pathway B)"""
    application_id: int = Field(..., description="Application ID to accept")
    contract_start: datetime = Field(..., description="Contract start date (can adjust from posting)")
    contract_end: datetime = Field(..., description="Contract end date (can adjust from posting)")
    offer_deadline_days: int = Field(14, ge=1, le=90, description="Days until offer expires")

    @validator('contract_end')
    def validate_contract_period(cls, v, values):
        """Ensure contract_end is after contract_start"""
        if 'contract_start' in values and v <= values['contract_start']:
            raise ValueError("Contract end date must be after start date")
        return v


class MasterOpeningCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for posting master instructor opening (Pathway B)"""
    location_id: int = Field(..., description="Location ID")
    year: int = Field(..., ge=2020, le=2100, description="Year (e.g., 2026)")
    time_period_start: str = Field(..., description="Start period code (Q1, Q2, etc.)")
    time_period_end: str = Field(..., description="End period code (Q4, etc.)")
    description: str = Field(..., min_length=10, max_length=5000, description="Job description")
    application_deadline: datetime = Field(..., description="Application deadline")
    priority: int = Field(10, ge=1, le=10, description="Priority (default 10 for master positions)")
    contract_start: datetime = Field(..., description="Suggested contract start date")
    contract_end: datetime = Field(..., description="Suggested contract end date")

    @validator('application_deadline')
    def validate_deadline(cls, v):
        """Ensure deadline is in the future"""
        if v <= datetime.now(v.tzinfo):
            raise ValueError("Application deadline must be in the future")
        return v


class InstructorAvailabilityInfo(BaseModel):
    """Schema for instructor availability information"""
    instructor_id: int
    instructor_name: str
    instructor_email: str
    availability_windows: List[str] = Field(default_factory=list, description="e.g., ['Q1', 'Q2', 'Q3']")
    match_score: int = Field(0, ge=0, le=100, description="Percentage match with requested period")
    current_master_locations: List[str] = Field(default_factory=list, description="Locations where already master")


class AvailabilityCheckResult(BaseModel):
    """Result of availability validation"""
    match_score: int = Field(..., ge=0, le=100, description="Percentage match (0-100)")
    warnings: List[str] = Field(default_factory=list)
    instructor_availability: List[str] = Field(default_factory=list, description="Instructor's available periods")
    contract_coverage: List[str] = Field(default_factory=list, description="Periods covered by contract")
