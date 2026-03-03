"""
Unit Tests: availability_service — pure algorithmic functions

Covers:
- parse_date_to_quarters: same-year, multi-year, boundary months, cross-year
- calculate_quarter_overlap: empty inputs, full match, partial, zero, superset
- generate_availability_warnings: all 4 match-score bands (0, 1-49, 50-99, 100)

DB-dependent functions (check_availability_match, check_instructor_has_active_master_position,
get_instructor_active_master_location) are NOT tested here — they require live or mocked
DB sessions and are deferred to integration tests.
"""
import pytest
from datetime import datetime

from app.services.availability_service import (
    parse_date_to_quarters,
    calculate_quarter_overlap,
    generate_availability_warnings,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _dt(year: int, month: int, day: int = 1) -> datetime:
    return datetime(year, month, day)


# ===========================================================================
# TestParseDateToQuarters
# ===========================================================================

class TestParseDateToQuarters:
    """parse_date_to_quarters: converts a date range to sorted quarter codes."""

    # --- Same-year contracts ---

    def test_single_month_q1(self):
        result = parse_date_to_quarters(_dt(2026, 1), _dt(2026, 1))
        assert result == ['Q1']

    def test_single_month_q2(self):
        result = parse_date_to_quarters(_dt(2026, 5), _dt(2026, 5))
        assert result == ['Q2']

    def test_single_month_q3(self):
        result = parse_date_to_quarters(_dt(2026, 7), _dt(2026, 7))
        assert result == ['Q3']

    def test_single_month_q4(self):
        result = parse_date_to_quarters(_dt(2026, 12), _dt(2026, 12))
        assert result == ['Q4']

    def test_full_q1_jan_to_mar(self):
        result = parse_date_to_quarters(_dt(2026, 1), _dt(2026, 3))
        assert result == ['Q1']

    def test_q1_to_q2_span(self):
        result = parse_date_to_quarters(_dt(2026, 1), _dt(2026, 6))
        assert result == ['Q1', 'Q2']

    def test_q2_to_q3_span(self):
        result = parse_date_to_quarters(_dt(2026, 4), _dt(2026, 9))
        assert result == ['Q2', 'Q3']

    def test_q3_to_q4_span(self):
        result = parse_date_to_quarters(_dt(2026, 7), _dt(2026, 12))
        assert result == ['Q3', 'Q4']

    def test_full_year_all_quarters(self):
        result = parse_date_to_quarters(_dt(2026, 1), _dt(2026, 12))
        assert result == ['Q1', 'Q2', 'Q3', 'Q4']

    def test_mid_quarter_boundary_q1_q2(self):
        """March (Q1) to April (Q2) — crosses quarter boundary."""
        result = parse_date_to_quarters(_dt(2026, 3), _dt(2026, 4))
        assert result == ['Q1', 'Q2']

    def test_result_is_sorted(self):
        """Output must be lexicographically sorted."""
        result = parse_date_to_quarters(_dt(2026, 1), _dt(2026, 12))
        assert result == sorted(result)

    # --- Multi-year contracts ---

    def test_two_year_q4_to_q1(self):
        """Oct 2025 – Mar 2026: Q4 (start) + Q1 (end) = [Q1, Q4]."""
        result = parse_date_to_quarters(_dt(2025, 10), _dt(2026, 3))
        assert 'Q4' in result
        assert 'Q1' in result

    def test_two_year_full_years_all_quarters(self):
        """Jan 2025 – Dec 2026: all four quarters covered."""
        result = parse_date_to_quarters(_dt(2025, 1), _dt(2026, 12))
        assert result == ['Q1', 'Q2', 'Q3', 'Q4']

    def test_three_year_span_all_quarters(self):
        """Contract spanning 3 years always covers all quarters (middle year fills gaps)."""
        result = parse_date_to_quarters(_dt(2024, 12), _dt(2026, 1))
        assert result == ['Q1', 'Q2', 'Q3', 'Q4']

    def test_two_year_q3_to_q2(self):
        """Jul 2025 – Jun 2026: Q3, Q4 from 2025; Q1, Q2 from 2026."""
        result = parse_date_to_quarters(_dt(2025, 7), _dt(2026, 6))
        assert sorted(result) == ['Q1', 'Q2', 'Q3', 'Q4']


# ===========================================================================
# TestCalculateQuarterOverlap
# ===========================================================================

class TestCalculateQuarterOverlap:
    """calculate_quarter_overlap: int percentage (0-100)."""

    def test_empty_contract_quarters_returns_100(self):
        """No contract coverage needed → 100% match."""
        assert calculate_quarter_overlap(['Q1', 'Q2'], []) == 100

    def test_empty_instructor_quarters_returns_0(self):
        """Instructor has no availability → 0% match."""
        assert calculate_quarter_overlap([], ['Q1', 'Q2']) == 0

    def test_both_empty_returns_100(self):
        """No requirements, no availability → 100 (vacuously true)."""
        assert calculate_quarter_overlap([], []) == 100

    def test_perfect_match_single_quarter(self):
        assert calculate_quarter_overlap(['Q1'], ['Q1']) == 100

    def test_perfect_match_all_quarters(self):
        qs = ['Q1', 'Q2', 'Q3', 'Q4']
        assert calculate_quarter_overlap(qs, qs) == 100

    def test_zero_overlap(self):
        assert calculate_quarter_overlap(['Q1', 'Q2'], ['Q3', 'Q4']) == 0

    def test_50_percent_overlap(self):
        """Instructor covers 2 of 4 contract quarters → 50%."""
        assert calculate_quarter_overlap(['Q1', 'Q2'], ['Q1', 'Q2', 'Q3', 'Q4']) == 50

    def test_25_percent_overlap(self):
        """Instructor covers 1 of 4 quarters → 25%."""
        assert calculate_quarter_overlap(['Q1'], ['Q1', 'Q2', 'Q3', 'Q4']) == 25

    def test_75_percent_overlap(self):
        assert calculate_quarter_overlap(['Q1', 'Q2', 'Q3'], ['Q1', 'Q2', 'Q3', 'Q4']) == 75

    def test_superset_instructor_returns_100(self):
        """Instructor available for all 4, contract only needs 2 → 100%."""
        assert calculate_quarter_overlap(['Q1', 'Q2', 'Q3', 'Q4'], ['Q1', 'Q2']) == 100

    def test_result_is_integer(self):
        result = calculate_quarter_overlap(['Q1', 'Q2'], ['Q1', 'Q2', 'Q3'])
        assert isinstance(result, int)

    def test_result_clamped_0_to_100(self):
        result = calculate_quarter_overlap(['Q1'], ['Q1', 'Q2', 'Q3', 'Q4'])
        assert 0 <= result <= 100


# ===========================================================================
# TestGenerateAvailabilityWarnings
# ===========================================================================

class TestGenerateAvailabilityWarnings:
    """generate_availability_warnings: 4 score bands (0, <50, <100, 100)."""

    # --- 100% match: no warnings ---

    def test_100_percent_no_warnings(self):
        result = generate_availability_warnings(['Q1', 'Q2'], ['Q1', 'Q2'], 100)
        assert result == []

    def test_100_percent_no_warnings_all_quarters(self):
        qs = ['Q1', 'Q2', 'Q3', 'Q4']
        result = generate_availability_warnings(qs, qs, 100)
        assert result == []

    # --- 0% match: CRITICAL ---

    def test_0_percent_critical_warning(self):
        result = generate_availability_warnings([], ['Q1', 'Q2'], 0)
        assert len(result) == 1
        assert 'CRITICAL' in result[0]

    def test_0_percent_shows_none_for_empty_instructor(self):
        result = generate_availability_warnings([], ['Q1'], 0)
        assert 'NONE' in result[0]

    def test_0_percent_shows_contract_quarters(self):
        result = generate_availability_warnings(['Q3'], ['Q1', 'Q2'], 0)
        assert 'Q1' in result[0]
        assert 'Q2' in result[0]

    def test_0_percent_shows_instructor_quarters(self):
        """Even when instructor has some quarters but none overlap."""
        result = generate_availability_warnings(['Q3', 'Q4'], ['Q1', 'Q2'], 0)
        assert 'Q3' in result[0] or 'Q4' in result[0]

    # --- 1-49%: LOW MATCH ---

    def test_25_percent_low_match_warning(self):
        result = generate_availability_warnings(['Q1'], ['Q1', 'Q2', 'Q3', 'Q4'], 25)
        assert len(result) == 1
        assert 'LOW MATCH' in result[0]
        assert '25%' in result[0]

    def test_49_percent_low_match(self):
        result = generate_availability_warnings(['Q1'], ['Q1', 'Q2', 'Q3'], 49)
        assert 'LOW MATCH' in result[0]

    def test_low_match_shows_missing_quarters(self):
        result = generate_availability_warnings(['Q1'], ['Q1', 'Q2', 'Q3'], 33)
        assert 'Q2' in result[0] or 'Q3' in result[0]

    # --- 50-99%: PARTIAL MATCH ---

    def test_50_percent_is_partial_not_low(self):
        """Boundary: 50% goes into PARTIAL, not LOW MATCH."""
        result = generate_availability_warnings(['Q1', 'Q2'], ['Q1', 'Q2', 'Q3', 'Q4'], 50)
        assert len(result) == 1
        assert 'PARTIAL MATCH' in result[0]
        assert '50%' in result[0]

    def test_75_percent_partial_match(self):
        result = generate_availability_warnings(['Q1', 'Q2', 'Q3'], ['Q1', 'Q2', 'Q3', 'Q4'], 75)
        assert 'PARTIAL MATCH' in result[0]
        assert '75%' in result[0]

    def test_99_percent_still_partial(self):
        result = generate_availability_warnings(['Q1', 'Q2', 'Q3'], ['Q1', 'Q2', 'Q3', 'Q4'], 99)
        assert 'PARTIAL MATCH' in result[0]

    def test_partial_shows_missing_quarters(self):
        result = generate_availability_warnings(['Q1', 'Q2'], ['Q1', 'Q2', 'Q4'], 66)
        assert 'Q4' in result[0]

    def test_partial_shows_instructor_quarters(self):
        result = generate_availability_warnings(['Q1', 'Q2'], ['Q1', 'Q2', 'Q4'], 66)
        # Instructor availability should appear in the warning
        assert 'Q1' in result[0] or 'Q2' in result[0]

    # --- Return type ---

    def test_returns_list(self):
        result = generate_availability_warnings(['Q1'], ['Q1', 'Q2'], 50)
        assert isinstance(result, list)

    def test_each_warning_is_string(self):
        result = generate_availability_warnings([], ['Q1'], 0)
        assert all(isinstance(w, str) for w in result)

    def test_at_most_one_warning_per_call(self):
        """Function generates exactly 0 or 1 warning (not multiple)."""
        for score, iq, cq in [
            (0, [], ['Q1']),
            (25, ['Q1'], ['Q1', 'Q2', 'Q3', 'Q4']),
            (75, ['Q1', 'Q2', 'Q3'], ['Q1', 'Q2', 'Q3', 'Q4']),
            (100, ['Q1'], ['Q1']),
        ]:
            result = generate_availability_warnings(iq, cq, score)
            assert len(result) <= 1, f"Expected ≤1 warning for score={score}, got {result}"
