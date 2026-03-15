from sqlalchemy import Column, Index, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timezone
import enum

from ..database import Base


class BookingStatus(enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    WAITLISTED = "WAITLISTED"


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        # Composite index for the hot capacity-check query:
        #   SELECT COUNT(*) FROM bookings WHERE session_id=? AND status='CONFIRMED'
        # Also covers waitlist count query (session_id=? AND status='WAITLISTED')
        Index("ix_bookings_session_status", "session_id", "status"),
        # Single-column index for participant-level queries (user's booking history,
        # duplicate-booking check: WHERE user_id=? AND session_id=? AND status!=CANCELLED)
        Index("ix_bookings_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    waitlist_position = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    cancelled_at = Column(DateTime, nullable=True)

    # NEW: Track attendance status for easier queries
    attended_status = Column(String(20), nullable=True)

    # NEW: Link booking to tournament enrollment (for tournaments only)
    enrollment_id = Column(Integer, ForeignKey("semester_enrollments.id"), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="bookings")
    session = relationship("Session", back_populates="bookings")
    attendance = relationship("Attendance", back_populates="booking", uselist=False)
    notifications = relationship("Notification", back_populates="related_booking")
    enrollment = relationship("SemesterEnrollment", back_populates="bookings")

    @hybrid_property
    def attended(self):
        """True if user attended the session (present or late)"""
        if self.attendance:
            return self.attendance.status.value in ['present', 'late']
        return False

    @attended.expression  
    def attended(cls):
        """SQLAlchemy expression for database queries"""
        return cls.attended_status.in_(['present', 'late'])

    @hybrid_property
    def can_give_feedback(self):
        """True if user has CONFIRMED booking, attended, and hasn't given feedback yet"""
        
        # 🎯 PHASE 1: Check booking status (align with backend validation)
        if self.status != BookingStatus.CONFIRMED:
            return False
        
        # 🎯 PHASE 2: Check attendance requirement  
        if not self.attended:
            return False
        
        # 🎯 PHASE 3: Check for existing feedback
        return not any(f.session_id == self.session_id for f in self.user.feedbacks)

    @hybrid_property  
    def feedback_submitted(self):
        """True if user has submitted feedback for this session"""
        return any(f.session_id == self.session_id for f in self.user.feedbacks)

    def update_attendance_status(self):
        """Sync attended_status field with attendance record"""
        if self.attendance:
            self.attended_status = self.attendance.status.value
        else:
            self.attended_status = None