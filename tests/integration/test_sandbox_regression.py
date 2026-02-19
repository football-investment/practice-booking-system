"""
Sandbox Tournament Regression Test

This test ensures that the sandbox tournament simulation produces consistent,
deterministic results when given the same seed. This prevents regressions in
the match generation, ranking calculation, and reward distribution logic.

⚠️ IMPORTANT: This test uses a fixed random seed for deterministic results.
If match simulation logic changes, expected values may need updating.
"""

import pytest
from sqlalchemy.orm import Session
from decimal import Decimal

from app.services.sandbox_test_orchestrator import SandboxTestOrchestrator
from app.models.tournament_ranking import TournamentRanking
from app.models.user import User


class TestSandboxRegression:
    """
    Regression tests for sandbox tournament simulation

    These tests verify that:
    1. Same seed produces same results (deterministic)
    2. Rankings are calculated correctly
    3. Match statistics (W-D-L) are consistent
    4. Reward distribution works as expected
    """

    @pytest.fixture
    def orchestrator(self, db: Session):
        """Create sandbox orchestrator instance"""
        return SandboxTestOrchestrator(db)

    def test_deterministic_head_to_head_4_players(self, db: Session, orchestrator: SandboxTestOrchestrator):
        """
        Test that 4-player HEAD_TO_HEAD tournament produces consistent results

        Tournament setup:
        - 4 players (user IDs: 4, 5, 6, 7)
        - HEAD_TO_HEAD format (round-robin)
        - Total matches: 6 (4 × 3 / 2)
        - Random seed: 42
        - Draw probability: 20%
        - Home win probability: 40%

        Expected results (with seed=42):
        These values are FIXED based on seed 42. If match generation logic changes,
        these values will need to be updated by running the test and capturing output.
        """
        # Run tournament with fixed seed
        result = orchestrator.execute_test(
            tournament_type_code="league",
            skills_to_test=["ball_control", "stamina"],
            skill_weights={"ball_control": 2.0, "stamina": 1.5},
            player_count=4,
            user_ids=[4, 5, 6, 7],  # Fixed user IDs
            campus_id=1,
            draw_probability=0.20,
            home_win_probability=0.40,
            random_seed=42  # DETERMINISTIC
        )

        # Verify tournament was created successfully
        assert result["verdict"] in ["WORKING", "NEEDS_TUNING", "NOT_WORKING"]
        assert result["tournament"]["type"] == "LEAGUE"
        assert result["tournament"]["player_count"] == 4

        tournament_id = result["tournament"]["id"]

        # Fetch rankings from database
        rankings = (
            db.query(TournamentRanking, User.name)
            .join(User, TournamentRanking.user_id == User.id)
            .filter(TournamentRanking.tournament_id == tournament_id)
            .order_by(TournamentRanking.rank)
            .all()
        )

        assert len(rankings) == 4, "Should have 4 players in rankings"

        # Extract rankings data
        rankings_data = [
            {
                "rank": r.TournamentRanking.rank,
                "name": r.name,
                "points": int(r.TournamentRanking.points),
                "wins": r.TournamentRanking.wins,
                "draws": r.TournamentRanking.draws,
                "losses": r.TournamentRanking.losses,
                "goals_for": r.TournamentRanking.goals_for,
                "goals_against": r.TournamentRanking.goals_against,
            }
            for r in rankings
        ]

        # EXPECTED VALUES (REGRESSION BASELINE)
        # These are the expected results with seed=42
        # If match generation logic changes, run test and update these values
        expected_baseline = [
            # Rank 1
            {
                "rank": 1,
                "points": 9,  # 3 wins = 9 points
                "wins": 3,
                "draws": 0,
                "losses": 0,
                "matches": 3,
            },
            # Rank 2
            {
                "rank": 2,
                "points": 6,  # 2 wins = 6 points
                "wins": 2,
                "draws": 0,
                "losses": 1,
                "matches": 3,
            },
            # Rank 3
            {
                "rank": 3,
                "points": 3,  # 1 win = 3 points
                "wins": 1,
                "draws": 0,
                "losses": 2,
                "matches": 3,
            },
            # Rank 4
            {
                "rank": 4,
                "points": 0,  # 0 wins = 0 points
                "wins": 0,
                "draws": 0,
                "losses": 3,
                "matches": 3,
            },
        ]

        # Verify each ranking against baseline
        for i, (actual, expected) in enumerate(zip(rankings_data, expected_baseline)):
            assert actual["rank"] == expected["rank"], f"Player {i+1}: rank mismatch"
            assert actual["points"] == expected["points"], f"Player {i+1}: points mismatch"
            assert actual["wins"] == expected["wins"], f"Player {i+1}: wins mismatch"
            assert actual["draws"] == expected["draws"], f"Player {i+1}: draws mismatch"
            assert actual["losses"] == expected["losses"], f"Player {i+1}: losses mismatch"

            # Verify match count
            matches_played = actual["wins"] + actual["draws"] + actual["losses"]
            assert matches_played == expected["matches"], f"Player {i+1}: should play {expected['matches']} matches"

        # Verify total matches (each player plays 3, total 6 unique matches)
        total_wins = sum(r["wins"] for r in rankings_data)
        total_draws = sum(r["draws"] for r in rankings_data)
        total_losses = sum(r["losses"] for r in rankings_data)

        assert total_wins == total_losses, "Total wins should equal total losses"
        assert total_draws % 2 == 0, "Total draws should be even (2 per draw match)"

        # Calculate total matches from stats
        total_matches = total_wins + (total_draws // 2)
        expected_total_matches = 6  # 4 players: 4 × 3 / 2 = 6 matches
        assert total_matches == expected_total_matches, f"Should have {expected_total_matches} total matches"

        print(f"\n✅ Regression test passed with seed=42")
        print(f"   Tournament ID: {tournament_id}")
        print(f"   Total matches: {total_matches}")
        print(f"   Leaderboard verified against baseline")

    def test_deterministic_repeatability(self, db: Session, orchestrator: SandboxTestOrchestrator):
        """
        Test that running the same test twice with same seed produces identical results
        """
        # Run tournament twice with same seed
        result1 = orchestrator.execute_test(
            tournament_type_code="league",
            skills_to_test=["ball_control"],
            player_count=4,
            user_ids=[4, 5, 6, 7],
            campus_id=1,
            random_seed=12345
        )

        tournament_id_1 = result1["tournament"]["id"]

        # Fetch rankings from first tournament
        rankings1 = (
            db.query(TournamentRanking)
            .filter(TournamentRanking.tournament_id == tournament_id_1)
            .order_by(TournamentRanking.rank)
            .all()
        )

        # Run second tournament with same seed
        result2 = orchestrator.execute_test(
            tournament_type_code="league",
            skills_to_test=["ball_control"],
            player_count=4,
            user_ids=[4, 5, 6, 7],
            campus_id=1,
            random_seed=12345  # SAME SEED
        )

        tournament_id_2 = result2["tournament"]["id"]

        # Fetch rankings from second tournament
        rankings2 = (
            db.query(TournamentRanking)
            .filter(TournamentRanking.tournament_id == tournament_id_2)
            .order_by(TournamentRanking.rank)
            .all()
        )

        # Verify both have same number of players
        assert len(rankings1) == len(rankings2), "Both tournaments should have same player count"

        # Verify rankings are identical
        for r1, r2 in zip(rankings1, rankings2):
            # User IDs should match (same order)
            assert r1.user_id == r2.user_id, f"User IDs should match at same rank"

            # Statistics should be identical
            assert r1.points == r2.points, f"Points should match for user {r1.user_id}"
            assert r1.wins == r2.wins, f"Wins should match for user {r1.user_id}"
            assert r1.draws == r2.draws, f"Draws should match for user {r1.user_id}"
            assert r1.losses == r2.losses, f"Losses should match for user {r1.user_id}"
            assert r1.goals_for == r2.goals_for, f"Goals for should match for user {r1.user_id}"
            assert r1.goals_against == r2.goals_against, f"Goals against should match for user {r1.user_id}"

        print(f"\n✅ Repeatability test passed")
        print(f"   Tournament 1 ID: {tournament_id_1}")
        print(f"   Tournament 2 ID: {tournament_id_2}")
        print(f"   Both produced identical rankings with seed=12345")

    def test_different_seeds_produce_different_results(self, db: Session, orchestrator: SandboxTestOrchestrator):
        """
        Test that different seeds produce different results (non-deterministic randomness works)
        """
        # Run with seed 100
        result1 = orchestrator.execute_test(
            tournament_type_code="league",
            skills_to_test=["ball_control"],
            player_count=4,
            user_ids=[4, 5, 6, 7],
            campus_id=1,
            random_seed=100
        )

        tournament_id_1 = result1["tournament"]["id"]
        rankings1 = (
            db.query(TournamentRanking)
            .filter(TournamentRanking.tournament_id == tournament_id_1)
            .order_by(TournamentRanking.user_id)  # Order by user_id for comparison
            .all()
        )

        # Run with seed 200
        result2 = orchestrator.execute_test(
            tournament_type_code="league",
            skills_to_test=["ball_control"],
            player_count=4,
            user_ids=[4, 5, 6, 7],
            campus_id=1,
            random_seed=200  # DIFFERENT SEED
        )

        tournament_id_2 = result2["tournament"]["id"]
        rankings2 = (
            db.query(TournamentRanking)
            .filter(TournamentRanking.tournament_id == tournament_id_2)
            .order_by(TournamentRanking.user_id)
            .all()
        )

        # At least one player should have different statistics
        differences_found = False
        for r1, r2 in zip(rankings1, rankings2):
            if (r1.points != r2.points or
                r1.wins != r2.wins or
                r1.draws != r2.draws or
                r1.losses != r2.losses):
                differences_found = True
                break

        assert differences_found, "Different seeds should produce different results"

        print(f"\n✅ Different seeds test passed")
        print(f"   Seed 100 vs Seed 200 produced different results (randomness works)")


@pytest.mark.skip(reason="Manual baseline update - run to regenerate expected values")
def test_generate_regression_baseline(db: Session):
    """
    MANUAL TEST: Run this to generate new baseline values when match logic changes

    Usage:
        pytest tests/integration/test_sandbox_regression.py::test_generate_regression_baseline -v -s

    Copy the output and update expected_baseline in test_deterministic_head_to_head_4_players
    """
    orchestrator = SandboxTestOrchestrator(db)

    result = orchestrator.execute_test(
        tournament_type_code="league",
        skills_to_test=["ball_control", "stamina"],
        skill_weights={"ball_control": 2.0, "stamina": 1.5},
        player_count=4,
        user_ids=[4, 5, 6, 7],
        campus_id=1,
        draw_probability=0.20,
        home_win_probability=0.40,
        random_seed=42  # SAME SEED AS REGRESSION TEST
    )

    tournament_id = result["tournament"]["id"]

    rankings = (
        db.query(TournamentRanking, User.name)
        .join(User, TournamentRanking.user_id == User.id)
        .filter(TournamentRanking.tournament_id == tournament_id)
        .order_by(TournamentRanking.rank)
        .all()
    )

    print("\n" + "="*60)
    print("REGRESSION BASELINE (seed=42)")
    print("="*60)
    print("\nCopy this into expected_baseline in test_deterministic_head_to_head_4_players:\n")
    print("expected_baseline = [")

    for r in rankings:
        ranking = r.TournamentRanking
        matches_played = ranking.wins + ranking.draws + ranking.losses
        print(f"    # Rank {ranking.rank} - {r.name}")
        print(f"    {{")
        print(f"        \"rank\": {ranking.rank},")
        print(f"        \"points\": {int(ranking.points)},")
        print(f"        \"wins\": {ranking.wins},")
        print(f"        \"draws\": {ranking.draws},")
        print(f"        \"losses\": {ranking.losses},")
        print(f"        \"matches\": {matches_played},")
        print(f"    }},")

    print("]")
    print("="*60)
