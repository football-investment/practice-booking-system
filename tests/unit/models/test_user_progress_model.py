"""
Unit tests for app/models/user_progress.py

Covers UserTrackProgress and UserModuleProgress branch targets:

UserTrackProgress:
  calculate_completion_percentage():
    - empty module_progresses → 0.0
    - non-empty but track has 0 modules → 0.0
    - normal calculation
  is_ready_for_certificate property:
    - status != COMPLETED → False (short-circuit)
    - completion_percentage < 100 → False
    - certificate_id already set → False
    - all conditions met → True
  duration_days property:
    - started_at is None → 0
    - completed_at set → uses it
    - completed_at is None → uses utcnow() (ongoing)

UserModuleProgress:
  complete(grade):
    - grade is not None → stores grade
    - grade is None → grade stays unset
  duration_hours property:
    - started_at is None → 0.0
    - completed_at set → uses it
    - completed_at is None → uses utcnow() (ongoing)
  is_passed property:
    - grade is None → False
    - grade < 60 → False
    - grade >= 60 → True
  grade_letter property:
    - grade is None → "N/A"
    - grade >= 90 → "A"
    - grade >= 80 → "B"
    - grade >= 70 → "C"
    - grade >= 60 → "D"
    - grade < 60 → "F"
"""

import pytest
import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.models.user_progress import (
    UserTrackProgress,
    UserModuleProgress,
    TrackProgressStatus,
    ModuleProgressStatus,
)


# ---------------------------------------------------------------------------
# UserTrackProgress helpers
# ---------------------------------------------------------------------------

def _utp(**overrides):
    """Transient UserTrackProgress with safe defaults."""
    t = UserTrackProgress()
    t.module_progresses = []
    t.track = MagicMock()
    t.track.modules = []
    t.status = TrackProgressStatus.ENROLLED
    t.completion_percentage = 0.0
    t.certificate_id = None
    t.started_at = None
    t.completed_at = None
    for k, v in overrides.items():
        setattr(t, k, v)
    return t


# ============================================================================
# UserTrackProgress.calculate_completion_percentage()
# ============================================================================

class TestCalculateCompletionPercentage:

    def test_empty_module_progresses_returns_zero(self):
        t = _utp(module_progresses=[])
        assert t.calculate_completion_percentage() == 0.0

    def test_zero_total_modules_returns_zero(self):
        t = _utp(module_progresses=[MagicMock()])
        t.track.modules = []  # track has no modules despite progress records
        assert t.calculate_completion_percentage() == 0.0

    def test_one_of_two_completed(self):
        mp_done = MagicMock(status=ModuleProgressStatus.COMPLETED)
        mp_pending = MagicMock(status=ModuleProgressStatus.IN_PROGRESS)
        t = _utp(module_progresses=[mp_done, mp_pending])
        t.track.modules = [MagicMock(), MagicMock()]
        result = t.calculate_completion_percentage()
        assert result == 50.0

    def test_all_completed(self):
        mp1 = MagicMock(status=ModuleProgressStatus.COMPLETED)
        mp2 = MagicMock(status=ModuleProgressStatus.COMPLETED)
        t = _utp(module_progresses=[mp1, mp2])
        t.track.modules = [MagicMock(), MagicMock()]
        result = t.calculate_completion_percentage()
        assert result == 100.0
        assert t.completion_percentage == 100.0


# ============================================================================
# UserTrackProgress.is_ready_for_certificate property
# ============================================================================

class TestIsReadyForCertificate:

    def test_not_ready_status_not_completed(self):
        t = _utp(
            status=TrackProgressStatus.ACTIVE,
            completion_percentage=100.0,
            certificate_id=None,
        )
        assert t.is_ready_for_certificate is False

    def test_not_ready_percentage_below_100(self):
        t = _utp(
            status=TrackProgressStatus.COMPLETED,
            completion_percentage=90.0,
            certificate_id=None,
        )
        assert t.is_ready_for_certificate is False

    def test_not_ready_already_has_certificate(self):
        t = _utp(
            status=TrackProgressStatus.COMPLETED,
            completion_percentage=100.0,
            certificate_id=uuid.uuid4(),
        )
        assert t.is_ready_for_certificate is False

    def test_ready_when_all_conditions_met(self):
        t = _utp(
            status=TrackProgressStatus.COMPLETED,
            completion_percentage=100.0,
            certificate_id=None,
        )
        assert t.is_ready_for_certificate is True


# ============================================================================
# UserTrackProgress.duration_days property
# ============================================================================

class TestDurationDays:

    def test_not_started_returns_zero(self):
        t = _utp(started_at=None)
        assert t.duration_days == 0

    def test_with_completed_at(self):
        t = _utp(
            started_at=datetime(2024, 1, 1),
            completed_at=datetime(2024, 1, 11),
        )
        assert t.duration_days == 10

    def test_ongoing_uses_utcnow(self):
        t = _utp(
            started_at=datetime(2024, 1, 1),
            completed_at=None,
        )
        # Result is positive (started in the past)
        assert t.duration_days >= 0


# ---------------------------------------------------------------------------
# UserModuleProgress helpers
# ---------------------------------------------------------------------------

def _ump(**overrides):
    """Transient UserModuleProgress with safe defaults."""
    m = UserModuleProgress()
    m.grade = None
    m.status = ModuleProgressStatus.NOT_STARTED
    m.started_at = None
    m.completed_at = None
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


# ============================================================================
# UserModuleProgress.complete()
# ============================================================================

class TestModuleComplete:

    def test_complete_with_grade_stores_grade(self):
        m = _ump()
        m.complete(grade=85.0)
        assert m.grade == 85.0
        assert m.status == ModuleProgressStatus.COMPLETED

    def test_complete_without_grade_leaves_grade_unset(self):
        m = _ump()
        m.complete(grade=None)
        assert m.grade is None  # not set
        assert m.status == ModuleProgressStatus.COMPLETED


# ============================================================================
# UserModuleProgress.duration_hours property
# ============================================================================

class TestDurationHours:

    def test_not_started_returns_zero(self):
        m = _ump(started_at=None)
        assert m.duration_hours == 0.0

    def test_with_completed_at(self):
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 12, 0, 0)
        m = _ump(started_at=start, completed_at=end)
        assert m.duration_hours == 2.0

    def test_ongoing_uses_utcnow(self):
        m = _ump(
            started_at=datetime(2024, 1, 1, 10, 0, 0),
            completed_at=None,
        )
        assert m.duration_hours >= 0.0


# ============================================================================
# UserModuleProgress.is_passed property
# ============================================================================

class TestIsPassed:

    def test_grade_none_not_passed(self):
        assert _ump(grade=None).is_passed is False

    def test_grade_below_60_not_passed(self):
        assert _ump(grade=59.9).is_passed is False

    def test_grade_exactly_60_is_passed(self):
        assert _ump(grade=60.0).is_passed is True

    def test_grade_above_60_is_passed(self):
        assert _ump(grade=85.0).is_passed is True


# ============================================================================
# UserModuleProgress.grade_letter property
# ============================================================================

class TestGradeLetter:

    def test_none_grade_returns_na(self):
        assert _ump(grade=None).grade_letter == "N/A"

    def test_90_and_above_returns_a(self):
        assert _ump(grade=90.0).grade_letter == "A"
        assert _ump(grade=100.0).grade_letter == "A"

    def test_80_to_89_returns_b(self):
        assert _ump(grade=80.0).grade_letter == "B"
        assert _ump(grade=89.9).grade_letter == "B"

    def test_70_to_79_returns_c(self):
        assert _ump(grade=70.0).grade_letter == "C"
        assert _ump(grade=79.9).grade_letter == "C"

    def test_60_to_69_returns_d(self):
        assert _ump(grade=60.0).grade_letter == "D"
        assert _ump(grade=69.9).grade_letter == "D"

    def test_below_60_returns_f(self):
        assert _ump(grade=59.9).grade_letter == "F"
        assert _ump(grade=0.0).grade_letter == "F"
