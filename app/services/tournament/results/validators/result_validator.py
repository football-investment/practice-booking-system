"""
Result Validator

Validates submitted match results before processing.
Extracted from match_results.py as part of P2 decomposition.
"""

from typing import List, Set
from sqlalchemy.orm import Session

from app.models.semester_enrollment import SemesterEnrollment


class ResultValidator:
    """
    Validate submitted match results.

    Handles:
    - User enrollment validation
    - Rank uniqueness validation
    - Duplicate detection
    """

    def __init__(self, db: Session):
        """
        Initialize validator with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_enrolled_user_ids(
        self,
        tournament_id: int,
        user_ids: List[int]
    ) -> Set[int]:
        """
        Get set of enrolled user IDs for tournament.

        Args:
            tournament_id: Tournament ID
            user_ids: List of user IDs to check

        Returns:
            Set of enrolled user IDs
        """
        enrollments = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.user_id.in_(user_ids),
            SemesterEnrollment.is_active == True
        ).all()

        return {e.user_id for e in enrollments}

    def validate_users_enrolled(
        self,
        tournament_id: int,
        user_ids: List[int]
    ) -> tuple[bool, Set[int]]:
        """
        Validate that all users are enrolled in tournament.

        Args:
            tournament_id: Tournament ID
            user_ids: List of user IDs to validate

        Returns:
            Tuple of (is_valid, invalid_user_ids)
            - is_valid: True if all users enrolled
            - invalid_user_ids: Set of user IDs not enrolled
        """
        enrolled_user_ids = self.get_enrolled_user_ids(tournament_id, user_ids)
        invalid_users = set(user_ids) - enrolled_user_ids

        return len(invalid_users) == 0, invalid_users

    @staticmethod
    def validate_ranks_unique(ranks: List[int]) -> tuple[bool, str]:
        """
        Validate that ranks are unique (no duplicates).

        Args:
            ranks: List of rank values

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if ranks are unique
            - error_message: Error message if not valid, empty string otherwise
        """
        if len(ranks) != len(set(ranks)):
            return False, "Duplicate ranks are not allowed"

        return True, ""

    def validate_match_results(
        self,
        tournament_id: int,
        user_ids: List[int],
        ranks: List[int]
    ) -> tuple[bool, str]:
        """
        Validate match results submission.

        Args:
            tournament_id: Tournament ID
            user_ids: List of user IDs in results
            ranks: List of rank values

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if validation passes
            - error_message: Error message if not valid, empty string otherwise
        """
        # Validate users enrolled
        users_valid, invalid_users = self.validate_users_enrolled(
            tournament_id, user_ids
        )

        if not users_valid:
            return False, f"Users {invalid_users} are not enrolled in this tournament"

        # Validate ranks unique
        ranks_valid, error_message = self.validate_ranks_unique(ranks)

        if not ranks_valid:
            return False, error_message

        return True, ""


# Export main class
__all__ = ["ResultValidator"]
