from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from ..models.booking import BookingStatus
from .user import User
from .session import Session


class BookingBase(BaseModel):
    session_id: int
    notes: Optional[str] = None


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[BookingStatus] = None


class Booking(BookingBase):
    id: int
    user_id: int
    status: BookingStatus
    waitlist_position: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BookingWithRelations(Booking):
    user: User
    session: Session
    attended: Optional[bool] = None  # Whether the user attended this session


class BookingList(BaseModel):
    bookings: List[BookingWithRelations]
    total: int
    page: int
    size: int


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
    notes: Optional[str] = None


class BookingConfirm(BaseModel):
    notes: Optional[str] = None


class BookingCancel(BaseModel):
    reason: Optional[str] = None