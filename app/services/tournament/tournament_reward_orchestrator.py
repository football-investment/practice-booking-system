"""
Tournament Reward Orchestrator

Coordinates both participation rewards (skill/XP) and visual badges.
Provides unified interface for reward distribution.
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.models.semester import Semester
from app.models.tournament_ranking import TournamentRanking
from app.models.user import User
from app.schemas.tournament_rewards import (
    TournamentRewardResult,
    ParticipationReward,
    BadgeReward,
    SkillPointsAwarded,
    BadgeAwarded,
    BulkRewardDistributionResult,
    RewardPolicy,
    BadgeEvaluationContext
)
from app.schemas.reward_config import TournamentRewardConfig

# Import both service modules
from app.services.tournament import tournament_participation_service as participation_service
from app.services.tournament import tournament_badge_service as badge_service
from app.services import skill_progression_service

logger = logging.getLogger(__name__)

# Default reward policy (fallback)
DEFAULT_REWARD_POLICY = RewardPolicy()


def load_reward_policy_from_config(
    db: Session,
    tournament_id: int
) -> RewardPolicy:
    """
    Load reward policy from tournament's reward_config JSONB field.

    🎁 V2: Parses saved TournamentRewardConfig and converts to RewardPolicy.
    Falls back to DEFAULT_REWARD_POLICY if no config found.

    Args:
        db: Database session
        tournament_id: Tournament (semester) ID

    Returns:
        RewardPolicy object (from config or default)
    """
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament or not tournament.reward_config:
        logger.info(f"No reward config found for tournament {tournament_id}, using default policy")
        return DEFAULT_REWARD_POLICY

    try:
        # Parse reward_config JSONB to TournamentRewardConfig
        config = TournamentRewardConfig(**tournament.reward_config)

        # Extract placement rewards with XP multipliers
        first_place = config.first_place
        second_place = config.second_place
        third_place = config.third_place
        participation = config.participation

        # Build RewardPolicy from config
        policy = RewardPolicy(
            tournament_type=config.template_name or "custom",
            # 1st place
            first_place_xp=int(500 * first_place.xp_multiplier) if first_place else 500,
            first_place_credits=first_place.credits if first_place else 100,
            # 2nd place
            second_place_xp=int(300 * second_place.xp_multiplier) if second_place else 300,
            second_place_credits=second_place.credits if second_place else 50,
            # 3rd place
            third_place_xp=int(200 * third_place.xp_multiplier) if third_place else 200,
            third_place_credits=third_place.credits if third_place else 25,
            # Participation
            participant_xp=int(50 * participation.xp_multiplier) if participation else 50,
            participant_credits=participation.credits if participation else 0
        )

        logger.info(f"Loaded reward policy from config for tournament {tournament_id}: {config.template_name}")
        return policy

    except Exception as e:
        logger.error(f"Failed to parse reward config for tournament {tournament_id}: {e}")
        return DEFAULT_REWARD_POLICY


def get_placement_rewards(placement: Optional[int], policy: RewardPolicy = DEFAULT_REWARD_POLICY) -> Dict:
    """
    Get XP and credits for a placement based on reward policy.

    Args:
        placement: Player placement (1, 2, 3, or None)
        policy: Reward policy to use

    Returns:
        Dictionary with xp and credits
    """
    if placement == 1:
        return {"xp": policy.first_place_xp, "credits": policy.first_place_credits}
    elif placement == 2:
        return {"xp": policy.second_place_xp, "credits": policy.second_place_credits}
    elif placement == 3:
        return {"xp": policy.third_place_xp, "credits": policy.third_place_credits}
    else:
        return {"xp": policy.participant_xp, "credits": policy.participant_credits}


def build_badge_evaluation_context(
    db: Session,
    user_id: int,
    tournament_id: int,
    placement: Optional[int],
    total_participants: int
) -> BadgeEvaluationContext:
    """
    Build evaluation context for badge awarding decisions.

    Gathers all relevant data for determining which badges to award.
    """
    # Get tournament info
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    # Get user's previous tournament history
    from app.models.tournament_achievement import TournamentParticipation
    previous_participations = db.query(TournamentParticipation).filter(
        TournamentParticipation.user_id == user_id,
        TournamentParticipation.semester_id != tournament_id
    ).all()

    previous_count = len(previous_participations)
    previous_placements = [p.placement for p in previous_participations if p.placement]

    # Calculate consecutive wins
    consecutive_wins = 0
    for p in sorted(previous_participations, key=lambda x: x.achieved_at, reverse=True):
        if p.placement == 1:
            consecutive_wins += 1
        else:
            break

    return BadgeEvaluationContext(
        user_id=user_id,
        tournament_id=tournament_id,
        placement=placement,
        total_participants=total_participants,
        previous_tournaments_count=previous_count,
        previous_placements=previous_placements,
        consecutive_wins=consecutive_wins,
        tournament_format=tournament.format if tournament else "",
        measurement_unit=tournament.measurement_unit if tournament else None
    )


def distribute_rewards_for_user(
    db: Session,
    user_id: int,
    tournament_id: int,
    placement: Optional[int],
    total_participants: int,
    reward_policy: RewardPolicy = DEFAULT_REWARD_POLICY,
    distributed_by: Optional[int] = None,
    force_redistribution: bool = False,
    is_sandbox_mode: bool = False
) -> TournamentRewardResult:
    """
    Distribute both participation rewards and badges for a single user.

    🔒 IDEMPOTENT: Checks if rewards already distributed for (user_id, tournament_id).
    Will not double-award unless force_redistribution=True.

    This is the main orchestration function that coordinates:
    1. Skill point calculation and participation recording (DATA layer)
    2. Badge awarding based on achievements (UI layer)

    Args:
        db: Database session
        user_id: Player user ID
        tournament_id: Tournament ID
        placement: Final placement (1, 2, 3, or None)
        total_participants: Total number of participants
        reward_policy: Custom reward policy (optional)
        distributed_by: Admin/instructor who triggered distribution
        force_redistribution: If True, allows re-distribution (updates existing records)
        is_sandbox_mode: If True, skip skill profile persistence (sandbox isolation)

    Returns:
        TournamentRewardResult with both participation and badge data

    Raises:
        ValueError: If rewards already distributed and force_redistribution=False
    """
    from app.models.tournament_achievement import TournamentParticipation

    # ========================================================================
    # 🔒 IDEMPOTENCY GUARD: Check if already distributed
    # ========================================================================
    existing_participation = db.query(TournamentParticipation).filter(
        TournamentParticipation.user_id == user_id,
        TournamentParticipation.semester_id == tournament_id
    ).first()

    if existing_participation and not force_redistribution:
        # Already distributed - return existing summary
        return get_user_reward_summary(db, user_id, tournament_id)

    # Get tournament info
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    tournament_name = tournament.name if tournament else f"Tournament #{tournament_id}"

    # ========================================================================
    # STEP 1: PARTICIPATION REWARDS (Skill Points + XP + Credits)
    # ========================================================================

    # Get base rewards for placement
    placement_rewards = get_placement_rewards(placement, reward_policy)
    base_xp = placement_rewards["xp"]
    credits = placement_rewards["credits"]

    # Calculate skill points
    skill_points = participation_service.calculate_skill_points_for_placement(
        db, tournament_id, placement
    )

    # Convert skill points to bonus XP
    bonus_xp = participation_service.convert_skill_points_to_xp(db, skill_points)
    total_xp = base_xp + bonus_xp

    # Record participation
    participation_record = participation_service.record_tournament_participation(
        db, user_id, tournament_id, placement, skill_points, base_xp, credits, distributed_by
    )

    # ========================================================================
    # STEP 1.5: APPLY SKILL DELTAS TO PLAYER PROFILE (Dynamic Progression)
    # ========================================================================
    # 🧪 SANDBOX MODE GUARD: Skip skill persistence in sandbox to maintain isolation
    if is_sandbox_mode:
        logger.info(
            f"🧪 SANDBOX MODE: Skipping skill profile persistence for user {user_id} "
            f"(skills calculated in-memory only for verdict)"
        )
    else:
        # Apply tournament skill deltas to player's football_skills profile
        # This updates UserLicense.football_skills with calculated deltas
        try:
            # Get user's active license
            from app.models.license import UserLicense
            active_license = db.query(UserLicense).filter(
                UserLicense.user_id == user_id,
                UserLicense.is_active == True
            ).first()

            # 🔥 V2 SKILL PROGRESSION: Skills are calculated on-the-fly from tournament placements
            # No need to "apply" deltas - get_skill_profile() automatically calculates from all participations
            if active_license and participation_record:
                logger.info(
                    f"✅ V2: Skills will be calculated dynamically from placement: "
                    f"user_id={user_id}, license_id={active_license.id}, placement={participation_record.placement}"
                )
            else:
                logger.warning(
                    f"Could not track skill progression: "
                    f"user_id={user_id}, has_license={active_license is not None}, "
                    f"has_participation={participation_record is not None}"
                )
        except Exception as e:
            logger.error(f"Failed to apply skill deltas for user {user_id}: {e}", exc_info=True)
            # Don't fail the entire reward distribution on skill progression errors
            # Continue with badge awarding

    # Build participation reward DTO
    skill_points_awarded = [
        SkillPointsAwarded(
            skill_name=skill_name,
            points=points,
            skill_category=None  # TODO: Get from mapping
        )
        for skill_name, points in skill_points.items()
    ]

    participation_reward = ParticipationReward(
        user_id=user_id,
        placement=placement,
        skill_points=skill_points_awarded,
        base_xp=base_xp,
        bonus_xp=bonus_xp,
        total_xp=total_xp,
        credits=credits
    )

    # ========================================================================
    # STEP 2: BADGE REWARDS (Visual Achievements)
    # ========================================================================

    awarded_badges = []

    # Award placement-based badges (Champion, Runner-Up, Third Place)
    if placement is not None and placement <= 3:
        placement_badges = badge_service.award_placement_badges(
            db, user_id, tournament_id, placement, total_participants
        )
        awarded_badges.extend(placement_badges)

    # Award participation badge (includes first tournament check)
    participation_badge = badge_service.award_participation_badge(
        db, user_id, tournament_id
    )
    awarded_badges.append(participation_badge)

    # Check and award milestone badges (Veteran, Legend, Triple Crown)
    milestone_badges = badge_service.check_and_award_milestone_badges(
        db, user_id, tournament_id
    )
    awarded_badges.extend(milestone_badges)

    # TODO: Award achievement badges (Undefeated, Comeback King, etc.)
    # This requires additional game data analysis - implement in Phase 2

    # Build badge reward DTO
    badges_awarded = [
        BadgeAwarded(
            badge_type=badge.badge_type,
            badge_category=badge.badge_category,
            title=badge.title,
            description=badge.description,
            icon=badge.icon,
            rarity=badge.rarity,
            metadata=badge.badge_metadata
        )
        for badge in awarded_badges
    ]

    # Determine rarest badge
    rarity_order = {"LEGENDARY": 1, "EPIC": 2, "RARE": 3, "UNCOMMON": 4, "COMMON": 5}
    rarest_badge = None
    if badges_awarded:
        rarest = min(badges_awarded, key=lambda b: rarity_order.get(b.rarity, 99))
        rarest_badge = rarest.rarity

    badge_reward = BadgeReward(
        user_id=user_id,
        badges=badges_awarded,
        total_badges_earned=len(badges_awarded),
        rarest_badge=rarest_badge
    )

    # ========================================================================
    # STEP 3: BUILD UNIFIED RESULT
    # ========================================================================

    result = TournamentRewardResult(
        user_id=user_id,
        tournament_id=tournament_id,
        tournament_name=tournament_name,
        participation=participation_reward,
        badges=badge_reward,
        distributed_at=datetime.now(),
        distributed_by=distributed_by
    )

    # Commit all changes
    db.commit()

    return result


def distribute_rewards_for_tournament(
    db: Session,
    tournament_id: int,
    reward_policy: Optional[RewardPolicy] = None,
    distributed_by: Optional[int] = None,
    force_redistribution: bool = False,
    is_sandbox_mode: bool = False
) -> BulkRewardDistributionResult:
    """
    Distribute rewards for all participants in a tournament.

    🎁 V2: Automatically loads reward policy from tournament.reward_config.
    If no config found, falls back to DEFAULT_REWARD_POLICY.

    Args:
        db: Database session
        tournament_id: Tournament ID
        reward_policy: Custom reward policy (optional, overrides config)
        distributed_by: Admin/instructor who triggered distribution
        force_redistribution: If True, allow re-distribution of rewards
        is_sandbox_mode: If True, skip skill profile persistence (sandbox isolation)

    Returns:
        BulkRewardDistributionResult with all rewards
    """
    # Get tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    # 🎁 V2: Load reward policy from config (unless overridden)
    if reward_policy is None:
        reward_policy = load_reward_policy_from_config(db, tournament_id)
        logger.info(f"Using reward policy from config for tournament {tournament_id}")

    # Get all rankings
    rankings = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).all()

    if not rankings:
        raise ValueError(f"No rankings found for tournament {tournament_id}")

    total_participants = len(rankings)
    rewards_distributed = []

    # Distribute rewards for each participant
    for ranking in rankings:
        if ranking.user_id is None:
            continue  # Skip team rankings (for now)

        # Check if already distributed
        from app.models.tournament_achievement import TournamentParticipation
        existing = db.query(TournamentParticipation).filter(
            TournamentParticipation.user_id == ranking.user_id,
            TournamentParticipation.semester_id == tournament_id
        ).first()

        if existing and not force_redistribution:
            # Skip - already distributed
            continue

        # Distribute rewards (force_redistribution and is_sandbox_mode passed through)
        result = distribute_rewards_for_user(
            db, ranking.user_id, tournament_id, ranking.rank,
            total_participants, reward_policy, distributed_by, force_redistribution, is_sandbox_mode
        )
        rewards_distributed.append(result)

    # Build summary
    total_xp_awarded = sum(r.participation.total_xp for r in rewards_distributed)
    total_credits_awarded = sum(r.participation.credits for r in rewards_distributed)
    total_badges_awarded = sum(r.badges.total_badges_earned for r in rewards_distributed)

    placement_counts = {1: 0, 2: 0, 3: 0, None: 0}
    for r in rewards_distributed:
        placement = r.participation.placement
        if placement in placement_counts:
            placement_counts[placement] += 1
        elif placement is None:
            placement_counts[None] += 1

    summary = {
        "total_xp_awarded": total_xp_awarded,
        "total_credits_awarded": total_credits_awarded,
        "total_badges_awarded": total_badges_awarded,
        "placement_distribution": {
            "first_place": placement_counts[1],
            "second_place": placement_counts[2],
            "third_place": placement_counts[3],
            "participants": placement_counts[None]
        }
    }

    return BulkRewardDistributionResult(
        tournament_id=tournament_id,
        tournament_name=tournament.name,
        total_participants=total_participants,
        rewards_distributed=rewards_distributed,
        distribution_summary=summary,
        distributed_at=datetime.now(),
        distributed_by=distributed_by
    )


def get_user_reward_summary(
    db: Session,
    user_id: int,
    tournament_id: int
) -> Optional[TournamentRewardResult]:
    """
    Get reward summary for a user in a specific tournament.

    Fetches existing participation and badge data.
    """
    from app.models.tournament_achievement import TournamentParticipation, TournamentBadge

    # Get participation record
    participation = db.query(TournamentParticipation).filter(
        TournamentParticipation.user_id == user_id,
        TournamentParticipation.semester_id == tournament_id
    ).first()

    if not participation:
        return None

    # Get tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    tournament_name = tournament.name if tournament else f"Tournament #{tournament_id}"

    # Build participation reward
    skill_points_awarded = []
    if participation.skill_points_awarded:
        skill_points_awarded = [
            SkillPointsAwarded(skill_name=k, points=v)
            for k, v in participation.skill_points_awarded.items()
        ]

    participation_reward = ParticipationReward(
        user_id=user_id,
        placement=participation.placement,
        skill_points=skill_points_awarded,
        base_xp=participation.xp_awarded,  # Note: includes bonus
        bonus_xp=0,  # Not stored separately
        total_xp=participation.xp_awarded,
        credits=participation.credits_awarded
    )

    # Get badges
    badges = db.query(TournamentBadge).filter(
        TournamentBadge.user_id == user_id,
        TournamentBadge.semester_id == tournament_id
    ).all()

    badges_awarded = [
        BadgeAwarded(
            badge_type=b.badge_type,
            badge_category=b.badge_category,
            title=b.title,
            description=b.description,
            icon=b.icon,
            rarity=b.rarity,
            metadata=b.badge_metadata
        )
        for b in badges
    ]

    # Determine rarest badge
    rarity_order = {"LEGENDARY": 1, "EPIC": 2, "RARE": 3, "UNCOMMON": 4, "COMMON": 5}
    rarest_badge = None
    if badges_awarded:
        rarest = min(badges_awarded, key=lambda b: rarity_order.get(b.rarity, 99))
        rarest_badge = rarest.rarity

    badge_reward = BadgeReward(
        user_id=user_id,
        badges=badges_awarded,
        total_badges_earned=len(badges_awarded),
        rarest_badge=rarest_badge
    )

    return TournamentRewardResult(
        user_id=user_id,
        tournament_id=tournament_id,
        tournament_name=tournament_name,
        participation=participation_reward,
        badges=badge_reward,
        distributed_at=participation.achieved_at,
        distributed_by=None  # Not tracked in current schema
    )
