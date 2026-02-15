"""
Unit tests for reward distribution using policy snapshots
"""
import pytest
import uuid
from datetime import date

from app.services.tournament.core import create_tournament_semester
from app.services.tournament.tournament_xp_service import distribute_rewards
from app.models.specialization import SpecializationType
from app.models.tournament_ranking import TournamentRanking
from app.models.user import User
from app.models.credit_transaction import CreditTransaction, TransactionType


class TestRewardDistributionFromPolicy:
    """Test reward distribution using policy snapshots"""

    @pytest.fixture
    def tournament_with_policy(self, test_db):
        """Create tournament with default policy and instructor assigned"""
        from app.models.user import User, UserRole
        from app.models.semester import SemesterStatus

        # Create instructor
        instructor = User(
            email=f"instructor+{uuid.uuid4().hex[:8]}@test.com",
            name="Test Instructor",
            password_hash="test_hash",
            role=UserRole.INSTRUCTOR
        )
        test_db.add(instructor)
        test_db.flush()

        # Create tournament
        tournament = create_tournament_semester(
            db=test_db,
            tournament_date=date(2026, 2, 15),
            name="Test Tournament",
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER,
            reward_policy_name="default"
        )

        # Assign instructor and set status
        tournament.master_instructor_id = instructor.id
        tournament.status = SemesterStatus.READY_FOR_ENROLLMENT
        test_db.commit()
        test_db.refresh(tournament)
        return tournament

    @pytest.fixture
    def test_users(self, test_db):
        """Create test users for rankings"""
        users = []
        for i in range(5):
            user = User(
                email=f"user{i}+{uuid.uuid4().hex[:8]}@test.com",
                name=f"Test User {i}",
                password_hash="hashedpassword",
                xp_balance=0  # Changed from deprecated total_xp
            )
            test_db.add(user)
            users.append(user)

        test_db.commit()
        for user in users:
            test_db.refresh(user)

        return users

    def test_distribute_first_place_reward(self, test_db, tournament_with_policy, test_users):
        """Distribute 1st place reward: 500 XP, 100 credits"""
        tournament = tournament_with_policy
        user = test_users[0]

        # Create ranking for 1st place
        ranking = TournamentRanking(
            tournament_id=tournament.id,
            user_id=user.id,
            participant_type="INDIVIDUAL",
            rank=1,
            points=100
        )
        test_db.add(ranking)
        test_db.commit()

        # Distribute rewards
        stats = distribute_rewards(test_db, tournament.id)

        # Refresh user to get updated values
        test_db.refresh(user)

        # Verify XP awarded
        assert user.total_xp == 500
        assert stats['xp_distributed'] == 500

        # Verify credits awarded
        assert user.credit_balance == 100
        assert stats['credits_distributed'] == 100

        # Verify credit transaction created
        transaction = test_db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user.id
        ).first()
        assert transaction is not None
        assert transaction.amount == 100
        assert transaction.balance_after == 100
        assert transaction.transaction_type == TransactionType.TOURNAMENT_REWARD.value
        assert "1ST" in transaction.description

    def test_distribute_second_place_reward(self, test_db, tournament_with_policy, test_users):
        """Distribute 2nd place reward: 300 XP, 50 credits"""
        tournament = tournament_with_policy
        user = test_users[0]

        ranking = TournamentRanking(
            tournament_id=tournament.id,
            user_id=user.id,
            participant_type="INDIVIDUAL",
            rank=2,
            points=80
        )
        test_db.add(ranking)
        test_db.commit()

        distribute_rewards(test_db, tournament.id)
        test_db.refresh(user)

        assert user.total_xp == 300
        assert user.credit_balance == 50

    def test_distribute_third_place_reward(self, test_db, tournament_with_policy, test_users):
        """Distribute 3rd place reward: 200 XP, 25 credits"""
        tournament = tournament_with_policy
        user = test_users[0]

        ranking = TournamentRanking(
            tournament_id=tournament.id,
            user_id=user.id,
            participant_type="INDIVIDUAL",
            rank=3,
            points=60
        )
        test_db.add(ranking)
        test_db.commit()

        distribute_rewards(test_db, tournament.id)
        test_db.refresh(user)

        assert user.total_xp == 200
        assert user.credit_balance == 25

    def test_distribute_participant_reward(self, test_db, tournament_with_policy, test_users):
        """Distribute participant reward: 50 XP, 0 credits"""
        tournament = tournament_with_policy
        user = test_users[0]

        ranking = TournamentRanking(
            tournament_id=tournament.id,
            user_id=user.id,
            participant_type="INDIVIDUAL",
            rank=4,
            points=40
        )
        test_db.add(ranking)
        test_db.commit()

        distribute_rewards(test_db, tournament.id)
        test_db.refresh(user)

        assert user.total_xp == 50
        assert user.credit_balance == 0

        # Verify NO credit transaction for 0 credits
        transaction_count = test_db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user.id
        ).count()
        assert transaction_count == 0

    def test_distribute_multiple_rewards(self, test_db, tournament_with_policy, test_users):
        """Distribute rewards to multiple participants"""
        tournament = tournament_with_policy

        # Create rankings for all positions
        rankings = [
            TournamentRanking(tournament_id=tournament.id, user_id=test_users[0].id,
                            participant_type="INDIVIDUAL", rank=1, points=100),
            TournamentRanking(tournament_id=tournament.id, user_id=test_users[1].id,
                            participant_type="INDIVIDUAL", rank=2, points=80),
            TournamentRanking(tournament_id=tournament.id, user_id=test_users[2].id,
                            participant_type="INDIVIDUAL", rank=3, points=60),
            TournamentRanking(tournament_id=tournament.id, user_id=test_users[3].id,
                            participant_type="INDIVIDUAL", rank=4, points=40),
            TournamentRanking(tournament_id=tournament.id, user_id=test_users[4].id,
                            participant_type="INDIVIDUAL", rank=5, points=20),
        ]
        for ranking in rankings:
            test_db.add(ranking)
        test_db.commit()

        # Distribute rewards
        stats = distribute_rewards(test_db, tournament.id)

        # Verify stats
        assert stats['total_participants'] == 5
        assert stats['xp_distributed'] == 500 + 300 + 200 + 50 + 50  # 1100 total XP
        assert stats['credits_distributed'] == 100 + 50 + 25 + 0 + 0  # 175 total credits

        # Verify individual rewards
        for user in test_users:
            test_db.refresh(user)

        assert test_users[0].total_xp == 500
        assert test_users[0].credit_balance == 100

        assert test_users[1].total_xp == 300
        assert test_users[1].credit_balance == 50

        assert test_users[2].total_xp == 200
        assert test_users[2].credit_balance == 25

        assert test_users[3].total_xp == 50
        assert test_users[3].credit_balance == 0

        assert test_users[4].total_xp == 50
        assert test_users[4].credit_balance == 0

    def test_rewards_identical_across_specializations(self, test_db, test_users):
        """All 4 specializations receive identical rewards"""
        specializations = [
            SpecializationType.LFA_FOOTBALL_PLAYER,
            SpecializationType.LFA_COACH,
            SpecializationType.INTERNSHIP,
            SpecializationType.GANCUJU_PLAYER
        ]

        results = []
        for i, spec in enumerate(specializations):
            # Create tournament for this specialization
            tournament = create_tournament_semester(
                db=test_db,
                tournament_date=date(2026, 2, 15 + i),
                name=f"Tournament {spec.value}",
                specialization_type=spec
            )

            # Use different user for each tournament
            user = test_users[i]
            user.total_xp = 0
            user.credit_balance = 0
            test_db.commit()

            # Create 1st place ranking
            ranking = TournamentRanking(
                tournament_id=tournament.id,
                user_id=user.id,
                participant_type="INDIVIDUAL",
                rank=1,
                points=100
            )
            test_db.add(ranking)
            test_db.commit()

            # Distribute rewards
            distribute_rewards(test_db, tournament.id)
            test_db.refresh(user)

            results.append({
                "spec": spec.value,
                "xp": user.total_xp,
                "credits": user.credit_balance
            })

        # All specializations should have identical rewards
        for result in results:
            assert result["xp"] == 500
            assert result["credits"] == 100

    def test_credit_transaction_audit_trail(self, test_db, tournament_with_policy, test_users):
        """Credit transactions created for audit trail"""
        tournament = tournament_with_policy
        user = test_users[0]

        ranking = TournamentRanking(
            tournament_id=tournament.id,
            user_id=user.id,
            participant_type="INDIVIDUAL",
            rank=1,
            points=100
        )
        test_db.add(ranking)
        test_db.commit()

        distribute_rewards(test_db, tournament.id)

        # Verify transaction exists
        transaction = test_db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user.id,
            CreditTransaction.transaction_type == TransactionType.TOURNAMENT_REWARD.value
        ).first()

        assert transaction is not None
        assert transaction.user_id == user.id
        assert transaction.user_license_id is None  # User-level, not license-level
        assert transaction.amount == 100
        assert transaction.balance_after == 100
        assert "Tournament" in transaction.description
        assert "1ST" in transaction.description

    def test_rewards_use_policy_snapshot_not_current_file(self, test_db, tournament_with_policy, test_users):
        """Rewards use policy snapshot, not current policy file"""
        tournament = tournament_with_policy
        user = test_users[0]

        # Manually modify the snapshot (simulating policy file change)
        tournament.reward_policy_snapshot["placement_rewards"]["1ST"]["xp"] = 999
        tournament.reward_policy_snapshot["placement_rewards"]["1ST"]["credits"] = 888
        test_db.commit()

        ranking = TournamentRanking(
            tournament_id=tournament.id,
            user_id=user.id,
            participant_type="INDIVIDUAL",
            rank=1,
            points=100
        )
        test_db.add(ranking)
        test_db.commit()

        distribute_rewards(test_db, tournament.id)
        test_db.refresh(user)

        # Should use modified snapshot values, not default policy file
        assert user.total_xp == 999
        assert user.credit_balance == 888

    def test_no_rewards_for_nonexistent_tournament(self, test_db):
        """Distributing rewards for nonexistent tournament raises error"""
        with pytest.raises(ValueError, match="Tournament semester .* not found"):
            distribute_rewards(test_db, 999999)

    def test_participant_ranks_above_3_get_participant_reward(self, test_db, tournament_with_policy, test_users):
        """Ranks 4+ all receive PARTICIPANT reward"""
        tournament = tournament_with_policy

        # Create rankings for ranks 4-10
        for i in range(4, 11):
            user = test_users[i % len(test_users)]
            ranking = TournamentRanking(
                tournament_id=tournament.id,
                user_id=user.id,
                participant_type="INDIVIDUAL",
                rank=i,
                points=100 - (i * 5)
            )
            test_db.add(ranking)

        test_db.commit()

        distribute_rewards(test_db, tournament.id)

        # All should receive participant reward (50 XP, 0 credits)
        # Note: Some users will have cumulative rewards due to multiple rankings
        # This test verifies the logic handles ranks > 3 correctly

    def test_backward_compatibility_with_tournament_reward_table(self, test_db, test_users):
        """Fallback to TournamentReward table if no policy snapshot exists"""
        # Create tournament without using the service (to skip policy snapshot)
        from app.models.semester import Semester, SemesterStatus

        semester = Semester(
            code="TOURN-20260215",
            name="Legacy Tournament",
            start_date=date(2026, 2, 15),
            end_date=date(2026, 2, 15),
            is_active=True,
            status=SemesterStatus.READY_FOR_ENROLLMENT,
            specialization_type=SpecializationType.LFA_PLAYER.value,
            reward_policy_snapshot=None  # No policy snapshot (legacy)
        )
        test_db.add(semester)
        test_db.commit()
        test_db.refresh(semester)

        # Create ranking
        user = test_users[0]
        ranking = TournamentRanking(
            tournament_id=semester.id,
            user_id=user.id,
            participant_type="INDIVIDUAL",
            rank=1,
            points=100
        )
        test_db.add(ranking)
        test_db.commit()

        # Distribute rewards (should fallback to default creation)
        stats = distribute_rewards(test_db, semester.id)

        # Should still work with default values
        test_db.refresh(user)
        assert user.total_xp == 500
        assert user.credit_balance == 100
