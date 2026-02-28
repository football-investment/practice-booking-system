from pydantic import BaseModel, ConfigDict, Field
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
    model_config = ConfigDict(extra='forbid')

    title: str = Field(..., max_length=200, description="Milestone title")
    description: Optional[str] = Field(None, max_length=2000, description="Optional milestone description")
    order_index: int = Field(..., ge=0, le=100, description="Milestone order index (0-100)")
    required_sessions: int = Field(2, ge=1, le=50, description="Required sessions to complete milestone (1-50)")
    xp_reward: int = Field(25, ge=0, le=10000, description="XP reward for milestone completion (0-10000)")
    deadline: Optional[date] = Field(None, description="Optional milestone deadline")
    is_required: bool = Field(True, description="Whether milestone is required for project completion")


class ProjectMilestoneCreate(ProjectMilestoneBase):
    pass


class ProjectMilestoneUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: Optional[str] = Field(None, max_length=200, description="Milestone title")
    description: Optional[str] = Field(None, max_length=2000, description="Optional milestone description")
    order_index: Optional[int] = Field(None, ge=0, le=100, description="Milestone order index (0-100)")
    required_sessions: Optional[int] = Field(None, ge=1, le=50, description="Required sessions (1-50)")
    xp_reward: Optional[int] = Field(None, ge=0, le=10000, description="XP reward (0-10000)")
    deadline: Optional[date] = Field(None, description="Optional milestone deadline")
    is_required: Optional[bool] = Field(None, description="Whether milestone is required")


class ProjectMilestone(ProjectMilestoneBase):
    id: int
    project_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Project Base Schemas
class ProjectBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: str = Field(..., max_length=200, description="Project title")
    description: Optional[str] = Field(None, max_length=5000, description="Optional project description")
    max_participants: int = Field(10, ge=1, le=1000, description="Maximum participants (1-1000)")
    required_sessions: int = Field(8, ge=1, le=100, description="Required sessions to complete project (1-100)")
    xp_reward: int = Field(200, ge=0, le=100000, description="XP reward for project completion (0-100000)")
    deadline: Optional[date] = Field(None, description="Optional project deadline")


class ProjectCreate(ProjectBase):
    semester_id: int = Field(..., ge=1, description="Semester ID (must be positive)")
    instructor_id: Optional[int] = Field(None, ge=1, description="Optional instructor ID (must be positive)")
    milestones: Optional[List[ProjectMilestoneCreate]] = Field([], description="Optional list of project milestones")


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: Optional[str] = Field(None, max_length=200, description="Project title")
    description: Optional[str] = Field(None, max_length=5000, description="Optional project description")
    max_participants: Optional[int] = Field(None, ge=1, le=1000, description="Maximum participants (1-1000)")
    required_sessions: Optional[int] = Field(None, ge=1, le=100, description="Required sessions (1-100)")
    xp_reward: Optional[int] = Field(None, ge=0, le=100000, description="XP reward (0-100000)")
    deadline: Optional[date] = Field(None, description="Optional project deadline")
    status: Optional[ProjectStatusEnum] = Field(None, description="Project status")


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

    model_config = ConfigDict(from_attributes=True)


class ProjectWithDetails(Project):
    milestones: List[ProjectMilestone] = []
    instructor: Optional[Dict[str, Any]] = None
    semester: Optional[Dict[str, Any]] = None


# Project Enrollment Schemas
class ProjectEnrollmentBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    project_id: int = Field(..., ge=1, description="Project ID (must be positive)")


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

    model_config = ConfigDict(from_attributes=True)


class ProjectEnrollmentWithDetails(ProjectEnrollment):
    project: Project
    user: Optional[Dict[str, Any]] = None
    milestone_progress: List[Dict[str, Any]] = []


# Milestone Progress Schemas
class MilestoneProgressBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    enrollment_id: int = Field(..., ge=1, description="Enrollment ID (must be positive)")
    milestone_id: int = Field(..., ge=1, description="Milestone ID (must be positive)")


class MilestoneProgressUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: Optional[MilestoneStatusEnum] = Field(None, description="Milestone status")
    instructor_feedback: Optional[str] = Field(None, max_length=2000, description="Optional instructor feedback")
    sessions_completed: Optional[int] = Field(None, ge=0, le=100, description="Sessions completed (0-100)")


class MilestoneProgress(MilestoneProgressBase):
    id: int
    status: str
    submitted_at: Optional[datetime] = None
    instructor_feedback: Optional[str] = None
    instructor_approved_at: Optional[datetime] = None
    sessions_completed: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MilestoneProgressWithDetails(MilestoneProgress):
    milestone: ProjectMilestone
    enrollment: ProjectEnrollment


# Project Session Connection Schemas
class ProjectSessionBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    project_id: int = Field(..., ge=1, description="Project ID (must be positive)")
    session_id: int = Field(..., ge=1, description="Session ID (must be positive)")
    milestone_id: Optional[int] = Field(None, ge=1, description="Optional milestone ID (must be positive)")
    is_required: bool = Field(False, description="Whether session is required for project completion")


class ProjectSessionCreate(ProjectSessionBase):
    pass


class ProjectSession(ProjectSessionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    model_config = ConfigDict(extra='forbid')

    project_id: int = Field(..., ge=1, description="Project ID (must be positive)")
    quiz_id: int = Field(..., ge=1, description="Quiz ID (must be positive)")
    milestone_id: Optional[int] = Field(None, ge=1, description="Optional milestone ID (must be positive)")
    quiz_type: str = Field("milestone", description="Quiz type: 'enrollment' or 'milestone'")
    is_required: bool = Field(True, description="Whether quiz is required")
    minimum_score: float = Field(75.0, ge=0.0, le=100.0, description="Minimum passing score (0-100)")
    order_index: int = Field(0, ge=0, le=100, description="Quiz order index (0-100)")
    is_active: bool = Field(True, description="Whether quiz is active")


class ProjectQuizCreate(ProjectQuizBase):
    pass


class ProjectQuizUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    milestone_id: Optional[int] = Field(None, ge=1, description="Optional milestone ID (must be positive)")
    quiz_type: Optional[str] = Field(None, description="Quiz type: 'enrollment' or 'milestone'")
    is_required: Optional[bool] = Field(None, description="Whether quiz is required")
    minimum_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Minimum passing score (0-100)")
    order_index: Optional[int] = Field(None, ge=0, le=100, description="Quiz order index (0-100)")
    is_active: Optional[bool] = Field(None, description="Whether quiz is active")


class ProjectQuiz(ProjectQuizBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProjectQuizWithDetails(ProjectQuiz):
    quiz: Optional[Dict[str, Any]] = None  # Quiz részletek
    milestone: Optional[ProjectMilestone] = None


# Enrollment Quiz Results
class ProjectEnrollmentQuizBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    project_id: int = Field(..., ge=1, description="Project ID (must be positive)")
    user_id: int = Field(..., ge=1, description="User ID (must be positive)")
    quiz_attempt_id: int = Field(..., ge=1, description="Quiz attempt ID (must be positive)")


class ProjectEnrollmentQuizCreate(ProjectEnrollmentQuizBase):
    enrollment_priority: Optional[int] = Field(None, ge=1, le=1000, description="Optional enrollment priority (1-1000)")
    enrollment_confirmed: bool = Field(False, description="Whether enrollment is confirmed")


class ProjectEnrollmentQuiz(ProjectEnrollmentQuizBase):
    id: int
    enrollment_priority: Optional[int] = None
    enrollment_confirmed: bool = False
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProjectEnrollmentQuizWithDetails(ProjectEnrollmentQuiz):
    quiz_attempt: Optional[Dict[str, Any]] = None
    user: Optional[Dict[str, Any]] = None


# Extended Project Schema with Quizzes
class ProjectWithQuizzes(ProjectWithDetails):
    project_quizzes: List[ProjectQuizWithDetails] = []
    enrollment_quiz: Optional[ProjectQuizWithDetails] = None


# Quiz Configuration for Instructors
class ProjectQuizConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')

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