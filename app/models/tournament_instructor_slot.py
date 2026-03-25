"""
Tournament Instructor Slot Model

Per-event instructor planning + game-day check-in state.

Each tournament can have:
  - 1 MASTER slot  (overall coordinator; NULL pitch_id)
  - N FIELD slots  (one per pitch; pitch_id required)

Status lifecycle:
  PLANNED → CONFIRMED → CHECKED_IN
                      ↘ ABSENT
"""

import enum

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class SlotRole(str, enum.Enum):
    MASTER = "MASTER"   # Overall coordinator (1 per tournament)
    FIELD  = "FIELD"    # Pitch-level match manager (1 per pitch)


class SlotStatus(str, enum.Enum):
    PLANNED    = "PLANNED"      # Tervezett, de nem megerősített
    CONFIRMED  = "CONFIRMED"    # Instructor visszaigazolta részvételét
    CHECKED_IN = "CHECKED_IN"   # Fizikailag megjelent (game-day)
    ABSENT     = "ABSENT"       # Nem jelent meg


class TournamentInstructorSlot(Base):
    """
    Instructor planning + attendance record for a single tournament event.

    Authority chain enforced at service layer:
      - Admin: can add/remove slots; marks MASTER absent
      - Master (MASTER slot holder): self-check-in; marks FIELD present/absent
      - Field (FIELD slot holder): no slot management rights
    """
    __tablename__ = "tournament_instructor_slots"

    id = Column(Integer, primary_key=True, index=True)

    semester_id = Column(
        Integer,
        ForeignKey("semesters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    instructor_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    role = Column(
        String(20),
        nullable=False,
        comment="MASTER | FIELD",
    )

    # NULL for MASTER role; required for FIELD role
    pitch_id = Column(
        Integer,
        ForeignKey("pitches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status = Column(
        String(20),
        nullable=False,
        default=SlotStatus.PLANNED.value,
        index=True,
    )

    checked_in_at  = Column(DateTime(timezone=True), nullable=True)
    checked_out_at = Column(DateTime(timezone=True), nullable=True)

    assigned_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    semester   = relationship("Semester")
    instructor = relationship("User", foreign_keys=[instructor_id],
                              backref="tournament_instructor_slots")
    pitch      = relationship("Pitch", backref="instructor_slots")
    assigner   = relationship("User", foreign_keys=[assigned_by],
                              backref="instructor_slots_assigned")

    __table_args__ = (
        # 1 instructor = 1 slot per tournament
        UniqueConstraint("semester_id", "instructor_id",
                         name="uq_tournament_slot_instructor"),
        # 1 field instructor per pitch per tournament
        # (partial: only for FIELD role, enforced in service layer too)
        Index(
            "ix_tournament_slot_pitch_unique",
            "semester_id", "pitch_id",
            unique=True,
            postgresql_where=("role = 'FIELD'"),
        ),
    )

    def __repr__(self):
        return (
            f"<TournamentInstructorSlot("
            f"semester_id={self.semester_id}, "
            f"instructor_id={self.instructor_id}, "
            f"role={self.role}, "
            f"status={self.status})>"
        )
