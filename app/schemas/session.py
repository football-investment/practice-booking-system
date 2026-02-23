from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator
from typing import Optional, List, Union
from datetime import datetime
from ..models.session import SessionType
from .user import User
from .semester import Semester
from .group import Group


class SessionBase(BaseModel):
    title: str
    description: Optional[str] = None
    date_start: datetime
    date_end: datetime
    session_type: SessionType = SessionType.on_site
    capacity: int = 20
    location: Optional[str] = None
    meeting_link: Optional[Union[HttpUrl, str]] = None  # 🔒 URL validation for virtual sessions
    sport_type: Optional[str] = 'General'  # Enhanced field for UI
    level: Optional[str] = 'All Levels'  # Enhanced field for UI
    instructor_name: Optional[str] = None  # Enhanced field for UI
    semester_id: int
    group_id: Optional[int] = None  # FIXED: Made optional to allow null values
    instructor_id: Optional[int] = None
    campus_id: Optional[int] = None  # 🏟️ Multi-campus support (for tournament session distribution)
    credit_cost: int = 1  # Number of credits required to book this session
    is_tournament_game: bool = False  # 🏆 Tournament game flag
    game_type: Optional[str] = None  # Tournament game type (e.g., "Group Stage", "Semifinal", "Final")

    @field_validator('meeting_link', mode='before')
    @classmethod
    def validate_meeting_link(cls, v, info):
        """
        Validate meeting_link URL format
        - Allow None (for non-virtual sessions)
        - Allow empty string (converts to None)
        - Validate URL format if provided
        """
        if v is None or v == '':
            return None

        # If it's already a valid URL string, return it
        if isinstance(v, str):
            # Basic URL validation: must start with http:// or https://
            if not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError('Meeting link must be a valid URL starting with http:// or https://')

        return v


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    session_type: Optional[SessionType] = None
    capacity: Optional[int] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    sport_type: Optional[str] = None  # Enhanced field for UI
    level: Optional[str] = None  # Enhanced field for UI
    instructor_name: Optional[str] = None  # Enhanced field for UI
    semester_id: Optional[int] = None
    group_id: Optional[int] = None
    instructor_id: Optional[int] = None
    campus_id: Optional[int] = None  # 🏟️ Multi-campus support (for tournament session distribution)
    credit_cost: Optional[int] = None  # Number of credits required to book this session
    is_tournament_game: Optional[bool] = None  # 🏆 Tournament game flag
    game_type: Optional[str] = None  # Tournament game type (e.g., "Group Stage", "Semifinal", "Final")


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