"""
Pitch Instructor Assignment Model

Assigns instructors to specific pitches (fields) within a campus.
Supports two assignment modes:
  - DIRECT: Admin/master invites a specific instructor
  - JOB_POSTING: Open position; instructors apply via InstructorPosition

A pitch assignment is always scoped to a (pitch, semester) pair.
One master instructor per pitch per semester (enforced by UniqueConstraint).
Multiple assistant instructors are allowed.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
import enum

from ..database import Base


class PitchAssignmentType(str, enum.Enum):
    """How the instructor was assigned to this pitch."""
    DIRECT      = "DIRECT"       # Admin/master directly invited the instructor
    JOB_POSTING = "JOB_POSTING"  # Instructor applied via open job posting


class PitchAssignmentStatus(str, enum.Enum):
    """Lifecycle state of the pitch assignment."""
    PENDING   = "PENDING"    # Invitation sent, awaiting instructor response
    ACTIVE    = "ACTIVE"     # Instructor accepted and is managing this pitch
    DECLINED  = "DECLINED"   # Instructor declined the invitation
    COMPLETED = "COMPLETED"  # Tournament/semester ended, assignment closed


class PitchInstructorAssignment(Base):
    """
    Instructor assignment to a specific pitch for a tournament semester.

    Workflow:
      DIRECT:       assign_instructor_to_pitch_direct() → PENDING
                    accept_pitch_assignment()           → ACTIVE
      JOB_POSTING:  InstructorPosition created with pitch_id
                    PositionApplication accepted         → ACTIVE (auto-created)
    """
    __tablename__ = "pitch_instructor_assignments"

    id = Column(Integer, primary_key=True, index=True)

    # The pitch being managed
    pitch_id = Column(
        Integer,
        ForeignKey("pitches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # The instructor assigned
    instructor_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Tournament context (optional: campus-wide assignment has no semester_id)
    semester_id = Column(
        Integer,
        ForeignKey("semesters.id"),
        nullable=True,
        index=True
    )

    # Master = true means this instructor is responsible for data entry on this pitch.
    # Only 1 master per pitch per semester (enforced below).
    is_master = Column(Boolean, default=False, nullable=False)

    # How the assignment was created
    assignment_type = Column(
        String(20),
        nullable=False,
        comment="DIRECT (admin invite) or JOB_POSTING (open application)"
    )

    status = Column(
        String(20),
        nullable=False,
        default=PitchAssignmentStatus.PENDING.value,
        index=True
    )

    # Eligibility requirements (used for filtering in get_eligible_instructors_for_pitch)
    required_license_type = Column(
        String(50),
        nullable=True,
        comment="Required InstructorSpecialization type, e.g. 'LFA_FOOTBALL_PLAYER'"
    )
    required_age_group = Column(
        String(20),
        nullable=True,
        comment="Required age group, e.g. 'YOUTH', 'PRO', 'AMATEUR'"
    )

    # Who created the assignment (admin or campus master)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Lifecycle timestamps
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    ended_at     = Column(DateTime(timezone=True), nullable=True)

    # Optional notes (admin message when sending DIRECT invite)
    notes = Column(Text, nullable=True)

    # Relationships
    pitch      = relationship("Pitch", back_populates="instructor_assignments")
    instructor = relationship("User", foreign_keys=[instructor_id],
                              backref="pitch_assignments_as_instructor")
    semester   = relationship("Semester")
    assigner   = relationship("User", foreign_keys=[assigned_by],
                              backref="pitch_assignments_created")

    __table_args__ = (
        # Exactly 1 active master per pitch per semester
        UniqueConstraint(
            "pitch_id", "semester_id",
            name="uq_pitch_master_per_semester",
            # PostgreSQL partial index: only enforced for active masters
        ),
    )

    def __repr__(self):
        return (
            f"<PitchInstructorAssignment("
            f"pitch_id={self.pitch_id}, "
            f"instructor_id={self.instructor_id}, "
            f"status={self.status}, "
            f"is_master={self.is_master})>"
        )
