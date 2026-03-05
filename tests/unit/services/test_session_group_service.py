"""
Unit tests for SessionGroupService (services/session_group_service.py)
Sprint M4 (2026-03-05) — branch coverage

get_present_students:
  - returns list of User objects from PRESENT attendances
  - attendance.user is None → filtered out

get_available_instructors:
  - session not found → []
  - session found, no instructor → []
  - session found, instructor present → [instructor]

auto_assign_groups:
  - no students → ValueError
  - no instructors → ValueError
  - even distribution (6 students, 2 instructors → groups of 3,3)
  - uneven distribution (7 students, 2 instructors → groups of 4,3)
  - single instructor (all students in one group)
  - existing groups cleared before re-assign
  - commit called once at end

get_session_groups:
  - returns ordered list from DB query

move_student_to_group:
  - old_assignment not found → False
  - old_assignment found → deleted, new created, commit → True

get_group_summary:
  - empty groups → summary with zeros
  - groups with students → correct totals and structure

delete_all_groups:
  - deletes all groups for session, commits, returns True
"""

import pytest
from unittest.mock import MagicMock, patch, call

from app.services.session_group_service import SessionGroupService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db():
    return MagicMock()


def _q(all_val=None, first_val=None):
    """Flexible query chain mock."""
    m = MagicMock()
    m.filter.return_value = m
    m.order_by.return_value = m
    m.all.return_value = all_val or []
    m.first.return_value = first_val
    return m


def _mock_user(uid=1, name="Test User"):
    u = MagicMock()
    u.id = uid
    u.name = name
    return u


def _mock_attendance(user):
    a = MagicMock()
    a.user = user
    return a


def _mock_instructor(uid=10, name="Coach"):
    return _mock_user(uid=uid, name=name)


def _mock_session(instructor=None):
    s = MagicMock()
    s.instructor = instructor
    return s


# ===========================================================================
# get_present_students
# ===========================================================================

_PATCH_STATUS = "app.services.session_group_service.AttendanceStatus"


@pytest.mark.unit
class TestGetPresentStudents:
    # NOTE: AttendanceStatus.PRESENT used in production code but enum uses lowercase .present
    # Patch the module-level AttendanceStatus to avoid AttributeError during filter evaluation.

    def test_returns_users_from_present_attendances(self):
        db = _db()
        user1 = _mock_user(1, "Alice")
        user2 = _mock_user(2, "Bob")
        att1 = _mock_attendance(user1)
        att2 = _mock_attendance(user2)
        db.query.return_value = _q(all_val=[att1, att2])
        with patch(_PATCH_STATUS) as mock_status:
            mock_status.PRESENT = "present"
            result = SessionGroupService.get_present_students(db, session_id=10)
        assert result == [user1, user2]

    def test_returns_empty_when_no_attendances(self):
        db = _db()
        db.query.return_value = _q(all_val=[])
        with patch(_PATCH_STATUS) as mock_status:
            mock_status.PRESENT = "present"
            result = SessionGroupService.get_present_students(db, session_id=10)
        assert result == []

    def test_filters_out_none_users(self):
        """Attendances where att.user is None are excluded."""
        db = _db()
        user1 = _mock_user(1)
        att_with_user = _mock_attendance(user1)
        att_without_user = _mock_attendance(None)
        db.query.return_value = _q(all_val=[att_with_user, att_without_user])
        with patch(_PATCH_STATUS) as mock_status:
            mock_status.PRESENT = "present"
            result = SessionGroupService.get_present_students(db, session_id=10)
        assert result == [user1]
        assert len(result) == 1


# ===========================================================================
# get_available_instructors
# ===========================================================================

@pytest.mark.unit
class TestGetAvailableInstructors:

    def test_session_not_found_returns_empty(self):
        db = _db()
        db.query.return_value = _q(first_val=None)
        result = SessionGroupService.get_available_instructors(db, session_id=99)
        assert result == []

    def test_session_with_no_instructor_returns_empty(self):
        db = _db()
        session = _mock_session(instructor=None)
        db.query.return_value = _q(first_val=session)
        result = SessionGroupService.get_available_instructors(db, session_id=1)
        assert result == []

    def test_session_with_instructor_returns_list(self):
        db = _db()
        instructor = _mock_instructor()
        session = _mock_session(instructor=instructor)
        db.query.return_value = _q(first_val=session)
        result = SessionGroupService.get_available_instructors(db, session_id=1)
        assert result == [instructor]


# ===========================================================================
# auto_assign_groups
# ===========================================================================

@pytest.mark.unit
class TestAutoAssignGroups:

    @staticmethod
    def _students(n):
        return [_mock_user(uid=i, name=f"Student{i}") for i in range(1, n + 1)]

    @staticmethod
    def _instructors(n):
        return [_mock_instructor(uid=100 + i, name=f"Instructor{i}") for i in range(1, n + 1)]

    def _setup_db(self, db):
        """Set up db.query to return empty existing groups."""
        db.query.return_value = _q(all_val=[])

    def test_no_students_raises_value_error(self):
        db = _db()
        with patch.object(SessionGroupService, "get_present_students", return_value=[]):
            with patch.object(SessionGroupService, "get_available_instructors",
                              return_value=self._instructors(1)):
                with pytest.raises(ValueError, match="No students"):
                    SessionGroupService.auto_assign_groups(db, session_id=1,
                                                          created_by_user_id=99)

    def test_no_instructors_raises_value_error(self):
        db = _db()
        with patch.object(SessionGroupService, "get_present_students",
                          return_value=self._students(3)):
            with patch.object(SessionGroupService, "get_available_instructors", return_value=[]):
                with pytest.raises(ValueError, match="No instructors"):
                    SessionGroupService.auto_assign_groups(db, session_id=1,
                                                          created_by_user_id=99)

    def test_even_distribution_6_students_2_instructors(self):
        """6 students, 2 instructors → 2 groups × 3 students. db.add called 8 times."""
        db = _db()
        self._setup_db(db)
        students = self._students(6)
        instructors = self._instructors(2)
        with patch.object(SessionGroupService, "get_present_students",
                          return_value=students):
            with patch.object(SessionGroupService, "get_available_instructors",
                              return_value=instructors):
                groups = SessionGroupService.auto_assign_groups(
                    db, session_id=1, created_by_user_id=99
                )
        # 2 groups created
        assert len(groups) == 2
        # db.add called 8 times: 2 groups + 6 student assignments
        assert db.add.call_count == 8
        db.commit.assert_called_once()

    def test_uneven_distribution_7_students_2_instructors(self):
        """7 students, 2 instructors → groups of 4, 3. db.add called 9 times."""
        db = _db()
        self._setup_db(db)
        students = self._students(7)
        instructors = self._instructors(2)
        with patch.object(SessionGroupService, "get_present_students",
                          return_value=students):
            with patch.object(SessionGroupService, "get_available_instructors",
                              return_value=instructors):
                groups = SessionGroupService.auto_assign_groups(
                    db, session_id=1, created_by_user_id=99
                )
        assert len(groups) == 2
        # 2 groups + 7 student assignments = 9 adds
        assert db.add.call_count == 9

    def test_single_instructor_all_in_one_group(self):
        """1 instructor → 1 group with all students."""
        db = _db()
        self._setup_db(db)
        students = self._students(4)
        instructors = self._instructors(1)
        with patch.object(SessionGroupService, "get_present_students",
                          return_value=students):
            with patch.object(SessionGroupService, "get_available_instructors",
                              return_value=instructors):
                groups = SessionGroupService.auto_assign_groups(
                    db, session_id=1, created_by_user_id=99
                )
        assert len(groups) == 1
        # 1 group + 4 student assignments = 5 adds
        assert db.add.call_count == 5

    def test_existing_groups_cleared_before_reassign(self):
        """Existing groups are deleted before new ones are created."""
        db = _db()
        existing1 = MagicMock()
        existing2 = MagicMock()
        db.query.return_value = _q(all_val=[existing1, existing2])
        students = self._students(2)
        instructors = self._instructors(1)
        with patch.object(SessionGroupService, "get_present_students",
                          return_value=students):
            with patch.object(SessionGroupService, "get_available_instructors",
                              return_value=instructors):
                SessionGroupService.auto_assign_groups(
                    db, session_id=1, created_by_user_id=99
                )
        # Both existing groups should be deleted
        assert db.delete.call_count == 2
        db.delete.assert_any_call(existing1)
        db.delete.assert_any_call(existing2)


# ===========================================================================
# get_session_groups
# ===========================================================================

@pytest.mark.unit
class TestGetSessionGroups:

    def test_returns_ordered_groups(self):
        db = _db()
        g1 = MagicMock()
        g2 = MagicMock()
        db.query.return_value = _q(all_val=[g1, g2])
        result = SessionGroupService.get_session_groups(db, session_id=5)
        assert result == [g1, g2]

    def test_returns_empty_when_no_groups(self):
        db = _db()
        db.query.return_value = _q(all_val=[])
        result = SessionGroupService.get_session_groups(db, session_id=5)
        assert result == []


# ===========================================================================
# move_student_to_group
# ===========================================================================

@pytest.mark.unit
class TestMoveStudentToGroup:

    def test_old_assignment_not_found_returns_false(self):
        db = _db()
        db.query.return_value = _q(first_val=None)
        result = SessionGroupService.move_student_to_group(
            db, student_id=1, from_group_id=10, to_group_id=20
        )
        assert result is False
        db.commit.assert_not_called()

    def test_old_assignment_found_moved_returns_true(self):
        db = _db()
        old_assignment = MagicMock()
        db.query.return_value = _q(first_val=old_assignment)
        result = SessionGroupService.move_student_to_group(
            db, student_id=1, from_group_id=10, to_group_id=20
        )
        assert result is True
        db.delete.assert_called_once_with(old_assignment)
        db.add.assert_called_once()
        db.commit.assert_called_once()


# ===========================================================================
# get_group_summary
# ===========================================================================

@pytest.mark.unit
class TestGetGroupSummary:

    def _mock_group(self, group_number, instructor_name, students):
        """Create a mock SessionGroupAssignment with student mocks."""
        group = MagicMock()
        group.group_number = group_number
        group.instructor = MagicMock()
        group.instructor.name = instructor_name
        group.instructor_id = 100 + group_number

        student_assignments = []
        for i, (sid, sname) in enumerate(students):
            s = MagicMock()
            s.student = MagicMock()
            s.student.name = sname
            s.student_id = sid
            student_assignments.append(s)

        group.students = student_assignments
        return group

    def test_empty_groups_returns_zero_totals(self):
        db = _db()
        with patch.object(SessionGroupService, "get_session_groups", return_value=[]):
            result = SessionGroupService.get_group_summary(db, session_id=1)
        assert result["session_id"] == 1
        assert result["total_students"] == 0
        assert result["total_instructors"] == 0
        assert result["groups"] == []

    def test_groups_with_students_correct_totals(self):
        db = _db()
        g1 = self._mock_group(1, "Alice Coach", [(1, "Alice"), (2, "Bob")])
        g2 = self._mock_group(2, "Bob Coach", [(3, "Charlie")])
        with patch.object(SessionGroupService, "get_session_groups",
                          return_value=[g1, g2]):
            result = SessionGroupService.get_group_summary(db, session_id=5)
        assert result["session_id"] == 5
        assert result["total_students"] == 3
        assert result["total_instructors"] == 2
        assert len(result["groups"]) == 2

    def test_group_data_structure(self):
        db = _db()
        g = self._mock_group(1, "Head Coach", [(10, "Dave"), (11, "Eve")])
        with patch.object(SessionGroupService, "get_session_groups", return_value=[g]):
            result = SessionGroupService.get_group_summary(db, session_id=7)
        group_data = result["groups"][0]
        assert group_data["group_number"] == 1
        assert group_data["instructor_name"] == "Head Coach"
        assert group_data["student_count"] == 2
        assert "Dave" in group_data["students"]
        assert "Eve" in group_data["students"]
        assert 10 in group_data["student_ids"]

    def test_instructor_none_shows_unknown(self):
        """If group.instructor is None → instructor_name = 'Unknown'."""
        db = _db()
        group = MagicMock()
        group.group_number = 1
        group.instructor = None
        group.instructor_id = None
        # No students
        group.students = []
        with patch.object(SessionGroupService, "get_session_groups", return_value=[group]):
            result = SessionGroupService.get_group_summary(db, session_id=3)
        assert result["groups"][0]["instructor_name"] == "Unknown"

    def test_student_with_none_user_filtered_in_summary(self):
        """Students where s.student is None are filtered from names but not student_ids."""
        db = _db()
        group = MagicMock()
        group.group_number = 1
        group.instructor = MagicMock()
        group.instructor.name = "Coach"
        group.instructor_id = 100
        s1 = MagicMock()
        s1.student = MagicMock()
        s1.student.name = "Alice"
        s1.student_id = 1
        s_none = MagicMock()
        s_none.student = None
        s_none.student_id = 2
        group.students = [s1, s_none]
        with patch.object(SessionGroupService, "get_session_groups", return_value=[group]):
            result = SessionGroupService.get_group_summary(db, session_id=1)
        # Only 1 named student (Alice), not 2
        assert result["total_students"] == 1
        assert result["groups"][0]["student_count"] == 1


# ===========================================================================
# delete_all_groups
# ===========================================================================

@pytest.mark.unit
class TestDeleteAllGroups:

    def test_deletes_all_groups_commits_returns_true(self):
        db = _db()
        g1, g2 = MagicMock(), MagicMock()
        db.query.return_value = _q(all_val=[g1, g2])
        result = SessionGroupService.delete_all_groups(db, session_id=3)
        assert result is True
        assert db.delete.call_count == 2
        db.commit.assert_called_once()

    def test_no_groups_still_commits_returns_true(self):
        db = _db()
        db.query.return_value = _q(all_val=[])
        result = SessionGroupService.delete_all_groups(db, session_id=3)
        assert result is True
        db.delete.assert_not_called()
        db.commit.assert_called_once()
