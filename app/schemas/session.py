from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from ..models.session import SessionMode
from .user import User
from .semester import Semester
from .group import Group


class SessionBase(BaseModel):
    title: str
    description: Optional[str] = None
    date_start: datetime
    date_end: datetime
    mode: SessionMode = SessionMode.OFFLINE
    capacity: int = 20
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    sport_type: Optional[str] = 'General'  # Enhanced field for UI
    level: Optional[str] = 'All Levels'  # Enhanced field for UI
    instructor_name: Optional[str] = None  # Enhanced field for UI
    semester_id: int
    group_id: Optional[int] = None  # FIXED: Made optional to allow null values
    instructor_id: Optional[int] = None


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    mode: Optional[SessionMode] = None
    capacity: Optional[int] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    sport_type: Optional[str] = None  # Enhanced field for UI
    level: Optional[str] = None  # Enhanced field for UI
    instructor_name: Optional[str] = None  # Enhanced field for UI
    semester_id: Optional[int] = None
    group_id: Optional[int] = None
    instructor_id: Optional[int] = None


class Session(SessionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SessionWithRelations(Session):
    semester: Semester
    group: Optional[Group] = None  # FIXED: Made optional since group_id can be None
    instructor: Optional[User] = None


class SessionWithStats(Session):
    semester: Semester
    group: Optional[Group] = None  # FIXED: Made optional since group_id can be None
    instructor: Optional[User] = None
    booking_count: int
    confirmed_bookings: int
    current_bookings: int  # FIXED: Added for frontend compatibility (mapped from confirmed_bookings)
    waitlist_count: int
    attendance_count: int
    average_rating: Optional[float] = None


class SessionList(BaseModel):
    sessions: List[SessionWithStats]
    total: int
    page: int
    size: int