"""
Unit tests for KnockoutBracket.calculate_structure

Covers all explicit branch cases (4, 6, 8, 10, 12 qualifiers) and the
generic power-of-2 fallback for non-standard counts.

DB-free: KnockoutBracket has no instance state; all methods are @staticmethod.
"""
import pytest

from app.services.tournament.session_generation.algorithms.knockout_bracket import (
    KnockoutBracket,
)


@pytest.mark.unit
class TestKnockoutBracketCalculateStructure:
    """Explicit lookup cases for standard tournament sizes."""

    def test_4_qualifiers(self):
        result = KnockoutBracket.calculate_structure(4)
        assert result == {
            "play_in_matches": 0,
            "byes": 0,
            "bracket_size": 4,
            "has_bronze": True,
        }

    def test_6_qualifiers(self):
        result = KnockoutBracket.calculate_structure(6)
        assert result == {
            "play_in_matches": 2,
            "byes": 2,
            "bracket_size": 4,
            "has_bronze": True,
        }

    def test_8_qualifiers(self):
        result = KnockoutBracket.calculate_structure(8)
        assert result == {
            "play_in_matches": 0,
            "byes": 0,
            "bracket_size": 8,
            "has_bronze": True,
        }

    def test_10_qualifiers(self):
        result = KnockoutBracket.calculate_structure(10)
        assert result == {
            "play_in_matches": 3,
            "byes": 4,
            "bracket_size": 8,
            "has_bronze": True,
        }

    def test_12_qualifiers(self):
        result = KnockoutBracket.calculate_structure(12)
        assert result == {
            "play_in_matches": 4,
            "byes": 4,
            "bracket_size": 8,
            "has_bronze": True,
        }


@pytest.mark.unit
class TestKnockoutBracketFallback:
    """Generic power-of-2 fallback for non-standard qualifier counts."""

    def test_3_qualifiers_rounds_to_4_no_bronze(self):
        # 2^ceil(log2(3)) = 4; byes = 1; play_in = (3-1)//2 = 1; has_bronze = False
        result = KnockoutBracket.calculate_structure(3)
        assert result["bracket_size"] == 4
        assert result["byes"] == 1
        assert result["play_in_matches"] == 1
        assert result["has_bronze"] is False

    def test_5_qualifiers_rounds_to_8_has_bronze(self):
        # 2^ceil(log2(5)) = 8; byes = 3; play_in = (5-3)//2 = 1
        result = KnockoutBracket.calculate_structure(5)
        assert result["bracket_size"] == 8
        assert result["byes"] == 3
        assert result["play_in_matches"] == 1
        assert result["has_bronze"] is True

    def test_7_qualifiers_rounds_to_8_has_bronze(self):
        # 2^ceil(log2(7)) = 8; byes = 1; play_in = (7-1)//2 = 3
        result = KnockoutBracket.calculate_structure(7)
        assert result["bracket_size"] == 8
        assert result["byes"] == 1
        assert result["play_in_matches"] == 3
        assert result["has_bronze"] is True

    def test_16_qualifiers_exact_power_of_2(self):
        # 2^ceil(log2(16)) = 16; byes = 0; play_in = 8
        result = KnockoutBracket.calculate_structure(16)
        assert result["bracket_size"] == 16
        assert result["byes"] == 0
        assert result["play_in_matches"] == 8
        assert result["has_bronze"] is True

    def test_14_qualifiers_rounds_to_16(self):
        # 2^ceil(log2(14)) = 16; byes = 2; play_in = (14-2)//2 = 6
        result = KnockoutBracket.calculate_structure(14)
        assert result["bracket_size"] == 16
        assert result["byes"] == 2
        assert result["play_in_matches"] == 6
        assert result["has_bronze"] is True

    def test_bracket_size_plus_byes_equals_next_power_of_2(self):
        """Invariant: byes = bracket_size - qualifiers for any non-standard count."""
        for q in [3, 5, 7, 9, 11, 13, 14, 15, 16]:
            r = KnockoutBracket.calculate_structure(q)
            assert r["byes"] == r["bracket_size"] - q, f"failed for qualifiers={q}"
