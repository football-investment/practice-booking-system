#!/usr/bin/env python3
"""
Coach Service - Business Logic Layer

Handles Coach license management with certification system:
- License creation with 2-year expiry
- Level progression (1-8)
- Theory and practice hours tracking
- Expiry management and renewal
- Manual level promotion

Table structure:
- current_level: INTEGER (1-8)
- max_achieved_level: INTEGER (1-8, auto-updated via trigger)
- theory_hours: INTEGER (0+)
- practice_hours: INTEGER (0+)
- expires_at: TIMESTAMP (2 years from creation)
- is_expired: BOOLEAN (auto-updated via trigger)
"""

from typing import Optional, Dict
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text


class CoachService:
    """Service for managing Coach licenses with certification levels"""

    def __init__(self, db: Session):
        """
        Initialize Coach service

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_license(
        self,
        user_id: int,
        starting_level: int = 1,
        duration_years: int = 2
    ) -> Dict:
        """
        Create a new Coach license

        Args:
            user_id: User ID
            starting_level: Starting certification level (1-8, default 1)
            duration_years: License duration in years (default 2)

        Returns:
            License details dict

        Raises:
            ValueError: If user already has active license or invalid level
        """
        if not (1 <= starting_level <= 8):
            raise ValueError(f"Invalid level. Must be between 1 and 8")

        existing = self.db.execute(
            text("SELECT id FROM coach_licenses WHERE user_id = :user_id AND is_active = TRUE"),
            {"user_id": user_id}
        ).fetchone()

        if existing:
            raise ValueError(f"User {user_id} already has an active Coach license")

        # Calculate expiry date
        expires_at = datetime.now(timezone.utc) + timedelta(days=duration_years * 365)

        result = self.db.execute(
            text("""
            INSERT INTO coach_licenses (user_id, current_level, expires_at)
            VALUES (:user_id, :level, :expires_at)
            RETURNING id, user_id, current_level, max_achieved_level,
                      theory_hours, practice_hours, expires_at,
                      is_expired, is_active, created_at
            """),
            {
                "user_id": user_id,
                "level": starting_level,
                "expires_at": expires_at
            }
        )
        # NOTE: No commit here! Caller (API endpoint) will commit the transaction
        # This allows atomicity: if credit deduction fails, license creation rolls back

        row = result.fetchone()
        return {
            'id': row[0],
            'user_id': row[1],
            'current_level': row[2],
            'max_achieved_level': row[3],
            'theory_hours': row[4],
            'practice_hours': row[5],
            'expires_at': row[6],
            'is_expired': row[7],
            'is_active': row[8],
            'created_at': row[9]
        }

    def get_license_by_user(self, user_id: int) -> Optional[Dict]:
        """Get active Coach license for user"""
        result = self.db.execute(
            text("""
            SELECT id, user_id, current_level, max_achieved_level,
                   theory_hours, practice_hours, expires_at,
                   is_expired, is_active, created_at, updated_at
            FROM coach_licenses
            WHERE user_id = :user_id AND is_active = TRUE
            """),
            {"user_id": user_id}
        ).fetchone()

        if not result:
            return None

        return {
            'id': result[0],
            'user_id': result[1],
            'current_level': result[2],
            'max_achieved_level': result[3],
            'theory_hours': result[4],
            'practice_hours': result[5],
            'expires_at': result[6],
            'is_expired': result[7],
            'is_active': result[8],
            'created_at': result[9],
            'updated_at': result[10]
        }

    def add_theory_hours(
        self,
        license_id: int,
        hours: int,
        description: Optional[str] = None
    ) -> Dict:
        """
        Add theory training hours

        Args:
            license_id: License ID
            hours: Theory hours to add (must be positive)
            description: Optional description

        Returns:
            Dict with hours_added, total_theory_hours
        """
        if hours <= 0:
            raise ValueError("Theory hours must be positive")

        result = self.db.execute(
            text("""
            UPDATE coach_licenses
            SET theory_hours = theory_hours + :hours
            WHERE id = :license_id AND is_active = TRUE
            RETURNING theory_hours
            """),
            {"license_id": license_id, "hours": hours}
        )

        self.db.commit()

        row = result.fetchone()
        if not row:
            raise ValueError(f"License {license_id} not found or inactive")

        return {
            'license_id': license_id,
            'hours_added': hours,
            'total_theory_hours': row[0],
            'description': description
        }

    def add_practice_hours(
        self,
        license_id: int,
        hours: int,
        description: Optional[str] = None
    ) -> Dict:
        """
        Add practical training hours

        Args:
            license_id: License ID
            hours: Practice hours to add (must be positive)
            description: Optional description

        Returns:
            Dict with hours_added, total_practice_hours
        """
        if hours <= 0:
            raise ValueError("Practice hours must be positive")

        result = self.db.execute(
            text("""
            UPDATE coach_licenses
            SET practice_hours = practice_hours + :hours
            WHERE id = :license_id AND is_active = TRUE
            RETURNING practice_hours
            """),
            {"license_id": license_id, "hours": hours}
        )

        self.db.commit()

        row = result.fetchone()
        if not row:
            raise ValueError(f"License {license_id} not found or inactive")

        return {
            'license_id': license_id,
            'hours_added': hours,
            'total_practice_hours': row[0],
            'description': description
        }

    def check_expiry(self, license_id: int) -> Dict:
        """
        Check if certification is expired

        Returns:
            Dict with is_expired, expires_at, days_remaining
        """
        result = self.db.execute(
            text("SELECT expires_at, is_expired, is_active FROM coach_licenses WHERE id = :id"),
            {"id": license_id}
        ).fetchone()

        if not result:
            raise ValueError(f"License {license_id} not found")

        expires_at = result[0]
        is_expired = result[1]
        is_active = result[2]
        now = datetime.now(timezone.utc)

        days_remaining = max(0, (expires_at - now).days)

        return {
            'license_id': license_id,
            'expires_at': expires_at,
            'is_expired': is_expired,
            'is_active': is_active,
            'days_remaining': days_remaining
        }

    def renew_certification(
        self,
        license_id: int,
        extension_years: int = 2
    ) -> Dict:
        """
        Renew/extend certification expiry

        Args:
            license_id: License ID
            extension_years: Years to extend (default 2)

        Returns:
            Dict with old_expires_at, new_expires_at
        """
        # Get current expiry
        current = self.db.execute(
            text("SELECT expires_at FROM coach_licenses WHERE id = :id"),
            {"id": license_id}
        ).fetchone()

        if not current:
            raise ValueError(f"License {license_id} not found")

        old_expires = current[0]

        # Extend from current expiry (or now if already expired)
        base_date = max(old_expires, datetime.now(timezone.utc))
        new_expires = base_date + timedelta(days=extension_years * 365)

        self.db.execute(
            text("""
            UPDATE coach_licenses
            SET expires_at = :new_expires, is_expired = FALSE, is_active = TRUE
            WHERE id = :license_id
            """),
            {"license_id": license_id, "new_expires": new_expires}
        )
        self.db.commit()

        return {
            'license_id': license_id,
            'old_expires_at': old_expires,
            'new_expires_at': new_expires,
            'extension_years': extension_years
        }

    def promote_level(
        self,
        license_id: int,
        reason: Optional[str] = None
    ) -> Dict:
        """
        Promote to next certification level (1->2->3->...->8)
        max_achieved_level auto-updates via trigger

        Args:
            license_id: License ID
            reason: Optional reason for promotion

        Returns:
            Dict with old_level, new_level, promoted_at

        Raises:
            ValueError: If already at level 8
        """
        current = self.db.execute(
            text("SELECT current_level FROM coach_licenses WHERE id = :id AND is_active = TRUE"),
            {"id": license_id}
        ).fetchone()

        if not current:
            raise ValueError(f"License {license_id} not found or inactive")

        current_level = current[0]
        if current_level >= 8:
            raise ValueError(f"Already at maximum certification level (8)")

        new_level = current_level + 1

        self.db.execute(
            text("UPDATE coach_licenses SET current_level = :new_level WHERE id = :license_id"),
            {"new_level": new_level, "license_id": license_id}
        )

        self.db.commit()

        return {
            'license_id': license_id,
            'old_level': current_level,
            'new_level': new_level,
            'promoted_at': datetime.now(timezone.utc),
            'reason': reason
        }

    def get_license_stats(self, license_id: int) -> Dict:
        """
        Get comprehensive license statistics

        Returns:
            Dict with current/max level, hours, expiry status
        """
        result = self.db.execute(
            text("""
            SELECT current_level, max_achieved_level,
                   theory_hours, practice_hours,
                   expires_at, is_expired, is_active
            FROM coach_licenses
            WHERE id = :license_id
            """),
            {"license_id": license_id}
        ).fetchone()

        if not result:
            raise ValueError(f"License {license_id} not found")

        expires_at = result[4]
        now = datetime.now(timezone.utc)
        days_remaining = max(0, (expires_at - now).days)

        return {
            'license_id': license_id,
            'current_level': result[0],
            'max_achieved_level': result[1],
            'theory_hours': result[2],
            'practice_hours': result[3],
            'total_hours': result[2] + result[3],
            'expires_at': expires_at,
            'is_expired': result[5],
            'is_active': result[6],
            'days_remaining': days_remaining
        }
