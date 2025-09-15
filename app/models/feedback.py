from sqlalchemy import Column, Integer, Text, Float, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ..database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    rating = Column(Float, nullable=False)  # Overall rating
    instructor_rating = Column(Float, nullable=True)  # Instructor specific rating
    session_quality = Column(Float, nullable=True)   # Session quality rating
    would_recommend = Column(Boolean, nullable=True)  # Recommendation
    comment = Column(Text, nullable=True)
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Add constraints for ratings between 1.0 and 5.0
    __table_args__ = (
        CheckConstraint('rating >= 1.0 AND rating <= 5.0', name='rating_range'),
        CheckConstraint('instructor_rating IS NULL OR (instructor_rating >= 1.0 AND instructor_rating <= 5.0)', name='instructor_rating_range'),
        CheckConstraint('session_quality IS NULL OR (session_quality >= 1.0 AND session_quality <= 5.0)', name='session_quality_range'),
    )

    # Relationships
    user = relationship("User", back_populates="feedbacks")
    session = relationship("Session", back_populates="feedbacks")