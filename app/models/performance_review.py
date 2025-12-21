"""
Performance Review Models for On-Site Sessions

Two-way evaluation system:
1. Instructor evaluates Student performance (soft skills)
2. Student evaluates Instructor and Session quality
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database import Base


class StudentPerformanceReview(Base):
    """
    Instructor evaluates Student performance on On-Site sessions

    Focus: Soft skills and work attitude
    Categories: Punctuality, Engagement, Focus, Collaboration, Attitude
    Scale: 1-5 (1=Poor, 2=Below Average, 3=Average, 4=Good, 5=Excellent)
    """
    __tablename__ = "student_performance_reviews"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 5 Soft Skill Categories (1-5 scale)
    punctuality = Column(Integer, nullable=False)  # Was student on time?
    engagement = Column(Integer, nullable=False)   # Active participation?
    focus = Column(Integer, nullable=False)        # Concentration level?
    collaboration = Column(Integer, nullable=False) # Teamwork quality?
    attitude = Column(Integer, nullable=False)     # General attitude?

    # Text feedback
    comments = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("Session", back_populates="student_reviews")
    student = relationship("User", foreign_keys=[student_id])
    instructor = relationship("User", foreign_keys=[instructor_id])

    # Constraints
    __table_args__ = (
        CheckConstraint('punctuality BETWEEN 1 AND 5', name='check_punctuality_range'),
        CheckConstraint('engagement BETWEEN 1 AND 5', name='check_engagement_range'),
        CheckConstraint('focus BETWEEN 1 AND 5', name='check_focus_range'),
        CheckConstraint('collaboration BETWEEN 1 AND 5', name='check_collaboration_range'),
        CheckConstraint('attitude BETWEEN 1 AND 5', name='check_attitude_range'),
    )

    @property
    def average_score(self) -> float:
        """Calculate average score across all categories"""
        return (self.punctuality + self.engagement + self.focus +
                self.collaboration + self.attitude) / 5

    @property
    def score_breakdown(self) -> dict:
        """Get detailed breakdown of scores"""
        return {
            'punctuality': self.punctuality,
            'engagement': self.engagement,
            'focus': self.focus,
            'collaboration': self.collaboration,
            'attitude': self.attitude,
            'average': self.average_score
        }


class InstructorSessionReview(Base):
    """
    Student evaluates Instructor and Session quality for On-Site sessions

    Focus: Teaching quality, session structure, environment
    Categories: 8 dimensions of session quality
    Scale: 1-5 (1=Poor, 2=Below Average, 3=Average, 4=Good, 5=Excellent)

    IMPORTANT: Only students who ATTENDED (present/late status) can submit reviews
    """
    __tablename__ = "instructor_session_reviews"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 8 Quality Categories (1-5 scale)
    instructor_clarity = Column(Integer, nullable=False)        # Was explanation clear?
    support_approachability = Column(Integer, nullable=False)   # Easy to ask for help?
    session_structure = Column(Integer, nullable=False)         # Logical flow?
    relevance = Column(Integer, nullable=False)                 # Useful for development?
    environment = Column(Integer, nullable=False)               # Comfortable venue?
    engagement_feeling = Column(Integer, nullable=False)        # Felt engaged?
    feedback_quality = Column(Integer, nullable=False)          # Quality of feedback received?
    satisfaction = Column(Integer, nullable=False)              # Overall satisfaction?

    # Text feedback
    comments = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("Session", back_populates="instructor_reviews")
    student = relationship("User", foreign_keys=[student_id])
    instructor = relationship("User", foreign_keys=[instructor_id])

    # Constraints
    __table_args__ = (
        CheckConstraint('instructor_clarity BETWEEN 1 AND 5', name='check_instructor_clarity_range'),
        CheckConstraint('support_approachability BETWEEN 1 AND 5', name='check_support_approachability_range'),
        CheckConstraint('session_structure BETWEEN 1 AND 5', name='check_session_structure_range'),
        CheckConstraint('relevance BETWEEN 1 AND 5', name='check_relevance_range'),
        CheckConstraint('environment BETWEEN 1 AND 5', name='check_environment_range'),
        CheckConstraint('engagement_feeling BETWEEN 1 AND 5', name='check_engagement_feeling_range'),
        CheckConstraint('feedback_quality BETWEEN 1 AND 5', name='check_feedback_quality_range'),
        CheckConstraint('satisfaction BETWEEN 1 AND 5', name='check_satisfaction_range'),
        # One review per student per session
        {'sqlite_autoincrement': True}
    )

    @property
    def average_score(self) -> float:
        """Calculate average score across all categories"""
        return (self.instructor_clarity + self.support_approachability +
                self.session_structure + self.relevance + self.environment +
                self.engagement_feeling + self.feedback_quality + self.satisfaction) / 8

    @property
    def score_breakdown(self) -> dict:
        """Get detailed breakdown of scores"""
        return {
            'instructor_clarity': self.instructor_clarity,
            'support_approachability': self.support_approachability,
            'session_structure': self.session_structure,
            'relevance': self.relevance,
            'environment': self.environment,
            'engagement_feeling': self.engagement_feeling,
            'feedback_quality': self.feedback_quality,
            'satisfaction': self.satisfaction,
            'average': self.average_score
        }
