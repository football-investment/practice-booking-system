"""
Team Models

Models for team-based tournaments.
"""
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class TeamInviteStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Team(Base):
    """Team model for team-based tournaments"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, index=True)
    captain_user_id = Column(Integer, ForeignKey("users.id"))
    specialization_type = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    # Club association (optional — backward compat: nullable)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=True, index=True)
    age_group_label = Column(String(20), nullable=True)  # U12, U15, Adult, etc.

    # Relationships
    captain = relationship("User", foreign_keys=[captain_user_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    tournament_enrollments = relationship("TournamentTeamEnrollment", back_populates="team", cascade="all, delete-orphan")
    rankings = relationship("TournamentRanking", back_populates="team", cascade="all, delete-orphan")
    invites = relationship("TeamInvite", back_populates="team", cascade="all, delete-orphan")
    club = relationship("Club", back_populates="teams", foreign_keys=[club_id])


class TeamMember(Base):
    """Team member association"""
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50))  # CAPTAIN, PLAYER
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        {'extend_existing': True}
    )


class TournamentTeamEnrollment(Base):
    """Team enrollment in tournaments"""
    __tablename__ = "tournament_team_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    semester_id = Column(Integer, ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_date = Column(DateTime(timezone=True), server_default=func.now())
    payment_verified = Column(Boolean, default=False)
    payment_verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    payment_verified_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    checked_in_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    semester = relationship("Semester")
    team = relationship("Team", back_populates="tournament_enrollments")

    __table_args__ = (
        {'extend_existing': True}
    )


class TeamInvite(Base):
    """Pending/accepted/rejected invite for a player to join a team"""
    __tablename__ = "team_invites"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    invited_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    invited_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default=TeamInviteStatus.PENDING.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    team = relationship("Team", back_populates="invites")
    invited_user = relationship("User", foreign_keys=[invited_user_id])
    invited_by = relationship("User", foreign_keys=[invited_by_id])


class TournamentPlayerCheckin(Base):
    """Pre-tournament player check-in record (separate from per-session Attendance)."""
    __tablename__ = "tournament_player_checkins"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    checked_in_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    checked_in_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    team = relationship("Team", foreign_keys=[team_id])
    checked_in_by = relationship("User", foreign_keys=[checked_in_by_id])

    __table_args__ = (
        UniqueConstraint("tournament_id", "user_id", name="uq_player_checkin"),
    )
