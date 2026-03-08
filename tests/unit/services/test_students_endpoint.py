"""
Sprint 36 — app/api/api_v1/endpoints/students.py
=================================================
Target: branch coverage gaps (9 missing branches, 45% → ≥80%)

Covers:
  get_semester_progress:
    * no active semester → returns None progress dict (L32 true branch)
    * semester with datetime start/end → .date() conversion (L48-51 branches)
    * early phase (elapsed < third)  → "Early Semester" (L59 true branch)
    * mid phase (third ≤ elapsed < 2*third) → "Mid-Semester" (L61 branch)
    * final phase (elapsed ≥ 2*third) → "Final Phase" (L63 else branch)
    * total_days == 0 guard → 0% completion (L55 else branch)

  get_achievements:
    * no activity → empty achievements list
    * high skill_improvements (≥5) → gold tier
    * low skill_improvements (<5) → silver tier
    * high training_consistency (≥3) → gold tier
    * focus_array > 0 → focus achievement added

  get_daily_challenge:
    * recent_bookings == 0 → "Book Your First Session" challenge
    * recent_bookings > 0, recent_projects == 0 → "Join a Training Project"
    * both > 0 → "Maintain Training Consistency"
"""
import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.api.api_v1.endpoints.students import (
    get_achievements,
    get_daily_challenge,
    get_semester_progress,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _q(first=None, count=0, all_=None):
    """Fluent query mock."""
    q = MagicMock()
    for m in ("filter", "join", "options", "order_by", "offset",
              "limit", "filter_by", "distinct"):
        getattr(q, m).return_value = q
    q.first.return_value = first
    q.count.return_value = count
    q.all.return_value = all_ if all_ is not None else []
    return q


def _seq_db(*queries):
    """db where each db.query() call returns the next query in sequence."""
    calls = [0]
    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        return queries[idx] if idx < len(queries) else _q()
    db = MagicMock()
    db.query.side_effect = _side
    return db


def _user(uid=42):
    u = MagicMock()
    u.id = uid
    return u


def _semester(start_days_ago=30, total_days=90, use_date=True):
    """Create a mock semester with date or datetime start/end."""
    today = date.today()
    start = today - timedelta(days=start_days_ago)
    end = start + timedelta(days=total_days)
    s = MagicMock()
    s.id = 1
    s.name = "Test Semester"
    if use_date:
        s.start_date = start
        s.end_date = end
    else:
        s.start_date = datetime.combine(start, datetime.min.time())
        s.end_date = datetime.combine(end, datetime.min.time())
    return s


# ── get_semester_progress tests ───────────────────────────────────────────────

class TestGetSemesterProgress:

    def test_no_active_semester_returns_none_dict(self):
        """No current semester → L32 true branch: returns {'semester': None, ...}."""
        db = _seq_db(_q(first=None))  # no semester
        result = asyncio.run(get_semester_progress(current_user=_user(), db=db))
        assert result["semester"] is None
        assert result["progress"]["completion_percentage"] == 0
        assert result["progress"]["current_phase"] == "No Active Semester"

    def test_semester_with_date_objects_early_phase(self):
        """Semester with plain date objects, elapsed in early phase (< 1/3)."""
        # Start 5 days ago, total 90 days → elapsed=5, third=30 → early phase
        sem = _semester(start_days_ago=5, total_days=90, use_date=True)
        db = _seq_db(
            _q(first=sem),  # semester query
            _q(count=2),    # bookings count
            _q(count=1),    # projects count
        )
        result = asyncio.run(get_semester_progress(current_user=_user(), db=db))
        assert result["semester"]["id"] == 1
        assert result["progress"]["current_phase"] == "Early Semester"

    def test_semester_with_datetime_objects_mid_phase(self):
        """Semester with datetime objects → .date() conversion (L48-51); mid phase."""
        # Start 40 days ago, total 90 days → elapsed=40, third=30 → mid phase
        sem = _semester(start_days_ago=40, total_days=90, use_date=False)
        db = _seq_db(
            _q(first=sem),
            _q(count=5),
            _q(count=2),
        )
        result = asyncio.run(get_semester_progress(current_user=_user(), db=db))
        assert result["progress"]["current_phase"] == "Mid-Semester"

    def test_semester_final_phase(self):
        """Elapsed ≥ 2*third → 'Final Phase' (L64 else branch)."""
        # Start 70 days ago, total 90 days → elapsed=70, third=30, 2*third=60 → final
        sem = _semester(start_days_ago=70, total_days=90, use_date=True)
        db = _seq_db(
            _q(first=sem),
            _q(count=8),
            _q(count=3),
        )
        result = asyncio.run(get_semester_progress(current_user=_user(), db=db))
        assert result["progress"]["current_phase"] == "Final Phase"

    def test_semester_total_days_zero_completion_guard(self):
        """total_days == 0 → completion_percentage = 0 (L55 'if total_days > 0 else 0' branch)."""
        today = date.today()
        sem = MagicMock()
        sem.id = 99
        sem.name = "Zero Day Semester"
        sem.start_date = today
        sem.end_date = today  # same day → total_days = 0
        db = _seq_db(
            _q(first=sem),
            _q(count=0),
            _q(count=0),
        )
        result = asyncio.run(get_semester_progress(current_user=_user(), db=db))
        assert result["progress"]["completion_percentage"] == 0

    def test_midterm_timeline_completed_branch(self):
        """Timeline midterm 'completed' branch: elapsed > total_days//2."""
        # Start 60 days ago, total 90 → elapsed=60 > 45 → midterm completed=True
        sem = _semester(start_days_ago=60, total_days=90, use_date=True)
        db = _seq_db(_q(first=sem), _q(count=0), _q(count=0))
        result = asyncio.run(get_semester_progress(current_user=_user(), db=db))
        timeline = result["progress"]["timeline"]
        midterm = next(t for t in timeline if t["label"] == "Mid-Term Evaluation")
        assert midterm["completed"] is True


# ── get_achievements tests ────────────────────────────────────────────────────

class TestGetAchievements:

    def _run(self, bookings=0, projects=0, quizzes=0):
        """Run get_achievements with given activity counts."""
        db = _seq_db(
            _q(count=bookings),   # total_bookings
            _q(count=projects),   # total_projects
            _q(count=quizzes),    # completed_quizzes
        )
        return asyncio.run(get_achievements(current_user=_user(), db=db))

    def test_no_activity_returns_empty_achievements(self):
        """All zeros → no achievements unlocked (all if-branches false)."""
        result = self._run(bookings=0, projects=0, quizzes=0)
        assert result["achievements"] == []
        assert result["summary"]["total_unlocked"] == 0

    def test_low_skill_improvement_silver_tier(self):
        """skill_improvements 1-4 (bookings=5..19) → silver tier."""
        result = self._run(bookings=5)  # skill_improvements = 1
        skills = [a for a in result["achievements"] if a["id"] == "skill_improved"]
        assert len(skills) == 1
        assert skills[0]["tier"] == "silver"

    def test_high_skill_improvement_gold_tier(self):
        """skill_improvements ≥ 5 (bookings≥25) → gold tier."""
        result = self._run(bookings=25)  # skill_improvements = 5
        skills = [a for a in result["achievements"] if a["id"] == "skill_improved"]
        assert skills[0]["tier"] == "gold"

    def test_low_training_consistency_bronze_tier(self):
        """training_consistency 1-2 (bookings=10..29) → bronze tier."""
        result = self._run(bookings=10)  # consistency = 1
        cons = [a for a in result["achievements"] if a["id"] == "training_consistency"]
        assert len(cons) == 1
        assert cons[0]["tier"] == "bronze"

    def test_high_training_consistency_gold_tier(self):
        """training_consistency ≥ 3 (bookings≥30) → gold tier."""
        result = self._run(bookings=30)  # consistency = 3
        cons = [a for a in result["achievements"] if a["id"] == "training_consistency"]
        assert cons[0]["tier"] == "gold"

    def test_focus_array_achievement_added(self):
        """focus_array > 0 (quizzes > 0) → focus achievement in list."""
        result = self._run(quizzes=3)
        focus = [a for a in result["achievements"] if a["id"] == "focus_array"]
        assert len(focus) == 1
        assert focus[0]["progress"]["current"] == 3

    def test_all_achievements_unlocked(self):
        """bookings=30, quizzes=5 → all 3 achievement types present."""
        result = self._run(bookings=30, quizzes=5)
        assert result["summary"]["total_unlocked"] == 3


# ── get_daily_challenge tests ─────────────────────────────────────────────────

class TestGetDailyChallenge:

    def _run(self, recent_bookings=0, recent_projects=0):
        db = _seq_db(
            _q(count=recent_bookings),   # recent_bookings
            _q(count=recent_projects),   # recent_projects
        )
        return asyncio.run(get_daily_challenge(current_user=_user(), db=db))

    def test_no_recent_bookings_book_session_challenge(self):
        """recent_bookings == 0 → 'Book Your First Session' challenge (L234 branch)."""
        result = self._run(recent_bookings=0)
        challenge = result["daily_challenge"]
        assert challenge["title"] == "Book Your First Session"
        assert challenge["difficulty"] == "easy"

    def test_has_bookings_no_projects_join_project_challenge(self):
        """recent_bookings > 0, recent_projects == 0 → 'Join a Training Project' (L250 branch)."""
        result = self._run(recent_bookings=3, recent_projects=0)
        challenge = result["daily_challenge"]
        assert challenge["title"] == "Join a Training Project"
        assert challenge["difficulty"] == "medium"

    def test_has_both_consistency_challenge(self):
        """Both > 0 → 'Maintain Training Consistency' else branch (L266)."""
        result = self._run(recent_bookings=5, recent_projects=2)
        challenge = result["daily_challenge"]
        assert challenge["title"] == "Maintain Training Consistency"
        assert challenge["difficulty"] == "hard"
        assert challenge["progress"]["current"] == 5

    def test_user_activity_returned(self):
        """user_activity dict is always present in response."""
        result = self._run(recent_bookings=2, recent_projects=1)
        assert result["user_activity"]["recent_bookings"] == 2
        assert result["user_activity"]["recent_projects"] == 1
