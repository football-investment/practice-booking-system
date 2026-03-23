#!/usr/bin/env python3
"""
Internship Service - Business Logic Layer

Handles Internship license management with XP and level progression:
- License creation with 15-month expiry
- XP tracking (auto level-up via trigger)
- Credit system (purchase, spend)
- Expiry management and renewal
- Level progression (1-8 based on XP)

Table structure:
- total_xp: INTEGER (0+, triggers auto level-up)
- current_level: INTEGER (1-8, auto-computed from XP)
- max_achieved_level: INTEGER (1-8, auto-updated via trigger)
- credit_balance: INTEGER
- expires_at: TIMESTAMP (15 months from creation)
- sessions_completed: INTEGER
"""

from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text


class InternshipService:
    """Service for managing Internship licenses with XP progression"""

    def __init__(self, db: Session):
        """
        Initialize Internship service

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_license(
        self,
        user_id: int,
        initial_credits: int = 0,
        duration_months: int = 15
    ) -> Dict:
        """
        Create a new Internship license

        Args:
            user_id: User ID
            initial_credits: Initial credit balance (default 0)
            duration_months: License duration in months (default 15)

        Returns:
            License details dict

        Raises:
            ValueError: If user already has active license
        """
        existing = self.db.execute(
            text("SELECT id FROM internship_licenses WHERE user_id = :user_id AND is_active = TRUE"),
            {"user_id": user_id}
        ).fetchone()

        if existing:
            raise ValueError(f"User {user_id} already has an active Internship license")

        # Calculate expiry date
        expires_at = datetime.now(timezone.utc) + timedelta(days=duration_months * 30)

        result = self.db.execute(
            text("""
            INSERT INTO internship_licenses (user_id, credit_balance, expires_at)
            VALUES (:user_id, :credits, :expires_at)
            RETURNING id, user_id, credit_balance, total_xp, current_level,
                      max_achieved_level, sessions_completed, expires_at,
                      is_active, created_at
            """),
            {
                "user_id": user_id,
                "credits": initial_credits,
                "expires_at": expires_at
            }
        )
        # NOTE: No commit here! Caller (API endpoint) will commit the transaction
        # This allows atomicity: if credit deduction fails, license creation rolls back

        row = result.fetchone()
        return {
            'id': row[0],
            'user_id': row[1],
            'credit_balance': row[2],
            'total_xp': row[3],
            'current_level': row[4],
            'max_achieved_level': row[5],
            'sessions_completed': row[6],
            'expires_at': row[7],
            'is_active': row[8],
            'created_at': row[9]
        }

    def get_license_by_user(self, user_id: int) -> Optional[Dict]:
        """Get active Internship license for user"""
        result = self.db.execute(
            text("""
            SELECT id, user_id, credit_balance, total_xp, current_level,
                   max_achieved_level, sessions_completed, expires_at,
                   is_active, created_at, updated_at
            FROM internship_licenses
            WHERE user_id = :user_id AND is_active = TRUE
            """),
            {"user_id": user_id}
        ).fetchone()

        if not result:
            return None

        return {
            'id': result[0],
            'user_id': result[1],
            'credit_balance': result[2],
            'total_xp': result[3],
            'current_level': result[4],
            'max_achieved_level': result[5],
            'sessions_completed': result[6],
            'expires_at': result[7],
            'is_active': result[8],
            'created_at': result[9],
            'updated_at': result[10]
        }

    def add_xp(
        self,
        license_id: int,
        xp_amount: int,
        reason: Optional[str] = None
    ) -> Dict:
        """
        Add XP to license (triggers auto level-up via database trigger)

        Args:
            license_id: License ID
            xp_amount: XP to add (must be positive)
            reason: Optional reason for XP gain

        Returns:
            Dict with new total_xp, current_level, level_up indicator

        Raises:
            ValueError: If license not found or xp_amount invalid
        """
        if xp_amount <= 0:
            raise ValueError("XP amount must be positive")

        # Get current state
        current = self.db.execute(
            text("SELECT total_xp, current_level FROM internship_licenses WHERE id = :id AND is_active = TRUE"),
            {"id": license_id}
        ).fetchone()

        if not current:
            raise ValueError(f"License {license_id} not found or inactive")

        old_level = current[1]

        # Add XP (auto level-up via trigger)
        result = self.db.execute(
            text("""
            UPDATE internship_licenses
            SET total_xp = total_xp + :xp_amount
            WHERE id = :license_id AND is_active = TRUE
            RETURNING total_xp, current_level, max_achieved_level
            """),
            {"license_id": license_id, "xp_amount": xp_amount}
        )
        self.db.commit()

        row = result.fetchone()
        if not row:
            raise ValueError(f"License {license_id} not found or inactive")

        new_level = row[1]
        leveled_up = new_level > old_level

        return {
            'license_id': license_id,
            'xp_added': xp_amount,
            'total_xp': row[0],
            'old_level': old_level,
            'current_level': new_level,
            'max_achieved_level': row[2],
            'leveled_up': leveled_up,
            'reason': reason
        }

    def check_expiry(self, license_id: int) -> Dict:
        """
        Check if license is expired

        Returns:
            Dict with is_expired, expires_at, days_remaining
        """
        result = self.db.execute(
            text("SELECT expires_at, is_active FROM internship_licenses WHERE id = :id"),
            {"id": license_id}
        ).fetchone()

        if not result:
            raise ValueError(f"License {license_id} not found")

        expires_at = result[0]
        is_active = result[1]
        now = datetime.now(timezone.utc)

        is_expired = expires_at < now
        days_remaining = max(0, (expires_at - now).days)

        return {
            'license_id': license_id,
            'expires_at': expires_at,
            'is_expired': is_expired,
            'is_active': is_active,
            'days_remaining': days_remaining
        }

    def renew_license(
        self,
        license_id: int,
        extension_months: int = 15
    ) -> Dict:
        """
        Renew/extend license expiry

        Args:
            license_id: License ID
            extension_months: Months to extend (default 15)

        Returns:
            Dict with old_expires_at, new_expires_at
        """
        # Get current expiry
        current = self.db.execute(
            text("SELECT expires_at FROM internship_licenses WHERE id = :id"),
            {"id": license_id}
        ).fetchone()

        if not current:
            raise ValueError(f"License {license_id} not found")

        old_expires = current[0]

        # Extend from current expiry (or now if already expired)
        base_date = max(old_expires, datetime.now(timezone.utc))
        new_expires = base_date + timedelta(days=extension_months * 30)

        self.db.execute(
            text("""
            UPDATE internship_licenses
            SET expires_at = :new_expires, is_active = TRUE
            WHERE id = :license_id
            """),
            {"license_id": license_id, "new_expires": new_expires}
        )
        self.db.commit()

        return {
            'license_id': license_id,
            'old_expires_at': old_expires,
            'new_expires_at': new_expires,
            'extension_months': extension_months
        }

    def purchase_credits(
        self,
        license_id: int,
        amount: int,
        payment_verified: bool = False,
        payment_proof_url: Optional[str] = None,
        payment_reference_code: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[Dict, int]:
        """Purchase credits for license"""
        if amount <= 0:
            raise ValueError("Purchase amount must be positive")

        # Create transaction
        result = self.db.execute(
            text("""
            INSERT INTO internship_credit_transactions (
                license_id, transaction_type, amount,
                payment_verified, payment_proof_url, payment_reference_code,
                description
            )
            VALUES (
                :license_id, 'PURCHASE', :amount,
                :verified, :proof_url, :ref_code, :description
            )
            RETURNING id, amount, created_at
            """),
            {
                "license_id": license_id,
                "amount": amount,
                "verified": payment_verified,
                "proof_url": payment_proof_url,
                "ref_code": payment_reference_code,
                "description": description or f"Purchased {amount} credits"
            }
        )

        # Update license balance
        self.db.execute(
            text("""
            UPDATE internship_licenses
            SET credit_balance = credit_balance + :amount
            WHERE id = :license_id
            """),
            {"license_id": license_id, "amount": amount}
        )

        self.db.commit()

        tx_row = result.fetchone()

        # Get new balance
        balance_row = self.db.execute(
            text("SELECT credit_balance FROM internship_licenses WHERE id = :license_id"),
            {"license_id": license_id}
        ).fetchone()

        return (
            {
                'transaction_id': tx_row[0],
                'amount': tx_row[1],
                'created_at': tx_row[2],
                'payment_verified': payment_verified
            },
            balance_row[0]
        )

    def spend_credits(
        self,
        license_id: int,
        enrollment_id: int,
        amount: int,
        description: Optional[str] = None
    ) -> Tuple[Dict, int]:
        """Spend credits from license"""
        if amount <= 0:
            raise ValueError("Spend amount must be positive")

        # Check balance
        balance_row = self.db.execute(
            text("SELECT credit_balance FROM internship_licenses WHERE id = :license_id"),
            {"license_id": license_id}
        ).fetchone()

        if not balance_row:
            raise ValueError(f"License {license_id} not found")

        current_balance = balance_row[0]
        if current_balance < amount:
            raise ValueError(f"Insufficient balance. Have: {current_balance}, need: {amount}")

        # Create transaction (store as negative)
        result = self.db.execute(
            text("""
            INSERT INTO internship_credit_transactions (
                license_id, enrollment_id, transaction_type, amount, description
            )
            VALUES (
                :license_id, :enrollment_id, 'SPENT', :amount, :description
            )
            RETURNING id, amount, created_at
            """),
            {
                "license_id": license_id,
                "enrollment_id": enrollment_id,
                "amount": -amount,  # Store as negative
                "description": description or f"Spent {amount} credits on enrollment"
            }
        )

        # Update license balance
        self.db.execute(
            text("""
            UPDATE internship_licenses
            SET credit_balance = credit_balance - :amount
            WHERE id = :license_id
            """),
            {"license_id": license_id, "amount": amount}
        )

        self.db.commit()

        tx_row = result.fetchone()

        return (
            {
                'transaction_id': tx_row[0],
                'amount': tx_row[1],
                'created_at': tx_row[2]
            },
            current_balance - amount
        )

    def get_credit_balance(self, license_id: int) -> int:
        """Get current credit balance"""
        result = self.db.execute(
            text("SELECT credit_balance FROM internship_licenses WHERE id = :license_id"),
            {"license_id": license_id}
        ).fetchone()

        if not result:
            raise ValueError(f"License {license_id} not found")

        return result[0]
