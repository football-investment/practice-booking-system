"""
🎯 Skill Reward Model
Tracks skill point rewards from tournaments and training sessions
Strict separation: FootballSkillAssessment = measurements, SkillReward = auditable events
"""
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import Dict, Any

from ..database import Base


class SourceType(enum.Enum):
    """Source types for skill rewards"""
    TOURNAMENT = "TOURNAMENT"
    TRAINING = "TRAINING"  # Future: training session rewards


class SkillReward(Base):
    """Track skill point rewards from tournaments and training sessions

    This table provides an auditable history of all skill point awards.
    It is the foundation for the player progression motor.

    Separation of concerns:
    - FootballSkillAssessment: Measurements and current state of player skills
    - SkillReward: Historical events of skill point awards from specific activities
    """
    __tablename__ = "skill_rewards"

    id = Column(Integer, primary_key=True, index=True)

    # Who received the reward
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # What activity generated the reward
    source_type = Column(String(20), nullable=False)  # 'TOURNAMENT' or 'TRAINING'
    source_id = Column(Integer, nullable=False)  # tournament_id or training_id

    # Skill details
    skill_name = Column(String(50), nullable=False)
    points_awarded = Column(Integer, nullable=False)  # Can be positive or negative

    # When the reward was created
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = relationship("User", back_populates="skill_rewards")

    # Composite index for efficient queries by source
    __table_args__ = (
        Index('ix_skill_rewards_source', 'source_type', 'source_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "skill_name": self.skill_name,
            "points_awarded": self.points_awarded,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
