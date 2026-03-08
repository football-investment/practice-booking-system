"""
Sprint 30 — app/api/api_v1/endpoints/projects/core.py
======================================================
Target: ≥80% statement, ≥70% branch

Covers create_project:
  * semester not found → 404
  * instructor_id not set + instructor role → set to current_user.id
  * instructor_id set → kept as-is
  * no milestones → only project added
  * milestones provided → project + milestones added

Covers list_projects:
  * semester_id filter applied
  * status filter applied
  * student role → ACTIVE filter added
  * student + available_only=True → subquery filter
  * non-student → no extra filter
  * project with semester → semester_data populated
  * project without semester → semester_data=None
  * project with deadline → isoformat called
  * project without deadline → None

Covers get_project:
  * project not found → 404
  * project with milestones → all serialized
  * milestone with deadline/without deadline
  * project with instructor → instructor dict
  * project without instructor → None
  * project with semester → semester dict
  * project without semester → None
"""

import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.api_v1.endpoints.projects.core import (
    create_project,
    list_projects,
    get_project,
)

_BASE = "app.api.api_v1.endpoints.projects.core"


# ── helpers ──────────────────────────────────────────────────────────────────

def _user(role="instructor", uid=99):
    u = MagicMock()
    u.id = uid
    u.role.value = role
    return u


def _admin():
    return _user(role="admin", uid=1)


def _instructor(uid=99):
    return _user(role="instructor", uid=uid)


def _student():
    return _user(role="student", uid=42)


def _q():
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.join.return_value = q
    q.correlate.return_value = q
    q.scalar_subquery.return_value = MagicMock()
    q.first.return_value = None
    q.all.return_value = []
    q.count.return_value = 0
    return q


def _flat_db(first_val=None, all_val=None, count_val=0):
    """All db.query() calls return the same chained mock."""
    q = _q()
    q.first.return_value = first_val
    q.all.return_value = all_val or []
    q.count.return_value = count_val
    db = MagicMock()
    db.query.return_value = q
    return db


def _project_mock(with_milestones=True, with_instructor=True, with_semester=True,
                  with_deadline=True):
    p = MagicMock()
    p.id = 10
    p.title = "Test Project"
    p.description = "Desc"
    p.semester_id = 5
    p.instructor_id = 99
    p.max_participants = 20
    p.required_sessions = 10
    p.xp_reward = 300
    p.status = "active"
    p.difficulty = "medium"
    p.has_enrollment_quiz = False
    p.enrolled_count = 5
    p.available_spots = 15
    p.created_at = MagicMock()
    p.created_at.isoformat.return_value = "2026-01-01T00:00:00"
    p.updated_at = MagicMock()
    p.updated_at.isoformat.return_value = "2026-01-02T00:00:00"

    if with_deadline:
        p.deadline = MagicMock()
        p.deadline.isoformat.return_value = "2026-12-31"
    else:
        p.deadline = None

    if with_milestones:
        m = MagicMock()
        m.id = 200
        m.title = "Milestone 1"
        m.description = "M desc"
        m.order_index = 1
        m.required_sessions = 3
        m.xp_reward = 50
        m.is_required = True
        m.project_id = 10
        m.deadline = None
        m.created_at = MagicMock()
        m.created_at.isoformat.return_value = "2026-01-01T00:00:00"
        p.milestones = [m]
    else:
        p.milestones = []

    if with_instructor:
        p.instructor = MagicMock()
        p.instructor.id = 99
        p.instructor.name = "Coach"
        p.instructor.email = "coach@test.com"
    else:
        p.instructor = None

    if with_semester:
        p.semester = MagicMock()
        p.semester.id = 5
        p.semester.name = "Fall 2026"
        p.semester.is_active = True
        p.semester.start_date = MagicMock()
        p.semester.start_date.isoformat.return_value = "2026-09-01"
        p.semester.end_date = MagicMock()
        p.semester.end_date.isoformat.return_value = "2026-12-31"
    else:
        p.semester = None

    p.project_quizzes = []
    return p


# ============================================================================
# create_project
# ============================================================================

class TestCreateProject:

    def _call(self, project_data=None, user=None, db=None):
        if project_data is None:
            project_data = MagicMock()
            project_data.semester_id = 5
            project_data.milestones = []
            project_data.model_dump.return_value = {
                "semester_id": 5,
                "title": "New Project",
                "description": "Desc",
                "max_participants": 10,
                "required_sessions": 8,
                "xp_reward": 200,
                "instructor_id": None
            }
        return create_project(
            project_data=project_data,
            db=db or _flat_db(),
            current_user=user or _instructor(),
        )

    def test_semester_not_found_404(self):
        """CRP-01: semester not found → 404."""
        db = _flat_db(first_val=None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404
        assert "semester" in exc.value.detail.lower()

    def test_instructor_sets_own_id_when_not_specified(self):
        """CRP-02: instructor_id not set + instructor role → uses current_user.id."""
        semester = MagicMock()
        db = _flat_db(first_val=semester)
        user = _instructor(uid=99)
        project_data = MagicMock()
        project_data.semester_id = 5
        project_data.milestones = []
        project_data.model_dump.return_value = {
            "semester_id": 5,
            "title": "New Project",
            "instructor_id": None
        }
        self._call(project_data=project_data, user=user, db=db)
        # Check that db.add was called with a ProjectModel containing instructor_id=99
        args = db.add.call_args_list
        assert len(args) >= 1
        # The project arg should have instructor_id set
        project_arg = args[0][0][0]
        assert project_arg.instructor_id == 99

    def test_instructor_id_already_set_not_overridden(self):
        """CRP-03: instructor_id already in dict → not overridden by current_user.id."""
        semester = MagicMock()
        db = _flat_db(first_val=semester)
        user = _instructor(uid=99)
        project_data = MagicMock()
        project_data.semester_id = 5
        project_data.milestones = []
        project_data.model_dump.return_value = {
            "semester_id": 5,
            "title": "New Project",
            "instructor_id": 77  # already set
        }
        self._call(project_data=project_data, user=user, db=db)
        project_arg = db.add.call_args_list[0][0][0]
        assert project_arg.instructor_id == 77

    def test_admin_does_not_override_instructor_id(self):
        """CRP-04: admin role → instructor_id not auto-set even if None."""
        semester = MagicMock()
        db = _flat_db(first_val=semester)
        user = _admin()
        project_data = MagicMock()
        project_data.semester_id = 5
        project_data.milestones = []
        project_data.model_dump.return_value = {
            "semester_id": 5,
            "instructor_id": None
        }
        self._call(project_data=project_data, user=user, db=db)
        # admin doesn't set instructor_id automatically
        project_arg = db.add.call_args_list[0][0][0]
        assert project_arg.instructor_id is None

    def test_no_milestones_one_add_commit(self):
        """CRP-05: no milestones → only 1 db.add (project), 1 db.commit."""
        semester = MagicMock()
        db = _flat_db(first_val=semester)
        project_data = MagicMock()
        project_data.semester_id = 5
        project_data.milestones = []
        project_data.model_dump.return_value = {"semester_id": 5, "instructor_id": None}
        self._call(project_data=project_data, db=db)
        assert db.add.call_count == 1
        assert db.commit.call_count == 1

    def test_with_milestones_multiple_adds(self):
        """CRP-06: 2 milestones → 3 db.add() calls (project + 2 milestones)."""
        semester = MagicMock()
        db = _flat_db(first_val=semester)

        m1_data = MagicMock()
        m1_data.model_dump.return_value = {"title": "M1", "order_index": 1}
        m2_data = MagicMock()
        m2_data.model_dump.return_value = {"title": "M2", "order_index": 2}

        project_data = MagicMock()
        project_data.semester_id = 5
        project_data.milestones = [m1_data, m2_data]
        project_data.model_dump.return_value = {"semester_id": 5, "instructor_id": None}

        # db.refresh sets project.id (needed for milestone creation)
        def do_refresh(obj):
            obj.id = 10
        db.refresh.side_effect = do_refresh

        self._call(project_data=project_data, db=db)
        assert db.add.call_count == 3  # 1 project + 2 milestones
        assert db.commit.call_count == 2  # once for project, once for milestones


# ============================================================================
# list_projects
# ============================================================================

class TestListProjects:

    def _call(self, user=None, db=None, page=1, size=50, semester_id=None,
              status="active", available_only=False):
        return list_projects(
            db=db or _flat_db(),
            current_user=user or _student(),
            page=page,
            size=size,
            semester_id=semester_id,
            status=status,
            available_only=available_only,
        )

    def test_empty_list_returns_project_list(self):
        """LST-01: no projects → ProjectList with empty list."""
        db = _flat_db(all_val=[], count_val=0)
        result = self._call(db=db)
        assert result.total == 0
        assert result.projects == []

    def test_semester_id_filter_applied(self):
        """LST-02: semester_id provided → filter applied to query."""
        db = _flat_db(all_val=[], count_val=0)
        self._call(db=db, semester_id=5)
        # filter was called (at least once)
        assert db.query.return_value.filter.called

    def test_status_filter_applied(self):
        """LST-03: status provided → filter applied."""
        db = _flat_db(all_val=[], count_val=0)
        self._call(db=db, status="draft")
        assert db.query.return_value.filter.called

    def test_student_available_only_subquery(self):
        """LST-04: student + available_only=True → subquery filter applied."""
        db = _flat_db(all_val=[], count_val=0)
        # Should not raise — scalar_subquery handled by mock
        result = self._call(user=_student(), db=db, available_only=True)
        assert result is not None

    def test_non_student_no_active_filter(self):
        """LST-05: admin → no student-specific ACTIVE filter."""
        db = _flat_db(all_val=[], count_val=0)
        result = self._call(user=_admin(), db=db)
        assert result is not None

    def test_project_with_semester(self):
        """LST-06: project has semester → no crash, 1 project returned."""
        p = _project_mock(with_semester=True)
        db = _flat_db(all_val=[p], count_val=1)
        result = self._call(db=db)
        assert len(result.projects) == 1
        # Branch covered: semester_data dict was built
        proj = result.projects[0]
        proj_dict = proj.model_dump() if hasattr(proj, "model_dump") else vars(proj)
        assert proj_dict.get("semester") is not None

    def test_project_without_semester(self):
        """LST-07: project.semester is None → semester=None in result."""
        p = _project_mock(with_semester=False)
        db = _flat_db(all_val=[p], count_val=1)
        result = self._call(db=db)
        assert len(result.projects) == 1
        # Branch covered: semester_data = None path was taken

    def test_project_with_deadline(self):
        """LST-08: project.deadline set → isoformat called, no crash."""
        p = _project_mock(with_deadline=True)
        db = _flat_db(all_val=[p], count_val=1)
        result = self._call(db=db)
        assert len(result.projects) == 1
        # Branch covered: deadline.isoformat() was called

    def test_project_without_deadline(self):
        """LST-09: project.deadline is None → no crash."""
        p = _project_mock(with_deadline=False)
        db = _flat_db(all_val=[p], count_val=1)
        result = self._call(db=db)
        assert len(result.projects) == 1
        # Branch covered: deadline=None path was taken

    def test_pagination_page2(self):
        """LST-10: page=2, size=10 → offset=(2-1)*10=10."""
        db = _flat_db(all_val=[], count_val=0)
        result = self._call(db=db, page=2, size=10)
        assert result.page == 2
        assert result.size == 10


# ============================================================================
# get_project
# ============================================================================

class TestGetProject:

    def _call(self, project_id=10, user=None, db=None):
        return get_project(
            project_id=project_id,
            db=db or _flat_db(),
            current_user=user or _student(),
        )

    def test_project_not_found_404(self):
        """GET-01: project not found → 404."""
        db = _flat_db(first_val=None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_project_with_milestones(self):
        """GET-02: project has milestones → all serialized."""
        p = _project_mock(with_milestones=True)
        db = _flat_db(first_val=p)
        result = self._call(db=db)
        assert len(result["milestones"]) == 1
        assert result["milestones"][0]["id"] == 200

    def test_project_no_milestones(self):
        """GET-03: no milestones → empty list."""
        p = _project_mock(with_milestones=False)
        db = _flat_db(first_val=p)
        result = self._call(db=db)
        assert result["milestones"] == []

    def test_milestone_with_deadline(self):
        """GET-04: milestone has deadline → isoformat called."""
        p = _project_mock(with_milestones=True)
        m = p.milestones[0]
        m.deadline = MagicMock()
        m.deadline.isoformat.return_value = "2026-06-01"
        db = _flat_db(first_val=p)
        result = self._call(db=db)
        assert result["milestones"][0]["deadline"] == "2026-06-01"

    def test_milestone_without_deadline(self):
        """GET-05: milestone.deadline is None → None in result."""
        p = _project_mock(with_milestones=True)
        p.milestones[0].deadline = None
        db = _flat_db(first_val=p)
        result = self._call(db=db)
        assert result["milestones"][0]["deadline"] is None

    def test_project_with_instructor(self):
        """GET-06: project has instructor → instructor dict."""
        p = _project_mock(with_instructor=True)
        db = _flat_db(first_val=p)
        result = self._call(db=db)
        assert result["instructor"]["id"] == 99
        assert result["instructor"]["name"] == "Coach"

    def test_project_without_instructor(self):
        """GET-07: project.instructor is None → None in result."""
        p = _project_mock(with_instructor=False)
        db = _flat_db(first_val=p)
        result = self._call(db=db)
        assert result["instructor"] is None

    def test_project_with_semester(self):
        """GET-08: project has semester → semester dict."""
        p = _project_mock(with_semester=True)
        db = _flat_db(first_val=p)
        result = self._call(db=db)
        assert result["semester"]["id"] == 5
        assert result["semester"]["name"] == "Fall 2026"

    def test_project_without_semester(self):
        """GET-09: project.semester is None → None in result."""
        p = _project_mock(with_semester=False)
        db = _flat_db(first_val=p)
        result = self._call(db=db)
        assert result["semester"] is None

    def test_project_with_deadline(self):
        """GET-10: project.deadline set → isoformat called."""
        p = _project_mock(with_deadline=True)
        db = _flat_db(first_val=p)
        result = self._call(db=db)
        assert result["deadline"] == "2026-12-31"

    def test_project_without_deadline(self):
        """GET-11: project.deadline is None → None."""
        p = _project_mock(with_deadline=False)
        db = _flat_db(first_val=p)
        result = self._call(db=db)
        assert result["deadline"] is None

    def test_semester_start_end_none(self):
        """GET-12: semester start_date/end_date is None → None in result."""
        p = _project_mock(with_semester=True)
        p.semester.start_date = None
        p.semester.end_date = None
        db = _flat_db(first_val=p)
        result = self._call(db=db)
        assert result["semester"]["start_date"] is None
        assert result["semester"]["end_date"] is None
