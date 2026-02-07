"""
⚽ Football Skill Assessment Service - V2
Handles assessment creation and average calculation for LFA Player skills
"""
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timezone
import logging

from ..models.football_skill_assessment import FootballSkillAssessment
from ..models.license import UserLicense
from ..models.user import User
from ..models.skill_reward import SkillReward
from ..skills_config import get_all_skill_keys

logger = logging.getLogger(__name__)

class FootballSkillService:
    """Service for managing football skill assessments"""

    # ✅ CONSOLIDATED: Use central skill list from skills_config.py (29 skills)
    # Old hardcoded list (6 skills) is deprecated
    @property
    def VALID_SKILLS(self) -> List[str]:
        """Get all valid skill keys from central configuration"""
        return get_all_skill_keys()

    def __init__(self, db: Session):
        self.db = db

    def create_assessment(
        self,
        user_license_id: int,
        skill_name: str,
        points_earned: int,
        points_total: int,
        assessed_by: int,
        notes: Optional[str] = None
    ) -> FootballSkillAssessment:
        """
        Create a new skill assessment and update cached average

        Args:
            user_license_id: UserLicense ID
            skill_name: Skill name (heading, shooting, etc.)
            points_earned: Points earned (e.g., 7)
            points_total: Total points (e.g., 10)
            assessed_by: Instructor user ID
            notes: Optional notes

        Returns:
            Created assessment
        """
        # Validate skill name
        if skill_name not in self.VALID_SKILLS:
            raise ValueError(f"Invalid skill name: {skill_name}. Must be one of {self.VALID_SKILLS}")

        # Validate points
        if points_earned < 0:
            raise ValueError("Points earned cannot be negative")
        if points_total <= 0:
            raise ValueError("Total points must be greater than 0")
        if points_earned > points_total:
            raise ValueError(f"Points earned ({points_earned}) cannot exceed total points ({points_total})")

        # Calculate percentage
        percentage = FootballSkillAssessment.calculate_percentage(points_earned, points_total)

        # Create assessment
        assessment = FootballSkillAssessment(
            user_license_id=user_license_id,
            skill_name=skill_name,
            points_earned=points_earned,
            points_total=points_total,
            percentage=percentage,
            assessed_by=assessed_by,
            assessed_at=datetime.now(timezone.utc),
            notes=notes
        )

        self.db.add(assessment)
        self.db.flush()  # Get ID without committing

        # Recalculate and update cached average
        self.recalculate_skill_average(user_license_id, skill_name)

        return assessment

    def recalculate_skill_average(self, user_license_id: int, skill_name: str) -> float:
        """
        Recalculate average for a specific skill and update cached value

        Args:
            user_license_id: UserLicense ID
            skill_name: Skill to recalculate

        Returns:
            New average percentage
        """
        # Get all assessments for this skill
        assessments = self.db.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.user_license_id == user_license_id,
            FootballSkillAssessment.skill_name == skill_name
        ).all()

        if not assessments:
            return 0.0

        # Calculate average
        average = sum(a.percentage for a in assessments) / len(assessments)
        average = round(average, 1)

        # Update cached value in user_licenses.football_skills JSON
        license = self.db.query(UserLicense).filter(UserLicense.id == user_license_id).first()
        if license:
            if not license.football_skills:
                license.football_skills = {}

            license.football_skills[skill_name] = average

            # Mark as modified (for JSON field)
            flag_modified(license, 'football_skills')

        return average

    def recalculate_all_skill_averages(self, user_license_id: int) -> Dict[str, float]:
        """
        Recalculate averages for ALL 6 skills

        Args:
            user_license_id: UserLicense ID

        Returns:
            Dict of skill_name -> average
        """
        averages = {}
        for skill in self.VALID_SKILLS:
            avg = self.recalculate_skill_average(user_license_id, skill)
            averages[skill] = avg

        return averages

    def get_assessment_history(
        self,
        user_license_id: int,
        skill_name: str,
        limit: Optional[int] = None
    ):
        """
        Get assessment history for a specific skill with averages

        Args:
            user_license_id: UserLicense ID
            skill_name: Skill name to get history for
            limit: Optional limit results

        Returns:
            SkillAssessmentHistoryResponse with current average, count, and assessments
        """
        assessments = self.db.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.user_license_id == user_license_id,
            FootballSkillAssessment.skill_name == skill_name
        ).order_by(FootballSkillAssessment.assessed_at.desc())

        if limit:
            assessments = assessments.limit(limit)

        assessments = assessments.all()

        # Calculate current average
        if assessments:
            current_average = sum(a.percentage for a in assessments) / len(assessments)
            current_average = round(current_average, 1)
        else:
            current_average = 0.0

        # Get total count
        total_count = self.db.query(func.count(FootballSkillAssessment.id)).filter(
            FootballSkillAssessment.user_license_id == user_license_id,
            FootballSkillAssessment.skill_name == skill_name
        ).scalar() or 0

        # Convert to response schema
        assessment_responses = []
        for assessment in assessments:
            # Get assessor name
            assessor = self.db.query(User).filter(User.id == assessment.assessed_by).first()
            assessor_name = assessor.name if assessor else "Unknown"

            assessment_responses.append(SkillAssessmentResponse(
                id=assessment.id,
                user_license_id=assessment.user_license_id,
                skill_name=assessment.skill_name,
                points_earned=assessment.points_earned,
                points_total=assessment.points_total,
                percentage=assessment.percentage,
                assessed_by=assessment.assessed_by,
                assessed_at=assessment.assessed_at,
                assessor_name=assessor_name,
                notes=assessment.notes
            ))

        return SkillAssessmentHistoryResponse(
            skill_name=skill_name,
            current_average=current_average,
            assessment_count=total_count,
            assessments=assessment_responses
        )

    def get_current_averages(self, user_license_id: int) -> Dict[str, float]:
        """
        Get current skill averages from cached values

        Args:
            user_license_id: UserLicense ID

        Returns:
            Dict of skill_name -> average (0.0 if not assessed yet)
        """
        license = self.db.query(UserLicense).filter(UserLicense.id == user_license_id).first()

        if not license or not license.football_skills:
            return {skill: 0.0 for skill in self.VALID_SKILLS}

        averages = {}
        for skill in self.VALID_SKILLS:
            averages[skill] = license.football_skills.get(skill, 0.0)

        return averages

    def get_assessment_counts(self, user_license_id: int) -> Dict[str, int]:
        """
        Get count of assessments per skill

        Args:
            user_license_id: UserLicense ID

        Returns:
            Dict of skill_name -> count
        """
        counts = {}
        for skill in self.VALID_SKILLS:
            count = self.db.query(func.count(FootballSkillAssessment.id)).filter(
                FootballSkillAssessment.user_license_id == user_license_id,
                FootballSkillAssessment.skill_name == skill
            ).scalar()
            counts[skill] = count or 0

        return counts

    def bulk_create_assessments(
        self,
        user_license_id: int,
        assessments: Dict[str, Dict],
        assessed_by: int
    ) -> Dict[str, FootballSkillAssessment]:
        """
        Create assessments for multiple skills at once

        Args:
            user_license_id: UserLicense ID
            assessments: Dict of skill_name -> {points_earned, points_total, notes}
            assessed_by: Instructor user ID

        Returns:
            Dict of skill_name -> created assessment

        Example:
            assessments = {
                'heading': {'points_earned': 7, 'points_total': 10, 'notes': 'Good'},
                'shooting': {'points_earned': 8, 'points_total': 10, 'notes': None},
                ...
            }
        """
        created = {}

        for skill_name, data in assessments.items():
            if skill_name not in self.VALID_SKILLS:
                continue

            assessment = self.create_assessment(
                user_license_id=user_license_id,
                skill_name=skill_name,
                points_earned=data['points_earned'],
                points_total=data['points_total'],
                assessed_by=assessed_by,
                notes=data.get('notes')
            )
            created[skill_name] = assessment

        # Commit all at once
        self.db.commit()

        return created

    def award_skill_points(
        self,
        user_id: int,
        source_type: str,
        source_id: int,
        skill_name: str,
        points_awarded: int
    ) -> Tuple[SkillReward, bool]:
        """
        Award skill points to a user with duplicate protection.

        This is the CENTRALIZED method for creating skill rewards.
        All skill reward creation MUST go through this method to prevent dual-path bugs.

        Business Invariant: One skill reward per (user_id, source_type, source_id, skill_name)

        Args:
            user_id: User receiving skill points
            source_type: Source type (e.g., "TOURNAMENT", "SESSION")
            source_id: Source ID (tournament ID, session ID, etc.)
            skill_name: Skill being rewarded (must be in VALID_SKILLS)
            points_awarded: Points to award (positive integer)

        Returns:
            Tuple of (SkillReward, created)
            - created=True: Reward was created
            - created=False: Reward already existed (idempotent return)

        Raises:
            ValueError: If business rules are violated
            IntegrityError: If database constraints are violated
        """
        # Validate skill name
        if skill_name not in self.VALID_SKILLS:
            raise ValueError(
                f"Invalid skill name: {skill_name}. Must be one of {self.VALID_SKILLS}"
            )

        # Validate points (allow negative for skill decrease/penalties)
        if points_awarded == 0:
            raise ValueError(f"Points awarded cannot be zero, got {points_awarded}")

        # Allow negative points for skill decrease (e.g., bottom players in tournaments)

        # Check for existing reward (idempotency based on unique constraint)
        # Constraint: (user_id, source_type, source_id, skill_name)
        existing = self.db.query(SkillReward).filter(
            SkillReward.user_id == user_id,
            SkillReward.source_type == source_type,
            SkillReward.source_id == source_id,
            SkillReward.skill_name == skill_name
        ).first()

        if existing:
            logger.info(
                f"🔒 IDEMPOTENT RETURN: Skill reward already exists "
                f"(id={existing.id}, user={user_id}, source={source_type}:{source_id}, "
                f"skill={skill_name}). Returning existing reward."
            )
            return (existing, False)

        # Create new reward
        reward = SkillReward(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            skill_name=skill_name,
            points_awarded=points_awarded
        )

        try:
            self.db.add(reward)
            self.db.flush()  # Flush to get ID and check constraints

            logger.info(
                f"✅ Skill reward created: id={reward.id}, user={user_id}, "
                f"source={source_type}:{source_id}, skill={skill_name}, "
                f"points={points_awarded}"
            )

            return (reward, True)

        except IntegrityError as e:
            # If unique constraint violation, return existing
            if "uq_skill_rewards_user_source_skill" in str(e):
                self.db.rollback()

                # Fetch the existing reward
                existing = self.db.query(SkillReward).filter(
                    SkillReward.user_id == user_id,
                    SkillReward.source_type == source_type,
                    SkillReward.source_id == source_id,
                    SkillReward.skill_name == skill_name
                ).first()

                if existing:
                    logger.warning(
                        f"🔒 RACE CONDITION: Skill reward was created by another request. "
                        f"Returning existing reward (id={existing.id}, user={user_id}, "
                        f"source={source_type}:{source_id}, skill={skill_name})."
                    )
                    return (existing, False)
                else:
                    logger.error(
                        f"❌ CRITICAL: IntegrityError on unique constraint but reward not found! "
                        f"user={user_id}, source={source_type}:{source_id}, skill={skill_name}"
                    )
                    raise ValueError(
                        f"Skill reward failed due to race condition: "
                        f"user={user_id}, source={source_type}:{source_id}, skill={skill_name}"
                    ) from e
            else:
                # Other integrity error - re-raise
                logger.error(f"❌ IntegrityError creating skill reward: {e}")
                raise
