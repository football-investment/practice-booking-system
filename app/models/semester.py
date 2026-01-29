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


    # 🏆 TOURNAMENT FIELDS (new tournament system)
    # NEW: FK to tournament_types table (preferred for auto-generation)
    tournament_type_id = Column(Integer, ForeignKey('tournament_types.id', ondelete='SET NULL'), nullable=True,
                                comment="FK to tournament_types table (for auto-generating session structure)")


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
    scoring_type = Column(String(50), nullable=False, default="PLACEMENT",
                         comment="Scoring type for INDIVIDUAL_RANKING: TIME_BASED, DISTANCE_BASED, SCORE_BASED, PLACEMENT. Ignored for HEAD_TO_HEAD.")
    measurement_unit = Column(String(50), nullable=True,
                             comment="Unit of measurement for INDIVIDUAL_RANKING results: seconds/minutes (TIME_BASED), meters/centimeters (DISTANCE_BASED), points/repetitions (SCORE_BASED). NULL for PLACEMENT or HEAD_TO_HEAD.")
    ranking_direction = Column(String(10), nullable=True,
                               comment="Ranking direction for INDIVIDUAL_RANKING: ASC (lowest wins, e.g. 100m sprint), DESC (highest wins, e.g. plank). HEAD_TO_HEAD always DESC. NULL for PLACEMENT.")
    number_of_rounds = Column(Integer, nullable=True, default=1,
                             comment="Number of rounds for INDIVIDUAL_RANKING tournaments (1-10). Each round is a separate session. HEAD_TO_HEAD ignores this.")

    # 🎯 TOURNAMENT ASSIGNMENT & CAPACITY (explicit business attributes)
    assignment_type = Column(String(30), nullable=True,
                            comment="Tournament instructor assignment strategy: OPEN_ASSIGNMENT (admin assigns directly) or APPLICATION_BASED (instructors apply)")
    max_players = Column(Integer, nullable=True,
                        comment="Maximum tournament participants (explicit capacity, independent of session capacity sum)")

    # 🎁 REWARD POLICY FIELDS (tournament reward system)
    # ⚠️ DEPRECATED in P1: reward_config moved to separate table (tournament_reward_configs)
    # Use reward_config_obj relationship instead
    # reward_config @property provides backward compatibility

    # 🎮 GAME CONFIGURATION FIELDS (tournament simulation rules)
    game_preset_id = Column(Integer, ForeignKey("game_presets.id", name="fk_semesters_game_preset"),
                           nullable=True, index=True,
                           comment="Reference to pre-configured game type (e.g., GanFootvolley, Stole My Goal). Preset defines default skills, weights, and match rules.")

    game_config = Column(JSONB, nullable=True,
                        comment="Merged game configuration (preset + overrides). Final configuration used for tournament simulation. Includes match probabilities, ranking rules, skill weights, and simulation options.")

    game_config_overrides = Column(JSONB, nullable=True, index=True,
                                   comment="Custom overrides applied to preset configuration. Tracks what was customized from the base preset. NULL if using preset defaults.")

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
    game_preset = relationship("GamePreset", foreign_keys=[game_preset_id],
                              back_populates="semesters",
                              doc="Pre-configured game type defining skills, weights, and match rules")
    groups = relationship("Group", back_populates="semester")
    sessions = relationship("Session", back_populates="semester")
    projects = relationship("Project", back_populates="semester")
    enrollments = relationship("SemesterEnrollment", back_populates="semester", cascade="all, delete-orphan")

    # 🏆 Tournament participation & badge relationships
    skill_mappings = relationship("TournamentSkillMapping", back_populates="tournament", cascade="all, delete-orphan")
    participations = relationship("TournamentParticipation", back_populates="tournament", cascade="all, delete-orphan")
    badges = relationship("TournamentBadge", back_populates="tournament", cascade="all, delete-orphan")

    # 🎁 Reward configuration (P1: separate table)
    reward_config_obj = relationship(
        "TournamentRewardConfig",
        uselist=False,
        back_populates="tournament",
        cascade="all, delete-orphan",
        doc="Reward configuration for this tournament (1:1 relationship)"
    )

    @property
    def format(self) -> str:
        """
        Derive tournament format from tournament_type.format (single source of truth).

        Priority:
        1. tournament_type.format (if tournament_type_id is set)
        2. game_preset's format_config (if game_preset_id is set)
        3. Default: INDIVIDUAL_RANKING

        Returns:
            str: Either "HEAD_TO_HEAD" or "INDIVIDUAL_RANKING"
        """
        # Priority 1: tournament_type.format (preferred)
        if self.tournament_type_id and self.tournament_type_config:
            return self.tournament_type_config.format

        # Priority 2: game_preset's format_config
        if self.game_preset_id and self.game_preset:
            format_config = self.game_preset.game_config.get('format_config', {})
            if format_config:
                # format_config is a dict with format as key: {"HEAD_TO_HEAD": {...}} or {"INDIVIDUAL_RANKING": {...}}
                return list(format_config.keys())[0]

        # Priority 3: Default
        return "INDIVIDUAL_RANKING"

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

    # ========================================================================
    # 🎁 P1 REFACTORING: BACKWARD COMPATIBILITY PROPERTIES
    # ========================================================================

    @property
    def reward_config(self) -> dict:
        """
        Backward compatible property for reward_config.

        🔄 P1 Refactoring: reward_config moved to separate table.
        This property provides transparent access to the new structure.

        Returns:
            Dict: Reward configuration (TournamentRewardConfig schema)
        """
        if self.reward_config_obj:
            return self.reward_config_obj.reward_config or {}
        return {}

    @property
    def reward_policy_name(self) -> str:
        """
        Backward compatible property for reward_policy_name.

        Returns:
            str: Reward policy name (default: "default")
        """
        if self.reward_config_obj:
            return self.reward_config_obj.reward_policy_name
        return "default"

    @property
    def reward_policy_snapshot(self) -> dict:
        """
        Backward compatible property for reward_policy_snapshot.

        Returns:
            Dict: Reward policy snapshot (or empty dict)
        """
        if self.reward_config_obj:
            return self.reward_config_obj.reward_policy_snapshot or {}
        return {}