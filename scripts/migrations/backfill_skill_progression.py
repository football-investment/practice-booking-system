"""
Backfill Historical Tournament Skill Deltas

This script recalculates skill deltas from all historical tournament participations
and applies them to player profiles in chronological order.

Purpose:
- Create complete historical skill progression timeline
- Apply all past tournament rewards to UserLicense.football_skills
- Preserve baseline values from onboarding
- Calculate accurate current skill levels

Usage:
    python backfill_skill_progression.py [--dry-run]

Options:
    --dry-run: Preview changes without committing to database
"""

import sys
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.semester import Semester
from app.models.tournament_achievement import TournamentParticipation
from app.models.license import UserLicense
from app.schemas.reward_config import TournamentRewardConfig
from app.services.skill_progression_service import SkillProgressionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_completed_tournaments(db: Session) -> List[Semester]:
    """
    Get all completed tournaments with reward configs, sorted chronologically.

    Returns:
        List of completed tournament semesters
    """
    tournaments = db.query(Semester).filter(
        Semester.specialization_type.in_([
            'TOURNAMENT_SPEED',
            'TOURNAMENT_STAMINA',
            'TOURNAMENT_HYBRID',
            'TOURNAMENT_INDIVIDUAL_RANKING'
        ]),
        Semester.end_date.isnot(None)  # Only tournaments that have ended
    ).order_by(
        Semester.end_date.asc()  # Chronological order
    ).all()

    logger.info(f"Found {len(tournaments)} completed tournaments")
    return tournaments


def get_tournament_participations(
    db: Session,
    tournament_id: int
) -> List[TournamentParticipation]:
    """
    Get all participations for a tournament that have skill points awarded.

    Args:
        db: Database session
        tournament_id: Tournament (semester) ID

    Returns:
        List of participations with skill_points_awarded
    """
    participations = db.query(TournamentParticipation).filter(
        TournamentParticipation.semester_id == tournament_id,
        TournamentParticipation.skill_points_awarded.isnot(None)
    ).all()

    return [p for p in participations if p.skill_points_awarded]


def validate_skill_profile(
    skill_profile: Dict,
    expected_skills: List[str]
) -> bool:
    """
    Validate skill profile structure after backfill.

    Args:
        skill_profile: Updated skill profile
        expected_skills: List of skills that should be present

    Returns:
        True if valid, False otherwise
    """
    if not skill_profile:
        return False

    for skill_name in expected_skills:
        if skill_name not in skill_profile:
            continue

        skill_data = skill_profile[skill_name]

        # Check required fields
        required_fields = [
            "current_level", "baseline", "total_delta",
            "last_updated", "tournament_count"
        ]
        for field in required_fields:
            if field not in skill_data:
                logger.error(
                    f"Missing field '{field}' in skill '{skill_name}'"
                )
                return False

        # Validate values
        if not (0 <= skill_data["current_level"] <= 100):
            logger.error(
                f"Invalid current_level for '{skill_name}': "
                f"{skill_data['current_level']}"
            )
            return False

    return True


def backfill_tournament_skill_progression(dry_run: bool = False):
    """
    Backfill skill progression from historical tournaments.

    This function:
    1. Fetches all completed tournaments in chronological order
    2. For each tournament participation, recalculates skill deltas
    3. Applies deltas to UserLicense.football_skills
    4. Validates results

    Args:
        dry_run: If True, preview changes without committing
    """
    db = next(get_db())
    skill_service = SkillProgressionService(db)

    logger.info("=" * 80)
    logger.info("STARTING TOURNAMENT SKILL PROGRESSION BACKFILL")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("=" * 80)

    # Get all completed tournaments
    tournaments = get_completed_tournaments(db)

    if not tournaments:
        logger.warning("No completed tournaments found. Nothing to backfill.")
        return

    # Track statistics
    stats = {
        "tournaments_processed": 0,
        "tournaments_with_participations": 0,
        "total_participations": 0,
        "total_skills_updated": 0,
        "users_affected": set(),
        "errors": []
    }

    # Process each tournament chronologically
    for tournament in tournaments:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Processing: {tournament.name} ({tournament.tournament_code})")
        logger.info(f"Tournament ID: {tournament.id}")
        logger.info(f"End Date: {tournament.end_date}")
        logger.info(f"Type: {tournament.specialization_type}")

        try:
            # Get participations with skill points
            participations = get_tournament_participations(db, tournament.id)

            if not participations:
                logger.info(f"  No participations with skill points, skipping")
                stats["tournaments_processed"] += 1
                continue

            stats["tournaments_with_participations"] += 1
            logger.info(f"  Found {len(participations)} participations with rewards")

            # Display reward config info if available
            if tournament.reward_config:
                try:
                    config = TournamentRewardConfig(**tournament.reward_config)
                    enabled_skills = [
                        s.skill for s in config.enabled_skills if s.enabled
                    ]
                    logger.info(f"  Enabled skills: {', '.join(enabled_skills)}")
                except Exception as e:
                    logger.warning(f"  Could not parse reward config: {e}")

            # Process each participation
            for participation in participations:
                stats["total_participations"] += 1

                if not participation.user_license_id:
                    logger.warning(
                        f"  Participation {participation.id} has no user_license_id, "
                        f"skipping"
                    )
                    continue

                # Log participation details
                skill_count = len(participation.skill_points_awarded)
                logger.info(
                    f"  User {participation.user_id} "
                    f"(License {participation.user_license_id}): "
                    f"Placement {participation.placement}, "
                    f"{skill_count} skills"
                )

                # Display skill points
                for skill_name, raw_points in participation.skill_points_awarded.items():
                    delta = skill_service._calculate_delta(raw_points)
                    logger.info(f"    - {skill_name}: {raw_points:.1f} raw → {delta:.2f} delta")

                try:
                    # Apply skill deltas
                    if not dry_run:
                        updated_skills = skill_service.apply_tournament_skill_deltas(
                            user_license_id=participation.user_license_id,
                            tournament_participation_id=participation.id
                        )

                        # Validate result
                        expected_skills = list(participation.skill_points_awarded.keys())
                        if validate_skill_profile(updated_skills, expected_skills):
                            stats["total_skills_updated"] += skill_count
                            stats["users_affected"].add(participation.user_id)
                            logger.info(f"    ✓ Applied {skill_count} skill deltas")
                        else:
                            error_msg = (
                                f"Validation failed for participation "
                                f"{participation.id}"
                            )
                            logger.error(f"    ✗ {error_msg}")
                            stats["errors"].append(error_msg)
                    else:
                        # Dry run - just simulate
                        stats["total_skills_updated"] += skill_count
                        stats["users_affected"].add(participation.user_id)
                        logger.info(f"    ✓ [DRY RUN] Would apply {skill_count} deltas")

                except Exception as e:
                    error_msg = (
                        f"Failed to apply deltas for participation "
                        f"{participation.id}: {e}"
                    )
                    logger.error(f"    ✗ {error_msg}", exc_info=True)
                    stats["errors"].append(error_msg)

            stats["tournaments_processed"] += 1

        except Exception as e:
            error_msg = f"Failed to process tournament {tournament.id}: {e}"
            logger.error(f"✗ {error_msg}", exc_info=True)
            stats["errors"].append(error_msg)

    # Print summary
    logger.info(f"\n{'=' * 80}")
    logger.info("BACKFILL COMPLETE")
    logger.info(f"{'=' * 80}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"Tournaments processed: {stats['tournaments_processed']}")
    logger.info(
        f"Tournaments with participations: {stats['tournaments_with_participations']}"
    )
    logger.info(f"Total participations processed: {stats['total_participations']}")
    logger.info(f"Total skill updates: {stats['total_skills_updated']}")
    logger.info(f"Unique users affected: {len(stats['users_affected'])}")
    logger.info(f"Errors encountered: {len(stats['errors'])}")

    if stats["errors"]:
        logger.error("\nErrors encountered:")
        for i, error in enumerate(stats["errors"][:20], 1):  # Show first 20
            logger.error(f"  {i}. {error}")
        if len(stats["errors"]) > 20:
            logger.error(f"  ... and {len(stats['errors']) - 20} more")

    if dry_run:
        logger.info("\n🔍 This was a DRY RUN - no changes were committed to the database")
        logger.info("Run without --dry-run to apply changes")
    else:
        logger.info("\n✅ Changes have been committed to the database")

    db.close()


def print_sample_skill_profiles(db: Session, user_count: int = 5):
    """
    Print sample skill profiles after backfill for validation.

    Args:
        db: Database session
        user_count: Number of users to sample
    """
    logger.info(f"\n{'=' * 80}")
    logger.info("SAMPLE SKILL PROFILES (After Backfill)")
    logger.info(f"{'=' * 80}")

    # Get users with tournament participations
    participations = db.query(TournamentParticipation).filter(
        TournamentParticipation.user_license_id.isnot(None)
    ).group_by(
        TournamentParticipation.user_license_id
    ).limit(user_count).all()

    skill_service = SkillProgressionService(db)

    for participation in participations:
        license_id = participation.user_license_id

        license = db.query(UserLicense).filter(
            UserLicense.id == license_id
        ).first()

        if not license:
            continue

        logger.info(f"\nUser License ID: {license_id}")
        logger.info(f"User ID: {license.user_id}")
        logger.info(f"Specialization: {license.specialization_type}")

        skill_profile = skill_service.get_skill_profile(license_id)
        average = skill_service.calculate_average_level(license_id)

        logger.info(f"Average Skill Level: {average:.1f}")
        logger.info("Skills:")

        for skill_name, skill_data in sorted(skill_profile.items()):
            current = skill_data["current_level"]
            baseline = skill_data["baseline"]
            delta = skill_data["total_delta"]
            tournaments = skill_data["tournament_count"]
            tier = skill_service.get_skill_display_tier(current)
            emoji = skill_service.get_tier_emoji(tier)

            logger.info(
                f"  {skill_name:15} {emoji} {tier:12} "
                f"Current: {current:5.1f} | Baseline: {baseline:5.1f} | "
                f"Delta: {delta:+5.2f} | Tournaments: {tournaments}"
            )


if __name__ == "__main__":
    # Parse command line arguments
    dry_run = "--dry-run" in sys.argv

    # Run backfill
    backfill_tournament_skill_progression(dry_run=dry_run)

    # Show sample profiles (only in live mode)
    if not dry_run:
        db = next(get_db())
        print_sample_skill_profiles(db, user_count=5)
        db.close()
