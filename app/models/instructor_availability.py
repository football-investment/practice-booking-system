"""
Instructor Specialization Availability Model

Allows instructors (especially Grandmasters) to choose:
- Which time periods they want to work (Q1, Q2, Q3, Q4 or M01-M12)
- Which age groups they want to teach (PRE, YOUTH, AMATEUR, PRO)

Example use case:
- Grandmaster has licenses for all 4 age groups
- But only wants to teach PRE and YOUTH in Q3
- Can deactivate AMATEUR and PRO for Q3 period
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class InstructorSpecializationAvailability(Base):
    """
    Tracks instructor availability for specific specializations in specific time periods.

    Key concept: Instructors can choose which specializations to teach in which time periods,
    even if they have licenses for all specializations.
    """
    __tablename__ = "instructor_specialization_availability"

    id = Column(Integer, primary_key=True, index=True)

    # Instructor reference
    instructor_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
                          comment="Instructor who sets this availability preference")

    # Specialization details
    specialization_type = Column(String(50), nullable=False,
                                comment="LFA_PLAYER_PRE, LFA_PLAYER_YOUTH, LFA_PLAYER_AMATEUR, LFA_PLAYER_PRO")

    # Time period (supports both quarterly and monthly)
    # For quarterly: Q1, Q2, Q3, Q4
    # For monthly: M01, M02, M03, ..., M12
    time_period_code = Column(String(10), nullable=False,
                             comment="Q1-Q4 for quarterly, M01-M12 for monthly")

    # Year for the availability
    year = Column(Integer, nullable=False,
                 comment="Year for which this availability applies (e.g., 2025)")

    # Location (instructor can have different availability per location)
    location_city = Column(String(100), nullable=True,
                          comment="City where this availability applies (e.g., Budapest, Budaörs)")

    # Availability status
    is_available = Column(Boolean, nullable=False, default=True,
                         comment="True if instructor is available for this specialization in this time period")

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Notes from instructor
    notes = Column(String(500), nullable=True,
                  comment="Optional notes from instructor about this availability")

    # Relationships
    instructor = relationship("User", foreign_keys=[instructor_id], backref="specialization_availability")

    # Constraints
    __table_args__ = (
        # Prevent duplicate entries for same instructor/specialization/time_period/year/location
        UniqueConstraint(
            'instructor_id', 'specialization_type', 'time_period_code', 'year', 'location_city',
            name='uix_instructor_spec_period_year_location'
        ),
        # Validate time_period_code format (SQLite-compatible LIKE pattern)
        CheckConstraint(
            "(time_period_code LIKE 'Q_' AND time_period_code IN ('Q1', 'Q2', 'Q3', 'Q4')) OR "
            "(time_period_code LIKE 'M__' AND time_period_code >= 'M01' AND time_period_code <= 'M12')",
            name='check_time_period_code_format'
        ),
        # Validate year range
        CheckConstraint(
            "year >= 2024 AND year <= 2100",
            name='check_year_range'
        ),
    )

    def __repr__(self):
        return (f"<InstructorSpecializationAvailability("
                f"instructor_id={self.instructor_id}, "
                f"spec={self.specialization_type}, "
                f"period={self.time_period_code}, "
                f"year={self.year}, "
                f"available={self.is_available})>")
