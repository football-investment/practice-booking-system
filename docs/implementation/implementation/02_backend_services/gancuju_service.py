#!/usr/bin/env python3
"""
GānCuju Service - Business Logic Layer

Handles GānCuju license management with level progression system:
- License creation and retrieval
- Level promotions (8 levels: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8)
- Competition tracking (wins/total competitions, auto win_rate)
- Teaching hours tracking
- Level demotion (if needed)

Table structure:
- current_level: INTEGER (1-8)
- max_achieved_level: INTEGER (1-8, auto-updated via trigger)
- competitions_entered: INTEGER
- competitions_won: INTEGER
- win_rate: NUMERIC (auto-computed: won/entered*100)
- teaching_hours: INTEGER
- sessions_attended: INTEGER
"""

from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text


class GanCujuService:
    """Service for managing GānCuju licenses with level progression"""

    def __init__(self, db: Session):
        """
        Initialize GānCuju service

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_license(
        self,
        user_id: int,
        starting_level: int = 1
    ) -> Dict:
        """
        Create a new GānCuju license

        Args:
            user_id: User ID
            starting_level: Starting level (1-8, default 1)

        Returns:
            License details dict

        Raises:
            ValueError: If user already has active license or invalid level
        """
        if not (1 <= starting_level <= 8):
            raise ValueError(f"Invalid level. Must be between 1 and 8")

        existing = self.db.execute(
            text("SELECT id FROM gancuju_licenses WHERE user_id = :user_id AND is_active = TRUE"),
            {"user_id": user_id}
        ).fetchone()

        if existing:
            raise ValueError(f"User {user_id} already has an active GānCuju license")

        result = self.db.execute(
            text("""
            INSERT INTO gancuju_licenses (user_id, current_level)
            VALUES (:user_id, :level)
            RETURNING id, user_id, current_level, max_achieved_level,
                      sessions_attended, competitions_entered, competitions_won,
                      win_rate, teaching_hours, created_at
            """),
            {"user_id": user_id, "level": starting_level}
        )
        # NOTE: No commit here! Caller (API endpoint) will commit the transaction
        # This allows atomicity: if credit deduction fails, license creation rolls back

        row = result.fetchone()
        return {
            'id': row[0],
            'user_id': row[1],
            'current_level': row[2],
            'max_achieved_level': row[3],
            'sessions_attended': row[4],
            'competitions_entered': row[5],
            'competitions_won': row[6],
            'win_rate': row[7],
            'teaching_hours': row[8],
            'created_at': row[9]
        }

    def get_license_by_user(self, user_id: int) -> Optional[Dict]:
        """Get active GānCuju license for user"""
        result = self.db.execute(
            text("""
            SELECT id, user_id, current_level, max_achieved_level,
                   sessions_attended, competitions_entered, competitions_won,
                   win_rate, teaching_hours, is_active, created_at, updated_at
            FROM gancuju_licenses
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
            'sessions_attended': result[4],
            'competitions_entered': result[5],
            'competitions_won': result[6],
            'win_rate': result[7],
            'teaching_hours': result[8],
            'is_active': result[9],
            'created_at': result[10],
            'updated_at': result[11]
        }

    def promote_level(self, license_id: int, reason: Optional[str] = None) -> Dict:
        """
        Promote to next level (1->2->3->...->8)
        max_achieved_level auto-updates via trigger

        Raises:
            ValueError: If already at level 8
        """
        current = self.db.execute(
            text("SELECT current_level FROM gancuju_licenses WHERE id = :id AND is_active = TRUE"),
            {"id": license_id}
        ).fetchone()

        if not current:
            raise ValueError(f"License {license_id} not found or inactive")

        current_level = current[0]
        if current_level >= 8:
            raise ValueError(f"Already at maximum level (8)")

        new_level = current_level + 1

        result = self.db.execute(
            text("""
            UPDATE gancuju_licenses
            SET current_level = :new_level
            WHERE id = :license_id
            RETURNING max_achieved_level
            """),
            {"new_level": new_level, "license_id": license_id}
        )

        self.db.commit()

        row = result.fetchone()
        max_achieved = row[0] if row else new_level

        return {
            'license_id': license_id,
            'old_level': current_level,
            'new_level': new_level,
            'max_level_reached': max_achieved,
            'changed_at': datetime.utcnow(),
            'reason': reason
        }

    def demote_level(self, license_id: int, reason: Optional[str] = None) -> Dict:
        """
        Demote to previous level (8->7->...->1)

        Raises:
            ValueError: If already at level 1
        """
        current = self.db.execute(
            text("SELECT current_level, max_achieved_level FROM gancuju_licenses WHERE id = :id AND is_active = TRUE"),
            {"id": license_id}
        ).fetchone()

        if not current:
            raise ValueError(f"License {license_id} not found or inactive")

        current_level = current[0]
        max_achieved = current[1]

        if current_level <= 1:
            raise ValueError(f"Already at minimum level (1)")

        new_level = current_level - 1

        self.db.execute(
            text("UPDATE gancuju_licenses SET current_level = :new_level WHERE id = :license_id"),
            {"new_level": new_level, "license_id": license_id}
        )

        self.db.commit()

        return {
            'license_id': license_id,
            'old_level': current_level,
            'new_level': new_level,
            'max_level_reached': max_achieved,
            'changed_at': datetime.utcnow(),
            'reason': reason
        }

    def record_competition(
        self,
        license_id: int,
        won: bool,
        competition_name: Optional[str] = None
    ) -> Dict:
        """
        Record competition result
        Automatically updates win_rate via GENERATED column

        Args:
            license_id: License ID
            won: True if won, False if lost
        """
        if won:
            result = self.db.execute(
                text("""
                UPDATE gancuju_licenses
                SET competitions_entered = competitions_entered + 1,
                    competitions_won = competitions_won + 1
                WHERE id = :license_id AND is_active = TRUE
                RETURNING competitions_entered, competitions_won, win_rate
                """),
                {"license_id": license_id}
            )
        else:
            result = self.db.execute(
                text("""
                UPDATE gancuju_licenses
                SET competitions_entered = competitions_entered + 1
                WHERE id = :license_id AND is_active = TRUE
                RETURNING competitions_entered, competitions_won, win_rate
                """),
                {"license_id": license_id}
            )

        self.db.commit()

        row = result.fetchone()
        if not row:
            raise ValueError(f"License {license_id} not found or inactive")

        return {
            'license_id': license_id,
            'result': 'WON' if won else 'LOST',
            'competitions_entered': row[0],
            'competitions_won': row[1],
            'win_rate': row[2],
            'competition_name': competition_name
        }

    def record_teaching_hours(
        self,
        license_id: int,
        hours: int,
        description: Optional[str] = None
    ) -> Dict:
        """Record teaching hours (integer)"""
        if hours <= 0:
            raise ValueError("Teaching hours must be positive")

        result = self.db.execute(
            text("""
            UPDATE gancuju_licenses
            SET teaching_hours = teaching_hours + :hours
            WHERE id = :license_id AND is_active = TRUE
            RETURNING teaching_hours
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
            'total_teaching_hours': row[0],
            'description': description
        }

    def get_license_stats(self, license_id: int) -> Dict:
        """
        Get comprehensive license statistics

        Returns:
            Dict with current/max level, competition stats, teaching hours
        """
        result = self.db.execute(
            text("""
            SELECT current_level, max_achieved_level,
                   competitions_entered, competitions_won, win_rate,
                   teaching_hours, sessions_attended
            FROM gancuju_licenses
            WHERE id = :license_id AND is_active = TRUE
            """),
            {"license_id": license_id}
        ).fetchone()

        if not result:
            raise ValueError(f"License {license_id} not found or inactive")

        return {
            'license_id': license_id,
            'current_level': result[0],
            'max_achieved_level': result[1],
            'competitions_entered': result[2],
            'competitions_won': result[3],
            'win_rate': result[4],
            'teaching_hours': result[5],
            'sessions_attended': result[6]
        }
