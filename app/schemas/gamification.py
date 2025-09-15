from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class Achievement(BaseModel):
    id: int
    title: str
    description: str
    icon: str
    badge_type: str
    earned_at: str
    semester_count: Optional[int] = None

    class Config:
        from_attributes = True


class UserStats(BaseModel):
    semesters_participated: int
    total_bookings: int
    total_attended: int
    attendance_rate: float
    feedback_given: int
    total_xp: int
    level: int
    first_semester_date: Optional[str] = None

    class Config:
        from_attributes = True


class StudentStatus(BaseModel):
    title: str
    icon: str
    is_returning: bool

    class Config:
        from_attributes = True


class NextLevel(BaseModel):
    current_xp: int
    next_level_xp: int
    progress_percentage: float

    class Config:
        from_attributes = True


class SemesterInfo(BaseModel):
    id: int
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    class Config:
        from_attributes = True


class UserGamificationResponse(BaseModel):
    stats: UserStats
    achievements: List[Achievement]
    status: StudentStatus
    next_level: NextLevel
    semesters: List[SemesterInfo] = []
    current_semester: Optional[SemesterInfo] = None

    class Config:
        from_attributes = True