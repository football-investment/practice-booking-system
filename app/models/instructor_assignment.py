"""
📅 Instructor Assignment Request System

NEW CONCEPT: Demand-driven instructor assignment workflow

Flow:
1. Instructor sets general availability: "Q3 2026, Budapest+Budaörs"
2. Admin generates semesters for specific age groups
3. System shows admins which instructors are available
4. Admin sends assignment request to instructor
5. Instructor accepts/declines specific semester assignments

Example:
- Instructor: "I'm available Q3 2026 in Budapest"
- Admin: Creates PRE semester Q3 Budapest
- Admin: Sends request to instructor: "Teach PRE Q3 Budapest?"
- Instructor: Accepts → semester.master_instructor_id = instructor.id
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..database import Base


class AssignmentRequestStatus(enum.Enum):
    """Status of instructor assignment request"""
    PENDING = "PENDING"  # Waiting for instructor response
    ACCEPTED = "ACCEPTED"  # Instructor accepted
    DECLINED = "DECLINED"  # Instructor declined
    CANCELLED = "CANCELLED"  # Admin cancelled before response
    EXPIRED = "EXPIRED"  # Request expired (timeout)


class InstructorAvailabilityWindow(Base):
    """
    Simplified availability: Instructor just marks time periods ONLY.

    Location comes from assignment requests! Instructor doesn't choose location upfront.
    """
    __tablename__ = "instructor_availability_windows"

    id = Column(Integer, primary_key=True, index=True)

    # Instructor
    instructor_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
                          comment="Instructor setting availability")

    # Time window
    year = Column(Integer, nullable=False, comment="Year (e.g., 2026)")
    time_period = Column(String(10), nullable=False,
                        comment="Q1, Q2, Q3, Q4 or M01-M12")

    # NO LOCATION! Location comes from assignment request!

    # Availability status
    is_available = Column(Boolean, nullable=False, default=True,
                         comment="True if instructor is available for this window")

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    notes = Column(Text, nullable=True, comment="Optional notes from instructor")

    # Relationships
    instructor = relationship("User", foreign_keys=[instructor_id], backref="availability_windows")

    def __repr__(self):
        return (f"<InstructorAvailabilityWindow("
                f"instructor_id={self.instructor_id}, "
                f"period={self.time_period}, "
                f"year={self.year})>")


class InstructorAssignmentRequest(Base):
    """
    Admin → Instructor assignment request for a specific semester.

    Workflow:
    1. Admin creates semester (e.g., PRE Q3 Budapest)
    2. System suggests available instructors for Q3 Budapest
    3. Admin sends request to instructor
    4. Instructor accepts/declines
    5. If accepted: semester.master_instructor_id = instructor.id
    """
    __tablename__ = "instructor_assignment_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Semester to assign
    semester_id = Column(Integer, ForeignKey('semesters.id', ondelete='CASCADE'), nullable=False,
                        comment="Semester needing an instructor")

    # Instructor being asked
    instructor_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
                          comment="Instructor receiving the request")

    # Admin who created the request
    requested_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
                         comment="Admin who sent the request")

    # Request status
    status = Column(Enum(AssignmentRequestStatus), nullable=False,
                   default=AssignmentRequestStatus.PENDING,
                   comment="PENDING, ACCEPTED, DECLINED, CANCELLED, EXPIRED")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True,
                         comment="When instructor responded")
    expires_at = Column(DateTime(timezone=True), nullable=True,
                       comment="Request expiration (optional)")

    # Messages
    request_message = Column(Text, nullable=True,
                            comment="Message from admin to instructor")
    response_message = Column(Text, nullable=True,
                             comment="Message from instructor (if declined, reason)")

    # Priority
    priority = Column(Integer, nullable=False, default=0,
                     comment="Higher number = higher priority (0-10)")

    # Relationships
    semester = relationship("Semester", foreign_keys=[semester_id], backref="assignment_requests")
    instructor = relationship("User", foreign_keys=[instructor_id], backref="received_assignment_requests")
    admin = relationship("User", foreign_keys=[requested_by], backref="sent_assignment_requests")

    def __repr__(self):
        return (f"<InstructorAssignmentRequest("
                f"id={self.id}, "
                f"semester_id={self.semester_id}, "
                f"instructor_id={self.instructor_id}, "
                f"status={self.status.value})>")
