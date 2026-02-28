from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from ..models.attendance import AttendanceStatus
from .user import User
from .session import Session
from .booking import Booking


class AttendanceBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    user_id: int
    session_id: int
    booking_id: Optional[int] = None  # Optional for tournament sessions
    status: AttendanceStatus = AttendanceStatus.present
    notes: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: Optional[AttendanceStatus] = None
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    notes: Optional[str] = None


class Attendance(AttendanceBase):
    id: int
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    marked_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AttendanceWithRelations(Attendance):
    user: User
    session: Session
    booking: Optional[Booking] = None  # Optional for tournament sessions
    marker: Optional[User] = None


class AttendanceList(BaseModel):
    attendances: List[AttendanceWithRelations]
    total: int


class AttendanceCheckIn(BaseModel):
    notes: Optional[str] = None


class AttendanceBulkUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    attendances: List[dict]  # List of {booking_id: int, status: AttendanceStatus, notes: Optional[str]}