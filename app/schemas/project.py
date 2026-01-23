from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum


# Enums for API
class ProjectStatusEnum(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"


class ProjectEnrollmentStatusEnum(str, Enum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    COMPLETED = "completed"


class ProjectProgressStatusEnum(str, Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"


class MilestoneStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


# Base schemas
class ProjectMilestoneBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    order_index: int
    required_sessions: int = 2
    xp_reward: int = 25
    deadline: Optional[date] = None
    is_required: bool = True


class ProjectMilestoneCreate(ProjectMilestoneBase):
    pass


class ProjectMilestoneUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    order_index: Optional[int] = None
    required_sessions: Optional[int] = None
    xp_reward: Optional[int] = None
    deadline: Optional[date] = None
    is_required: Optional[bool] = None


class ProjectMilestone(ProjectMilestoneBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Project Base Schemas
class ProjectBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    max_participants: int = 10
    required_sessions: int = 8
    xp_reward: int = 200
    deadline: Optional[date] = None


class ProjectCreate(ProjectBase):
    semester_id: int
    instructor_id: Optional[int] = None
    milestones: Optional[List[ProjectMilestoneCreate]] = []


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    max_participants: Optional[int] = None
    required_sessions: Optional[int] = None
    xp_reward: Optional[int] = None
    deadline: Optional[date] = None
    status: Optional[ProjectStatusEnum] = None


class Project(ProjectBase):
    id: int
    semester_id: int
    instructor_id: Optional[int] = None
    status: str
    difficulty: Optional[str] = None
    has_enrollment_quiz: Optional[bool] = None
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    enrolled_count: Optional[int] = None
    available_spots: Optional[int] = None
    
    # Optional semester details for enrollment validation
    semester: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ProjectWithDetails(Project):
    milestones: List[ProjectMilestone] = []
    instructor: Optional[Dict[str, Any]] = None
    semester: Optional[Dict[str, Any]] = None


# Project Enrollment Schemas
class ProjectEnrollmentBase(BaseModel):
    project_id: int


class ProjectEnrollmentCreate(ProjectEnrollmentBase):
    pass


class ProjectEnrollment(ProjectEnrollmentBase):
    id: int
    user_id: int
    enrolled_at: datetime
    status: str
    progress_status: str
    completion_percentage: float = 0.0
    instructor_approved: bool = False
    final_grade: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    # Computed fields
    sessions_completed: Optional[int] = None
    sessions_required: Optional[int] = None

    class Config:
        from_attributes = True


class ProjectEnrollmentWithDetails(ProjectEnrollment):
    project: Project
    user: Optional[Dict[str, Any]] = None
    milestone_progress: List[Dict[str, Any]] = []


# Milestone Progress Schemas
class MilestoneProgressBase(BaseModel):
    enrollment_id: int
    milestone_id: int


class MilestoneProgressUpdate(BaseModel):
    status: Optional[MilestoneStatusEnum] = None
    instructor_feedback: Optional[str] = None
    sessions_completed: Optional[int] = None


class MilestoneProgress(MilestoneProgressBase):
    id: int
    status: str
    submitted_at: Optional[datetime] = None
    instructor_feedback: Optional[str] = None
    instructor_approved_at: Optional[datetime] = None
    sessions_completed: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MilestoneProgressWithDetails(MilestoneProgress):
    milestone: ProjectMilestone
    enrollment: ProjectEnrollment


# Project Session Connection Schemas
class ProjectSessionBase(BaseModel):
    project_id: int
    session_id: int
    milestone_id: Optional[int] = None
    is_required: bool = False


class ProjectSessionCreate(ProjectSessionBase):
    pass


class ProjectSession(ProjectSessionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Response schemas for lists
class ProjectList(BaseModel):
    projects: List[Project]
    total: int
    page: int
    size: int


class ProjectEnrollmentList(BaseModel):
    enrollments: List[ProjectEnrollment]
    total: int
    page: int
    size: int


# Student Dashboard Integration
class StudentProjectSummary(BaseModel):
    """Summary for student dashboard"""
    current_project: Optional[ProjectEnrollmentWithDetails] = None
    available_projects: List[Project] = []
    total_projects_completed: int = 0
    total_xp_from_projects: int = 0


# Instructor Dashboard Integration  
class InstructorProjectSummary(BaseModel):
    """Summary for instructor dashboard"""
    managed_projects: List[ProjectWithDetails] = []
    total_students_enrolled: int = 0
    pending_reviews: int = 0
    completed_projects: int = 0


# Progress tracking
class ProjectProgressResponse(BaseModel):
    """Detailed progress response for students"""
    enrollment: ProjectEnrollmentWithDetails
    milestone_progress: List[MilestoneProgressWithDetails]
    overall_progress: float
    next_milestone: Optional[ProjectMilestone] = None
    sessions_remaining: int
    estimated_completion: Optional[date] = None


# Project-Quiz Connection Schemas
class ProjectQuizBase(BaseModel):
    project_id: int
    quiz_id: int
    milestone_id: Optional[int] = None
    quiz_type: str = "milestone"  # "enrollment" vagy "milestone"
    is_required: bool = True
    minimum_score: float = 75.0
    order_index: int = 0
    is_active: bool = True


class ProjectQuizCreate(ProjectQuizBase):
    pass


class ProjectQuizUpdate(BaseModel):
    milestone_id: Optional[int] = None
    quiz_type: Optional[str] = None
    is_required: Optional[bool] = None
    minimum_score: Optional[float] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class ProjectQuiz(ProjectQuizBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProjectQuizWithDetails(ProjectQuiz):
    quiz: Optional[Dict[str, Any]] = None  # Quiz részletek
    milestone: Optional[ProjectMilestone] = None


# Enrollment Quiz Results
class ProjectEnrollmentQuizBase(BaseModel):
    project_id: int
    user_id: int
    quiz_attempt_id: int


class ProjectEnrollmentQuizCreate(ProjectEnrollmentQuizBase):
    enrollment_priority: Optional[int] = None
    enrollment_confirmed: bool = False


class ProjectEnrollmentQuiz(ProjectEnrollmentQuizBase):
    id: int
    enrollment_priority: Optional[int] = None
    enrollment_confirmed: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProjectEnrollmentQuizWithDetails(ProjectEnrollmentQuiz):
    quiz_attempt: Optional[Dict[str, Any]] = None
    user: Optional[Dict[str, Any]] = None


# Extended Project Schema with Quizzes
class ProjectWithQuizzes(ProjectWithDetails):
    project_quizzes: List[ProjectQuizWithDetails] = []
    enrollment_quiz: Optional[ProjectQuizWithDetails] = None


# Quiz Configuration for Instructors
class ProjectQuizConfig(BaseModel):
    """Konfigurációs adatok instruktoroknak"""
    project_id: int
    enrollment_quiz_id: Optional[int] = None
    milestone_quizzes: List[ProjectQuizCreate] = []
    quiz_settings: Dict[str, Any] = {}  # További beállítások


# Enrollment Priority Response
class EnrollmentPriorityResponse(BaseModel):
    """Rangsorolási információk"""
    user_id: int
    project_id: int
    quiz_score: float
    enrollment_priority: int
    total_applicants: int
    is_eligible: bool
    can_confirm: bool