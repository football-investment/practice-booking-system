"""
XP Transaction Service - Centralized XP Management

This service provides the SINGLE SOURCE OF TRUTH for creating XP transactions.
All XP transaction creation MUST go through this service to prevent dual-path bugs.

Business Invariant: One XP transaction per (user_id, semester_id, transaction_type)
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime
import logging

from ..models.xp_transaction import XPTransaction

logger = logging.getLogger(__name__)


class XPTransactionService:
    """Centralized service for XP transaction management"""

    def __init__(self, db: Session):
        self.db = db

    def award_xp(
        self,
        user_id: int,
        transaction_type: str,
        amount: int,
        balance_after: int,
        description: str,
        semester_id: Optional[int] = None
    ) -> tuple[XPTransaction, bool]:
        """
        Award XP to a user with duplicate protection.

        Args:
            user_id: User receiving XP
            transaction_type: Type of transaction (e.g., "TOURNAMENT_REWARD", "SESSION_ATTENDANCE")
            amount: XP amount (should be positive for awards)
            balance_after: User's XP balance after this transaction
            description: Human-readable description
            semester_id: Optional semester reference (tournament ID for tournaments)

        Returns:
            Tuple of (XPTransaction, created)
            - created=True: Transaction was created
            - created=False: Transaction already existed (idempotent return)

        Raises:
            ValueError: If business rules are violated
            IntegrityError: If database constraints are violated
        """
        # Validate business rules
        if amount <= 0:
            raise ValueError(f"XP amount must be positive, got {amount}")

        if balance_after < 0:
            raise ValueError(f"Balance cannot be negative, got {balance_after}")

        # Check for existing transaction (idempotency based on unique constraint)
        # Constraint: (user_id, semester_id, transaction_type)
        existing = self.db.query(XPTransaction).filter(
            XPTransaction.user_id == user_id,
            XPTransaction.semester_id == semester_id,
            XPTransaction.transaction_type == transaction_type
        ).first()

        if existing:
            logger.info(
                f"🔒 IDEMPOTENT RETURN: XP transaction already exists "
                f"(id={existing.id}, user={user_id}, semester={semester_id}, type={transaction_type}). "
                f"Returning existing transaction."
            )
            return (existing, False)

        # Create new transaction
        transaction = XPTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=balance_after,
            description=description,
            semester_id=semester_id,
            created_at=datetime.utcnow()
        )

        try:
            self.db.add(transaction)
            self.db.flush()  # Flush to get ID and check constraints

            logger.info(
                f"✅ XP transaction created: id={transaction.id}, "
                f"user={user_id}, type={transaction_type}, amount={amount}, "
                f"semester={semester_id}"
            )

            return (transaction, True)

        except IntegrityError as e:
            # If unique constraint violation, return existing
            if "uq_xp_transactions_user_semester_type" in str(e):
                self.db.rollback()

                # Fetch the existing transaction
                existing = self.db.query(XPTransaction).filter(
                    XPTransaction.user_id == user_id,
                    XPTransaction.semester_id == semester_id,
                    XPTransaction.transaction_type == transaction_type
                ).first()

                if existing:
                    logger.warning(
                        f"🔒 RACE CONDITION: XP transaction was created by another request. "
                        f"Returning existing transaction (id={existing.id}, user={user_id}, "
                        f"semester={semester_id}, type={transaction_type})."
                    )
                    return (existing, False)
                else:
                    logger.error(
                        f"❌ CRITICAL: IntegrityError on unique constraint but transaction not found! "
                        f"user={user_id}, semester={semester_id}, type={transaction_type}"
                    )
                    raise ValueError(
                        f"XP transaction failed due to race condition: "
                        f"user={user_id}, semester={semester_id}, type={transaction_type}"
                    ) from e
            else:
                # Other integrity error - re-raise
                logger.error(f"❌ IntegrityError creating XP transaction: {e}")
                raise

    def get_user_balance(self, user_id: int) -> int:
        """
        Get user's current XP balance.

        Args:
            user_id: User ID

        Returns:
            Current XP balance (or 0 if no transactions)
        """
        latest_transaction = self.db.query(XPTransaction).filter(
            XPTransaction.user_id == user_id
        ).order_by(XPTransaction.created_at.desc()).first()

        if latest_transaction:
            return latest_transaction.balance_after
        return 0

    def get_transaction_history(
        self,
        user_id: int,
        limit: Optional[int] = None,
        semester_id: Optional[int] = None
    ) -> list[XPTransaction]:
        """
        Get user's XP transaction history.

        Args:
            user_id: User ID
            limit: Optional limit on number of results
            semester_id: Optional filter by semester

        Returns:
            List of XP transactions (newest first)
        """
        query = self.db.query(XPTransaction).filter(
            XPTransaction.user_id == user_id
        )

        if semester_id is not None:
            query = query.filter(XPTransaction.semester_id == semester_id)

        query = query.order_by(XPTransaction.created_at.desc())

        if limit:
            query = query.limit(limit)

        return query.all()
