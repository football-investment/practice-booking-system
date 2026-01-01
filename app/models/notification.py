from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from ..database import Base


class NotificationType(enum.Enum):
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    SESSION_REMINDER = "session_reminder"
    SESSION_CANCELLED = "session_cancelled"
    WAITLIST_PROMOTED = "waitlist_promoted"
    GENERAL = "general"
    JOB_OFFER = "job_offer"  # New: Instructor job offer notification
    OFFER_ACCEPTED = "offer_accepted"  # New: Offer accepted notification
    OFFER_DECLINED = "offer_declined"  # New: Offer declined notification


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(Enum(NotificationType), default=NotificationType.GENERAL)
    is_read = Column(Boolean, default=False)
    related_session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    related_booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    read_at = Column(DateTime, nullable=True)

    # New fields for instructor job offers
    link = Column(String(255), nullable=True)  # Deep link to relevant page
    related_semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=True)
    related_request_id = Column(Integer, ForeignKey("instructor_assignment_requests.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
    related_session = relationship("Session", back_populates="notifications")
    related_booking = relationship("Booking", back_populates="notifications")
    # New relationships for job offers
    related_semester = relationship("Semester", foreign_keys=[related_semester_id])
    related_request = relationship("InstructorAssignmentRequest", foreign_keys=[related_request_id])