"""
Tournament Participation Service

Handles skill point calculation, XP rewards, and participation tracking (DATA LAYER).
Separate from visual badge awards.
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
from sqlalchemy.exc import IntegrityError
import logging

from app.models.tournament_achievement import (
    TournamentSkillMapping,
    TournamentParticipation,
    SkillPointConversionRate
)
from app.models.semester import Semester
from app.models.tournament_ranking import TournamentRanking
from app.models.football_skill_assessment import FootballSkillAssessment
from app.models.xp_transaction import XPTransaction
from app.schemas.reward_config import TournamentRewardConfig

logger = logging.getLogger(__name__)

# Placement-based skill point rewards
PLACEMENT_SKILL_POINTS = {
    1: 10,  # 1st place: 10 base points
    2: 7,   # 2nd place: 7 base points
    3: 5,   # 3rd place: 5 base points
    None: 1 # Participation: 1 base point
}


def calculate_skill_points_for_placement(
    db: Session,
    tournament_id: int,
    placement: Optional[int]
) -> Dict[str, float]:
    """
    Calculate skill points based on placement and tournament skill mappings.

    🎁 V2: Uses reward_config.skill_mappings if available, falls back to TournamentSkillMapping table.

    Args:
        db: Database session
        tournament_id: Tournament (semester) ID
        placement: Player placement (1, 2, 3, or None for participation)

    Returns:
        Dictionary of skill_name -> points earned
        Example: {"agility": 4.3, "physical_fitness": 2.2}
    """
    # Get base points for placement
    base_points = PLACEMENT_SKILL_POINTS.get(placement, PLACEMENT_SKILL_POINTS[None])

    # 🎁 V2: Try to load skill mappings from reward_config
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    skill_mappings_data = []

    if tournament and tournament.reward_config:
        try:
            # Parse reward_config JSONB to TournamentRewardConfig
            config = TournamentRewardConfig(**tournament.reward_config)

            # 🔒 VALIDATION GUARD: Check that at least 1 skill is enabled
            is_valid, error_message = config.validate_enabled_skills()
            if not is_valid:
                logger.error(f"Tournament {tournament_id} has invalid skill configuration: {error_message}")
                logger.warning(f"Falling back to legacy TournamentSkillMapping table")
                skill_mappings_data = []
            else:
                # Extract enabled skill mappings with weights
                for skill_mapping in config.skill_mappings:
                    if skill_mapping.enabled:  # Only include enabled skills
                        skill_mappings_data.append({
                            'skill_name': skill_mapping.skill,
                            'weight': skill_mapping.weight,
                            'skill_category': skill_mapping.category
                        })

                logger.info(f"Loaded {len(skill_mappings_data)} enabled skill mappings from reward_config for tournament {tournament_id}")

        except Exception as e:
            logger.error(f"Failed to parse skill mappings from reward_config for tournament {tournament_id}: {e}")
            skill_mappings_data = []

    # Fallback: Use legacy TournamentSkillMapping table if no config found
    if not skill_mappings_data:
        logger.info(f"No reward config found, using TournamentSkillMapping table for tournament {tournament_id}")
        skill_mappings = db.query(TournamentSkillMapping).filter(
            TournamentSkillMapping.semester_id == tournament_id
        ).all()

        if not skill_mappings:
            return {}  # No skills mapped, return empty

        skill_mappings_data = [
            {
                'skill_name': mapping.skill_name,
                'weight': float(mapping.weight),
                'skill_category': mapping.skill_category
            }
            for mapping in skill_mappings
        ]

    if not skill_mappings_data:
        return {}

    # Calculate total weight
    total_weight = sum(mapping['weight'] for mapping in skill_mappings_data)

    if total_weight == 0:
        return {}

    # Distribute base points proportionally by weight
    skill_points = {}
    for mapping in skill_mappings_data:
        weight = mapping['weight']
        points = (weight / total_weight) * base_points
        # Round to 1 decimal place
        skill_points[mapping['skill_name']] = round(points, 1)

    return skill_points


def convert_skill_points_to_xp(
    db: Session,
    skill_points: Dict[str, float]
) -> int:
    """
    Convert skill points to bonus XP based on conversion rates.

    Args:
        db: Database session
        skill_points: Dictionary of skill_name -> points

    Returns:
        Total bonus XP to award
    """
    if not skill_points:
        return 0

    total_xp = 0

    # Get all conversion rates (cached in memory for performance)
    conversion_rates = {
        rate.skill_category: rate.xp_per_point
        for rate in db.query(SkillPointConversionRate).all()
    }

    # Get skill mappings to determine category for each skill
    skill_categories = {}
    for skill_name in skill_points.keys():
        mapping = db.query(TournamentSkillMapping).filter(
            TournamentSkillMapping.skill_name == skill_name
        ).first()
        if mapping and mapping.skill_category:
            skill_categories[skill_name] = mapping.skill_category

    # Calculate XP for each skill
    for skill_name, points in skill_points.items():
        category = skill_categories.get(skill_name, "football_skill")  # Default to football_skill
        xp_per_point = conversion_rates.get(category, 10)  # Default to 10 if not found
        total_xp += int(points * xp_per_point)

    return total_xp


def update_skill_assessments(
    db: Session,
    user_id: int,
    skill_points: Dict[str, float],
    assessed_by_id: Optional[int] = None
) -> None:
    """
    Update football skill assessments with earned skill points.

    Note: This function currently skips updating FootballSkillAssessment because
    tournaments award skill points directly to users, not to specific licenses.
    FootballSkillAssessment uses user_license_id, not user_id.

    Future enhancement: Create a tournament-specific skill tracking table
    or map tournament skills to user licenses appropriately.

    Args:
        db: Database session
        user_id: Player user ID
        skill_points: Dictionary of skill_name -> points
        assessed_by_id: ID of admin/instructor who triggered the assessment (optional)
    """
    # TODO: Implement tournament skill tracking
    # For now, skill points are recorded in TournamentParticipation.skill_points_awarded
    # and contribute to XP bonus, but don't update FootballSkillAssessment
    pass


def record_tournament_participation(
    db: Session,
    user_id: int,
    tournament_id: int,
    placement: Optional[int],
    skill_points: Dict[str, float],
    base_xp: int,
    credits: int,
    assessed_by_id: Optional[int] = None
) -> TournamentParticipation:
    """
    Record tournament participation and update player skill assessments.

    This is the DATA layer - records numerical rewards only.
    Visual badges are handled separately by tournament_badge_service.py

    Args:
        db: Database session
        user_id: Player user ID
        tournament_id: Tournament (semester) ID
        placement: Player placement (1, 2, 3, or None)
        skill_points: Dictionary of skill_name -> points
        base_xp: Base XP from placement
        credits: Credits from placement
        assessed_by_id: ID of admin/instructor who triggered the reward

    Returns:
        Created TournamentParticipation record
    """
    # Calculate bonus XP from skill points
    bonus_xp = convert_skill_points_to_xp(db, skill_points)
    total_xp = base_xp + bonus_xp

    # Update skill assessments
    if skill_points:
        update_skill_assessments(db, user_id, skill_points, assessed_by_id)

    # ── Phase 1: upsert placement + rewards (no skill_rating_delta yet) ──────────
    # skill_rating_delta requires placement to be visible in DB before computing.
    existing_participation = db.query(TournamentParticipation).filter(
        TournamentParticipation.user_id == user_id,
        TournamentParticipation.semester_id == tournament_id
    ).first()

    if existing_participation:
        existing_participation.placement = placement
        existing_participation.skill_points_awarded = skill_points if skill_points else None
        existing_participation.xp_awarded = total_xp
        existing_participation.credits_awarded = credits
        participation = existing_participation
    else:
        participation = TournamentParticipation(
            user_id=user_id,
            semester_id=tournament_id,
            placement=placement,
            skill_points_awarded=skill_points if skill_points else None,
            xp_awarded=total_xp,
            credits_awarded=credits
        )
        db.add(participation)

    # Flush so placement is visible to the skill delta query (autoflush may handle
    # this, but an explicit flush guarantees it regardless of session config)
    db.flush()

    # ── Phase 2: compute isolated per-tournament EMA delta and write back ────────
    from app.services.skill_progression_service import compute_single_tournament_skill_delta
    rating_delta = compute_single_tournament_skill_delta(db, user_id, tournament_id) or None
    participation.skill_rating_delta = rating_delta

    # Create XP transaction for bonus XP (if any)
    if bonus_xp > 0:
        from app.models.user import User
        tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
        tournament_name = tournament.name if tournament else f"Tournament #{tournament_id}"

        # R07: Atomic XP balance increment — prevents lost-update race when two concurrent
        # distributions for different tournaments both read the same stale xp_balance.
        new_balance = db.execute(
            text(
                "UPDATE users SET xp_balance = xp_balance + :delta "
                "WHERE id = :uid RETURNING xp_balance"
            ),
            {"delta": bonus_xp, "uid": user_id},
        ).scalar() or 0

        # R06: Idempotency key prevents duplicate XP grants on concurrent distribution retry.
        xp_idempotency_key = f"reward_xp_{tournament_id}_{user_id}"
        xp_transaction = XPTransaction(
            user_id=user_id,
            transaction_type="TOURNAMENT_SKILL_BONUS",
            amount=bonus_xp,
            balance_after=new_balance,
            description=f"Skill point bonus from {tournament_name}",
            idempotency_key=xp_idempotency_key,
            semester_id=tournament_id,
        )
        sp_xp = db.begin_nested()
        db.add(xp_transaction)
        try:
            sp_xp.commit()
        except IntegrityError:
            sp_xp.rollback()
            logger.debug(
                "record_tournament_participation: XP transaction idempotency key collision "
                "for user=%d tournament=%d — skipping duplicate insert.",
                user_id, tournament_id,
            )

    # Create credit transaction and update credit balance (if credits awarded)
    if credits > 0:
        from app.models.user import User
        from app.models.credit_transaction import CreditTransaction

        tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
        tournament_name = tournament.name if tournament else f"Tournament #{tournament_id}"

        # Determine rank display
        if placement == 1:
            rank_display = "#1"
        elif placement == 2:
            rank_display = "#2"
        elif placement == 3:
            rank_display = "#3"
        else:
            rank_display = f"#{placement}" if placement else "participation"

        # R07: Atomic credit balance increment — prevents lost-update race.
        new_credit_balance = db.execute(
            text(
                "UPDATE users SET credit_balance = credit_balance + :delta "
                "WHERE id = :uid RETURNING credit_balance"
            ),
            {"delta": credits, "uid": user_id},
        ).scalar() or 0

        # Generate idempotency key for credit transaction (R06)
        idempotency_key = f"tournament_reward_{tournament_id}_{user_id}_{placement}"

        credit_transaction = CreditTransaction(
            user_id=user_id,
            transaction_type="TOURNAMENT_REWARD",
            amount=credits,
            balance_after=new_credit_balance,
            description=f"Tournament '{tournament_name}' - Rank {rank_display} reward",
            idempotency_key=idempotency_key,
            semester_id=tournament_id,
        )
        sp_cr = db.begin_nested()
        db.add(credit_transaction)
        try:
            sp_cr.commit()
        except IntegrityError:
            sp_cr.rollback()
            logger.debug(
                "record_tournament_participation: credit transaction idempotency key collision "
                "for user=%d tournament=%d — skipping duplicate insert.",
                user_id, tournament_id,
            )

    return participation


def get_player_tournament_history(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Dict], int]:
    """
    Get comprehensive tournament history for a player.

    Args:
        db: Database session
        user_id: Player user ID
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        Tuple of (list of tournament dicts, total count)
    """
    # Query participations with tournament info
    query = db.query(
        TournamentParticipation,
        Semester
    ).join(
        Semester, TournamentParticipation.semester_id == Semester.id
    ).filter(
        TournamentParticipation.user_id == user_id
    ).order_by(
        desc(TournamentParticipation.achieved_at)
    )

    total_count = query.count()
    participations = query.limit(limit).offset(offset).all()

    results = []
    for participation, semester in participations:
        results.append({
            "tournament_id": semester.id,
            "tournament_name": semester.name,
            "tournament_format": semester.format,
            "specialization": semester.specialization_type,
            "start_date": semester.start_date.isoformat() if semester.start_date else None,
            "end_date": semester.end_date.isoformat() if semester.end_date else None,
            "placement": participation.placement,
            "skill_points_awarded": participation.skill_points_awarded,
            "xp_awarded": participation.xp_awarded,
            "credits_awarded": participation.credits_awarded,
            "achieved_at": participation.achieved_at.isoformat()
        })

    return results, total_count


def get_player_participation_stats(
    db: Session,
    user_id: int
) -> Dict:
    """
    Get aggregate participation statistics for a player.

    Args:
        db: Database session
        user_id: Player user ID

    Returns:
        Dictionary with aggregate stats
    """
    # Count total tournaments
    total_tournaments = db.query(func.count(TournamentParticipation.id)).filter(
        TournamentParticipation.user_id == user_id
    ).scalar() or 0

    # Count placements
    first_places = db.query(func.count(TournamentParticipation.id)).filter(
        TournamentParticipation.user_id == user_id,
        TournamentParticipation.placement == 1
    ).scalar() or 0

    second_places = db.query(func.count(TournamentParticipation.id)).filter(
        TournamentParticipation.user_id == user_id,
        TournamentParticipation.placement == 2
    ).scalar() or 0

    third_places = db.query(func.count(TournamentParticipation.id)).filter(
        TournamentParticipation.user_id == user_id,
        TournamentParticipation.placement == 3
    ).scalar() or 0

    # Sum XP and credits
    xp_sum = db.query(func.sum(TournamentParticipation.xp_awarded)).filter(
        TournamentParticipation.user_id == user_id
    ).scalar() or 0

    credits_sum = db.query(func.sum(TournamentParticipation.credits_awarded)).filter(
        TournamentParticipation.user_id == user_id
    ).scalar() or 0

    # Calculate total skill points per skill
    participations = db.query(TournamentParticipation).filter(
        TournamentParticipation.user_id == user_id,
        TournamentParticipation.skill_points_awarded.isnot(None)
    ).all()

    skill_totals = {}
    for participation in participations:
        if participation.skill_points_awarded:
            for skill_name, points in participation.skill_points_awarded.items():
                skill_totals[skill_name] = skill_totals.get(skill_name, 0) + points

    # Find top skill
    top_skill = None
    top_skill_points = 0
    if skill_totals:
        top_skill = max(skill_totals, key=skill_totals.get)
        top_skill_points = skill_totals[top_skill]

    return {
        "total_tournaments": total_tournaments,
        "first_places": first_places,
        "second_places": second_places,
        "third_places": third_places,
        "total_xp_earned": int(xp_sum),
        "total_credits_earned": int(credits_sum),
        "skill_totals": skill_totals,
        "top_skill": top_skill,
        "top_skill_points": top_skill_points
    }
