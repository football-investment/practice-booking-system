"""
Unit tests for ProgressLicenseCoupler.validate_consistency
(services/progress_license_coupling.py)

Covers all 5 branches of validate_consistency:
  - Neither progress nor license exists  → consistent (no records)
  - Only license exists                  → inconsistent, recommended_action = create_progress_from_license
  - Only progress exists                 → inconsistent, recommended_action = create_license_from_progress
  - Both exist, same level               → consistent, level returned
  - Both exist, different levels         → desync detected, difference + recommended_action
  - Lowercase specialization input       → normalised to uppercase (no error)
"""

import pytest
from unittest.mock import MagicMock

from app.services.progress_license_coupling import ProgressLicenseCoupler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coupler():
    db = MagicMock()
    return ProgressLicenseCoupler(db=db), db


def _multi_q(db, first_values):
    """
    Configure successive db.query().filter().first() calls to return
    different values in order.
    """
    mocks = []
    for first in first_values:
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = first
        mocks.append(q)
    db.query.side_effect = mocks


# ===========================================================================
# validate_consistency
# ===========================================================================

@pytest.mark.unit
class TestValidateConsistency:
    def test_neither_exists_is_consistent(self):
        coupler, db = _coupler()
        _multi_q(db, [None, None])
        result = coupler.validate_consistency(user_id=42, specialization="PLAYER")
        assert result["consistent"] is True
        assert result["progress_exists"] is False
        assert result["license_exists"] is False
        assert "No records" in result["message"]

    def test_only_license_inconsistent(self):
        coupler, db = _coupler()
        license_mock = MagicMock()
        license_mock.current_level = 3
        _multi_q(db, [None, license_mock])
        result = coupler.validate_consistency(user_id=42, specialization="PLAYER")
        assert result["consistent"] is False
        assert result["license_exists"] is True
        assert result["progress_exists"] is False
        assert result["license_level"] == 3
        assert result["recommended_action"] == "create_progress_from_license"

    def test_only_progress_inconsistent(self):
        coupler, db = _coupler()
        progress_mock = MagicMock()
        progress_mock.current_level = 2
        _multi_q(db, [progress_mock, None])
        result = coupler.validate_consistency(user_id=42, specialization="COACH")
        assert result["consistent"] is False
        assert result["progress_exists"] is True
        assert result["license_exists"] is False
        assert result["progress_level"] == 2
        assert result["recommended_action"] == "create_license_from_progress"

    def test_both_exist_same_level_consistent(self):
        coupler, db = _coupler()
        progress_mock = MagicMock()
        progress_mock.current_level = 4
        license_mock = MagicMock()
        license_mock.current_level = 4
        _multi_q(db, [progress_mock, license_mock])
        result = coupler.validate_consistency(user_id=42, specialization="PLAYER")
        assert result["consistent"] is True
        assert result["progress_exists"] is True
        assert result["license_exists"] is True
        assert result["level"] == 4

    def test_both_exist_different_levels_desync(self):
        coupler, db = _coupler()
        progress_mock = MagicMock()
        progress_mock.current_level = 5
        license_mock = MagicMock()
        license_mock.current_level = 3
        _multi_q(db, [progress_mock, license_mock])
        result = coupler.validate_consistency(user_id=42, specialization="INTERNSHIP")
        assert result["consistent"] is False
        assert result["progress_level"] == 5
        assert result["license_level"] == 3
        assert result["difference"] == 2
        assert result["recommended_action"] == "sync_to_higher_level"
        assert "Desync" in result["message"]

    def test_lowercase_specialization_normalised(self):
        """Lowercase input is uppercased internally — no error raised."""
        coupler, db = _coupler()
        _multi_q(db, [None, None])
        result = coupler.validate_consistency(user_id=42, specialization="player")
        assert result["consistent"] is True
