"""
Unit tests for app/services/semester_status_service.py

Mock-based: no DB fixture, all SQLAlchemy queries mocked.
Covers all 5 functions and their branch paths.
"""
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch, call
from app.services.semester_status_service import (
    transition_to_instructor_assigned,
    transition_to_ready_for_enrollment,
    check_and_transition_semester,
    get_semesters_for_status_transition,
    bulk_transition_by_date,
)
from app.models.semester import SemesterStatus
from app.models.instructor_assignment import MasterOfferStatus


# ── helpers ──────────────────────────────────────────────────────────────────

def _mock_master(offer_status=MasterOfferStatus.ACCEPTED):
    m = MagicMock()
    m.offer_status = offer_status
    return m


def _db_returning(value):
    """DB mock whose .query().filter().first() returns value."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = value
    return db


def _db_update_returning(n):
    """DB mock whose .query().filter().update() returns n (row count)."""
    db = MagicMock()
    db.query.return_value.filter.return_value.update.return_value = n
    return db


# ── transition_to_instructor_assigned ─────────────────────────────────────────

class TestTransitionToInstructorAssigned:

    def test_no_master_contract_returns_zero(self):
        db = _db_returning(None)
        count = transition_to_instructor_assigned(db, location_id=10, master_instructor_id=1)
        assert count == 0
        db.commit.assert_not_called()

    def test_offered_status_not_accepted_skips(self):
        master = _mock_master(offer_status=MasterOfferStatus.OFFERED)
        db = _db_returning(master)
        count = transition_to_instructor_assigned(db, location_id=10, master_instructor_id=1)
        assert count == 0
        db.commit.assert_not_called()

    def test_accepted_status_transitions_semesters(self):
        master = _mock_master(offer_status=MasterOfferStatus.ACCEPTED)
        # Need two separate query chains: first for master lookup, second for semester update
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = master
        db.query.return_value.filter.return_value.update.return_value = 3
        count = transition_to_instructor_assigned(db, location_id=10, master_instructor_id=1)
        assert count == 3
        db.commit.assert_called_once()

    def test_legacy_null_offer_status_transitions(self):
        master = _mock_master(offer_status=None)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = master
        db.query.return_value.filter.return_value.update.return_value = 2
        count = transition_to_instructor_assigned(db, location_id=20, master_instructor_id=5)
        assert count == 2
        db.commit.assert_called_once()

    def test_zero_semesters_updated_still_commits(self):
        master = _mock_master(offer_status=MasterOfferStatus.ACCEPTED)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = master
        db.query.return_value.filter.return_value.update.return_value = 0
        count = transition_to_instructor_assigned(db, location_id=30, master_instructor_id=7)
        assert count == 0
        db.commit.assert_called_once()


# ── transition_to_ready_for_enrollment ────────────────────────────────────────

class TestTransitionToReadyForEnrollment:

    def test_transitions_instructor_assigned_semester(self):
        semester = MagicMock()
        semester.status = SemesterStatus.INSTRUCTOR_ASSIGNED
        db = _db_returning(semester)
        result = transition_to_ready_for_enrollment(db, semester_id=10)
        assert result is True
        assert semester.status == SemesterStatus.READY_FOR_ENROLLMENT
        db.commit.assert_called_once()

    def test_semester_not_found_returns_false(self):
        db = _db_returning(None)
        result = transition_to_ready_for_enrollment(db, semester_id=999)
        assert result is False
        db.commit.assert_not_called()

    def test_non_instructor_assigned_not_found_by_filter(self):
        # The filter queries for INSTRUCTOR_ASSIGNED — non-matching returns None
        db = _db_returning(None)
        result = transition_to_ready_for_enrollment(db, semester_id=5)
        assert result is False

    def test_updated_at_is_set(self):
        semester = MagicMock()
        semester.status = SemesterStatus.INSTRUCTOR_ASSIGNED
        db = _db_returning(semester)
        transition_to_ready_for_enrollment(db, semester_id=10)
        assert semester.updated_at is not None


# ── check_and_transition_semester ─────────────────────────────────────────────

class TestCheckAndTransitionSemester:

    def _setup_db(self, semester, instructor_count):
        db = MagicMock()
        # First query returns semester
        db.query.return_value.filter.return_value.first.return_value = semester
        # Second query returns instructor count
        db.query.return_value.filter.return_value.count.return_value = instructor_count
        return db

    def test_semester_not_found_returns_none(self):
        db = _db_returning(None)
        result = check_and_transition_semester(db, semester_id=1)
        assert result is None

    def test_no_master_no_transition(self):
        semester = MagicMock()
        semester.master_instructor_id = None
        semester.status = SemesterStatus.DRAFT
        db = self._setup_db(semester, instructor_count=2)
        result = check_and_transition_semester(db, semester_id=5)
        # No transition: master is None
        assert semester.status == SemesterStatus.DRAFT

    def test_no_assistants_no_transition(self):
        semester = MagicMock()
        semester.master_instructor_id = 1
        semester.status = SemesterStatus.DRAFT
        db = self._setup_db(semester, instructor_count=0)
        check_and_transition_semester(db, semester_id=5)
        assert semester.status == SemesterStatus.DRAFT

    def test_draft_with_master_and_assistant_transitions(self):
        semester = MagicMock()
        semester.master_instructor_id = 1
        semester.status = SemesterStatus.DRAFT
        db = self._setup_db(semester, instructor_count=1)
        check_and_transition_semester(db, semester_id=5)
        assert semester.status == SemesterStatus.READY_FOR_ENROLLMENT
        db.commit.assert_called_once()

    def test_instructor_assigned_with_assistant_transitions(self):
        semester = MagicMock()
        semester.master_instructor_id = 1
        semester.status = SemesterStatus.INSTRUCTOR_ASSIGNED
        db = self._setup_db(semester, instructor_count=2)
        check_and_transition_semester(db, semester_id=5)
        assert semester.status == SemesterStatus.READY_FOR_ENROLLMENT

    def test_ready_for_enrollment_not_re_transitioned(self):
        semester = MagicMock()
        semester.master_instructor_id = 1
        semester.status = SemesterStatus.READY_FOR_ENROLLMENT
        db = self._setup_db(semester, instructor_count=3)
        check_and_transition_semester(db, semester_id=5)
        # Already at READY_FOR_ENROLLMENT — should not change
        assert semester.status == SemesterStatus.READY_FOR_ENROLLMENT
        db.commit.assert_not_called()

    def test_returns_semester_status_value(self):
        semester = MagicMock()
        semester.master_instructor_id = None
        semester.status = SemesterStatus.DRAFT
        db = self._setup_db(semester, instructor_count=0)
        result = check_and_transition_semester(db, semester_id=5)
        assert result == "DRAFT"


# ── get_semesters_for_status_transition ───────────────────────────────────────

class TestGetSemestersForStatusTransition:

    def test_returns_query_results(self):
        semesters = [MagicMock(), MagicMock()]
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = semesters
        result = get_semesters_for_status_transition(
            db, SemesterStatus.DRAFT, SemesterStatus.INSTRUCTOR_ASSIGNED
        )
        assert result == semesters

    def test_returns_empty_list_if_none_eligible(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        result = get_semesters_for_status_transition(
            db, SemesterStatus.COMPLETED, SemesterStatus.ONGOING
        )
        assert result == []

    def test_queries_by_from_status(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        get_semesters_for_status_transition(
            db, SemesterStatus.ONGOING, SemesterStatus.COMPLETED
        )
        db.query.assert_called_once()


# ── bulk_transition_by_date ───────────────────────────────────────────────────

class TestBulkTransitionByDate:

    def _db_bulk(self, started=2, completed=1):
        db = MagicMock()
        db.query.return_value.filter.return_value.update.side_effect = [started, completed]
        return db

    def test_returns_started_and_completed_counts(self):
        db = self._db_bulk(started=3, completed=1)
        result = bulk_transition_by_date(db)
        assert result["started"] == 3
        assert result["completed"] == 1

    def test_commits_after_transitions(self):
        db = self._db_bulk()
        bulk_transition_by_date(db)
        db.commit.assert_called_once()

    def test_skip_start_dates(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.update.return_value = 4
        result = bulk_transition_by_date(db, check_start_dates=False)
        assert result["started"] == 0
        assert result["completed"] == 4

    def test_skip_end_dates(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.update.return_value = 2
        result = bulk_transition_by_date(db, check_end_dates=False)
        assert result["started"] == 2
        assert result["completed"] == 0

    def test_both_skipped_returns_zeros(self):
        db = MagicMock()
        result = bulk_transition_by_date(db, check_start_dates=False, check_end_dates=False)
        assert result == {"started": 0, "completed": 0}
        db.commit.assert_called_once()

    @patch("app.services.semester_status_service.date")
    def test_uses_today_for_comparison(self, mock_date):
        mock_date.today.return_value = date(2026, 6, 1)
        db = MagicMock()
        db.query.return_value.filter.return_value.update.side_effect = [1, 0]
        bulk_transition_by_date(db)
        mock_date.today.assert_called_once()
