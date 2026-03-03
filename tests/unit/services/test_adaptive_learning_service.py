"""
Unit tests for app/services/adaptive_learning.py (AdaptiveLearningService)

Covers:
  Pure helper methods (no DB):
    _calculate_performance_trend — few questions, high/low/neutral success rate
    _adjust_target_difficulty    — correct+high-trend, incorrect+low-trend, small adjustments
    _is_session_time_expired     — no start time, expired, not expired
    _get_session_time_remaining  — no start time, expired, near-full remaining

  DB-dependent methods (MagicMock db):
    get_user_learning_analytics  — no performances (zero stats), with performances
    _calculate_adaptive_xp       — incorrect answer (consolation), correct with/without metadata
    _get_mastery_update          — no performance record, performance record exists

  Additional DB-dependent methods (MagicMock db):
    start_adaptive_session       — creates session object, calls db.add/commit/refresh
    _calculate_target_difficulty — high/low/neutral success rate adjustments
    _update_user_question_performance — no existing performance (create), existing (update)
    _update_question_metadata    — no existing metadata (create), existing (update)
    end_session                  — session not found (returns {}), session found (returns stats)
    record_answer                — session not found path
"""
import pytest
import math
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.services.adaptive_learning import AdaptiveLearningService
from app.models.quiz import QuizCategory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc():
    """Return (service, mock_db)."""
    db = MagicMock()
    return AdaptiveLearningService(db), db


def _q(db, first=None, all_=None):
    q = MagicMock()
    q.filter.return_value = q
    q.join.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    db.query.return_value = q
    return q


def _mock_session(presented=5, correct=3, trend=0.0, start_time=None, time_limit=None):
    s = MagicMock()
    s.questions_presented = presented
    s.questions_correct = correct
    s.performance_trend = trend
    s.session_start_time = start_time
    s.session_time_limit_seconds = time_limit
    return s


# ===========================================================================
# _calculate_performance_trend
# ===========================================================================

@pytest.mark.unit
class TestCalculatePerformanceTrend:
    def test_few_questions_returns_current_trend(self):
        svc, _ = _svc()
        session = _mock_session(presented=2, correct=2, trend=0.3)
        result = svc._calculate_performance_trend(session)
        assert result == 0.3  # unchanged when < 3 questions

    def test_high_success_rate_increases_trend(self):
        svc, _ = _svc()
        # 4/5 = 0.80 > 0.70 → increase by 0.1
        session = _mock_session(presented=5, correct=4, trend=0.2)
        result = svc._calculate_performance_trend(session)
        assert result == min(1.0, 0.2 + 0.1)

    def test_high_trend_clamped_at_one(self):
        svc, _ = _svc()
        # Already at 0.95, high success → min(1.0, 0.95+0.1) = 1.0
        session = _mock_session(presented=10, correct=9, trend=0.95)
        result = svc._calculate_performance_trend(session)
        assert result == 1.0

    def test_low_success_rate_decreases_trend(self):
        svc, _ = _svc()
        # 2/5 = 0.40 < 0.50 → decrease by 0.1
        session = _mock_session(presented=5, correct=2, trend=0.1)
        result = svc._calculate_performance_trend(session)
        assert result == max(-1.0, 0.1 - 0.1)

    def test_low_trend_clamped_at_neg_one(self):
        svc, _ = _svc()
        # At -0.95, low success → max(-1.0, -0.95 - 0.1) = -1.0
        session = _mock_session(presented=5, correct=1, trend=-0.95)
        result = svc._calculate_performance_trend(session)
        assert result == -1.0

    def test_neutral_success_rate_decays_trend(self):
        svc, _ = _svc()
        # 3/5 = 0.60, between 0.50 and 0.70 → trend * 0.9
        session = _mock_session(presented=5, correct=3, trend=0.5)
        result = svc._calculate_performance_trend(session)
        assert abs(result - 0.5 * 0.9) < 1e-9

    def test_exactly_three_questions_triggers_calculation(self):
        svc, _ = _svc()
        # 3 questions, 2 correct = 0.667 → neutral range
        session = _mock_session(presented=3, correct=2, trend=0.2)
        result = svc._calculate_performance_trend(session)
        assert result == 0.2 * 0.9


# ===========================================================================
# _adjust_target_difficulty
# ===========================================================================

@pytest.mark.unit
class TestAdjustTargetDifficulty:
    def test_correct_with_high_trend_increases_difficulty(self):
        svc, _ = _svc()
        result = svc._adjust_target_difficulty(0.5, is_correct=True, trend=0.8)
        assert result == min(0.9, 0.5 + 0.05)

    def test_correct_difficulty_clamped_at_0_9(self):
        svc, _ = _svc()
        result = svc._adjust_target_difficulty(0.88, is_correct=True, trend=0.9)
        assert result == 0.9

    def test_incorrect_with_low_trend_decreases_difficulty(self):
        svc, _ = _svc()
        result = svc._adjust_target_difficulty(0.5, is_correct=False, trend=-0.8)
        assert result == max(0.1, 0.5 - 0.05)

    def test_incorrect_difficulty_clamped_at_0_1(self):
        svc, _ = _svc()
        result = svc._adjust_target_difficulty(0.12, is_correct=False, trend=-0.9)
        assert result == 0.1

    def test_correct_with_neutral_trend_small_increase(self):
        svc, _ = _svc()
        result = svc._adjust_target_difficulty(0.5, is_correct=True, trend=0.3)
        assert abs(result - (0.5 + 0.05 * 0.5)) < 1e-9

    def test_incorrect_with_neutral_trend_small_decrease(self):
        svc, _ = _svc()
        result = svc._adjust_target_difficulty(0.5, is_correct=False, trend=0.0)
        assert abs(result - (0.5 - 0.05 * 0.5)) < 1e-9


# ===========================================================================
# _is_session_time_expired
# ===========================================================================

@pytest.mark.unit
class TestIsSessionTimeExpired:
    def test_no_start_time_returns_false(self):
        svc, _ = _svc()
        session = _mock_session(start_time=None, time_limit=300)
        assert svc._is_session_time_expired(session) is False

    def test_no_time_limit_returns_false(self):
        svc, _ = _svc()
        start = datetime.now(timezone.utc) - timedelta(seconds=600)
        session = _mock_session(start_time=start, time_limit=None)
        assert svc._is_session_time_expired(session) is False

    def test_expired_session_returns_true(self):
        svc, _ = _svc()
        start = datetime.now(timezone.utc) - timedelta(seconds=400)
        session = _mock_session(start_time=start, time_limit=300)  # 300s limit, 400s elapsed
        assert svc._is_session_time_expired(session) is True

    def test_not_expired_returns_false(self):
        svc, _ = _svc()
        start = datetime.now(timezone.utc) - timedelta(seconds=100)
        session = _mock_session(start_time=start, time_limit=300)  # 300s limit, 100s elapsed
        assert svc._is_session_time_expired(session) is False

    def test_exactly_at_limit_returns_true(self):
        svc, _ = _svc()
        # elapsed ≈ limit (exact boundary, elapsed >= limit)
        start = datetime.now(timezone.utc) - timedelta(seconds=300)
        session = _mock_session(start_time=start, time_limit=300)
        assert svc._is_session_time_expired(session) is True


# ===========================================================================
# _get_session_time_remaining
# ===========================================================================

@pytest.mark.unit
class TestGetSessionTimeRemaining:
    def test_no_start_time_returns_zero(self):
        svc, _ = _svc()
        session = _mock_session(start_time=None, time_limit=300)
        assert svc._get_session_time_remaining(session) == 0

    def test_no_time_limit_returns_zero(self):
        svc, _ = _svc()
        start = datetime.now(timezone.utc)
        session = _mock_session(start_time=start, time_limit=None)
        assert svc._get_session_time_remaining(session) == 0

    def test_expired_returns_zero(self):
        svc, _ = _svc()
        start = datetime.now(timezone.utc) - timedelta(seconds=400)
        session = _mock_session(start_time=start, time_limit=300)
        assert svc._get_session_time_remaining(session) == 0

    def test_remaining_time_is_positive(self):
        svc, _ = _svc()
        start = datetime.now(timezone.utc) - timedelta(seconds=100)
        session = _mock_session(start_time=start, time_limit=300)
        remaining = svc._get_session_time_remaining(session)
        assert remaining > 0
        assert remaining <= 200  # should be ~200s remaining


# ===========================================================================
# get_user_learning_analytics
# ===========================================================================

@pytest.mark.unit
class TestGetUserLearningAnalytics:
    def test_no_performances_returns_zeros(self):
        svc, db = _svc()
        _q(db, all_=[])
        result = svc.get_user_learning_analytics(user_id=42)
        assert result["total_questions_attempted"] == 0
        assert result["total_attempts"] == 0
        assert result["overall_success_rate"] == 0.0
        assert result["mastery_level"] == 0.0
        assert result["learning_velocity"] == 0.0
        assert result["recommended_difficulty"] == 0.5

    def test_with_performances_calculates_stats(self):
        svc, db = _svc()
        p1 = MagicMock()
        p1.total_attempts = 5
        p1.correct_attempts = 4
        p1.mastery_level = 0.8
        p1.last_attempted_at = datetime.now(timezone.utc) - timedelta(days=1)  # recent
        p1.success_rate = 0.8
        _q(db, all_=[p1])
        result = svc.get_user_learning_analytics(user_id=42)
        assert result["total_questions_attempted"] == 1
        assert result["total_attempts"] == 5
        assert abs(result["overall_success_rate"] - 4/5) < 0.01
        assert result["mastery_level"] == 0.8


# ===========================================================================
# _calculate_adaptive_xp
# ===========================================================================

@pytest.mark.unit
class TestCalculateAdaptiveXp:
    def test_incorrect_answer_returns_consolation_xp(self):
        svc, db = _svc()
        result = svc._calculate_adaptive_xp(question_id=1, is_correct=False, time_spent=30.0)
        assert result == 5

    def test_correct_no_metadata_returns_base_xp(self):
        svc, db = _svc()
        _q(db, first=None)  # No metadata → base XP only
        result = svc._calculate_adaptive_xp(question_id=1, is_correct=True, time_spent=30.0)
        assert result == 25  # base_xp with no difficulty bonus or time bonus

    def test_correct_with_metadata_difficulty_bonus(self):
        svc, db = _svc()
        meta = MagicMock()
        meta.estimated_difficulty = 0.8  # 80% difficulty
        meta.average_time_seconds = None  # no time bonus
        _q(db, first=meta)
        result = svc._calculate_adaptive_xp(question_id=1, is_correct=True, time_spent=30.0)
        # difficulty_bonus = int(0.8 * 20) = 16
        assert result == 25 + 16

    def test_correct_with_time_bonus(self):
        svc, db = _svc()
        meta = MagicMock()
        meta.estimated_difficulty = 0.0  # no difficulty bonus
        meta.average_time_seconds = 60.0  # avg is 60s, user took 20s → faster
        _q(db, first=meta)
        result = svc._calculate_adaptive_xp(question_id=1, is_correct=True, time_spent=20.0)
        # time_ratio = 60/20 = 3.0, time_bonus = min(0.5, max(0, (3.0-1)*0.25)) = min(0.5, 0.5) = 0.5
        # result = int(25 * 1.5) = 37
        assert result == 37


# ===========================================================================
# _get_mastery_update
# ===========================================================================

@pytest.mark.unit
class TestGetMasteryUpdate:
    def test_no_performance_returns_zero_dict(self):
        svc, db = _svc()
        _q(db, first=None)
        result = svc._get_mastery_update(user_id=42, question_id=1)
        assert result == {"mastery_level": 0.0, "success_rate": 0.0, "next_review": None}

    def test_with_performance_returns_values(self):
        svc, db = _svc()
        perf = MagicMock()
        perf.mastery_level = 0.7
        perf.success_rate = 0.75
        perf.next_review_at = None  # no scheduled review
        _q(db, first=perf)
        result = svc._get_mastery_update(user_id=42, question_id=1)
        assert result["mastery_level"] == 0.7
        assert result["success_rate"] == 0.75
        assert result["next_review"] is None

    def test_with_performance_and_review_date(self):
        svc, db = _svc()
        review_time = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
        perf = MagicMock()
        perf.mastery_level = 0.5
        perf.success_rate = 0.5
        perf.next_review_at = review_time
        _q(db, first=perf)
        result = svc._get_mastery_update(user_id=42, question_id=1)
        assert result["next_review"] == review_time.isoformat()


# ===========================================================================
# start_adaptive_session
# ===========================================================================

@pytest.mark.unit
class TestStartAdaptiveSession:
    def test_creates_session_and_commits(self):
        svc, db = _svc()
        with patch.object(svc, "_calculate_target_difficulty", return_value=0.5):
            result = svc.start_adaptive_session(user_id=42, category=QuizCategory.GENERAL)
        # Service should call db.add, db.commit, db.refresh
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_uses_provided_session_duration(self):
        svc, db = _svc()
        with patch.object(svc, "_calculate_target_difficulty", return_value=0.5):
            svc.start_adaptive_session(user_id=2, category=QuizCategory.GENERAL,
                                       session_duration_seconds=600)
        # The session object passed to db.add should have the right duration
        added_session = db.add.call_args[0][0]
        assert added_session.session_time_limit_seconds == 600


# ===========================================================================
# _calculate_target_difficulty
# ===========================================================================

@pytest.mark.unit
class TestCalculateTargetDifficulty:
    def _analytics(self, success_rate, velocity=0.0):
        return {
            "overall_success_rate": success_rate,
            "learning_velocity": velocity
        }

    def test_high_success_rate_increases_difficulty(self):
        svc, db = _svc()
        with patch.object(svc, "get_user_learning_analytics",
                          return_value=self._analytics(0.9)):
            result = svc._calculate_target_difficulty(user_id=42, category=QuizCategory.GENERAL)
        assert result == max(0.1, min(0.9, 0.5 + 0.2))  # 0.7

    def test_low_success_rate_decreases_difficulty(self):
        svc, db = _svc()
        with patch.object(svc, "get_user_learning_analytics",
                          return_value=self._analytics(0.4)):
            result = svc._calculate_target_difficulty(user_id=42, category=QuizCategory.GENERAL)
        assert result == max(0.1, min(0.9, 0.5 - 0.2))  # 0.3

    def test_middle_success_rate_returns_base(self):
        svc, db = _svc()
        with patch.object(svc, "get_user_learning_analytics",
                          return_value=self._analytics(0.7, velocity=0.0)):
            result = svc._calculate_target_difficulty(user_id=42, category=QuizCategory.GENERAL)
        assert result == 0.5

    def test_learning_velocity_adjusts_base(self):
        svc, db = _svc()
        with patch.object(svc, "get_user_learning_analytics",
                          return_value=self._analytics(0.7, velocity=1.0)):
            result = svc._calculate_target_difficulty(user_id=42, category=QuizCategory.GENERAL)
        # base=0.5, velocity=1.0 → 0.5 + 0.1 = 0.6
        assert abs(result - 0.6) < 1e-9


# ===========================================================================
# _update_user_question_performance
# ===========================================================================

@pytest.mark.unit
class TestUpdateUserQuestionPerformance:
    def test_no_existing_performance_creates_new(self):
        svc, db = _svc()
        _q(db, first=None)  # No existing record
        svc._update_user_question_performance(
            user_id=42, question_id=1, is_correct=True, time_spent=30.0
        )
        db.add.assert_called_once()

    def test_existing_performance_increments_attempts(self):
        svc, db = _svc()
        perf = MagicMock()
        perf.total_attempts = 5
        perf.correct_attempts = 3
        perf.mastery_level = 0.6
        _q(db, first=perf)
        svc._update_user_question_performance(
            user_id=42, question_id=1, is_correct=True, time_spent=30.0
        )
        # total_attempts should be incremented
        assert perf.total_attempts == 6
        assert perf.correct_attempts == 4
        db.add.assert_not_called()

    def test_incorrect_answer_does_not_increment_correct(self):
        svc, db = _svc()
        perf = MagicMock()
        perf.total_attempts = 3
        perf.correct_attempts = 1
        perf.mastery_level = 0.2
        _q(db, first=perf)
        svc._update_user_question_performance(
            user_id=42, question_id=1, is_correct=False, time_spent=20.0
        )
        assert perf.total_attempts == 4
        assert perf.correct_attempts == 1  # unchanged
        assert perf.last_attempt_correct is False


# ===========================================================================
# _update_question_metadata
# ===========================================================================

@pytest.mark.unit
class TestUpdateQuestionMetadata:
    def test_no_existing_metadata_creates_new(self):
        svc, db = _svc()
        _q(db, first=None)
        svc._update_question_metadata(question_id=1, is_correct=True, time_spent=30.0)
        db.add.assert_called_once()

    def test_existing_metadata_updates_success_rate(self):
        svc, db = _svc()
        meta = MagicMock()
        meta.global_success_rate = 0.6
        meta.average_time_seconds = 60.0
        meta.estimated_difficulty = 0.5
        _q(db, first=meta)
        svc._update_question_metadata(question_id=1, is_correct=True, time_spent=30.0)
        # Success rate and avg time should be updated (exponential moving average)
        assert meta.global_success_rate != 0.6  # changed
        assert meta.last_analytics_update is not None
        db.add.assert_not_called()


# ===========================================================================
# end_session
# ===========================================================================

@pytest.mark.unit
class TestEndSession:
    def test_session_not_found_returns_empty_dict(self):
        svc, db = _svc()
        _q(db, first=None)
        result = svc.end_session(session_id=99)
        assert result == {}

    def test_session_found_returns_stats(self):
        svc, db = _svc()
        session = MagicMock()
        session.questions_presented = 10
        session.questions_correct = 8
        session.xp_earned = 100
        session.performance_trend = 0.5
        session.target_difficulty = 0.7
        session.user_id = 1
        _q(db, first=session)
        # Patch the lazy GamificationService import
        mock_gam = MagicMock()
        mock_stats = MagicMock()
        mock_stats.total_xp = 0
        mock_gam.return_value.get_or_create_user_stats.return_value = mock_stats
        # GamificationService is lazy-imported inside end_session; patch at source module
        with patch("app.services.gamification.GamificationService", mock_gam):
            result = svc.end_session(session_id=1)
        assert result["questions_answered"] == 10
        assert result["correct_answers"] == 8
        assert abs(result["success_rate"] - 0.8) < 1e-9
        assert result["xp_earned"] == 100


# ===========================================================================
# record_answer — session not found path
# ===========================================================================

@pytest.mark.unit
class TestRecordAnswer:
    def test_session_not_found_still_returns_dict(self):
        svc, db = _svc()
        # session query returns None
        _q(db, first=None)
        with patch.object(svc, "_update_user_question_performance"):
            with patch.object(svc, "_update_question_metadata"):
                with patch.object(svc, "_calculate_adaptive_xp", return_value=5):
                    with patch.object(svc, "_get_mastery_update",
                                      return_value={"mastery_level": 0.0,
                                                    "success_rate": 0.0,
                                                    "next_review": None}):
                        result = svc.record_answer(
                            user_id=42, session_id=99, question_id=1,
                            is_correct=False, time_spent_seconds=30.0
                        )
        assert result["xp_earned"] == 5
        assert result["new_target_difficulty"] is None
        assert result["performance_trend"] is None
