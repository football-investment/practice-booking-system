"""
🔐 License Authorization Service
==================================
Service for checking instructor license authorization for teaching sessions and semesters.

Business Rules:
1. COACH license can teach PLAYER sessions (coach knows the game)
2. PLAYER license CANNOT teach COACH sessions (player ≠ coach certification)
3. License level must meet minimum requirements for age group
4. Only ACTIVE licenses count for authorization
5. Expired licenses are automatically marked inactive (Fase 2)
"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from app.models.license import UserLicense
from app.models.user import User
from app.services.license_renewal_service import LicenseRenewalService


class LicenseAuthorizationService:
    """Service for license-based authorization logic"""

    # Minimum PLAYER license level for each age group
    PLAYER_MIN_LEVELS = {
        "PRE": 1,      # Level 1+ (Bamboo Student)
        "YOUTH": 3,    # Level 3+ (Flexible Reed)
        "AMATEUR": 5,  # Level 5+ (Strong Root)
        "PRO": 8       # Level 8 (Dragon Wisdom)
    }

    # Minimum COACH license level for each age group
    COACH_MIN_LEVELS = {
        "PRE": 1,      # Level 1-2 (LFA PRE Assistant/Head)
        "YOUTH": 3,    # Level 3-4 (LFA YOUTH Assistant/Head)
        "AMATEUR": 5,  # Level 5-6 (LFA AMATEUR Assistant/Head)
        "PRO": 7       # Level 7-8 (LFA PRO Assistant/Head)
    }

    @staticmethod
    def extract_age_group_from_specialization(spec_type: str) -> Optional[str]:
        """
        Extract age group from specialization type string.

        Examples:
            "LFA_PLAYER_PRE" -> "PRE"
            "LFA_PLAYER_YOUTH" -> "YOUTH"
            "GANCUJU_PLAYER_PRE" -> "PRE"
        """
        if not spec_type:
            return None

        # Split by underscore and find age group
        parts = spec_type.upper().split("_")
        for part in parts:
            if part in ["PRE", "YOUTH", "AMATEUR", "PRO"]:
                return part

        return None

    @staticmethod
    def extract_base_specialization(spec_type: str) -> Optional[str]:
        """
        Extract base specialization (PLAYER, COACH, INTERNSHIP) from full spec type.

        Examples:
            "LFA_PLAYER_PRE" -> "PLAYER"
            "GANCUJU_PLAYER_YOUTH" -> "PLAYER"
            "LFA_COACH" -> "COACH"
        """
        if not spec_type:
            return None

        spec_upper = spec_type.upper()

        if "PLAYER" in spec_upper:
            return "PLAYER"
        elif "COACH" in spec_upper:
            return "COACH"
        elif "INTERNSHIP" in spec_upper or "INTERN" in spec_upper:
            return "INTERNSHIP"

        return None

    @classmethod
    def can_be_master_instructor(
        cls,
        instructor: User,
        semester_specialization: str,
        semester_age_group: Optional[str],
        db: Session
    ) -> Dict[str, any]:
        """
        Check if instructor can be Master Instructor for a semester.

        Args:
            instructor: User object (instructor)
            semester_specialization: e.g., "LFA_PLAYER_PRE"
            semester_age_group: e.g., "PRE" (can be None for INTERNSHIP)
            db: Database session

        Returns:
            {
                "authorized": bool,
                "reason": str,
                "matching_licenses": List[UserLicense]
            }
        """
        # Get instructor's licenses (marked as active)
        licenses = db.query(UserLicense).filter(
            UserLicense.user_id == instructor.id,
            UserLicense.is_active == True
        ).all()

        # Check expiration for each license (Fase 2)
        active_licenses = []
        for lic in licenses:
            if LicenseRenewalService.check_license_expiration(lic):
                active_licenses.append(lic)

        # Commit any license deactivations
        db.commit()

        if not active_licenses:
            return {
                "authorized": False,
                "reason": "No active licenses found (some may have expired)",
                "matching_licenses": []
            }

        # Extract base specialization and age group
        base_spec = cls.extract_base_specialization(semester_specialization)
        age_group = semester_age_group or cls.extract_age_group_from_specialization(semester_specialization)

        if not base_spec:
            return {
                "authorized": False,
                "reason": f"Invalid semester specialization: {semester_specialization}",
                "matching_licenses": []
            }

        # Special case: INTERNSHIP doesn't have age groups
        if base_spec == "INTERNSHIP":
            internship_licenses = [
                lic for lic in active_licenses
                if lic.specialization_type == "INTERNSHIP"
            ]
            if internship_licenses:
                return {
                    "authorized": True,
                    "reason": f"Has INTERNSHIP license (Level {internship_licenses[0].current_level})",
                    "matching_licenses": internship_licenses
                }
            return {
                "authorized": False,
                "reason": "No INTERNSHIP license found",
                "matching_licenses": []
            }

        # Check PLAYER and COACH licenses for LFA/GANCUJU semesters
        matching_licenses = []

        # 1. Check for direct PLAYER license match
        for lic in active_licenses:
            if lic.specialization_type == "PLAYER":
                min_level = cls.PLAYER_MIN_LEVELS.get(age_group, 1)
                if lic.current_level >= min_level:
                    matching_licenses.append(lic)

        # 2. Check for COACH license (COACH can teach PLAYER sessions!)
        if base_spec == "PLAYER":
            for lic in active_licenses:
                if lic.specialization_type == "COACH":
                    min_level = cls.COACH_MIN_LEVELS.get(age_group, 1)
                    if lic.current_level >= min_level:
                        matching_licenses.append(lic)

        # 3. Check for COACH semester (only COACH license works)
        if base_spec == "COACH":
            for lic in active_licenses:
                if lic.specialization_type == "COACH":
                    min_level = cls.COACH_MIN_LEVELS.get(age_group, 1)
                    if lic.current_level >= min_level:
                        matching_licenses.append(lic)

        # Result
        if matching_licenses:
            license_desc = ", ".join([
                f"{lic.specialization_type} Level {lic.current_level}"
                for lic in matching_licenses
            ])
            return {
                "authorized": True,
                "reason": f"Qualified with: {license_desc}",
                "matching_licenses": matching_licenses
            }

        return {
            "authorized": False,
            "reason": f"No license meets minimum requirement for {semester_specialization} (Age group: {age_group})",
            "matching_licenses": []
        }

    @classmethod
    def can_teach_session(
        cls,
        instructor: User,
        session_specialization: Optional[str],
        is_mixed_session: bool,
        db: Session
    ) -> Dict[str, any]:
        """
        Check if instructor can teach a specific session.

        Args:
            instructor: User object (instructor)
            session_specialization: e.g., "LFA_PLAYER_PRE" (None = mixed session)
            is_mixed_session: Whether session is open to all specializations
            db: Database session

        Returns:
            {
                "authorized": bool,
                "reason": str,
                "matching_licenses": List[UserLicense]
            }
        """
        # Mixed sessions: anyone can teach
        if is_mixed_session or not session_specialization:
            return {
                "authorized": True,
                "reason": "Mixed session (open to all)",
                "matching_licenses": []
            }

        # Get instructor's licenses (marked as active)
        licenses = db.query(UserLicense).filter(
            UserLicense.user_id == instructor.id,
            UserLicense.is_active == True
        ).all()

        # Check expiration for each license (Fase 2)
        active_licenses = []
        for lic in licenses:
            if LicenseRenewalService.check_license_expiration(lic):
                active_licenses.append(lic)

        # Commit any license deactivations
        db.commit()

        if not active_licenses:
            return {
                "authorized": False,
                "reason": "No active licenses found (some may have expired)",
                "matching_licenses": []
            }

        # Extract base specialization and age group
        base_spec = cls.extract_base_specialization(session_specialization)
        age_group = cls.extract_age_group_from_specialization(session_specialization)

        if not base_spec:
            return {
                "authorized": False,
                "reason": f"Invalid session specialization: {session_specialization}",
                "matching_licenses": []
            }

        # Check licenses (same logic as semester check)
        matching_licenses = []

        # PLAYER sessions: PLAYER or COACH license works
        if base_spec == "PLAYER":
            for lic in active_licenses:
                if lic.specialization_type == "PLAYER":
                    min_level = cls.PLAYER_MIN_LEVELS.get(age_group, 1) if age_group else 1
                    if lic.current_level >= min_level:
                        matching_licenses.append(lic)

                # COACH can teach PLAYER sessions
                elif lic.specialization_type == "COACH":
                    min_level = cls.COACH_MIN_LEVELS.get(age_group, 1) if age_group else 1
                    if lic.current_level >= min_level:
                        matching_licenses.append(lic)

        # COACH sessions: only COACH license works
        elif base_spec == "COACH":
            for lic in active_licenses:
                if lic.specialization_type == "COACH":
                    min_level = cls.COACH_MIN_LEVELS.get(age_group, 1) if age_group else 1
                    if lic.current_level >= min_level:
                        matching_licenses.append(lic)

        # INTERNSHIP sessions: only INTERNSHIP license works
        elif base_spec == "INTERNSHIP":
            for lic in active_licenses:
                if lic.specialization_type == "INTERNSHIP":
                    matching_licenses.append(lic)

        # Result
        if matching_licenses:
            license_desc = ", ".join([
                f"{lic.specialization_type} Level {lic.current_level}"
                for lic in matching_licenses
            ])
            return {
                "authorized": True,
                "reason": f"Qualified with: {license_desc}",
                "matching_licenses": matching_licenses
            }

        return {
            "authorized": False,
            "reason": f"No license meets requirement for {session_specialization}",
            "matching_licenses": []
        }

    @classmethod
    def get_qualified_instructors_for_semester(
        cls,
        semester_specialization: str,
        semester_age_group: Optional[str],
        db: Session
    ) -> List[Dict]:
        """
        Get all instructors qualified to teach a semester.

        Args:
            semester_specialization: e.g., "LFA_PLAYER_PRE"
            semester_age_group: e.g., "PRE"
            db: Database session

        Returns:
            List of dicts with instructor info and matching licenses
        """
        # Get all users with ACTIVE licenses
        users_with_licenses = db.query(User).join(UserLicense).filter(
            UserLicense.is_active == True
        ).distinct().all()

        qualified_instructors = []

        for user in users_with_licenses:
            auth_result = cls.can_be_master_instructor(
                instructor=user,
                semester_specialization=semester_specialization,
                semester_age_group=semester_age_group,
                db=db
            )

            if auth_result["authorized"]:
                qualified_instructors.append({
                    "instructor": user,
                    "matching_licenses": auth_result["matching_licenses"],
                    "authorization_reason": auth_result["reason"]
                })

        return qualified_instructors
