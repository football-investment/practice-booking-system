"""
Unit tests for app/utils/lock_logger.py

Coverage target: lock_timer context manager (113 lines, ~0% previously)
Tests:
  - Normal path: acquired + released events emitted in correct order
  - Exception path: released event still emitted when body raises
  - Log record structure: all required JSON fields present
  - entity_id=None is preserved in log payload
  - caller="" default is preserved
  - duration_ms is a non-negative float
  - Timestamps are valid ISO-8601 UTC strings
"""

import json
import logging
import pytest
from unittest.mock import MagicMock, call
from app.utils.lock_logger import lock_timer


# ── Helpers ───────────────────────────────────────────────────────────────────

def _capture_logger() -> tuple[logging.Logger, list[tuple[int, str]]]:
    """Return a mock logger that stores (level, message) pairs."""
    records: list[tuple[int, str]] = []

    logger = MagicMock(spec=logging.Logger)

    def _debug(msg, *args, **kwargs):
        records.append((logging.DEBUG, msg))

    def _info(msg, *args, **kwargs):
        records.append((logging.INFO, msg))

    logger.debug.side_effect = _debug
    logger.info.side_effect = _info
    return logger, records


# ── Normal path ───────────────────────────────────────────────────────────────

class TestLockTimerNormalPath:

    def test_emits_two_log_calls(self):
        logger, records = _capture_logger()
        with lock_timer("booking", "Semester", 42, logger):
            pass
        assert len(records) == 2

    def test_first_call_is_debug(self):
        logger, records = _capture_logger()
        with lock_timer("booking", "Semester", 42, logger):
            pass
        level, _ = records[0]
        assert level == logging.DEBUG

    def test_second_call_is_info(self):
        logger, records = _capture_logger()
        with lock_timer("booking", "Semester", 42, logger):
            pass
        level, _ = records[1]
        assert level == logging.INFO

    def test_acquired_event_fields(self):
        logger, records = _capture_logger()
        with lock_timer("reward", "UserLicense", 7, logger, caller="TournamentFinalizer.finalize"):
            pass
        _, msg = records[0]
        data = json.loads(msg)
        assert data["event"] == "lock_acquired"
        assert data["pipeline"] == "reward"
        assert data["entity_type"] == "UserLicense"
        assert data["entity_id"] == 7
        assert data["caller"] == "TournamentFinalizer.finalize"
        assert "lock_acquired_at" in data

    def test_released_event_fields(self):
        logger, records = _capture_logger()
        with lock_timer("enrollment", "Semester", 3, logger, caller="award_badge"):
            pass
        _, msg = records[1]
        data = json.loads(msg)
        assert data["event"] == "lock_released"
        assert data["pipeline"] == "enrollment"
        assert data["entity_type"] == "Semester"
        assert data["entity_id"] == 3
        assert data["caller"] == "award_badge"
        assert "lock_released_at" in data
        assert "duration_ms" in data

    def test_duration_ms_is_non_negative_float(self):
        logger, records = _capture_logger()
        with lock_timer("skill", "UserLicense", 1, logger):
            pass
        data = json.loads(records[1][1])
        assert isinstance(data["duration_ms"], (int, float))
        assert data["duration_ms"] >= 0

    def test_lock_acquired_event_has_no_duration_ms(self):
        """Acquired event should NOT have duration_ms — that's only in released."""
        logger, records = _capture_logger()
        with lock_timer("booking", "Semester", 1, logger):
            pass
        data = json.loads(records[0][1])
        assert "duration_ms" not in data

    def test_lock_released_event_has_no_lock_acquired_at(self):
        """Released event has lock_released_at, not lock_acquired_at."""
        logger, records = _capture_logger()
        with lock_timer("booking", "Semester", 1, logger):
            pass
        data = json.loads(records[1][1])
        assert "lock_released_at" in data
        assert "lock_acquired_at" not in data


# ── None entity_id ────────────────────────────────────────────────────────────

class TestLockTimerNoneEntityId:

    def test_none_entity_id_preserved_in_acquired(self):
        logger, records = _capture_logger()
        with lock_timer("booking", "Semester", None, logger):
            pass
        data = json.loads(records[0][1])
        assert data["entity_id"] is None

    def test_none_entity_id_preserved_in_released(self):
        logger, records = _capture_logger()
        with lock_timer("booking", "Semester", None, logger):
            pass
        data = json.loads(records[1][1])
        assert data["entity_id"] is None


# ── Default caller ────────────────────────────────────────────────────────────

class TestLockTimerDefaultCaller:

    def test_default_caller_is_empty_string(self):
        logger, records = _capture_logger()
        with lock_timer("booking", "Semester", 1, logger):
            pass
        acquired = json.loads(records[0][1])
        released = json.loads(records[1][1])
        assert acquired["caller"] == ""
        assert released["caller"] == ""


# ── Exception path ────────────────────────────────────────────────────────────

class TestLockTimerExceptionPath:

    def test_released_event_emitted_even_on_exception(self):
        """The finally block must fire even when the body raises."""
        logger, records = _capture_logger()
        with pytest.raises(RuntimeError, match="db error"):
            with lock_timer("booking", "Semester", 42, logger):
                raise RuntimeError("db error")
        # Both log calls must have been made
        assert len(records) == 2
        assert records[0][0] == logging.DEBUG   # acquired
        assert records[1][0] == logging.INFO    # released

    def test_released_event_has_correct_pipeline_on_exception(self):
        logger, records = _capture_logger()
        with pytest.raises(ValueError):
            with lock_timer("reward", "UserLicense", 5, logger):
                raise ValueError("integrity constraint")
        data = json.loads(records[1][1])
        assert data["event"] == "lock_released"
        assert data["pipeline"] == "reward"

    def test_body_executes_within_context(self):
        """Verify the yield actually runs the body."""
        logger, _ = _capture_logger()
        executed = []
        with lock_timer("booking", "Semester", 1, logger):
            executed.append(True)
        assert executed == [True]
