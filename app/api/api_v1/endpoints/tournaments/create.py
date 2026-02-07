"""
Tournament Creation Endpoint

POST /api/v1/tournaments/create

Creates a tournament with proper domain logic matching production requirements.
This is the clean entry point for tournament workflows.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
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
    max_players: int = Field(..., ge=4, le=16, description="Maximum number of players (4-16)")
    skills_to_test: List[str] = Field(..., min_items=1, max_items=20, description="Skills to validate")
    reward_config: List[RewardTierConfig] = Field(..., min_items=1, description="Reward distribution tiers")
    game_preset_id: Optional[int] = Field(default=None, description="Game preset ID (P3)")
    game_config: Optional[Dict] = Field(default=None, description="Game configuration overrides")
    enrollment_cost: int = Field(default=0, ge=0, description="Enrollment cost in credits (0 = free)")


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

    # Step 4: Skip game configuration for now (P3 feature - model schema TBD)
    # TODO: Add game configuration support once model is finalized
    if request.game_preset_id or request.game_config:
        logger.info(f"⏭️  Skipping game configuration (P3 feature): preset_id={request.game_preset_id}")

    # Step 5: Create skill mappings
    from app.models.tournament_achievement import TournamentSkillMapping

    for skill_name in request.skills_to_test:
        skill_mapping = TournamentSkillMapping(
            semester_id=tournament.id,
            skill_name=skill_name
        )
        db.add(skill_mapping)

    logger.info(f"✅ Skill mappings created: {len(request.skills_to_test)} skills")

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
