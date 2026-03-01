"""
Skill Progression Configuration

Centralized configuration for skill progression system.
Can be overridden per-tournament via reward_config.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SkillProgressionConfig(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={
            "example": {
                "tournament_delta_multiplier": 0.125,
                "tournament_max_contribution": 15.0,
                "assessment_delta_multiplier": 0.20,
                "assessment_max_contribution": 10.0,
                "max_skill_level": 100.0,
                "min_skill_level": 0.0,
                "decay_enabled": False,
                "decay_threshold_days": 30,
                "decay_max_percentage": 0.20,
                "decay_curve_steepness": 0.5
            }
        }
    )

    """
    Skill progression configuration model.

    This configuration controls how skill points are converted to deltas
    and how caps are applied.
    """

    # === Tournament Configuration ===
    tournament_delta_multiplier: float = Field(
        default=0.125,
        ge=0.05,
        le=0.30,
        description="Multiplier for tournament skill points (default: 0.125 = 12.5%)"
    )
    tournament_max_contribution: float = Field(
        default=15.0,
        ge=5.0,
        le=30.0,
        description="Maximum skill points from tournaments per skill (default: +15)"
    )

    # === Assessment Configuration ===
    assessment_delta_multiplier: float = Field(
        default=0.20,
        ge=0.10,
        le=0.50,
        description="Multiplier for assessment skill points (default: 0.20 = 20%)"
    )
    assessment_max_contribution: float = Field(
        default=10.0,
        ge=5.0,
        le=20.0,
        description="Maximum skill points from assessments per skill (default: +10)"
    )

    # === Overall Limits ===
    max_skill_level: float = Field(
        default=100.0,
        description="Absolute maximum skill level (default: 100)"
    )
    min_skill_level: float = Field(
        default=0.0,
        description="Absolute minimum skill level (default: 0)"
    )

    # === Decay Configuration ===
    decay_enabled: bool = Field(
        default=False,
        description="Enable time-based skill decay (default: False)"
    )
    decay_threshold_days: int = Field(
        default=30,
        ge=7,
        le=90,
        description="Days of inactivity before decay starts (default: 30)"
    )
    decay_max_percentage: float = Field(
        default=0.20,
        ge=0.05,
        le=0.50,
        description="Maximum percentage of deltas that can decay (default: 0.20 = 20%)"
    )
    decay_curve_steepness: float = Field(
        default=0.5,
        ge=0.1,
        le=2.0,
        description="Steepness of decay curve (k parameter, default: 0.5)"
    )
        }


# === Global Default Configuration ===
DEFAULT_SKILL_PROGRESSION_CONFIG = SkillProgressionConfig()


# === Predefined Tournament Templates ===
TOURNAMENT_CONFIG_TEMPLATES = {
    "SPEED_FOCUS": SkillProgressionConfig(
        tournament_delta_multiplier=0.15,  # Higher multiplier for speed tournaments
        tournament_max_contribution=20.0,  # Higher cap
        assessment_delta_multiplier=0.20,
        assessment_max_contribution=10.0
    ),
    "TECHNICAL_FOCUS": SkillProgressionConfig(
        tournament_delta_multiplier=0.10,  # Lower multiplier (harder to improve technical)
        tournament_max_contribution=12.0,  # Lower cap
        assessment_delta_multiplier=0.25,  # Assessments more important for technical
        assessment_max_contribution=15.0
    ),
    "BALANCED": SkillProgressionConfig(
        tournament_delta_multiplier=0.125,
        tournament_max_contribution=15.0,
        assessment_delta_multiplier=0.20,
        assessment_max_contribution=10.0
    ),
    "HIGH_STAKES": SkillProgressionConfig(
        tournament_delta_multiplier=0.18,  # Championship tournaments
        tournament_max_contribution=25.0,
        assessment_delta_multiplier=0.20,
        assessment_max_contribution=10.0
    ),
    "LEARNING": SkillProgressionConfig(
        tournament_delta_multiplier=0.08,  # Beginner-friendly
        tournament_max_contribution=10.0,
        assessment_delta_multiplier=0.30,  # Emphasis on instructor feedback
        assessment_max_contribution=15.0
    )
}


def get_tournament_config(
    tournament_type: Optional[str] = None,
    custom_config: Optional[dict] = None
) -> SkillProgressionConfig:
    """
    Get skill progression config for a tournament.

    Args:
        tournament_type: Predefined template name (SPEED_FOCUS, TECHNICAL_FOCUS, etc.)
        custom_config: Custom config dict to override defaults

    Returns:
        SkillProgressionConfig instance

    Example:
        # Use template
        config = get_tournament_config(tournament_type="SPEED_FOCUS")

        # Custom override
        config = get_tournament_config(custom_config={
            "tournament_delta_multiplier": 0.15,
            "tournament_max_contribution": 18.0)
    """
    # Start with default
    if tournament_type and tournament_type in TOURNAMENT_CONFIG_TEMPLATES:
        config = TOURNAMENT_CONFIG_TEMPLATES[tournament_type].model_copy()
    else:
        config = DEFAULT_SKILL_PROGRESSION_CONFIG.model_copy()

    # Apply custom overrides
    if custom_config:
        for key, value in custom_config.items():
            if hasattr(config, key):
                setattr(config, key, value)

    return config
