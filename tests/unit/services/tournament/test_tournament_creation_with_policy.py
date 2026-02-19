"""
Unit tests for tournament creation with reward policy snapshots
"""
import pytest
from datetime import date

from app.services.tournament.core import create_tournament_semester
from app.services.tournament.reward_policy_loader import RewardPolicyError
from app.models.specialization import SpecializationType
from app.models.semester import Semester


class TestTournamentCreationWithPolicy:
    """Test tournament creation with reward policy snapshots"""

    def test_create_tournament_with_default_policy(self, test_db):
        """Create tournament with default reward policy"""
        tournament = create_tournament_semester(
            db=test_db,
            tournament_date=date(2026, 2, 15),
            name="Test Tournament",
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER,
            reward_policy_name="default"
        )

        assert tournament is not None
        assert tournament.reward_policy_name == "default"
        assert tournament.reward_policy_snapshot is not None
        assert "placement_rewards" in tournament.reward_policy_snapshot
        assert "participation_rewards" in tournament.reward_policy_snapshot

    def test_create_tournament_policy_defaults_to_default(self, test_db):
        """Tournament creation defaults to 'default' policy when not specified"""
        tournament = create_tournament_semester(
            db=test_db,
            tournament_date=date(2026, 2, 15),
            name="Test Tournament",
            specialization_type=SpecializationType.LFA_COACH
        )

        assert tournament.reward_policy_name == "default"
        assert tournament.reward_policy_snapshot is not None

    def test_policy_snapshot_is_immutable_copy(self, test_db):
        """Policy snapshot is a copy, not a reference"""
        tournament = create_tournament_semester(
            db=test_db,
            tournament_date=date(2026, 2, 15),
            name="Test Tournament",
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER
        )

        # Snapshot should be a dict (JSON), not a file reference
        assert isinstance(tournament.reward_policy_snapshot, dict)
        assert tournament.reward_policy_snapshot["policy_name"] == "default"
        assert tournament.reward_policy_snapshot["version"] == "1.0.0"

    def test_policy_snapshot_contains_exact_values(self, test_db):
        """Policy snapshot contains exact user-specified reward values"""
        tournament = create_tournament_semester(
            db=test_db,
            tournament_date=date(2026, 2, 15),
            name="Test Tournament",
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER
        )

        snapshot = tournament.reward_policy_snapshot
        placement = snapshot["placement_rewards"]

        # Verify exact values from user spec
        assert placement["1ST"]["xp"] == 500
        assert placement["1ST"]["credits"] == 100

        assert placement["2ND"]["xp"] == 300
        assert placement["2ND"]["credits"] == 50

        assert placement["3RD"]["xp"] == 200
        assert placement["3RD"]["credits"] == 25

        assert placement["PARTICIPANT"]["xp"] == 50
        assert placement["PARTICIPANT"]["credits"] == 0

        participation = snapshot["participation_rewards"]
        assert participation["session_attendance"]["xp"] == 10
        assert participation["session_attendance"]["credits"] == 0

    def test_policy_snapshot_applies_to_all_specializations(self, test_db):
        """Same policy applies to all 4 specializations"""
        specializations = [
            SpecializationType.LFA_FOOTBALL_PLAYER,
            SpecializationType.LFA_COACH,
            SpecializationType.INTERNSHIP,
            SpecializationType.GANCUJU_PLAYER
        ]

        tournaments = []
        for spec in specializations:
            tournament = create_tournament_semester(
                db=test_db,
                tournament_date=date(2026, 2, 15 + len(tournaments)),  # Different dates
                name=f"Test Tournament {spec.value}",
                specialization_type=spec
            )
            tournaments.append(tournament)

        # All tournaments should have identical policy snapshots
        first_snapshot = tournaments[0].reward_policy_snapshot
        for tournament in tournaments[1:]:
            assert tournament.reward_policy_snapshot == first_snapshot

    def test_create_tournament_with_nonexistent_policy_fails(self, test_db):
        """Creating tournament with nonexistent policy raises error"""
        with pytest.raises(RewardPolicyError, match="Policy file not found"):
            create_tournament_semester(
                db=test_db,
                tournament_date=date(2026, 2, 15),
                name="Test Tournament",
                specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER,
                reward_policy_name="nonexistent_policy"
            )

    def test_policy_snapshot_persisted_in_database(self, test_db):
        """Policy snapshot is correctly persisted in JSONB column"""
        tournament = create_tournament_semester(
            db=test_db,
            tournament_date=date(2026, 2, 15),
            name="Test Tournament",
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER
        )

        # Commit and refresh to ensure DB persistence
        test_db.commit()
        test_db.refresh(tournament)

        # Re-query from DB to verify persistence
        retrieved = test_db.query(Semester).filter(Semester.id == tournament.id).first()
        assert retrieved.reward_policy_snapshot is not None
        assert retrieved.reward_policy_snapshot["placement_rewards"]["1ST"]["xp"] == 500

    def test_multiple_tournaments_have_independent_snapshots(self, test_db):
        """Each tournament has its own independent policy snapshot"""
        tournament1 = create_tournament_semester(
            db=test_db,
            tournament_date=date(2026, 2, 15),
            name="Tournament 1",
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER
        )

        tournament2 = create_tournament_semester(
            db=test_db,
            tournament_date=date(2026, 2, 16),
            name="Tournament 2",
            specialization_type=SpecializationType.LFA_COACH
        )

        # Snapshots should be equal in content but independent objects
        assert tournament1.reward_policy_snapshot == tournament2.reward_policy_snapshot
        assert tournament1.reward_policy_snapshot is not tournament2.reward_policy_snapshot

    def test_policy_snapshot_includes_all_required_fields(self, test_db):
        """Policy snapshot includes all required fields from policy file"""
        tournament = create_tournament_semester(
            db=test_db,
            tournament_date=date(2026, 2, 15),
            name="Test Tournament",
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER
        )

        snapshot = tournament.reward_policy_snapshot

        # Required top-level fields
        assert "policy_name" in snapshot
        assert "version" in snapshot
        assert "placement_rewards" in snapshot
        assert "participation_rewards" in snapshot
        assert "specializations" in snapshot
        assert "applies_to_all_tournament_types" in snapshot

        # Required placement rewards
        assert "1ST" in snapshot["placement_rewards"]
        assert "2ND" in snapshot["placement_rewards"]
        assert "3RD" in snapshot["placement_rewards"]
        assert "PARTICIPANT" in snapshot["placement_rewards"]

        # Required participation rewards
        assert "session_attendance" in snapshot["participation_rewards"]

    def test_policy_name_stored_separately(self, test_db):
        """Policy name is stored separately from snapshot"""
        tournament = create_tournament_semester(
            db=test_db,
            tournament_date=date(2026, 2, 15),
            name="Test Tournament",
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER,
            reward_policy_name="default"
        )

        # Both fields should be populated
        assert tournament.reward_policy_name == "default"
        assert tournament.reward_policy_snapshot["policy_name"] == "default"

    def test_no_extra_reward_features_in_snapshot(self, test_db):
        """Policy snapshot does NOT contain excluded features"""
        tournament = create_tournament_semester(
            db=test_db,
            tournament_date=date(2026, 2, 15),
            name="Test Tournament",
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER
        )

        snapshot = tournament.reward_policy_snapshot
        placement = snapshot["placement_rewards"]

        # Verify NO TOP_10 reward
        assert "TOP_10" not in placement

        # Verify NO multipliers in any placement reward
        for position, reward in placement.items():
            assert "multiplier" not in reward
            assert "modifier" not in reward

        # Verify NO penalties
        assert "penalties" not in snapshot
        assert "late_arrival_penalty" not in snapshot
        assert "absence_penalty" not in snapshot

        # Verify NO thresholds
        assert "thresholds" not in snapshot
