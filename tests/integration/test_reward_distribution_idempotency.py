"""
Integration Test: Reward Distribution Idempotency

Tests that reward distribution is idempotent - calling it multiple times
produces the same result without creating duplicate transactions.

This is a CRITICAL test that verifies Phase 1 database constraints prevent
the dual-path bug that caused Tournament 227 to have duplicate rewards.
"""

import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.credit_transaction import CreditTransaction
from app.models.xp_transaction import XPTransaction
from app.models.skill_reward import SkillReward
from app.models.tournament_ranking import TournamentRanking


class TestRewardDistributionIdempotency:
    """Test reward distribution idempotency at API level"""

    def test_distribute_rewards_twice_same_results(self, client: TestClient, postgres_db: Session):
        """
        CRITICAL TEST: Calling /tournaments/{id}/rewards/distribute twice should:
        1. First call: Create rewards (credits, XP, skills)
        2. Second call: Return same results without creating duplicates
        3. Database should have EXACT same number of transactions
        """
        # This test requires a tournament to exist with rankings
        # For now, we'll test the database constraints directly
        # TODO: Set up full tournament workflow when test fixtures are ready
        pass

    def test_credit_transaction_duplicate_blocked_by_constraint(self, postgres_db: Session):
        """
        Test that database constraint blocks duplicate credit transactions.

        Simulates what would happen if two code paths try to create the same
        credit transaction (e.g., reward distribution called twice).
        """
        from sqlalchemy.exc import IntegrityError
        from datetime import datetime

        # Create first transaction
        transaction1 = CreditTransaction(
            user_id=2,
            transaction_type="TEST_REWARD",
            amount=100,
            balance_after=100,
            description="Test reward idempotency",
            idempotency_key="test_tournament_999_reward_2",
            semester_id=1,
            created_at=datetime.utcnow()
        )
        postgres_db.add(transaction1)
        postgres_db.commit()

        transaction1_id = transaction1.id

        # Try to create duplicate - should fail
        with pytest.raises(IntegrityError) as exc_info:
            transaction2 = CreditTransaction(
                user_id=2,
                transaction_type="TEST_REWARD",
                amount=100,
                balance_after=100,
                description="Test reward idempotency - duplicate",
                idempotency_key="test_tournament_999_reward_2",  # Same key!
                semester_id=1,
                created_at=datetime.utcnow()
            )
            postgres_db.add(transaction2)
            postgres_db.commit()

        # Verify correct constraint was triggered
        assert "uq_credit_transactions_idempotency_key" in str(exc_info.value)

        # Rollback the failed transaction
        postgres_db.rollback()

        # Verify only ONE transaction exists
        count = postgres_db.query(CreditTransaction).filter(
            CreditTransaction.idempotency_key == "test_tournament_999_reward_2"
        ).count()
        assert count == 1, f"Expected 1 transaction, found {count}"

        # Cleanup
        postgres_db.query(CreditTransaction).filter(
            CreditTransaction.id == transaction1_id
        ).delete()
        postgres_db.commit()

    def test_xp_transaction_duplicate_blocked_by_constraint(self, postgres_db: Session):
        """
        Test that database constraint blocks duplicate XP transactions.

        Unique constraint: (user_id, semester_id, transaction_type)
        """
        from sqlalchemy.exc import IntegrityError
        from datetime import datetime

        # Create first transaction
        xp1 = XPTransaction(
            user_id=2,
            transaction_type="TEST_TOURNAMENT_REWARD",
            amount=50,
            balance_after=50,
            description="Test XP idempotency",
            semester_id=1,
            created_at=datetime.utcnow()
        )
        postgres_db.add(xp1)
        postgres_db.commit()

        xp1_id = xp1.id

        # Try to create duplicate - should fail
        with pytest.raises(IntegrityError) as exc_info:
            xp2 = XPTransaction(
                user_id=2,
                transaction_type="TEST_TOURNAMENT_REWARD",  # Same type
                amount=50,
                balance_after=100,
                description="Test XP idempotency - duplicate",
                semester_id=1,  # Same semester
                created_at=datetime.utcnow()
            )
            postgres_db.add(xp2)
            postgres_db.commit()

        # Verify correct constraint was triggered
        assert "uq_xp_transactions_user_semester_type" in str(exc_info.value)

        # Rollback the failed transaction
        postgres_db.rollback()

        # Verify only ONE transaction exists
        count = postgres_db.query(XPTransaction).filter(
            XPTransaction.user_id == 2,
            XPTransaction.semester_id == 1,
            XPTransaction.transaction_type == "TEST_TOURNAMENT_REWARD"
        ).count()
        assert count == 1, f"Expected 1 XP transaction, found {count}"

        # Cleanup
        postgres_db.query(XPTransaction).filter(
            XPTransaction.id == xp1_id
        ).delete()
        postgres_db.commit()

    def test_skill_reward_duplicate_blocked_by_constraint(self, postgres_db: Session):
        """
        Test that database constraint blocks duplicate skill rewards.

        Unique constraint: (user_id, source_type, source_id, skill_name)
        """
        from sqlalchemy.exc import IntegrityError
        from datetime import datetime

        # Create first reward
        reward1 = SkillReward(
            user_id=2,
            source_type="TEST_TOURNAMENT",
            source_id=999,
            skill_name="Passing",
            points_awarded=10
        )
        postgres_db.add(reward1)
        postgres_db.commit()

        reward1_id = reward1.id

        # Try to create duplicate - should fail
        with pytest.raises(IntegrityError) as exc_info:
            reward2 = SkillReward(
                user_id=2,
                source_type="TEST_TOURNAMENT",  # Same source
                source_id=999,  # Same ID
                skill_name="Passing",  # Same skill
                points_awarded=15  # Different points (doesn't matter)
            )
            postgres_db.add(reward2)
            postgres_db.commit()

        # Verify correct constraint was triggered
        assert "uq_skill_rewards_user_source_skill" in str(exc_info.value)

        # Rollback the failed transaction
        postgres_db.rollback()

        # Verify only ONE reward exists
        count = postgres_db.query(SkillReward).filter(
            SkillReward.user_id == 2,
            SkillReward.source_type == "TEST_TOURNAMENT",
            SkillReward.source_id == 999,
            SkillReward.skill_name == "Passing"
        ).count()
        assert count == 1, f"Expected 1 skill reward, found {count}"

        # Cleanup
        postgres_db.query(SkillReward).filter(
            SkillReward.id == reward1_id
        ).delete()
        postgres_db.commit()

    def test_business_invariant_ranking_count_equals_player_count(self, postgres_db: Session):
        """
        Business Invariant #1: ranking_count = player_count

        This was violated in Tournament 227 (16 rankings for 8 players).
        Verify that unique constraint prevents this.
        """
        # Get a tournament with rankings
        tournament_with_rankings = postgres_db.query(TournamentRanking).first()

        if not tournament_with_rankings:
            pytest.skip("No tournaments with rankings found")

        tournament_id = tournament_with_rankings.tournament_id

        # Count rankings for this tournament
        ranking_count = postgres_db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament_id
        ).count()

        # Count unique users in rankings
        unique_users = postgres_db.query(TournamentRanking.user_id).filter(
            TournamentRanking.tournament_id == tournament_id
        ).distinct().count()

        # INVARIANT: Each user should have exactly ONE ranking
        assert ranking_count == unique_users, (
            f"INVARIANT VIOLATION: Tournament {tournament_id} has {ranking_count} rankings "
            f"but only {unique_users} unique users. Each user should have EXACTLY one ranking."
        )

    def test_business_invariant_no_duplicate_rewards_same_tournament(self, postgres_db: Session):
        """
        Business Invariant #2: One reward per (user, tournament)

        Verify that a user cannot receive multiple credit/XP/skill rewards
        from the same tournament.
        """
        from sqlalchemy import func

        # Check credit transactions
        credit_duplicates = postgres_db.query(
            CreditTransaction.semester_id,
            CreditTransaction.user_id,
            func.count(CreditTransaction.id).label('count')
        ).filter(
            CreditTransaction.transaction_type == 'TOURNAMENT_REWARD',
            CreditTransaction.semester_id.isnot(None)
        ).group_by(
            CreditTransaction.semester_id,
            CreditTransaction.user_id
        ).having(
            func.count(CreditTransaction.id) > 1
        ).all()

        assert len(credit_duplicates) == 0, (
            f"INVARIANT VIOLATION: Found {len(credit_duplicates)} users with duplicate "
            f"credit rewards from same tournament: {credit_duplicates}"
        )

        # Check XP transactions
        xp_duplicates = postgres_db.query(
            XPTransaction.semester_id,
            XPTransaction.user_id,
            func.count(XPTransaction.id).label('count')
        ).filter(
            XPTransaction.transaction_type == 'TOURNAMENT_REWARD',
            XPTransaction.semester_id.isnot(None)
        ).group_by(
            XPTransaction.semester_id,
            XPTransaction.user_id
        ).having(
            func.count(XPTransaction.id) > 1
        ).all()

        assert len(xp_duplicates) == 0, (
            f"INVARIANT VIOLATION: Found {len(xp_duplicates)} users with duplicate "
            f"XP rewards from same tournament: {xp_duplicates}"
        )

        # Check skill rewards
        skill_duplicates = postgres_db.query(
            SkillReward.source_id,
            SkillReward.user_id,
            SkillReward.skill_name,
            func.count(SkillReward.id).label('count')
        ).filter(
            SkillReward.source_type == 'TOURNAMENT'
        ).group_by(
            SkillReward.source_id,
            SkillReward.user_id,
            SkillReward.skill_name
        ).having(
            func.count(SkillReward.id) > 1
        ).all()

        assert len(skill_duplicates) == 0, (
            f"INVARIANT VIOLATION: Found {len(skill_duplicates)} duplicate skill rewards "
            f"from same tournament: {skill_duplicates}"
        )
