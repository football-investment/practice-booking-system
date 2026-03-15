"""
EventRewardLog — universal reward tracking for sessions (M-07, 2026-03-15).

Records XP and skill-area rewards earned per user per session.
Decoupled from LicenseProgression (which tracks structural level advancement).
"""
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ..database import Base


class EventRewardLog(Base):
    """
    Tracks rewards earned when a user completes a session (TRAINING or MATCH).

    Design principles:
    - One row per (user, session) pair — upsert on re-award via ON CONFLICT DO UPDATE
    - Unique constraint on (user_id, session_id) guarantees at-most-one row per pair
      even under concurrent INSERT calls, eliminating the TOCTOU race condition.
    - skill_areas_affected mirrors session_reward_config.skill_areas
    - multiplier_applied captures any dynamic multiplier (streak, performance tier, etc.)
    """
    __tablename__ = "event_reward_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_event_reward_log_user_session"),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    xp_earned = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total XP credited to user for this session"
    )
    points_earned = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Skill / ranking points earned (separate ledger from XP)"
    )
    skill_areas_affected = Column(
        ARRAY(String),
        nullable=True,
        comment="Skill area codes impacted (e.g. ['dribbling', 'passing'])"
    )
    multiplier_applied = Column(
        Float,
        nullable=False,
        default=1.0,
        comment="Final multiplier used (streak, tier, attendance bonus, etc.)"
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="event_reward_logs")
    session = relationship("Session", foreign_keys=[session_id], backref="event_reward_logs")
