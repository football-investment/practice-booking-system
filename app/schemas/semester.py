from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from ..models.semester import SemesterStatus


class SemesterBase(BaseModel):
    code: str
    name: str
    start_date: date
    end_date: date
    status: SemesterStatus = SemesterStatus.DRAFT
    is_active: bool = True
    enrollment_cost: int = 500
    master_instructor_id: Optional[int] = None
    specialization_type: Optional[str] = None
    age_group: Optional[str] = None
    theme: Optional[str] = None
    focus_description: Optional[str] = None
    location_city: Optional[str] = None
    location_venue: Optional[str] = None
    location_address: Optional[str] = None


class SemesterCreate(SemesterBase):
    pass


class SemesterUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[SemesterStatus] = None
    is_active: Optional[bool] = None
    enrollment_cost: Optional[int] = None
    master_instructor_id: Optional[int] = None


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
    location_type: Optional[str] = None  # PARTNER or CENTER from location relationship


class SemesterList(BaseModel):
    semesters: List[SemesterWithStats]
    total: int