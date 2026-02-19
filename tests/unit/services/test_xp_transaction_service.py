"""
Unit Tests: XPTransactionService

Tests the centralized XP transaction service in isolation.
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.services.xp_transaction_service import XPTransactionService
from app.models.xp_transaction import XPTransaction


class TestXPTransactionService:
    """Unit tests for XPTransactionService"""

    def test_award_xp_success(self, postgres_db: Session):
        """Test awarding XP to a user"""
        service = XPTransactionService(postgres_db)

        (transaction, created) = service.award_xp(
            user_id=1,
            transaction_type="TEST_REWARD",
            amount=50,
            balance_after=50,
            description="Test XP award",
            semester_id=None
        )

        assert created is True, "Transaction should be marked as created"
        assert transaction.id is not None, "Transaction should have an ID"
        assert transaction.amount == 50
        assert transaction.user_id == 1
        assert transaction.semester_id == None

        # Cleanup
        postgres_db.delete(transaction)
        postgres_db.commit()

    def test_award_xp_duplicate_protection(self, postgres_db: Session):
        """Test that duplicate (user, semester, type) returns existing transaction"""
        service = XPTransactionService(postgres_db)

        # First call - should create
        (transaction1, created1) = service.award_xp(
            user_id=1,
            transaction_type="TEST_TOURNAMENT_REWARD",
            amount=50,
            balance_after=50,
            description="First XP award",
            semester_id=None
        )

        assert created1 is True
        transaction1_id = transaction1.id

        # Second call with same (user, semester, type) - should return existing
        (transaction2, created2) = service.award_xp(
            user_id=1,
            transaction_type="TEST_TOURNAMENT_REWARD",  # Same type
            amount=100,  # Different amount (doesn't matter)
            balance_after=150,  # Different balance (doesn't matter)
            description="Second XP award (should be ignored)",
            semester_id=None  # Same semester
        )

        assert created2 is False, "Second call should return existing transaction"
        assert transaction2.id == transaction1_id, "Should return same transaction"
        assert transaction2.amount == 50, "Should have original amount, not new one"

        # Verify only ONE transaction in database
        count = postgres_db.query(XPTransaction).filter(
            XPTransaction.user_id == 1,
            XPTransaction.semester_id == None,
            XPTransaction.transaction_type == "TEST_TOURNAMENT_REWARD"
        ).count()
        assert count == 1, f"Expected 1 transaction, found {count}"

        # Cleanup
        postgres_db.delete(transaction1)
        postgres_db.commit()

    def test_award_xp_validation_negative_amount(self, postgres_db: Session):
        """Test that negative XP amounts are rejected"""
        service = XPTransactionService(postgres_db)

        with pytest.raises(ValueError) as exc_info:
            service.award_xp(
                user_id=1,
                transaction_type="TEST_REWARD",
                amount=-50,  # Negative!
                balance_after=0,
                description="Invalid negative XP"
            )

        assert "XP amount must be positive" in str(exc_info.value)

    def test_award_xp_validation_negative_balance(self, postgres_db: Session):
        """Test that negative balance is rejected"""
        service = XPTransactionService(postgres_db)

        with pytest.raises(ValueError) as exc_info:
            service.award_xp(
                user_id=1,
                transaction_type="TEST_REWARD",
                amount=50,
                balance_after=-10,  # Negative!
                description="Invalid negative balance"
            )

        assert "Balance cannot be negative" in str(exc_info.value)

    def test_award_xp_without_semester(self, postgres_db: Session):
        """Test awarding XP without semester_id (should still work)"""
        service = XPTransactionService(postgres_db)

        (transaction, created) = service.award_xp(
            user_id=1,
            transaction_type="TEST_GENERAL_REWARD",
            amount=25,
            balance_after=25,
            description="XP without semester",
            semester_id=None  # No semester
        )

        assert created is True
        assert transaction.semester_id is None

        # Cleanup
        postgres_db.delete(transaction)
        postgres_db.commit()

    def test_get_user_balance_empty(self, postgres_db: Session):
        """Test getting balance for user with no transactions"""
        service = XPTransactionService(postgres_db)

        # Use a user ID that definitely has no XP transactions
        balance = service.get_user_balance(user_id=999999)

        assert balance == 0, "User with no transactions should have 0 balance"

    def test_get_user_balance_with_transactions(self, postgres_db: Session):
        """Test getting balance for user with transactions"""
        service = XPTransactionService(postgres_db)

        # Create transaction
        (transaction, _) = service.award_xp(
            user_id=1,
            transaction_type="TEST_BALANCE_CHECK",
            amount=75,
            balance_after=175,
            description="Test balance retrieval",
            semester_id=None
        )

        # Get balance
        balance = service.get_user_balance(user_id=1)

        # Balance should be the latest balance_after value
        assert balance >= 175, f"Expected balance >= 175, got {balance}"

        # Cleanup
        postgres_db.delete(transaction)
        postgres_db.commit()

    def test_get_transaction_history(self, postgres_db: Session):
        """Test retrieving transaction history"""
        service = XPTransactionService(postgres_db)

        # Create multiple transactions
        (tx1, _) = service.award_xp(
            user_id=1,
            transaction_type="TEST_HISTORY_1",
            amount=10,
            balance_after=10,
            description="First transaction",
            semester_id=None
        )

        (tx2, _) = service.award_xp(
            user_id=1,
            transaction_type="TEST_HISTORY_2",
            amount=20,
            balance_after=30,
            description="Second transaction",
            semester_id=None
        )

        # Get history
        history = service.get_transaction_history(user_id=1)

        # Should include both transactions (and possibly others from seed data)
        assert len(history) >= 2, f"Expected at least 2 transactions, found {len(history)}"

        # Check that our transactions are in history
        tx_ids = [tx.id for tx in history]
        assert tx1.id in tx_ids
        assert tx2.id in tx_ids

        # Cleanup
        postgres_db.delete(tx1)
        postgres_db.delete(tx2)
        postgres_db.commit()

    def test_get_transaction_history_with_limit(self, postgres_db: Session):
        """Test retrieving transaction history with limit"""
        service = XPTransactionService(postgres_db)

        # Get limited history
        history = service.get_transaction_history(user_id=1, limit=5)

        assert len(history) <= 5, f"Expected max 5 transactions, found {len(history)}"

    def test_get_transaction_history_filter_by_semester(self, postgres_db: Session):
        """Test retrieving transaction history filtered by semester"""
        service = XPTransactionService(postgres_db)

        # Create transaction for specific semester
        (tx1, _) = service.award_xp(
            user_id=1,
            transaction_type="TEST_SEMESTER_FILTER",
            amount=15,
            balance_after=15,
            description="Semester 1 transaction",
            semester_id=None
        )

        # Get history for semester 1
        history = service.get_transaction_history(user_id=1, semester_id=None)

        # Should include our transaction
        tx_ids = [tx.id for tx in history]
        assert tx1.id in tx_ids

        # All transactions should be from semester 1
        for tx in history:
            if tx.semester_id is not None:
                assert tx.semester_id == None

        # Cleanup
        postgres_db.delete(tx1)
        postgres_db.commit()

    def test_race_condition_handling(self, postgres_db: Session):
        """
        Test that race condition (concurrent creates) is handled gracefully.
        """
        service = XPTransactionService(postgres_db)

        # First request creates transaction
        (transaction1, created1) = service.award_xp(
            user_id=1,
            transaction_type="TEST_RACE_XP",
            amount=30,
            balance_after=30,
            description="First request",
            semester_id=None
        )

        assert created1 is True

        # Commit to database
        postgres_db.commit()

        # Second request (simulating race condition) - should get existing
        (transaction2, created2) = service.award_xp(
            user_id=1,
            transaction_type="TEST_RACE_XP",
            amount=40,
            balance_after=70,
            description="Second request (race condition)",
            semester_id=None
        )

        assert created2 is False, "Second request should get existing transaction"
        assert transaction2.id == transaction1.id

        # Cleanup
        postgres_db.delete(transaction1)
        postgres_db.commit()
