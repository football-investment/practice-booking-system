"""
Unit Tests: badge_service

Coverage targets (pure service unit tests, DB fully mocked):
  award_achievement               — idempotency, creation, specialization_id scoping
  check_and_award_semester_achievements — threshold tiers (1/2/3/5 semesters),
                                          attendance gate, feedback gate
  check_newcomer_welcome          — 24-hour window, timezone-naive handling,
                                    user not found, already-awarded guard
  check_and_unlock_achievements   — action mismatch skip, already-unlocked skip,
                                    count/level/score/spec_count requirements,
                                    xp awarded on unlock, empty achievement list
  _check_achievement_requirements — all 5 requirement branches
  _get_user_action_count          — known action → audit query, unknown action → 0

NOTE: check_and_award_first_time_achievements, check_first_project_enrollment,
_check_quiz_enrollment_combo, and check_and_award_specialization_achievements
reference QuizAttempt / ProjectEnrollment / SpecializationProgress which are NOT
imported in badge_service.py — those functions raise NameError at runtime and are
excluded from this test suite (documented as technical debt).
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, call

from app.models.gamification import BadgeType
from app.models.audit_log import AuditAction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db():
    """Return a blank MagicMock DB."""
    return MagicMock()


def _mock_query(db, return_first=None, return_all=None, return_scalar=None):
    """
    Wire db.query(...).filter(...).first/all/scalar/count to return the given values.
    Works for a single query pattern per call.
    """
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.first.return_value = return_first
    q.all.return_value = return_all or []
    q.scalar.return_value = return_scalar
    q.count.return_value = 0
    db.query.return_value = q
    return q


def _make_achievement_model(id=1, code="TEST", name="Test Badge",
                            description="Desc", icon="⭐", is_active=True,
                            xp_reward=50, requirements=None):
    a = MagicMock()
    a.id = id
    a.code = code
    a.name = name
    a.description = description
    a.icon = icon
    a.is_active = is_active
    a.xp_reward = xp_reward
    a.requirements = requirements or {}
    return a


def _make_user_achievement(id=1, achievement_id=None, badge_type="returning_student"):
    ua = MagicMock()
    ua.id = id
    ua.achievement_id = achievement_id
    ua.badge_type = badge_type
    return ua


def _make_stats(semesters=0, attendance=0.0, bookings=0, feedback=0):
    s = MagicMock()
    s.semesters_participated = semesters
    s.attendance_rate = attendance
    s.total_bookings = bookings
    s.feedback_given = feedback
    return s


# ---------------------------------------------------------------------------
# award_achievement
# ---------------------------------------------------------------------------

class TestAwardAchievement:
    """Tests for award_achievement() idempotency and creation."""

    def test_existing_achievement_returned_without_db_write(self):
        from app.services.gamification.badge_service import award_achievement
        db = _db()
        existing = MagicMock()
        _mock_query(db, return_first=existing)

        result = award_achievement(
            db=db,
            user_id=42,
            badge_type=BadgeType.RETURNING_STUDENT,
            title="Title",
            description="Desc",
            icon="🔄",
        )

        assert result is existing
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_new_achievement_created_and_committed(self):
        from app.services.gamification.badge_service import award_achievement
        db = _db()
        _mock_query(db, return_first=None)

        result = award_achievement(
            db=db,
            user_id=42,
            badge_type=BadgeType.RETURNING_STUDENT,
            title="Returning Student",
            description="2 semesters",
            icon="🔄",
            semester_count=2,
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_specialization_id_included_in_uniqueness_check(self):
        """Two calls with different specialization_id must each query DB."""
        from app.services.gamification.badge_service import award_achievement
        db = _db()
        _mock_query(db, return_first=None)

        # First call — no existing
        award_achievement(db, 1, BadgeType.FIRST_LEVEL_UP, "T", "D", "⚽",
                          specialization_id="PLAYER")
        # Second call — no existing for COACH spec either
        award_achievement(db, 1, BadgeType.FIRST_LEVEL_UP, "T", "D", "⭐",
                          specialization_id="COACH")

        # Both should have resulted in db.add calls
        assert db.add.call_count == 2

    def test_idempotent_same_badge_same_spec(self):
        """Calling twice for same badge + spec returns existing on second call."""
        from app.services.gamification.badge_service import award_achievement
        db = _db()
        existing = MagicMock()

        # First call: no existing → creates
        db.query.return_value.filter.return_value.first.return_value = None
        award_achievement(db, 1, BadgeType.RETURNING_STUDENT, "T", "D", "🔄")

        # Second call: now existing
        db.query.return_value.filter.return_value.first.return_value = existing
        result = award_achievement(db, 1, BadgeType.RETURNING_STUDENT, "T", "D", "🔄")
        assert result is existing


# ---------------------------------------------------------------------------
# check_and_award_semester_achievements
# ---------------------------------------------------------------------------

class TestCheckAndAwardSemesterAchievements:

    def _run(self, semesters=0, attendance=0.0, bookings=0, feedback=0,
             existing_first=None):
        from app.services.gamification.badge_service import (
            check_and_award_semester_achievements,
        )
        db = _db()
        _mock_query(db, return_first=existing_first)
        stats = _make_stats(semesters, attendance, bookings, feedback)

        with patch("app.services.gamification.badge_service.calculate_user_stats",
                   return_value=stats):
            return check_and_award_semester_achievements(db, user_id=42)

    def test_one_semester_no_achievements(self):
        result = self._run(semesters=1)
        assert result == []

    def test_two_semesters_returning_student(self):
        result = self._run(semesters=2)
        # At least one achievement awarded
        assert len(result) >= 1

    def test_three_semesters_returning_and_veteran(self):
        result = self._run(semesters=3)
        assert len(result) >= 2   # RETURNING + VETERAN

    def test_five_semesters_all_three_semester_badges(self):
        result = self._run(semesters=5)
        assert len(result) >= 3   # RETURNING + VETERAN + MASTER

    def test_attendance_below_threshold_no_star(self):
        """79.9% and 10 bookings → no attendance badge."""
        result = self._run(semesters=0, attendance=79.9, bookings=10)
        assert len(result) == 0

    def test_attendance_above_but_insufficient_bookings_no_star(self):
        """80%+ but < 10 bookings → no attendance badge."""
        result = self._run(semesters=0, attendance=85.0, bookings=9)
        assert len(result) == 0

    def test_attendance_star_awarded_when_threshold_met(self):
        result = self._run(semesters=0, attendance=80.0, bookings=10)
        assert len(result) >= 1

    def test_feedback_below_threshold_no_badge(self):
        result = self._run(semesters=0, feedback=9)
        assert len(result) == 0

    def test_feedback_champion_at_threshold(self):
        result = self._run(semesters=0, feedback=10)
        assert len(result) >= 1

    def test_existing_achievement_not_duplicated(self):
        """award_achievement short-circuits when existing found → still in list."""
        existing = MagicMock()
        result = self._run(semesters=2, existing_first=existing)
        # Existing is returned, so at least one entry
        assert len(result) >= 1
        assert existing in result


# ---------------------------------------------------------------------------
# check_newcomer_welcome
# ---------------------------------------------------------------------------

class TestCheckNewcomerWelcome:

    def test_user_not_found_returns_empty(self):
        from app.services.gamification.badge_service import check_newcomer_welcome
        db = _db()
        _mock_query(db, return_first=None)   # user query returns None
        result = check_newcomer_welcome(db, user_id=999)
        assert result == []

    def test_user_created_over_24h_ago_no_award(self):
        from app.services.gamification.badge_service import check_newcomer_welcome
        db = _db()
        user = MagicMock()
        user.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        _mock_query(db, return_first=user)

        result = check_newcomer_welcome(db, user_id=42)
        assert result == []

    def test_user_created_within_24h_award_given(self):
        from app.services.gamification.badge_service import check_newcomer_welcome
        db = _db()
        user = MagicMock()
        user.created_at = datetime.now(timezone.utc) - timedelta(hours=1)

        call_count = [0]
        def first_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return user         # first query = user found
            return None             # second query = no existing achievement

        db.query.return_value.filter.return_value.first.side_effect = first_side_effect

        with patch("app.services.gamification.badge_service.award_xp"):
            result = check_newcomer_welcome(db, user_id=42)

        assert len(result) >= 1

    def test_timezone_naive_created_at_handled(self):
        """created_at without tzinfo is treated as UTC — should not raise."""
        from app.services.gamification.badge_service import check_newcomer_welcome
        db = _db()
        user = MagicMock()
        user.created_at = datetime.now() - timedelta(minutes=30)   # naive

        call_count = [0]
        def first_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return user
            return None

        db.query.return_value.filter.return_value.first.side_effect = first_side_effect

        with patch("app.services.gamification.badge_service.award_xp"):
            result = check_newcomer_welcome(db, user_id=42)

        assert len(result) >= 1

    def test_already_awarded_not_duplicated(self):
        """Existing NEWCOMER_WELCOME → award_achievement not called again."""
        from app.services.gamification.badge_service import check_newcomer_welcome
        db = _db()
        user = MagicMock()
        user.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        existing_welcome = MagicMock()

        call_count = [0]
        def first_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return user
            return existing_welcome   # already has welcome badge

        db.query.return_value.filter.return_value.first.side_effect = first_side_effect

        result = check_newcomer_welcome(db, user_id=42)
        # award_achievement returns existing → still returned
        assert len(result) == 0   # no new award created


# ---------------------------------------------------------------------------
# check_and_unlock_achievements
# ---------------------------------------------------------------------------

class TestCheckAndUnlockAchievements:

    def _run(self, achievements, user_achievements=None, trigger="login",
             context=None):
        from app.services.gamification.badge_service import check_and_unlock_achievements
        db = _db()

        call_count = [0]
        def query_side_effect(model):
            # Alternate between Achievement query and UserAchievement query
            q = MagicMock()
            q.filter.return_value = q
            call_count[0] += 1
            if call_count[0] == 1:
                # Achievement.is_active query
                q.all.return_value = achievements
            else:
                # UserAchievement query (existing)
                q.all.return_value = user_achievements or []
            return q

        db.query.side_effect = query_side_effect

        with patch("app.services.gamification.badge_service.award_xp"):
            return check_and_unlock_achievements(
                db, user_id=42, trigger_action=trigger, context=context or {})

    def test_no_active_achievements_returns_empty(self):
        result = self._run(achievements=[])
        assert result == []

    def test_already_unlocked_achievement_skipped(self):
        a = _make_achievement_model(id=5, requirements={})
        ua = _make_user_achievement(achievement_id=5)
        result = self._run(achievements=[a], user_achievements=[ua])
        assert result == []

    def test_action_mismatch_skips_achievement(self):
        a = _make_achievement_model(requirements={"action": "complete_quiz"})
        result = self._run(achievements=[a], trigger="login")
        assert result == []

    def test_action_match_triggers_unlock(self):
        a = _make_achievement_model(requirements={"action": "login"})
        result = self._run(achievements=[a], trigger="login")
        assert a in result

    def test_count_requirement_not_met_skips(self):
        a = _make_achievement_model(
            requirements={"action": "login", "count": 10})
        # Patch _get_user_action_count to return 5
        with patch("app.services.gamification.badge_service._get_user_action_count",
                   return_value=5):
            result = self._run(achievements=[a], trigger="login")
        assert result == []

    def test_count_requirement_met_unlocks(self):
        a = _make_achievement_model(
            requirements={"action": "login", "count": 5})
        with patch("app.services.gamification.badge_service._get_user_action_count",
                   return_value=5):
            result = self._run(achievements=[a], trigger="login")
        assert a in result

    def test_no_requirements_default_unlock(self):
        """Empty requirements dict → default True → unlock."""
        a = _make_achievement_model(requirements={})
        result = self._run(achievements=[a], trigger="any_trigger")
        assert a in result

    def test_xp_awarded_when_xp_reward_positive(self):
        from app.services.gamification.badge_service import check_and_unlock_achievements
        a = _make_achievement_model(xp_reward=100, requirements={})
        db = _db()

        call_count = [0]
        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value = q
            call_count[0] += 1
            q.all.return_value = [a] if call_count[0] == 1 else []
            return q

        db.query.side_effect = query_side_effect

        with patch("app.services.gamification.badge_service.award_xp") as mock_xp:
            check_and_unlock_achievements(db, user_id=42, trigger_action="login")
            mock_xp.assert_called_once_with(db, 1, 100, f"Achievement: {a.name}")

    def test_xp_not_awarded_when_xp_reward_zero(self):
        from app.services.gamification.badge_service import check_and_unlock_achievements
        a = _make_achievement_model(xp_reward=0, requirements={})
        db = _db()

        call_count = [0]
        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value = q
            call_count[0] += 1
            q.all.return_value = [a] if call_count[0] == 1 else []
            return q

        db.query.side_effect = query_side_effect

        with patch("app.services.gamification.badge_service.award_xp") as mock_xp:
            check_and_unlock_achievements(db, user_id=42, trigger_action="login")
            mock_xp.assert_not_called()

    def test_no_unlock_means_no_commit(self):
        from app.services.gamification.badge_service import check_and_unlock_achievements
        db = _db()

        call_count = [0]
        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value = q
            call_count[0] += 1
            q.all.return_value = [] if call_count[0] == 1 else []
            return q

        db.query.side_effect = query_side_effect
        check_and_unlock_achievements(db, user_id=42, trigger_action="login")
        db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# _check_achievement_requirements
# ---------------------------------------------------------------------------

class TestCheckAchievementRequirements:

    def _call(self, requirements, trigger="login", context=None,
              action_count=0, max_level=None, spec_count=None):
        from app.services.gamification.badge_service import _check_achievement_requirements
        db = _db()
        achievement = MagicMock()
        achievement.requirements = requirements

        # Wire DB scalar queries
        db.query.return_value.filter.return_value.scalar.return_value = (
            max_level if max_level is not None else spec_count
        )

        with patch("app.services.gamification.badge_service._get_user_action_count",
                   return_value=action_count):
            return _check_achievement_requirements(
                db, user_id=42, achievement=achievement,
                trigger_action=trigger, context=context or {})

    def test_no_requirements_returns_true(self):
        assert self._call({}) is True

    def test_action_mismatch_returns_false(self):
        assert self._call({"action": "complete_quiz"}, trigger="login") is False

    def test_action_match_no_other_requirement_returns_true(self):
        assert self._call({"action": "login"}, trigger="login") is True

    # count requirement
    def test_count_not_met(self):
        assert self._call({"count": 5}, trigger="login", action_count=4) is False

    def test_count_exactly_met(self):
        assert self._call({"count": 5}, trigger="login", action_count=5) is True

    def test_count_exceeded(self):
        assert self._call({"count": 5}, trigger="login", action_count=10) is True

    # level requirement — context branch
    def test_level_from_context(self):
        assert self._call({"level": 3}, context={"level": 3}) is True

    def test_level_from_context_mismatch(self):
        """Context level mismatch falls through to DB query."""
        assert self._call({"level": 5}, context={"level": 3}, max_level=5) is True

    def test_level_db_not_reached(self):
        assert self._call({"level": 5}, context={}, max_level=4) is False

    def test_level_db_null_returns_false(self):
        assert self._call({"level": 3}, context={}, max_level=None) is False

    # min_score requirement
    def test_min_score_met(self):
        assert self._call({"min_score": 80}, context={"score": 95}) is True

    def test_min_score_exactly_met(self):
        assert self._call({"min_score": 80}, context={"score": 80}) is True

    def test_min_score_not_met(self):
        assert self._call({"min_score": 80}, context={"score": 60}) is False

    def test_min_score_no_score_in_context(self):
        """Missing score key defaults to 0 → not met unless min_score is 0."""
        assert self._call({"min_score": 1}, context={}) is False

    # specialization_count requirement
    def test_specialization_count_met(self):
        assert self._call({"specialization_count": 2}, spec_count=2) is True

    def test_specialization_count_not_met(self):
        assert self._call({"specialization_count": 3}, spec_count=1) is False

    def test_specialization_count_null_returns_false(self):
        assert self._call({"specialization_count": 1}, spec_count=None) is False


# ---------------------------------------------------------------------------
# _get_user_action_count
# ---------------------------------------------------------------------------

class TestGetUserActionCount:

    def _call(self, action, audit_count=0):
        from app.services.gamification.badge_service import _get_user_action_count
        db = _db()
        db.query.return_value.filter.return_value.count.return_value = audit_count
        return _get_user_action_count(db, user_id=42, action=action)

    def test_unknown_action_returns_zero(self):
        assert self._call("nonexistent_action_xyz") == 0

    def test_login_mapped_to_audit_query(self):
        assert self._call("login", audit_count=5) == 5

    def test_complete_quiz_mapped(self):
        assert self._call("complete_quiz", audit_count=3) == 3

    def test_select_specialization_mapped(self):
        assert self._call("select_specialization", audit_count=1) == 1

    def test_license_earned_mapped(self):
        assert self._call("license_earned", audit_count=2) == 2

    def test_project_enroll_mapped(self):
        assert self._call("project_enroll", audit_count=7) == 7

    def test_project_complete_mapped(self):
        assert self._call("project_complete", audit_count=4) == 4

    def test_quiz_perfect_score_mapped(self):
        assert self._call("quiz_perfect_score", audit_count=1) == 1

    def test_zero_count_for_known_action(self):
        assert self._call("login", audit_count=0) == 0
