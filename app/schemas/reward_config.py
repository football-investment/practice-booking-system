"""
Reward Configuration Schemas - Pydantic V2

Pydantic schemas for tournament reward policy configuration.
Defines validation rules for skill mappings, badge configurations, and credit bonuses.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Skill Mapping Schemas
# ============================================================================

class SkillMappingConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Configuration for a single skill mapping"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "skill": "speed",
            "weight": 1.5,
            "category": "PHYSICAL",
            "enabled": True
        }
    })

    skill: str = Field(..., description="Skill name (e.g., 'speed', 'agility')")
    weight: float = Field(default=1.0, ge=0.1, le=5.0, description="Skill weight multiplier")
    category: str = Field(default="PHYSICAL", description="Skill category (PHYSICAL, TECHNICAL, MENTAL)")
    enabled: bool = Field(default=False, description="Whether this skill is active for this tournament - MUST BE EXPLICITLY ENABLED")


# ============================================================================
# Badge Configuration Schemas
# ============================================================================

class BadgeCondition(BaseModel):
    """Conditional badge award logic"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "type": "perfect_score",
            "threshold": None
        }
    })

    type: Literal["first_tournament", "perfect_score", "score_threshold", "always"] = "always"
    threshold: Optional[float] = Field(None, ge=0, le=100, description="Score threshold (for score_threshold type)")


class BadgeConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Configuration for a single badge"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "badge_type": "CHAMPION",
            "icon": "🥇",
            "title": "Champion",
            "description": "Won 1st place in {tournament_name}",
            "rarity": "EPIC",
            "enabled": True,
            "condition": {"type": "always"}
        }
    })

    badge_type: str = Field(..., description="Badge type constant (CHAMPION, RUNNER_UP, etc.)")
    icon: str = Field(default="🏆", description="Badge emoji icon")
    title: str = Field(..., description="Badge title")
    description: Optional[str] = Field(None, description="Badge description template")
    rarity: Literal["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"] = Field(default="COMMON")
    enabled: bool = Field(default=True, description="Whether this badge is active")
    condition: Optional[BadgeCondition] = Field(None, description="Conditional award logic")


class PlacementRewardConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Rewards for a specific placement tier"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "badges": [
                {
                    "badge_type": "CHAMPION",
                    "icon": "🥇",
                    "title": "Champion",
                    "rarity": "EPIC",
                    "enabled": True
                }
            ],
            "credits": 500,
            "xp_multiplier": 1.5
        }
    })

    badges: List[BadgeConfig] = Field(default_factory=list, description="Badges awarded for this placement")
    credits: int = Field(default=0, ge=0, description="Credit bonus for this placement")
    xp_multiplier: float = Field(default=1.0, ge=0.0, le=5.0, description="XP multiplier for this placement")


# ============================================================================
# Main Reward Configuration Schema
# ============================================================================

class TournamentRewardConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """
    Complete reward configuration for a tournament.

    This schema defines:
    - Skill mappings (which skills earn points)
    - Badge configurations (placement-based and conditional)
    - Credit bonuses per placement
    - XP multipliers

    ⚠️ IMPORTANT: Skills must be explicitly enabled per tournament.
    At least 1 skill must be enabled, or validation fails.
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "skill_mappings": [
                {"skill": "speed", "weight": 1.5, "category": "PHYSICAL", "enabled": True},
                {"skill": "agility", "weight": 1.2, "category": "PHYSICAL", "enabled": True}
            ],
            "first_place": {
                "badges": [
                    {
                        "badge_type": "CHAMPION",
                        "icon": "🥇",
                        "title": "Champion",
                        "rarity": "EPIC",
                        "enabled": True
                    }
                ],
                "credits": 500,
                "xp_multiplier": 1.5
            },
            "template_name": "Standard",
            "custom_config": False
        }
    })

    # Skill mappings
    skill_mappings: List[SkillMappingConfig] = Field(
        default_factory=list,
        description="List of skills that earn points in this tournament (at least 1 must be enabled)"
    )

    @property
    def enabled_skills(self) -> List[SkillMappingConfig]:
        """Get list of enabled skills only"""
        return [skill for skill in self.skill_mappings if skill.enabled]

    def validate_enabled_skills(self) -> tuple[bool, str]:
        """
        Validate that at least 1 skill is enabled.

        Returns:
            (is_valid, error_message)
        """
        enabled_count = len(self.enabled_skills)

        if enabled_count == 0:
            return False, "At least 1 skill must be enabled for tournament rewards"

        return True, ""

    # Badge configurations by placement
    first_place: Optional[PlacementRewardConfig] = Field(None, description="Rewards for 1st place")
    second_place: Optional[PlacementRewardConfig] = Field(None, description="Rewards for 2nd place")
    third_place: Optional[PlacementRewardConfig] = Field(None, description="Rewards for 3rd place")
    top_25_percent: Optional[PlacementRewardConfig] = Field(None, description="Rewards for top 25% performers (dynamic)")
    participation: Optional[PlacementRewardConfig] = Field(None, description="Rewards for all participants")

    # Metadata
    template_name: Optional[str] = Field(None, description="Template name if using preset")
    custom_config: bool = Field(default=False, description="Whether this is a custom configuration")


# ============================================================================
# Reward Config Templates (Constants)
# ============================================================================

def create_standard_template() -> TournamentRewardConfig:
    """
    Standard tournament reward template.

    ⚠️ NOTE: All skills start DISABLED by default.
    You MUST explicitly enable the skills relevant to your tournament.
    """
    return TournamentRewardConfig(
        skill_mappings=[
            # Physical skills (all disabled by default - enable what's relevant)
            SkillMappingConfig(skill="speed", weight=1.5, category="PHYSICAL", enabled=False),
            SkillMappingConfig(skill="agility", weight=1.2, category="PHYSICAL", enabled=False),
            SkillMappingConfig(skill="stamina", weight=1.0, category="PHYSICAL", enabled=False),
            SkillMappingConfig(skill="strength", weight=1.3, category="PHYSICAL", enabled=False),
            SkillMappingConfig(skill="jumping", weight=1.0, category="PHYSICAL", enabled=False),
            # Technical skills
            SkillMappingConfig(skill="ball_control", weight=1.2, category="TECHNICAL", enabled=False),
            SkillMappingConfig(skill="passing", weight=1.0, category="TECHNICAL", enabled=False),
            SkillMappingConfig(skill="shooting", weight=1.1, category="TECHNICAL", enabled=False),
            SkillMappingConfig(skill="dribbling", weight=1.2, category="TECHNICAL", enabled=False),
            # Mental skills
            SkillMappingConfig(skill="decision_making", weight=1.0, category="MENTAL", enabled=False),
            SkillMappingConfig(skill="composure", weight=1.0, category="MENTAL", enabled=False),
        ],
        first_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="CHAMPION",
                    icon="🥇",
                    title="Champion",
                    description="Won 1st place in {tournament_name}",
                    rarity="EPIC",
                    enabled=True
                )
            ],
            credits=500,
            xp_multiplier=1.5
        ),
        second_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="RUNNER_UP",
                    icon="🥈",
                    title="Runner-Up",
                    description="Finished 2nd in {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ],
            credits=300,
            xp_multiplier=1.3
        ),
        third_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="THIRD_PLACE",
                    icon="🥉",
                    title="Third Place",
                    description="Secured 3rd place in {tournament_name}",
                    rarity="UNCOMMON",
                    enabled=True
                )
            ],
            credits=200,
            xp_multiplier=1.2
        ),
        top_25_percent=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="TOP_PERFORMER",
                    icon="🌟",
                    title="Top Performer",
                    description="Finished in top 25% of {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ],
            credits=100,
            xp_multiplier=1.1
        ),
        participation=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="TOURNAMENT_DEBUT",
                    icon="⚽",
                    title="Tournament Debut",
                    description="First tournament participation",
                    rarity="COMMON",
                    enabled=True,
                    condition=BadgeCondition(type="first_tournament")
                )
            ],
            credits=50,
            xp_multiplier=1.0
        ),
        template_name="Standard",
        custom_config=False
    )


def create_championship_template() -> TournamentRewardConfig:
    """
    Championship tournament reward template (premium rewards).

    ⚠️ NOTE: All skills start DISABLED by default.
    You MUST explicitly enable the skills relevant to your tournament.
    """
    return TournamentRewardConfig(
        skill_mappings=[
            # Physical skills
            SkillMappingConfig(skill="speed", weight=2.0, category="PHYSICAL", enabled=False),
            SkillMappingConfig(skill="agility", weight=1.8, category="PHYSICAL", enabled=False),
            SkillMappingConfig(skill="stamina", weight=1.5, category="PHYSICAL", enabled=False),
            SkillMappingConfig(skill="strength", weight=1.7, category="PHYSICAL", enabled=False),
            # Technical skills
            SkillMappingConfig(skill="ball_control", weight=1.5, category="TECHNICAL", enabled=False),
            SkillMappingConfig(skill="passing", weight=1.3, category="TECHNICAL", enabled=False),
            SkillMappingConfig(skill="shooting", weight=1.4, category="TECHNICAL", enabled=False),
            # Mental skills
            SkillMappingConfig(skill="decision_making", weight=1.2, category="MENTAL", enabled=False),
        ],
        first_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="CHAMPION",
                    icon="🥇",
                    title="Champion",
                    description="Won {tournament_name}",
                    rarity="LEGENDARY",
                    enabled=True
                ),
                BadgeConfig(
                    badge_type="PERFECT_SCORE",
                    icon="💯",
                    title="Perfect Score",
                    description="Achieved perfect score in {tournament_name}",
                    rarity="LEGENDARY",
                    enabled=True,
                    condition=BadgeCondition(type="perfect_score")
                )
            ],
            credits=1000,
            xp_multiplier=2.0
        ),
        second_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="RUNNER_UP",
                    icon="🥈",
                    title="Runner-Up",
                    description="Finished 2nd in {tournament_name}",
                    rarity="EPIC",
                    enabled=True
                )
            ],
            credits=600,
            xp_multiplier=1.5
        ),
        third_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="THIRD_PLACE",
                    icon="🥉",
                    title="Third Place",
                    description="Secured 3rd place in {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ],
            credits=400,
            xp_multiplier=1.3
        ),
        top_25_percent=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="TOP_PERFORMER",
                    icon="🌟",
                    title="Top Performer",
                    description="Elite performance in {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ],
            credits=200,
            xp_multiplier=1.2
        ),
        participation=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="PARTICIPANT",
                    icon="⚽",
                    title="Championship Participant",
                    description="Participated in {tournament_name}",
                    rarity="COMMON",
                    enabled=True
                )
            ],
            credits=100,
            xp_multiplier=1.0
        ),
        template_name="Championship",
        custom_config=False
    )


def create_friendly_template() -> TournamentRewardConfig:
    """
    Friendly tournament reward template (reduced rewards).

    ⚠️ NOTE: All skills start DISABLED by default.
    You MUST explicitly enable the skills relevant to your tournament.
    """
    return TournamentRewardConfig(
        skill_mappings=[
            # Physical skills
            SkillMappingConfig(skill="speed", weight=1.0, category="PHYSICAL", enabled=False),
            SkillMappingConfig(skill="agility", weight=1.0, category="PHYSICAL", enabled=False),
            SkillMappingConfig(skill="stamina", weight=1.0, category="PHYSICAL", enabled=False),
            # Technical skills
            SkillMappingConfig(skill="ball_control", weight=1.0, category="TECHNICAL", enabled=False),
            SkillMappingConfig(skill="passing", weight=1.0, category="TECHNICAL", enabled=False),
        ],
        first_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="WINNER",
                    icon="🏆",
                    title="Winner",
                    description="Won {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ],
            credits=200,
            xp_multiplier=1.2
        ),
        second_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="RUNNER_UP",
                    icon="🥈",
                    title="Runner-Up",
                    description="Finished 2nd in {tournament_name}",
                    rarity="UNCOMMON",
                    enabled=True
                )
            ],
            credits=100,
            xp_multiplier=1.1
        ),
        third_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="THIRD_PLACE",
                    icon="🥉",
                    title="Third Place",
                    description="Secured 3rd place in {tournament_name}",
                    rarity="UNCOMMON",
                    enabled=True
                )
            ],
            credits=50,
            xp_multiplier=1.0
        ),
        participation=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="PARTICIPANT",
                    icon="⚽",
                    title="Participant",
                    description="Participated in {tournament_name}",
                    rarity="COMMON",
                    enabled=True
                )
            ],
            credits=25,
            xp_multiplier=1.0
        ),
        template_name="Friendly",
        custom_config=False
    )


# Pre-create templates
REWARD_CONFIG_TEMPLATES = {
    "STANDARD": create_standard_template(),
    "CHAMPIONSHIP": create_championship_template(),
    "FRIENDLY": create_friendly_template()
}
