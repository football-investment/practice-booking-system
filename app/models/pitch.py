"""
Pitch (Pálya) Model

Explicit pitch/field model within a Campus.

Hierarchy:
  Location (City) → Campus (Venue) → Pitch (Field/Pálya)

A campus can have multiple pitches running in parallel.
The TournamentConfiguration.parallel_fields value drives auto-creation
of pitches during session generation.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class Pitch(Base):
    """
    Pitch/Pálya — a specific playing field within a campus.

    Auto-created by the session generator when parallel_fields > 1.
    Can also be created manually by admin for pre-assignment.
    """
    __tablename__ = "pitches"

    id = Column(Integer, primary_key=True, index=True)

    # Parent campus
    campus_id = Column(
        Integer,
        ForeignKey("campuses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Campus this pitch belongs to"
    )

    # Ordering within the campus (1, 2, 3, ...)
    pitch_number = Column(
        Integer,
        nullable=False,
        comment="Sequential number within the campus (1=Pálya 1, 2=Pálya 2, ...)"
    )

    # Human-readable name — auto-generated or overridden by admin
    name = Column(
        String(100),
        nullable=False,
        comment="Display name, e.g. 'Pálya 1', 'North Field', 'Indoor A'"
    )

    # Physical capacity (persons at the same time)
    capacity = Column(
        Integer,
        default=2,
        nullable=False,
        comment="Max concurrent persons on this pitch (2 for 1v1 matches)"
    )

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    campus = relationship("Campus", back_populates="pitches")
    sessions = relationship("Session", back_populates="pitch")
    instructor_assignments = relationship(
        "PitchInstructorAssignment",
        back_populates="pitch",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "campus_id", "pitch_number",
            name="uq_campus_pitch_number"
        ),
    )

    def __repr__(self):
        return (
            f"<Pitch(id={self.id}, campus_id={self.campus_id}, "
            f"pitch_number={self.pitch_number}, name='{self.name}')>"
        )
