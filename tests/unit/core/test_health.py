"""
Unit tests for app/core/health.py — HealthChecker

Covers:
  get_database_health() [async]
    - successful DB path → status="healthy", response_time_ms set
    - connection_test=True when SELECT 1 returns 1
    - slow response (>1000ms) → status="degraded", warning present
    - SQLAlchemyError → status="unhealthy", error field set
    - DB close called on success
    - DB close called even on SQLAlchemyError
    - details dict contains users_count, sessions_count, bookings_count

  get_system_health() [sync]
    - normal load (≤4.0) and normal disk (≤85%) → status="healthy"
    - high CPU load (>4.0) → status="degraded", warning message
    - high disk usage (>85%) → status="degraded", warning message
    - both high → status="degraded", two warnings
    - os.getloadavg() unavailable (AttributeError) → no crash, load_average=None
    - os.statvfs() unavailable (OSError) → no crash, disk=None
    - platform info keys present

  get_application_health() [sync]
    - always returns status="healthy"
    - version key present
    - features dict contains expected keys
    - debug_mode reflects settings.DEBUG

  get_comprehensive_health() [async]
    - all healthy → overall_status="healthy"
    - DB unhealthy → overall_status="unhealthy"
    - DB degraded, others healthy → overall_status="degraded"
    - summary.total_checks == 3
    - summary.healthy_checks counts correctly
    - response_time_ms key present
    - checks dict has database/system/application keys
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from sqlalchemy.exc import SQLAlchemyError

from app.core.health import HealthChecker

# ──────────────────────────────────────────────────────────────────────────────
# Patch targets
# ──────────────────────────────────────────────────────────────────────────────

_PATCH_SESSION = "app.core.health.SessionLocal"


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _mock_db(
    select_1_result=1,
    users_count=5,
    sessions_count=3,
    bookings_count=2,
):
    """Return a MagicMock DB session with execute chains set up."""
    mock_db = MagicMock()

    def _execute_side_effect(query):
        query_str = str(query)
        q_result = MagicMock()
        if "SELECT 1" in query_str:
            q_result.scalar.return_value = select_1_result
        elif "users" in query_str:
            q_result.scalar.return_value = users_count
        elif "sessions" in query_str:
            q_result.scalar.return_value = sessions_count
        elif "bookings" in query_str:
            q_result.scalar.return_value = bookings_count
        else:
            q_result.scalar.return_value = 0
        return q_result

    mock_db.execute.side_effect = _execute_side_effect
    return mock_db


# ──────────────────────────────────────────────────────────────────────────────
# get_database_health
# ──────────────────────────────────────────────────────────────────────────────

class TestGetDatabaseHealth:

    def test_successful_connection_returns_healthy(self):
        """Normal DB → status='healthy'."""
        with patch(_PATCH_SESSION) as mock_sl:
            mock_sl.return_value = _mock_db()
            result = _run(HealthChecker.get_database_health())

        assert result["status"] == "healthy"

    def test_connection_test_true_when_select_1_returns_1(self):
        """details.connection_test is True when SELECT 1 scalar == 1."""
        with patch(_PATCH_SESSION) as mock_sl:
            mock_sl.return_value = _mock_db(select_1_result=1)
            result = _run(HealthChecker.get_database_health())

        assert result["details"]["connection_test"] is True

    def test_response_time_ms_is_set(self):
        """response_time_ms is a non-negative float."""
        with patch(_PATCH_SESSION) as mock_sl:
            mock_sl.return_value = _mock_db()
            result = _run(HealthChecker.get_database_health())

        assert isinstance(result["response_time_ms"], (int, float))
        assert result["response_time_ms"] >= 0

    def test_details_contain_row_counts(self):
        """details dict includes users_count, sessions_count, bookings_count."""
        with patch(_PATCH_SESSION) as mock_sl:
            mock_sl.return_value = _mock_db(users_count=10, sessions_count=4, bookings_count=7)
            result = _run(HealthChecker.get_database_health())

        assert result["details"]["users_count"] == 10
        assert result["details"]["sessions_count"] == 4
        assert result["details"]["bookings_count"] == 7

    def test_slow_response_returns_degraded(self):
        """response_time_ms > 1000 → status='degraded' with warning."""
        with patch(_PATCH_SESSION) as mock_sl, \
             patch("app.core.health.time") as mock_time:
            mock_db = _mock_db()
            mock_sl.return_value = mock_db
            # Simulate slow response: start=0, later calls return 1.5s
            mock_time.time.side_effect = [0.0, 1.5]
            result = _run(HealthChecker.get_database_health())

        assert result["status"] == "degraded"
        assert "warning" in result

    def test_sqlalchemy_error_returns_unhealthy(self):
        """SQLAlchemyError → status='unhealthy', error field populated."""
        with patch(_PATCH_SESSION) as mock_sl:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.side_effect = SQLAlchemyError("Connection refused")
            result = _run(HealthChecker.get_database_health())

        assert result["status"] == "unhealthy"
        assert result["error"] is not None
        assert "Connection refused" in result["error"]

    def test_sqlalchemy_error_sets_connection_failed_detail(self):
        """SQLAlchemyError → details.connection_failed=True."""
        with patch(_PATCH_SESSION) as mock_sl:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.side_effect = SQLAlchemyError("timeout")
            result = _run(HealthChecker.get_database_health())

        assert result["details"]["connection_failed"] is True

    def test_db_closed_on_success(self):
        """DB session is closed after successful health check."""
        with patch(_PATCH_SESSION) as mock_sl:
            mock_db = _mock_db()
            mock_sl.return_value = mock_db
            _run(HealthChecker.get_database_health())

        mock_db.close.assert_called_once()

    def test_db_closed_on_sqlalchemy_error(self):
        """DB session is closed even when SQLAlchemyError occurs."""
        with patch(_PATCH_SESSION) as mock_sl:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            mock_db.execute.side_effect = SQLAlchemyError("fail")
            _run(HealthChecker.get_database_health())

        mock_db.close.assert_called_once()

    def test_unknown_status_not_returned_on_success(self):
        """Status 'unknown' should not appear in the result on success."""
        with patch(_PATCH_SESSION) as mock_sl:
            mock_sl.return_value = _mock_db()
            result = _run(HealthChecker.get_database_health())

        assert result["status"] != "unknown"


# ──────────────────────────────────────────────────────────────────────────────
# get_system_health
# ──────────────────────────────────────────────────────────────────────────────

class TestGetSystemHealth:

    def _statvfs(self, total_gb=100, used_pct=50):
        """Build a mock statvfs result with the desired disk usage."""
        total_bytes = total_gb * (1024 ** 3)
        free_bytes = int(total_bytes * (1 - used_pct / 100))
        mock_stat = MagicMock()
        mock_stat.f_frsize = 4096
        mock_stat.f_blocks = total_bytes // 4096
        mock_stat.f_available = free_bytes // 4096
        return mock_stat

    def test_normal_conditions_returns_healthy(self):
        """Normal load + normal disk → status='healthy'."""
        with patch("os.getloadavg", return_value=(1.0, 0.9, 0.8)), \
             patch("os.statvfs", return_value=self._statvfs(used_pct=40)):
            result = HealthChecker.get_system_health()

        assert result["status"] == "healthy"

    def test_high_load_returns_degraded(self):
        """CPU load > 4.0 → status='degraded'."""
        with patch("os.getloadavg", return_value=(5.0, 4.5, 3.0)), \
             patch("os.statvfs", return_value=self._statvfs(used_pct=40)):
            result = HealthChecker.get_system_health()

        assert result["status"] == "degraded"

    def test_high_load_warning_message(self):
        """High load warning appears in warnings list."""
        with patch("os.getloadavg", return_value=(5.0, 4.5, 3.0)), \
             patch("os.statvfs", return_value=self._statvfs(used_pct=40)):
            result = HealthChecker.get_system_health()

        assert result["warnings"] is not None
        assert any("load" in w.lower() for w in result["warnings"])

    def test_high_disk_usage_returns_degraded(self):
        """Disk usage > 85% → status='degraded'."""
        with patch("os.getloadavg", return_value=(1.0, 0.9, 0.8)), \
             patch("os.statvfs", return_value=self._statvfs(used_pct=90)):
            result = HealthChecker.get_system_health()

        assert result["status"] == "degraded"

    def test_high_disk_warning_message(self):
        """High disk warning appears in warnings list."""
        with patch("os.getloadavg", return_value=(1.0, 0.9, 0.8)), \
             patch("os.statvfs", return_value=self._statvfs(used_pct=90)):
            result = HealthChecker.get_system_health()

        assert result["warnings"] is not None
        assert any("disk" in w.lower() for w in result["warnings"])

    def test_both_high_load_and_disk_two_warnings(self):
        """Both metrics critical → two separate warnings."""
        with patch("os.getloadavg", return_value=(6.0, 5.0, 4.0)), \
             patch("os.statvfs", return_value=self._statvfs(used_pct=92)):
            result = HealthChecker.get_system_health()

        assert len(result["warnings"]) == 2

    def test_load_at_exactly_4_is_healthy(self):
        """Load == 4.0 exactly is NOT degraded (threshold is >4.0)."""
        with patch("os.getloadavg", return_value=(4.0, 3.5, 2.5)), \
             patch("os.statvfs", return_value=self._statvfs(used_pct=40)):
            result = HealthChecker.get_system_health()

        assert result["status"] == "healthy"

    def test_disk_at_exactly_85_is_healthy(self):
        """Disk == 85.0% exactly is NOT degraded (threshold is >85)."""
        with patch("os.getloadavg", return_value=(1.0, 0.9, 0.8)), \
             patch("os.statvfs", return_value=self._statvfs(used_pct=85)):
            result = HealthChecker.get_system_health()

        assert result["status"] == "healthy"

    def test_getloadavg_unavailable_no_crash(self):
        """AttributeError from os.getloadavg → load_average=None, no exception."""
        with patch("os.getloadavg", side_effect=AttributeError), \
             patch("os.statvfs", return_value=self._statvfs(used_pct=40)):
            result = HealthChecker.get_system_health()

        assert result["load_average"] is None

    def test_statvfs_unavailable_no_crash(self):
        """OSError from os.statvfs → disk=None, no exception."""
        with patch("os.getloadavg", return_value=(1.0, 0.9, 0.8)), \
             patch("os.statvfs", side_effect=OSError):
            result = HealthChecker.get_system_health()

        assert result["disk"] is None

    def test_platform_keys_present(self):
        """Result includes platform.system, machine, python_version."""
        with patch("os.getloadavg", return_value=(1.0, 0.9, 0.8)), \
             patch("os.statvfs", return_value=self._statvfs()):
            result = HealthChecker.get_system_health()

        assert "platform" in result
        assert "system" in result["platform"]
        assert "python_version" in result["platform"]

    def test_no_warnings_key_is_none_when_healthy(self):
        """warnings is None (not empty list) when no issues detected."""
        with patch("os.getloadavg", return_value=(1.0, 0.9, 0.8)), \
             patch("os.statvfs", return_value=self._statvfs(used_pct=40)):
            result = HealthChecker.get_system_health()

        assert result["warnings"] is None

    def test_uncaught_exception_returns_unhealthy(self):
        """Unexpected exception in system health → status='unhealthy'."""
        with patch("os.getloadavg", side_effect=RuntimeError("unexpected")), \
             patch("os.statvfs", side_effect=RuntimeError("unexpected")):
            result = HealthChecker.get_system_health()

        # The outer try/except catches and returns unhealthy
        assert result["status"] == "unhealthy"
        assert "error" in result


# ──────────────────────────────────────────────────────────────────────────────
# get_application_health
# ──────────────────────────────────────────────────────────────────────────────

class TestGetApplicationHealth:

    def test_always_returns_healthy(self):
        """Application health always returns status='healthy'."""
        result = HealthChecker.get_application_health()
        assert result["status"] == "healthy"

    def test_version_key_present(self):
        """Result contains a 'version' key."""
        result = HealthChecker.get_application_health()
        assert "version" in result
        assert result["version"]  # non-empty

    def test_features_dict_present(self):
        """Result contains a 'features' dict."""
        result = HealthChecker.get_application_health()
        assert "features" in result
        assert isinstance(result["features"], dict)

    def test_features_includes_expected_keys(self):
        """features dict has authentication and booking_system flags."""
        result = HealthChecker.get_application_health()
        features = result["features"]
        assert "authentication" in features
        assert "booking_system" in features

    def test_debug_mode_key_present(self):
        """Result contains 'debug_mode' key."""
        result = HealthChecker.get_application_health()
        assert "debug_mode" in result

    def test_debug_mode_reflects_settings(self):
        """debug_mode matches settings.DEBUG."""
        from app.config import settings
        result = HealthChecker.get_application_health()
        assert result["debug_mode"] == settings.DEBUG


# ──────────────────────────────────────────────────────────────────────────────
# get_comprehensive_health
# ──────────────────────────────────────────────────────────────────────────────

class TestGetComprehensiveHealth:

    _WORKER_PATCH = "app.core.health.HealthChecker.get_worker_health"
    _WORKER_RESULT = {"status": "healthy", "redis": "healthy", "workers": [], "error": None}

    def _mock_components(self, db_status="healthy", sys_status="healthy", app_status="healthy"):
        """Return patch context where each component reports the given status."""
        db_result = {"status": db_status, "response_time_ms": 5.0, "details": {}, "error": None}
        sys_result = {"status": sys_status, "load_average": None, "disk": None}
        app_result = {"status": app_status, "version": "1.0.0", "features": {}}
        return db_result, sys_result, app_result

    def test_all_healthy_returns_healthy(self):
        """All components healthy → overall_status='healthy'."""
        db_r, sys_r, app_r = self._mock_components("healthy", "healthy", "healthy")
        with patch(_PATCH_SESSION) as mock_sl, \
             patch("app.core.health.HealthChecker.get_database_health",
                   new=AsyncMock(return_value=db_r)), \
             patch("app.core.health.HealthChecker.get_system_health",
                   return_value=sys_r), \
             patch("app.core.health.HealthChecker.get_application_health",
                   return_value=app_r), \
             patch(self._WORKER_PATCH, new=AsyncMock(return_value=self._WORKER_RESULT)):
            result = _run(HealthChecker.get_comprehensive_health())

        assert result["status"] == "healthy"

    def test_db_unhealthy_returns_unhealthy(self):
        """DB unhealthy → overall_status='unhealthy'."""
        db_r, sys_r, app_r = self._mock_components("unhealthy", "healthy", "healthy")
        with patch("app.core.health.HealthChecker.get_database_health",
                   new=AsyncMock(return_value=db_r)), \
             patch("app.core.health.HealthChecker.get_system_health",
                   return_value=sys_r), \
             patch("app.core.health.HealthChecker.get_application_health",
                   return_value=app_r), \
             patch(self._WORKER_PATCH, new=AsyncMock(return_value=self._WORKER_RESULT)):
            result = _run(HealthChecker.get_comprehensive_health())

        assert result["status"] == "unhealthy"

    def test_db_degraded_returns_degraded(self):
        """DB degraded, others healthy → overall_status='degraded'."""
        db_r, sys_r, app_r = self._mock_components("degraded", "healthy", "healthy")
        with patch("app.core.health.HealthChecker.get_database_health",
                   new=AsyncMock(return_value=db_r)), \
             patch("app.core.health.HealthChecker.get_system_health",
                   return_value=sys_r), \
             patch("app.core.health.HealthChecker.get_application_health",
                   return_value=app_r), \
             patch(self._WORKER_PATCH, new=AsyncMock(return_value=self._WORKER_RESULT)):
            result = _run(HealthChecker.get_comprehensive_health())

        assert result["status"] == "degraded"

    def test_unhealthy_takes_priority_over_degraded(self):
        """One unhealthy + one degraded → overall='unhealthy'."""
        db_r = {"status": "unhealthy"}
        sys_r = {"status": "degraded"}
        app_r = {"status": "healthy"}
        with patch("app.core.health.HealthChecker.get_database_health",
                   new=AsyncMock(return_value=db_r)), \
             patch("app.core.health.HealthChecker.get_system_health",
                   return_value=sys_r), \
             patch("app.core.health.HealthChecker.get_application_health",
                   return_value=app_r), \
             patch(self._WORKER_PATCH, new=AsyncMock(return_value=self._WORKER_RESULT)):
            result = _run(HealthChecker.get_comprehensive_health())

        assert result["status"] == "unhealthy"

    def test_summary_total_checks_is_4(self):
        """summary.total_checks == 4 (db + system + app + worker)."""
        db_r, sys_r, app_r = self._mock_components()
        with patch("app.core.health.HealthChecker.get_database_health",
                   new=AsyncMock(return_value=db_r)), \
             patch("app.core.health.HealthChecker.get_system_health",
                   return_value=sys_r), \
             patch("app.core.health.HealthChecker.get_application_health",
                   return_value=app_r), \
             patch(self._WORKER_PATCH, new=AsyncMock(return_value=self._WORKER_RESULT)):
            result = _run(HealthChecker.get_comprehensive_health())

        assert result["summary"]["total_checks"] == 4

    def test_summary_healthy_checks_count(self):
        """summary.healthy_checks = 3 when 3 of 4 are healthy (db degraded)."""
        db_r = {"status": "degraded"}
        sys_r = {"status": "healthy"}
        app_r = {"status": "healthy"}
        with patch("app.core.health.HealthChecker.get_database_health",
                   new=AsyncMock(return_value=db_r)), \
             patch("app.core.health.HealthChecker.get_system_health",
                   return_value=sys_r), \
             patch("app.core.health.HealthChecker.get_application_health",
                   return_value=app_r), \
             patch(self._WORKER_PATCH, new=AsyncMock(return_value=self._WORKER_RESULT)):
            result = _run(HealthChecker.get_comprehensive_health())

        assert result["summary"]["healthy_checks"] == 3
        assert result["summary"]["degraded_checks"] == 1

    def test_response_time_ms_present(self):
        """Result contains response_time_ms key."""
        db_r, sys_r, app_r = self._mock_components()
        with patch("app.core.health.HealthChecker.get_database_health",
                   new=AsyncMock(return_value=db_r)), \
             patch("app.core.health.HealthChecker.get_system_health",
                   return_value=sys_r), \
             patch("app.core.health.HealthChecker.get_application_health",
                   return_value=app_r), \
             patch(self._WORKER_PATCH, new=AsyncMock(return_value=self._WORKER_RESULT)):
            result = _run(HealthChecker.get_comprehensive_health())

        assert "response_time_ms" in result
        assert result["response_time_ms"] >= 0

    def test_checks_dict_has_all_component_keys(self):
        """checks dict contains database, system, application, and worker keys."""
        db_r, sys_r, app_r = self._mock_components()
        with patch("app.core.health.HealthChecker.get_database_health",
                   new=AsyncMock(return_value=db_r)), \
             patch("app.core.health.HealthChecker.get_system_health",
                   return_value=sys_r), \
             patch("app.core.health.HealthChecker.get_application_health",
                   return_value=app_r), \
             patch(self._WORKER_PATCH, new=AsyncMock(return_value=self._WORKER_RESULT)):
            result = _run(HealthChecker.get_comprehensive_health())

        assert "database" in result["checks"]
        assert "system" in result["checks"]
        assert "application" in result["checks"]
        assert "worker" in result["checks"]

    def test_timestamp_key_present(self):
        """Result contains ISO timestamp."""
        db_r, sys_r, app_r = self._mock_components()
        with patch("app.core.health.HealthChecker.get_database_health",
                   new=AsyncMock(return_value=db_r)), \
             patch("app.core.health.HealthChecker.get_system_health",
                   return_value=sys_r), \
             patch("app.core.health.HealthChecker.get_application_health",
                   return_value=app_r), \
             patch(self._WORKER_PATCH, new=AsyncMock(return_value=self._WORKER_RESULT)):
            result = _run(HealthChecker.get_comprehensive_health())

        assert "timestamp" in result
        assert result["timestamp"]  # non-empty string
