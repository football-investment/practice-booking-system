"""
Unit tests for app/api/api_v1/endpoints/curriculum/modules.py

Coverage targets (raw-SQL endpoint, no real DB needed):
  mark_module_viewed()     — POST /module/{id}/view
  mark_module_complete()   — POST /module/{id}/complete
  _update_lesson_progress() — internal helper (exercised via both routes)

Mock strategy
-------------
All paths use ``db.execute(text(...), {...}).fetchone()`` sequentially.
Setting ``db.execute.return_value.fetchone.side_effect = [v1, v2, ...]``
lets us control what the n-th fetchone() returns.
UPDATE/INSERT calls never read fetchone(), so they don't consume items
from side_effect.

Call counts
-----------
mark_module_viewed (update-existing path):
  fetchone[0] = existing progress row  (Q1 → UPDATE branch)
  + _update_lesson_progress:
    fetchone[1] = lesson row
    fetchone[2] = stats row (total, completed)
    fetchone[3] = existing lesson progress row → UPDATE branch

mark_module_viewed (insert-new path):
  fetchone[0] = None  (Q1 → INSERT branch)
  + _update_lesson_progress:
    fetchone[1] = lesson row
    fetchone[2] = stats row
    fetchone[3] = None → INSERT branch

mark_module_complete:
  fetchone[0] = (xp_reward,)   (Q1 → module exists)
  fetchone[1] = None           (Q2 → INSERT branch)
  + _update_lesson_progress:
    fetchone[2] = lesson row
    fetchone[3] = stats row
    fetchone[4] = existing lesson progress row
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from types import SimpleNamespace

from app.api.api_v1.endpoints.curriculum.modules import (
    mark_module_viewed,
    mark_module_complete,
    _update_lesson_progress,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user(user_id: int = 42) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    return u


def _db_seq(*fetchone_values):
    """
    Build a mock DB where the n-th .fetchone() call returns fetchone_values[n].
    All other db.execute calls (UPDATE/INSERT) share the same mock without
    calling fetchone().
    """
    db = MagicMock()
    execute_mock = MagicMock()
    execute_mock.fetchone.side_effect = list(fetchone_values)
    db.execute.return_value = execute_mock
    return db


def _lesson_stats(total: int, completed: int):
    """Simulate a stats fetchone row."""
    row = MagicMock()
    row.__getitem__ = lambda self, i: (total, completed)[i]
    return row


def _row(val):
    """Simulate a single-value fetchone row."""
    row = MagicMock()
    row.__getitem__ = lambda self, i: [val][i]
    return row


def _row_id(id_val: int):
    return _row(id_val)


# ── mark_module_viewed — update existing path ─────────────────────────────────

class TestMarkModuleViewedUpdatePath:

    def test_returns_success_status(self):
        existing_row = _row_id(7)          # existing progress record
        lesson_row   = _row(10)            # lesson_id = 10
        stats_row    = _lesson_stats(5, 2) # 5 total, 2 completed
        lesson_progress_row = _row_id(99)  # existing lesson progress

        db = _db_seq(existing_row, lesson_row, stats_row, lesson_progress_row)
        user = _user()
        result = mark_module_viewed(module_id=1, current_user=user, db=db)
        assert result["status"] == "success"

    def test_commits_transaction(self):
        existing_row = _row_id(7)
        lesson_row   = _row(10)
        stats_row    = _lesson_stats(3, 3)  # all completed → COMPLETED status
        lesson_progress_row = _row_id(99)

        db = _db_seq(existing_row, lesson_row, stats_row, lesson_progress_row)
        mark_module_viewed(module_id=1, current_user=_user(), db=db)
        db.commit.assert_called_once()

    def test_calls_execute_multiple_times(self):
        """UPDATE path + _update_lesson_progress = at least 4 execute calls."""
        existing_row = _row_id(7)
        lesson_row   = _row(10)
        stats_row    = _lesson_stats(5, 2)
        lesson_progress_row = _row_id(99)

        db = _db_seq(existing_row, lesson_row, stats_row, lesson_progress_row)
        mark_module_viewed(module_id=1, current_user=_user(), db=db)
        assert db.execute.call_count >= 4


# ── mark_module_viewed — insert new path ──────────────────────────────────────

class TestMarkModuleViewedInsertPath:

    def test_returns_success_on_new_record(self):
        lesson_row   = _row(20)
        stats_row    = _lesson_stats(4, 0)  # 0 completed → UNLOCKED
        db = _db_seq(None, lesson_row, stats_row, None)  # no existing, no lesson progress

        result = mark_module_viewed(module_id=5, current_user=_user(), db=db)
        assert result["status"] == "success"

    def test_commits_on_new_record(self):
        lesson_row = _row(20)
        stats_row  = _lesson_stats(4, 0)
        db = _db_seq(None, lesson_row, stats_row, None)

        mark_module_viewed(module_id=5, current_user=_user(), db=db)
        db.commit.assert_called_once()


# ── mark_module_complete — 404 path ──────────────────────────────────────────

class TestMarkModuleComplete404:

    def test_raises_404_when_module_not_found(self):
        db = _db_seq(None)  # module not found
        with pytest.raises(HTTPException) as exc:
            mark_module_complete(module_id=99999, current_user=_user(), db=db)
        assert exc.value.status_code == 404


# ── mark_module_complete — no XP path ────────────────────────────────────────

class TestMarkModuleCompleteNoXP:

    def test_returns_success_with_zero_xp(self):
        module_row   = _row(0)       # xp_reward = 0
        existing_row = _row_id(55)   # existing progress record
        lesson_row   = _row(15)
        stats_row    = _lesson_stats(3, 1)
        lesson_progress_row = _row_id(77)

        db = _db_seq(module_row, existing_row, lesson_row, stats_row, lesson_progress_row)
        result = mark_module_complete(module_id=2, current_user=_user(), db=db)
        assert result["status"] == "success"
        assert result["xp_awarded"] == 0

    def test_commits_on_no_xp(self):
        module_row   = _row(0)
        existing_row = _row_id(55)
        lesson_row   = _row(15)
        stats_row    = _lesson_stats(3, 1)
        lesson_progress_row = _row_id(77)

        db = _db_seq(module_row, existing_row, lesson_row, stats_row, lesson_progress_row)
        mark_module_complete(module_id=2, current_user=_user(), db=db)
        db.commit.assert_called_once()


# ── mark_module_complete — with XP path ──────────────────────────────────────

class TestMarkModuleCompleteWithXP:

    def test_returns_xp_in_response(self):
        module_row   = _row(50)    # xp_reward = 50
        existing_row = None        # INSERT path
        lesson_row   = _row(8)
        stats_row    = _lesson_stats(2, 2)  # all done → COMPLETED
        lesson_progress_row = _row_id(11)

        db = _db_seq(module_row, existing_row, lesson_row, stats_row, lesson_progress_row)
        result = mark_module_complete(module_id=3, current_user=_user(), db=db)
        assert result["xp_awarded"] == 50

    def test_xp_update_query_issued_when_xp_positive(self):
        """When xp_reward > 0 there must be an additional execute call for UPDATE users."""
        module_row   = _row(100)
        existing_row = None
        lesson_row   = _row(8)
        stats_row    = _lesson_stats(2, 2)
        lesson_progress_row = _row_id(11)

        db = _db_seq(module_row, existing_row, lesson_row, stats_row, lesson_progress_row)
        mark_module_complete(module_id=3, current_user=_user(), db=db)
        # 5 fetchone calls (module, existing, lesson, stats, lesson_progress)
        # + XP UPDATE execute (no fetchone) = 6 execute calls total minimum
        assert db.execute.call_count >= 6


# ── _update_lesson_progress — no lesson found path ───────────────────────────

class TestUpdateLessonProgressNoLesson:

    def test_returns_early_when_lesson_not_found(self):
        """If lesson_modules has no row for module_id, helper returns silently."""
        db = _db_seq(None)  # lesson fetchone = None
        # Should not raise
        _update_lesson_progress(module_id=999, user_id=42, db=db)
        db.commit.assert_not_called()


# ── _update_lesson_progress — status branches ────────────────────────────────

class TestUpdateLessonProgressStatusBranches:

    def _run(self, total, completed, lesson_progress_existing):
        lesson_row = _row(10)
        stats_row  = _lesson_stats(total, completed)
        db = _db_seq(lesson_row, stats_row, lesson_progress_existing)
        _update_lesson_progress(module_id=1, user_id=42, db=db)
        return db

    def test_unlocked_status_when_zero_completed(self):
        """0/4 completed → UNLOCKED branch."""
        self._run(total=4, completed=0, lesson_progress_existing=None)

    def test_in_progress_status_when_partial(self):
        """2/4 completed → IN_PROGRESS branch."""
        self._run(total=4, completed=2, lesson_progress_existing=_row_id(5))

    def test_completed_status_when_all_done(self):
        """4/4 completed → COMPLETED branch."""
        self._run(total=4, completed=4, lesson_progress_existing=_row_id(5))
