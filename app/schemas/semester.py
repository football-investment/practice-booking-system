from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date


class SemesterBase(BaseModel):
    code: str
    name: str
    start_date: date
    end_date: date
    is_active: bool = True


class SemesterCreate(SemesterBase):
    pass


class SemesterUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class Semester(SemesterBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SemesterWithStats(Semester):
    total_groups: int
    total_sessions: int
    total_bookings: int
    active_users: int


class SemesterList(BaseModel):
    semesters: List[SemesterWithStats]
    total: int