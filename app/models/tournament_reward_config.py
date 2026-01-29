"""
Tournament Reward Configuration Model

Separate table for tournament reward policies (P1 refactoring).
Extracted from Semester model to achieve clean separation of concerns.

Architecture:
- Tournament Information: Semester (location, dates, theme)
- Tournament Configuration: Semester (type, max_players, etc.)
- Game Configuration: game_config, game_preset_id (skills, weights, match rules)
- Reward Configuration: TournamentRewardConfig (THIS TABLE - badges, XP, credits)
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ..database import Base


class TournamentRewardConfig(Base):
    """
    Reward configuration for tournament (separate entity from Semester).

    🎁 Manages reward policies:
    - Skill mappings (which skills earn points, weights, placement bonuses)
    - Badge configurations (placement-based and conditional)
    - Credit bonuses per placement
    - XP multipliers

    ✅ Benefits of separation:
    - Auditability: Track reward changes over time
    - Reusability: Same reward policy can be shared across tournaments (future)
    - Clarity: Reward logic isolated from tournament configuration

    Schema follows TournamentRewardConfig (app/schemas/reward_config.py)
    """
    __tablename__ = "tournament_reward_configs"

    id = Column(Integer, primary_key=True, index=True)

    # FK to semester (tournament)
    semester_id = Column(
        Integer,
        ForeignKey('semesters.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
        index=True,
        comment="Tournament this reward config belongs to (1:1 relationship)"
    )

    # Reward policy metadata
    reward_policy_name = Column(
        String(100),
        nullable=False,
        default="default",
        comment="Name of the reward policy (Standard, Championship, Friendly, Custom)"
    )

    # Immutable snapshot of the reward policy at tournament creation
    reward_policy_snapshot = Column(
        JSONB,
        nullable=True,
        comment="Immutable snapshot of the reward policy at tournament creation time"
    )

    # Detailed reward configuration (JSONB)
    # Structure: TournamentRewardConfig schema from app/schemas/reward_config.py
    reward_config = Column(
        JSONB,
        nullable=True,
        comment="""Detailed reward configuration:
        - skill_mappings: List of skills with weights, categories, enabled flags
        - first_place, second_place, third_place: Placement-based rewards (badges, credits, XP)
        - top_25_percent: Dynamic rewards for top performers
        - participation: Participation rewards (badges, credits, XP)
        - template_name: Template name if using preset
        - custom_config: Whether this is a custom configuration
        """
    )

    # Audit timestamps
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When this reward config was created"
    )

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When this reward config was last updated"
    )

    # Relationships
    tournament = relationship(
        "Semester",
        back_populates="reward_config_obj",
        doc="Tournament this reward config belongs to"
    )

    def __repr__(self):
        return (
            f"<TournamentRewardConfig(id={self.id}, "
            f"semester_id={self.semester_id}, "
            f"policy={self.reward_policy_name})>"
        )
