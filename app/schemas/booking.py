from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from ..models.booking import BookingStatus
from ..models.session import SessionType


class BookingBase(BaseModel):


    session_id: int = Field(..., ge=1, description="Session ID (must be positive)")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional booking notes")


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    notes: Optional[str] = Field(None, max_length=1000, description="Optional booking notes")
    status: Optional[BookingStatus] = None


class Booking(BookingBase):
    id: int
    user_id: int
    status: BookingStatus
    waitlist_position: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    attended_status: Optional[str] = None  # Attendance status field from database

    model_config = ConfigDict(from_attributes=True)


# Simplified schemas to avoid circular dependencies
class BookingUserSimple(BaseModel):
    """Simplified user schema for booking responses - avoids circular imports"""
    id: int
    name: str
    nickname: Optional[str] = None
    email: str
    role: str
    specialization: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BookingSessionSimple(BaseModel):
    """Simplified session schema for booking responses - avoids circular imports"""
    id: int
    title: str
    description: Optional[str] = None
    date_start: datetime
    date_end: datetime
    session_type: SessionType
    capacity: int
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    sport_type: Optional[str] = None
    level: Optional[str] = None
    instructor_name: Optional[str] = None
    semester_id: int

    model_config = ConfigDict(from_attributes=True)


class BookingWithRelations(Booking):
    user: BookingUserSimple
    session: BookingSessionSimple
    attended: Optional[bool] = None  # Whether the user attended this session


class BookingList(BaseModel):
    bookings: List[BookingWithRelations]
    total: int
    page: int
    size: int


class BookingStatusUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: BookingStatus
    notes: Optional[str] = Field(None, max_length=1000, description="Optional status update notes")


class BookingConfirm(BaseModel):
    model_config = ConfigDict(extra='forbid')

    notes: Optional[str] = Field(None, max_length=1000, description="Optional confirmation notes")


class BookingCancel(BaseModel):
    model_config = ConfigDict(extra='forbid')

    reason: Optional[str] = Field(None, max_length=1000, description="Optional cancellation reason")