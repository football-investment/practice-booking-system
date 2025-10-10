"""
Track-related Pydantic schemas
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


# Base Track Schemas
class TrackBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    duration_semesters: int = 1
    is_active: bool = True


class TrackCreate(TrackBase):
    prerequisites: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TrackUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_semesters: Optional[int] = None
    is_active: Optional[bool] = None
    prerequisites: Optional[Dict[str, Any]] = None


class TrackResponse(TrackBase):
    id: UUID
    total_modules: int = 0
    mandatory_modules: int = 0
    prerequisites: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


# Module Schemas
class ModuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    order_in_track: int = 0
    estimated_hours: int = 0
    is_mandatory: bool = True


class ModuleCreate(ModuleBase):
    track_id: UUID
    semester_id: Optional[UUID] = None
    learning_objectives: Optional[List[str]] = Field(default_factory=list)


class ModuleResponse(ModuleBase):
    id: UUID
    track_id: UUID
    semester_id: Optional[UUID] = None
    learning_objectives: List[str] = Field(default_factory=list)
    total_components: int = 0
    mandatory_components: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# Module Component Schemas
class ModuleComponentBase(BaseModel):
    type: str  # 'theory', 'quiz', 'project', 'assignment', 'video'
    name: str
    description: Optional[str] = None
    order_in_module: int = 0
    estimated_minutes: int = 0
    is_mandatory: bool = True


class ModuleComponentCreate(ModuleComponentBase):
    module_id: UUID
    component_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ModuleComponentResponse(ModuleComponentBase):
    id: UUID
    module_id: UUID
    component_data: Dict[str, Any] = Field(default_factory=dict)
    estimated_hours: float = 0
    created_at: datetime

    class Config:
        from_attributes = True


# Track Progress Schemas
class UserTrackProgressBase(BaseModel):
    status: str
    completion_percentage: float = 0.0
    current_semester: int = 1


class UserTrackProgressResponse(UserTrackProgressBase):
    track_progress_id: UUID
    track: TrackResponse
    enrollment_date: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    certificate_id: Optional[UUID] = None

    class Config:
        from_attributes = True


# Module Progress Schemas
class UserModuleProgressResponse(BaseModel):
    module_progress_id: UUID
    module: ModuleResponse
    status: str
    grade: Optional[float] = None
    attempts: int = 0
    time_spent_minutes: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Track Enrollment Schemas
class TrackEnrollmentRequest(BaseModel):
    track_id: UUID
    semester_id: UUID


class TrackEnrollmentResponse(BaseModel):
    success: bool
    message: str
    track_progress_id: Optional[UUID] = None


# Analytics Schemas
class TrackAnalyticsResponse(BaseModel):
    track_id: UUID
    total_enrollments: int
    active_enrollments: int
    completions: int
    completion_rate: float
    average_completion_days: float


# Detailed Progress Schema
class DetailedTrackProgressResponse(BaseModel):
    track_progress_id: UUID
    track: TrackResponse
    status: str
    completion_percentage: float
    enrollment_date: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    certificate_id: Optional[UUID] = None
    module_progresses: List[UserModuleProgressResponse]

    class Config:
        from_attributes = True