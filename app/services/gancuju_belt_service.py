"""
🥋 Gancuju Belt Service
Handles belt progression tracking for Gancuju Player specialization
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime, timezone

from ..models.belt_promotion import BeltPromotion
from ..models.license import UserLicense
from ..models.user import User


class GancujuBeltService:
    """Service for managing Gancuju belt progressions"""

    # Valid belt levels in order
    BELT_LEVELS = ['white', 'yellow', 'green', 'blue', 'brown', 'grey', 'black', 'red']

    def __init__(self, db: Session):
        self.db = db

    def get_current_belt(self, user_license_id: int) -> str:
        """Get current belt level from user license"""
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license or not license.current_belt:
            return 'white'  # Default starting belt

        return license.current_belt.lower()

    def get_belt_history(self, user_license_id: int) -> List[BeltPromotion]:
        """Get all belt promotions for a license"""
        return self.db.query(BeltPromotion).filter(
            BeltPromotion.user_license_id == user_license_id
        ).order_by(BeltPromotion.promoted_at.asc()).all()

    def get_next_belt(self, current_belt: str) -> Optional[str]:
        """Get the next belt in progression"""
        try:
            current_index = self.BELT_LEVELS.index(current_belt.lower())
            if current_index < len(self.BELT_LEVELS) - 1:
                return self.BELT_LEVELS[current_index + 1]
            return None  # Already at highest belt
        except ValueError:
            return None

    def can_promote(self, user_license_id: int) -> bool:
        """Check if student can be promoted to next belt"""
        current_belt = self.get_current_belt(user_license_id)
        next_belt = self.get_next_belt(current_belt)
        return next_belt is not None

    def promote_belt(
        self,
        user_license_id: int,
        promoted_by: int,
        notes: Optional[str] = None
    ) -> Optional[BeltPromotion]:
        """
        Promote student to next belt level

        Args:
            user_license_id: UserLicense ID
            promoted_by: Instructor/admin user ID
            notes: Optional promotion notes

        Returns:
            Created BeltPromotion or None if cannot promote
        """
        current_belt = self.get_current_belt(user_license_id)
        next_belt = self.get_next_belt(current_belt)

        if not next_belt:
            return None

        # Create promotion record
        promotion = BeltPromotion(
            user_license_id=user_license_id,
            from_belt=current_belt,
            to_belt=next_belt,
            promoted_by=promoted_by,
            promoted_at=datetime.now(timezone.utc),
            notes=notes
        )

        self.db.add(promotion)

        # Update license
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if license:
            license.current_belt = next_belt

        self.db.flush()

        return promotion
