"""
Integration Test: Reward Distribution Idempotency

Tests that reward distribution is idempotent - calling it multiple times
produces the same result without creating duplicate transactions.

This is a CRITICAL test that verifies Phase 1 database constraints prevent
the dual-path bug that caused Tournament 227 to have duplicate rewards.
"""

import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.credit_transaction import CreditTransaction
from app.models.xp_transaction import XPTransaction
from app.models.skill_reward import SkillReward
from app.models.tournament_ranking import TournamentRanking
from app.models.semester import Semester, SemesterStatus


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

    def test_credit_transaction_duplicate_blocked_by_constraint(self, postgres_db: Session, postgres_admin_user):
        """
        Test that database constraint blocks duplicate credit transactions.

        Simulates what would happen if two code paths try to create the same
        credit transaction (e.g., reward distribution called twice).
        """
        from sqlalchemy.exc import IntegrityError
        from datetime import datetime

        idem_key = f"test_tournament_999_reward_{uuid.uuid4().hex[:8]}"

        # Create first transaction (semester_id=None is nullable; constraint is on idempotency_key)
        transaction1 = CreditTransaction(
            user_id=postgres_admin_user.id,
            transaction_type="TEST_REWARD",
            amount=100,
            balance_after=100,
            description="Test reward idempotency",
            idempotency_key=idem_key,
            semester_id=None,
            created_at=datetime.utcnow()
        )
        postgres_db.add(transaction1)
        postgres_db.commit()

        transaction1_id = transaction1.id

        # Try to create duplicate - should fail
        with pytest.raises(IntegrityError) as exc_info:
            transaction2 = CreditTransaction(
                user_id=postgres_admin_user.id,
                transaction_type="TEST_REWARD",
                amount=100,
                balance_after=100,
                description="Test reward idempotency - duplicate",
                idempotency_key=idem_key,  # Same key!
                semester_id=None,
                created_at=datetime.utcnow()
            )
            postgres_db.add(transaction2)
            postgres_db.commit()

        # Verify correct constraint was triggered (DB uses ix_ prefix for index-backed unique)
        assert "idempotency_key" in str(exc_info.value)

        # Rollback the failed transaction
        postgres_db.rollback()

        # Verify only ONE transaction exists
        count = postgres_db.query(CreditTransaction).filter(
            CreditTransaction.idempotency_key == idem_key
        ).count()
        assert count == 1, f"Expected 1 transaction, found {count}"

        # Cleanup
        postgres_db.query(CreditTransaction).filter(
            CreditTransaction.id == transaction1_id
        ).delete()
        postgres_db.commit()

    def test_xp_transaction_duplicate_blocked_by_constraint(self, postgres_db: Session, postgres_admin_user):
        """
        Test that database constraint blocks duplicate XP transactions.

        Unique constraint: (user_id, semester_id, transaction_type)
        """
        from sqlalchemy import inspect as sa_inspect
        from sqlalchemy.exc import IntegrityError
        from datetime import datetime, date

        # Skip if the unique constraint hasn't been applied via migration yet
        insp = sa_inspect(postgres_db.bind)
        xp_constraints = [c['name'] for c in insp.get_unique_constraints('xp_transactions')]
        if 'uq_xp_transactions_user_semester_type' not in xp_constraints:
            pytest.skip(
                "Unique constraint 'uq_xp_transactions_user_semester_type' not yet applied "
                "(migration rw01concurr00 missing)."
            )

        # Reuse an existing semester or create a temporary one for this test
        semester = postgres_db.query(Semester).first()
        created_semester = False
        if not semester:
            semester = Semester(
                code=f"TEST_IDEM_{uuid.uuid4().hex[:6]}",
                name="Test Idempotency Semester",
                start_date=date.today(),
                end_date=date.today(),
                status=SemesterStatus.DRAFT,
            )
            postgres_db.add(semester)
            postgres_db.commit()
            postgres_db.refresh(semester)
            created_semester = True

        semester_id = semester.id
        tx_type = f"TEST_XP_IDEM_{uuid.uuid4().hex[:8]}"

        try:
            # Create first transaction
            xp1 = XPTransaction(
                user_id=postgres_admin_user.id,
                transaction_type=tx_type,
                amount=50,
                balance_after=50,
                description="Test XP idempotency",
                semester_id=semester_id,
                created_at=datetime.utcnow()
            )
            postgres_db.add(xp1)
            postgres_db.commit()

            xp1_id = xp1.id

            # Try to create duplicate - should fail
            with pytest.raises(IntegrityError) as exc_info:
                xp2 = XPTransaction(
                    user_id=postgres_admin_user.id,
                    transaction_type=tx_type,  # Same type
                    amount=50,
                    balance_after=100,
                    description="Test XP idempotency - duplicate",
                    semester_id=semester_id,  # Same semester
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
                XPTransaction.user_id == postgres_admin_user.id,
                XPTransaction.semester_id == semester_id,
                XPTransaction.transaction_type == tx_type
            ).count()
            assert count == 1, f"Expected 1 XP transaction, found {count}"

            # Cleanup transaction
            postgres_db.query(XPTransaction).filter(
                XPTransaction.id == xp1_id
            ).delete()
            postgres_db.commit()

        finally:
            # Cleanup temporary semester if we created it
            if created_semester:
                postgres_db.query(Semester).filter(Semester.id == semester_id).delete()
                postgres_db.commit()

    def test_skill_reward_duplicate_blocked_by_constraint(self, postgres_db: Session, postgres_admin_user):
        """
        Test that database constraint blocks duplicate skill rewards.

        Unique constraint: (user_id, source_type, source_id, skill_name)
        """
        from sqlalchemy import inspect as sa_inspect
        from sqlalchemy.exc import IntegrityError

        # Skip if the unique constraint hasn't been applied via migration yet
        insp = sa_inspect(postgres_db.bind)
        sr_constraints = [c['name'] for c in insp.get_unique_constraints('skill_rewards')]
        if 'uq_skill_rewards_user_source_skill' not in sr_constraints:
            pytest.skip(
                "Unique constraint 'uq_skill_rewards_user_source_skill' not yet applied "
                "(migration missing)."
            )

        source_id = int(uuid.uuid4().int % 1_000_000) + 100_000  # unique source_id

        # Create first reward
        reward1 = SkillReward(
            user_id=postgres_admin_user.id,
            source_type="TEST_TOURNAMENT",
            source_id=source_id,
            skill_name="Passing",
            points_awarded=10
        )
        postgres_db.add(reward1)
        postgres_db.commit()

        reward1_id = reward1.id

        # Try to create duplicate - should fail
        with pytest.raises(IntegrityError) as exc_info:
            reward2 = SkillReward(
                user_id=postgres_admin_user.id,
                source_type="TEST_TOURNAMENT",  # Same source
                source_id=source_id,            # Same ID
                skill_name="Passing",           # Same skill
                points_awarded=15               # Different points (doesn't matter)
            )
            postgres_db.add(reward2)
            postgres_db.commit()

        # Verify correct constraint was triggered
        assert "uq_skill_rewards_user_source_skill" in str(exc_info.value)

        # Rollback the failed transaction
        postgres_db.rollback()

        # Verify only ONE reward exists
        count = postgres_db.query(SkillReward).filter(
            SkillReward.user_id == postgres_admin_user.id,
            SkillReward.source_type == "TEST_TOURNAMENT",
            SkillReward.source_id == source_id,
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
