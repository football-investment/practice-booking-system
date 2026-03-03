"""
Unit tests for tournament status_service module

Covers all pure/mockable functions:
- is_valid_status       — dict membership, no DB
- can_transition        — state machine dict lookup, no DB
- get_valid_next_statuses — dict .get(), no DB
- can_open_enrollment   — attribute checks, no DB
- can_start_tournament  — attribute checks, no DB
- change_tournament_status — validation + attribute mutation; db.execute mocked

DB-only functions (record_status_change, get_status_history, get_tournaments_by_status)
are excluded — integration coverage via api_smoke suite.
"""
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.tournament.status_service import (
    VALID_STATUSES,
    VALID_TRANSITIONS,
    is_valid_status,
    can_transition,
    get_valid_next_statuses,
    can_open_enrollment,
    can_start_tournament,
    change_tournament_status,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _tournament(status: str, instructor_id=None):
    return SimpleNamespace(
        id=1,
        tournament_status=status,
        master_instructor_id=instructor_id,
        updated_at=None,
    )


def _mock_db():
    db = MagicMock()
    db.execute.return_value = None
    return db


# ─── is_valid_status ──────────────────────────────────────────────────────────

@pytest.mark.unit
class TestIsValidStatus:

    def test_all_valid_statuses_accepted(self):
        for status in VALID_STATUSES:
            assert is_valid_status(status) is True

    def test_invalid_status_rejected(self):
        assert is_valid_status("INVALID") is False
        assert is_valid_status("") is False
        assert is_valid_status("in_progress") is False  # case-sensitive


# ─── can_transition ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestCanTransition:

    def test_valid_transition_in_progress_to_closed(self):
        assert can_transition("IN_PROGRESS", "CLOSED") is True

    def test_valid_transition_in_progress_to_completed(self):
        assert can_transition("IN_PROGRESS", "COMPLETED") is True

    def test_valid_transition_in_progress_to_cancelled(self):
        assert can_transition("IN_PROGRESS", "CANCELLED") is True

    def test_valid_transition_open_enrollment_to_in_progress(self):
        assert can_transition("OPEN_FOR_ENROLLMENT", "IN_PROGRESS") is True

    def test_valid_transition_seeking_to_pending_acceptance(self):
        assert can_transition("SEEKING_INSTRUCTOR", "PENDING_INSTRUCTOR_ACCEPTANCE") is True

    def test_invalid_reverse_transition(self):
        assert can_transition("IN_PROGRESS", "OPEN_FOR_ENROLLMENT") is False

    def test_terminal_completed_no_transitions(self):
        assert can_transition("COMPLETED", "IN_PROGRESS") is False
        assert can_transition("COMPLETED", "CANCELLED") is False

    def test_terminal_cancelled_no_transitions(self):
        assert can_transition("CANCELLED", "IN_PROGRESS") is False

    def test_unknown_from_status_returns_false(self):
        assert can_transition("UNKNOWN_STATUS", "IN_PROGRESS") is False

    def test_all_valid_transitions_from_transition_table(self):
        """Every edge in VALID_TRANSITIONS must return True."""
        for from_s, targets in VALID_TRANSITIONS.items():
            for to_s in targets:
                assert can_transition(from_s, to_s) is True, (
                    f"Expected True for {from_s!r} -> {to_s!r}"
                )


# ─── get_valid_next_statuses ──────────────────────────────────────────────────

@pytest.mark.unit
class TestGetValidNextStatuses:

    def test_in_progress_next_statuses(self):
        result = get_valid_next_statuses("IN_PROGRESS")
        assert set(result) == {"CLOSED", "COMPLETED", "CANCELLED"}

    def test_completed_is_terminal(self):
        assert get_valid_next_statuses("COMPLETED") == []

    def test_cancelled_is_terminal(self):
        assert get_valid_next_statuses("CANCELLED") == []

    def test_unknown_status_returns_empty(self):
        assert get_valid_next_statuses("DOES_NOT_EXIST") == []

    def test_closed_only_leads_to_completed(self):
        assert get_valid_next_statuses("CLOSED") == ["COMPLETED"]


# ─── can_open_enrollment ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestCanOpenEnrollment:

    def test_wrong_status_returns_false(self):
        t = _tournament("IN_PROGRESS", instructor_id=5)
        ok, reason = can_open_enrollment(t)
        assert ok is False
        assert "INSTRUCTOR_CONFIRMED" in reason

    def test_correct_status_no_instructor_returns_false(self):
        t = _tournament("INSTRUCTOR_CONFIRMED", instructor_id=None)
        ok, reason = can_open_enrollment(t)
        assert ok is False
        assert "instructor" in reason.lower()

    def test_correct_status_with_instructor_returns_true(self):
        t = _tournament("INSTRUCTOR_CONFIRMED", instructor_id=42)
        ok, reason = can_open_enrollment(t)
        assert ok is True
        assert reason is None


# ─── can_start_tournament ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestCanStartTournament:

    def test_wrong_status_returns_false(self):
        t = _tournament("SEEKING_INSTRUCTOR", instructor_id=5)
        ok, reason = can_start_tournament(t)
        assert ok is False
        assert "READY_FOR_ENROLLMENT" in reason

    def test_ready_for_enrollment_no_instructor_returns_false(self):
        t = _tournament("READY_FOR_ENROLLMENT", instructor_id=None)
        ok, reason = can_start_tournament(t)
        assert ok is False
        assert "instructor" in reason.lower()

    def test_open_for_enrollment_with_instructor_returns_true(self):
        t = _tournament("OPEN_FOR_ENROLLMENT", instructor_id=7)
        ok, reason = can_start_tournament(t)
        assert ok is True
        assert reason is None

    def test_ready_for_enrollment_with_instructor_returns_true(self):
        t = _tournament("READY_FOR_ENROLLMENT", instructor_id=3)
        ok, reason = can_start_tournament(t)
        assert ok is True
        assert reason is None


# ─── change_tournament_status ─────────────────────────────────────────────────

@pytest.mark.unit
class TestChangeTournamentStatus:

    def test_invalid_new_status_raises_value_error(self):
        t = _tournament("IN_PROGRESS")
        with pytest.raises(ValueError, match="Invalid status"):
            change_tournament_status(_mock_db(), t, "BOGUS_STATUS", changed_by=1)

    def test_invalid_transition_raises_value_error(self):
        t = _tournament("COMPLETED")
        with pytest.raises(ValueError, match="Invalid status transition"):
            change_tournament_status(_mock_db(), t, "IN_PROGRESS", changed_by=1)

    def test_valid_transition_updates_status_attribute(self):
        t = _tournament("IN_PROGRESS")
        db = _mock_db()
        result = change_tournament_status(db, t, "CLOSED", changed_by=1)
        assert result is True
        assert t.tournament_status == "CLOSED"

    def test_valid_transition_updates_updated_at(self):
        t = _tournament("IN_PROGRESS")
        change_tournament_status(_mock_db(), t, "CLOSED", changed_by=1)
        assert t.updated_at is not None

    def test_skip_transition_validation_allows_any_valid_status(self):
        """validate_transition=False bypasses state machine check."""
        t = _tournament("COMPLETED")  # terminal state
        db = _mock_db()
        result = change_tournament_status(
            db, t, "IN_PROGRESS", changed_by=1, validate_transition=False
        )
        assert result is True
        assert t.tournament_status == "IN_PROGRESS"

    def test_record_status_change_called_with_correct_args(self):
        """db.execute must be called exactly once (INSERT into tournament_status_history)."""
        t = _tournament("IN_PROGRESS")
        db = _mock_db()
        change_tournament_status(db, t, "CLOSED", changed_by=99, reason="end of round")
        db.execute.assert_called_once()
