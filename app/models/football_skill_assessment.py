"""
⚽ Football Skill Assessment Model
Tracks individual skill assessments for LFA Player specializations
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import Dict, Any

from ..database import Base


class FootballSkillAssessment(Base):
    """
    Individual skill assessment record

    Each row represents ONE assessment of ONE skill at ONE point in time.
    Multiple assessments are averaged to calculate the current skill level.

    Example:
        Heading assessments for Junior Intern:
        - 2025-11-20: 7/10 = 70%
        - 2025-11-25: 8/10 = 80%
        - 2025-12-01: 6/10 = 60%
        → Current average: (70 + 80 + 60) / 3 = 70%
    """
    __tablename__ = "football_skill_assessments"

    id = Column(Integer, primary_key=True, index=True)

    # Which license/student?
    user_license_id = Column(Integer, ForeignKey("user_licenses.id", ondelete="CASCADE"), nullable=False)

    # Which skill?
    skill_name = Column(String(50), nullable=False)  # 'heading', 'shooting', 'crossing', 'passing', 'dribbling', 'ball_control'

    # Assessment scores
    points_earned = Column(Integer, nullable=False)  # e.g., 7
    points_total = Column(Integer, nullable=False)   # e.g., 10
    percentage = Column(Float, nullable=False)       # e.g., 70.0 (auto-calculated)

    # Who assessed and when?
    assessed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    assessed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Optional notes from instructor
    notes = Column(Text, nullable=True)

    # Relationships
    user_license = relationship("UserLicense", foreign_keys=[user_license_id])
    assessor = relationship("User", foreign_keys=[assessed_by])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_license_id": self.user_license_id,
            "skill_name": self.skill_name,
            "points_earned": self.points_earned,
            "points_total": self.points_total,
            "percentage": round(self.percentage, 1),
            "assessed_by": self.assessed_by,
            "assessed_at": self.assessed_at.isoformat() if self.assessed_at else None,
            "notes": self.notes
        }

    @classmethod
    def calculate_percentage(cls, points_earned: int, points_total: int) -> float:
        """Calculate percentage from points"""
        if points_total == 0:
            return 0.0
        return round((points_earned / points_total) * 100, 1)

    def __repr__(self):
        return f"<FootballSkillAssessment {self.skill_name}: {self.points_earned}/{self.points_total} ({self.percentage}%)>"
