"""
Tournament Rewards API V2 - Modern Unified System

New endpoints using the unified reward orchestrator.
Distributes both participation rewards (skill/XP) and visual badges.
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.schemas.tournament_rewards import (
    DistributeRewardsRequest,
    TournamentRewardResult,
    BulkRewardDistributionResult,
    AddSkillMappingRequest,
    RewardPolicy
)
from app.services.tournament import tournament_reward_orchestrator as orchestrator


router = APIRouter()


# ============================================================================
# REWARD DISTRIBUTION ENDPOINTS
# ============================================================================

@router.post("/{tournament_id}/distribute-rewards-v2", response_model=Dict[str, Any])
def distribute_tournament_rewards_v2(
    tournament_id: int,
    request: DistributeRewardsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Distribute tournament rewards (V2 - Unified System)

    Distributes both:
    - Participation rewards: Skill points, XP, Credits (DATA layer)
    - Visual badges: Achievement badges (UI layer)

    **Authorization**: Admin or Instructor only

    **Business Rules**:
    - Tournament must be COMPLETED
    - Rankings must exist
    - Awards both skill/XP and visual badges
    - Transitions to REWARDS_DISTRIBUTED status
    """
    # Authorization
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can distribute rewards"
        )

    # Validate tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    if tournament.tournament_status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tournament must be COMPLETED. Current status: {tournament.tournament_status}"
        )

    # Distribute rewards using orchestrator
    try:
        # Pass reward_policy as-is (None means load from config)
        reward_policy = request.reward_policy

        result = orchestrator.distribute_rewards_for_tournament(
            db=db,
            tournament_id=tournament_id,
            reward_policy=reward_policy,
            distributed_by=current_user.id,
            force_redistribution=request.force_redistribution
        )

        # Update tournament status
        from app.api.api_v1.endpoints.tournaments.lifecycle import record_status_change

        old_status = tournament.tournament_status
        tournament.tournament_status = "REWARDS_DISTRIBUTED"

        record_status_change(
            db=db,
            tournament_id=tournament_id,
            old_status=old_status,
            new_status="REWARDS_DISTRIBUTED",
            changed_by=current_user.id,
            reason=f"Rewards distributed: {result.total_participants} participants, "
                   f"{result.distribution_summary.get('total_badges_awarded', 0)} badges, "
                   f"{result.distribution_summary.get('total_xp_awarded', 0)} XP"
        )

        db.commit()

        return {
            "success": True,
            "tournament_id": result.tournament_id,
            "tournament_name": result.tournament_name,
            "total_participants": result.total_participants,
            "rewards_distributed_count": len(result.rewards_distributed),
            "summary": result.distribution_summary,
            "distributed_at": result.distributed_at.isoformat(),
            "message": f"Successfully distributed rewards to {len(result.rewards_distributed)} participants"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to distribute rewards: {str(e)}"
        )


@router.get("/{tournament_id}/rewards/{user_id}", response_model=Dict[str, Any])
def get_user_tournament_rewards(
    tournament_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get reward details for a specific user in a tournament.

    Returns both participation rewards and badges earned.

    **Authorization**: User can view their own rewards, or Admin/Instructor can view any
    """
    # Authorization
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own rewards"
        )

    # Get rewards
    result = orchestrator.get_user_reward_summary(db, user_id, tournament_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No rewards found for user {user_id} in tournament {tournament_id}"
        )

    return result.to_dict()


# ============================================================================
# SKILL MAPPING ENDPOINTS
# ============================================================================

@router.post("/{tournament_id}/skill-mappings", response_model=Dict[str, Any])
def add_tournament_skill_mapping(
    tournament_id: int,
    request: AddSkillMappingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a skill mapping to a tournament.

    Defines which skills this tournament develops and their weights.

    **Authorization**: Admin only

    **Example**:
    ```json
    {
        "skill_name": "agility",
        "skill_category": "Physical",
        "weight": 1.0
    }
    ```
    """
    # Authorization
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage skill mappings"
        )

    # Validate tournament exists
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Create skill mapping
    from app.models.tournament_achievement import TournamentSkillMapping

    mapping = TournamentSkillMapping(
        semester_id=tournament_id,
        skill_name=request.skill_name,
        skill_category=request.skill_category,
        weight=str(request.weight)  # Store as string
    )

    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    return {
        "success": True,
        "mapping_id": mapping.id,
        "tournament_id": tournament_id,
        "skill_name": mapping.skill_name,
        "skill_category": mapping.skill_category,
        "weight": float(mapping.weight),
        "message": f"Skill mapping added: {request.skill_name}"
    }


@router.get("/{tournament_id}/skill-mappings", response_model=List[Dict[str, Any]])
def get_tournament_skill_mappings(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all skill mappings for a tournament.

    Returns which skills this tournament develops.
    """
    from app.models.tournament_achievement import TournamentSkillMapping

    mappings = db.query(TournamentSkillMapping).filter(
        TournamentSkillMapping.semester_id == tournament_id
    ).all()

    return [
        {
            "id": m.id,
            "skill_name": m.skill_name,
            "skill_category": m.skill_category,
            "weight": float(m.weight),
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in mappings
    ]


@router.delete("/{tournament_id}/skill-mappings/{mapping_id}")
def delete_tournament_skill_mapping(
    tournament_id: int,
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a skill mapping from a tournament.

    **Authorization**: Admin only
    """
    # Authorization
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage skill mappings"
        )

    from app.models.tournament_achievement import TournamentSkillMapping

    mapping = db.query(TournamentSkillMapping).filter(
        TournamentSkillMapping.id == mapping_id,
        TournamentSkillMapping.semester_id == tournament_id
    ).first()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill mapping {mapping_id} not found"
        )

    db.delete(mapping)
    db.commit()

    return {
        "success": True,
        "message": f"Skill mapping deleted: {mapping.skill_name}"
    }


# ============================================================================
# BADGE ENDPOINTS
# ============================================================================

@router.get("/badges/user/{user_id}", response_model=Dict[str, Any])
def get_user_tournament_badges(
    user_id: int,
    tournament_id: int = Query(None, description="Filter by specific tournament"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tournament badges for a user.

    Returns all visual achievement badges earned in tournaments.

    **Authorization**: User can view their own badges, or Admin/Instructor can view any
    """
    # Authorization
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own badges"
        )

    from app.services.tournament import tournament_badge_service as badge_service

    badges = badge_service.get_player_badges(db, user_id, tournament_id, limit)

    return {
        "user_id": user_id,
        "total_badges": len(badges),
        "badges": badges
    }


@router.get("/badges/showcase/{user_id}", response_model=Dict[str, Any])
def get_user_badge_showcase(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get badge showcase for user profile.

    Returns rarest and most recent badges grouped by category.

    **Authorization**: User can view their own showcase, or Admin/Instructor can view any
    """
    # Authorization
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own badge showcase"
        )

    from app.services.tournament import tournament_badge_service as badge_service

    showcase = badge_service.get_player_badge_showcase(db, user_id)

    return {
        "user_id": user_id,
        "showcase": showcase
    }
