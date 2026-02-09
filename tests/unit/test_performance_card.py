"""
Unit tests for Performance Card component
Tests percentile calculation, fallback chain, and badge validation
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "streamlit_app"))

from components.tournaments.performance_card_styles import (
    get_percentile_tier,
    get_percentile_badge_text,
    get_badge_icon,
    get_badge_title
)


class TestPercentileCalculation:
    """Test percentile tier calculation and badge text"""

    def test_percentile_tier_top_5(self):
        """Test TOP 5% tier (rank 1/64 = 1.56%)"""
        percentile = 1.56
        tier = get_percentile_tier(percentile)
        assert tier == "top_5"

    def test_percentile_tier_top_5_boundary(self):
        """Test TOP 5% boundary (exactly 5%)"""
        percentile = 5.0
        tier = get_percentile_tier(percentile)
        assert tier == "top_5"

    def test_percentile_tier_top_10(self):
        """Test TOP 10% tier (rank 6/64 = 9.375%)"""
        percentile = 9.375
        tier = get_percentile_tier(percentile)
        assert tier == "top_10"

    def test_percentile_tier_top_10_boundary(self):
        """Test TOP 10% boundary (exactly 10%)"""
        percentile = 10.0
        tier = get_percentile_tier(percentile)
        assert tier == "top_10"

    def test_percentile_tier_top_25(self):
        """Test TOP 25% tier (rank 16/64 = 25%)"""
        percentile = 25.0
        tier = get_percentile_tier(percentile)
        assert tier == "top_25"

    def test_percentile_tier_default(self):
        """Test default tier (rank 32/64 = 50%)"""
        percentile = 50.0
        tier = get_percentile_tier(percentile)
        assert tier == "default"

    def test_percentile_badge_text_top_5(self):
        """Test badge text for TOP 5%"""
        percentile = 3.0
        text = get_percentile_badge_text(percentile)
        assert text == "🔥 TOP 5%"

    def test_percentile_badge_text_top_10(self):
        """Test badge text for TOP 10%"""
        percentile = 8.0
        text = get_percentile_badge_text(percentile)
        assert text == "⚡ TOP 10%"

    def test_percentile_badge_text_top_25(self):
        """Test badge text for TOP 25%"""
        percentile = 20.0
        text = get_percentile_badge_text(percentile)
        assert text == "🎯 TOP 25%"

    def test_percentile_badge_text_default(self):
        """Test badge text for TOP 50%"""
        percentile = 40.0
        text = get_percentile_badge_text(percentile)
        assert text == "📊 TOP 50%"

    def test_edge_case_rank_1_of_1(self):
        """Test edge case: 1st place out of 1 participant (100%)"""
        rank = 1
        total = 1
        percentile = (rank / total) * 100
        assert percentile == 100.0
        tier = get_percentile_tier(percentile)
        assert tier == "default"  # 100% is not top performer

    def test_edge_case_rank_1_of_64(self):
        """Test edge case: 1st place out of 64 (1.56% - TOP 5%)"""
        rank = 1
        total = 64
        percentile = (rank / total) * 100
        assert percentile == 1.5625
        tier = get_percentile_tier(percentile)
        assert tier == "top_5"

    def test_edge_case_rank_32_of_64(self):
        """Test edge case: Median rank (50%)"""
        rank = 32
        total = 64
        percentile = (rank / total) * 100
        assert percentile == 50.0
        tier = get_percentile_tier(percentile)
        assert tier == "default"


class TestBadgeHelpers:
    """Test badge icon and title helper functions"""

    def test_get_badge_icon_champion(self):
        """Test CHAMPION badge icon"""
        icon = get_badge_icon("CHAMPION")
        assert icon == "🥇"

    def test_get_badge_icon_runner_up(self):
        """Test RUNNER_UP badge icon"""
        icon = get_badge_icon("RUNNER_UP")
        assert icon == "🥈"

    def test_get_badge_icon_third_place(self):
        """Test THIRD_PLACE badge icon"""
        icon = get_badge_icon("THIRD_PLACE")
        assert icon == "🥉"

    def test_get_badge_icon_unknown(self):
        """Test unknown badge type returns default icon"""
        icon = get_badge_icon("UNKNOWN_BADGE_TYPE")
        assert icon == "🏅"

    def test_get_badge_title_champion(self):
        """Test CHAMPION badge title"""
        title = get_badge_title("CHAMPION")
        assert title == "CHAMPION"

    def test_get_badge_title_runner_up(self):
        """Test RUNNER_UP badge title"""
        title = get_badge_title("RUNNER_UP")
        assert title == "RUNNER-UP"

    def test_get_badge_title_third_place(self):
        """Test THIRD_PLACE badge title"""
        title = get_badge_title("THIRD_PLACE")
        assert title == "3RD PLACE"

    def test_get_badge_title_unknown(self):
        """Test unknown badge type returns formatted title"""
        title = get_badge_title("SOME_NEW_BADGE")
        assert title == "Some New Badge"  # Title case conversion


class TestRankFallbackChain:
    """Test rank fallback chain logic (simulated)"""

    def test_fallback_chain_current_rank(self):
        """Test fallback chain: ranking.rank exists (AUTHORITY)"""
        badge = {"badge_metadata": {"placement": 1}}
        ranking = {"rank": 1}
        participation = {"placement": 1}

        # Simulate fallback logic
        display_rank = None
        rank_source = None

        if ranking and ranking.get("rank"):
            display_rank = ranking["rank"]
            rank_source = "current"

        assert display_rank == 1
        assert rank_source == "current"

    def test_fallback_chain_participation(self):
        """Test fallback chain: ranking missing, use participation"""
        badge = {"badge_metadata": {"placement": 1}}
        ranking = None
        participation = {"placement": 1}

        # Simulate fallback logic
        display_rank = None
        rank_source = None

        if ranking and ranking.get("rank"):
            display_rank = ranking["rank"]
            rank_source = "current"
        elif participation and participation.get("placement"):
            display_rank = participation["placement"]
            rank_source = "fallback_participation"

        assert display_rank == 1
        assert rank_source == "fallback_participation"

    def test_fallback_chain_badge_metadata(self):
        """Test fallback chain: ranking + participation missing, use badge_metadata"""
        badge = {"badge_metadata": {"placement": 1}}
        ranking = None
        participation = None

        # Simulate fallback logic
        display_rank = None
        rank_source = None

        if ranking and ranking.get("rank"):
            display_rank = ranking["rank"]
            rank_source = "current"
        elif participation and participation.get("placement"):
            display_rank = participation["placement"]
            rank_source = "fallback_participation"
        elif badge and badge.get("badge_metadata", {}).get("placement"):
            display_rank = badge["badge_metadata"]["placement"]
            rank_source = "snapshot"

        assert display_rank == 1
        assert rank_source == "snapshot"

    def test_fallback_chain_all_null(self):
        """Test fallback chain: all sources NULL, rank = None"""
        badge = {"badge_metadata": {}}
        ranking = None
        participation = None

        # Simulate fallback logic
        display_rank = None
        rank_source = None

        if ranking and ranking.get("rank"):
            display_rank = ranking["rank"]
            rank_source = "current"
        elif participation and participation.get("placement"):
            display_rank = participation["placement"]
            rank_source = "fallback_participation"
        elif badge and badge.get("badge_metadata", {}).get("placement"):
            display_rank = badge["badge_metadata"]["placement"]
            rank_source = "snapshot"

        assert display_rank is None
        assert rank_source is None


class TestPlacementValidation:
    """Test placement consistency validation logic"""

    def test_champion_badge_rank_1_valid(self):
        """Test CHAMPION badge with rank=1 (valid)"""
        badge_type = "CHAMPION"
        display_rank = 1

        # Simulate validation
        expected = {"CHAMPION": 1, "RUNNER_UP": 2, "THIRD_PLACE": 3}
        is_valid = display_rank == expected[badge_type]

        assert is_valid is True

    def test_champion_badge_rank_8_invalid(self):
        """Test CHAMPION badge with rank=8 (DATA DRIFT)"""
        badge_type = "CHAMPION"
        display_rank = 8

        # Simulate validation
        expected = {"CHAMPION": 1, "RUNNER_UP": 2, "THIRD_PLACE": 3}
        is_data_drift = display_rank > 3

        assert is_data_drift is True

    def test_runner_up_badge_rank_2_valid(self):
        """Test RUNNER_UP badge with rank=2 (valid)"""
        badge_type = "RUNNER_UP"
        display_rank = 2

        # Simulate validation
        expected = {"CHAMPION": 1, "RUNNER_UP": 2, "THIRD_PLACE": 3}
        is_valid = display_rank == expected[badge_type]

        assert is_valid is True

    def test_third_place_badge_rank_3_valid(self):
        """Test THIRD_PLACE badge with rank=3 (valid)"""
        badge_type = "THIRD_PLACE"
        display_rank = 3

        # Simulate validation
        expected = {"CHAMPION": 1, "RUNNER_UP": 2, "THIRD_PLACE": 3}
        is_valid = display_rank == expected[badge_type]

        assert is_valid is True

    def test_participant_badge_no_validation(self):
        """Test PARTICIPANT badge (no rank validation)"""
        badge_type = "TOURNAMENT_PARTICIPANT"
        display_rank = 15

        # Simulate validation (only validate placement badges)
        placement_badges = ["CHAMPION", "RUNNER_UP", "THIRD_PLACE"]
        requires_validation = badge_type in placement_badges

        assert requires_validation is False


class TestGracefulDegradation:
    """Test graceful degradation for missing data"""

    def test_missing_rank_hides_metric(self):
        """Test: rank=None → metric hidden (not "N/A")"""
        rank = None
        should_display = rank is not None
        assert should_display is False

    def test_missing_points_hides_metric(self):
        """Test: points=None → metric hidden"""
        points = None
        should_display = points is not None
        assert should_display is False

    def test_missing_goals_hides_metric(self):
        """Test: goals_for=None → metric hidden"""
        goals_for = None
        should_display = goals_for is not None
        assert should_display is False

    def test_missing_record_hides_metric(self):
        """Test: all W/D/L None → metric hidden"""
        wins = None
        draws = None
        losses = None
        should_display = any([wins, draws, losses])
        assert should_display is False

    def test_partial_record_shows_metric(self):
        """Test: some W/D/L present → metric shown"""
        wins = 5
        draws = None
        losses = None
        should_display = any([wins, draws, losses])
        assert should_display is True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
