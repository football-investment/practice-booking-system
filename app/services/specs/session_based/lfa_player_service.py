"""
LFA Player Service - SEASON-Based Specialization

This service handles all LFA Football Player-specific logic including:
- Age-based automatic categorization (PRE, YOUTH, AMATEUR, PRO)
- Season enrollment required (Semester = Season with theme/age_group)
- Session booking based on age group compatibility
- Master Instructor promotion workflow
- Football skills tracking (7 skills)

Age Group Rules (OFFICIAL):
UP (Children) Categories:
- PRE: 6-11 years old (can self-enroll)
- YOUTH: 12-18 years old (can self-enroll)

Adult Categories (14+ minimum):
- AMATEUR: 14+ years old (can self-enroll)
- PRO: 14+ years old (CANNOT self-enroll, only promoted by Master Instructor)

CRITICAL BOUNDARY: 14 years is the minimum age for adult categories.
Ages 14-18 can be in YOUTH (UP) OR AMATEUR/PRO (Adult) categories.

Key Characteristics:
- SEASON-BASED: SemesterEnrollment REQUIRED (Semester = Season)
- Payment verified per season enrollment
- Cross-age-group movement controlled by Master Instructor
- Skills tracking: heading, shooting, crossing, passing, dribbling, ball_control, defending
"""

from typing import Tuple, Dict, Optional, List
from datetime import date
from sqlalchemy.orm import Session
from app.services.specs.base_spec import BaseSpecializationService
from app.models.license import UserLicense
from app.models.football_skill_assessment import FootballSkillAssessment
from app.models.semester_enrollment import SemesterEnrollment
from app.skills_config import get_all_skill_keys


class LFAPlayerService(BaseSpecializationService):
    """
    Service for LFA Football Player specialization.

    Handles age-based categorization, session booking, and skills progression.
    """

    def __init__(self, db: Session = None):
        """Initialize LFA Player service with optional database session"""
        self.db = db

    # ========================================================================
    # AGE GROUP CONFIGURATION
    # ========================================================================

    AGE_GROUPS = {
        'PRE': {
            'min_age': 6,
            'max_age': 11,
            'display_name': 'Pre (6-11 years)',
            'can_self_enroll': True,
            'category': 'UP'  # Children category
        },
        'YOUTH': {
            'min_age': 12,
            'max_age': 18,
            'display_name': 'Youth (12-18 years)',
            'can_self_enroll': True,
            'category': 'UP'  # Children category
        },
        'AMATEUR': {
            'min_age': 14,
            'max_age': None,  # No upper limit
            'display_name': 'Amateur (14+ years)',
            'can_self_enroll': True,
            'category': 'ADULT'  # Adult category (14+ minimum)
        },
        'PRO': {
            'min_age': 14,
            'max_age': None,  # No upper limit
            'display_name': 'Pro (14+ years)',
            'can_self_enroll': False,  # Only Master Instructor can promote
            'category': 'ADULT'  # Adult category (14+ minimum)
        }
    }

    # ✅ CONSOLIDATED: Use central skill list from skills_config.py (29 skills)
    # Old hardcoded list (7 skills) is deprecated
    @property
    def VALID_SKILLS(self) -> List[str]:
        """Get all valid skill keys from central configuration"""
        return get_all_skill_keys()

    # ========================================================================
    # OVERRIDE: BaseSpecializationService Methods
    # ========================================================================

    def is_session_based(self) -> bool:
        """
        LFA Player is SEASON-based (requires season enrollment).

        Note: Returns True for backward compatibility, but season enrollment IS required.
        Season = Semester with specific theme/age_group.

        Season Structure:
        - PRE: 12 seasons/year (monthly)
        - YOUTH: 4 seasons/year (quarterly)
        - AMATEUR: 1 season/year (annual 07.01-06.30)
        - PRO: 1 season/year (annual 07.01-06.30)
        """
        return True

    def get_specialization_name(self) -> str:
        """Human-readable name"""
        return "LFA Football Player"

    # ========================================================================
    # AGE GROUP CALCULATION & VALIDATION
    # ========================================================================

    def calculate_age_group(self, date_of_birth: date) -> str:
        """
        Calculate which age group user belongs to based on current age.

        IMPORTANT: Ages 14-18 can be in YOUTH (UP category) OR AMATEUR (Adult category).
        This method returns the default "natural" age group based on UP categories.
        For adult category enrollment, use validate_age_eligibility() separately.

        Age Group Rules:
        - PRE: 6-11 years (UP category)
        - YOUTH: 12-18 years (UP category)
        - AMATEUR: 14+ years (Adult category, self-enroll allowed)
        - PRO: 14+ years (Adult category, Master Instructor promotion only)

        Critical Boundary: 14 years is the minimum age for adult categories.

        Args:
            date_of_birth: User's date of birth

        Returns:
            Age group string ('PRE', 'YOUTH', 'AMATEUR', 'PRO')
            For ages 6-13: Returns natural UP category (PRE or YOUTH)
            For ages 14-18: Returns 'YOUTH' (natural UP category)
            For ages 19+: Returns 'AMATEUR' (adult category default)

        Raises:
            ValueError: If age is below minimum (6 years)
        """
        age = self.calculate_age(date_of_birth)

        if age < 6:
            raise ValueError(f"Age {age} is below minimum (6 years) for LFA Player")

        if 6 <= age <= 11:
            return 'PRE'
        elif 12 <= age <= 18:
            return 'YOUTH'  # Natural UP category (can also enroll in AMATEUR if 14+)
        else:  # age >= 19
            return 'AMATEUR'  # Default adult category (PRO requires promotion)

    def get_age_group_from_specialization(self, spec_type: str) -> Optional[str]:
        """
        Extract age group from specialization_type.

        Args:
            spec_type: Full specialization (e.g., "LFA_PLAYER_PRE")

        Returns:
            Age group string or None if invalid

        Examples:
            >>> service.get_age_group_from_specialization("LFA_PLAYER_PRE")
            'PRE'
            >>> service.get_age_group_from_specialization("LFA_PLAYER_YOUTH")
            'YOUTH'
        """
        if not spec_type or not spec_type.startswith('LFA_PLAYER'):
            return None

        parts = spec_type.split('_')
        if len(parts) < 3:
            return None

        age_group = parts[-1]  # Last part is age group
        return age_group if age_group in self.AGE_GROUPS else None

    def validate_age_eligibility(self, user, target_group: Optional[str] = None, db: Session = None) -> Tuple[bool, str]:
        """
        Validate if user's age fits the age group rules.

        Args:
            user: User model instance
            target_group: Optional specific age group to validate against
            db: Database session (not used for LFA Player)

        Returns:
            Tuple of (is_eligible: bool, reason: str)
        """
        # Check date of birth exists
        is_valid, error = self.validate_date_of_birth(user)
        if not is_valid:
            return False, error

        # Calculate user's natural age group
        try:
            natural_age_group = self.calculate_age_group(user.date_of_birth)
        except ValueError as e:
            return False, str(e)

        # If no target specified, check if user can be in their natural age group
        if not target_group:
            age_config = self.AGE_GROUPS[natural_age_group]
            if not age_config['can_self_enroll']:
                return False, f"Cannot self-enroll in {natural_age_group} group. Master Instructor promotion required."
            return True, f"Eligible for {natural_age_group} age group"

        # Validate against specific target group
        if target_group not in self.AGE_GROUPS:
            return False, f"Invalid age group: {target_group}"

        target_config = self.AGE_GROUPS[target_group]
        age = self.calculate_age(user.date_of_birth)

        # Check if age fits target group range
        if age < target_config['min_age']:
            return False, f"Age {age} is below minimum ({target_config['min_age']}) for {target_group}"

        if target_config['max_age'] and age > target_config['max_age']:
            return False, f"Age {age} is above maximum ({target_config['max_age']}) for {target_group}"

        return True, f"Eligible for {target_group} age group"

    # ========================================================================
    # SESSION BOOKING LOGIC
    # ========================================================================

    def can_book_session(self, user, session, db: Session) -> Tuple[bool, str]:
        """
        Check if LFA Player can book a session.

        Rules:
        1. User must have active license
        2. User must have active season enrollment (SemesterEnrollment with payment_verified)
        3. User's date of birth must be set
        4. Session age group must match user's license age group OR
           Master Instructor has allowed cross-age-group booking

        Season Structure (LFA Player):
        - PRE: 12 seasons/year (monthly)
        - YOUTH: 4 seasons/year (quarterly)
        - AMATEUR: 1 season/year (annual 07.01-06.30)
        - PRO: 1 season/year (annual 07.01-06.30)

        Args:
            user: User model instance
            session: Session model instance
            db: Database session

        Returns:
            Tuple of (can_book: bool, reason: str)
        """
        # Check if user has active license
        has_license, error = self.validate_user_has_license(user, db)
        if not has_license:
            return False, error

        # Get user's license
        license = db.query(UserLicense).filter(
            UserLicense.user_id == user.id,
            UserLicense.is_active == True
        ).first()

        # ✅ CHECK SEASON ENROLLMENT (payment verified)
        if session.semester_id:
            season_enrollment = db.query(SemesterEnrollment).filter(
                SemesterEnrollment.user_id == user.id,
                SemesterEnrollment.semester_id == session.semester_id,
                SemesterEnrollment.is_active == True
            ).first()

            if not season_enrollment:
                return False, "No active season enrollment found. You must enroll in the current season first."

            if not season_enrollment.payment_verified:
                return False, "Season payment not verified. Please complete payment to access sessions."

        # Extract age group from license specialization_type
        user_age_group = self.get_age_group_from_specialization(license.specialization_type)
        if not user_age_group:
            return False, "Invalid license specialization type (missing age group)"

        # Extract age group from session specialization_type
        session_age_group = self.get_age_group_from_specialization(session.specialization_type)
        if not session_age_group:
            return False, "Invalid session specialization type (missing age group)"

        # Check if age groups match
        if user_age_group == session_age_group:
            return True, f"Age group matches: {user_age_group}"

        # Check if cross-age-group booking is allowed
        can_attend, reason = self.can_attend_age_group_session(user_age_group, session_age_group)
        if can_attend:
            return True, f"Cross-age-group booking allowed: {reason}"

        return False, f"Age group mismatch: user is {user_age_group}, session is {session_age_group}. {reason}"

    def can_attend_age_group_session(self, user_age_group: str, session_age_group: str) -> Tuple[bool, str]:
        """
        Check if player from one age group can attend session of another age group.

        Business Rules (can be customized):
        - PRE can attend YOUTH sessions (advanced training)
        - YOUTH can attend PRE sessions (mentoring younger players)
        - AMATEUR can attend YOUTH sessions (help younger players)
        - PRO cannot attend any other sessions (too advanced)

        Args:
            user_age_group: User's age group
            session_age_group: Session's age group

        Returns:
            Tuple of (can_attend: bool, reason: str)
        """
        # Same age group always allowed
        if user_age_group == session_age_group:
            return True, "Same age group"

        # Define cross-age-group rules
        allowed_combinations = {
            'PRE': ['YOUTH'],  # PRE can attend YOUTH
            'YOUTH': ['PRE', 'AMATEUR'],  # YOUTH can attend PRE and AMATEUR
            'AMATEUR': ['YOUTH'],  # AMATEUR can attend YOUTH
            'PRO': []  # PRO cannot attend other groups
        }

        if session_age_group in allowed_combinations.get(user_age_group, []):
            return True, f"{user_age_group} players can attend {session_age_group} sessions"

        return False, f"{user_age_group} players cannot attend {session_age_group} sessions"

    # ========================================================================
    # ENROLLMENT REQUIREMENTS
    # ========================================================================

    def get_enrollment_requirements(self, user, db: Session) -> Dict:
        """
        Get what's needed for user to participate in LFA Player.

        Returns license status and age group info.

        Args:
            user: User model instance
            db: Database session

        Returns:
            Dictionary with structure:
            {
                "can_participate": bool,
                "missing_requirements": List[str],
                "current_status": {
                    "has_license": bool,
                    "license_active": bool,
                    "age_group": str,
                    "natural_age_group": str,
                    "can_self_enroll": bool
                }
            }
        """
        missing = []
        status = {
            "has_license": False,
            "license_active": False,
            "age_group": None,
            "natural_age_group": None,
            "can_self_enroll": False
        }

        # Check date of birth
        is_valid, error = self.validate_date_of_birth(user)
        if not is_valid:
            missing.append(f"Date of birth: {error}")
        else:
            # Calculate natural age group
            try:
                natural_age_group = self.calculate_age_group(user.date_of_birth)
                status["natural_age_group"] = natural_age_group
                status["can_self_enroll"] = self.AGE_GROUPS[natural_age_group]['can_self_enroll']
            except ValueError as e:
                missing.append(str(e))

        # Check license
        has_license, license_error = self.validate_user_has_license(user, db)
        if has_license:
            license = db.query(UserLicense).filter(
                UserLicense.user_id == user.id,
                UserLicense.is_active == True
            ).first()

            status["has_license"] = True
            status["license_active"] = license.is_active
            status["age_group"] = self.get_age_group_from_specialization(license.specialization_type)
        else:
            missing.append(f"Active license: {license_error}")

        can_participate = len(missing) == 0
        return {
            "can_participate": can_participate,
            "missing_requirements": missing,
            "current_status": status
        }

    # ========================================================================
    # PROGRESSION & SKILLS
    # ========================================================================

    def get_progression_status(self, user_license, db: Session) -> Dict:
        """
        Get current skills assessment progress for LFA Player.

        Args:
            user_license: UserLicense model instance
            db: Database session

        Returns:
            Dictionary with structure:
            {
                "current_level": str (age group),
                "progress_percentage": float (average skill percentage),
                "skills": List[Dict] (individual skill assessments),
                "achievements": List[Dict] (completed milestones)
            }
        """
        # Get age group from license
        age_group = self.get_age_group_from_specialization(user_license.specialization_type)

        # Fetch all skill assessments for this license
        assessments = db.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.user_license_id == user_license.id
        ).all()

        # Calculate average skill percentage
        if assessments:
            avg_percentage = sum(a.percentage for a in assessments) / len(assessments)
        else:
            avg_percentage = 0.0

        # Format skills data
        skills_data = []
        for skill in self.VALID_SKILLS:
            assessment = next((a for a in assessments if a.skill_name == skill), None)
            if assessment:
                skills_data.append({
                    "skill_name": skill,
                    "percentage": assessment.percentage,
                    "points_earned": assessment.points_earned,
                    "points_total": assessment.points_total,
                    "last_updated": assessment.created_at.isoformat() if assessment.created_at else None
                })
            else:
                skills_data.append({
                    "skill_name": skill,
                    "percentage": 0.0,
                    "points_earned": 0,
                    "points_total": 0,
                    "last_updated": None
                })

        # Simple achievement logic (can be expanded)
        achievements = []
        if avg_percentage >= 80:
            achievements.append({"name": "Expert Player", "description": "80%+ average skill"})
        if avg_percentage >= 60:
            achievements.append({"name": "Proficient Player", "description": "60%+ average skill"})
        if len(assessments) == len(self.VALID_SKILLS):
            achievements.append({"name": "All Skills Assessed", "description": "Completed all 7 skills"})

        return {
            "current_level": age_group or "Unknown",
            "progress_percentage": round(avg_percentage, 2),
            "skills": skills_data,
            "achievements": achievements,
            "next_milestone": self._get_next_milestone(avg_percentage, age_group)
        }

    def _get_next_milestone(self, avg_percentage: float, age_group: Optional[str]) -> Optional[Dict]:
        """
        Calculate next milestone for player progression.

        Args:
            avg_percentage: Current average skill percentage
            age_group: Current age group

        Returns:
            Dictionary with next milestone info or None
        """
        if avg_percentage < 60:
            return {
                "name": "Proficient Player",
                "target_percentage": 60.0,
                "remaining": round(60.0 - avg_percentage, 2)
            }
        elif avg_percentage < 80:
            return {
                "name": "Expert Player",
                "target_percentage": 80.0,
                "remaining": round(80.0 - avg_percentage, 2)
            }
        elif age_group and age_group != 'PRO':
            # Suggest age group promotion
            next_groups = {'PRE': 'YOUTH', 'YOUTH': 'AMATEUR', 'AMATEUR': 'PRO'}
            next_group = next_groups.get(age_group)
            if next_group:
                return {
                    "name": f"Promotion to {next_group}",
                    "description": "Contact Master Instructor for age group promotion",
                    "target_percentage": None
                }

        return None

    # ========================================================================
    # MASTER INSTRUCTOR PROMOTION
    # ========================================================================

    def promote_to_higher_age_group(
        self,
        user_license: UserLicense,
        target_age_group: str,
        promoted_by_instructor_id: int,
        db: Session
    ) -> Tuple[bool, str]:
        """
        Master Instructor promotes player to a different age group.

        This is the ONLY way to move a player to PRO group or to override
        natural age-based categorization.

        Args:
            user_license: UserLicense to promote
            target_age_group: Target age group (PRE, YOUTH, AMATEUR, PRO)
            promoted_by_instructor_id: ID of Master Instructor performing promotion
            db: Database session

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate target age group
        if target_age_group not in self.AGE_GROUPS:
            return False, f"Invalid target age group: {target_age_group}"

        # Get current age group
        current_age_group = self.get_age_group_from_specialization(user_license.specialization_type)
        if not current_age_group:
            return False, "Invalid current license specialization type"

        # Check if already in target group
        if current_age_group == target_age_group:
            return False, f"Player is already in {target_age_group} group"

        # Update license specialization_type
        new_spec_type = f"LFA_PLAYER_{target_age_group}"
        user_license.specialization_type = new_spec_type

        # Log promotion (you might want to create an audit log entry here)
        # For now, just update the license
        db.commit()

        return True, f"Successfully promoted from {current_age_group} to {target_age_group}"

    # ========================================================================
    # CREDIT MANAGEMENT (for compatibility with LFA Player credit endpoints)
    # ========================================================================

    def get_license_by_user(self, user_id: int) -> Optional[Dict]:
        """
        Get user's active LFA Player license

        Returns license data as dict for compatibility with credit endpoints.
        If no license exists, returns None.
        """
        try:
            license = self.db.query(UserLicense).filter(
                UserLicense.user_id == user_id,
                UserLicense.is_active == True
            ).first()

            if not license:
                return None

            # Get current age group from user (Player ages are category-based)
            from app.models.user import User
            user = self.db.query(User).filter(User.id == user_id).first()
            age_group = getattr(user, 'age_group', 'AMATEUR')  # Default to AMATEUR

            # Calculate overall average and skills from skill assessments
            overall_avg = 0.0
            skills = {
                'heading_avg': None,
                'shooting_avg': None,
                'crossing_avg': None,
                'passing_avg': None,
                'dribbling_avg': None,
                'ball_control_avg': None,
                'defending_avg': None
            }

            try:
                assessments = self.db.query(FootballSkillAssessment).filter(
                    FootballSkillAssessment.user_id == user_id
                ).all()

                if assessments:
                    # Calculate overall average
                    total_score = sum(getattr(a, 'score', 0) for a in assessments)
                    overall_avg = round(total_score / len(assessments), 2)

                    # Calculate per-skill averages
                    skill_scores = {}
                    for assessment in assessments:
                        skill_name = getattr(assessment, 'skill_name', None)
                        score = getattr(assessment, 'score', 0)
                        if skill_name:
                            if skill_name not in skill_scores:
                                skill_scores[skill_name] = []
                            skill_scores[skill_name].append(score)

                    # Average per skill
                    for skill_name, scores in skill_scores.items():
                        avg_key = f"{skill_name}_avg"
                        if avg_key in skills:
                            skills[avg_key] = round(sum(scores) / len(scores), 2)
            except:
                pass

            return {
                'id': license.id,
                'user_id': license.user_id,
                'age_group': age_group,
                'credit_balance': getattr(license, 'credit_balance', 0),
                'overall_avg': overall_avg,
                'skills': skills,
                'is_active': license.is_active,
                'created_at': license.created_at,
                'updated_at': getattr(license, 'updated_at', license.created_at)
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching license for user {user_id}: {str(e)}")
            return None

    def get_credit_balance(self, license_id: int) -> int:
        """
        Get current credit balance for a license

        Returns:
            int: Current credit balance (defaults to 0 if not found)
        """
        try:
            license = self.db.query(UserLicense).filter(
                UserLicense.id == license_id
            ).first()

            if not license:
                return 0

            return getattr(license, 'credit_balance', 0)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching balance for license {license_id}: {str(e)}")
            return 0

    def get_transaction_history(self, license_id: int, limit: int = 50) -> List[Dict]:
        """
        Get credit transaction history for a license

        Returns:
            List[Dict]: Transaction history (empty list if unavailable)
        """
        try:
            # Note: This assumes a CreditTransaction model exists
            # If it doesn't, return empty list gracefully
            from app.models.credit_transaction import CreditTransaction

            transactions = self.db.query(CreditTransaction).filter(
                CreditTransaction.license_id == license_id
            ).order_by(
                CreditTransaction.created_at.desc()
            ).limit(limit).all()

            return [
                {
                    'id': tx.id,
                    'transaction_type': tx.transaction_type,
                    'amount': tx.amount,
                    'enrollment_id': getattr(tx, 'enrollment_id', None),
                    'payment_verified': getattr(tx, 'payment_verified', None),
                    'payment_reference_code': getattr(tx, 'payment_reference_code', None),
                    'description': getattr(tx, 'description', None),
                    'created_at': tx.created_at
                }
                for tx in transactions
            ]
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Transaction history unavailable for license {license_id}: {str(e)}")
            return []
