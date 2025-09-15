from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from ..models.attendance import AttendanceStatus
from .user import User
from .session import Session
from .booking import Booking


class AttendanceBase(BaseModel):
    user_id: int
    session_id: int
    booking_id: int
    status: AttendanceStatus = AttendanceStatus.PRESENT
    notes: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
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
    booking: Booking
    marker: Optional[User] = None


class AttendanceList(BaseModel):
    attendances: List[AttendanceWithRelations]
    total: int


class AttendanceCheckIn(BaseModel):
    notes: Optional[str] = None


class AttendanceBulkUpdate(BaseModel):
    attendances: List[dict]  # List of {booking_id: int, status: AttendanceStatus, notes: Optional[str]}