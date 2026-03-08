"""
Unit tests for ResultValidator

Covers:
- validate_ranks_unique (@staticmethod, no DB) — full branch coverage
- validate_users_enrolled / validate_match_results — via mock db

DB-free paths use ResultValidator(db=None).
DB paths mock self.db.query(...).filter(...).all() via patch.object.
"""
import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from app.services.tournament.results.validators.result_validator import ResultValidator


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _enrollment(user_id: int):
    return SimpleNamespace(user_id=user_id)


def _validator_with_enrolled(enrolled_ids):
    """Return a ResultValidator whose db returns a fixed enrollment list."""
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [
        _enrollment(uid) for uid in enrolled_ids
    ]
    return ResultValidator(db=db)


# ─── validate_ranks_unique ────────────────────────────────────────────────────

@pytest.mark.unit
class TestValidateRanksUnique:

    def test_unique_ranks_valid(self):
        is_valid, msg = ResultValidator.validate_ranks_unique([1, 2, 3])
        assert is_valid is True
        assert msg == ""

    def test_duplicate_ranks_invalid(self):
        is_valid, msg = ResultValidator.validate_ranks_unique([1, 2, 2])
        assert is_valid is False
        assert msg == "Duplicate ranks are not allowed"

    def test_single_rank_valid(self):
        is_valid, msg = ResultValidator.validate_ranks_unique([1])
        assert is_valid is True
        assert msg == ""

    def test_empty_ranks_valid(self):
        is_valid, msg = ResultValidator.validate_ranks_unique([])
        assert is_valid is True
        assert msg == ""

    def test_all_same_ranks_invalid(self):
        is_valid, msg = ResultValidator.validate_ranks_unique([1, 1, 1])
        assert is_valid is False
        assert "Duplicate" in msg

    def test_first_and_last_duplicate(self):
        is_valid, msg = ResultValidator.validate_ranks_unique([1, 2, 3, 4, 1])
        assert is_valid is False

    def test_large_unique_list_valid(self):
        is_valid, msg = ResultValidator.validate_ranks_unique(list(range(1, 17)))
        assert is_valid is True
        assert msg == ""


# ─── validate_users_enrolled ──────────────────────────────────────────────────

@pytest.mark.unit
class TestValidateUsersEnrolled:

    def test_all_users_enrolled(self):
        validator = _validator_with_enrolled([1, 2, 3])
        is_valid, invalid = validator.validate_users_enrolled(tournament_id=10, user_ids=[1, 2, 3])
        assert is_valid is True
        assert invalid == set()

    def test_one_user_not_enrolled(self):
        validator = _validator_with_enrolled([1, 2])  # user 3 missing
        is_valid, invalid = validator.validate_users_enrolled(tournament_id=10, user_ids=[1, 2, 3])
        assert is_valid is False
        assert 3 in invalid

    def test_all_users_not_enrolled(self):
        validator = _validator_with_enrolled([])
        is_valid, invalid = validator.validate_users_enrolled(tournament_id=10, user_ids=[1, 2])
        assert is_valid is False
        assert invalid == {1, 2}

    def test_empty_user_list_valid(self):
        validator = _validator_with_enrolled([])
        is_valid, invalid = validator.validate_users_enrolled(tournament_id=10, user_ids=[])
        assert is_valid is True
        assert invalid == set()


# ─── validate_match_results ───────────────────────────────────────────────────

@pytest.mark.unit
class TestValidateMatchResults:

    def test_valid_enrolled_unique_ranks(self):
        validator = _validator_with_enrolled([1, 2, 3])
        is_valid, msg = validator.validate_match_results(
            tournament_id=10, user_ids=[1, 2, 3], ranks=[1, 2, 3]
        )
        assert is_valid is True
        assert msg == ""

    def test_unenrolled_user_short_circuits(self):
        validator = _validator_with_enrolled([1, 2])  # user 3 not enrolled
        is_valid, msg = validator.validate_match_results(
            tournament_id=10, user_ids=[1, 2, 3], ranks=[1, 2, 3]
        )
        assert is_valid is False
        assert "not enrolled" in msg
        assert "3" in msg

    def test_duplicate_ranks_fails_after_enrollment_check(self):
        validator = _validator_with_enrolled([1, 2, 3])
        is_valid, msg = validator.validate_match_results(
            tournament_id=10, user_ids=[1, 2, 3], ranks=[1, 2, 2]
        )
        assert is_valid is False
        assert "Duplicate" in msg

    def test_unenrolled_check_takes_priority_over_duplicate_ranks(self):
        """Enrollment check runs first; duplicate rank error should not appear."""
        validator = _validator_with_enrolled([1])  # users 2, 3 not enrolled
        is_valid, msg = validator.validate_match_results(
            tournament_id=10, user_ids=[1, 2, 3], ranks=[1, 1, 2]
        )
        assert is_valid is False
        assert "not enrolled" in msg
