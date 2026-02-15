"""
Tournament Creation Endpoint

POST /api/v1/tournaments/create

Creates a tournament with proper domain logic matching production requirements.
This is the clean entry point for tournament workflows.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.tournament_type import TournamentType
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_reward_config import TournamentRewardConfig
from app.models.game_configuration import GameConfiguration
from app.models.game_preset import GamePreset
from app.models.tournament_achievement import TournamentSkillMapping

router = APIRouter()
logger = logging.getLogger(__name__)


class RewardTierConfig(BaseModel):
    """Reward tier configuration"""
    rank: int
    xp_reward: int
    credits_reward: int


class TournamentCreateRequest(BaseModel):
    """Request schema for tournament creation"""
    name: str = Field(..., min_length=3, max_length=200, description="Tournament name")
    tournament_type: str = Field(..., description="Tournament type code (league, knockout, hybrid)")
    age_group: str = Field(..., description="Age group code (e.g., PRE, YOUTH, ADULT)")
    max_players: int = Field(..., ge=4, le=1024, description="Maximum number of players (4-1024)")
    skills_to_test: List[str] = Field(
        default_factory=list,
        max_length=20,
        description=(
            "Skills to develop in this tournament (weight=1.0 each). "
            "Optional if game_preset_id is provided — the preset's skills_tested "
            "and weights are used automatically."
        )
    )
    reward_config: List[RewardTierConfig] = Field(..., min_length=1, description="Reward distribution tiers")
    game_preset_id: Optional[int] = Field(
        default=None,
        description=(
            "Game preset ID (e.g., GānFootvolley=1, GānFoottennis=2). "
            "When provided, the preset's skills_tested and skill_weights are "
            "automatically synced to tournament_skill_mappings with converted "
            "reactivity multipliers. Takes priority over skills_to_test."
        )
    )
    game_config: Optional[Dict] = Field(default=None, description="Game configuration overrides (future use)")
    skill_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description=(
            "Explicit skill weight overrides for skills_to_test. "
            "Keys are skill names, values are reactivity multipliers (e.g., {'finishing': 1.5, 'passing': 0.6}). "
            "If provided, these weights override the default weight=1.0 assigned to each skill in skills_to_test. "
            "Ignored when game_preset_id is provided (preset weights take priority)."
        )
    )
    enrollment_cost: int = Field(default=0, ge=0, description="Enrollment cost in credits (0 = free)")

    @model_validator(mode="after")
    def validate_skills_source(self) -> "TournamentCreateRequest":
        """At least one skill source must be provided: game_preset_id OR skills_to_test."""
        if not self.game_preset_id and not self.skills_to_test:
            raise ValueError(
                "Either 'game_preset_id' or 'skills_to_test' must be provided. "
                "Use game_preset_id to auto-sync skills from a game preset, "
                "or provide skills_to_test manually."
            )
        return self


class TournamentCreateResponse(BaseModel):
    """Response schema for tournament creation"""
    success: bool
    tournament_id: int
    tournament_name: str
    tournament_code: str
    tournament_type: str
    tournament_status: str
    max_players: int
    message: str


@router.post("/create", response_model=TournamentCreateResponse, status_code=status.HTTP_201_CREATED)
def create_tournament(
    request: TournamentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a tournament using production domain logic

    **Authorization:** Admin only

    **Domain Rules:**
    1. Tournament is created with status IN_PROGRESS (ready for enrollment)
    2. Grand Master instructor is assigned automatically for sandbox/testing
    3. Tournament configuration is created as separate entity (P2 architecture)
    4. Reward configuration is created with specified tiers
    5. Game configuration is created if preset_id or config provided (P3)

    **Example Request:**
    ```json
    {
      "name": "LFA Winter Cup 2026",
      "tournament_type": "hybrid",
      "age_group": "YOUTH",
      "max_players": 8,
      "skills_to_test": ["PASSING", "DRIBBLING"],
      "reward_config": [
        {"rank": 1, "xp_reward": 100, "credits_reward": 50},
        {"rank": 2, "xp_reward": 75, "credits_reward": 30},
        {"rank": 3, "xp_reward": 50, "credits_reward": 20}
      ],
      "enrollment_cost": 0
    }
    ```

    **Response:**
    ```json
    {
      "success": true,
      "tournament_id": 123,
      "tournament_name": "LFA Winter Cup 2026",
      "tournament_code": "TOURN-20260206-ABC123",
      "tournament_type": "hybrid",
      "tournament_status": "IN_PROGRESS",
      "max_players": 8,
      "message": "Tournament created successfully"
    }
    ```
    """
    # Authorization: Admin only
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create tournaments"
        )

    logger.info(
        f"🏆 Creating tournament: name={request.name}, type={request.tournament_type}, "
        f"max_players={request.max_players}, admin={current_user.email}"
    )

    # Validate tournament type exists
    tournament_type = db.query(TournamentType).filter(
        TournamentType.code == request.tournament_type
    ).first()

    if not tournament_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tournament type: {request.tournament_type}. Must be one of: league, knockout, hybrid"
        )

    # Validate player count against tournament type constraints
    is_valid, error_msg = tournament_type.validate_player_count(request.max_players)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Get Grand Master instructor for tournament management
    grandmaster = db.query(User).filter(
        User.role == UserRole.INSTRUCTOR,
        User.email == "grandmaster@lfa.com"
    ).first()

    if not grandmaster:
        logger.warning("Grand Master instructor not found, tournament will have no master instructor")

    # Generate unique tournament code
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tournament_code = f"TOURN-{timestamp}"

    # Step 1: Create tournament (Semester entity with P2 architecture)
    tournament = Semester(
        code=tournament_code,
        name=request.name,
        start_date=datetime.now().date(),
        end_date=(datetime.now() + timedelta(days=30)).date(),
        is_active=True,
        tournament_status="IN_PROGRESS",  # Ready for enrollment and session generation
        master_instructor_id=grandmaster.id if grandmaster else None,
        enrollment_cost=request.enrollment_cost
        # Note: age_group not stored in Semester, only in request validation
    )

    db.add(tournament)
    db.flush()  # Get tournament.id

    logger.info(f"✅ Tournament created: id={tournament.id}, code={tournament_code}")

    # Step 2: Create tournament configuration (P2: separate entity)
    tournament_config = TournamentConfiguration(
        semester_id=tournament.id,
        tournament_type_id=tournament_type.id,
        participant_type="INDIVIDUAL",
        is_multi_day=False,
        max_players=request.max_players,
        parallel_fields=1,
        scoring_type="HEAD_TO_HEAD",  # Default for most tournament types
        number_of_rounds=1,
        assignment_type="OPEN_ASSIGNMENT",
        sessions_generated=False  # Will be set to True after session generation
    )

    db.add(tournament_config)
    db.flush()

    logger.info(f"✅ Tournament configuration created: config_id={tournament_config.id}")

    # Step 3: Create reward configuration (using JSONB structure)
    # Build reward_config JSON from tiers
    reward_tiers_dict = {}
    for tier in request.reward_config:
        placement_key = {
            1: "first_place",
            2: "second_place",
            3: "third_place"
        }.get(tier.rank, f"rank_{tier.rank}")

        reward_tiers_dict[placement_key] = {
            "xp": tier.xp_reward,
            "credits": tier.credits_reward
        }

    tournament_reward_config = TournamentRewardConfig(
        semester_id=tournament.id,
        reward_policy_name="custom",
        reward_config=reward_tiers_dict
    )
    db.add(tournament_reward_config)

    logger.info(f"✅ Reward configuration created with {len(request.reward_config)} tiers")

    # Step 4: Create game configuration + resolve preset for skill auto-sync
    preset: Optional[GamePreset] = None
    if request.game_preset_id:
        preset = db.query(GamePreset).filter(
            GamePreset.id == request.game_preset_id,
            GamePreset.is_active == True
        ).first()
        if not preset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Game preset with id={request.game_preset_id} not found or inactive."
            )
        game_config_entity = GameConfiguration(
            semester_id=tournament.id,
            game_preset_id=preset.id,
            game_config=preset.game_config  # full preset config as base, no overrides yet
        )
        db.add(game_config_entity)
        logger.info(
            f"✅ Game configuration created: preset='{preset.code}' "
            f"({len(preset.skills_tested)} skills)"
        )
    elif request.game_config:
        # Custom config dict without a preset reference
        game_config_entity = GameConfiguration(
            semester_id=tournament.id,
            game_preset_id=None,
            game_config=request.game_config
        )
        db.add(game_config_entity)
        logger.info("✅ Game configuration created from custom config dict")

    # Step 5: Create skill mappings
    #
    # Priority A — game_preset_id supplied:
    #   Use preset.skills_tested + convert fractional preset weights to
    #   reactivity multipliers (weight / avg_weight).
    #   This ensures dominant preset skills (e.g. ball_control in GānFootvolley)
    #   have a proportionally stronger effect on skill development.
    #
    # Priority B — no preset (or preset has no skill_weights):
    #   Fall back to the manually supplied skills_to_test list, weight = 1.0 each.
    #   This preserves the existing behaviour for tournaments without a preset.

    skill_mappings_added = 0

    if preset and preset.skill_weights:
        preset_weights: Dict[str, float] = preset.skill_weights   # fractional, sum ≈ 1.0
        avg_w = sum(preset_weights.values()) / len(preset_weights)

        for skill_name in preset.skills_tested:
            fractional = preset_weights.get(skill_name, avg_w)
            # Convert to reactivity multiplier: dominant skill → > 1.0, minor skill → < 1.0
            reactivity = round(fractional / avg_w, 2)
            reactivity = max(0.1, min(5.0, reactivity))   # clamp to schema bounds

            db.add(TournamentSkillMapping(
                semester_id=tournament.id,
                skill_name=skill_name,
                weight=reactivity
            ))
            skill_mappings_added += 1

        logger.info(
            f"✅ Skill mappings auto-synced from preset '{preset.code}': "
            f"{skill_mappings_added} skills (avg_w={avg_w:.4f})"
        )

    elif request.skills_to_test:
        # Manual list — use explicit skill_weights if provided, else weight = 1.0
        explicit_weights: Dict[str, float] = request.skill_weights or {}
        for skill_name in request.skills_to_test:
            weight = explicit_weights.get(skill_name, 1.0)
            weight = max(0.1, min(5.0, float(weight)))  # clamp to schema bounds
            db.add(TournamentSkillMapping(
                semester_id=tournament.id,
                skill_name=skill_name,
                weight=weight,
            ))
            skill_mappings_added += 1

        if explicit_weights:
            logger.info(
                f"✅ Skill mappings created from manual list with explicit weights: "
                f"{skill_mappings_added} skills — {explicit_weights}"
            )
        else:
            logger.info(f"✅ Skill mappings created from manual list: {skill_mappings_added} skills (weight=1.0 each)")

    elif preset and not preset.skill_weights:
        # Preset exists but has no weights defined — fall back to skills_tested with weight=1.0
        for skill_name in preset.skills_tested:
            db.add(TournamentSkillMapping(
                semester_id=tournament.id,
                skill_name=skill_name
            ))
            skill_mappings_added += 1

        logger.info(
            f"✅ Skill mappings created from preset '{preset.code}' (no weights, using 1.0): "
            f"{skill_mappings_added} skills"
        )

    # Commit all changes
    db.commit()
    db.refresh(tournament)

    logger.info(f"🎉 Tournament creation complete: id={tournament.id}, status={tournament.tournament_status}")

    return TournamentCreateResponse(
        success=True,
        tournament_id=tournament.id,
        tournament_name=tournament.name,
        tournament_code=tournament.code,
        tournament_type=request.tournament_type,
        tournament_status=tournament.tournament_status,
        max_players=request.max_players,
        message=f"Tournament '{request.name}' created successfully"
    )
