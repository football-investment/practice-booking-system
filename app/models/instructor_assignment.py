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

    # NEW: Location context
    location_id = Column(Integer, ForeignKey('locations.id', ondelete='CASCADE'), nullable=True,
                        comment="Location for the assignment")

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
    location = relationship("Location", foreign_keys=[location_id], backref="assignment_requests")

    def __repr__(self):
        return (f"<InstructorAssignmentRequest("
                f"id={self.id}, "
                f"semester_id={self.semester_id}, "
                f"instructor_id={self.instructor_id}, "
                f"status={self.status.value})>")


# ============================================================================
# NEW: Two-Tier Instructor Management System
# ============================================================================


class MasterOfferStatus(enum.Enum):
    """Status of master instructor offer"""
    OFFERED = "OFFERED"      # Offer sent, awaiting instructor response
    ACCEPTED = "ACCEPTED"    # Instructor accepted offer
    DECLINED = "DECLINED"    # Instructor declined offer
    EXPIRED = "EXPIRED"      # Offer deadline passed without response


class LocationMasterInstructor(Base):
    """
    TIER 1: Master Instructor Contract (Location-Level)

    Business Rules:
    - One master instructor per location
    - Admin hires the master instructor (DIRECT or via JOB_POSTING)
    - Master manages all instruction at that location
    - Master posts positions and selects assistant instructors

    Hybrid Hiring System:
    - DIRECT pathway: Admin sends offer → Instructor accepts/declines
    - JOB_POSTING pathway: Admin posts job → Instructors apply → Admin selects → Offer created
    - Both pathways require instructor acceptance (legal requirement)
    """
    __tablename__ = "location_master_instructors"

    id = Column(Integer, primary_key=True, index=True)

    # Location (UNIQUE per active master)
    location_id = Column(Integer, ForeignKey('locations.id', ondelete='CASCADE'),
                        nullable=False, comment="Location for master instructor")

    # Master instructor
    instructor_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'),
                          nullable=False, comment="Master instructor user")

    # Contract period
    contract_start = Column(DateTime(timezone=True), nullable=False,
                           comment="Contract start date")
    contract_end = Column(DateTime(timezone=True), nullable=False,
                         comment="Contract end date")

    # Status
    is_active = Column(Boolean, nullable=False, default=True,
                      comment="Only one active master per location")

    # Offer workflow (NULL = legacy immediate-active contract)
    offer_status = Column(Enum(MasterOfferStatus), nullable=True, default=None,
                         comment="Offer workflow status: NULL=legacy, OFFERED=pending, ACCEPTED=active, DECLINED/EXPIRED=rejected")

    # Offer timestamps
    offered_at = Column(DateTime(timezone=True), nullable=True,
                       comment="When offer was sent to instructor")
    offer_deadline = Column(DateTime(timezone=True), nullable=True,
                           comment="Deadline for instructor to accept/decline offer")
    accepted_at = Column(DateTime(timezone=True), nullable=True,
                        comment="When instructor accepted the offer")
    declined_at = Column(DateTime(timezone=True), nullable=True,
                        comment="When instructor declined or offer expired")

    # Hiring pathway metadata
    hiring_pathway = Column(String(20), nullable=False, default='DIRECT',
                           comment="Hiring method: DIRECT or JOB_POSTING")
    source_position_id = Column(Integer, ForeignKey('instructor_positions.id', ondelete='SET NULL'),
                               nullable=True,
                               comment="Links to job posting if hired via JOB_POSTING pathway")
    availability_override = Column(Boolean, nullable=False, default=False,
                                  comment="True if admin sent offer despite availability mismatch")

    # Legacy metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    terminated_at = Column(DateTime(timezone=True), nullable=True,
                          comment="When contract was terminated")

    # Relationships
    location = relationship("Location", foreign_keys=[location_id], backref="master_instructors")
    instructor = relationship("User", foreign_keys=[instructor_id], backref="master_locations")
    source_position = relationship("InstructorPosition", foreign_keys=[source_position_id],
                                  backref="resulting_master_contracts")

    def __repr__(self):
        return (f"<LocationMasterInstructor("
                f"location_id={self.location_id}, "
                f"instructor_id={self.instructor_id}, "
                f"active={self.is_active}, "
                f"offer_status={self.offer_status.value if self.offer_status else 'LEGACY'})>")


class PositionStatus(enum.Enum):
    """Status of instructor position posting"""
    OPEN = "OPEN"  # Accepting applications
    FILLED = "FILLED"  # Position filled
    CLOSED = "CLOSED"  # Closed without filling
    CANCELLED = "CANCELLED"  # Cancelled by master


class InstructorPosition(Base):
    """
    TIER 2: Position Postings (Job Board)

    Workflow:
    1. Master instructor posts position: "LFA_PLAYER/PRE M01-M06 needed"
    2. Position visible to all instructors with matching license
    3. Instructors apply with cover letter
    4. Master reviews and accepts/declines

    Supports both:
    - Assistant instructor positions (is_master_position=False, existing Tier 2)
    - Master instructor job openings (is_master_position=True, new JOB_POSTING pathway)
    """
    __tablename__ = "instructor_positions"

    id = Column(Integer, primary_key=True, index=True)

    # Location context
    location_id = Column(Integer, ForeignKey('locations.id', ondelete='CASCADE'),
                        nullable=False, comment="Location for position")

    # Posted by (admin for master positions, master for assistant positions)
    posted_by = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'),
                      nullable=False, comment="Admin or master instructor who posted")

    # Position type
    is_master_position = Column(Boolean, nullable=False, default=False,
                               comment="True if this is a master instructor opening, False for assistant positions")

    # Position details
    specialization_type = Column(String(50), nullable=False,
                                comment="LFA_PLAYER, INTERNSHIP, etc.")
    age_group = Column(String(20), nullable=False,
                      comment="PRE, YOUTH, AMATEUR, PRO")
    year = Column(Integer, nullable=False, comment="Year (e.g., 2026)")
    time_period_start = Column(String(10), nullable=False,
                              comment="Start period code (M01, Q1, etc.)")
    time_period_end = Column(String(10), nullable=False,
                            comment="End period code (M06, Q2, etc.)")

    # Job description
    description = Column(Text, nullable=False,
                        comment="Job description and requirements")

    # Priority and status
    priority = Column(Integer, nullable=False, default=5,
                     comment="1=low, 5=medium, 10=high")
    status = Column(Enum(PositionStatus), nullable=False, default=PositionStatus.OPEN,
                   comment="OPEN, FILLED, CLOSED, CANCELLED")

    # Deadlines
    application_deadline = Column(DateTime(timezone=True), nullable=False,
                                 comment="Application deadline")

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                       onupdate=func.now(), nullable=False)

    # Relationships
    location = relationship("Location", foreign_keys=[location_id], backref="instructor_positions")
    master = relationship("User", foreign_keys=[posted_by], backref="posted_positions")

    def __repr__(self):
        position_type = "MASTER" if self.is_master_position else "ASSISTANT"
        return (f"<InstructorPosition("
                f"id={self.id}, "
                f"type={position_type}, "
                f"spec={self.specialization_type}/{self.age_group}, "
                f"period={self.time_period_start}-{self.time_period_end}, "
                f"status={self.status.value})>")


class ApplicationStatus(enum.Enum):
    """Status of position application"""
    PENDING = "PENDING"  # Waiting for master review
    ACCEPTED = "ACCEPTED"  # Master accepted
    DECLINED = "DECLINED"  # Master declined


class PositionApplication(Base):
    """
    Applications to instructor positions

    Workflow:
    1. Instructor sees position on job board
    2. Instructor applies with cover letter
    3. Master reviews application
    4. Master accepts → creates InstructorAssignment
    """
    __tablename__ = "position_applications"

    id = Column(Integer, primary_key=True, index=True)

    # Position and applicant
    position_id = Column(Integer, ForeignKey('instructor_positions.id', ondelete='CASCADE'),
                        nullable=False, comment="Position being applied to")
    applicant_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'),
                         nullable=False, comment="Instructor applying")

    # Application content
    application_message = Column(Text, nullable=False,
                                comment="Cover letter / application message")

    # Status
    status = Column(Enum(ApplicationStatus), nullable=False,
                   default=ApplicationStatus.PENDING,
                   comment="PENDING, ACCEPTED, DECLINED")

    # Review
    reviewed_at = Column(DateTime(timezone=True), nullable=True,
                        comment="When master reviewed application")

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    position = relationship("InstructorPosition", foreign_keys=[position_id],
                          backref="applications")
    applicant = relationship("User", foreign_keys=[applicant_id],
                           backref="position_applications")

    def __repr__(self):
        return (f"<PositionApplication("
                f"position_id={self.position_id}, "
                f"applicant_id={self.applicant_id}, "
                f"status={self.status.value})>")


class InstructorAssignment(Base):
    """
    Active instructor assignments (supports co-instructors)

    Business Rules:
    - Multiple instructors can be assigned to same period (co-instructors)
    - Assignment tracks location, spec, age group, year, time period
    - Master instructor posts position → accepts applicant → creates assignment
    """
    __tablename__ = "instructor_assignments"

    id = Column(Integer, primary_key=True, index=True)

    # Location and instructor
    location_id = Column(Integer, ForeignKey('locations.id', ondelete='CASCADE'),
                        nullable=False, comment="Assignment location")
    instructor_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'),
                          nullable=False, comment="Assigned instructor")

    # Assignment details
    specialization_type = Column(String(50), nullable=False,
                                comment="LFA_PLAYER, INTERNSHIP, etc.")
    age_group = Column(String(20), nullable=False,
                      comment="PRE, YOUTH, AMATEUR, PRO")
    year = Column(Integer, nullable=False, comment="Year (e.g., 2026)")
    time_period_start = Column(String(10), nullable=False,
                              comment="Start period code (M01, Q1, etc.)")
    time_period_end = Column(String(10), nullable=False,
                            comment="End period code (M06, Q2, etc.)")

    # Master vs assistant
    is_master = Column(Boolean, nullable=False, default=False,
                      comment="True if this is the master instructor")

    # Assignment metadata
    assigned_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
                        comment="Master instructor who made assignment")
    is_active = Column(Boolean, nullable=False, default=True,
                      comment="Active assignment")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deactivated_at = Column(DateTime(timezone=True), nullable=True,
                           comment="When assignment was deactivated")

    # Relationships
    location = relationship("Location", foreign_keys=[location_id], backref="instructor_assignments")
    instructor = relationship("User", foreign_keys=[instructor_id], backref="instructor_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by], backref="assigned_instructors")

    def __repr__(self):
        return (f"<InstructorAssignment("
                f"instructor_id={self.instructor_id}, "
                f"spec={self.specialization_type}/{self.age_group}, "
                f"period={self.time_period_start}-{self.time_period_end}, "
                f"active={self.is_active})>")
