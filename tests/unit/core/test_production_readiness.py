"""
Unit tests — production readiness (PR-01 through PR-09)
========================================================

Tests
-----
  PR-01  DB_POOL_SIZE / DB_MAX_OVERFLOW / DB_POOL_RECYCLE settings exist with
         positive defaults
  PR-02  GRACEFUL_SHUTDOWN_TIMEOUT setting exists and is > 0
  PR-03  CELERY_BROKER_CONNECTION_MAX_RETRIES setting exists and is > 0
  PR-04  database.py engine is created with settings-based pool_size / max_overflow
  PR-05  stop_scheduler() returns immediately when scheduler is None
  PR-06  stop_scheduler() logs warning and force-stops when timeout exceeded
  PR-07  stop_scheduler() succeeds cleanly when scheduler shuts down in time
  PR-08  Celery config includes broker_connection_retry_on_startup=True
  PR-09  Celery config includes broker_transport_options with socket timeouts
"""
from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_scheduler_mock(shutdown_delay: float = 0.0) -> MagicMock:
    """Return an APScheduler mock whose shutdown() sleeps for shutdown_delay seconds."""
    import time

    mock = MagicMock()

    def _fake_shutdown(wait: bool = True) -> None:
        if wait and shutdown_delay > 0:
            time.sleep(shutdown_delay)

    mock.shutdown.side_effect = _fake_shutdown
    return mock


# ── Settings tests ────────────────────────────────────────────────────────────

class TestProductionSettings:

    def test_pr01_pool_size_settings_are_positive(self):
        """PR-01: DB pool settings exist in config and have positive default values."""
        from app.config import settings
        assert settings.DB_POOL_SIZE > 0
        assert settings.DB_MAX_OVERFLOW > 0
        assert settings.DB_POOL_RECYCLE > 0

    def test_pr02_graceful_shutdown_timeout_is_positive(self):
        """PR-02: GRACEFUL_SHUTDOWN_TIMEOUT exists and is > 0."""
        from app.config import settings
        assert settings.GRACEFUL_SHUTDOWN_TIMEOUT > 0

    def test_pr03_celery_max_retries_is_positive(self):
        """PR-03: CELERY_BROKER_CONNECTION_MAX_RETRIES exists and is > 0."""
        from app.config import settings
        assert settings.CELERY_BROKER_CONNECTION_MAX_RETRIES > 0


# ── Database engine pool tests ────────────────────────────────────────────────

class TestDatabaseEnginePool:

    def test_pr04_engine_pool_max_overflow_matches_settings(self):
        """PR-04: SQLAlchemy engine max_overflow reflects the settings value."""
        from app.database import engine
        from app.config import settings
        # _max_overflow is stable across SQLAlchemy 1.4 and 2.x
        assert engine.pool._max_overflow == settings.DB_MAX_OVERFLOW  # type: ignore[attr-defined]

    def test_pr04b_pool_settings_are_positive(self):
        """PR-04b: DB pool settings are positive (engine created with valid config)."""
        from app.config import settings
        # Verify pool settings in config (the engine is created from these values)
        assert settings.DB_POOL_SIZE > 0
        assert settings.DB_MAX_OVERFLOW > 0
        assert settings.DB_POOL_RECYCLE > 0


# ── stop_scheduler() tests ────────────────────────────────────────────────────

class TestStopScheduler:

    def test_pr05_stop_scheduler_no_op_when_none(self, caplog):
        """PR-05: stop_scheduler() returns immediately (no error) when scheduler is None."""
        import logging
        import app.background.scheduler as sched_module

        original = sched_module.scheduler
        sched_module.scheduler = None
        try:
            with caplog.at_level(logging.WARNING, logger="app.background.scheduler"):
                from app.background.scheduler import stop_scheduler
                stop_scheduler()
        finally:
            sched_module.scheduler = original

    def test_pr07_stop_scheduler_clean_shutdown(self):
        """PR-07: stop_scheduler() sets scheduler to None after clean shutdown."""
        import app.background.scheduler as sched_module

        mock_sched = _make_scheduler_mock(shutdown_delay=0.0)
        original = sched_module.scheduler
        sched_module.scheduler = mock_sched
        try:
            from app.background.scheduler import stop_scheduler
            stop_scheduler(timeout=5.0)
            assert sched_module.scheduler is None
            mock_sched.shutdown.assert_called_once_with(wait=True)
        finally:
            sched_module.scheduler = original

    def test_pr06_stop_scheduler_force_stops_on_timeout(self, caplog):
        """PR-06: stop_scheduler() logs a warning and calls shutdown(wait=False) on timeout."""
        import logging
        import app.background.scheduler as sched_module

        # Scheduler that takes 2 s to shut down — longer than our 0.05 s timeout
        mock_sched = _make_scheduler_mock(shutdown_delay=2.0)
        original = sched_module.scheduler
        sched_module.scheduler = mock_sched
        try:
            with caplog.at_level(logging.WARNING, logger="app.background.scheduler"):
                from app.background.scheduler import stop_scheduler
                stop_scheduler(timeout=0.05)
        finally:
            sched_module.scheduler = original

        # Warning should have been logged
        assert any("timeout" in r.getMessage().lower() or "not stop" in r.getMessage().lower()
                   for r in caplog.records), f"No timeout warning found in: {[r.getMessage() for r in caplog.records]}"

        # Force shutdown (wait=False) must have been called as fallback
        calls = [str(c) for c in mock_sched.shutdown.call_args_list]
        assert any("wait=False" in c for c in calls), f"shutdown(wait=False) not called: {calls}"


# ── Celery configuration tests ────────────────────────────────────────────────

class TestCeleryConfig:

    def test_pr08_celery_broker_retry_on_startup_enabled(self):
        """PR-08: Celery is configured to retry broker connection on worker startup."""
        from app.celery_app import celery_app
        assert celery_app.conf.broker_connection_retry_on_startup is True

    def test_pr09_celery_broker_transport_options_have_socket_timeouts(self):
        """PR-09: Celery broker_transport_options include socket_timeout and socket_connect_timeout."""
        from app.celery_app import celery_app
        opts = celery_app.conf.broker_transport_options or {}
        assert "socket_timeout" in opts, f"socket_timeout missing from {opts}"
        assert "socket_connect_timeout" in opts, f"socket_connect_timeout missing from {opts}"
        assert opts["socket_timeout"] > 0
        assert opts["socket_connect_timeout"] > 0

    def test_pr08b_celery_max_retries_matches_settings(self):
        """PR-08b: Celery broker_connection_max_retries matches settings."""
        from app.celery_app import celery_app
        from app.config import settings
        assert celery_app.conf.broker_connection_max_retries == settings.CELERY_BROKER_CONNECTION_MAX_RETRIES
