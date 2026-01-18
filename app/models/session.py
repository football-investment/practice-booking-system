from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from typing import Optional

from ..database import Base
from .specialization import SpecializationType

            from app.services.specialization_config_loader import SpecializationConfigLoader
class SessionType(enum.Enum):
    """Professional session type classification for edtech/sporttech platforms"""
    on_site = "on_site"    # Physical presence required at venue
    virtual = "virtual"    # Remote attendance via online platform
    hybrid = "hybrid"      # Both on-site and virtual attendance options available


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    date_start = Column(DateTime, nullable=False)
    date_end = Column(DateTime, nullable=False)
    session_type = Column(Enum(SessionType), default=SessionType.on_site, nullable=False)
    capacity = Column(Integer, default=20)
    location = Column(String, nullable=True)  # for on-site sessions
    meeting_link = Column(String, nullable=True)  # for virtual sessions
    sport_type = Column(String, default='General')  # Enhanced field for UI
    level = Column(String, default='All Levels')  # Enhanced field for UI
    instructor_name = Column(String, nullable=True)  # Enhanced field for UI
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)  # FIXED: Made nullable to allow sessions without groups
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 🎓 NEW: Specialization fields
    target_specialization = Column(
        Enum(SpecializationType),
        nullable=True,
        comment="Target specialization for this session (null = all specializations)"
    )
    
    mixed_specialization = Column(
        Boolean,
        default=False,
        comment="Whether this session is open to all specializations"
    )

    # ⏱️ Session Timer/Tracker fields (On-Site & Hybrid only)
    actual_start_time = Column(
        DateTime,
        nullable=True,
        comment="Actual start time when instructor starts the session"
    )
    actual_end_time = Column(
        DateTime,
        nullable=True,
        comment="Actual end time when instructor stops the session"
    )
    session_status = Column(
        String(20),
        default="scheduled",
        comment="Session status: scheduled, in_progress, completed"
    )

    # 🔓 Quiz Access Control (HYBRID sessions only)
    quiz_unlocked = Column(
        Boolean,
        default=False,
        comment="Whether the quiz is unlocked for students (HYBRID sessions)"
    )

    # 🎯 XP/Gamification
    base_xp = Column(
        Integer,
        default=50,
        comment="Base XP awarded for completing this session (HYBRID=100, ON-SITE=75, VIRTUAL=50)"
    )

    # 💳 Credit System
    credit_cost = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Number of credits required to book this session (default: 1, workshops may cost more)"
    )

    # 🏆 Tournament Game Fields
    is_tournament_game = Column(
        Boolean,
        default=False,
        index=True,
        comment="True if this session is a tournament game"
    )

    game_type = Column(
        String(100),
        nullable=True,
        comment="Type/name of tournament game (user-defined, e.g., 'Skills Challenge')"
    )

    game_results = Column(
        Text,
        nullable=True,
        comment="JSON array of game results: [{user_id: 1, score: 95, rank: 1}, ...]"
    )

    # 🎯 AUTO-GENERATED TOURNAMENT SESSION METADATA
    auto_generated = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if this session was auto-generated from tournament type config"
    )

    tournament_phase = Column(
        String(50),
        nullable=True,
        comment="Tournament phase: 'Group Stage', 'Knockout Stage', 'Finals'"
    )

    tournament_round = Column(
        Integer,
        nullable=True,
        comment="Round number within the tournament (1, 2, 3, ...)"
    )

    tournament_match_number = Column(
        Integer,
        nullable=True,
        comment="Match number within the round (1, 2, 3, ...)"
    )

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

    # Performance review relationships (On-Site sessions only)
    student_reviews = relationship("StudentPerformanceReview", back_populates="session")
    instructor_reviews = relationship("InstructorSessionReview", back_populates="session")

    @property
    def related_projects(self):
        return [ps.project for ps in self.project_sessions]
    
    @property
    def is_project_session(self):
        return len(self.project_sessions) > 0
    
    # 🎓 NEW: Specialization helper properties
    @property
    def specialization_info(self) -> str:
        """Get user-friendly specialization information (HYBRID: loads from JSON)"""
        if self.mixed_specialization:
            return "Vegyes (Player + Coach)"
        elif self.target_specialization:
            loader = SpecializationConfigLoader()
            try:
                display_info = loader.get_display_info(self.target_specialization)
                return display_info.get('name', str(self.target_specialization.value))
            except Exception:
                return str(self.target_specialization.value)
        return "Minden szakirány"

    @property
    def specialization_badge(self) -> str:
        """Get specialization badge/icon (HYBRID: loads from JSON)"""
        if self.mixed_specialization:
            return "⚽👨‍🏫"
        elif self.target_specialization:
            loader = SpecializationConfigLoader()
            try:
                display_info = loader.get_display_info(self.target_specialization)
                return display_info.get('icon', '🎯')
            except Exception:
                return "🎯"
        return "🎯"
    
    @property
    def is_accessible_to_all(self) -> bool:
        """Check if session is accessible to all specializations"""
        return self.mixed_specialization or self.target_specialization is None

    @property
    def type_display(self) -> str:
        """Get user-friendly session type display name"""
        type_map = {
            SessionType.on_site: "On-Site",
            SessionType.virtual: "Virtual",
            SessionType.hybrid: "Hybrid"
        }
        return type_map.get(self.session_type, "On-Site")

    @property
    def type_icon(self) -> str:
        """Get session type icon"""
        icon_map = {
            SessionType.on_site: "🏟️",
            SessionType.virtual: "💻",
            SessionType.hybrid: "🔄"
        }
        return icon_map.get(self.session_type, "🏟️")

    @property
    def type_badge_color(self) -> str:
        """Get session type badge color for UI"""
        color_map = {
            SessionType.on_site: "#3498db",  # Blue
            SessionType.virtual: "#9b59b6",  # Purple
            SessionType.hybrid: "#e67e22"    # Orange
        }
        return color_map.get(self.session_type, "#3498db")