"""
Team Models

Models for team-based tournaments.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


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

    # Relationships
    captain = relationship("User", foreign_keys=[captain_user_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    tournament_enrollments = relationship("TournamentTeamEnrollment", back_populates="team", cascade="all, delete-orphan")
    rankings = relationship("TournamentRanking", back_populates="team", cascade="all, delete-orphan")


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
    is_active = Column(Boolean, default=True)

    # Relationships
    semester = relationship("Semester")
    team = relationship("Team", back_populates="tournament_enrollments")

    __table_args__ = (
        {'extend_existing': True}
    )
