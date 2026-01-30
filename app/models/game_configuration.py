"""
Game Configuration Model

Separate table for game configuration (P3 refactoring).
Extracted from Semester model to achieve clean separation of concerns.

Architecture:
- Tournament Information: Semester (location, dates, theme, status)
- Tournament Configuration: TournamentConfiguration (type, schedule, scoring)
- Game Configuration: GameConfiguration (THIS TABLE - skills, weights, match rules, simulation)
- Reward Configuration: TournamentRewardConfig (badges, XP, credits)
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ..database import Base


class GameConfiguration(Base):
    """
    Game configuration for tournament simulation (separate entity from Semester).

    🎮 Manages game-specific settings:
    - Game preset reference (template configuration)
    - Merged game config (preset + overrides)
    - Custom overrides (what was customized from preset)

    ✅ Benefits of separation:
    - Clarity: Game simulation logic isolated from tournament information
    - Auditability: Track game config changes over time
    - Flexibility: Game config can be changed without affecting tournament info
    - Reusability: Future - share game configurations across tournaments

    Schema follows the configuration layer design from TOURNAMENT_ARCHITECTURE_AUDIT.md
    """
    __tablename__ = "game_configurations"

    id = Column(Integer, primary_key=True, index=True)

    # FK to semester (tournament)
    semester_id = Column(
        Integer,
        ForeignKey('semesters.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
        index=True,
        comment="Tournament this game configuration belongs to (1:1 relationship)"
    )

    # Game Preset Reference
    game_preset_id = Column(
        Integer,
        ForeignKey("game_presets.id", ondelete='SET NULL'),
        nullable=True,
        index=True,
        comment="Reference to pre-configured game type (e.g., GanFootvolley, Stole My Goal). Preset defines default skills, weights, and match rules."
    )

    # Merged Game Configuration
    game_config = Column(
        JSONB,
        nullable=True,
        comment="Merged game configuration (preset + overrides). Final configuration used for tournament simulation. Includes match probabilities, ranking rules, skill weights, and simulation options."
    )

    # Custom Overrides
    game_config_overrides = Column(
        JSONB,
        nullable=True,
        comment="Custom overrides applied to preset configuration. Tracks what was customized from the base preset. NULL if using preset defaults."
    )

    # Audit timestamps
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When this game configuration was created"
    )

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When this game configuration was last updated"
    )

    # Relationships
    tournament = relationship(
        "Semester",
        back_populates="game_config_obj",
        doc="Tournament this game configuration belongs to"
    )

    game_preset = relationship(
        "GamePreset",
        foreign_keys=[game_preset_id],
        doc="Pre-configured game type template"
    )

    def __repr__(self):
        return (
            f"<GameConfiguration(id={self.id}, "
            f"semester_id={self.semester_id}, "
            f"preset_id={self.game_preset_id})>"
        )
