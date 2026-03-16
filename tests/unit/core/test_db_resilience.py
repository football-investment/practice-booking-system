"""
Unit tests — database connection resilience (app/database.py)
=============================================================

Tests
-----
  DB-01  wait_for_db() returns immediately when the DB is reachable
  DB-02  wait_for_db() retries on transient failure and succeeds on later attempt
  DB-03  wait_for_db() raises RuntimeError after max_retries exhausted
  DB-04  _connect_args includes connect_timeout from settings
  DB-05  DB_STATEMENT_TIMEOUT_MS=0 → options key absent from _connect_args
  DB-06  wait_for_db() uses DB_STARTUP_RETRIES / DB_STARTUP_RETRY_DELAY defaults
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError


# Helper: build a context-manager mock that executes SELECT 1 successfully.
def _ok_conn() -> MagicMock:
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn


class TestWaitForDb:

    def test_db01_succeeds_immediately(self):
        """DB-01: wait_for_db() returns without error when the DB is immediately reachable."""
        from app.database import wait_for_db

        with patch("app.database.engine.connect", return_value=_ok_conn()):
            wait_for_db(max_retries=3, delay_seconds=0)

    def test_db02_retries_on_transient_failure(self):
        """DB-02: wait_for_db() retries after a transient failure and returns on success."""
        from app.database import wait_for_db

        call_count = 0

        def _connect():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OperationalError("conn", None, Exception("transient"))
            return _ok_conn()

        with patch("app.database.engine.connect", side_effect=_connect):
            with patch("time.sleep"):  # prevent actual sleeping in unit tests
                wait_for_db(max_retries=3, delay_seconds=0.01)

        assert call_count == 2

    def test_db03_raises_after_max_retries(self):
        """DB-03: wait_for_db() raises RuntimeError when all attempts are exhausted."""
        from app.database import wait_for_db

        err = OperationalError("conn", None, Exception("db down"))
        with patch("app.database.engine.connect", side_effect=err):
            with patch("time.sleep"):
                with pytest.raises(RuntimeError, match="Database unavailable"):
                    wait_for_db(max_retries=3, delay_seconds=0.01)

    def test_db06_defaults_come_from_settings(self):
        """DB-06: wait_for_db() uses DB_STARTUP_RETRIES and DB_STARTUP_RETRY_DELAY when no args given."""
        from app.database import wait_for_db
        from app.config import settings

        call_count = 0

        def _always_fail():
            nonlocal call_count
            call_count += 1
            raise OperationalError("conn", None, Exception("down"))

        with patch("app.database.engine.connect", side_effect=_always_fail):
            with patch("time.sleep"):
                with pytest.raises(RuntimeError):
                    wait_for_db()  # uses settings defaults

        assert call_count == settings.DB_STARTUP_RETRIES


class TestEngineConnectArgs:

    def test_db04_connect_args_include_timeout(self):
        """DB-04: _connect_args includes connect_timeout from settings."""
        from app.database import _connect_args
        from app.config import settings

        assert "connect_timeout" in _connect_args
        assert _connect_args["connect_timeout"] == settings.DB_CONNECT_TIMEOUT
        assert _connect_args["connect_timeout"] > 0

    def test_db05_no_options_when_statement_timeout_disabled(self):
        """DB-05: When DB_STATEMENT_TIMEOUT_MS=0, the options key is absent."""
        from app.config import settings

        # In the test environment DB_STATEMENT_TIMEOUT_MS defaults to 0 (disabled).
        # The options key should not be present in _connect_args.
        if settings.DB_STATEMENT_TIMEOUT_MS == 0:
            from app.database import _connect_args
            assert "options" not in _connect_args
        else:
            # If overridden in env, verify the format is correct.
            from app.database import _connect_args
            assert "options" in _connect_args
            assert "statement_timeout" in _connect_args["options"]
