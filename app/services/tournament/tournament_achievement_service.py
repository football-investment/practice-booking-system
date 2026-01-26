"""
Tournament Achievement Service

Handles skill point calculation, achievement recording, and tournament history.
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.tournament_achievement import (
    TournamentSkillMapping,
    TournamentAchievement,
    SkillPointConversionRate
)
from app.models.semester import Semester
from app.models.tournament_ranking import TournamentRanking
from app.models.football_skill_assessment import FootballSkillAssessment
from app.models.xp_transaction import XPTransaction


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
) -> Dict[str, Decimal]:
    """
    Calculate skill points based on placement and tournament skill mappings.

    Args:
        db: Database session
        tournament_id: Tournament (semester) ID
        placement: Player placement (1, 2, 3, or None for participation)

    Returns:
        Dictionary of skill_name -> points earned
        Example: {"agility": Decimal("4.3"), "physical_fitness": Decimal("2.2")}
    """
    # Get base points for placement
    base_points = PLACEMENT_SKILL_POINTS.get(placement, PLACEMENT_SKILL_POINTS[None])

    # Get skill mappings for this tournament
    skill_mappings = db.query(TournamentSkillMapping).filter(
        TournamentSkillMapping.semester_id == tournament_id
    ).all()

    if not skill_mappings:
        return {}  # No skills mapped, return empty

    # Calculate total weight
    total_weight = sum(Decimal(str(mapping.weight)) for mapping in skill_mappings)

    if total_weight == 0:
        return {}

    # Distribute base points proportionally by weight
    skill_points = {}
    for mapping in skill_mappings:
        weight = Decimal(str(mapping.weight))
        points = (weight / total_weight) * Decimal(str(base_points))
        # Round to 1 decimal place
        skill_points[mapping.skill_name] = points.quantize(Decimal("0.1"))

    return skill_points


def convert_skill_points_to_xp(
    db: Session,
    skill_points: Dict[str, Decimal]
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
        total_xp += int(float(points) * xp_per_point)

    return total_xp


def update_skill_assessments(
    db: Session,
    user_id: int,
    skill_points: Dict[str, Decimal],
    assessed_by_id: Optional[int] = None
) -> None:
    """
    Update football skill assessments with earned skill points.

    Args:
        db: Database session
        user_id: Player user ID
        skill_points: Dictionary of skill_name -> points
        assessed_by_id: ID of admin/instructor who triggered the assessment (optional)
    """
    for skill_name, points in skill_points.items():
        # Check if assessment exists
        assessment = db.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.user_id == user_id,
            FootballSkillAssessment.skill_name == skill_name
        ).first()

        if assessment:
            # Update existing assessment
            assessment.points_earned += float(points)
            if assessment.points_total and assessment.points_total > 0:
                assessment.percentage = (assessment.points_earned / assessment.points_total) * 100
        else:
            # Create new assessment
            assessment = FootballSkillAssessment(
                user_id=user_id,
                skill_name=skill_name,
                points_earned=float(points),
                points_total=100.0,  # Default total
                percentage=(float(points) / 100.0) * 100,
                assessed_by=assessed_by_id
            )
            db.add(assessment)


def award_tournament_achievement(
    db: Session,
    user_id: int,
    tournament_id: int,
    placement: Optional[int],
    skill_points: Dict[str, Decimal],
    base_xp: int,
    credits: int,
    assessed_by_id: Optional[int] = None
) -> TournamentAchievement:
    """
    Record tournament achievement and update player skill assessments.

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
        Created TournamentAchievement record
    """
    # Calculate bonus XP from skill points
    bonus_xp = convert_skill_points_to_xp(db, skill_points)
    total_xp = base_xp + bonus_xp

    # Update skill assessments
    if skill_points:
        update_skill_assessments(db, user_id, skill_points, assessed_by_id)

    # Convert Decimal values to float for JSONB storage
    skill_points_json = {k: float(v) for k, v in skill_points.items()} if skill_points else None

    # Check if achievement already exists
    existing_achievement = db.query(TournamentAchievement).filter(
        TournamentAchievement.user_id == user_id,
        TournamentAchievement.semester_id == tournament_id
    ).first()

    if existing_achievement:
        # Update existing achievement
        existing_achievement.placement = placement
        existing_achievement.skill_points_awarded = skill_points_json
        existing_achievement.xp_awarded = total_xp
        existing_achievement.credits_awarded = credits
        achievement = existing_achievement
    else:
        # Create new achievement
        achievement = TournamentAchievement(
            user_id=user_id,
            semester_id=tournament_id,
            placement=placement,
            skill_points_awarded=skill_points_json,
            xp_awarded=total_xp,
            credits_awarded=credits
        )
        db.add(achievement)

    # Create XP transaction for bonus XP (if any)
    if bonus_xp > 0:
        tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
        tournament_name = tournament.name if tournament else f"Tournament #{tournament_id}"

        xp_transaction = XPTransaction(
            user_id=user_id,
            transaction_type="TOURNAMENT_SKILL_BONUS",
            amount=bonus_xp,
            description=f"Skill point bonus from {tournament_name}",
            semester_id=tournament_id
        )
        db.add(xp_transaction)

    return achievement


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
    # Query achievements with tournament info
    query = db.query(
        TournamentAchievement,
        Semester
    ).join(
        Semester, TournamentAchievement.semester_id == Semester.id
    ).filter(
        TournamentAchievement.user_id == user_id
    ).order_by(
        desc(TournamentAchievement.achieved_at)
    )

    total_count = query.count()
    achievements = query.limit(limit).offset(offset).all()

    results = []
    for achievement, semester in achievements:
        results.append({
            "tournament_id": semester.id,
            "tournament_name": semester.name,
            "tournament_format": semester.format,
            "specialization": semester.specialization_type,
            "start_date": semester.start_date.isoformat() if semester.start_date else None,
            "end_date": semester.end_date.isoformat() if semester.end_date else None,
            "placement": achievement.placement,
            "skill_points_awarded": achievement.skill_points_awarded,
            "xp_awarded": achievement.xp_awarded,
            "credits_awarded": achievement.credits_awarded,
            "achieved_at": achievement.achieved_at.isoformat()
        })

    return results, total_count


def get_player_achievement_stats(
    db: Session,
    user_id: int
) -> Dict:
    """
    Get aggregate achievement statistics for a player.

    Args:
        db: Database session
        user_id: Player user ID

    Returns:
        Dictionary with aggregate stats
    """
    # Count total tournaments
    total_tournaments = db.query(func.count(TournamentAchievement.id)).filter(
        TournamentAchievement.user_id == user_id
    ).scalar() or 0

    # Count placements
    first_places = db.query(func.count(TournamentAchievement.id)).filter(
        TournamentAchievement.user_id == user_id,
        TournamentAchievement.placement == 1
    ).scalar() or 0

    second_places = db.query(func.count(TournamentAchievement.id)).filter(
        TournamentAchievement.user_id == user_id,
        TournamentAchievement.placement == 2
    ).scalar() or 0

    third_places = db.query(func.count(TournamentAchievement.id)).filter(
        TournamentAchievement.user_id == user_id,
        TournamentAchievement.placement == 3
    ).scalar() or 0

    # Sum XP and credits
    xp_sum = db.query(func.sum(TournamentAchievement.xp_awarded)).filter(
        TournamentAchievement.user_id == user_id
    ).scalar() or 0

    credits_sum = db.query(func.sum(TournamentAchievement.credits_awarded)).filter(
        TournamentAchievement.user_id == user_id
    ).scalar() or 0

    # Calculate total skill points per skill
    achievements = db.query(TournamentAchievement).filter(
        TournamentAchievement.user_id == user_id,
        TournamentAchievement.skill_points_awarded.isnot(None)
    ).all()

    skill_totals = {}
    for achievement in achievements:
        if achievement.skill_points_awarded:
            for skill_name, points in achievement.skill_points_awarded.items():
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
