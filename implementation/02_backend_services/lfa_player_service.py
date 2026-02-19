"""
LFA Player Service
==================
Business logic layer for LFA Player license management.

This service handles:
- License creation and retrieval
- Skill average updates (triggers auto-compute overall_avg)
- Credit transactions (purchase, spend, refund)
- Credit balance queries
"""

from typing import Optional, Dict, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, text


class LFAPlayerService:
    """Service for managing LFA Player licenses"""

    def __init__(self, db: Session):
        """
        Initialize service with database session

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_license(
        self,
        user_id: int,
        age_group: str,
        initial_credits: int = 0,
        initial_skills: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        Create a new LFA Player license

        Args:
            user_id: User ID to create license for
            age_group: Age group (PRE, YOUTH, AMATEUR, PRO)
            initial_credits: Starting credit balance (default: 0)
            initial_skills: Dict of initial skill averages (default: all 0)

        Returns:
            Dict with license details

        Raises:
            ValueError: If user already has active license
            ValueError: If age_group invalid
        """
        # Validate age group
        valid_age_groups = ['PRE', 'YOUTH', 'AMATEUR', 'PRO']
        if age_group not in valid_age_groups:
            raise ValueError(f"Invalid age_group. Must be one of: {valid_age_groups}")

        # Check for existing active license
        existing = self.db.execute(
            text("""
            SELECT id FROM lfa_player_licenses
            WHERE user_id = :user_id AND is_active = TRUE
            """),
            {"user_id": user_id}
        ).fetchone()

        if existing:
            raise ValueError(f"User {user_id} already has an active LFA Player license")

        # Set default skills (7 skills total)
        skills = initial_skills or {}
        skill_defaults = {
            'heading_avg': 0.0,
            'shooting_avg': 0.0,
            'crossing_avg': 0.0,
            'passing_avg': 0.0,
            'dribbling_avg': 0.0,
            'ball_control_avg': 0.0,
            'defending_avg': 0.0
        }
        skill_defaults.update(skills)

        # Create license
        result = self.db.execute(
            text("""
            INSERT INTO lfa_player_licenses (
                user_id, age_group, credit_balance,
                heading_avg, shooting_avg, crossing_avg,
                passing_avg, dribbling_avg, ball_control_avg, defending_avg
            )
            VALUES (
                :user_id, :age_group, :credit_balance,
                :heading, :shooting, :crossing,
                :passing, :dribbling, :ball_control, :defending
            )
            RETURNING id, user_id, age_group, credit_balance, overall_avg, created_at
            """),
            {
                "user_id": user_id,
                "age_group": age_group,
                "credit_balance": initial_credits,
                "heading": skill_defaults['heading_avg'],
                "shooting": skill_defaults['shooting_avg'],
                "crossing": skill_defaults['crossing_avg'],
                "passing": skill_defaults['passing_avg'],
                "dribbling": skill_defaults['dribbling_avg'],
                "ball_control": skill_defaults['ball_control_avg'],
                "defending": skill_defaults['defending_avg']
            }
        )
        # NOTE: No commit here! Caller (API endpoint) will commit the transaction
        # This allows atomicity: if credit deduction fails, license creation rolls back

        row = result.fetchone()
        return {
            'id': row[0],
            'user_id': row[1],
            'age_group': row[2],
            'credit_balance': row[3],
            'overall_avg': float(row[4]),
            'created_at': row[5]
        }

    def get_license_by_user(self, user_id: int) -> Optional[Dict]:
        """
        Get active LFA Player license for user

        Args:
            user_id: User ID

        Returns:
            License details dict or None if not found
        """
        result = self.db.execute(
            text("""
            SELECT id, user_id, age_group, credit_balance,
                   heading_avg, shooting_avg, crossing_avg,
                   passing_avg, dribbling_avg, ball_control_avg, defending_avg,
                   overall_avg, is_active, created_at, updated_at
            FROM lfa_player_licenses
            WHERE user_id = :user_id AND is_active = TRUE
            """),
            {"user_id": user_id}
        ).fetchone()

        if not result:
            return None

        return {
            'id': result[0],
            'user_id': result[1],
            'age_group': result[2],
            'credit_balance': result[3],
            'skills': {
                'heading_avg': float(result[4]),
                'shooting_avg': float(result[5]),
                'crossing_avg': float(result[6]),
                'passing_avg': float(result[7]),
                'dribbling_avg': float(result[8]),
                'ball_control_avg': float(result[9]),
                'defending_avg': float(result[10])
            },
            'overall_avg': float(result[11]),
            'is_active': result[12],
            'created_at': result[13],
            'updated_at': result[14]
        }

    def update_skill_avg(
        self,
        license_id: int,
        skill_name: str,
        new_avg: float
    ) -> Dict:
        """
        Update a specific skill average (triggers overall_avg auto-compute)

        Args:
            license_id: License ID
            skill_name: Skill name (heading, shooting, crossing, passing, dribbling, ball_control, defending)
            new_avg: New average value (0-100)

        Returns:
            Updated license with new overall_avg

        Raises:
            ValueError: If skill_name invalid or new_avg out of range
        """
        valid_skills = [
            'heading_avg', 'shooting_avg', 'crossing_avg',
            'passing_avg', 'dribbling_avg', 'ball_control_avg', 'defending_avg'
        ]

        # Normalize skill name (add _avg if missing)
        if not skill_name.endswith('_avg'):
            skill_name = f"{skill_name}_avg"

        if skill_name not in valid_skills:
            raise ValueError(f"Invalid skill_name. Must be one of: {valid_skills}")

        if not (0 <= new_avg <= 100):
            raise ValueError("new_avg must be between 0 and 100")

        # Update skill (overall_avg auto-computes via GENERATED ALWAYS AS)
        result = self.db.execute(
            text(f"""
            UPDATE lfa_player_licenses
            SET {skill_name} = :new_avg
            WHERE id = :license_id AND is_active = TRUE
            RETURNING id, {skill_name}, overall_avg, updated_at
            """),
            {"license_id": license_id, "new_avg": new_avg}
        )
        self.db.commit()

        row = result.fetchone()
        if not row:
            raise ValueError(f"License {license_id} not found or inactive")

        return {
            'id': row[0],
            'skill_name': skill_name,
            'new_avg': float(row[1]),
            'overall_avg': float(row[2]),
            'updated_at': row[3]
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
        """
        Purchase credits for license

        Args:
            license_id: License ID
            amount: Number of credits to purchase (positive integer)
            payment_verified: Whether payment is verified
            payment_proof_url: URL to payment proof
            payment_reference_code: Payment reference code
            description: Transaction description

        Returns:
            Tuple of (transaction_dict, new_balance)

        Raises:
            ValueError: If amount <= 0
        """
        if amount <= 0:
            raise ValueError("Purchase amount must be positive")

        # Create transaction
        result = self.db.execute(
            text("""
            INSERT INTO lfa_player_credit_transactions (
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
            UPDATE lfa_player_licenses
            SET credit_balance = credit_balance + :amount
            WHERE id = :license_id
            """),
            {"license_id": license_id, "amount": amount}
        )

        self.db.commit()

        tx_row = result.fetchone()

        # Get new balance
        balance_row = self.db.execute(
            text("SELECT credit_balance FROM lfa_player_licenses WHERE id = :license_id"),
            {"license_id": license_id}
        ).fetchone()

        return (
            {
                'transaction_id': tx_row[0],
                'amount': tx_row[1],
                'created_at': tx_row[2]
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
        """
        Spend credits from license (e.g., for enrollment)

        Args:
            license_id: License ID
            enrollment_id: Enrollment ID (required for SPENT transactions)
            amount: Number of credits to spend (positive integer, will be stored as negative)
            description: Transaction description

        Returns:
            Tuple of (transaction_dict, new_balance)

        Raises:
            ValueError: If amount <= 0 or insufficient balance
        """
        if amount <= 0:
            raise ValueError("Spend amount must be positive")

        # Check balance
        balance_row = self.db.execute(
            text("SELECT credit_balance FROM lfa_player_licenses WHERE id = :license_id"),
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
            INSERT INTO lfa_player_credit_transactions (
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
            UPDATE lfa_player_licenses
            SET credit_balance = credit_balance - :amount
            WHERE id = :license_id
            """),
            {"license_id": license_id, "amount": amount}
        )

        self.db.commit()

        tx_row = result.fetchone()
        new_balance = current_balance - amount

        return (
            {
                'transaction_id': tx_row[0],
                'amount': tx_row[1],  # This will be negative
                'created_at': tx_row[2]
            },
            new_balance
        )

    def get_credit_balance(self, license_id: int) -> int:
        """
        Get current credit balance

        Args:
            license_id: License ID

        Returns:
            Current credit balance

        Raises:
            ValueError: If license not found
        """
        result = self.db.execute(
            text("SELECT credit_balance FROM lfa_player_licenses WHERE id = :license_id"),
            {"license_id": license_id}
        ).fetchone()

        if not result:
            raise ValueError(f"License {license_id} not found")

        return result[0]

    def get_transaction_history(
        self,
        license_id: int,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get credit transaction history

        Args:
            license_id: License ID
            limit: Maximum number of transactions to return

        Returns:
            List of transaction dicts, newest first
        """
        result = self.db.execute(
            text("""
            SELECT id, transaction_type, amount, enrollment_id,
                   payment_verified, payment_reference_code,
                   description, created_at
            FROM lfa_player_credit_transactions
            WHERE license_id = :license_id
            ORDER BY created_at DESC
            LIMIT :limit
            """),
            {"license_id": license_id, "limit": limit}
        )

        transactions = []
        for row in result:
            transactions.append({
                'id': row[0],
                'transaction_type': row[1],
                'amount': row[2],
                'enrollment_id': row[3],
                'payment_verified': row[4],
                'payment_reference_code': row[5],
                'description': row[6],
                'created_at': row[7]
            })

        return transactions
