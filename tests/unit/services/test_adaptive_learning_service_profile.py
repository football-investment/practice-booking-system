"""
Sprint P3 — adaptive_learning_service.py
==========================================
Target: ≥80% stmt, ≥75% branch

Covers all methods of AdaptiveLearningService:
  _categorize_pace             — 4 branches (pure function)
  _calculate_quiz_average      — empty / 1 score / 3-score weighted
  _calculate_pace_score        — no data → 50.0 / with data (formula)
  _count_lessons_completed     — count / no result
  _calculate_avg_lesson_time   — avg / None avg
  _detect_content_preference   — VIDEO / TEXT / PRACTICE branches
  get_or_create_profile        — profile exists / missing → create
  update_profile_metrics       — full pipeline (5 helpers + UPDATE)
  _detect_burnout              — no result / below 600 / ≥ 600
  _find_weak_lessons           — empty / lesson list
  _suggest_next_lesson         — no result / no spec / spec+no lesson / next lesson
  _check_inactivity            — no result / active recently / 7+ days
  _suggest_practice            — no result / < 5 lessons / practice needed / enough exercises
  generate_recommendations     — cached (no refresh) / refresh all-empty / refresh with recs
  _save_recommendations        — empty list / with recs
  _format_recommendation       — row → dict
  dismiss_recommendation       — UPDATE + commit
  create_daily_snapshot        — full flow (mocked profile + today queries)
  get_performance_history      — empty / with rows
"""
import pytest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.adaptive_learning_service import AdaptiveLearningService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _svc(db=None) -> AdaptiveLearningService:
    if db is None:
        db = MagicMock()
    return AdaptiveLearningService(db)


def _row(**kwargs):
    """Minimal DB row substitute."""
    return SimpleNamespace(**kwargs)


def _db_one(row) -> MagicMock:
    """DB whose single execute().fetchone() returns `row`."""
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = row
    return db


def _db_all(rows) -> MagicMock:
    """DB whose single execute().fetchall() returns `rows`."""
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = rows
    return db


def _profile_row(user_id=42, pace=65.0, quiz_avg=75.0, pace_cat="FAST",
                 lessons=10, avg_time=15.0, pref="TEXT") -> SimpleNamespace:
    return _row(
        id=1, user_id=user_id,
        learning_pace=pace_cat,
        pace_score=pace,
        quiz_average_score=quiz_avg,
        lessons_completed_count=lessons,
        avg_time_per_lesson_minutes=avg_time,
        preferred_content_type=pref,
        last_activity_at=None,
        created_at=None,
        updated_at=None,
    )


# ── _categorize_pace (pure) ───────────────────────────────────────────────────

class TestCategorizePace:
    def setup_method(self):
        self.svc = _svc()

    def test_80_returns_accelerated(self):
        assert self.svc._categorize_pace(80) == "ACCELERATED"

    def test_100_returns_accelerated(self):
        assert self.svc._categorize_pace(100) == "ACCELERATED"

    def test_60_returns_fast(self):
        assert self.svc._categorize_pace(60) == "FAST"

    def test_79_returns_fast(self):
        assert self.svc._categorize_pace(79) == "FAST"

    def test_40_returns_medium(self):
        assert self.svc._categorize_pace(40) == "MEDIUM"

    def test_59_returns_medium(self):
        assert self.svc._categorize_pace(59) == "MEDIUM"

    def test_39_returns_slow(self):
        assert self.svc._categorize_pace(39) == "SLOW"

    def test_0_returns_slow(self):
        assert self.svc._categorize_pace(0) == "SLOW"


# ── _calculate_quiz_average ───────────────────────────────────────────────────

class TestCalculateQuizAverage:
    def test_empty_result_returns_zero(self):
        svc = _svc(_db_all([]))
        assert svc._calculate_quiz_average(42) == 0.0

    def test_single_score_returns_that_score(self):
        """Single score: weight=[0.4], weighted_sum/weight_sum = score."""
        svc = _svc(_db_all([_row(score=80.0)]))
        result = svc._calculate_quiz_average(42)
        assert abs(result - 80.0) < 0.01

    def test_three_scores_weighted_average(self):
        """weights=[0.4, 0.25, 0.2]; scores=[90, 70, 60].
        weighted_sum = 90*0.4 + 70*0.25 + 60*0.2 = 36 + 17.5 + 12 = 65.5
        weight_sum   = 0.85
        result       = 65.5 / 0.85 ≈ 77.06
        """
        rows = [_row(score=90.0), _row(score=70.0), _row(score=60.0)]
        svc = _svc(_db_all(rows))
        result = svc._calculate_quiz_average(42)
        assert abs(result - 65.5 / 0.85) < 0.01


# ── _calculate_pace_score ─────────────────────────────────────────────────────

class TestCalculatePaceScore:
    def test_no_result_returns_50(self):
        svc = _svc(_db_one(None))
        assert svc._calculate_pace_score(42) == 50.0

    def test_zero_lessons_returns_50(self):
        row = _row(lessons_completed=0, avg_quiz_score=0.0, active_days=0)
        svc = _svc(_db_one(row))
        assert svc._calculate_pace_score(42) == 50.0

    def test_with_data_returns_formula_value(self):
        """lessons=10, quiz=80, active_days=15
        lesson_velocity = min(10/30*100, 100) = 33.33
        consistency     = min(15/20*100, 100) = 75.0
        performance     = 80.0
        pace_score      = 33.33*0.4 + 75*0.3 + 80*0.3 ≈ 59.83
        """
        row = _row(lessons_completed=10, avg_quiz_score=80.0, active_days=15)
        svc = _svc(_db_one(row))
        result = svc._calculate_pace_score(42)
        expected = (10 / 30.0 * 100) * 0.4 + (15 / 20.0 * 100) * 0.3 + 80.0 * 0.3
        assert abs(result - expected) < 0.01

    def test_capped_at_100(self):
        """With massive numbers the score should be capped at 100."""
        row = _row(lessons_completed=100, avg_quiz_score=100.0, active_days=100)
        svc = _svc(_db_one(row))
        assert svc._calculate_pace_score(42) == 100.0


# ── _count_lessons_completed ──────────────────────────────────────────────────

class TestCountLessonsCompleted:
    def test_no_result_returns_zero(self):
        svc = _svc(_db_one(None))
        assert svc._count_lessons_completed(42) == 0

    def test_count_returned(self):
        svc = _svc(_db_one(_row(count=7)))
        assert svc._count_lessons_completed(42) == 7


# ── _calculate_avg_lesson_time ────────────────────────────────────────────────

class TestCalculateAvgLessonTime:
    def test_no_result_returns_zero(self):
        svc = _svc(_db_one(None))
        assert svc._calculate_avg_lesson_time(42) == 0.0

    def test_null_avg_time_returns_zero(self):
        svc = _svc(_db_one(_row(avg_time=None)))
        assert svc._calculate_avg_lesson_time(42) == 0.0

    def test_avg_time_returned_as_float(self):
        svc = _svc(_db_one(_row(avg_time=18.5)))
        assert svc._calculate_avg_lesson_time(42) == 18.5


# ── _detect_content_preference ────────────────────────────────────────────────

class TestDetectContentPreference:
    def test_avg_below_10_returns_video(self):
        svc = _svc()
        with patch.object(svc, "_calculate_avg_lesson_time", return_value=5.0):
            assert svc._detect_content_preference(42) == "VIDEO"

    def test_avg_exactly_10_returns_text(self):
        svc = _svc()
        with patch.object(svc, "_calculate_avg_lesson_time", return_value=10.0):
            assert svc._detect_content_preference(42) == "TEXT"

    def test_avg_between_10_and_20_returns_text(self):
        svc = _svc()
        with patch.object(svc, "_calculate_avg_lesson_time", return_value=15.0):
            assert svc._detect_content_preference(42) == "TEXT"

    def test_avg_exactly_20_returns_practice(self):
        svc = _svc()
        with patch.object(svc, "_calculate_avg_lesson_time", return_value=20.0):
            assert svc._detect_content_preference(42) == "PRACTICE"

    def test_avg_above_20_returns_practice(self):
        svc = _svc()
        with patch.object(svc, "_calculate_avg_lesson_time", return_value=30.0):
            assert svc._detect_content_preference(42) == "PRACTICE"

    def test_zero_avg_time_returns_video(self):
        svc = _svc()
        with patch.object(svc, "_calculate_avg_lesson_time", return_value=0.0):
            assert svc._detect_content_preference(42) == "VIDEO"


# ── get_or_create_profile ─────────────────────────────────────────────────────

class TestGetOrCreateProfile:
    def test_existing_profile_returned_as_dict(self):
        row = _profile_row(user_id=42)
        svc = _svc(_db_one(row))
        result = svc.get_or_create_profile(42)
        assert result["user_id"] == 42
        assert result["learning_pace"] == "FAST"
        assert result["pace_score"] == 65.0
        assert result["preferred_content_type"] == "TEXT"

    def test_missing_profile_triggers_insert_then_returns_dict(self):
        """First fetchone → None, INSERT, commit, second fetchone → profile row."""
        created = _profile_row(user_id=42)
        db = MagicMock()
        db.execute.return_value.fetchone.side_effect = [None, created]
        svc = _svc(db)
        result = svc.get_or_create_profile(42)
        assert result["user_id"] == 42
        db.commit.assert_called_once()

    def test_none_pace_score_defaults_to_zero(self):
        row = _profile_row()
        row.pace_score = None
        svc = _svc(_db_one(row))
        result = svc.get_or_create_profile(42)
        assert result["pace_score"] == 0.0

    def test_none_preferred_content_defaults_to_text(self):
        row = _profile_row()
        row.preferred_content_type = None
        svc = _svc(_db_one(row))
        result = svc.get_or_create_profile(42)
        assert result["preferred_content_type"] == "TEXT"


# ── update_profile_metrics ────────────────────────────────────────────────────

class TestUpdateProfileMetrics:
    def test_delegates_to_five_helpers_and_returns_profile(self):
        profile = {"user_id": 42, "learning_pace": "FAST"}
        svc = _svc()
        with (
            patch.object(svc, "_calculate_quiz_average", return_value=75.0),
            patch.object(svc, "_calculate_pace_score", return_value=65.0),
            patch.object(svc, "_count_lessons_completed", return_value=10),
            patch.object(svc, "_calculate_avg_lesson_time", return_value=15.0),
            patch.object(svc, "_detect_content_preference", return_value="TEXT"),
            patch.object(svc, "get_or_create_profile", return_value=profile),
        ):
            result = svc.update_profile_metrics(42)
        assert result == profile
        svc.db.execute.assert_called()  # UPDATE was issued

    def test_pace_category_computed_from_pace_score(self):
        """_categorize_pace(65) == 'FAST' → UPDATE receives pace_category='FAST'."""
        profile = {"user_id": 42}
        svc = _svc()
        captured = {}

        def fake_execute(sql, params):
            if "UPDATE" in str(sql):
                captured.update(params)
            return MagicMock()

        svc.db.execute.side_effect = fake_execute
        with (
            patch.object(svc, "_calculate_quiz_average", return_value=75.0),
            patch.object(svc, "_calculate_pace_score", return_value=65.0),
            patch.object(svc, "_count_lessons_completed", return_value=10),
            patch.object(svc, "_calculate_avg_lesson_time", return_value=15.0),
            patch.object(svc, "_detect_content_preference", return_value="TEXT"),
            patch.object(svc, "get_or_create_profile", return_value=profile),
        ):
            svc.update_profile_metrics(42)
        assert captured.get("pace_category") == "FAST"


# ── _detect_burnout ───────────────────────────────────────────────────────────

class TestDetectBurnout:
    def test_no_result_returns_none(self):
        svc = _svc(_db_one(None))
        assert svc._detect_burnout(42) is None

    def test_null_total_time_returns_none(self):
        svc = _svc(_db_one(_row(total_time=None, lesson_count=2)))
        assert svc._detect_burnout(42) is None

    def test_below_600_returns_none(self):
        svc = _svc(_db_one(_row(total_time=300.0, lesson_count=5)))
        assert svc._detect_burnout(42) is None

    def test_exactly_600_returns_take_break(self):
        svc = _svc(_db_one(_row(total_time=600.0, lesson_count=10)))
        result = svc._detect_burnout(42)
        assert result is not None
        assert result["type"] == "TAKE_BREAK"
        assert result["priority"] == 95

    def test_above_600_returns_take_break(self):
        svc = _svc(_db_one(_row(total_time=720.0, lesson_count=12)))
        result = svc._detect_burnout(42)
        assert result["type"] == "TAKE_BREAK"
        assert result["metadata"]["total_minutes"] == 720.0


# ── _find_weak_lessons ────────────────────────────────────────────────────────

class TestFindWeakLessons:
    def test_no_result_returns_empty_list(self):
        svc = _svc(_db_all([]))
        assert svc._find_weak_lessons(42) == []

    def test_returns_list_of_lesson_ids(self):
        rows = [_row(lesson_id=101), _row(lesson_id=202), _row(lesson_id=303)]
        svc = _svc(_db_all(rows))
        result = svc._find_weak_lessons(42)
        assert result == [101, 202, 303]


# ── _suggest_next_lesson ──────────────────────────────────────────────────────

class TestSuggestNextLesson:
    def test_no_user_result_returns_none(self):
        svc = _svc(_db_one(None))
        assert svc._suggest_next_lesson(42) is None

    def test_no_specialization_returns_none(self):
        svc = _svc(_db_one(_row(current_specialization=None, current_level=1)))
        assert svc._suggest_next_lesson(42) is None

    def test_spec_but_no_next_lesson_returns_none(self):
        db = MagicMock()
        db.execute.return_value.fetchone.side_effect = [
            _row(current_specialization="LFA_PLAYER", current_level=2),
            None,  # no next lesson available
        ]
        svc = _svc(db)
        assert svc._suggest_next_lesson(42) is None

    def test_next_lesson_found_returns_dict(self):
        db = MagicMock()
        db.execute.return_value.fetchone.side_effect = [
            _row(current_specialization="LFA_PLAYER", current_level=2),
            _row(id=55, title="Dribbling Basics", display_order=1),
        ]
        svc = _svc(db)
        result = svc._suggest_next_lesson(42)
        assert result["type"] == "CONTINUE_LEARNING"
        assert result["metadata"]["lesson_id"] == 55
        assert result["priority"] == 70

    def test_level_defaults_to_1_when_none(self):
        """current_level=None → level used as 1 (no KeyError)."""
        db = MagicMock()
        db.execute.return_value.fetchone.side_effect = [
            _row(current_specialization="LFA_PLAYER", current_level=None),
            None,
        ]
        svc = _svc(db)
        result = svc._suggest_next_lesson(42)
        assert result is None  # no lesson → None, but no crash


# ── _check_inactivity ─────────────────────────────────────────────────────────

class TestCheckInactivity:
    def test_no_result_returns_start_learning(self):
        svc = _svc(_db_one(None))
        result = svc._check_inactivity(42)
        assert result["type"] == "START_LEARNING"
        assert result["priority"] == 80

    def test_null_last_activity_returns_start_learning(self):
        svc = _svc(_db_one(_row(last_activity=None)))
        result = svc._check_inactivity(42)
        assert result["type"] == "START_LEARNING"

    def test_active_within_7_days_returns_none(self):
        recent = datetime.now() - timedelta(days=2)
        svc = _svc(_db_one(_row(last_activity=recent)))
        assert svc._check_inactivity(42) is None

    def test_exactly_7_days_inactive_returns_resume(self):
        last = datetime.now() - timedelta(days=7)
        svc = _svc(_db_one(_row(last_activity=last)))
        result = svc._check_inactivity(42)
        assert result["type"] == "RESUME_LEARNING"
        assert result["priority"] == 90

    def test_10_days_inactive_includes_count_in_metadata(self):
        last = datetime.now() - timedelta(days=10)
        svc = _svc(_db_one(_row(last_activity=last)))
        result = svc._check_inactivity(42)
        assert result["metadata"]["days_inactive"] == 10


# ── _suggest_practice ─────────────────────────────────────────────────────────

class TestSuggestPractice:
    def test_no_result_returns_none(self):
        svc = _svc(_db_one(None))
        assert svc._suggest_practice(42) is None

    def test_fewer_than_5_lessons_returns_none(self):
        svc = _svc(_db_one(_row(lessons_done=3, exercises_done=0)))
        assert svc._suggest_practice(42) is None

    def test_5_lessons_0_exercises_returns_practice_more(self):
        svc = _svc(_db_one(_row(lessons_done=5, exercises_done=0)))
        result = svc._suggest_practice(42)
        assert result["type"] == "PRACTICE_MORE"
        assert result["priority"] == 75

    def test_5_lessons_1_exercise_still_recommends_practice(self):
        svc = _svc(_db_one(_row(lessons_done=5, exercises_done=1)))
        result = svc._suggest_practice(42)
        assert result is not None
        assert result["type"] == "PRACTICE_MORE"

    def test_5_lessons_2_exercises_returns_none(self):
        svc = _svc(_db_one(_row(lessons_done=5, exercises_done=2)))
        assert svc._suggest_practice(42) is None

    def test_metadata_contains_lesson_and_exercise_count(self):
        svc = _svc(_db_one(_row(lessons_done=7, exercises_done=0)))
        result = svc._suggest_practice(42)
        assert result["metadata"]["lessons_done"] == 7
        assert result["metadata"]["exercises_done"] == 0


# ── generate_recommendations ──────────────────────────────────────────────────

class TestGenerateRecommendations:
    def test_cached_results_returned_without_refresh(self):
        """refresh=False + existing rows → return formatted list, skip generators."""
        cached_row = _row(
            id=10, recommendation_type="CONTINUE_LEARNING",
            title="Keep Going", message="Next lesson waiting",
            priority=70, metadata={}, is_active=True, created_at=None,
        )
        svc = _svc(_db_all([cached_row]))
        result = svc.generate_recommendations(42, refresh=False)
        assert len(result) == 1
        assert result[0]["type"] == "CONTINUE_LEARNING"

    def test_no_cache_with_refresh_false_still_generates(self):
        """refresh=False but no cached rows → falls through to generate."""
        db = _db_all([])  # fetchall returns empty → no cache
        svc = _svc(db)
        with (
            patch.object(svc, "_detect_burnout", return_value=None),
            patch.object(svc, "_find_weak_lessons", return_value=[]),
            patch.object(svc, "_suggest_next_lesson", return_value=None),
            patch.object(svc, "_check_inactivity", return_value=None),
            patch.object(svc, "_suggest_practice", return_value=None),
            patch.object(svc, "_save_recommendations") as mock_save,
        ):
            result = svc.generate_recommendations(42, refresh=False)
        assert result == []
        mock_save.assert_called_once_with(42, [])

    def test_refresh_true_generates_fresh_all_empty(self):
        svc = _svc()
        with (
            patch.object(svc, "_detect_burnout", return_value=None),
            patch.object(svc, "_find_weak_lessons", return_value=[]),
            patch.object(svc, "_suggest_next_lesson", return_value=None),
            patch.object(svc, "_check_inactivity", return_value=None),
            patch.object(svc, "_suggest_practice", return_value=None),
            patch.object(svc, "_save_recommendations") as mock_save,
        ):
            result = svc.generate_recommendations(42, refresh=True)
        assert result == []
        mock_save.assert_called_once_with(42, [])

    def test_burnout_and_weak_lessons_sorted_by_priority(self):
        """Burnout (priority 95) before review_lesson (priority 85)."""
        burnout = {
            "type": "TAKE_BREAK", "title": "Rest", "message": "Rest",
            "priority": 95, "metadata": {"total_minutes": 700},
        }
        svc = _svc()
        with (
            patch.object(svc, "_detect_burnout", return_value=burnout),
            patch.object(svc, "_find_weak_lessons", return_value=[101, 202]),
            patch.object(svc, "_suggest_next_lesson", return_value=None),
            patch.object(svc, "_check_inactivity", return_value=None),
            patch.object(svc, "_suggest_practice", return_value=None),
            patch.object(svc, "_save_recommendations"),
        ):
            result = svc.generate_recommendations(42, refresh=True)
        assert len(result) == 2
        assert result[0]["type"] == "TAKE_BREAK"
        assert result[1]["type"] == "REVIEW_LESSON"

    def test_inactivity_recommendation_included(self):
        inactivity = {
            "type": "START_LEARNING", "title": "Start", "message": "Begin",
            "priority": 80, "metadata": {},
        }
        svc = _svc()
        with (
            patch.object(svc, "_detect_burnout", return_value=None),
            patch.object(svc, "_find_weak_lessons", return_value=[]),
            patch.object(svc, "_suggest_next_lesson", return_value=None),
            patch.object(svc, "_check_inactivity", return_value=inactivity),
            patch.object(svc, "_suggest_practice", return_value=None),
            patch.object(svc, "_save_recommendations"),
        ):
            result = svc.generate_recommendations(42, refresh=True)
        assert any(r["type"] == "START_LEARNING" for r in result)

    def test_capped_at_five_recommendations(self):
        """Even with 6+ raw recs, only top 5 returned and saved."""
        recs = [
            {"type": f"T{i}", "title": "", "message": "", "priority": i, "metadata": {}}
            for i in range(10, 70, 10)  # 6 recs with priorities 10,20,...,60
        ]
        svc = _svc()
        with (
            patch.object(svc, "_detect_burnout", return_value=recs[0]),
            patch.object(svc, "_find_weak_lessons", return_value=[1, 2, 3]),  # adds 1
            patch.object(svc, "_suggest_next_lesson", return_value=recs[2]),
            patch.object(svc, "_check_inactivity", return_value=recs[3]),
            patch.object(svc, "_suggest_practice", return_value=recs[4]),
            patch.object(svc, "_save_recommendations") as mock_save,
        ):
            result = svc.generate_recommendations(42, refresh=True)
        # _save_recommendations called with ≤ 5
        saved_count = len(mock_save.call_args[0][1])
        assert saved_count <= 5
        assert len(result) <= 5


# ── _save_recommendations ─────────────────────────────────────────────────────

class TestSaveRecommendations:
    def test_empty_list_only_deactivates(self):
        db = MagicMock()
        svc = _svc(db)
        svc._save_recommendations(42, [])
        # One execute for UPDATE, no INSERT calls
        assert db.execute.call_count == 1

    def test_two_recs_deactivate_plus_two_inserts(self):
        db = MagicMock()
        svc = _svc(db)
        recs = [
            {"type": "A", "title": "T1", "message": "M1", "priority": 80, "metadata": {}},
            {"type": "B", "title": "T2", "message": "M2", "priority": 70, "metadata": {}},
        ]
        svc._save_recommendations(42, recs)
        assert db.execute.call_count == 3  # 1 deactivate + 2 inserts


# ── _format_recommendation ────────────────────────────────────────────────────

class TestFormatRecommendation:
    def test_row_converted_to_dict(self):
        row = _row(
            id=99, recommendation_type="TAKE_BREAK",
            title="Rest", message="Take a break", priority=95,
            metadata={"total_minutes": 700},
            is_active=True, created_at="2026-03-05",
        )
        svc = _svc()
        result = svc._format_recommendation(row)
        assert result["id"] == 99
        assert result["type"] == "TAKE_BREAK"
        assert result["title"] == "Rest"
        assert result["priority"] == 95
        assert result["is_active"] is True


# ── dismiss_recommendation ────────────────────────────────────────────────────

class TestDismissRecommendation:
    def test_executes_update_and_commits(self):
        db = MagicMock()
        svc = _svc(db)
        svc.dismiss_recommendation(user_id=42, recommendation_id=7)
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    def test_passes_correct_ids_to_query(self):
        db = MagicMock()
        svc = _svc(db)
        svc.dismiss_recommendation(user_id=42, recommendation_id=7)
        _, params = db.execute.call_args[0], db.execute.call_args
        # Both ids must appear in the call args
        call_kwargs = db.execute.call_args[0][1]
        assert call_kwargs["user_id"] == 42
        assert call_kwargs["rec_id"] == 7


# ── create_daily_snapshot ─────────────────────────────────────────────────────

class TestCreateDailySnapshot:
    def test_full_flow_commits_once(self):
        """get_or_create_profile (1 fetchone) + 2 today queries (2 fetchone) + INSERT."""
        profile_result = _profile_row(user_id=42)
        lesson_count_row = _row(count=3)
        time_row = _row(total=45)

        db = MagicMock()
        db.execute.return_value.fetchone.side_effect = [
            profile_result,   # get_or_create_profile SELECT
            lesson_count_row,  # today_lessons COUNT
            time_row,          # today_time SUM
        ]
        svc = _svc(db)
        svc.create_daily_snapshot(42)
        db.commit.assert_called_once()

    def test_zero_today_values_handled(self):
        """today_lessons.count = None, today_time.total = None → no crash."""
        profile_result = _profile_row(user_id=42)
        lesson_count_row = _row(count=None)
        time_row = _row(total=None)

        db = MagicMock()
        db.execute.return_value.fetchone.side_effect = [
            profile_result,
            lesson_count_row,
            time_row,
        ]
        svc = _svc(db)
        svc.create_daily_snapshot(42)
        db.commit.assert_called_once()


# ── get_performance_history ───────────────────────────────────────────────────

class TestGetPerformanceHistory:
    def test_empty_result_returns_empty_list(self):
        svc = _svc(_db_all([]))
        assert svc.get_performance_history(42) == []

    def test_with_rows_returns_formatted_list(self):
        rows = [
            _row(snapshot_date="2026-03-04", pace_score=65.0,
                 quiz_average=75.0, lessons_completed_count=3,
                 time_spent_minutes_today=45.0),
        ]
        svc = _svc(_db_all(rows))
        result = svc.get_performance_history(42)
        assert len(result) == 1
        assert result[0]["pace_score"] == 65.0
        assert result[0]["quiz_average"] == 75.0
        assert result[0]["lessons_completed"] == 3
        assert result[0]["time_spent"] == 45.0

    def test_null_fields_default_to_zero(self):
        rows = [
            _row(snapshot_date="2026-03-04", pace_score=None,
                 quiz_average=None, lessons_completed_count=None,
                 time_spent_minutes_today=None),
        ]
        svc = _svc(_db_all(rows))
        result = svc.get_performance_history(42)
        assert result[0]["pace_score"] == 0
        assert result[0]["quiz_average"] == 0
        assert result[0]["lessons_completed"] == 0
        assert result[0]["time_spent"] == 0

    def test_custom_days_parameter_accepted(self):
        """days parameter flows through without error."""
        svc = _svc(_db_all([]))
        result = svc.get_performance_history(42, days=7)
        assert result == []
