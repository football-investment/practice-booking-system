"""
Tournament Ranking and Stats Models

Models for tournament leaderboards, rankings, and statistics.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class TournamentRanking(Base):
    """Tournament leaderboard rankings"""
    __tablename__ = "tournament_rankings"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    participant_type = Column(String(50), nullable=False)  # INDIVIDUAL, TEAM
    rank = Column(Integer)
    points = Column(Numeric(10, 2), default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tournament = relationship("Semester")
    user = relationship("User")
    team = relationship("Team", back_populates="rankings")

    __table_args__ = (
        {'extend_existing': True}
    )


class TournamentStats(Base):
    """Tournament-level statistics"""
    __tablename__ = "tournament_stats"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    total_participants = Column(Integer, default=0)
    total_teams = Column(Integer, default=0)
    total_matches = Column(Integer, default=0)
    completed_matches = Column(Integer, default=0)
    total_revenue = Column(Integer, default=0)  # Credits collected
    avg_attendance_rate = Column(Numeric(5, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tournament = relationship("Semester")

    __table_args__ = (
        {'extend_existing': True}
    )


class TournamentReward(Base):
    """Tournament rewards configuration"""
    __tablename__ = "tournament_rewards"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(String(20), nullable=False)  # "1ST", "2ND", "3RD", "PARTICIPANT"
    xp_amount = Column(Integer, default=0)
    credits_reward = Column(Integer, default=0)
    badge_id = Column(Integer, nullable=True)

    # Relationships
    tournament = relationship("Semester")

    __table_args__ = (
        {'extend_existing': True}
    )
