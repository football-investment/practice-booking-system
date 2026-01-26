"""
Skill Progression Service V2 - Placement-Based Skill Assessment

Core principle: Tournament results provide realistic skill assessment, not just progression.

Key features:
- Placement-based skill values (1st place → 95-100, last place → 40-50)
- Skills can both INCREASE and DECREASE based on performance
- Weighted average between baseline (onboarding) and placement-based value
- More tournaments = trust placement more, less = trust baseline more

Example:
    Player with baseline speed=70 finishes 10th out of 10 players (last place):
    - Tournament 1: (70*0.50 + 40*0.50) = 55.0 ❌ Decreased by -15.0
    - Tournament 2: (70*0.33 + 40*0.67) = 50.0 ❌ Decreased by -20.0

    Same player finishes 1st out of 10 players:
    - Tournament 1: (70*0.50 + 100*0.50) = 85.0 ✅ Increased by +15.0
    - Tournament 2: (70*0.33 + 100*0.67) = 90.0 ✅ Increased by +20.0
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.user import User
from ..models.license import UserLicense
from ..models.tournament_achievement import TournamentParticipation
from ..skills_config import SKILL_CATEGORIES


# Configuration constants
MIN_SKILL_VALUE = 40.0  # Worst possible skill value (last place)
MAX_SKILL_VALUE = 100.0  # Best possible skill value (1st place)
DEFAULT_BASELINE = 50.0  # Default if no onboarding data


def calculate_skill_value_from_placement(
    baseline: float,
    placement: int,
    total_players: int,
    tournament_count: int
) -> float:
    """
    Calculate realistic skill value based on tournament placement.

    Args:
        baseline: Initial skill value from onboarding (0-100)
        placement: Player's placement in tournament (1 = best)
        total_players: Total number of players in tournament
        tournament_count: Number of tournaments completed for this skill

    Returns:
        New skill value (40-100)

    Formula:
        1. Calculate percentile: (placement - 1) / (total_players - 1)
           - 0.0 = best (1st place)
           - 1.0 = worst (last place)

        2. Map percentile to skill value:
           - 1st place → 100
           - Last place → 40

        3. Weighted average:
           - 1st tournament: 50% baseline, 50% placement
           - 2nd tournament: 33% baseline, 67% placement
           - 3rd tournament: 25% baseline, 75% placement
           - etc.

    Examples:
        >>> # Player finishes 1st out of 10 (baseline=70, first tournament)
        >>> calculate_skill_value_from_placement(70, 1, 10, 1)
        85.0  # (70*0.5 + 100*0.5)

        >>> # Player finishes 10th out of 10 (baseline=70, first tournament)
        >>> calculate_skill_value_from_placement(70, 10, 10, 1)
        55.0  # (70*0.5 + 40*0.5)

        >>> # Player finishes 1st out of 10 (baseline=70, third tournament)
        >>> calculate_skill_value_from_placement(70, 1, 10, 3)
        92.5  # (70*0.25 + 100*0.75)
    """
    # Handle edge case: single player tournament
    if total_players == 1:
        percentile = 0.0  # Treat as winner
    else:
        percentile = (placement - 1) / (total_players - 1)

    # Map percentile to skill value (linear interpolation)
    # 0.0 → MAX_SKILL_VALUE (100)
    # 1.0 → MIN_SKILL_VALUE (40)
    placement_skill = MAX_SKILL_VALUE - (percentile * (MAX_SKILL_VALUE - MIN_SKILL_VALUE))

    # Calculate weights based on tournament experience
    # More tournaments = trust placement more
    baseline_weight = 1.0 / (tournament_count + 1)
    placement_weight = tournament_count / (tournament_count + 1)

    # Weighted average
    new_skill = (baseline * baseline_weight) + (placement_skill * placement_weight)

    return round(new_skill, 1)


def get_all_skill_keys() -> List[str]:
    """
    Get list of all skill keys from skills_config.

    Returns:
        List of skill keys (e.g., ["ball_control", "dribbling", ...])
    """
    skill_keys = []
    for category in SKILL_CATEGORIES:
        for skill in category["skills"]:
            skill_keys.append(skill["key"])
    return skill_keys


def get_baseline_skills(db: Session, user_id: int) -> Dict[str, float]:
    """
    Get baseline skill values from UserLicense.football_skills (onboarding).

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Dict of skill_key → baseline_value (0-100)

    ⚠️ FALLBACK BEHAVIOR FOR MISSING SKILLS:
        If a skill is NOT found in UserLicense.football_skills, it defaults to DEFAULT_BASELINE (50.0).
        This is INTENTIONAL and handles cases where:
        - User completed onboarding with old skill set (before migration to 29 skills)
        - User's onboarding data is incomplete
        - New skills were added to system after user onboarding

        The DEFAULT_BASELINE (50.0) represents "neutral" skill level - neither strong nor weak.
        Tournament placements will then adjust this value up or down based on performance.

    Example:
        User has onboarding data: {"ball_control": 70, "dribbling": 65}
        System now has 29 skills total.
        Result: {"ball_control": 70.0, "dribbling": 65.0, "speed": 50.0, ...other skills... → 50.0}
    """
    # Get active LFA_FOOTBALL_PLAYER license
    license = db.query(UserLicense).filter(
        UserLicense.user_id == user_id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
        UserLicense.is_active == True
    ).first()

    if not license or not license.football_skills:
        # 🔒 GUARD: No onboarding data at all → return all skills at DEFAULT_BASELINE
        return {skill_key: DEFAULT_BASELINE for skill_key in get_all_skill_keys()}

    baseline_skills = {}
    for skill_key in get_all_skill_keys():
        # ⚠️ FALLBACK: Missing skill defaults to DEFAULT_BASELINE (50.0)
        # This is INTENTIONAL - allows graceful handling of skill migrations
        skill_value = license.football_skills.get(skill_key, DEFAULT_BASELINE)

        if isinstance(skill_value, dict):
            # New format: {"baseline": 70, "current_level": 85, ...}
            baseline_skills[skill_key] = float(skill_value.get("baseline", DEFAULT_BASELINE))
        else:
            # Old format: {"ball_control": 70, ...}
            baseline_skills[skill_key] = float(skill_value)

    return baseline_skills


def calculate_tournament_skill_contribution(
    db: Session,
    user_id: int,
    skill_keys: List[str]
) -> Dict[str, Dict[str, float]]:
    """
    Calculate tournament-based skill contributions for specified skills.

    Args:
        db: Database session
        user_id: User ID
        skill_keys: List of skill keys to calculate (from tournament reward config)

    Returns:
        Dict of skill_key → {
            "contribution": float,  # Net contribution from all tournaments
            "tournament_count": int,  # Number of tournaments affecting this skill
            "current_value": float,  # Current skill value after all tournaments
            "baseline": float  # Original onboarding value
        }

    Logic:
        1. Get user's baseline skills from onboarding
        2. For each tournament participation:
           - Get tournament's selected skills (from reward_config)
           - For each selected skill:
             - Calculate new skill value based on placement
             - Track contribution vs baseline
        3. Return aggregated data per skill
    """
    # Get baseline skills from UserLicense
    baseline_skills = get_baseline_skills(db, user_id)

    # Get all tournament participations for this user (ordered by date)
    participations = (
        db.query(TournamentParticipation)
        .filter(TournamentParticipation.user_id == user_id)
        .order_by(TournamentParticipation.achieved_at.asc())
        .all()
    )

    # Track skill evolution across tournaments
    skill_data = {}
    skill_tournament_counts = {}  # Track how many tournaments affected each skill

    for skill_key in skill_keys:
        baseline = baseline_skills.get(skill_key, DEFAULT_BASELINE)
        skill_data[skill_key] = {
            "baseline": baseline,
            "current_value": baseline,  # Start with baseline
            "contribution": 0.0,
            "tournament_count": 0
        }
        skill_tournament_counts[skill_key] = 0

    # Process each tournament participation
    for participation in participations:
        tournament = participation.tournament

        # Get tournament's reward config to know which skills were selected
        if not tournament or not tournament.reward_config:
            continue

        reward_config = tournament.reward_config
        skill_mappings = reward_config.get("skill_mappings", [])

        # Get list of enabled skills for this tournament
        tournament_skills = [
            mapping["skill"]
            for mapping in skill_mappings
            if mapping.get("enabled", False) and mapping["skill"] in skill_keys
        ]

        if not tournament_skills:
            continue

        # Get placement data
        placement = participation.placement
        if not placement:
            continue

        # Get total players in tournament
        total_players = (
            db.query(TournamentParticipation)
            .filter(TournamentParticipation.semester_id == tournament.id)
            .count()
        )

        if total_players == 0:
            continue

        # Update each affected skill
        for skill_key in tournament_skills:
            if skill_key not in skill_data:
                continue

            baseline = skill_data[skill_key]["baseline"]
            current_count = skill_tournament_counts[skill_key]

            # Calculate new skill value based on this tournament
            new_value = calculate_skill_value_from_placement(
                baseline=baseline,
                placement=placement,
                total_players=total_players,
                tournament_count=current_count + 1
            )

            # Update skill data
            skill_data[skill_key]["current_value"] = new_value
            skill_data[skill_key]["contribution"] = new_value - baseline
            skill_data[skill_key]["tournament_count"] = current_count + 1

            # Increment tournament count for this skill
            skill_tournament_counts[skill_key] += 1

    return skill_data


def get_skill_profile(db: Session, user_id: int) -> Dict[str, any]:
    """
    Get complete skill profile for user (for dashboard display).

    Returns:
        {
            "skills": {
                "ball_control": {
                    "baseline": 70.0,
                    "current_level": 85.0,
                    "total_delta": +15.0,
                    "tournament_delta": +15.0,
                    "assessment_delta": 0.0,  # Future: assessments
                    "tournament_count": 3,
                    "assessment_count": 0,
                    "tier": "ADVANCED",
                    "tier_emoji": "🔥"
                },
                ...
            },
            "average_level": 78.5,
            "total_tournaments": 5,
            "total_assessments": 0
        }
    """
    # Get all skill keys
    all_skill_keys = get_all_skill_keys()

    # Calculate tournament contributions for all skills
    skill_data = calculate_tournament_skill_contribution(db, user_id, all_skill_keys)

    # Get total tournament count
    total_tournaments = (
        db.query(TournamentParticipation)
        .filter(TournamentParticipation.user_id == user_id)
        .count()
    )

    # Build skill profile
    skill_profile = {}
    total_level = 0.0

    for skill_key in all_skill_keys:
        data = skill_data.get(skill_key, {
            "baseline": DEFAULT_BASELINE,
            "current_value": DEFAULT_BASELINE,
            "contribution": 0.0,
            "tournament_count": 0
        })

        current_level = data["current_value"]
        total_delta = data["contribution"]

        # Determine tier
        tier, tier_emoji = get_skill_tier(current_level)

        skill_profile[skill_key] = {
            "baseline": data["baseline"],
            "current_level": current_level,
            "total_delta": total_delta,
            "tournament_delta": total_delta,  # Currently only tournaments
            "assessment_delta": 0.0,  # Future: assessments
            "tournament_count": data["tournament_count"],
            "assessment_count": 0,
            "tier": tier,
            "tier_emoji": tier_emoji
        }

        total_level += current_level

    average_level = total_level / len(all_skill_keys) if all_skill_keys else 0.0

    return {
        "skills": skill_profile,
        "average_level": round(average_level, 1),
        "total_tournaments": total_tournaments,
        "total_assessments": 0  # Future: assessments
    }


def get_skill_tier(level: float) -> tuple[str, str]:
    """
    Get skill tier name and emoji based on level.

    Args:
        level: Skill level (0-100)

    Returns:
        (tier_name, tier_emoji)
    """
    if level >= 95:
        return ("MASTER", "💎")
    elif level >= 85:
        return ("ADVANCED", "🔥")
    elif level >= 70:
        return ("INTERMEDIATE", "⚡")
    elif level >= 50:
        return ("DEVELOPING", "📈")
    else:
        return ("BEGINNER", "🌱")
