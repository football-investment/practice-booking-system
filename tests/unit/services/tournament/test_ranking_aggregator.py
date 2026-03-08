"""
Unit Tests: RankingAggregator

Pure algorithmic class — no DB dependency.

Covers all four static methods:
  parse_measured_value      — string → Decimal, ValueError on no-numeric
  aggregate_user_values     — ASC=min / DESC=max across rounds
  calculate_performance_rankings — sort + tie-aware rank assignment
  calculate_wins_rankings   — per-round winner detection, tied-round wins, 0-win users
  aggregate_rankings        — integration: returns (perf, wins) tuple with correct cross-data
"""

import pytest
from decimal import Decimal

from app.services.tournament.results.calculators.ranking_aggregator import RankingAggregator


# ---------------------------------------------------------------------------
# parse_measured_value
# ---------------------------------------------------------------------------

class TestParseMeasuredValue:

    def test_seconds_suffix(self):
        assert RankingAggregator.parse_measured_value("12.5s") == Decimal("12.5")

    def test_points_suffix(self):
        assert RankingAggregator.parse_measured_value("95 points") == Decimal("95")

    def test_meters_suffix(self):
        assert RankingAggregator.parse_measured_value("15.2 meters") == Decimal("15.2")

    def test_bare_integer(self):
        assert RankingAggregator.parse_measured_value("42") == Decimal("42")

    def test_bare_decimal(self):
        assert RankingAggregator.parse_measured_value("3.14159") == Decimal("3.14159")

    def test_number_embedded_in_prefix(self):
        assert RankingAggregator.parse_measured_value("time: 9.8") == Decimal("9.8")

    def test_first_numeric_group_extracted(self):
        # "12.5" appears before "3" — first match wins
        assert RankingAggregator.parse_measured_value("12.5s (attempt 3)") == Decimal("12.5")

    def test_no_numeric_raises_value_error(self):
        with pytest.raises(ValueError, match="Cannot parse measured value"):
            RankingAggregator.parse_measured_value("no-number-here")

    def test_empty_raises_value_error(self):
        with pytest.raises(ValueError):
            RankingAggregator.parse_measured_value("abc")

    def test_special_chars_only_raises(self):
        with pytest.raises(ValueError):
            RankingAggregator.parse_measured_value("---")


# ---------------------------------------------------------------------------
# aggregate_user_values
# ---------------------------------------------------------------------------

class TestAggregateUserValues:

    def test_asc_takes_minimum(self):
        rr = {"1": {"101": "12.5s", "102": "13.2s"},
              "2": {"101": "12.0s", "102": "13.5s"}}
        result = RankingAggregator.aggregate_user_values(rr, "ASC")
        assert result[101] == Decimal("12.0")
        assert result[102] == Decimal("13.2")

    def test_desc_takes_maximum(self):
        rr = {"1": {"1": "80 points", "2": "70 points"},
              "2": {"1": "75 points", "2": "85 points"}}
        result = RankingAggregator.aggregate_user_values(rr, "DESC")
        assert result[1] == Decimal("80")
        assert result[2] == Decimal("85")

    def test_single_round_single_value(self):
        rr = {"1": {"5": "10.0s"}}
        result = RankingAggregator.aggregate_user_values(rr, "ASC")
        assert result[5] == Decimal("10.0")

    def test_empty_rounds_returns_empty(self):
        assert RankingAggregator.aggregate_user_values({}, "ASC") == {}
        assert RankingAggregator.aggregate_user_values({}, "DESC") == {}

    def test_three_rounds_asc_best_is_minimum(self):
        rr = {"1": {"1": "15s"}, "2": {"1": "13s"}, "3": {"1": "14s"}}
        result = RankingAggregator.aggregate_user_values(rr, "ASC")
        assert result[1] == Decimal("13")

    def test_three_rounds_desc_best_is_maximum(self):
        rr = {"1": {"1": "80 points"}, "2": {"1": "95 points"}, "3": {"1": "88 points"}}
        result = RankingAggregator.aggregate_user_values(rr, "DESC")
        assert result[1] == Decimal("95")

    def test_user_absent_from_some_rounds_uses_available(self):
        rr = {"1": {"1": "10s", "2": "12s"},
              "2": {"1": "9s"}}        # user 2 missing from round 2
        result = RankingAggregator.aggregate_user_values(rr, "ASC")
        assert result[1] == Decimal("9")
        assert result[2] == Decimal("12")   # only round 1 value available

    def test_user_ids_converted_to_int(self):
        rr = {"1": {"42": "5s"}}
        result = RankingAggregator.aggregate_user_values(rr, "ASC")
        assert 42 in result
        assert "42" not in result


# ---------------------------------------------------------------------------
# calculate_performance_rankings
# ---------------------------------------------------------------------------

class TestCalculatePerformanceRankings:

    def test_asc_lowest_value_is_rank_1(self):
        vals = {1: Decimal("12.0"), 2: Decimal("13.5"), 3: Decimal("11.8")}
        result = RankingAggregator.calculate_performance_rankings(vals, "ASC")
        by = {r["user_id"]: r for r in result}
        assert by[3]["rank"] == 1   # 11.8 best
        assert by[1]["rank"] == 2
        assert by[2]["rank"] == 3

    def test_desc_highest_value_is_rank_1(self):
        vals = {1: Decimal("80"), 2: Decimal("95"), 3: Decimal("70")}
        result = RankingAggregator.calculate_performance_rankings(vals, "DESC")
        by = {r["user_id"]: r for r in result}
        assert by[2]["rank"] == 1   # 95 best
        assert by[1]["rank"] == 2
        assert by[3]["rank"] == 3

    def test_tie_gives_same_rank(self):
        vals = {1: Decimal("12.0"), 2: Decimal("12.0"), 3: Decimal("15.0")}
        result = RankingAggregator.calculate_performance_rankings(vals, "ASC")
        by = {r["user_id"]: r for r in result}
        assert by[1]["rank"] == by[2]["rank"]   # tied
        assert by[3]["rank"] > by[1]["rank"]    # strictly worse

    def test_all_tied_same_rank(self):
        vals = {1: Decimal("10"), 2: Decimal("10"), 3: Decimal("10")}
        result = RankingAggregator.calculate_performance_rankings(vals, "DESC")
        ranks = {r["rank"] for r in result}
        assert len(ranks) == 1   # all same rank

    def test_single_user_rank_1(self):
        result = RankingAggregator.calculate_performance_rankings({99: Decimal("5.5")}, "ASC")
        assert result[0]["rank"] == 1
        assert result[0]["user_id"] == 99

    def test_empty_returns_empty_list(self):
        assert RankingAggregator.calculate_performance_rankings({}, "ASC") == []

    def test_measurement_unit_in_output(self):
        result = RankingAggregator.calculate_performance_rankings(
            {1: Decimal("10")}, "ASC", measurement_unit="seconds")
        assert result[0]["measurement_unit"] == "seconds"

    def test_default_measurement_unit_is_units(self):
        result = RankingAggregator.calculate_performance_rankings({1: Decimal("10")}, "ASC")
        assert result[0]["measurement_unit"] == "units"

    def test_final_value_is_float(self):
        result = RankingAggregator.calculate_performance_rankings(
            {1: Decimal("12.5")}, "ASC")
        assert isinstance(result[0]["final_value"], float)
        assert result[0]["final_value"] == 12.5


# ---------------------------------------------------------------------------
# calculate_wins_rankings
# ---------------------------------------------------------------------------

class TestCalculateWinsRankings:

    def test_asc_round_winner_has_lowest_value(self):
        rr = {"1": {"1": "10s", "2": "12s", "3": "11s"}}
        result = RankingAggregator.calculate_wins_rankings(rr, "ASC", total_rounds=1)
        by = {r["user_id"]: r for r in result}
        assert by[1]["wins"] == 1   # 10s is best
        assert by[2]["wins"] == 0
        assert by[3]["wins"] == 0

    def test_desc_round_winner_has_highest_value(self):
        rr = {"1": {"1": "80 points", "2": "90 points", "3": "70 points"}}
        result = RankingAggregator.calculate_wins_rankings(rr, "DESC", total_rounds=1)
        by = {r["user_id"]: r for r in result}
        assert by[2]["wins"] == 1   # 90 is best
        assert by[1]["wins"] == 0
        assert by[3]["wins"] == 0

    def test_tied_best_value_both_users_win_round(self):
        rr = {"1": {"1": "10s", "2": "10s", "3": "12s"}}
        result = RankingAggregator.calculate_wins_rankings(rr, "ASC", total_rounds=1)
        by = {r["user_id"]: r for r in result}
        assert by[1]["wins"] == 1
        assert by[2]["wins"] == 1   # tie → both win
        assert by[3]["wins"] == 0

    def test_multi_round_wins_accumulate(self):
        rr = {
            "1": {"1": "10s", "2": "12s"},
            "2": {"1": "11s", "2": "9s"},
            "3": {"1": "8s",  "2": "10s"},
        }
        result = RankingAggregator.calculate_wins_rankings(rr, "ASC", total_rounds=3)
        by = {r["user_id"]: r for r in result}
        assert by[1]["wins"] == 2   # rounds 1 and 3
        assert by[2]["wins"] == 1   # round 2

    def test_zero_win_user_included(self):
        rr = {"1": {"1": "5s", "2": "10s"}}
        result = RankingAggregator.calculate_wins_rankings(rr, "ASC", total_rounds=1)
        by = {r["user_id"]: r for r in result}
        assert 2 in by
        assert by[2]["wins"] == 0

    def test_parse_error_user_skipped_from_round(self):
        """Unparseable value → user excluded from round winner calc, still in output."""
        rr = {"1": {"1": "10s", "2": "invalid-value"}}
        result = RankingAggregator.calculate_wins_rankings(rr, "ASC", total_rounds=1)
        by = {r["user_id"]: r for r in result}
        assert by[1]["wins"] == 1   # parseable user wins
        assert by[2]["wins"] == 0   # unparseable — 0 wins

    def test_tied_wins_same_rank(self):
        rr = {"1": {"1": "10s", "2": "12s"},
              "2": {"1": "12s", "2": "10s"}}
        result = RankingAggregator.calculate_wins_rankings(rr, "ASC", total_rounds=2)
        by = {r["user_id"]: r for r in result}
        assert by[1]["wins"] == 1
        assert by[2]["wins"] == 1
        assert by[1]["rank"] == by[2]["rank"]

    def test_higher_wins_ranked_first(self):
        rr = {"1": {"1": "5s", "2": "10s"},
              "2": {"1": "6s", "2": "10s"},
              "3": {"1": "7s", "2": "10s"}}
        result = RankingAggregator.calculate_wins_rankings(rr, "ASC", total_rounds=3)
        by = {r["user_id"]: r for r in result}
        assert by[1]["rank"] == 1   # 3 wins
        assert by[2]["rank"] == 2   # 0 wins

    def test_total_rounds_in_every_entry(self):
        rr = {"1": {"1": "5s"}}
        result = RankingAggregator.calculate_wins_rankings(rr, "ASC", total_rounds=7)
        assert result[0]["total_rounds"] == 7

    def test_empty_rounds_returns_empty(self):
        assert RankingAggregator.calculate_wins_rankings({}, "ASC", total_rounds=0) == []


# ---------------------------------------------------------------------------
# aggregate_rankings (integration)
# ---------------------------------------------------------------------------

class TestAggregateRankings:

    def test_returns_tuple_with_two_lists(self):
        rr = {"1": {"1": "10s", "2": "12s"}, "2": {"1": "9s", "2": "11s"}}
        perf, wins = RankingAggregator.aggregate_rankings(rr, "ASC", total_rounds=2)
        assert isinstance(perf, list)
        assert isinstance(wins, list)

    def test_asc_best_performer_rank_1_in_perf(self):
        rr = {"1": {"1": "10s", "2": "13s"},
              "2": {"1": "9s",  "2": "14s"}}
        perf, wins = RankingAggregator.aggregate_rankings(rr, "ASC", total_rounds=2)
        by_perf = {r["user_id"]: r for r in perf}
        assert by_perf[1]["rank"] == 1   # best time = 9s

    def test_round_wins_computed_separately_from_best_time(self):
        """User with best individual time may win fewer rounds than
        a user with consistent good (but not best) times."""
        rr = {
            "1": {"1": "8s",  "2": "9s"},    # u1 wins round
            "2": {"1": "15s", "2": "10s"},   # u2 wins round
            "3": {"1": "20s", "2": "11s"},   # u2 wins round
        }
        perf, wins = RankingAggregator.aggregate_rankings(rr, "ASC", total_rounds=3)
        by_perf = {r["user_id"]: r for r in perf}
        by_wins = {r["user_id"]: r for r in wins}
        assert by_perf[1]["rank"] == 1   # best single time = 8s
        assert by_wins[2]["rank"] == 1   # more round wins (2 vs 1)

    def test_measurement_unit_passed_through(self):
        rr = {"1": {"1": "10 meters"}}
        perf, _ = RankingAggregator.aggregate_rankings(
            rr, "DESC", total_rounds=1, measurement_unit="meters")
        assert perf[0]["measurement_unit"] == "meters"

    def test_desc_highest_scorer_rank_1(self):
        rr = {"1": {"1": "80 points", "2": "95 points"},
              "2": {"1": "75 points", "2": "70 points"}}
        perf, wins = RankingAggregator.aggregate_rankings(rr, "DESC", total_rounds=2)
        by_perf = {r["user_id"]: r for r in perf}
        assert by_perf[2]["rank"] == 1   # 95 is highest personal best
