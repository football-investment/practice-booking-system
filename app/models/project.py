from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Date, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from typing import Optional

from ..database import Base
from .specialization import SpecializationType


class ProjectStatus(enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"


class ProjectDifficulty(enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate" 
    ADVANCED = "advanced"


class ProjectEnrollmentStatus(enum.Enum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn" 
    COMPLETED = "completed"
    NOT_ELIGIBLE = "not_eligible"


class ProjectProgressStatus(enum.Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"


class MilestoneStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    max_participants = Column(Integer, default=10)
    required_sessions = Column(Integer, default=8)
    xp_reward = Column(Integer, default=200)
    deadline = Column(Date, nullable=True)
    status = Column(String(20), default=ProjectStatus.ACTIVE.value)
    difficulty = Column(String(20), default=ProjectDifficulty.INTERMEDIATE.value)
    
    # 🎓 NEW: Specialization fields
    target_specialization = Column(
        Enum(SpecializationType),
        nullable=True,
        comment="Target specialization for this project (null = all specializations)"
    )
    
    mixed_specialization = Column(
        Boolean,
        default=False,
        comment="Whether this project encourages collaboration between Player and Coach specializations"
    )
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    semester = relationship("Semester", back_populates="projects")
    instructor = relationship("User", back_populates="instructed_projects")
    enrollments = relationship("ProjectEnrollment", back_populates="project")
    milestones = relationship("ProjectMilestone", back_populates="project", order_by="ProjectMilestone.order_index")
    project_sessions = relationship("ProjectSession", back_populates="project")
    project_quizzes = relationship("ProjectQuiz", back_populates="project")

    @property
    def enrolled_count(self):
        return len([e for e in self.enrollments if e.status == ProjectEnrollmentStatus.ACTIVE.value])

    @property
    def available_spots(self):
        return max(0, self.max_participants - self.enrolled_count)
    
    @property
    def has_enrollment_quiz(self):
        """Check if project has an enrollment quiz"""
        return any(pq.quiz_type == "enrollment" and pq.is_active for pq in self.project_quizzes)
    
    # 🎓 NEW: Specialization helper properties
    @property
    def specialization_info(self) -> str:
        """Get user-friendly specialization information (HYBRID: loads from JSON)"""
        if self.mixed_specialization:
            return "Vegyes (Player + Coach)"
        elif self.target_specialization:
            from app.services.specialization_config_loader import SpecializationConfigLoader
            loader = SpecializationConfigLoader()
            try:
                display_info = loader.get_display_info(self.target_specialization)
                return display_info.get('name', str(self.target_specialization.value))
            except Exception:
                return str(self.target_specialization.value)
        return "Minden szakirány"
    
    @property
    def is_open_enrollment(self) -> bool:
        """Check if project has open enrollment for all specializations"""
        return self.mixed_specialization or self.target_specialization is None


class ProjectEnrollment(Base):
    __tablename__ = "project_enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    enrolled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), default=ProjectEnrollmentStatus.ACTIVE.value)
    progress_status = Column(String(20), default=ProjectProgressStatus.PLANNING.value)
    completion_percentage = Column(Float, default=0.0)
    instructor_approved = Column(Boolean, default=False)
    instructor_feedback = Column(Text, nullable=True)  # Instructor feedback for enrollment
    enrollment_status = Column(String(20), default='pending')  # pending, approved, rejected, waitlisted
    quiz_passed = Column(Boolean, default=False)  # Whether enrollment quiz was passed
    final_grade = Column(String(5), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="enrollments")
    user = relationship("User", back_populates="project_enrollments")
    milestone_progress = relationship("ProjectMilestoneProgress", back_populates="enrollment")
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('project_id', 'user_id', name='unique_project_user'),)

    @property
    def sessions_completed(self):
        return sum(mp.sessions_completed for mp in self.milestone_progress)

    @property
    def sessions_required(self):
        return self.project.required_sessions


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False)
    required_sessions = Column(Integer, default=2)
    xp_reward = Column(Integer, default=25)
    deadline = Column(Date, nullable=True)
    is_required = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project = relationship("Project", back_populates="milestones")
    milestone_progress = relationship("ProjectMilestoneProgress", back_populates="milestone")
    milestone_quizzes = relationship("ProjectQuiz", back_populates="milestone")


class ProjectMilestoneProgress(Base):
    __tablename__ = "project_milestone_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("project_enrollments.id"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("project_milestones.id"), nullable=False)
    status = Column(String(20), default=MilestoneStatus.PENDING.value)
    submitted_at = Column(DateTime, nullable=True)
    instructor_feedback = Column(Text, nullable=True)
    instructor_approved_at = Column(DateTime, nullable=True)
    sessions_completed = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    enrollment = relationship("ProjectEnrollment", back_populates="milestone_progress")
    milestone = relationship("ProjectMilestone", back_populates="milestone_progress")
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('enrollment_id', 'milestone_id', name='unique_enrollment_milestone'),)


class ProjectSession(Base):
    __tablename__ = "project_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("project_milestones.id"), nullable=True)
    is_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project = relationship("Project", back_populates="project_sessions")
    session = relationship("Session", back_populates="project_sessions")
    milestone = relationship("ProjectMilestone")
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('project_id', 'session_id', name='unique_project_session'),)


class ProjectQuiz(Base):
    """Kapcsolótábla a projektek és quizek között"""
    __tablename__ = "project_quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("project_milestones.id"), nullable=True)  # melyik mérföldkőhöz tartozik
    quiz_type = Column(String(50), nullable=False, default="milestone")  # "enrollment" vagy "milestone"
    is_required = Column(Boolean, default=True)
    minimum_score = Column(Float, default=75.0)  # minimum százalékos teljesítmény
    order_index = Column(Integer, default=0)  # sorrendiség a projektben
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project = relationship("Project", back_populates="project_quizzes")
    quiz = relationship("Quiz")  # Quiz modell más fájlban van
    milestone = relationship("ProjectMilestone", back_populates="milestone_quizzes")
    
    # Unique constraint - egy milestonehoz/projekthez csak egy quiz egy típusból
    __table_args__ = (UniqueConstraint('project_id', 'quiz_id', 'quiz_type', name='unique_project_quiz_type'),)


class ProjectEnrollmentQuiz(Base):
    """Nyilvántartás a projekt jelentkezési quizek eredményeiről"""
    __tablename__ = "project_enrollment_quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False)
    enrollment_priority = Column(Integer, nullable=True)  # rangsor pozíció
    enrollment_confirmed = Column(Boolean, default=False)  # megerősítette-e a jelentkezést
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project = relationship("Project")
    user = relationship("User")
    quiz_attempt = relationship("QuizAttempt")
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('project_id', 'user_id', name='unique_project_user_enrollment_quiz'),)