"""
Tournament Rewards DTOs

Unified data transfer objects for tournament reward distribution.
Used across API endpoints and UI components.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# PARTICIPATION (Skill/XP) DTOs
# ============================================================================

class SkillPointsAwarded(BaseModel):
    """Skill points awarded from tournament participation"""
    skill_name: str
    points: float
    skill_category: Optional[str] = None

    class Config:
        from_attributes = True


class ParticipationReward(BaseModel):
    """Tournament participation rewards (DATA layer)"""
    user_id: int
    placement: Optional[int] = None
    skill_points: List[SkillPointsAwarded] = Field(default_factory=list)
    base_xp: int
    bonus_xp: int  # From skill points conversion
    total_xp: int
    credits: int

    class Config:
        from_attributes = True


# ============================================================================
# BADGE (Visual Achievement) DTOs
# ============================================================================

class BadgeAwarded(BaseModel):
    """Visual tournament badge awarded"""
    badge_type: str
    badge_category: str
    title: str
    description: str
    icon: str
    rarity: str
    metadata: Optional[Dict] = None

    class Config:
        from_attributes = True


class BadgeReward(BaseModel):
    """Tournament badge rewards (UI layer)"""
    user_id: int
    badges: List[BadgeAwarded] = Field(default_factory=list)
    total_badges_earned: int
    rarest_badge: Optional[str] = None  # Rarity level of rarest badge

    class Config:
        from_attributes = True


# ============================================================================
# UNIFIED REWARD RESULT
# ============================================================================

class TournamentRewardResult(BaseModel):
    """
    Unified tournament reward result.

    Combines both participation rewards (skill/XP) and visual badges.
    Used as single response object for reward distribution.
    """
    user_id: int
    tournament_id: int
    tournament_name: str

    # Participation rewards (DATA layer)
    participation: ParticipationReward

    # Badge rewards (UI layer)
    badges: BadgeReward

    # Metadata
    distributed_at: datetime
    distributed_by: Optional[int] = None  # Admin/instructor ID

    class Config:
        from_attributes = True

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "user_id": self.user_id,
            "tournament_id": self.tournament_id,
            "tournament_name": self.tournament_name,
            "participation": {
                "placement": self.participation.placement,
                "skill_points": [
                    {"skill_name": sp.skill_name, "points": sp.points, "category": sp.skill_category}
                    for sp in self.participation.skill_points
                ],
                "base_xp": self.participation.base_xp,
                "bonus_xp": self.participation.bonus_xp,
                "total_xp": self.participation.total_xp,
                "credits": self.participation.credits
            },
            "badges": {
                "badges": [
                    {
                        "type": b.badge_type,
                        "category": b.badge_category,
                        "title": b.title,
                        "description": b.description,
                        "icon": b.icon,
                        "rarity": b.rarity,
                        "metadata": b.metadata
                    }
                    for b in self.badges.badges
                ],
                "total_badges_earned": self.badges.total_badges_earned,
                "rarest_badge": self.badges.rarest_badge
            },
            "distributed_at": self.distributed_at.isoformat(),
            "distributed_by": self.distributed_by
        }


class BulkRewardDistributionResult(BaseModel):
    """Result of bulk reward distribution for entire tournament"""
    tournament_id: int
    tournament_name: str
    total_participants: int
    rewards_distributed: List[TournamentRewardResult]
    distribution_summary: Dict = Field(default_factory=dict)
    distributed_at: datetime
    distributed_by: Optional[int] = None

    class Config:
        from_attributes = True


# ============================================================================
# BADGE RULE ARCHITECTURE (Future Extensibility)
# ============================================================================

class BadgeCondition(BaseModel):
    """
    Base condition for badge awarding.

    Future extension point for complex badge logic.
    Examples:
    - PlacementCondition: placement <= 3
    - WinStreakCondition: consecutive_wins >= 3
    - PerformanceCondition: improvement_percentage > 50
    - ParticipationCountCondition: total_tournaments >= 5
    """
    condition_type: str
    parameters: Dict

    class Config:
        from_attributes = True


class BadgeRule(BaseModel):
    """
    Badge awarding rule (future extensibility).

    Defines when and how a badge should be awarded.
    Separates badge logic from service code.

    Future implementation could load rules from database or config file.
    """
    badge_type: str
    badge_category: str
    conditions: List[BadgeCondition]
    priority: int = 0  # For resolving conflicts
    is_active: bool = True

    class Config:
        from_attributes = True


class BadgeEvaluationContext(BaseModel):
    """
    Context for evaluating badge rules.

    Contains all data needed to determine if a badge should be awarded.
    """
    user_id: int
    tournament_id: int

    # Current tournament data
    placement: Optional[int] = None
    total_participants: int = 0
    final_score: Optional[float] = None

    # Historical data
    previous_tournaments_count: int = 0
    previous_placements: List[int] = Field(default_factory=list)
    consecutive_wins: int = 0

    # Performance metrics
    improvement_percentage: Optional[float] = None
    consistency_score: Optional[float] = None
    rounds_won: int = 0
    total_rounds: int = 0

    # Metadata
    tournament_format: str = ""
    measurement_unit: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# REWARD POLICY CONFIGURATION
# ============================================================================

class RewardPolicy(BaseModel):
    """
    Configurable reward policy for tournaments.

    Defines XP, credits, and skill points for each placement.
    Can be customized per tournament type.
    """
    tournament_type: Optional[str] = None  # None = default policy

    # Placement rewards
    first_place_xp: int = 500
    first_place_credits: int = 100

    second_place_xp: int = 300
    second_place_credits: int = 50

    third_place_xp: int = 200
    third_place_credits: int = 25

    participant_xp: int = 50
    participant_credits: int = 0

    # Skill point base values
    first_place_skill_points: int = 10
    second_place_skill_points: int = 7
    third_place_skill_points: int = 5
    participant_skill_points: int = 1

    class Config:
        from_attributes = True


# ============================================================================
# API REQUEST SCHEMAS
# ============================================================================

class DistributeRewardsRequest(BaseModel):
    """Request to distribute rewards for a tournament"""
    tournament_id: int
    force_redistribution: bool = False  # Allow re-distribution of rewards
    reward_policy: Optional[RewardPolicy] = None  # Custom policy (optional)

    class Config:
        from_attributes = True


class AddSkillMappingRequest(BaseModel):
    """Request to add skill mapping to tournament"""
    tournament_id: int
    skill_name: str
    skill_category: str
    weight: float = 1.0

    class Config:
        from_attributes = True
