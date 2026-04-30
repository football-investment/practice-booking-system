"""Unit tests for calculate_dominant_badge() — dominant foot badge utility.

Badge contract:
  "Rl" — right_pct ≥ 65 %
  "rL" — left_pct  ≥ 65 %
  "RL" — both feet in the 45–65 % balanced range
  "rl" — neither dominant / unassessed

pytest -m unit tests/unit/test_dominant_foot.py
"""
import pytest
from app.utils.dominant_foot import calculate_dominant_badge


@pytest.mark.unit
class TestDominantBadge:
    # ── None / zero inputs ────────────────────────────────────────────────────

    def test_both_none_returns_rl(self):
        assert calculate_dominant_badge(None, None) == "rl"

    def test_both_zero_returns_rl(self):
        assert calculate_dominant_badge(0.0, 0.0) == "rl"

    def test_right_none_left_zero_returns_rl(self):
        assert calculate_dominant_badge(None, 0.0) == "rl"

    def test_right_zero_left_none_returns_rl(self):
        assert calculate_dominant_badge(0.0, None) == "rl"

    # ── Right-footed "Rl" ────────────────────────────────────────────────────

    def test_right_dominant_clear(self):
        # right=80, left=20 → right_pct=80 ≥ 65 → "Rl"
        assert calculate_dominant_badge(80.0, 20.0) == "Rl"

    def test_right_dominant_boundary_65(self):
        # right=65, left=35 → right_pct=65.0 exactly → "Rl"
        assert calculate_dominant_badge(65.0, 35.0) == "Rl"

    def test_right_dominant_left_none(self):
        # left=None treated as 0 → right_pct=100 → "Rl"
        assert calculate_dominant_badge(70.0, None) == "Rl"

    # ── Left-footed "rL" ─────────────────────────────────────────────────────

    def test_left_dominant_clear(self):
        assert calculate_dominant_badge(20.0, 80.0) == "rL"

    def test_left_dominant_boundary_65(self):
        assert calculate_dominant_badge(35.0, 65.0) == "rL"

    def test_left_dominant_right_none(self):
        assert calculate_dominant_badge(None, 70.0) == "rL"

    # ── Two-footed "RL" ───────────────────────────────────────────────────────

    def test_two_footed_equal(self):
        # right=50, left=50 → both 50 → in [45,65] → "RL"
        assert calculate_dominant_badge(50.0, 50.0) == "RL"

    def test_two_footed_near_boundary(self):
        # right=55, left=45 → right_pct≈55, left_pct≈45 → "RL"
        assert calculate_dominant_badge(55.0, 45.0) == "RL"

    def test_two_footed_high_boundary(self):
        # right=64.9, left=35.1 → right_pct≈64.9 < 65 → left_pct≈35.1 < 45
        # → neither branch hits → "rl"  (not "RL" — left outside [45,65])
        assert calculate_dominant_badge(64.9, 35.1) == "rl"

    # ── Unassessed "rl" ───────────────────────────────────────────────────────

    def test_unassessed_asymmetric_not_dominant_not_balanced(self):
        # right=60, left=30 → right_pct=66.7 ≥ 65 → "Rl" actually
        # verify edge: right=64, left=36 → right_pct≈64 < 65; left≈36 < 45 → "rl"
        assert calculate_dominant_badge(64.0, 36.0) == "rl"

    def test_unassessed_very_low_scores(self):
        # both non-zero but tiny and neither dominant
        assert calculate_dominant_badge(10.0, 10.0) == "RL"

    # ── Boundary precision ────────────────────────────────────────────────────

    def test_right_just_below_65_is_not_rl(self):
        # right=64.99, left=35.01 → right_pct≈64.99 < 65 → not "Rl"
        result = calculate_dominant_badge(64.99, 35.01)
        assert result != "Rl"

    def test_left_just_below_65_is_not_rL(self):
        result = calculate_dominant_badge(35.01, 64.99)
        assert result != "rL"

    # ── Return type ───────────────────────────────────────────────────────────

    def test_always_returns_string(self):
        for args in [
            (None, None), (0.0, 0.0), (80.0, 20.0),
            (20.0, 80.0), (50.0, 50.0), (None, 70.0),
        ]:
            assert isinstance(calculate_dominant_badge(*args), str)
