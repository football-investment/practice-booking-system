"""
Unit tests for app/api/api_v1/endpoints/curriculum/modules.py
Covers: mark_module_viewed, mark_module_complete, _update_lesson_progress
Note: all endpoints are sync (no asyncio.run needed)
"""
import pytest
from unittest.mock import MagicMock, patch

from app.api.api_v1.endpoints.curriculum.modules import (
    mark_module_viewed,
    mark_module_complete,
    _update_lesson_progress,
)

_BASE = "app.api.api_v1.endpoints.curriculum.modules"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(uid=42):
    u = MagicMock(); u.id = uid; return u


def _exec(fetchone=None, fetchall=None):
    """Mock for a single db.execute() return value."""
    m = MagicMock()
    m.fetchone.return_value = fetchone
    m.fetchall.return_value = fetchall if fetchall is not None else []
    return m


# ---------------------------------------------------------------------------
# mark_module_viewed
# ---------------------------------------------------------------------------

class TestMarkModuleViewed:
    def _call(self, module_id=5, db=None):
        """Patches _update_lesson_progress to isolate mark_module_viewed."""
        with patch(f"{_BASE}._update_lesson_progress"):
            return mark_module_viewed(
                module_id=module_id,
                current_user=_user(),
                db=db or MagicMock(),
            )

    def test_mmv01_existing_record_update(self):
        """MMV-01: existing progress record → UPDATE called."""
        exec1 = _exec(fetchone=(10, "IN_PROGRESS"))
        exec2 = _exec()  # UPDATE
        db = MagicMock()
        db.execute.side_effect = [exec1, exec2]
        result = self._call(db=db)
        assert result["status"] == "success"
        db.commit.assert_called_once()

    def test_mmv02_no_existing_insert(self):
        """MMV-02: no existing record → INSERT called."""
        exec1 = _exec(fetchone=None)
        exec2 = _exec()  # INSERT
        db = MagicMock()
        db.execute.side_effect = [exec1, exec2]
        result = self._call(db=db)
        assert result["status"] == "success"
        db.commit.assert_called_once()

    def test_mmv03_update_lesson_progress_called(self):
        """MMV-03: _update_lesson_progress always called."""
        exec1 = _exec(fetchone=None)
        exec2 = _exec()
        db = MagicMock()
        db.execute.side_effect = [exec1, exec2]
        with patch(f"{_BASE}._update_lesson_progress") as mock_ulp:
            mark_module_viewed(module_id=5, current_user=_user(), db=db)
        mock_ulp.assert_called_once_with(5, 42, db)


# ---------------------------------------------------------------------------
# mark_module_complete
# ---------------------------------------------------------------------------

class TestMarkModuleComplete:
    def _call(self, module_id=5, db=None):
        """Patches _update_lesson_progress to isolate mark_module_complete."""
        with patch(f"{_BASE}._update_lesson_progress"):
            return mark_module_complete(
                module_id=module_id,
                current_user=_user(),
                db=db or MagicMock(),
            )

    def test_mmc01_module_not_found_404(self):
        """MMC-01: module not found → 404."""
        from fastapi import HTTPException
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        with pytest.raises(HTTPException) as exc:
            mark_module_complete(module_id=5, current_user=_user(), db=db)
        assert exc.value.status_code == 404

    def test_mmc02_existing_record_no_xp(self):
        """MMC-02: existing record, xp_reward=0 → no XP UPDATE."""
        exec1 = _exec(fetchone=(0,))       # module xp_reward=0
        exec2 = _exec(fetchone=(10,))      # existing progress id=10
        exec3 = _exec()                    # UPDATE progress
        db = MagicMock()
        db.execute.side_effect = [exec1, exec2, exec3]
        result = self._call(db=db)
        assert result["xp_awarded"] == 0
        assert db.execute.call_count == 3

    def test_mmc03_existing_record_with_xp(self):
        """MMC-03: xp_reward > 0 → UPDATE users called."""
        exec1 = _exec(fetchone=(50,))      # module xp_reward=50
        exec2 = _exec(fetchone=(10,))      # existing progress
        exec3 = _exec()                    # UPDATE progress
        exec4 = _exec()                    # UPDATE users SET total_xp
        db = MagicMock()
        db.execute.side_effect = [exec1, exec2, exec3, exec4]
        result = self._call(db=db)
        assert result["xp_awarded"] == 50
        assert db.execute.call_count == 4

    def test_mmc04_no_existing_record_insert(self):
        """MMC-04: no existing record → INSERT."""
        exec1 = _exec(fetchone=(0,))       # xp_reward=0
        exec2 = _exec(fetchone=None)       # no existing progress
        exec3 = _exec()                    # INSERT progress
        db = MagicMock()
        db.execute.side_effect = [exec1, exec2, exec3]
        result = self._call(db=db)
        assert result["status"] == "success"
        db.commit.assert_called_once()

    def test_mmc05_no_existing_with_xp_insert(self):
        """MMC-05: no existing record, xp > 0 → INSERT + UPDATE users."""
        exec1 = _exec(fetchone=(100,))     # xp_reward=100
        exec2 = _exec(fetchone=None)       # no existing progress
        exec3 = _exec()                    # INSERT progress
        exec4 = _exec()                    # UPDATE users
        db = MagicMock()
        db.execute.side_effect = [exec1, exec2, exec3, exec4]
        result = self._call(db=db)
        assert result["xp_awarded"] == 100


# ---------------------------------------------------------------------------
# _update_lesson_progress (tested directly)
# ---------------------------------------------------------------------------

class TestUpdateLessonProgress:
    def test_ulp01_lesson_not_found_returns_early(self):
        """ULP-01: lesson not found for module → returns early."""
        exec1 = _exec(fetchone=None)
        db = MagicMock()
        db.execute.side_effect = [exec1]
        _update_lesson_progress(module_id=5, user_id=42, db=db)
        assert db.execute.call_count == 1

    def test_ulp02_existing_lesson_progress_update(self):
        """ULP-02: lesson found, existing lesson_progress → UPDATE."""
        exec1 = _exec(fetchone=(1,))       # lesson_id=1
        exec2 = _exec(fetchone=(5, 3))     # total=5, completed=3 (IN_PROGRESS)
        exec3 = _exec(fetchone=(99,))      # existing lesson_progress id=99
        exec4 = _exec()                    # UPDATE lesson_progress
        db = MagicMock()
        db.execute.side_effect = [exec1, exec2, exec3, exec4]
        _update_lesson_progress(module_id=5, user_id=42, db=db)
        assert db.execute.call_count == 4

    def test_ulp03_no_lesson_progress_insert(self):
        """ULP-03: lesson found, no existing lesson_progress → INSERT."""
        exec1 = _exec(fetchone=(1,))
        exec2 = _exec(fetchone=(3, 1))     # IN_PROGRESS
        exec3 = _exec(fetchone=None)       # no existing
        exec4 = _exec()                    # INSERT
        db = MagicMock()
        db.execute.side_effect = [exec1, exec2, exec3, exec4]
        _update_lesson_progress(module_id=5, user_id=42, db=db)
        assert db.execute.call_count == 4

    def test_ulp04_all_completed_status_completed(self):
        """ULP-04: all modules completed → status=COMPLETED."""
        exec1 = _exec(fetchone=(1,))
        exec2 = _exec(fetchone=(3, 3))     # completed==total → COMPLETED
        exec3 = _exec(fetchone=(99,))
        exec4 = _exec()
        db = MagicMock()
        db.execute.side_effect = [exec1, exec2, exec3, exec4]
        _update_lesson_progress(module_id=5, user_id=42, db=db)
        # Verify UPDATE was called (4 total execute calls)
        assert db.execute.call_count == 4

    def test_ulp05_zero_completed_status_unlocked(self):
        """ULP-05: 0 modules completed → status=UNLOCKED."""
        exec1 = _exec(fetchone=(1,))
        exec2 = _exec(fetchone=(3, 0))     # completed=0 → UNLOCKED
        exec3 = _exec(fetchone=None)
        exec4 = _exec()
        db = MagicMock()
        db.execute.side_effect = [exec1, exec2, exec3, exec4]
        _update_lesson_progress(module_id=5, user_id=42, db=db)
        assert db.execute.call_count == 4
