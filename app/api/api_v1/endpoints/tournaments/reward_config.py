"""
Tournament Reward Configuration API Endpoints

Endpoints for managing tournament reward policies:
- Save reward configuration
- Load reward configuration
- Get available templates
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from .....database import get_db
from .....models.semester import Semester
from .....models.user import User, UserRole
from .....dependencies import get_current_active_user
from .....schemas.reward_config import TournamentRewardConfig, REWARD_CONFIG_TEMPLATES


router = APIRouter()


@router.get("/templates", response_model=Dict[str, Dict[str, Any]])
def get_reward_config_templates(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all available reward configuration templates.

    Returns:
        Dict of template name -> template config
    """
    templates = {}
    for name, config in REWARD_CONFIG_TEMPLATES.items():
        templates[name] = config.model_dump(mode="json")

    return templates


@router.get("/{tournament_id}/reward-config", response_model=Dict[str, Any])
def get_tournament_reward_config(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get reward configuration for a specific tournament.

    Args:
        tournament_id: Tournament (semester) ID

    Returns:
        Reward configuration dict or empty dict if not configured
    """
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournament {tournament_id} not found")

    # Return reward_config if exists, otherwise empty dict
    if tournament.reward_config:
        return tournament.reward_config

    return {}


@router.post("/{tournament_id}/reward-config", response_model=Dict[str, Any])
def save_tournament_reward_config(
    tournament_id: int,
    reward_config: TournamentRewardConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Save reward configuration for a tournament.

    ⚠️ VALIDATION: At least 1 skill must be enabled.

    Args:
        tournament_id: Tournament (semester) ID
        reward_config: Reward configuration to save

    Returns:
        Saved reward configuration

    Raises:
        403: If user is not admin
        404: If tournament not found
        400: If validation fails (no enabled skills, invalid config, etc.)
    """
    # Check if user is admin
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can configure tournament rewards")

    # Get tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournament {tournament_id} not found")

    # 🔒 VALIDATION GUARD: Check enabled skills
    is_valid, error_message = reward_config.validate_enabled_skills()
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid skill configuration: {error_message}. You must select at least 1 skill for this tournament."
        )

    # Validate and serialize config
    try:
        config_dict = reward_config.model_dump(mode="json")

        # Save to tournament
        tournament.reward_config = config_dict

        # Also update reward_policy_name for consistency
        tournament.reward_policy_name = reward_config.template_name or "Custom"

        db.commit()
        db.refresh(tournament)

        return tournament.reward_config

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid reward configuration: {str(e)}")


@router.put("/{tournament_id}/reward-config", response_model=Dict[str, Any])
def update_tournament_reward_config(
    tournament_id: int,
    reward_config: TournamentRewardConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update existing reward configuration for a tournament.

    Args:
        tournament_id: Tournament (semester) ID
        reward_config: Updated reward configuration

    Returns:
        Updated reward configuration
    """
    # Same as POST, just alias for semantic clarity
    return save_tournament_reward_config(tournament_id, reward_config, db, current_user)


@router.delete("/{tournament_id}/reward-config")
def delete_tournament_reward_config(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete reward configuration for a tournament (reset to default).

    Args:
        tournament_id: Tournament (semester) ID

    Returns:
        Success message
    """
    # Check if user is admin
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can delete tournament reward configs")

    # Get tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournament {tournament_id} not found")

    # Reset reward_config
    tournament.reward_config = None
    tournament.reward_policy_name = "default"

    db.commit()

    return {"message": "Reward configuration deleted successfully"}


@router.get("/{tournament_id}/reward-config/preview", response_model=Dict[str, Any])
def preview_tournament_rewards(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Preview estimated reward distribution for a tournament.

    Args:
        tournament_id: Tournament (semester) ID

    Returns:
        Estimated reward summary (total badges, credits, XP, etc.)
    """
    # Get tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournament {tournament_id} not found")

    # Get reward config
    if not tournament.reward_config:
        raise HTTPException(status_code=404, detail="No reward configuration found for this tournament")

    try:
        config = TournamentRewardConfig(**tournament.reward_config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid reward configuration: {str(e)}")

    # TODO: Get actual participant count from enrollments
    # For now, use estimated count
    estimated_participants = 8  # Placeholder

    # Calculate estimates
    total_badges = 0
    total_credits = 0
    badge_breakdown = {}

    # 1st place (1 person)
    if config.first_place:
        total_badges += len(config.first_place.badges)
        total_credits += config.first_place.credits
        for badge in config.first_place.badges:
            badge_breakdown[badge.badge_type] = badge_breakdown.get(badge.badge_type, 0) + 1

    # 2nd place (1 person)
    if config.second_place:
        total_badges += len(config.second_place.badges)
        total_credits += config.second_place.credits
        for badge in config.second_place.badges:
            badge_breakdown[badge.badge_type] = badge_breakdown.get(badge.badge_type, 0) + 1

    # 3rd place (1 person)
    if config.third_place:
        total_badges += len(config.third_place.badges)
        total_credits += config.third_place.credits
        for badge in config.third_place.badges:
            badge_breakdown[badge.badge_type] = badge_breakdown.get(badge.badge_type, 0) + 1

    # Top 25% (estimated)
    if config.top_25_percent:
        top_25_count = max(1, int(estimated_participants * 0.25))
        total_badges += len(config.top_25_percent.badges) * top_25_count
        total_credits += config.top_25_percent.credits * top_25_count
        for badge in config.top_25_percent.badges:
            badge_breakdown[badge.badge_type] = badge_breakdown.get(badge.badge_type, 0) + top_25_count

    # Participation (all players)
    if config.participation:
        total_badges += len(config.participation.badges) * estimated_participants
        total_credits += config.participation.credits * estimated_participants
        for badge in config.participation.badges:
            badge_breakdown[badge.badge_type] = badge_breakdown.get(badge.badge_type, 0) + estimated_participants

    # Estimate XP (rough calculation)
    estimated_total_xp = estimated_participants * 500  # Placeholder

    return {
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        "estimated_participants": estimated_participants,
        "total_badges": total_badges,
        "total_credits": total_credits,
        "estimated_total_xp": estimated_total_xp,
        "badge_breakdown": badge_breakdown,
        "rarity_distribution": {
            "LEGENDARY": sum(1 for b in badge_breakdown.keys() if "PERFECT_SCORE" in b or "UNDEFEATED" in b),
            "EPIC": len([b for b in badge_breakdown.keys() if "CHAMPION" in b]),
            "RARE": len([b for b in badge_breakdown.keys() if "RUNNER_UP" in b or "TOP_PERFORMER" in b]),
            "UNCOMMON": len([b for b in badge_breakdown.keys() if "THIRD_PLACE" in b]),
            "COMMON": len([b for b in badge_breakdown.keys() if "DEBUT" in b or "PARTICIPANT" in b]),
        }
    }
