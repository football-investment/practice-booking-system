from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey, Table, Enum, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from ..database import Base


class SemesterStatus(str, enum.Enum):
    """Semester lifecycle phases"""
    DRAFT = "DRAFT"  # Admin created, no instructor, no sessions
    SEEKING_INSTRUCTOR = "SEEKING_INSTRUCTOR"  # Admin looking for instructor
    INSTRUCTOR_ASSIGNED = "INSTRUCTOR_ASSIGNED"  # Has instructor, no sessions yet
    READY_FOR_ENROLLMENT = "READY_FOR_ENROLLMENT"  # Has instructor + sessions, students can enroll
    ONGOING = "ONGOING"  # Past enrollment deadline, classes in progress
    COMPLETED = "COMPLETED"  # All sessions finished
    CANCELLED = "CANCELLED"  # Admin cancelled


# Many-to-many association table for additional instructors
semester_instructors = Table(
    'semester_instructors',
    Base.metadata,
    Column('semester_id', Integer, ForeignKey('semesters.id', ondelete='CASCADE'), primary_key=True),
    Column('instructor_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
)


class Semester(Base):
    __tablename__ = "semesters"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # "2024/1"
    name = Column(String, nullable=False)  # "2024/25 őszi félév"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Lifecycle status (new, preferred)
    status = Column(Enum(SemesterStatus, name='semester_status'), nullable=False, default=SemesterStatus.DRAFT, index=True,
                   comment="Current lifecycle phase of the semester")

    # Tournament-specific status (for tournament lifecycle)
    tournament_status = Column(String(50), nullable=True, index=True,
                              comment="Tournament-specific status: DRAFT, SEEKING_INSTRUCTOR, READY_FOR_ENROLLMENT, etc.")

    # DEPRECATED: Use 'status' instead
    is_active = Column(Boolean, default=True,
                      comment="DEPRECATED: Use status field instead. Kept for backward compatibility.")

    # 💰 CREDIT SYSTEM: Enrollment cost for this semester
    enrollment_cost = Column(Integer, nullable=False, default=500,
                            comment="Credit cost to enroll in this semester (admin adjustable)")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 🥋 Master Instructor (Grandmaster who approves enrollments)
    master_instructor_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
                                  comment="Master instructor who approves enrollment requests for this semester")

    # 🎯 SPECIALIZATION & AGE GROUP FIELDS (for semester filtering)
    specialization_type = Column(String(50), nullable=True, index=True,
                                 comment="Specialization type (SEASON types: LFA_PLAYER_PRE/YOUTH/AMATEUR/PRO, GANCUJU_PLAYER, LFA_COACH, INTERNSHIP, OR user license for tournaments: LFA_FOOTBALL_PLAYER)")
    age_group = Column(String(20), nullable=True, index=True,
                      comment="Age group (PRE, YOUTH, AMATEUR, PRO)")
    theme = Column(String(200), nullable=True,
                  comment="Marketing theme (e.g., 'New Year Challenge', 'Q1', 'Fall')")
    focus_description = Column(String(500), nullable=True,
                              comment="Focus description (e.g., 'Újévi fogadalmak, friss kezdés')")

    # 📍 LOCATION FIELDS (for semester-level location)
    # NEW: Use campus_id FK for most specific location
    campus_id = Column(Integer, ForeignKey('campuses.id', ondelete='SET NULL'), nullable=True, index=True,
                      comment="FK to campuses table (most specific location - preferred)")

    # Use location_id FK instead of denormalized city/venue/address fields
    location_id = Column(Integer, ForeignKey('locations.id', ondelete='SET NULL'), nullable=True, index=True,
                        comment="FK to locations table (less specific than campus_id, preferred over legacy location_city/venue/address)")

    # DEPRECATED: Legacy location fields - kept for backward compatibility
    location_city = Column(String(100), nullable=True,
                          comment="DEPRECATED: Use campus_id or location_id instead. City where semester takes place")
    location_venue = Column(String(200), nullable=True,
                           comment="DEPRECATED: Use campus_id or location_id instead. Venue/campus name")
    location_address = Column(String(500), nullable=True,
                             comment="DEPRECATED: Use campus_id or location_id instead. Full address")

    # 🏆 TOURNAMENT FIELDS (new tournament system)
    # NEW: FK to tournament_types table (preferred for auto-generation)
    tournament_type_id = Column(Integer, ForeignKey('tournament_types.id', ondelete='SET NULL'), nullable=True,
                                comment="FK to tournament_types table (for auto-generating session structure)")

    # DEPRECATED: Legacy tournament_type string field - kept for backward compatibility
    tournament_type = Column(String(50), nullable=True,
                            comment="DEPRECATED: Use tournament_type_id instead. Tournament format: LEAGUE, KNOCKOUT, ROUND_ROBIN, CUSTOM")

    participant_type = Column(String(50), nullable=True, default="INDIVIDUAL",
                             comment="Participant type: INDIVIDUAL, TEAM, MIXED")
    is_multi_day = Column(Boolean, default=False,
                         comment="True if tournament spans multiple days")

    # 🔄 SESSION GENERATION TRACKING
    sessions_generated = Column(Boolean, default=False, nullable=False,
                               comment="True if tournament sessions have been auto-generated (prevents duplicate generation)")
    sessions_generated_at = Column(DateTime, nullable=True,
                                  comment="Timestamp when sessions were auto-generated")
    enrollment_snapshot = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True,
                                comment="📸 Snapshot of enrollment state before session generation (for regeneration if needed)")

    # ⏱️ TOURNAMENT SCHEDULE CONFIGURATION (set by admin before session generation)
    match_duration_minutes = Column(Integer, nullable=True,
                                   comment="Duration of each match in minutes (overrides tournament_type default)")
    break_duration_minutes = Column(Integer, nullable=True,
                                  comment="Break time between matches in minutes (overrides tournament_type default)")
    parallel_fields = Column(Integer, nullable=True, default=1,
                            comment="Number of parallel fields/pitches available (1-4) for simultaneous matches")
    format = Column(String(50), nullable=False, default="INDIVIDUAL_RANKING",
                   comment="Tournament format: HEAD_TO_HEAD (1v1 with scores) or INDIVIDUAL_RANKING (placement-based). Overrides tournament_type default.")
    scoring_type = Column(String(50), nullable=False, default="PLACEMENT",
                         comment="Scoring type for INDIVIDUAL_RANKING: TIME_BASED, DISTANCE_BASED, SCORE_BASED, PLACEMENT. Ignored for HEAD_TO_HEAD.")

    # 🎯 TOURNAMENT ASSIGNMENT & CAPACITY (explicit business attributes)
    assignment_type = Column(String(30), nullable=True,
                            comment="Tournament instructor assignment strategy: OPEN_ASSIGNMENT (admin assigns directly) or APPLICATION_BASED (instructors apply)")
    max_players = Column(Integer, nullable=True,
                        comment="Maximum tournament participants (explicit capacity, independent of session capacity sum)")

    # 🎁 REWARD POLICY FIELDS (tournament reward system)
    reward_policy_name = Column(String(100), nullable=False, default="default",
                                comment="Name of the reward policy applied to this tournament semester")
    reward_policy_snapshot = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True,
                                    comment="Immutable snapshot of the reward policy at tournament creation time")

    # Relationships
    campus = relationship("Campus", foreign_keys=[campus_id],
                         backref="semesters",
                         doc="Campus where this semester takes place (most specific)")
    location = relationship("Location", foreign_keys=[location_id],
                           backref="semesters",
                           doc="Location where this semester takes place")
    master_instructor = relationship("User", foreign_keys=[master_instructor_id],
                                    backref="mastered_semesters")
    assistant_instructors = relationship("User", secondary=semester_instructors,
                                        backref="assisted_semesters")
    tournament_type_config = relationship("TournamentType", foreign_keys=[tournament_type_id],
                                         back_populates="semesters",
                                         doc="Tournament type configuration (for auto-generating sessions)")
    groups = relationship("Group", back_populates="semester")
    sessions = relationship("Session", back_populates="semester")
    projects = relationship("Project", back_populates="semester")
    enrollments = relationship("SemesterEnrollment", back_populates="semester", cascade="all, delete-orphan")

    def validate_tournament_format_logic(self):
        """
        Validate tournament format and type consistency:
        - INDIVIDUAL_RANKING: tournament_type_id MUST be NULL (no structure needed)
        - HEAD_TO_HEAD: tournament_type_id MUST be set (Swiss, League, Knockout, etc.)
        """
        if self.format == "INDIVIDUAL_RANKING":
            if self.tournament_type_id is not None:
                raise ValueError(
                    "INDIVIDUAL_RANKING tournaments cannot have a tournament_type. "
                    "INDIVIDUAL_RANKING is a simple competition format where all players compete "
                    "and are ranked by their results (time, score, distance, or placement). "
                    "Set tournament_type_id to NULL."
                )
        elif self.format == "HEAD_TO_HEAD":
            if self.tournament_type_id is None:
                raise ValueError(
                    "HEAD_TO_HEAD tournaments MUST have a tournament_type (Swiss, Round Robin, Knockout, etc.). "
                    "Tournament type defines how 1v1 matches are structured and scheduled."
                )
        else:
            raise ValueError(f"Invalid format: {self.format}. Must be 'INDIVIDUAL_RANKING' or 'HEAD_TO_HEAD'.")