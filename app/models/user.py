from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from ..database import Base


class UserRole(enum.Enum):
    ADMIN = "admin"
    INSTRUCTOR = "instructor"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    nickname = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Boolean, default=True)
    onboarding_completed = Column(Boolean, default=False)
    phone = Column(String, nullable=True)
    emergency_contact = Column(String, nullable=True)
    emergency_phone = Column(String, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    medical_notes = Column(String, nullable=True)
    interests = Column(String, nullable=True)  # JSON string of interests array
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    creator = relationship("User", remote_side=[id], back_populates="created_users")
    created_users = relationship("User", back_populates="creator")
    groups = relationship("Group", secondary="group_users", back_populates="users")
    bookings = relationship("Booking", back_populates="user")
    attendances = relationship("Attendance", foreign_keys="Attendance.user_id", back_populates="user")
    feedbacks = relationship("Feedback", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    taught_sessions = relationship("Session", back_populates="instructor")
    marked_attendances = relationship("Attendance", foreign_keys="Attendance.marked_by", back_populates="marker")
    
    # Project relationships
    instructed_projects = relationship("Project", back_populates="instructor")
    project_enrollments = relationship("ProjectEnrollment", back_populates="user")
    
    # Gamification relationships (will be added after UserAchievement/UserStats are defined)
    
    # Message relationships
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
    received_messages = relationship("Message", back_populates="recipient", foreign_keys="Message.recipient_id")