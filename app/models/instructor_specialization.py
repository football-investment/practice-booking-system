"""
👨‍🏫 Instructor Specialization Model

Tracks which specializations each instructor is qualified to teach.

Example:
    Founder (admin) is qualified for ALL 4 specializations:
    - GANCUJU_PLAYER
    - LFA_FOOTBALL_PLAYER
    - LFA_COACH
    - INTERNSHIP

    Future instructors may only be qualified for 1-2 specializations.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base


class InstructorSpecialization(Base):
    """Instructor qualifications for teaching specific specializations"""
    __tablename__ = "instructor_specializations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    specialization = Column(String(50), nullable=False)
    certified_at = Column(DateTime, default=datetime.utcnow)
    certified_by = Column(Integer, ForeignKey("users.id"))
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    instructor = relationship("User", foreign_keys=[user_id], back_populates="instructor_specializations")
    certifier = relationship("User", foreign_keys=[certified_by])

    def __repr__(self):
        return f"<InstructorSpec(user_id={self.user_id}, spec={self.specialization})>"
