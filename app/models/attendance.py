from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from ..database import Base


class AttendanceStatus(enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"
    excused = "excused"


class ConfirmationStatus(enum.Enum):
    pending_confirmation = "pending_confirmation"  # Instructor marked, student hasn't confirmed
    confirmed = "confirmed"  # Both parties agree
    disputed = "disputed"  # Student disagrees with instructor


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)  # Nullable for tournament sessions
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.present)
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)
    marked_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Instructor who marked

    # Two-way confirmation fields
    confirmation_status = Column(Enum(ConfirmationStatus), default=ConfirmationStatus.pending_confirmation)
    student_confirmed_at = Column(DateTime, nullable=True)  # When student confirmed
    dispute_reason = Column(String, nullable=True)  # If student disputes

    # Change request fields (for confirmed attendance)
    pending_change_to = Column(String, nullable=True)  # Requested new status (e.g., 'late')
    change_requested_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Instructor who requested change
    change_requested_at = Column(DateTime, nullable=True)  # When change was requested
    change_request_reason = Column(String, nullable=True)  # Why instructor wants to change

    # 🎯 XP/Gamification
    xp_earned = Column(Integer, default=0, comment="XP earned for this attendance")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="attendances")
    session = relationship("Session", back_populates="attendances")
    booking = relationship("Booking", back_populates="attendance")
    marker = relationship("User", foreign_keys=[marked_by], back_populates="marked_attendances")
    history = relationship("AttendanceHistory", back_populates="attendance", cascade="all, delete-orphan")


class AttendanceHistory(Base):
    """Audit log for attendance changes"""
    __tablename__ = "attendance_history"

    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey("attendance.id"), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who made the change
    change_type = Column(String, nullable=False)  # 'status_change', 'confirmation', 'dispute'
    old_value = Column(String, nullable=True)  # Previous status
    new_value = Column(String, nullable=False)  # New status
    reason = Column(String, nullable=True)  # Dispute reason or notes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    attendance = relationship("Attendance", back_populates="history")
    changed_by_user = relationship("User", foreign_keys=[changed_by])