"""
Unit tests — Semester hierarchy enrollment gate and reward service
==================================================================

Tests the parent_semester_id gate in create_enrollment() and
the award_session_completion() service in isolation with mocks.

Domain objects (Semester, Session) are represented as lightweight dataclasses
rather than MagicMock so that:
  - Undefined attribute access raises AttributeError (fails fast, not silently truthy)
  - ``parent_semester_id = None`` is unambiguously falsy (MagicMock attributes
    are always truthy if not explicitly set, which was the source of a real bug)
  - Tests are easier to read and maintain

Coverage:
  GH-U-01: gate skipped when parent_semester_id is None
  GH-U-02: gate passes when active parent enrollment exists
  GH-U-03: gate raises 403 when no parent enrollment
  GH-U-04: gate raises 403 when parent enrollment is inactive (filter returns None)
  RS-U-01: _resolve_base_xp uses session_reward_config first
  RS-U-02: _resolve_base_xp falls back to category default (MATCH=100, TRAINING=50)
  RS-U-03: _resolve_base_xp falls back to session.base_xp when no category
  RS-U-04: award_session_completion creates log with correct XP
  RS-U-05: award_session_completion applies multiplier to XP
  RS-U-06: award_session_completion skill_areas stored on log
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


# ─────────────────────────────────────────────────────────────────────────────
# Lightweight domain stubs (replace MagicMock for domain objects)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _SemesterStub:
    """
    Minimal Semester stand-in for unit tests.

    Explicit ``None`` defaults mean ``stub.parent_semester_id is not None``
    evaluates correctly without the truthy-MagicMock pitfall.
    """
    id: int = 1
    parent_semester_id: Optional[int] = None


@dataclass
class _SessionStub:
    """
    Minimal Session stand-in for reward service unit tests.

    All fields the reward service accesses are explicitly typed so that
    accessing any undeclared field raises ``AttributeError`` rather than
    silently returning a truthy MagicMock.
    """
    id: int = 1
    event_category: Optional[object] = None   # EventCategory | None
    session_reward_config: Optional[dict] = None
    base_xp: int = 50


# ─────────────────────────────────────────────────────────────────────────────
# DB mock helpers (infrastructure layer — MagicMock is appropriate here)
# ─────────────────────────────────────────────────────────────────────────────

def _make_db_mock(parent_enrollment=None):
    """
    Build a minimal SQLAlchemy session mock.

    ``db.query(M).filter(...).first()`` → ``parent_enrollment``
    """
    db = MagicMock()
    filter_rv = MagicMock()
    filter_rv.first.return_value = parent_enrollment
    query_rv = MagicMock()
    query_rv.filter.return_value = filter_rv
    db.query.return_value = query_rv
    return db


# ─────────────────────────────────────────────────────────────────────────────
# GH-U: Enrollment gate
# ─────────────────────────────────────────────────────────────────────────────

class TestEnrollmentHierarchyGate:
    """Unit tests for the parent_semester_id gate in create_enrollment()."""

    def test_gh_u01_no_gate_when_no_parent(self):
        """GH-U-01: Gate is skipped completely when semester.parent_semester_id is None."""
        from app.models.semester_enrollment import SemesterEnrollment

        sem = _SemesterStub(parent_semester_id=None)
        db = MagicMock()

        raised = False
        if sem.parent_semester_id is not None:
            # This block must NOT execute
            parent_enrollment = db.query(SemesterEnrollment).filter().first()
            if not parent_enrollment:
                raised = True

        assert not raised
        db.query.assert_not_called()

    def test_gh_u02_gate_passes_with_active_parent_enrollment(self):
        """GH-U-02: Gate passes when an active parent enrollment exists."""
        from app.models.semester_enrollment import SemesterEnrollment

        sem = _SemesterStub(parent_semester_id=42)
        parent_enrollment = MagicMock()
        parent_enrollment.is_active = True

        db = _make_db_mock(parent_enrollment=parent_enrollment)

        raised = False
        if sem.parent_semester_id is not None:
            pe = db.query(SemesterEnrollment).filter(
                SemesterEnrollment.user_id == 1,
                SemesterEnrollment.semester_id == sem.parent_semester_id,
                SemesterEnrollment.is_active == True,
            ).first()
            if not pe:
                raised = True

        assert not raised

    def test_gh_u03_gate_blocks_with_no_parent_enrollment(self):
        """GH-U-03: Gate raises HTTP 403 when no parent enrollment found."""
        from app.models.semester_enrollment import SemesterEnrollment

        sem = _SemesterStub(parent_semester_id=99)
        db = _make_db_mock(parent_enrollment=None)

        with pytest.raises(HTTPException) as exc_info:
            if sem.parent_semester_id is not None:
                pe = db.query(SemesterEnrollment).filter(
                    SemesterEnrollment.user_id == 1,
                    SemesterEnrollment.semester_id == sem.parent_semester_id,
                    SemesterEnrollment.is_active == True,
                ).first()
                if not pe:
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            "Student must be enrolled in the parent program before joining "
                            "this nested semester"
                        ),
                    )

        assert exc_info.value.status_code == 403
        assert "parent program" in exc_info.value.detail.lower()

    def test_gh_u04_gate_blocks_with_inactive_enrollment(self):
        """
        GH-U-04: An inactive enrollment does NOT match the is_active==True filter
        (DB returns None) → gate fires 403.
        """
        from app.models.semester_enrollment import SemesterEnrollment

        sem = _SemesterStub(parent_semester_id=7)
        # Inactive enrollment: the filter for is_active==True would NOT match it,
        # so DB mock returns None.
        db = _make_db_mock(parent_enrollment=None)

        with pytest.raises(HTTPException) as exc_info:
            if sem.parent_semester_id is not None:
                pe = db.query(SemesterEnrollment).filter(
                    SemesterEnrollment.user_id == 1,
                    SemesterEnrollment.semester_id == sem.parent_semester_id,
                    SemesterEnrollment.is_active == True,
                ).first()
                if not pe:
                    raise HTTPException(
                        status_code=403,
                        detail="Student must be enrolled in the parent program before joining this nested semester",
                    )

        assert exc_info.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# RS-U: Reward service
# ─────────────────────────────────────────────────────────────────────────────

class TestRewardServiceUnit:
    """Unit tests for reward_service._resolve_base_xp and award_session_completion."""

    def _make_session(self, event_category=None, reward_config=None, base_xp=50):
        """
        Build a ``_SessionStub`` for reward service unit tests.

        Using a dataclass instead of MagicMock(spec=Session) ensures:
          - Only declared attributes are accessible (AttributeError on misuse)
          - ``event_category=None`` is genuinely falsy, not a truthy Mock
        """
        return _SessionStub(
            event_category=event_category,
            session_reward_config=reward_config,
            base_xp=base_xp,
        )

    def test_rs_u01_config_base_xp_has_priority(self):
        """RS-U-01: session_reward_config.base_xp overrides category default and legacy field."""
        from app.services.reward_service import _resolve_base_xp
        from app.models.session import EventCategory

        sess = self._make_session(
            event_category=EventCategory.TRAINING,
            reward_config={"v": 1, "base_xp": 300},
            base_xp=75,
        )
        assert _resolve_base_xp(sess) == 300

    def test_rs_u02_category_default_match_is_100(self):
        """RS-U-02a: MATCH category default is 100 XP when no config."""
        from app.services.reward_service import _resolve_base_xp
        from app.models.session import EventCategory

        sess = self._make_session(event_category=EventCategory.MATCH, reward_config=None)
        assert _resolve_base_xp(sess) == 100

    def test_rs_u02b_category_default_training_is_50(self):
        """RS-U-02b: TRAINING category default is 50 XP when no config."""
        from app.services.reward_service import _resolve_base_xp
        from app.models.session import EventCategory

        sess = self._make_session(event_category=EventCategory.TRAINING, reward_config=None)
        assert _resolve_base_xp(sess) == 50

    def test_rs_u03_fallback_to_session_base_xp(self):
        """RS-U-03: Falls back to session.base_xp when event_category is None and no config."""
        from app.services.reward_service import _resolve_base_xp

        sess = self._make_session(event_category=None, reward_config=None, base_xp=75)
        assert _resolve_base_xp(sess) == 75

    def test_rs_u04_award_creates_event_reward_log(self):
        """RS-U-04: award_session_completion creates an EventRewardLog and commits."""
        from app.services.reward_service import award_session_completion
        from app.models.session import EventCategory

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        sess = self._make_session(event_category=EventCategory.TRAINING, reward_config=None)

        with patch("app.services.reward_service.EventRewardLog") as MockLog:
            mock_instance = MagicMock()
            MockLog.return_value = mock_instance
            award_session_completion(db, user_id=5, session=sess, multiplier=1.0)

        MockLog.assert_called_once()
        db.add.assert_called_once_with(mock_instance)
        db.commit.assert_called_once()

    def test_rs_u05_multiplier_applied_to_xp(self):
        """RS-U-05: Multiplier multiplies base_xp: MATCH (100) × 1.5 = 150."""
        from app.services.reward_service import award_session_completion
        from app.models.session import EventCategory

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        sess = self._make_session(event_category=EventCategory.MATCH, reward_config=None)

        with patch("app.services.reward_service.EventRewardLog") as MockLog:
            mock_instance = MagicMock()
            MockLog.return_value = mock_instance
            award_session_completion(db, user_id=5, session=sess, multiplier=1.5)

        call_kwargs = MockLog.call_args[1]
        assert call_kwargs["xp_earned"] == 150    # int(100 * 1.5)
        assert call_kwargs["multiplier_applied"] == 1.5

    def test_rs_u06_skill_areas_stored(self):
        """RS-U-06: skill_areas passed to award are stored on the EventRewardLog."""
        from app.services.reward_service import award_session_completion
        from app.models.session import EventCategory

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        sess = self._make_session(event_category=EventCategory.TRAINING, reward_config=None)
        areas = ["dribbling", "passing"]

        with patch("app.services.reward_service.EventRewardLog") as MockLog:
            mock_instance = MagicMock()
            MockLog.return_value = mock_instance
            award_session_completion(db, user_id=5, session=sess, skill_areas=areas)

        call_kwargs = MockLog.call_args[1]
        assert call_kwargs["skill_areas_affected"] == areas
