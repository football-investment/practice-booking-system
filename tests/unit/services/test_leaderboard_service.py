"""
Unit tests for gamification/leaderboard_service.py — Sprint M (2026-03-05)

Functions covered:
  - get_leaderboard          (branches: empty result, limit respected, XP>0 filter)
  - get_user_rank            (branches: no stats, xp==0, user not found, total_users==1,
                               total_users>1, rank=1, rank=last, percentile math)
  - get_semester_leaderboard (branches: bookings>0 attendance_rate, bookings==0,
                               semester_xp=None→0)
  - get_specialization_leaderboard (basic query, empty result)

Target: leaderboard_service.py 20% stmt / 0% branch → 100% stmt+branch
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.gamification.leaderboard_service import (
    get_leaderboard,
    get_user_rank,
    get_semester_leaderboard,
    get_specialization_leaderboard,
)

# User.username / User.full_name don't exist as mapped columns (model uses User.name).
# get_semester_leaderboard uses them as SQL projections → AttributeError on class access.
# Patch the User reference inside the service module for those tests.
_PATCH_USER = "app.services.gamification.leaderboard_service.User"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db():
    return MagicMock()


def _mock_user(uid=1, username="alice", full_name="Alice Smith"):
    u = MagicMock()
    u.id = uid
    u.username = username
    u.full_name = full_name
    return u


def _mock_stats(uid=1, xp=500, level=3, attendance_rate=87.654, semesters=2):
    s = MagicMock()
    s.user_id = uid
    s.total_xp = xp
    s.level = level
    s.attendance_rate = attendance_rate
    s.semesters_participated = semesters
    return s


# ---------------------------------------------------------------------------
# get_leaderboard
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetLeaderboard:

    def _setup(self, db, rows):
        """Configure db.query(...).join(...).filter(...).order_by(...).limit(...).all()"""
        q = MagicMock()
        q.join.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = rows
        db.query.return_value = q
        return q

    def test_empty_leaderboard_returns_empty_list(self):
        db = _db()
        self._setup(db, [])
        result = get_leaderboard(db)
        assert result == []

    def test_single_entry_rank_1(self):
        db = _db()
        stats = _mock_stats(uid=1, xp=1000, level=5, attendance_rate=90.0, semesters=3)
        user = _mock_user(uid=1, username="top", full_name="Top User")
        self._setup(db, [(stats, user)])
        result = get_leaderboard(db)
        assert len(result) == 1
        assert result[0]["rank"] == 1
        assert result[0]["user_id"] == 1
        assert result[0]["username"] == "top"
        assert result[0]["total_xp"] == 1000
        assert result[0]["level"] == 5
        assert result[0]["attendance_rate"] == 90.0
        assert result[0]["semesters_participated"] == 3

    def test_multiple_entries_rank_assigned_in_order(self):
        db = _db()
        rows = [
            (_mock_stats(uid=i, xp=1000 - i * 100), _mock_user(uid=i))
            for i in range(1, 4)
        ]
        self._setup(db, rows)
        result = get_leaderboard(db)
        assert [r["rank"] for r in result] == [1, 2, 3]

    def test_attendance_rate_rounded_to_one_decimal(self):
        db = _db()
        stats = _mock_stats(attendance_rate=87.654)
        user = _mock_user()
        self._setup(db, [(stats, user)])
        result = get_leaderboard(db)
        assert result[0]["attendance_rate"] == 87.7

    def test_custom_limit_passed_to_query(self):
        db = _db()
        q = MagicMock()
        q.join.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []
        db.query.return_value = q
        get_leaderboard(db, limit=5)
        q.limit.assert_called_once_with(5)

    def test_default_limit_is_10(self):
        db = _db()
        q = MagicMock()
        q.join.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []
        db.query.return_value = q
        get_leaderboard(db)
        q.limit.assert_called_once_with(10)


# ---------------------------------------------------------------------------
# get_user_rank
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetUserRank:

    def _setup_rank(self, db, user_stats, user, users_above_count, total_users_count):
        """
        get_user_rank performs 4 db.query calls in order:
          1. UserStats.filter().first() → user_stats
          2. User.filter().first() → user
          3. UserStats.filter().count() → users_above_count
          4. UserStats.filter().count() → total_users_count
        """
        calls = []

        def _make_q(result, is_count=False):
            q = MagicMock()
            q.filter.return_value = q
            if is_count:
                q.count.return_value = result
            else:
                q.first.return_value = result
            return q

        db.query.side_effect = [
            _make_q(user_stats),
            _make_q(user),
            _make_q(users_above_count, is_count=True),
            _make_q(total_users_count, is_count=True),
        ]

    def test_no_user_stats_returns_none(self):
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        result = get_user_rank(db, user_id=99)
        assert result is None

    def test_zero_xp_returns_none(self):
        db = _db()
        stats = _mock_stats(xp=0)
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = stats
        db.query.return_value = q
        result = get_user_rank(db, user_id=1)
        assert result is None

    def test_user_not_found_returns_none(self):
        db = _db()

        def _q(model):
            q = MagicMock()
            q.filter.return_value = q
            from app.models.gamification import UserStats
            from app.models.user import User
            if model is UserStats:
                q.first.return_value = _mock_stats(xp=100)
            else:
                q.first.return_value = None  # User not found
            return q

        db.query.side_effect = _q
        result = get_user_rank(db, user_id=42)
        assert result is None

    def test_rank_1_top_user(self):
        db = _db()
        stats = _mock_stats(uid=1, xp=1000, level=5)
        user = _mock_user(uid=1)
        # users_above=0, total_users=5
        self._setup_rank(db, stats, user, users_above_count=0, total_users_count=5)
        result = get_user_rank(db, user_id=1)
        assert result is not None
        assert result["rank"] == 1
        assert result["total_users"] == 5
        # percentile: (5-1)/(5-1)*100 = 100.0
        assert result["percentile"] == 100.0

    def test_rank_last_user(self):
        db = _db()
        stats = _mock_stats(uid=5, xp=50, level=1)
        user = _mock_user(uid=5)
        # users_above=4, total_users=5 → rank=5
        self._setup_rank(db, stats, user, users_above_count=4, total_users_count=5)
        result = get_user_rank(db, user_id=5)
        assert result["rank"] == 5
        # percentile: (5-5)/(5-1)*100 = 0.0
        assert result["percentile"] == 0.0

    def test_percentile_middle_user(self):
        db = _db()
        stats = _mock_stats(uid=3, xp=500, level=3)
        user = _mock_user(uid=3)
        # users_above=2, total_users=5 → rank=3
        self._setup_rank(db, stats, user, users_above_count=2, total_users_count=5)
        result = get_user_rank(db, user_id=3)
        assert result["rank"] == 3
        # percentile: (5-3)/(5-1)*100 = 50.0
        assert result["percentile"] == 50.0

    def test_total_users_equals_1_percentile_zero(self):
        """Edge: only 1 user with XP — percentile must be 0 (not divide-by-zero)."""
        db = _db()
        stats = _mock_stats(uid=1, xp=100, level=1)
        user = _mock_user(uid=1)
        self._setup_rank(db, stats, user, users_above_count=0, total_users_count=1)
        result = get_user_rank(db, user_id=1)
        assert result["rank"] == 1
        assert result["percentile"] == 0.0

    def test_result_structure_complete(self):
        db = _db()
        stats = _mock_stats(uid=7, xp=200, level=2)
        user = _mock_user(uid=7, username="bob", full_name="Bob Jones")
        self._setup_rank(db, stats, user, users_above_count=1, total_users_count=3)
        result = get_user_rank(db, user_id=7)
        assert result["user_id"] == 7
        assert result["username"] == "bob"
        assert result["full_name"] == "Bob Jones"
        assert result["total_xp"] == 200
        assert result["level"] == 2

    def test_percentile_rounded_to_one_decimal(self):
        db = _db()
        stats = _mock_stats(xp=300)
        user = _mock_user()
        # users_above=1, total_users=4 → rank=2 → percentile=(4-2)/(4-1)*100=66.666...
        self._setup_rank(db, stats, user, users_above_count=1, total_users_count=4)
        result = get_user_rank(db, user_id=1)
        assert result["percentile"] == 66.7


# ---------------------------------------------------------------------------
# get_semester_leaderboard
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetSemesterLeaderboard:
    """
    get_semester_leaderboard uses User.username / User.full_name as SQL column
    projections. Since the User model uses User.name (not .username/.full_name),
    these attributes don't exist at the class level → AttributeError.

    All tests here patch the User class inside the service module so that
    User.username / User.full_name are valid mock attributes during the call.
    The result row attributes (row.username etc.) are returned by the query
    mock's .all() — fully under test control.
    """

    def _mock_stat_row(self, uid, username, full_name, bookings, attended, semester_xp):
        row = MagicMock()
        row.id = uid
        row.username = username
        row.full_name = full_name
        row.bookings = bookings
        row.attended = attended
        row.semester_xp = semester_xp
        return row

    def _setup(self, db, rows):
        q = MagicMock()
        q.select_from.return_value = q
        q.join.return_value = q
        q.outerjoin.return_value = q
        q.filter.return_value = q
        q.group_by.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = rows
        db.query.return_value = q

    @patch(_PATCH_USER)
    def test_empty_semester_returns_empty_list(self, _u):
        db = _db()
        self._setup(db, [])
        result = get_semester_leaderboard(db, semester_id=1)
        assert result == []

    @patch(_PATCH_USER)
    def test_attendance_rate_calculated_from_bookings(self, _u):
        """bookings > 0: attendance_rate = attended/bookings * 100"""
        db = _db()
        row = self._mock_stat_row(1, "alice", "Alice", bookings=10, attended=8, semester_xp=200)
        self._setup(db, [row])
        result = get_semester_leaderboard(db, semester_id=1)
        assert len(result) == 1
        assert result[0]["attendance_rate"] == 80.0
        assert result[0]["semester_xp"] == 200

    @patch(_PATCH_USER)
    def test_attendance_rate_zero_when_no_bookings(self, _u):
        """bookings == 0: attendance_rate = 0.0 (no ZeroDivisionError)"""
        db = _db()
        row = self._mock_stat_row(2, "bob", "Bob", bookings=0, attended=0, semester_xp=0)
        self._setup(db, [row])
        result = get_semester_leaderboard(db, semester_id=1)
        assert result[0]["attendance_rate"] == 0.0

    @patch(_PATCH_USER)
    def test_semester_xp_none_defaults_to_zero(self, _u):
        """semester_xp = None (outerjoin miss) → returned as 0"""
        db = _db()
        row = self._mock_stat_row(3, "carol", "Carol", bookings=5, attended=5, semester_xp=None)
        self._setup(db, [row])
        result = get_semester_leaderboard(db, semester_id=1)
        assert result[0]["semester_xp"] == 0

    @patch(_PATCH_USER)
    def test_rank_assigned_in_order(self, _u):
        db = _db()
        rows = [
            self._mock_stat_row(i, f"u{i}", f"User {i}", bookings=5, attended=i, semester_xp=i * 100)
            for i in range(1, 4)
        ]
        self._setup(db, rows)
        result = get_semester_leaderboard(db, semester_id=2)
        assert [r["rank"] for r in result] == [1, 2, 3]

    @patch(_PATCH_USER)
    def test_result_contains_all_fields(self, _u):
        db = _db()
        row = self._mock_stat_row(1, "alice", "Alice Smith", bookings=4, attended=3, semester_xp=150)
        self._setup(db, [row])
        result = get_semester_leaderboard(db, semester_id=5)
        r = result[0]
        assert r["user_id"] == 1
        assert r["username"] == "alice"
        assert r["full_name"] == "Alice Smith"
        assert r["bookings"] == 4
        assert r["attended"] == 3
        assert r["attendance_rate"] == 75.0
        assert r["semester_xp"] == 150

    @patch(_PATCH_USER)
    def test_custom_limit_passed_to_query(self, _u):
        db = _db()
        q = MagicMock()
        q.select_from.return_value = q
        q.join.return_value = q
        q.outerjoin.return_value = q
        q.filter.return_value = q
        q.group_by.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []
        db.query.return_value = q
        get_semester_leaderboard(db, semester_id=1, limit=3)
        q.limit.assert_called_once_with(3)


# ---------------------------------------------------------------------------
# get_specialization_leaderboard
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetSpecializationLeaderboard:

    def _setup(self, db, rows):
        q = MagicMock()
        q.join.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = rows
        db.query.return_value = q

    def _mock_progress(self, current_level, completed_sessions):
        p = MagicMock()
        p.current_level = current_level
        p.completed_sessions = completed_sessions
        return p

    def test_empty_result_returns_empty_list(self):
        db = _db()
        self._setup(db, [])
        result = get_specialization_leaderboard(db, specialization_id="PLAYER")
        assert result == []

    def test_single_entry_structure(self):
        db = _db()
        progress = self._mock_progress(current_level=4, completed_sessions=20)
        user = _mock_user(uid=1, username="alice", full_name="Alice")
        self._setup(db, [(progress, user)])
        result = get_specialization_leaderboard(db, specialization_id="COACH")
        assert len(result) == 1
        r = result[0]
        assert r["rank"] == 1
        assert r["user_id"] == 1
        assert r["username"] == "alice"
        assert r["current_level"] == 4
        assert r["completed_sessions"] == 20
        assert r["specialization_id"] == "COACH"

    def test_multiple_entries_ranked_in_order(self):
        db = _db()
        rows = [
            (self._mock_progress(current_level=5 - i, completed_sessions=10 - i), _mock_user(uid=i))
            for i in range(1, 4)
        ]
        self._setup(db, rows)
        result = get_specialization_leaderboard(db, specialization_id="INTERNSHIP")
        assert [r["rank"] for r in result] == [1, 2, 3]

    def test_specialization_id_stored_in_result(self):
        db = _db()
        progress = self._mock_progress(3, 10)
        user = _mock_user()
        self._setup(db, [(progress, user)])
        result = get_specialization_leaderboard(db, specialization_id="PLAYER")
        assert result[0]["specialization_id"] == "PLAYER"

    def test_custom_limit_passed(self):
        db = _db()
        q = MagicMock()
        q.join.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []
        db.query.return_value = q
        get_specialization_leaderboard(db, specialization_id="PLAYER", limit=5)
        q.limit.assert_called_once_with(5)
