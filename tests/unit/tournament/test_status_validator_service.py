"""
Tests for tournament/status_validator.py — missing branch coverage.

Missing targets:
  Lines 104-112: ENROLLMENT_CLOSED transition with tournament_type_id set
    → loads TournamentType from DB via _sa_instance_state.session
  Lines 132-140: IN_PROGRESS transition with tournament_type_id set
    → same pattern
"""
import pytest
from unittest.mock import MagicMock

from app.services.tournament.status_validator import validate_status_transition


# ──────────────────── helpers ────────────────────


def _active_enrollment():
    e = MagicMock()
    e.is_active = True
    return e


def _tournament(
    status="ENROLLMENT_OPEN",
    type_id=None,
    master_id=1,
    max_players=10,
    enrollments=None,
    sessions=None,
    campus_id=1,
    name="Test Tournament",
    start_date="2026-01-01",
    end_date="2026-12-31",
):
    t = MagicMock()
    t.tournament_status = status
    t.tournament_type_id = type_id
    t.master_instructor_id = master_id
    t.max_players = max_players
    t.campus_id = campus_id
    t.enrollments = enrollments or []
    t.sessions = sessions or [MagicMock()]
    t.name = name
    t.start_date = start_date
    t.end_date = end_date
    return t


def _sa_state(db):
    """Mock _sa_instance_state with a live DB session."""
    state = MagicMock()
    state.session = db
    return state


def _type_db(min_players, found=True):
    """DB mock that returns a TournamentType with given min_players."""
    db = MagicMock()
    tt = MagicMock()
    tt.min_players = min_players
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = tt if found else None
    db.query.return_value = q
    return db


# ──────────────────── ENROLLMENT_CLOSED with tournament_type_id ────────────────────


class TestEnrollmentClosedWithTournamentType:
    """Lines 104-112: ENROLLMENT_OPEN→ENROLLMENT_CLOSED when type_id is set."""

    def test_loads_type_min_players_enough_players(self):
        """Type min_players=2; 2 active enrollments → valid."""
        db = _type_db(min_players=2)
        enrollments = [_active_enrollment(), _active_enrollment()]
        t = _tournament(
            status="ENROLLMENT_OPEN", type_id=42, enrollments=enrollments
        )
        t.__dict__["_sa_instance_state"] = _sa_state(db)

        is_valid, err = validate_status_transition(
            "ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", t
        )

        assert is_valid is True
        assert err is None

    def test_loads_type_min_players_not_enough(self):
        """Type min_players=5; only 2 enrolled → invalid, message mentions 5."""
        db = _type_db(min_players=5)
        enrollments = [_active_enrollment(), _active_enrollment()]
        t = _tournament(
            status="ENROLLMENT_OPEN", type_id=42, enrollments=enrollments
        )
        t.__dict__["_sa_instance_state"] = _sa_state(db)

        is_valid, err = validate_status_transition(
            "ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", t
        )

        assert is_valid is False
        assert "5" in err

    def test_tournament_type_not_found_fallback_2(self):
        """Type query returns None → fallback min_players=2 → 2 enrollments ok."""
        db = _type_db(min_players=2, found=False)
        enrollments = [_active_enrollment(), _active_enrollment()]
        t = _tournament(
            status="ENROLLMENT_OPEN", type_id=99, enrollments=enrollments
        )
        t.__dict__["_sa_instance_state"] = _sa_state(db)

        is_valid, err = validate_status_transition(
            "ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", t
        )

        # fallback min=2, 2 players → passes
        assert is_valid is True

    def test_no_sa_session_uses_fallback_min_2(self):
        """_sa_instance_state.session is None → fallback min=2."""
        enrollments = [_active_enrollment(), _active_enrollment()]
        t = _tournament(
            status="ENROLLMENT_OPEN", type_id=42, enrollments=enrollments
        )
        state = MagicMock()
        state.session = None
        t.__dict__["_sa_instance_state"] = state

        is_valid, err = validate_status_transition(
            "ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", t
        )

        assert is_valid is True

    def test_rollback_in_progress_to_enrollment_closed_skips_guard(self):
        """IN_PROGRESS→ENROLLMENT_CLOSED is admin rollback — player count not checked."""
        t = _tournament(status="IN_PROGRESS", type_id=42, enrollments=[])
        # No _sa_instance_state needed since guard is skipped for rollback path

        is_valid, err = validate_status_transition(
            "IN_PROGRESS", "ENROLLMENT_CLOSED", t
        )

        assert is_valid is True


# ──────────────────── IN_PROGRESS with tournament_type_id ────────────────────


class TestInProgressWithTournamentType:
    """CHECK_IN_OPEN→IN_PROGRESS when type_id is set (formerly ENROLLMENT_CLOSED→IN_PROGRESS)."""

    def test_loads_type_min_players_enough(self):
        """Type min_players=3; 4 enrolled → valid."""
        db = _type_db(min_players=3)
        enrollments = [_active_enrollment() for _ in range(4)]
        t = _tournament(
            status="CHECK_IN_OPEN", type_id=10, enrollments=enrollments
        )
        t.__dict__["_sa_instance_state"] = _sa_state(db)

        is_valid, err = validate_status_transition(
            "CHECK_IN_OPEN", "IN_PROGRESS", t
        )

        assert is_valid is True

    def test_loads_type_min_players_not_enough(self):
        """Type min_players=5; only 2 enrolled → invalid, message mentions 5."""
        db = _type_db(min_players=5)
        enrollments = [_active_enrollment(), _active_enrollment()]
        t = _tournament(
            status="CHECK_IN_OPEN", type_id=10, enrollments=enrollments
        )
        t.__dict__["_sa_instance_state"] = _sa_state(db)

        is_valid, err = validate_status_transition(
            "CHECK_IN_OPEN", "IN_PROGRESS", t
        )

        assert is_valid is False
        assert "5" in err

    def test_type_not_found_fallback_min_2(self):
        """Type query returns None → fallback min=2 → 2 players passes."""
        db = _type_db(min_players=2, found=False)
        enrollments = [_active_enrollment(), _active_enrollment()]
        t = _tournament(
            status="CHECK_IN_OPEN", type_id=5, enrollments=enrollments
        )
        t.__dict__["_sa_instance_state"] = _sa_state(db)

        is_valid, err = validate_status_transition(
            "CHECK_IN_OPEN", "IN_PROGRESS", t
        )

        assert is_valid is True

    def test_no_sa_session_fallback_min_2(self):
        """session=None in _sa_instance_state → fallback min=2."""
        enrollments = [_active_enrollment(), _active_enrollment()]
        t = _tournament(
            status="CHECK_IN_OPEN", type_id=5, enrollments=enrollments
        )
        state = MagicMock()
        state.session = None
        t.__dict__["_sa_instance_state"] = state

        is_valid, err = validate_status_transition(
            "CHECK_IN_OPEN", "IN_PROGRESS", t
        )

        assert is_valid is True

    def test_no_instructor_blocks_in_progress(self):
        """No master_instructor_id → fails before type lookup."""
        t = _tournament(
            status="CHECK_IN_OPEN", type_id=10, master_id=None, enrollments=[]
        )

        is_valid, err = validate_status_transition(
            "CHECK_IN_OPEN", "IN_PROGRESS", t
        )

        assert is_valid is False
        assert "instructor" in err.lower()
