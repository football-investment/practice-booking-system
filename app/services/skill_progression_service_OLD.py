"""
⚽ Skill Progression Service - Dynamic Player Skill Management

Handles:
- Tournament skill delta application
- Assessment skill delta application
- Skill decay for inactive players
- Dynamic skill level calculation (baseline + delta - decay)
- Average skill level recalculation
- JSONB format migration
- Configurable multipliers and caps
"""

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import Dict, Optional
from datetime import datetime, timezone
import logging

from ..models.license import UserLicense
from ..models.tournament_achievement import TournamentParticipation
from ..schemas.skill_progression_config import (
    SkillProgressionConfig,
    DEFAULT_SKILL_PROGRESSION_CONFIG
)

logger = logging.getLogger(__name__)


class SkillProgressionService:
    """
    Service for applying tournament and assessment skill deltas to player profiles.

    This service uses configurable parameters that can be overridden per-tournament
    or per-assessment via the SkillProgressionConfig model.
    """

    def __init__(
        self,
        db: Session,
        config: Optional[SkillProgressionConfig] = None
    ):
        """
        Initialize skill progression service.

        Args:
            db: Database session
            config: Custom configuration (defaults to DEFAULT_SKILL_PROGRESSION_CONFIG)
        """
        self.db = db
        self.config = config or DEFAULT_SKILL_PROGRESSION_CONFIG

        # Extract config values for easy access
        self.MAX_SKILL_LEVEL = self.config.max_skill_level
        self.MIN_SKILL_LEVEL = self.config.min_skill_level
        self.TOURNAMENT_DELTA_MULTIPLIER = self.config.tournament_delta_multiplier
        self.TOURNAMENT_MAX_CONTRIBUTION = self.config.tournament_max_contribution
        self.ASSESSMENT_DELTA_MULTIPLIER = self.config.assessment_delta_multiplier
        self.ASSESSMENT_MAX_CONTRIBUTION = self.config.assessment_max_contribution
        self.DECAY_ENABLED = self.config.decay_enabled
        self.DECAY_THRESHOLD_DAYS = self.config.decay_threshold_days
        self.DECAY_MAX_PERCENTAGE = self.config.decay_max_percentage
        self.DECAY_CURVE_STEEPNESS = self.config.decay_curve_steepness

    def apply_tournament_skill_deltas(
        self,
        user_license_id: int,
        tournament_participation_id: int
    ) -> Dict[str, Dict]:
        """
        Apply skill deltas from tournament to player profile

        Args:
            user_license_id: UserLicense ID
            tournament_participation_id: TournamentParticipation ID

        Returns:
            Updated skill profile

        Example:
            Input: participation.skill_points_awarded = {"speed": 5.7, "agility": 4.3}
            Output: Updated football_skills with +0.7 speed, +0.5 agility
        """
        # Get tournament participation
        participation = self.db.query(TournamentParticipation).filter(
            TournamentParticipation.id == tournament_participation_id
        ).first()

        if not participation or not participation.skill_points_awarded:
            return {}

        # Get user license
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license:
            raise ValueError(f"UserLicense {user_license_id} not found")

        # Ensure skills dict exists
        if not license.football_skills:
            license.football_skills = {}

        # Migrate old format if needed
        license.football_skills = self._ensure_new_format(license.football_skills)

        # Apply deltas
        for skill_name, raw_points in participation.skill_points_awarded.items():
            delta = self._calculate_delta(raw_points)
            license.football_skills = self._apply_skill_delta(
                license.football_skills,
                skill_name,
                delta
            )

        # Mark as modified (required for JSONB fields)
        flag_modified(license, 'football_skills')

        self.db.commit()

        return license.football_skills

    def _ensure_new_format(self, skills: Dict) -> Dict:
        """
        Migrate old format to new format if needed

        Old format: {"speed": 85.0, "agility": 80.0}
        New format: {"speed": {"current_level": 85.0, "baseline": 85.0, ...}}
        """
        if not skills:
            return {}

        # Check if already new format
        first_skill = next(iter(skills.values()), None)
        if isinstance(first_skill, dict) and "current_level" in first_skill:
            return skills  # Already new format

        # Migrate to new format with separated deltas
        new_skills = {}
        for skill_name, value in skills.items():
            new_skills[skill_name] = {
                "current_level": float(value),
                "baseline": float(value),
                "total_delta": 0.0,  # Kept for backward compatibility
                "tournament_delta": 0.0,  # NEW: Tournament contributions only
                "assessment_delta": 0.0,  # NEW: Assessment contributions only
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "assessment_count": 0,
                "tournament_count": 0
            }
        return new_skills

    def _calculate_delta(
        self,
        raw_points: float,
        source: str = "tournament"
    ) -> float:
        """
        Convert raw skill points to delta based on source.

        Args:
            raw_points: Raw points from tournament or assessment
            source: "tournament" or "assessment"

        Returns:
            Delta to apply

        Example:
            Tournament: raw_points=5.7 → 5.7 × 0.125 = 0.71
            Assessment: raw_points=10.0 → 10.0 × 0.20 = 2.0
        """
        if source == "assessment":
            multiplier = self.ASSESSMENT_DELTA_MULTIPLIER
        else:  # Default to tournament
            multiplier = self.TOURNAMENT_DELTA_MULTIPLIER

        return round(raw_points * multiplier, 2)

    def _apply_skill_delta(
        self,
        skills: Dict,
        skill_name: str,
        delta: float,
        source: str = "tournament"
    ) -> Dict:
        """
        Apply delta to a specific skill with source-specific caps.

        Caps:
        - Tournament: max +15 points from tournaments
        - Assessment: max +10 points from assessments
        - Overall: max 100.0 total (baseline + tournament + assessment)

        Args:
            skills: Current skill profile
            skill_name: Skill to update
            delta: Delta to apply
            source: "tournament" or "assessment"

        Returns:
            Updated skill profile
        """
        if skill_name not in skills:
            # Initialize new skill with separated deltas
            skills[skill_name] = {
                "current_level": 50.0,  # Default starting level
                "baseline": 50.0,
                "total_delta": 0.0,
                "tournament_delta": 0.0,
                "assessment_delta": 0.0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "assessment_count": 0,
                "tournament_count": 0
            }

        skill = skills[skill_name]
        baseline = skill["baseline"]

        # Get current deltas (with backward compatibility)
        tournament_delta = skill.get("tournament_delta", 0.0)
        assessment_delta = skill.get("assessment_delta", 0.0)

        # Apply delta with source-specific cap
        if source == "tournament":
            # Check tournament cap
            new_tournament_delta = tournament_delta + delta
            if new_tournament_delta > self.TOURNAMENT_MAX_CONTRIBUTION:
                # Cap reached, only apply partial delta
                delta = self.TOURNAMENT_MAX_CONTRIBUTION - tournament_delta
                new_tournament_delta = self.TOURNAMENT_MAX_CONTRIBUTION

            if delta > 0:  # Only apply if not capped
                tournament_delta = new_tournament_delta
                skill["tournament_delta"] = round(tournament_delta, 2)
                skill["tournament_count"] = skill.get("tournament_count", 0) + 1

        elif source == "assessment":
            # Check assessment cap
            new_assessment_delta = assessment_delta + delta
            if new_assessment_delta > self.ASSESSMENT_MAX_CONTRIBUTION:
                # Cap reached, only apply partial delta
                delta = self.ASSESSMENT_MAX_CONTRIBUTION - assessment_delta
                new_assessment_delta = self.ASSESSMENT_MAX_CONTRIBUTION

            if delta > 0:  # Only apply if not capped
                assessment_delta = new_assessment_delta
                skill["assessment_delta"] = round(assessment_delta, 2)
                skill["assessment_count"] = skill.get("assessment_count", 0) + 1

        # Calculate new current level
        new_level = baseline + tournament_delta + assessment_delta

        # Apply overall hard cap at 100.0
        skill["current_level"] = round(
            min(self.MAX_SKILL_LEVEL, max(self.MIN_SKILL_LEVEL, new_level)),
            1
        )

        # Update total_delta for backward compatibility
        skill["total_delta"] = round(tournament_delta + assessment_delta, 2)
        skill["last_updated"] = datetime.now(timezone.utc).isoformat()

        return skills

    def get_skill_profile(self, user_license_id: int) -> Dict:
        """
        Get current skill profile with dynamic calculations

        Returns:
            Dict of skill_name -> skill_data
        """
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license or not license.football_skills:
            return {}

        # Ensure new format and return
        return self._ensure_new_format(license.football_skills)

    def calculate_average_level(self, user_license_id: int) -> float:
        """
        Calculate average skill level from current_level values

        Args:
            user_license_id: UserLicense ID

        Returns:
            Average skill level (0-100)
        """
        skills = self.get_skill_profile(user_license_id)

        if not skills:
            return 0.0

        current_levels = [
            skill_data.get("current_level", skill_data.get("baseline", 0.0))
            for skill_data in skills.values()
        ]

        if not current_levels:
            return 0.0

        return round(sum(current_levels) / len(current_levels), 1)

    def get_skill_display_tier(self, skill_level: float) -> str:
        """
        Determine visual tier for skill display

        Args:
            skill_level: Skill value (0-100)

        Returns:
            Tier identifier: BEGINNER, DEVELOPING, INTERMEDIATE, ADVANCED, MASTER
        """
        if skill_level >= 95:
            return "MASTER"  # 💎 Master (near-perfect)
        elif skill_level >= 85:
            return "ADVANCED"  # 🔥 Advanced
        elif skill_level >= 70:
            return "INTERMEDIATE"  # ⚡ Intermediate
        elif skill_level >= 50:
            return "DEVELOPING"  # 📈 Developing
        else:
            return "BEGINNER"  # 🌱 Beginner

    def get_tier_emoji(self, tier: str) -> str:
        """Get emoji for tier"""
        tier_emojis = {
            "MASTER": "💎",
            "ADVANCED": "🔥",
            "INTERMEDIATE": "⚡",
            "DEVELOPING": "📈",
            "BEGINNER": "🌱"
        }
        return tier_emojis.get(tier, "")

    def apply_skill_decay(
        self,
        user_license_id: int,
        current_date: Optional[datetime] = None
    ) -> Dict[str, Dict]:
        """
        Apply non-linear time-based decay to tournament-earned skill deltas.

        Decay Formula (exponential curve):
            decay_factor = 1 - e^(-k × months_inactive)
            decay_amount = total_delta × max_percentage × decay_factor

        This creates a curve where:
        - Initial decay is faster (noticeable impact)
        - Decay rate slows as time passes (asymptotic to max)
        - Never decays below baseline

        Args:
            user_license_id: UserLicense ID
            current_date: Current date (defaults to now, used for testing)

        Returns:
            Updated skill profile with decay applied

        Example Decay Curve (max 20%, k=0.5):
            30 days (1 month):   ~8% decay   (0.8 points on 10 delta)
            60 days (2 months):  ~15% decay  (1.5 points on 10 delta)
            90 days (3 months):  ~18% decay  (1.8 points on 10 delta)
            180 days (6 months): ~20% decay  (2.0 points on 10 delta, asymptote)
        """
        import math

        if not self.DECAY_ENABLED:
            return {}

        if current_date is None:
            current_date = datetime.now(timezone.utc)

        # Get user license
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license or not license.football_skills:
            return {}

        # Ensure new format
        skills = self._ensure_new_format(license.football_skills)

        # Get last tournament date from TournamentParticipation
        from app.models.tournament_achievement import TournamentParticipation
        last_participation = self.db.query(TournamentParticipation).filter(
            TournamentParticipation.user_license_id == user_license_id
        ).order_by(
            TournamentParticipation.created_at.desc()
        ).first()

        if not last_participation:
            # No tournament history, no decay needed
            return skills

        last_tournament_date = last_participation.created_at
        if last_tournament_date.tzinfo is None:
            last_tournament_date = last_tournament_date.replace(tzinfo=timezone.utc)

        # Calculate days inactive
        days_inactive = (current_date - last_tournament_date).days

        if days_inactive < self.DECAY_THRESHOLD_DAYS:
            # Not inactive long enough
            return skills

        # Calculate months inactive (after threshold)
        months_inactive = (days_inactive - self.DECAY_THRESHOLD_DAYS) / 30.0

        # Calculate decay factor (exponential curve)
        # decay_factor = 1 - e^(-k × months)
        # Approaches 1.0 as months → infinity (asymptotic to max decay)
        decay_factor = 1 - math.exp(-self.DECAY_CURVE_STEEPNESS * months_inactive)

        # Apply decay to each skill
        skills_updated = False
        for skill_name, skill_data in skills.items():
            current_level = skill_data["current_level"]
            baseline = skill_data["baseline"]
            total_delta = skill_data["total_delta"]

            # Only decay if current > baseline (tournament gains exist)
            if current_level <= baseline or total_delta <= 0:
                continue

            # Calculate decay amount (percentage of total delta)
            max_decay = total_delta * self.DECAY_MAX_PERCENTAGE
            decay_amount = max_decay * decay_factor

            # Apply decay, but never go below baseline
            new_level = max(baseline, current_level - decay_amount)

            if new_level != current_level:
                skill_data["current_level"] = round(new_level, 1)
                skill_data["total_decay_applied"] = skill_data.get(
                    "total_decay_applied", 0.0
                ) + (current_level - new_level)
                skill_data["last_decay_date"] = current_date.isoformat()
                skills_updated = True

        if skills_updated:
            # Save changes
            license.football_skills = skills
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(license, 'football_skills')
            self.db.commit()

            logger.info(
                f"Applied skill decay for user_license {user_license_id}: "
                f"{days_inactive} days inactive, "
                f"decay_factor={decay_factor:.2%}"
            )

        return skills

    def apply_assessment_skill_deltas(
        self,
        user_license_id: int,
        skill_deltas: Dict[str, float]
    ) -> Dict[str, Dict]:
        """
        Apply skill deltas from instructor assessment to player profile.

        Similar to tournament deltas but:
        - Uses ASSESSMENT_DELTA_MULTIPLIER (0.20 vs 0.125)
        - Subject to ASSESSMENT_MAX_CONTRIBUTION cap (+10 max)
        - Separate tracking in assessment_delta field

        Args:
            user_license_id: UserLicense ID
            skill_deltas: Dict of skill_name → raw assessment value

        Returns:
            Updated skill profile

        Example:
            skill_deltas = {"speed": 10.0, "ball_control": 8.5}
            → speed: +2.0 (10.0 × 0.20)
            → ball_control: +1.7 (8.5 × 0.20)
        """
        # Get user license
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license:
            raise ValueError(f"UserLicense {user_license_id} not found")

        # Ensure skills dict exists
        if not license.football_skills:
            license.football_skills = {}

        # Migrate old format if needed
        license.football_skills = self._ensure_new_format(license.football_skills)

        # Apply deltas for each skill
        for skill_name, raw_value in skill_deltas.items():
            delta = self._calculate_delta(raw_value, source="assessment")
            license.football_skills = self._apply_skill_delta(
                license.football_skills,
                skill_name,
                delta,
                source="assessment"
            )

        # Mark JSONB field as modified
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(license, 'football_skills')

        self.db.commit()

        logger.info(
            f"Applied assessment deltas for user_license {user_license_id}: "
            f"{len(skill_deltas)} skills updated"
        )

        return license.football_skills

    def get_skill_profile_with_decay(
        self,
        user_license_id: int,
        apply_decay: bool = True
    ) -> Dict[str, Dict]:
        """
        Get skill profile with optional real-time decay calculation.

        This method:
        1. Loads current skill profile
        2. Optionally applies decay based on current time
        3. Returns updated profile (decay applied in-place if enabled)

        Args:
            user_license_id: UserLicense ID
            apply_decay: If True, calculate and apply decay

        Returns:
            Skill profile (with decay applied if enabled)
        """
        if apply_decay and self.DECAY_ENABLED:
            # Apply decay and return updated profile
            return self.apply_skill_decay(user_license_id)

        # Just return current profile without decay
        return self.get_skill_profile(user_license_id)
