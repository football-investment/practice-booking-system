"""
🏆 Achievement Model

Defines available achievements in the gamification system.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, func
from sqlalchemy.orm import relationship
from typing import Dict, Any

from ..database import Base


class Achievement(Base):
    """
    Achievement definition.

    Defines what achievements are available in the system and their requirements.
    Used by gamification system to track and unlock user achievements.
    """
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(10), nullable=True)  # Emoji icon
    xp_reward = Column(Integer, default=0)
    category = Column(String(50), nullable=False, index=True)
    requirements = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user_achievements = relationship("UserAchievement", back_populates="achievement")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "xp_reward": self.xp_reward,
            "category": self.category,
            "requirements": self.requirements,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Achievement(code='{self.code}', name='{self.name}', xp={self.xp_reward})>"


class AchievementCategory:
    """Achievement category constants"""
    ONBOARDING = "onboarding"
    LEARNING = "learning"
    SOCIAL = "social"
    PROGRESSION = "progression"
    MASTERY = "mastery"
