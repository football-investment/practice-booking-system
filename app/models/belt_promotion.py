"""
🥋 Belt Promotion Model - Gancuju Belt System
Tracks belt promotions for Gancuju players
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from ..database import Base


class BeltPromotion(Base):
    """Belt promotion records for Gancuju players"""

    __tablename__ = "belt_promotions"

    id = Column(Integer, primary_key=True, index=True)
    user_license_id = Column(Integer, ForeignKey("user_licenses.id", ondelete="CASCADE"), nullable=False, index=True)
    from_belt = Column(String(50), nullable=True)  # NULL for initial belt
    to_belt = Column(String(50), nullable=False, index=True)
    promoted_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    promoted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    exam_score = Column(Integer, nullable=True)  # Optional exam score (0-100)
    exam_notes = Column(Text, nullable=True)

    # Relationships
    user_license = relationship("UserLicense", back_populates="belt_promotions")
    promoter = relationship("User", foreign_keys=[promoted_by])

    def __repr__(self):
        return f"<BeltPromotion(id={self.id}, license={self.user_license_id}, {self.from_belt or 'None'} → {self.to_belt})>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_license_id': self.user_license_id,
            'from_belt': self.from_belt,
            'to_belt': self.to_belt,
            'promoted_by': self.promoted_by,
            'promoted_at': self.promoted_at.isoformat() if self.promoted_at else None,
            'notes': self.notes,
            'exam_score': self.exam_score,
            'exam_notes': self.exam_notes
        }
