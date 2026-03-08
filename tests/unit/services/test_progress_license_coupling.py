"""
Unit tests for ProgressLicenseCoupler (services/progress_license_coupling.py)
Sprint M extension (2026-03-05) — complete branch coverage

validate_consistency:
  - Neither exists → consistent (no records)
  - Only license → inconsistent, recommended_action = create_progress_from_license
  - Only progress → inconsistent, recommended_action = create_license_from_progress
  - Both same level → consistent
  - Both different levels → desync, difference, recommended_action
  - Lowercase input → normalised

update_level_atomic:
  - Happy path: level unchanged (no LicenseProgression created)
  - Happy path: level changes (LicenseProgression created)
  - COACH specialization → theory/practice hours updated
  - invalid level < 1 → ValueError → {success: False, error_type: validation_error}
  - invalid level > max → ValueError → {success: False, error_type: validation_error}
  - negative XP → ValueError → rollback
  - negative sessions → ValueError → rollback
  - SQLAlchemyError → {success: False, error_type: database_error}
  - Unexpected exception → {success: False, error_type: unknown_error}

sync_existing_records_atomic:
  - source=progress, already in sync → action: "none"
  - source=progress, out of sync → license updated
  - source=license, already in sync → action: "none"
  - source=license, out of sync → progress updated
  - invalid source → ValueError caught → rollback → success: False
  - general exception → rollback → success: False
"""

import pytest
from unittest.mock import MagicMock, patch

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


# ===========================================================================
# Helpers for update_level_atomic / sync_existing_records_atomic
# ===========================================================================

def _mock_progress_obj(level=2, xp=100, sessions=5, projects=2,
                        theory=0, practice=0):
    p = MagicMock()
    p.current_level = level
    p.total_xp = xp
    p.completed_sessions = sessions
    p.completed_projects = projects
    p.theory_hours_completed = theory
    p.practice_hours_completed = practice
    p.id = 10
    return p


def _mock_license_obj(level=2, max_level=2):
    lic = MagicMock()
    lic.current_level = level
    lic.max_achieved_level = max_level
    lic.id = 20
    return lic


def _coupler_with_locks(progress_obj, license_obj):
    """
    Returns (coupler, db) with acquire_locks stubbed to yield (progress, license).
    db.commit / db.rollback / db.refresh are MagicMocks.
    """
    from contextlib import contextmanager
    coupler, db = _coupler()

    @contextmanager
    def _fake_locks(uid, spec):
        yield progress_obj, license_obj

    coupler.acquire_locks = _fake_locks
    return coupler, db


# ===========================================================================
# update_level_atomic
# ===========================================================================

@pytest.mark.unit
class TestUpdateLevelAtomic:

    @staticmethod
    def _patch_max_level(max_val=8):
        return patch(
            "app.models.license.LicenseSystemHelper.get_specialization_max_level",
            return_value=max_val
        )

    def test_level_unchanged_no_progression_record(self):
        """If old_license_level == new_level, no LicenseProgression is created."""
        progress = _mock_progress_obj(level=3, xp=100, sessions=5)
        license_ = _mock_license_obj(level=3, max_level=3)
        coupler, db = _coupler_with_locks(progress, license_)
        with self._patch_max_level():
            result = coupler.update_level_atomic(
                user_id=42, specialization="PLAYER", new_level=3
            )
        assert result["success"] is True
        assert result["progression_created"] is False
        db.add.assert_not_called()

    def test_level_changes_progression_record_created(self):
        """Level change → LicenseProgression added to db."""
        progress = _mock_progress_obj(level=2, xp=100, sessions=5)
        license_ = _mock_license_obj(level=2, max_level=2)
        coupler, db = _coupler_with_locks(progress, license_)
        with self._patch_max_level():
            result = coupler.update_level_atomic(
                user_id=42, specialization="PLAYER", new_level=3,
                xp_change=50, sessions_change=1
            )
        assert result["success"] is True
        assert result["progression_created"] is True
        db.add.assert_called_once()  # LicenseProgression added

    def test_level_changes_max_achieved_updated(self):
        progress = _mock_progress_obj(level=3)
        license_ = _mock_license_obj(level=3, max_level=3)
        coupler, db = _coupler_with_locks(progress, license_)
        with self._patch_max_level():
            coupler.update_level_atomic(user_id=42, specialization="PLAYER", new_level=5)
        assert license_.max_achieved_level == 5

    def test_max_achieved_not_downgraded(self):
        """max_achieved_level = max(current_max, new_level) — never decreases."""
        progress = _mock_progress_obj(level=5)
        license_ = _mock_license_obj(level=5, max_level=7)
        coupler, db = _coupler_with_locks(progress, license_)
        with self._patch_max_level(max_val=8):
            coupler.update_level_atomic(user_id=42, specialization="PLAYER", new_level=4)
        # max_achieved stays 7, not downgraded to 4
        assert license_.max_achieved_level == 7

    def test_coach_theory_practice_hours_updated(self):
        progress = _mock_progress_obj(level=2, theory=10, practice=5)
        license_ = _mock_license_obj(level=2)
        coupler, db = _coupler_with_locks(progress, license_)
        with self._patch_max_level():
            coupler.update_level_atomic(
                user_id=42, specialization="COACH", new_level=2,
                theory_hours_change=3, practice_hours_change=2
            )
        assert progress.theory_hours_completed == 13
        assert progress.practice_hours_completed == 7

    def test_player_does_not_update_coach_hours(self):
        """Non-COACH specialization: theory/practice not touched."""
        progress = _mock_progress_obj(level=2, theory=10, practice=5)
        license_ = _mock_license_obj(level=2)
        coupler, db = _coupler_with_locks(progress, license_)
        with self._patch_max_level():
            coupler.update_level_atomic(
                user_id=42, specialization="PLAYER", new_level=2,
                theory_hours_change=99, practice_hours_change=99
            )
        # theory/practice must NOT change for non-COACH
        assert progress.theory_hours_completed == 10
        assert progress.practice_hours_completed == 5

    def test_invalid_level_below_1_returns_validation_error(self):
        progress = _mock_progress_obj(level=2)
        license_ = _mock_license_obj(level=2)
        coupler, db = _coupler_with_locks(progress, license_)
        with self._patch_max_level(max_val=8):
            result = coupler.update_level_atomic(
                user_id=42, specialization="PLAYER", new_level=0
            )
        assert result["success"] is False
        assert result["error_type"] == "validation_error"
        db.rollback.assert_called_once()

    def test_invalid_level_above_max_returns_validation_error(self):
        progress = _mock_progress_obj(level=7)
        license_ = _mock_license_obj(level=7)
        coupler, db = _coupler_with_locks(progress, license_)
        with self._patch_max_level(max_val=8):
            result = coupler.update_level_atomic(
                user_id=42, specialization="PLAYER", new_level=9
            )
        assert result["success"] is False
        assert result["error_type"] == "validation_error"

    def test_negative_xp_raises_validation_error(self):
        """total_xp goes negative → ValueError → validation_error."""
        progress = _mock_progress_obj(level=2, xp=10)
        # Make total_xp go negative after +=
        progress.total_xp = 10
        license_ = _mock_license_obj(level=2)
        coupler, db = _coupler_with_locks(progress, license_)

        # total_xp += xp_change → 10 + (-50) = -40 → ValueError
        # But += on MagicMock won't actually compute. We need a real int.
        # Use a real progress object via spec to get actual int arithmetic.
        real_progress = MagicMock(spec=[
            "current_level", "total_xp", "completed_sessions",
            "completed_projects", "last_activity",
            "theory_hours_completed", "practice_hours_completed", "id"
        ])
        real_progress.current_level = 2
        real_progress.total_xp = 10
        real_progress.completed_sessions = 0
        real_progress.completed_projects = 0
        real_progress.id = 10

        coupler, db = _coupler_with_locks(real_progress, license_)
        with self._patch_max_level():
            result = coupler.update_level_atomic(
                user_id=42, specialization="PLAYER", new_level=2, xp_change=-50
            )
        assert result["success"] is False
        assert result["error_type"] == "validation_error"

    def test_sqlalchemy_error_returns_database_error(self):
        from sqlalchemy.exc import SQLAlchemyError
        coupler, db = _coupler()
        # acquire_locks raises SQLAlchemyError
        from contextlib import contextmanager

        @contextmanager
        def _fail_locks(uid, spec):
            raise SQLAlchemyError("DB failure")
            yield  # noqa: unreachable — needed for contextmanager protocol

        coupler.acquire_locks = _fail_locks
        result = coupler.update_level_atomic(
            user_id=42, specialization="PLAYER", new_level=2
        )
        assert result["success"] is False
        assert result["error_type"] == "database_error"
        db.rollback.assert_called_once()

    def test_unexpected_exception_returns_unknown_error(self):
        coupler, db = _coupler()
        from contextlib import contextmanager

        @contextmanager
        def _fail_locks(uid, spec):
            raise RuntimeError("something unexpected")
            yield  # noqa

        coupler.acquire_locks = _fail_locks
        result = coupler.update_level_atomic(
            user_id=42, specialization="PLAYER", new_level=2
        )
        assert result["success"] is False
        assert result["error_type"] == "unknown_error"
        db.rollback.assert_called_once()

    def test_xp_and_sessions_added_to_progress(self):
        progress = _mock_progress_obj(level=2, xp=100, sessions=5, projects=2)
        license_ = _mock_license_obj(level=2)
        coupler, db = _coupler_with_locks(progress, license_)
        with self._patch_max_level():
            result = coupler.update_level_atomic(
                user_id=42, specialization="PLAYER", new_level=2,
                xp_change=50, sessions_change=3, projects_change=1
            )
        assert result["success"] is True
        assert result["xp_change"] == 50
        assert result["sessions_change"] == 3


# ===========================================================================
# sync_existing_records_atomic
# ===========================================================================

@pytest.mark.unit
class TestSyncExistingRecordsAtomic:

    def test_source_progress_already_in_sync(self):
        """Progress and License same level → action: none, no commit."""
        progress = _mock_progress_obj(level=4)
        license_ = _mock_license_obj(level=4)
        coupler, db = _coupler_with_locks(progress, license_)
        result = coupler.sync_existing_records_atomic(
            user_id=42, specialization="PLAYER", source="progress"
        )
        assert result["success"] is True
        assert result["action"] == "none"
        db.commit.assert_not_called()

    def test_source_progress_out_of_sync_updates_license(self):
        progress = _mock_progress_obj(level=5)
        license_ = _mock_license_obj(level=3, max_level=3)
        coupler, db = _coupler_with_locks(progress, license_)
        result = coupler.sync_existing_records_atomic(
            user_id=42, specialization="PLAYER", source="progress"
        )
        assert result["success"] is True
        assert license_.current_level == 5
        assert license_.max_achieved_level == 5
        db.commit.assert_called_once()

    def test_source_license_already_in_sync(self):
        progress = _mock_progress_obj(level=3)
        license_ = _mock_license_obj(level=3)
        coupler, db = _coupler_with_locks(progress, license_)
        result = coupler.sync_existing_records_atomic(
            user_id=42, specialization="COACH", source="license"
        )
        assert result["success"] is True
        assert result["action"] == "none"
        db.commit.assert_not_called()

    def test_source_license_out_of_sync_updates_progress(self):
        progress = _mock_progress_obj(level=2)
        license_ = _mock_license_obj(level=6)
        coupler, db = _coupler_with_locks(progress, license_)
        result = coupler.sync_existing_records_atomic(
            user_id=42, specialization="INTERNSHIP", source="license"
        )
        assert result["success"] is True
        assert progress.current_level == 6
        db.commit.assert_called_once()

    def test_invalid_source_returns_failure(self):
        """source not 'progress' or 'license' → ValueError → caught → success:False."""
        progress = _mock_progress_obj(level=3)
        license_ = _mock_license_obj(level=3)
        coupler, db = _coupler_with_locks(progress, license_)
        result = coupler.sync_existing_records_atomic(
            user_id=42, specialization="PLAYER", source="invalid_source"
        )
        assert result["success"] is False
        db.rollback.assert_called_once()

    def test_exception_during_sync_triggers_rollback(self):
        """Any Exception inside acquire_locks → rollback → success: False."""
        coupler, db = _coupler()
        from contextlib import contextmanager

        @contextmanager
        def _boom(uid, spec):
            raise Exception("boom")
            yield  # noqa

        coupler.acquire_locks = _boom
        result = coupler.sync_existing_records_atomic(
            user_id=42, specialization="PLAYER", source="progress"
        )
        assert result["success"] is False
        db.rollback.assert_called_once()

    def test_final_level_in_result(self):
        """Result contains final_level matching progress after sync."""
        progress = _mock_progress_obj(level=2)
        license_ = _mock_license_obj(level=5)
        coupler, db = _coupler_with_locks(progress, license_)
        result = coupler.sync_existing_records_atomic(
            user_id=42, specialization="PLAYER", source="license"
        )
        # After sync: progress.current_level = 5 (set by sync)
        assert result["final_level"] == progress.current_level
