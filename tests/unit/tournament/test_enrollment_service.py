"""
Tests for tournament/enrollment_service.py

Missing coverage targets (lines 42-80):
  - auto_book_students: no students early return, session not found skip,
    normal booking, capacity capping, multi-session mix
"""
import pytest
from unittest.mock import MagicMock

from app.services.tournament.enrollment_service import auto_book_students


# ──────────────────── helpers ────────────────────


def _student(uid: int):
    s = MagicMock()
    s.id = uid
    return s


def _session(sid: int, capacity: int):
    s = MagicMock()
    s.id = sid
    s.capacity = capacity
    return s


def _make_db(students, session_lookup):
    """
    Build a DB mock.
    students: list returned for User query
    session_lookup: callable(session_id) -> session or None
    """
    from app.models.user import User
    from app.models.session import Session as SessionModel

    db = MagicMock()

    user_q = MagicMock()
    user_q.filter.return_value = user_q
    user_q.all.return_value = students

    def _session_q_factory(sid_filter=None):
        q = MagicMock()
        q.filter = MagicMock(return_value=q)
        q.first = MagicMock(side_effect=lambda: sid_filter)
        return q

    # We capture the last id passed to SessionModel.id == x via side_effect
    session_calls = []

    class _SessQ:
        def filter(self, *args):
            # extract the id from the binary expression if possible
            return self

        def first(self):
            # We track calls in order
            idx = len(session_calls)
            session_calls.append(idx)
            return None  # will be overridden

    def _query(model):
        if model is User:
            return user_q
        # SessionModel — return a fresh mock per call
        sq = MagicMock()
        sq.filter.return_value = sq
        return sq

    db.query.side_effect = _query
    return db


# ──────────────────── tests ────────────────────


class TestAutoBookStudents:

    def test_no_students_returns_empty_dict(self):
        """Lines 52-53: no students → early return, no db.add, no commit."""
        from app.models.user import User

        db = MagicMock()
        user_q = MagicMock()
        user_q.filter.return_value = user_q
        user_q.all.return_value = []
        db.query.return_value = user_q

        result = auto_book_students(db, session_ids=[1, 2, 3])

        assert result == {}
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_session_not_found_skipped(self):
        """Lines 56-58: session not found → skip, continue loop, commit called."""
        from app.models.user import User
        from app.models.session import Session as SessionModel

        student = _student(10)

        db = MagicMock()
        user_q = MagicMock()
        user_q.filter.return_value = user_q
        user_q.all.return_value = [student]

        session_q = MagicMock()
        session_q.filter.return_value = session_q
        session_q.first.return_value = None  # session not found

        def _q(model):
            if model is User:
                return user_q
            return session_q

        db.query.side_effect = _q

        result = auto_book_students(db, session_ids=[999])

        assert result == {}
        db.add.assert_not_called()
        db.commit.assert_called_once()

    def test_single_session_books_up_to_capacity(self):
        """Lines 61-77: books min(target, n_students) students."""
        from app.models.user import User
        from app.models.session import Session as SessionModel

        students = [_student(i) for i in range(5)]
        session = _session(42, capacity=10)  # target = int(10 * 0.7) = 7 → min(7, 5) = 5

        db = MagicMock()
        user_q = MagicMock()
        user_q.filter.return_value = user_q
        user_q.all.return_value = students

        session_q = MagicMock()
        session_q.filter.return_value = session_q
        session_q.first.return_value = session

        def _q(model):
            if model is User:
                return user_q
            return session_q

        db.query.side_effect = _q

        result = auto_book_students(db, session_ids=[42])

        assert 42 in result
        assert len(result[42]) == 5
        assert db.add.call_count == 5
        db.commit.assert_called_once()

    def test_capacity_percentage_limits_bookings(self):
        """target_bookings = int(capacity * capacity_percentage/100)."""
        from app.models.user import User
        from app.models.session import Session as SessionModel

        students = [_student(i) for i in range(10)]
        session = _session(1, capacity=4)  # target = int(4 * 0.5) = 2

        db = MagicMock()
        user_q = MagicMock()
        user_q.filter.return_value = user_q
        user_q.all.return_value = students

        session_q = MagicMock()
        session_q.filter.return_value = session_q
        session_q.first.return_value = session

        def _q(model):
            if model is User:
                return user_q
            return session_q

        db.query.side_effect = _q

        result = auto_book_students(db, session_ids=[1], capacity_percentage=50)

        assert 1 in result
        assert len(result[1]) == 2  # min(2, 10) = 2

    def test_bookings_map_contains_correct_user_ids(self):
        """Lines 65-77: result maps session_id → list of student user_ids."""
        from app.models.user import User
        from app.models.session import Session as SessionModel

        students = [_student(100), _student(200)]
        session = _session(7, capacity=100)  # target = 70, min(70, 2) = 2

        db = MagicMock()
        user_q = MagicMock()
        user_q.filter.return_value = user_q
        user_q.all.return_value = students

        session_q = MagicMock()
        session_q.filter.return_value = session_q
        session_q.first.return_value = session

        def _q(model):
            if model is User:
                return user_q
            return session_q

        db.query.side_effect = _q

        result = auto_book_students(db, session_ids=[7])

        assert result[7] == [100, 200]

    def test_multiple_sessions_mixed_found_not_found(self):
        """Session found → booked; session not found → skipped."""
        from app.models.user import User
        from app.models.session import Session as SessionModel

        students = [_student(1)]
        session_found = _session(1, capacity=10)

        db = MagicMock()
        user_q = MagicMock()
        user_q.filter.return_value = user_q
        user_q.all.return_value = students

        returns = iter([session_found, None])
        session_q = MagicMock()
        session_q.filter.return_value = session_q
        session_q.first.side_effect = lambda: next(returns)

        def _q(model):
            if model is User:
                return user_q
            return session_q

        db.query.side_effect = _q

        result = auto_book_students(db, session_ids=[1, 999])

        assert 1 in result
        assert 999 not in result

    def test_booking_status_is_confirmed(self):
        """Created Booking objects have status=CONFIRMED (line 72)."""
        from app.models.user import User
        from app.models.session import Session as SessionModel
        from app.models.booking import Booking, BookingStatus

        students = [_student(5)]
        session = _session(10, capacity=2)

        db = MagicMock()
        user_q = MagicMock()
        user_q.filter.return_value = user_q
        user_q.all.return_value = students

        session_q = MagicMock()
        session_q.filter.return_value = session_q
        session_q.first.return_value = session

        added_objects = []
        db.add.side_effect = added_objects.append

        def _q(model):
            if model is User:
                return user_q
            return session_q

        db.query.side_effect = _q

        auto_book_students(db, session_ids=[10])

        assert len(added_objects) == 1
        booking = added_objects[0]
        assert booking.status == BookingStatus.CONFIRMED
        assert booking.session_id == 10
        assert booking.user_id == 5
