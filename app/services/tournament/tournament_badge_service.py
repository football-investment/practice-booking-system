"""
Tournament Badge Service

Handles visual achievement badges for tournaments (UI LAYER).
Separate from skill/XP rewards which are handled by tournament_participation_service.py

Badge System:
- Icons: Emoji-based (🥇, 🥈, 🥉, 🏆, ⚽, 🌟, etc.)
- Categories: PLACEMENT, PARTICIPATION, ACHIEVEMENT, MILESTONE, SPECIALIZATION
- Rarity: COMMON, UNCOMMON, RARE, EPIC, LEGENDARY
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import logging

from app.models.tournament_achievement import (
    TournamentBadge,
    TournamentBadgeType,
    TournamentBadgeCategory,
    TournamentBadgeRarity
)
from app.models.semester import Semester
from app.models.tournament_ranking import TournamentRanking
from app.models.session import Session as SessionModel
from app.schemas.reward_config import TournamentRewardConfig

logger = logging.getLogger(__name__)


# Badge definitions with icons, titles, and descriptions
BADGE_DEFINITIONS = {
    TournamentBadgeType.CHAMPION: {
        "category": TournamentBadgeCategory.PLACEMENT,
        "icon": "🥇",
        "title_template": "Champion",
        "description_template": "Claimed 1st place in {tournament_name}",
        "rarity": TournamentBadgeRarity.EPIC
    },
    TournamentBadgeType.RUNNER_UP: {
        "category": TournamentBadgeCategory.PLACEMENT,
        "icon": "🥈",
        "title_template": "Runner-Up",
        "description_template": "Secured 2nd place in {tournament_name}",
        "rarity": TournamentBadgeRarity.RARE
    },
    TournamentBadgeType.THIRD_PLACE: {
        "category": TournamentBadgeCategory.PLACEMENT,
        "icon": "🥉",
        "title_template": "Podium Finisher",
        "description_template": "Earned 3rd place in {tournament_name}",
        "rarity": TournamentBadgeRarity.RARE
    },
    TournamentBadgeType.PODIUM_FINISH: {
        "category": TournamentBadgeCategory.PLACEMENT,
        "icon": "🏆",
        "title_template": "Top 3 Finish",
        "description_template": "Reached the podium in {tournament_name}",
        "rarity": TournamentBadgeRarity.RARE
    },
    TournamentBadgeType.TOURNAMENT_PARTICIPANT: {
        "category": TournamentBadgeCategory.PARTICIPATION,
        "icon": "⚽",
        "title_template": "Tournament Participant",
        "description_template": "Competed in {tournament_name}",
        "rarity": TournamentBadgeRarity.COMMON
    },
    TournamentBadgeType.FIRST_TOURNAMENT: {
        "category": TournamentBadgeCategory.PARTICIPATION,
        "icon": "🌟",
        "title_template": "Tournament Debut",
        "description_template": "First ever tournament: {tournament_name}",
        "rarity": TournamentBadgeRarity.UNCOMMON
    },
    TournamentBadgeType.UNDEFEATED: {
        "category": TournamentBadgeCategory.ACHIEVEMENT,
        "icon": "💪",
        "title_template": "Undefeated",
        "description_template": "Won all rounds in {tournament_name}",
        "rarity": TournamentBadgeRarity.LEGENDARY
    },
    TournamentBadgeType.COMEBACK_KING: {
        "category": TournamentBadgeCategory.ACHIEVEMENT,
        "icon": "📈",
        "title_template": "Comeback Champion",
        "description_template": "Dramatic improvement in {tournament_name}",
        "rarity": TournamentBadgeRarity.EPIC
    },
    TournamentBadgeType.CONSISTENCY: {
        "category": TournamentBadgeCategory.ACHIEVEMENT,
        "icon": "🎯",
        "title_template": "Consistency Master",
        "description_template": "Highly consistent performance in {tournament_name}",
        "rarity": TournamentBadgeRarity.RARE
    },
    TournamentBadgeType.RECORD_BREAKER: {
        "category": TournamentBadgeCategory.ACHIEVEMENT,
        "icon": "⚡",
        "title_template": "Record Breaker",
        "description_template": "Set new tournament record in {tournament_name}",
        "rarity": TournamentBadgeRarity.LEGENDARY
    },
    TournamentBadgeType.TOURNAMENT_VETERAN: {
        "category": TournamentBadgeCategory.MILESTONE,
        "icon": "🎖️",
        "title_template": "Tournament Veteran",
        "description_template": "Competed in {count} tournaments",
        "rarity": TournamentBadgeRarity.RARE
    },
    TournamentBadgeType.TOURNAMENT_LEGEND: {
        "category": TournamentBadgeCategory.MILESTONE,
        "icon": "👑",
        "title_template": "Tournament Legend",
        "description_template": "Competed in {count} tournaments",
        "rarity": TournamentBadgeRarity.EPIC
    },
    TournamentBadgeType.TRIPLE_CROWN: {
        "category": TournamentBadgeCategory.MILESTONE,
        "icon": "🔥",
        "title_template": "Triple Crown",
        "description_template": "Won 3 consecutive tournaments",
        "rarity": TournamentBadgeRarity.LEGENDARY
    },
    TournamentBadgeType.SPEED_DEMON: {
        "category": TournamentBadgeCategory.SPECIALIZATION,
        "icon": "🏃",
        "title_template": "Speed Demon",
        "description_template": "Fastest time in {tournament_name}",
        "rarity": TournamentBadgeRarity.EPIC
    },
    TournamentBadgeType.ENDURANCE_MASTER: {
        "category": TournamentBadgeCategory.SPECIALIZATION,
        "icon": "🧘",
        "title_template": "Endurance Master",
        "description_template": "Longest hold in {tournament_name}",
        "rarity": TournamentBadgeRarity.EPIC
    },
    TournamentBadgeType.MARKSMAN: {
        "category": TournamentBadgeCategory.SPECIALIZATION,
        "icon": "🎯",
        "title_template": "Marksman",
        "description_template": "Highest accuracy in {tournament_name}",
        "rarity": TournamentBadgeRarity.EPIC
    }
}


def award_badge(
    db: Session,
    user_id: int,
    tournament_id: int,
    badge_type: str,
    metadata: Optional[Dict] = None
) -> TournamentBadge:
    """
    Award a visual tournament badge to a player.

    Args:
        db: Database session
        user_id: Player user ID
        tournament_id: Tournament (semester) ID
        badge_type: TournamentBadgeType constant
        metadata: Additional context data for the badge

    Returns:
        Created TournamentBadge
    """
    # Get tournament info
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    tournament_name = tournament.name if tournament else f"Tournament #{tournament_id}"

    # Get badge definition
    badge_def = BADGE_DEFINITIONS.get(badge_type)
    if not badge_def:
        raise ValueError(f"Unknown badge type: {badge_type}")

    # Format title and description
    title = badge_def["title_template"]
    description = badge_def["description_template"].format(
        tournament_name=tournament_name,
        count=metadata.get("count") if metadata else ""
    )

    # Check if badge already exists (prevent duplicates)
    existing_badge = db.query(TournamentBadge).filter(
        TournamentBadge.user_id == user_id,
        TournamentBadge.semester_id == tournament_id,
        TournamentBadge.badge_type == badge_type
    ).first()

    if existing_badge:
        return existing_badge  # Don't award duplicate badges

    # Create new badge
    badge = TournamentBadge(
        user_id=user_id,
        semester_id=tournament_id,
        badge_type=badge_type,
        badge_category=badge_def["category"],
        title=title,
        description=description,
        icon=badge_def["icon"],
        rarity=badge_def["rarity"],
        badge_metadata=metadata
    )
    db.add(badge)

    return badge


def award_placement_badges(
    db: Session,
    user_id: int,
    tournament_id: int,
    placement: int,
    total_participants: int
) -> List[TournamentBadge]:
    """
    Award placement-based badges (Champion, Runner-Up, Third Place).

    🎁 V2: Uses reward_config badge configurations if available, falls back to hardcoded logic.

    Args:
        db: Database session
        user_id: Player user ID
        tournament_id: Tournament ID
        placement: Final placement (1, 2, 3, etc.)
        total_participants: Total number of participants

    Returns:
        List of awarded badges
    """
    badges = []

    metadata = {
        "placement": placement,
        "total_participants": total_participants
    }

    # 🎁 V2: Try to load badge configs from reward_config
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    badge_configs = []

    if tournament and tournament.reward_config:
        try:
            # Parse reward_config JSONB to TournamentRewardConfig
            config = TournamentRewardConfig(**tournament.reward_config)

            # Get placement-specific badge configs
            placement_config = None
            if placement == 1 and config.first_place:
                placement_config = config.first_place
            elif placement == 2 and config.second_place:
                placement_config = config.second_place
            elif placement == 3 and config.third_place:
                placement_config = config.third_place

            # Extract enabled badges from placement config
            if placement_config and placement_config.badges:
                for badge_cfg in placement_config.badges:
                    if badge_cfg.enabled:
                        badge_configs.append({
                            'badge_type': badge_cfg.badge_type,
                            'icon': badge_cfg.icon,
                            'title': badge_cfg.title,
                            'description': badge_cfg.description,
                            'rarity': badge_cfg.rarity
                        })

            logger.info(f"Loaded {len(badge_configs)} badge configs from reward_config for placement {placement} in tournament {tournament_id}")

        except Exception as e:
            logger.error(f"Failed to parse badge configs from reward_config for tournament {tournament_id}: {e}")
            badge_configs = []

    # Award badges from config or fallback to hardcoded logic
    if badge_configs:
        # 🎁 V2: Award badges from reward_config
        for badge_cfg in badge_configs:
            # Check if badge already exists (prevent duplicates)
            existing_badge = db.query(TournamentBadge).filter(
                TournamentBadge.user_id == user_id,
                TournamentBadge.semester_id == tournament_id,
                TournamentBadge.badge_type == badge_cfg['badge_type']
            ).first()

            if not existing_badge:
                # Create custom badge from config
                tournament_name = tournament.name if tournament else f"Tournament #{tournament_id}"
                description = badge_cfg['description'].format(tournament_name=tournament_name) if badge_cfg['description'] else ""

                badge = TournamentBadge(
                    user_id=user_id,
                    semester_id=tournament_id,
                    badge_type=badge_cfg['badge_type'],
                    badge_category=TournamentBadgeCategory.PLACEMENT,
                    title=badge_cfg['title'],
                    description=description,
                    icon=badge_cfg['icon'],
                    rarity=badge_cfg['rarity'],
                    badge_metadata=metadata
                )
                db.add(badge)
                badges.append(badge)

    else:
        # Fallback: Use hardcoded badge logic
        logger.info(f"No reward config found, using hardcoded badge logic for placement {placement} in tournament {tournament_id}")

        if placement == 1:
            badges.append(award_badge(db, user_id, tournament_id, TournamentBadgeType.CHAMPION, metadata))
        elif placement == 2:
            badges.append(award_badge(db, user_id, tournament_id, TournamentBadgeType.RUNNER_UP, metadata))
        elif placement == 3:
            badges.append(award_badge(db, user_id, tournament_id, TournamentBadgeType.THIRD_PLACE, metadata))

        # Award podium badge for top 3
        if placement <= 3:
            badges.append(award_badge(db, user_id, tournament_id, TournamentBadgeType.PODIUM_FINISH, metadata))

    return badges


def award_participation_badge(
    db: Session,
    user_id: int,
    tournament_id: int
) -> TournamentBadge:
    """
    Award basic participation badge.

    Args:
        db: Database session
        user_id: Player user ID
        tournament_id: Tournament ID

    Returns:
        Participation badge
    """
    # Check if this is user's first tournament
    previous_count = db.query(func.count(TournamentBadge.id)).filter(
        TournamentBadge.user_id == user_id,
        TournamentBadge.badge_category == TournamentBadgeCategory.PARTICIPATION
    ).scalar() or 0

    if previous_count == 0:
        # First tournament - award special badge
        return award_badge(db, user_id, tournament_id, TournamentBadgeType.FIRST_TOURNAMENT)
    else:
        # Regular participation badge
        return award_badge(db, user_id, tournament_id, TournamentBadgeType.TOURNAMENT_PARTICIPANT)


def check_and_award_milestone_badges(
    db: Session,
    user_id: int,
    tournament_id: int
) -> List[TournamentBadge]:
    """
    Check and award milestone badges (Veteran, Legend, Triple Crown).

    Args:
        db: Database session
        user_id: Player user ID
        tournament_id: Current tournament ID

    Returns:
        List of awarded milestone badges
    """
    badges = []

    # Count total tournaments participated
    total_tournaments = db.query(func.count(TournamentBadge.id)).filter(
        TournamentBadge.user_id == user_id,
        TournamentBadge.badge_category.in_([
            TournamentBadgeCategory.PLACEMENT,
            TournamentBadgeCategory.PARTICIPATION
        ])
    ).scalar() or 0

    # Award Veteran badge at 5 tournaments
    if total_tournaments >= 5:
        veteran_exists = db.query(TournamentBadge).filter(
            TournamentBadge.user_id == user_id,
            TournamentBadge.badge_type == TournamentBadgeType.TOURNAMENT_VETERAN
        ).first()
        if not veteran_exists:
            badges.append(award_badge(
                db, user_id, tournament_id,
                TournamentBadgeType.TOURNAMENT_VETERAN,
                {"count": total_tournaments}
            ))

    # Award Legend badge at 10 tournaments
    if total_tournaments >= 10:
        legend_exists = db.query(TournamentBadge).filter(
            TournamentBadge.user_id == user_id,
            TournamentBadge.badge_type == TournamentBadgeType.TOURNAMENT_LEGEND
        ).first()
        if not legend_exists:
            badges.append(award_badge(
                db, user_id, tournament_id,
                TournamentBadgeType.TOURNAMENT_LEGEND,
                {"count": total_tournaments}
            ))

    # Check for Triple Crown (3 consecutive 1st places)
    recent_champions = db.query(TournamentBadge).filter(
        TournamentBadge.user_id == user_id,
        TournamentBadge.badge_type == TournamentBadgeType.CHAMPION
    ).order_by(desc(TournamentBadge.earned_at)).limit(3).all()

    if len(recent_champions) >= 3:
        triple_crown_exists = db.query(TournamentBadge).filter(
            TournamentBadge.user_id == user_id,
            TournamentBadge.badge_type == TournamentBadgeType.TRIPLE_CROWN
        ).first()
        if not triple_crown_exists:
            badges.append(award_badge(
                db, user_id, tournament_id,
                TournamentBadgeType.TRIPLE_CROWN
            ))

    return badges


def get_player_badges(
    db: Session,
    user_id: int,
    tournament_id: Optional[int] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Get player's tournament badges.

    Args:
        db: Database session
        user_id: Player user ID
        tournament_id: Optional filter by tournament
        limit: Maximum results

    Returns:
        List of badge dictionaries
    """
    query = db.query(TournamentBadge).filter(
        TournamentBadge.user_id == user_id
    )

    if tournament_id:
        query = query.filter(TournamentBadge.semester_id == tournament_id)

    badges = query.order_by(desc(TournamentBadge.earned_at)).limit(limit).all()

    return [badge.to_dict() for badge in badges]


def get_player_badge_showcase(
    db: Session,
    user_id: int
) -> Dict:
    """
    Get player's badge showcase for profile display.

    Returns rarest and most recent badges grouped by category.

    Args:
        db: Database session
        user_id: Player user ID

    Returns:
        Dictionary with badge showcase data
    """
    # Rarity order for sorting
    rarity_order = {
        TournamentBadgeRarity.LEGENDARY: 1,
        TournamentBadgeRarity.EPIC: 2,
        TournamentBadgeRarity.RARE: 3,
        TournamentBadgeRarity.UNCOMMON: 4,
        TournamentBadgeRarity.COMMON: 5
    }

    # Get all badges
    all_badges = db.query(TournamentBadge).filter(
        TournamentBadge.user_id == user_id
    ).all()

    # Group by category
    badges_by_category = {}
    for badge in all_badges:
        category = badge.badge_category
        if category not in badges_by_category:
            badges_by_category[category] = []
        badges_by_category[category].append(badge)

    # Get showcase badges (rarest + most recent per category)
    showcase = {
        "total_badges": len(all_badges),
        "rarest_badges": [],
        "recent_badges": [],
        "by_category": {}
    }

    # Rarest badges (top 5)
    sorted_by_rarity = sorted(all_badges, key=lambda b: rarity_order.get(b.rarity, 99))
    showcase["rarest_badges"] = [b.to_dict() for b in sorted_by_rarity[:5]]

    # Most recent badges (top 5)
    sorted_by_date = sorted(all_badges, key=lambda b: b.earned_at, reverse=True)
    showcase["recent_badges"] = [b.to_dict() for b in sorted_by_date[:5]]

    # Badges by category
    for category, badges in badges_by_category.items():
        showcase["by_category"][category] = {
            "count": len(badges),
            "badges": [b.to_dict() for b in badges[:3]]  # Top 3 per category
        }

    return showcase
