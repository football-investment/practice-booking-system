"""
⚽ Football Skill Assessment Service - V3
Handles assessment creation and average calculation for LFA Player skills

PHASE 2: State Machine Integration
- Create assessment with auto-archive + idempotency
- Validate assessment (ASSESSED → VALIDATED)
- Archive assessment (ASSESSED/VALIDATED → ARCHIVED)
- Invalid transition rejection
- Row-level locking for concurrency protection
"""
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timezone, timedelta
import logging

from ..models.football_skill_assessment import FootballSkillAssessment
from ..models.license import UserLicense
from ..models.user import User, UserRole
from ..models.skill_reward import SkillReward
from ..skills_config import get_all_skill_keys
from app.utils.lock_logger import lock_timer
from .skill_state_machine import (
    SkillAssessmentState,
    validate_state_transition,
    determine_validation_requirement,
    get_skill_category,
    create_state_transition_audit,
    log_state_transition
)

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
    ) -> Tuple[FootballSkillAssessment, bool]:
        """
        Create a new skill assessment with state machine integration.

        PHASE 2 FEATURES:
        - Auto-archive old assessments (ASSESSED/VALIDATED → ARCHIVED)
        - Determine validation requirement (business rule)
        - Idempotency: Returns existing if active assessment exists
        - Row-level locking: Prevents concurrent duplicate creation
        - State transition audit trail

        Args:
            user_license_id: UserLicense ID
            skill_name: Skill name (heading, shooting, etc.)
            points_earned: Points earned (e.g., 7)
            points_total: Total points (e.g., 10)
            assessed_by: Instructor user ID
            notes: Optional notes

        Returns:
            (assessment, created) where:
            - assessment: FootballSkillAssessment object
            - created: True if new assessment created, False if existing returned (idempotent)

        Raises:
            ValueError: If business rules violated (invalid skill, invalid points, etc.)
        """
        # ====================================================================
        # Step 1: Validation (business rules)
        # ====================================================================

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

        # ====================================================================
        # Step 2: Row-level locking (concurrency protection)
        # ====================================================================
        # Lock UserLicense row to serialize concurrent assessment creation
        # for same license. Prevents race condition where 2 threads check
        # for existing assessment simultaneously and both create new one.
        # ====================================================================

        with lock_timer("skill_assessment", "UserLicense", user_license_id, logger,
                        caller="FootballSkillService.create_assessment"):
            license = self.db.query(UserLicense).filter(
                UserLicense.id == user_license_id
            ).with_for_update().first()

            if not license:
                raise ValueError(f"UserLicense {user_license_id} not found")

            # ================================================================
            # ================================================================
            # Step 3: Content-based idempotency check
            # ================================================================
            # If creating assessment with IDENTICAL data (same scores), return existing.
            # This prevents duplicate assessments from retries or instructor mistakes.
            # If data is DIFFERENT (new scores), continue to archive + create new.
            # ================================================================

            existing_active = self.db.query(FootballSkillAssessment).filter(
                FootballSkillAssessment.user_license_id == user_license_id,
                FootballSkillAssessment.skill_name == skill_name,
                FootballSkillAssessment.status.in_([
                    SkillAssessmentState.ASSESSED,
                    SkillAssessmentState.VALIDATED
                ])
            ).first()

            if existing_active:
                # Check if data is identical (same scores)
                if (existing_active.points_earned == points_earned and
                    existing_active.points_total == points_total):
                    logger.info(
                        f"🔒 IDEMPOTENT: Assessment with identical data already exists "
                        f"(id={existing_active.id}, status={existing_active.status}, "
                        f"score={points_earned}/{points_total}, user_license={user_license_id}, skill={skill_name})"
                    )
                    return (existing_active, False)
                else:
                    logger.info(
                        f"📝 UPDATE DETECTED: Assessment data changed "
                        f"(old: {existing_active.points_earned}/{existing_active.points_total}, "
                        f"new: {points_earned}/{points_total}) - will archive old and create new"
                    )

            # ================================================================
            # Step 4: Auto-archive old assessments (Manual Archive Policy)
            # ================================================================
            # Policy Decision: Manual archive triggered by new assessment creation
            # Archive any existing ASSESSED or VALIDATED assessments for this skill.
            # Only reached if data is DIFFERENT from existing assessment.
            # ================================================================

            old_assessments = self.db.query(FootballSkillAssessment).filter(
                FootballSkillAssessment.user_license_id == user_license_id,
                FootballSkillAssessment.skill_name == skill_name,
                FootballSkillAssessment.status.in_([
                    SkillAssessmentState.ASSESSED,
                    SkillAssessmentState.VALIDATED
                ])
            ).all()

            for old in old_assessments:
                # Validate transition (should always be valid, but check anyway)
                is_valid, error_msg = validate_state_transition(
                    old.status, SkillAssessmentState.ARCHIVED
                )
                if not is_valid:
                    raise ValueError(f"Cannot archive old assessment: {error_msg}")

                # Archive old assessment
                old.previous_status = old.status
                old.status = SkillAssessmentState.ARCHIVED
                old.archived_at = datetime.now(timezone.utc)
                old.archived_by = assessed_by
                old.archived_reason = "Replaced by new assessment"
                old.status_changed_at = datetime.now(timezone.utc)
                old.status_changed_by = assessed_by

                log_state_transition(
                    old.id, old.previous_status, SkillAssessmentState.ARCHIVED,
                    assessed_by, "Replaced by new assessment"
                )

            # ================================================================
            # Step 5: Determine validation requirement (business rule)
            # ================================================================

            # Get instructor tenure
            instructor = self.db.query(User).filter(User.id == assessed_by).first()
            if not instructor:
                raise ValueError(f"Instructor {assessed_by} not found")

            instructor_tenure_days = 0
            if instructor.created_at:
                # Handle both timezone-aware and timezone-naive datetimes
                instructor_created = instructor.created_at
                if instructor_created.tzinfo is None:
                    # Make timezone-aware if naive (assume UTC)
                    instructor_created = instructor_created.replace(tzinfo=timezone.utc)
                tenure_delta = datetime.now(timezone.utc) - instructor_created
                instructor_tenure_days = tenure_delta.days

            # Determine if validation required
            skill_category = get_skill_category(skill_name)
            requires_validation = determine_validation_requirement(
                license_level=license.current_level,
                instructor_tenure_days=instructor_tenure_days,
                skill_category=skill_category
            )

            # ================================================================
            # Step 6: Create new assessment with status=ASSESSED
            # ================================================================

            percentage = FootballSkillAssessment.calculate_percentage(points_earned, points_total)

            assessment = FootballSkillAssessment(
                user_license_id=user_license_id,
                skill_name=skill_name,
                points_earned=points_earned,
                points_total=points_total,
                percentage=percentage,
                assessed_by=assessed_by,
                assessed_at=datetime.now(timezone.utc),
                notes=notes,
                # Lifecycle state machine fields
                status=SkillAssessmentState.ASSESSED,
                requires_validation=requires_validation,
                status_changed_at=datetime.now(timezone.utc),
                status_changed_by=assessed_by,
                previous_status=SkillAssessmentState.NOT_ASSESSED
            )

            self.db.add(assessment)

            try:
                self.db.flush()  # Get ID without committing
            except IntegrityError as e:
                # Concurrent creation detected - UniqueConstraint violation
                # Another thread created assessment between our archive and create
                self.db.rollback()

                # Fetch the assessment created by concurrent thread
                existing = self.db.query(FootballSkillAssessment).filter(
                    FootballSkillAssessment.user_license_id == user_license_id,
                    FootballSkillAssessment.skill_name == skill_name,
                    FootballSkillAssessment.status.in_([
                        SkillAssessmentState.ASSESSED,
                        SkillAssessmentState.VALIDATED
                    ])
                ).first()

                if existing:
                    logger.info(
                        f"🔒 CONCURRENT CREATION DETECTED: Assessment created by another thread "
                        f"(id={existing.id}, status={existing.status}, user_license={user_license_id}, skill={skill_name})"
                    )
                    return (existing, False)
                else:
                    # Unexpected IntegrityError - re-raise
                    logger.error(f"Unexpected IntegrityError during assessment creation: {e}")
                    raise

            log_state_transition(
                assessment.id,
                SkillAssessmentState.NOT_ASSESSED,
                SkillAssessmentState.ASSESSED,
                assessed_by,
                f"Assessment created (requires_validation={requires_validation})"
            )

            # ================================================================
            # Step 7: Recalculate cached average (existing logic)
            # ================================================================
            self.recalculate_skill_average(user_license_id, skill_name)

            return (assessment, True)

    def validate_assessment(
        self,
        assessment_id: int,
        validated_by: int
    ) -> FootballSkillAssessment:
        """
        Validate assessment with state transition check.

        PHASE 2 FEATURE: State machine integration
        - Valid transition: ASSESSED → VALIDATED
        - Idempotent: VALIDATED → VALIDATED (no-op)
        - Invalid transitions rejected with clear error message
        - Row-level locking for concurrency protection

        Args:
            assessment_id: Assessment ID to validate
            validated_by: Admin/instructor user ID who validates

        Returns:
            Validated assessment

        Raises:
            ValueError: If assessment not found or invalid state transition
        """
        # ====================================================================
        # Step 1: Lock assessment row (concurrency protection)
        # ====================================================================
        assessment = self.db.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.id == assessment_id
        ).with_for_update().first()

        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        # ====================================================================
        # Step 2: Idempotency check (already validated)
        # ====================================================================
        if assessment.status == SkillAssessmentState.VALIDATED:
            logger.info(
                f"🔒 IDEMPOTENT: Assessment already VALIDATED (id={assessment_id})"
            )
            return assessment

        # ====================================================================
        # Step 3: Validate state transition
        # ====================================================================
        is_valid, error_msg = validate_state_transition(
            assessment.status, SkillAssessmentState.VALIDATED
        )

        if not is_valid:
            raise ValueError(
                f"Invalid state transition: {assessment.status} → VALIDATED. {error_msg}"
            )

        # ====================================================================
        # Step 4: Perform validation (state transition)
        # ====================================================================
        assessment.previous_status = assessment.status
        assessment.status = SkillAssessmentState.VALIDATED
        assessment.validated_by = validated_by
        assessment.validated_at = datetime.now(timezone.utc)
        assessment.status_changed_at = datetime.now(timezone.utc)
        assessment.status_changed_by = validated_by

        self.db.flush()

        log_state_transition(
            assessment_id, assessment.previous_status, SkillAssessmentState.VALIDATED,
            validated_by, "Admin/instructor validated assessment"
        )

        return assessment

    def archive_assessment(
        self,
        assessment_id: int,
        archived_by: int,
        reason: str
    ) -> FootballSkillAssessment:
        """
        Archive assessment with state transition check.

        PHASE 2 FEATURE: State machine integration
        - Valid transitions: ASSESSED → ARCHIVED, VALIDATED → ARCHIVED
        - Idempotent: ARCHIVED → ARCHIVED (no-op)
        - Invalid transitions rejected with clear error message
        - Row-level locking for concurrency protection

        Args:
            assessment_id: Assessment ID to archive
            archived_by: User ID who triggered archive
            reason: Reason for archiving

        Returns:
            Archived assessment

        Raises:
            ValueError: If assessment not found or invalid state transition
        """
        # ====================================================================
        # Step 1: Lock assessment row (concurrency protection)
        # ====================================================================
        assessment = self.db.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.id == assessment_id
        ).with_for_update().first()

        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        # ====================================================================
        # Step 2: Idempotency check (already archived)
        # ====================================================================
        if assessment.status == SkillAssessmentState.ARCHIVED:
            logger.info(
                f"🔒 IDEMPOTENT: Assessment already ARCHIVED (id={assessment_id})"
            )
            return assessment

        # ====================================================================
        # Step 3: Validate state transition
        # ====================================================================
        is_valid, error_msg = validate_state_transition(
            assessment.status, SkillAssessmentState.ARCHIVED
        )

        if not is_valid:
            raise ValueError(
                f"Invalid state transition: {assessment.status} → ARCHIVED. {error_msg}"
            )

        # ====================================================================
        # Step 4: Perform archive (state transition)
        # ====================================================================
        assessment.previous_status = assessment.status
        assessment.status = SkillAssessmentState.ARCHIVED
        assessment.archived_by = archived_by
        assessment.archived_at = datetime.now(timezone.utc)
        assessment.archived_reason = reason
        assessment.status_changed_at = datetime.now(timezone.utc)
        assessment.status_changed_by = archived_by

        self.db.flush()

        log_state_transition(
            assessment_id, assessment.previous_status, SkillAssessmentState.ARCHIVED,
            archived_by, reason
        )

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

        # Update cached value in user_licenses.football_skills JSON.
        # S02: FOR UPDATE serialises this write with concurrent tournament finalizations
        # that also hold FOR UPDATE on the same UserLicense row (Step 1.5 in orchestrator).
        # Lock order: both paths target the same physical row; whichever arrives first
        # holds the lock and the other blocks — no deadlock possible.
        # lock_timer measures time from FOR UPDATE through flag_modified (true hold time).
        with lock_timer("skill", "UserLicense", user_license_id, logger,
                        caller="FootballSkillService.recalculate_skill_average"):
            license = self.db.query(UserLicense).filter(
                UserLicense.id == user_license_id
            ).with_for_update().first()
            if license:
                if not license.football_skills:
                    license.football_skills = {}

                existing = license.football_skills.get(skill_name)
                if isinstance(existing, dict):
                    # S03: dict-format entry (V2 / tournament path) — preserve structure.
                    # Only update the 'baseline' sub-key; leave current_level / deltas intact.
                    existing["baseline"] = average
                    license.football_skills[skill_name] = existing
                else:
                    # Scalar-format entry (V1 / assessment-only user) — write as float.
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
