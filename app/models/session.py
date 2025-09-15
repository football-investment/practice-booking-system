from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from ..database import Base


class SessionMode(enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    HYBRID = "hybrid"


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    date_start = Column(DateTime, nullable=False)
    date_end = Column(DateTime, nullable=False)
    mode = Column(Enum(SessionMode), default=SessionMode.OFFLINE)
    capacity = Column(Integer, default=20)
    location = Column(String, nullable=True)  # for offline sessions
    meeting_link = Column(String, nullable=True)  # for online sessions
    sport_type = Column(String, default='General')  # Enhanced field for UI
    level = Column(String, default='All Levels')  # Enhanced field for UI
    instructor_name = Column(String, nullable=True)  # Enhanced field for UI
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)  # FIXED: Made nullable to allow sessions without groups
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    semester = relationship("Semester", back_populates="sessions")
    group = relationship("Group", back_populates="sessions")
    instructor = relationship("User", back_populates="taught_sessions")
    bookings = relationship("Booking", back_populates="session")
    attendances = relationship("Attendance", back_populates="session")
    feedbacks = relationship("Feedback", back_populates="session")
    notifications = relationship("Notification", back_populates="related_session")
    project_sessions = relationship("ProjectSession", back_populates="session")

    @property
    def related_projects(self):
        return [ps.project for ps in self.project_sessions]
    
    @property
    def is_project_session(self):
        return len(self.project_sessions) > 0