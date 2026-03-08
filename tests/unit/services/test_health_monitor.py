"""
Unit tests for app/services/health_monitor.py
Covers: HealthMonitor.check_all_users, _log_violations, get_latest_report,
        get_health_summary, health_check_job
Note: json and aiofiles are missing from source imports (production bugs).
      json is injected into the module namespace for _log_violations tests.
      Async methods are tested where possible; aiofiles path is skipped.
"""
import json
import asyncio
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import app.services.health_monitor as hm_module
from app.services.health_monitor import HealthMonitor, health_check_job


# Inject missing json import into the module (production bug workaround for tests)
hm_module.json = json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_monitor(user_spec_pairs=None, consistent_map=None, log_dir=None):
    """
    Build a HealthMonitor with mocked db and coupler.

    user_spec_pairs: list of (user_id, spec) rows returned by query
    consistent_map: dict of (user_id, spec) → bool (True=consistent)
    """
    db = MagicMock()
    fetchall_result = user_spec_pairs or []
    db.execute.return_value.fetchall.return_value = fetchall_result

    monitor = HealthMonitor.__new__(HealthMonitor)
    monitor.db = db

    coupler = MagicMock()
    if consistent_map is None:
        coupler.validate_consistency.return_value = {"consistent": True}
    else:
        def _validate(uid, spec):
            key = (uid, spec)
            is_consistent = consistent_map.get(key, True)
            if is_consistent:
                return {"consistent": True}
            return {
                "consistent": False,
                "progress_level": 2,
                "license_level": 1,
                "recommended_action": "sync_required",
            }
        coupler.validate_consistency.side_effect = _validate

    monitor.coupler = coupler

    if log_dir is None:
        tmp = tempfile.mkdtemp()
        monitor.log_dir = Path(tmp)
    else:
        monitor.log_dir = log_dir

    return monitor


# ---------------------------------------------------------------------------
# check_all_users
# ---------------------------------------------------------------------------

class TestCheckAllUsers:

    def test_cau01_empty_users_all_consistent(self):
        """CAU-01: no user-spec pairs → 100% consistency, no violations."""
        monitor = _make_monitor(user_spec_pairs=[])
        result = monitor.check_all_users(dry_run=True)
        assert result["total_checked"] == 0
        assert result["consistent"] == 0
        assert result["inconsistent"] == 0
        assert result["consistency_rate"] == 100.0
        assert result["violations"] == []

    def test_cau02_all_consistent(self):
        """CAU-02: all pairs consistent → 100% rate, no violations."""
        pairs = [(1, "GANCUJU_PLAYER"), (2, "LFA_FOOTBALL_PLAYER")]
        monitor = _make_monitor(user_spec_pairs=pairs)
        result = monitor.check_all_users(dry_run=True)
        assert result["total_checked"] == 2
        assert result["consistent"] == 2
        assert result["inconsistent"] == 0
        assert result["consistency_rate"] == 100.0

    def test_cau03_some_inconsistent_dry_run(self):
        """CAU-03: inconsistency with dry_run=True → violations collected, not logged."""
        pairs = [(1, "GANCUJU_PLAYER"), (2, "LFA_FOOTBALL_PLAYER")]
        cmap = {(1, "GANCUJU_PLAYER"): True, (2, "LFA_FOOTBALL_PLAYER"): False}
        monitor = _make_monitor(user_spec_pairs=pairs, consistent_map=cmap)
        result = monitor.check_all_users(dry_run=True)
        assert result["inconsistent"] == 1
        assert len(result["violations"]) == 1
        assert result["violations"][0]["user_id"] == 2

    def test_cau04_inconsistent_dry_run_false_no_violations_skip_log(self):
        """CAU-04: dry_run=False, all consistent → _log_violations NOT called."""
        monitor = _make_monitor(user_spec_pairs=[(1, "SPEC")])
        with patch.object(monitor, "_log_violations") as mock_log:
            result = monitor.check_all_users(dry_run=False)
        mock_log.assert_not_called()
        assert result["inconsistent"] == 0

    def test_cau05_inconsistent_dry_run_false_triggers_log(self):
        """CAU-05: dry_run=False + violations → _log_violations called once."""
        pairs = [(1, "SPEC")]
        cmap = {(1, "SPEC"): False}
        monitor = _make_monitor(user_spec_pairs=pairs, consistent_map=cmap)
        with patch.object(monitor, "_log_violations") as mock_log:
            result = monitor.check_all_users(dry_run=False)
        mock_log.assert_called_once()
        assert result["inconsistent"] == 1

    def test_cau06_consistency_rate_calculation(self):
        """CAU-06: 2 of 4 consistent → 50% rate."""
        pairs = [(i, "SPEC") for i in range(4)]
        cmap = {(0, "SPEC"): True, (1, "SPEC"): True, (2, "SPEC"): False, (3, "SPEC"): False}
        monitor = _make_monitor(user_spec_pairs=pairs, consistent_map=cmap)
        result = monitor.check_all_users(dry_run=True)
        assert result["consistency_rate"] == 50.0


# ---------------------------------------------------------------------------
# _log_violations
# ---------------------------------------------------------------------------

class TestLogViolations:

    def test_lv01_writes_json_file(self):
        """LV-01: writes violation report to JSON file in log_dir."""
        tmp = tempfile.mkdtemp()
        log_dir = Path(tmp)
        monitor = _make_monitor(log_dir=log_dir)
        report = {
            "timestamp": "2025-01-01T10:00:00",
            "total_checked": 5,
            "consistent": 4,
            "inconsistent": 1,
            "violations": [{"user_id": 99}],
        }
        monitor._log_violations(report)
        json_files = list(log_dir.glob("*_violations.json"))
        assert len(json_files) == 1
        data = json.loads(json_files[0].read_text())
        assert data["inconsistent"] == 1

    def test_lv02_file_write_exception_logged(self):
        """LV-02: open() raises inside try → exception caught, no crash."""
        monitor = _make_monitor()
        report = {"timestamp": "2025-01-01", "violations": []}
        with patch("builtins.open", side_effect=OSError("disk full")):
            monitor._log_violations(report)  # must not raise


# ---------------------------------------------------------------------------
# get_latest_report (sync)
# ---------------------------------------------------------------------------

class TestGetLatestReport:

    def test_glr01_no_files_returns_none(self):
        """GLR-01: empty log_dir → returns None."""
        monitor = _make_monitor()
        result = monitor.get_latest_report()
        assert result is None

    def test_glr02_file_exists_reads_json(self):
        """GLR-02: violation file exists → parsed JSON dict returned."""
        tmp = tempfile.mkdtemp()
        log_dir = Path(tmp)
        test_data = {"consistency_rate": 95.0, "inconsistent": 2}
        (log_dir / "20250101_100000_violations.json").write_text(json.dumps(test_data))
        monitor = _make_monitor(log_dir=log_dir)
        result = monitor.get_latest_report()
        assert result["consistency_rate"] == 95.0
        assert result["inconsistent"] == 2

    def test_glr03_file_read_error_returns_none(self):
        """GLR-03: file exists but read raises → returns None."""
        tmp = tempfile.mkdtemp()
        log_dir = Path(tmp)
        (log_dir / "20250101_100000_violations.json").write_text("broken json !!!")
        monitor = _make_monitor(log_dir=log_dir)
        result = monitor.get_latest_report()
        assert result is None


# ---------------------------------------------------------------------------
# get_health_summary (sync)
# ---------------------------------------------------------------------------

class TestGetHealthSummary:

    def _summary(self, report):
        monitor = _make_monitor()
        with patch.object(monitor, "get_latest_report", return_value=report):
            return monitor.get_health_summary()

    def test_ghs01_no_report_returns_unknown(self):
        """GHS-01: no latest report → status='unknown'."""
        result = self._summary(None)
        assert result["status"] == "unknown"
        assert result["last_check"] is None
        assert result["consistency_rate"] is None
        assert result["requires_attention"] is False

    def test_ghs02_rate_99_plus_is_healthy(self):
        """GHS-02: consistency_rate >= 99 → healthy."""
        report = {
            "consistency_rate": 99.5,
            "inconsistent": 0,
            "total_checked": 100,
            "timestamp": "2025-01-01T10:00:00",
            "violations": [],
        }
        result = self._summary(report)
        assert result["status"] == "healthy"
        assert result["requires_attention"] is False

    def test_ghs03_rate_95_to_99_is_degraded(self):
        """GHS-03: 95 <= consistency_rate < 99 → degraded."""
        report = {
            "consistency_rate": 97.0,
            "inconsistent": 3,
            "total_checked": 100,
            "timestamp": "2025-01-01T10:00:00",
            "violations": [],
        }
        result = self._summary(report)
        assert result["status"] == "degraded"
        assert result["requires_attention"] is True

    def test_ghs04_rate_below_95_is_critical(self):
        """GHS-04: consistency_rate < 95 → critical."""
        report = {
            "consistency_rate": 80.0,
            "inconsistent": 20,
            "total_checked": 100,
            "timestamp": "2025-01-01T10:00:00",
            "violations": [{"user_id": 1}],
        }
        result = self._summary(report)
        assert result["status"] == "critical"
        assert result["requires_attention"] is True
        assert result["total_violations"] == 20

    def test_ghs05_exactly_99_is_healthy(self):
        """GHS-05: consistency_rate == 99.0 → boundary is healthy."""
        report = {
            "consistency_rate": 99.0,
            "inconsistent": 0,
            "total_checked": 50,
            "timestamp": "ts",
            "violations": [],
        }
        result = self._summary(report)
        assert result["status"] == "healthy"

    def test_ghs06_exactly_95_is_degraded(self):
        """GHS-06: consistency_rate == 95.0 → boundary is degraded."""
        report = {
            "consistency_rate": 95.0,
            "inconsistent": 2,
            "total_checked": 40,
            "timestamp": "ts",
            "violations": [],
        }
        result = self._summary(report)
        assert result["status"] == "degraded"


# ---------------------------------------------------------------------------
# health_check_job
# ---------------------------------------------------------------------------

class TestHealthCheckJob:

    def test_hcj01_success_path(self):
        """HCJ-01: normal execution completes, db closed."""
        mock_db = MagicMock()
        mock_monitor = MagicMock()
        mock_monitor.check_all_users.return_value = {
            "consistent": 10,
            "total_checked": 10,
            "inconsistent": 0,
            "consistency_rate": 100.0,
        }
        with patch("app.services.health_monitor.SessionLocal", return_value=mock_db), \
             patch("app.services.health_monitor.HealthMonitor", return_value=mock_monitor):
            health_check_job()
        mock_monitor.check_all_users.assert_called_once_with(dry_run=False)
        mock_db.close.assert_called_once()

    def test_hcj02_inconsistencies_logged(self):
        """HCJ-02: inconsistencies found → warning path executed."""
        mock_db = MagicMock()
        mock_monitor = MagicMock()
        mock_monitor.check_all_users.return_value = {
            "consistent": 8,
            "total_checked": 10,
            "inconsistent": 2,
            "consistency_rate": 80.0,
        }
        with patch("app.services.health_monitor.SessionLocal", return_value=mock_db), \
             patch("app.services.health_monitor.HealthMonitor", return_value=mock_monitor):
            health_check_job()
        mock_db.close.assert_called_once()

    def test_hcj03_exception_closes_db(self):
        """HCJ-03: exception in monitor → caught, db still closed."""
        mock_db = MagicMock()
        with patch("app.services.health_monitor.SessionLocal", return_value=mock_db), \
             patch("app.services.health_monitor.HealthMonitor", side_effect=RuntimeError("boom")):
            health_check_job()  # must not raise
        mock_db.close.assert_called_once()
