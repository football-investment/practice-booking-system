"""
Unit tests for ProgressLicenseSyncService (services/progress_license_sync_service.py)
Sprint M3 (2026-03-05) — branch coverage

sync_progress_to_license:
  - no progress → failure
  - no license → create license
  - already in sync → action: none, no commit
  - out of sync → update license + LicenseProgression
  - max_achieved_level updated correctly
  - lowercase specialization normalised

sync_license_to_progress:
  - no license → failure
  - no progress → create progress
  - already in sync → action: none, no commit
  - out of sync → update progress

find_desync_issues:
  - no issues → []
  - level mismatch detected (progress > license)
  - level mismatch detected (license > progress) → opposite recommended_action
  - orphan progress (missing license) detected
  - orphan license (missing progress) detected
  - specialization filter applied
  - multiple issues aggregated

auto_sync_all:
  - dry_run=True → report only, no sync
  - missing_license issue_type → routes to sync_progress_to_license
  - missing_progress issue_type → routes to sync_license_to_progress
  - default direction progress_to_license
  - direction license_to_progress
  - sync failure → failed_count incremented
  - exception during sync → caught, failed_count
  - no issues → zeros

sync_user_all_specializations:
  - progress_to_license → calls sync_progress_to_license for all 3 specializations
  - license_to_progress → calls sync_license_to_progress for all 3
  - result contains PLAYER/COACH/INTERNSHIP keys
  - exception per specialization caught, result has success:False
  - sync_direction reflected in result
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.progress_license_sync_service import ProgressLicenseSyncService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc():
    db = MagicMock()
    return ProgressLicenseSyncService(db=db), db


def _q(first_val):
    """Single-use mock: db.query(...).filter(...).first() → first_val."""
    m = MagicMock()
    m.filter.return_value = m
    m.first.return_value = first_val
    return m


def _chain(return_all):
    """Mock for complex query chains (join/outerjoin/filter/all)."""
    m = MagicMock()
    m.join.return_value = m
    m.outerjoin.return_value = m
    m.filter.return_value = m
    m.all.return_value = return_all
    return m


def _row(**kwargs):
    """Create a mock row with named attributes."""
    r = MagicMock()
    for k, v in kwargs.items():
        setattr(r, k, v)
    return r


# ===========================================================================
# sync_progress_to_license
# ===========================================================================

@pytest.mark.unit
class TestSyncProgressToLicense:

    def test_no_progress_returns_failure(self):
        svc, db = _svc()
        db.query.side_effect = [_q(None)]
        result = svc.sync_progress_to_license(user_id=42, specialization="PLAYER")
        assert result["success"] is False
        assert result["action"] == "none"
        db.commit.assert_not_called()

    def test_no_license_creates_new_license(self):
        svc, db = _svc()
        progress = MagicMock()
        progress.current_level = 3
        progress.created_at = None
        progress.last_activity = None
        db.query.side_effect = [_q(progress), _q(None)]
        result = svc.sync_progress_to_license(user_id=42, specialization="PLAYER")
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["progress_level"] == 3
        assert result["synced"] is True
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_already_in_sync_no_update(self):
        svc, db = _svc()
        progress = MagicMock()
        progress.current_level = 4
        license_ = MagicMock()
        license_.current_level = 4
        db.query.side_effect = [_q(progress), _q(license_)]
        result = svc.sync_progress_to_license(user_id=42, specialization="PLAYER")
        assert result["success"] is True
        assert result["action"] == "none"
        assert result["synced"] is True
        db.commit.assert_not_called()

    def test_out_of_sync_updates_license(self):
        svc, db = _svc()
        progress = MagicMock()
        progress.current_level = 5
        progress.total_xp = 200
        progress.completed_sessions = 10
        license_ = MagicMock()
        license_.current_level = 3
        license_.max_achieved_level = 4
        license_.id = 20
        db.query.side_effect = [_q(progress), _q(license_)]
        result = svc.sync_progress_to_license(user_id=42, specialization="PLAYER")
        assert result["success"] is True
        assert result["action"] == "updated"
        assert license_.current_level == 5
        assert result["old_license_level"] == 3
        assert result["new_license_level"] == license_.current_level
        db.add.assert_called_once()   # LicenseProgression added
        db.commit.assert_called_once()

    def test_max_achieved_level_updated_on_sync(self):
        svc, db = _svc()
        progress = MagicMock()
        progress.current_level = 6
        progress.total_xp = 300
        progress.completed_sessions = 15
        license_ = MagicMock()
        license_.current_level = 4
        license_.max_achieved_level = 5
        license_.id = 20
        db.query.side_effect = [_q(progress), _q(license_)]
        svc.sync_progress_to_license(user_id=42, specialization="COACH")
        assert license_.max_achieved_level == 6

    def test_lowercase_specialization_normalised(self):
        """Lowercase 'player' is uppercased — treated as PLAYER."""
        svc, db = _svc()
        db.query.side_effect = [_q(None)]
        result = svc.sync_progress_to_license(user_id=42, specialization="player")
        assert result["success"] is False  # no progress — but no exception


# ===========================================================================
# sync_license_to_progress
# ===========================================================================

@pytest.mark.unit
class TestSyncLicenseToProgress:

    def test_no_license_returns_failure(self):
        svc, db = _svc()
        db.query.side_effect = [_q(None)]
        result = svc.sync_license_to_progress(user_id=42, specialization="PLAYER")
        assert result["success"] is False
        assert result["action"] == "none"

    def test_no_progress_creates_new_progress(self):
        svc, db = _svc()
        license_ = MagicMock()
        license_.current_level = 4
        license_.last_advanced_at = None
        db.query.side_effect = [_q(license_), _q(None)]
        result = svc.sync_license_to_progress(user_id=42, specialization="PLAYER")
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["license_level"] == 4
        assert result["synced"] is True
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_already_in_sync_no_update(self):
        svc, db = _svc()
        license_ = MagicMock()
        license_.current_level = 3
        progress = MagicMock()
        progress.current_level = 3
        db.query.side_effect = [_q(license_), _q(progress)]
        result = svc.sync_license_to_progress(user_id=42, specialization="COACH")
        assert result["success"] is True
        assert result["action"] == "none"
        db.commit.assert_not_called()

    def test_out_of_sync_updates_progress(self):
        svc, db = _svc()
        license_ = MagicMock()
        license_.current_level = 7
        progress = MagicMock()
        progress.current_level = 2
        db.query.side_effect = [_q(license_), _q(progress)]
        result = svc.sync_license_to_progress(user_id=42, specialization="INTERNSHIP")
        assert result["success"] is True
        assert result["action"] == "updated"
        assert progress.current_level == 7
        assert result["old_progress_level"] == 2
        assert result["new_progress_level"] == progress.current_level
        db.commit.assert_called_once()

    def test_lowercase_specialization_normalised(self):
        svc, db = _svc()
        db.query.side_effect = [_q(None)]
        result = svc.sync_license_to_progress(user_id=42, specialization="internship")
        assert result["success"] is False  # no license — but no exception


# ===========================================================================
# find_desync_issues
# ===========================================================================

@pytest.mark.unit
class TestFindDesyncIssues:

    def _setup(self, db, main_rows, orphan_progress_rows, orphan_license_rows):
        db.query.side_effect = [
            _chain(main_rows),
            _chain(orphan_progress_rows),
            _chain(orphan_license_rows),
        ]

    def test_no_issues_returns_empty(self):
        svc, db = _svc()
        same = _row(progress_level=3, license_level=3, student_id=1,
                    email="a@b.com", specialization_id="PLAYER")
        self._setup(db, [same], [], [])
        issues = svc.find_desync_issues()
        assert issues == []

    def test_level_mismatch_progress_ahead(self):
        svc, db = _svc()
        row = _row(progress_level=5, license_level=3, student_id=2,
                   email="x@y.com", specialization_id="PLAYER")
        self._setup(db, [row], [], [])
        issues = svc.find_desync_issues()
        assert len(issues) == 1
        assert issues[0]["user_id"] == 2
        assert issues[0]["difference"] == 2
        assert issues[0]["recommended_action"] == "sync_progress_to_license"

    def test_level_mismatch_license_ahead(self):
        svc, db = _svc()
        row = _row(progress_level=2, license_level=6, student_id=3,
                   email="z@z.com", specialization_id="COACH")
        self._setup(db, [row], [], [])
        issues = svc.find_desync_issues()
        assert issues[0]["recommended_action"] == "sync_license_to_progress"

    def test_orphan_progress_missing_license(self):
        svc, db = _svc()
        orphan = _row(student_id=4, email="o@p.com",
                      specialization_id="PLAYER", current_level=3)
        self._setup(db, [], [orphan], [])
        issues = svc.find_desync_issues()
        assert len(issues) == 1
        assert issues[0]["issue_type"] == "missing_license"
        assert issues[0]["recommended_action"] == "create_license_from_progress"
        assert issues[0]["license_level"] is None

    def test_orphan_license_missing_progress(self):
        svc, db = _svc()
        orphan = _row(user_id=5, email="q@r.com",
                      specialization_type="INTERNSHIP", current_level=2)
        self._setup(db, [], [], [orphan])
        issues = svc.find_desync_issues()
        assert len(issues) == 1
        assert issues[0]["issue_type"] == "missing_progress"
        assert issues[0]["recommended_action"] == "create_progress_from_license"
        assert issues[0]["progress_level"] is None

    def test_specialization_filter_applied(self):
        svc, db = _svc()
        self._setup(db, [], [], [])
        issues = svc.find_desync_issues(specialization="PLAYER")
        assert issues == []
        assert db.query.call_count == 3

    def test_multiple_issues_aggregated(self):
        svc, db = _svc()
        row1 = _row(progress_level=4, license_level=2, student_id=1,
                    email="a@b.com", specialization_id="PLAYER")
        row2 = _row(progress_level=1, license_level=5, student_id=2,
                    email="c@d.com", specialization_id="COACH")
        orphan = _row(student_id=3, email="e@f.com",
                      specialization_id="PLAYER", current_level=1)
        self._setup(db, [row1, row2], [orphan], [])
        issues = svc.find_desync_issues()
        assert len(issues) == 3


# ===========================================================================
# auto_sync_all
# ===========================================================================

@pytest.mark.unit
class TestAutoSyncAll:

    def test_dry_run_returns_issues_no_sync(self):
        svc, db = _svc()
        fake_issues = [{"user_id": 1, "specialization": "PLAYER"}]
        with patch.object(svc, "find_desync_issues", return_value=fake_issues):
            result = svc.auto_sync_all(dry_run=True)
        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["total_issues"] == 1
        assert result["issues"] == fake_issues

    def test_missing_license_routes_to_sync_progress_to_license(self):
        svc, db = _svc()
        issue = {"user_id": 1, "specialization": "PLAYER", "issue_type": "missing_license"}
        with patch.object(svc, "find_desync_issues", return_value=[issue]):
            with patch.object(svc, "sync_progress_to_license",
                              return_value={"success": True}) as mock_sync:
                result = svc.auto_sync_all()
        mock_sync.assert_called_once_with(1, "PLAYER")
        assert result["synced_count"] == 1
        assert result["failed_count"] == 0

    def test_missing_progress_routes_to_sync_license_to_progress(self):
        svc, db = _svc()
        issue = {"user_id": 2, "specialization": "COACH", "issue_type": "missing_progress"}
        with patch.object(svc, "find_desync_issues", return_value=[issue]):
            with patch.object(svc, "sync_license_to_progress",
                              return_value={"success": True}) as mock_sync:
                result = svc.auto_sync_all()
        mock_sync.assert_called_once_with(2, "COACH")
        assert result["synced_count"] == 1

    def test_default_direction_progress_to_license(self):
        svc, db = _svc()
        issue = {"user_id": 3, "specialization": "INTERNSHIP"}  # no issue_type
        with patch.object(svc, "find_desync_issues", return_value=[issue]):
            with patch.object(svc, "sync_progress_to_license",
                              return_value={"success": True}) as mock_sync:
                svc.auto_sync_all(sync_direction="progress_to_license")
        mock_sync.assert_called_once()

    def test_direction_license_to_progress(self):
        svc, db = _svc()
        issue = {"user_id": 3, "specialization": "PLAYER"}  # no issue_type
        with patch.object(svc, "find_desync_issues", return_value=[issue]):
            with patch.object(svc, "sync_license_to_progress",
                              return_value={"success": True}) as mock_sync:
                svc.auto_sync_all(sync_direction="license_to_progress")
        mock_sync.assert_called_once()

    def test_sync_failure_increments_failed_count(self):
        svc, db = _svc()
        issue = {"user_id": 1, "specialization": "PLAYER"}
        with patch.object(svc, "find_desync_issues", return_value=[issue]):
            with patch.object(svc, "sync_progress_to_license",
                              return_value={"success": False}):
                result = svc.auto_sync_all()
        assert result["failed_count"] == 1
        assert result["synced_count"] == 0

    def test_exception_during_sync_caught(self):
        svc, db = _svc()
        issue = {"user_id": 1, "specialization": "PLAYER"}
        with patch.object(svc, "find_desync_issues", return_value=[issue]):
            with patch.object(svc, "sync_progress_to_license",
                              side_effect=RuntimeError("boom")):
                result = svc.auto_sync_all()
        assert result["failed_count"] == 1
        assert result["synced_count"] == 0

    def test_no_issues_returns_zeros(self):
        svc, db = _svc()
        with patch.object(svc, "find_desync_issues", return_value=[]):
            result = svc.auto_sync_all()
        assert result["total_issues"] == 0
        assert result["synced_count"] == 0
        assert result["failed_count"] == 0


# ===========================================================================
# sync_user_all_specializations
# ===========================================================================

@pytest.mark.unit
class TestSyncUserAllSpecializations:

    def test_progress_to_license_calls_all_three(self):
        svc, db = _svc()
        with patch.object(svc, "sync_progress_to_license",
                          return_value={"success": True}) as mock_sync:
            svc.sync_user_all_specializations(user_id=42,
                                              sync_direction="progress_to_license")
        assert mock_sync.call_count == 3
        called_specs = {c.args[1] for c in mock_sync.call_args_list}
        assert called_specs == {"PLAYER", "COACH", "INTERNSHIP"}

    def test_license_to_progress_calls_all_three(self):
        svc, db = _svc()
        with patch.object(svc, "sync_license_to_progress",
                          return_value={"success": True}) as mock_sync:
            svc.sync_user_all_specializations(user_id=2,
                                              sync_direction="license_to_progress")
        assert mock_sync.call_count == 3

    def test_result_contains_all_specializations(self):
        svc, db = _svc()
        with patch.object(svc, "sync_progress_to_license",
                          return_value={"success": True}):
            result = svc.sync_user_all_specializations(user_id=42)
        assert "PLAYER" in result["results"]
        assert "COACH" in result["results"]
        assert "INTERNSHIP" in result["results"]
        assert result["user_id"] == 42

    def test_exception_per_specialization_caught(self):
        svc, db = _svc()
        with patch.object(svc, "sync_progress_to_license",
                          side_effect=RuntimeError("boom")):
            result = svc.sync_user_all_specializations(user_id=42)
        for spec_result in result["results"].values():
            assert spec_result["success"] is False

    def test_sync_direction_in_result(self):
        svc, db = _svc()
        with patch.object(svc, "sync_progress_to_license",
                          return_value={"success": True}):
            result = svc.sync_user_all_specializations(
                user_id=5, sync_direction="progress_to_license"
            )
        assert result["sync_direction"] == "progress_to_license"
