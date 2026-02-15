"""
CampusScheduleConfig Model

Per-campus schedule configuration for multi-venue tournaments.

Architecture:
  Tournament → TournamentConfiguration (global defaults)
             → CampusScheduleConfig (per-campus overrides, keyed by campus_id)

Each campus running a tournament can independently specify:
  - match_duration_minutes  (how long each match lasts)
  - break_duration_minutes  (rest between matches)
  - parallel_fields         (how many pitches/courts are available simultaneously)
  - venue_label             (optional human-readable label for the venue in this tournament)

Precedence (highest → lowest):
  1. CampusScheduleConfig for this (tournament, campus) pair
  2. TournamentConfiguration global defaults
  3. Request-level parameters
  4. TournamentType hardcoded defaults
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ..database import Base


class CampusScheduleConfig(Base):
    """
    Per-campus schedule override for a specific tournament.

    One row per (tournament_id, campus_id) pair.
    """
    __tablename__ = "campus_schedule_configs"

    __table_args__ = (
        UniqueConstraint(
            "tournament_id", "campus_id",
            name="uq_campus_schedule_tournament_campus"
        ),
        CheckConstraint("match_duration_minutes >= 1", name="ck_csc_match_duration_min"),
        CheckConstraint("match_duration_minutes <= 480", name="ck_csc_match_duration_max"),
        CheckConstraint("break_duration_minutes >= 0", name="ck_csc_break_duration_min"),
        CheckConstraint("break_duration_minutes <= 120", name="ck_csc_break_duration_max"),
        CheckConstraint("parallel_fields >= 1", name="ck_csc_parallel_fields_min"),
        CheckConstraint("parallel_fields <= 20", name="ck_csc_parallel_fields_max"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Tournament this config belongs to (FK to semesters)
    tournament_id = Column(
        Integer,
        ForeignKey("semesters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tournament (Semester) this campus schedule config belongs to"
    )

    # Campus this config applies to
    campus_id = Column(
        Integer,
        ForeignKey("campuses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Campus this schedule config applies to"
    )

    # ── Schedule parameters (all nullable = use global TournamentConfiguration defaults) ──

    match_duration_minutes = Column(
        Integer,
        nullable=True,
        comment=(
            "Duration of each match in minutes for this campus. "
            "NULL = use TournamentConfiguration.match_duration_minutes global default."
        )
    )

    break_duration_minutes = Column(
        Integer,
        nullable=True,
        comment=(
            "Break between matches in minutes for this campus. "
            "NULL = use TournamentConfiguration.break_duration_minutes global default."
        )
    )

    parallel_fields = Column(
        Integer,
        nullable=True,
        comment=(
            "Number of parallel pitches/courts at this campus. "
            "NULL = use TournamentConfiguration.parallel_fields global default."
        )
    )

    # Optional label shown in session titles for this venue
    venue_label = Column(
        String(100),
        nullable=True,
        comment="Human-readable venue label for this campus in this tournament (e.g. 'North Pitch', 'Hall B')"
    )

    # Whether this campus is active for session generation
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="If False, sessions will not be generated for this campus"
    )

    # Audit
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    tournament = relationship(
        "Semester",
        foreign_keys=[tournament_id],
        doc="Tournament this config belongs to"
    )
    campus = relationship(
        "Campus",
        foreign_keys=[campus_id],
        doc="Campus this config applies to"
    )

    def resolved_match_duration(self, global_default: int = 90) -> int:
        """Return effective match duration: campus-level override or global default."""
        return self.match_duration_minutes if self.match_duration_minutes is not None else global_default

    def resolved_break_duration(self, global_default: int = 15) -> int:
        """Return effective break duration: campus-level override or global default."""
        return self.break_duration_minutes if self.break_duration_minutes is not None else global_default

    def resolved_parallel_fields(self, global_default: int = 1) -> int:
        """Return effective parallel fields: campus-level override or global default."""
        return self.parallel_fields if self.parallel_fields is not None else global_default

    def __repr__(self) -> str:
        return (
            f"<CampusScheduleConfig("
            f"tournament_id={self.tournament_id}, "
            f"campus_id={self.campus_id}, "
            f"match_duration={self.match_duration_minutes}, "
            f"parallel_fields={self.parallel_fields})>"
        )
