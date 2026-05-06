"""
Unit tests for app/services/tournament/attendance_service.py

Stage 1+3 regression guards:
  CHK-ADMIN-01  checkin_player without instructor CHECKED_IN → succeeds (no 409)
  CHK-ADMIN-02  PROMOTION_EVENT bulk-enrolled user → admin can check in
  CHK-ADMIN-03  uncheckin_player → tournament_checked_in_at cleared on SemesterEnrollment
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

from fastapi import HTTPException

from app.services.tournament.attendance_service import (
    checkin_player,
    checkin_team,
    uncheckin_player,
)
from app.models.team import TournamentPlayerCheckin, TournamentTeamEnrollment
from app.models.semester_enrollment import SemesterEnrollment

_SVC = "app.services.tournament.attendance_service"


# ── helpers ───────────────────────────────────────────────────────────────────

def _db_query_factory(player_checkin=None, semester_enrollment=None, team_enrollment=None):
    """Return a mock db whose .query() chains return appropriate values
    based on the model class being queried.
    """
    def _query(model):
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None  # default: no existing row

        if model is TournamentPlayerCheckin:
            q.first.return_value = player_checkin
        elif model is SemesterEnrollment:
            q.first.return_value = semester_enrollment
        elif model is TournamentTeamEnrollment:
            q.first.return_value = team_enrollment
        return q

    db = MagicMock()
    db.query.side_effect = _query
    return db


# ── CHK-ADMIN-01 ──────────────────────────────────────────────────────────────

class TestCheckinPlayerNoInstructorGate:
    """CHK-ADMIN-01: checkin_player succeeds without any instructor CHECKED_IN.

    Stage 1 removed _require_instructor_checked_in from checkin_player.
    This test proves no 409 is raised regardless of instructor slot state.
    """

    def test_chk_admin_01_no_instructor_no_409(self):
        db = _db_query_factory(player_checkin=None, semester_enrollment=None)

        with patch(f"{_SVC}._get_tournament_or_404") as mock_get:
            mock_get.return_value = MagicMock()
            result = checkin_player(
                db=db,
                tournament_id=1,
                user_id=42,
                team_id=None,
                by_user_id=99,
            )

        # Must return a TournamentPlayerCheckin-like object (new row added)
        db.add.assert_called_once()
        db.flush.assert_called_once()

    def test_chk_admin_01b_instructor_gate_helper_not_called(self):
        """_require_instructor_checked_in is NOT called by checkin_player."""
        db = _db_query_factory()

        with patch(f"{_SVC}._get_tournament_or_404"), \
             patch(f"{_SVC}._require_instructor_checked_in") as mock_gate:
            checkin_player(db=db, tournament_id=1, user_id=42, team_id=None, by_user_id=99)

        mock_gate.assert_not_called()


# ── CHK-ADMIN-02 ──────────────────────────────────────────────────────────────

class TestCheckinPlayerPromotionEvent:
    """CHK-ADMIN-02: PROMOTION_EVENT bulk-enrolled user can be checked in by admin.

    The service is participant-type-agnostic — it checks tournament existence
    only.  This test verifies that a PROMOTION_EVENT tournament (no instructor
    slots required) allows a fresh player check-in to proceed end-to-end.
    """

    def test_chk_admin_02_promo_event_checkin_succeeds(self):
        # Simulate a PROMOTION_EVENT tournament object (service only checks existence)
        promo_tournament = MagicMock()
        promo_tournament.semester_category = "PROMOTION_EVENT"

        # Player has a SemesterEnrollment (bulk-enrolled, no team)
        enrollment = MagicMock(spec=SemesterEnrollment)
        enrollment.tournament_checked_in_at = None

        db = _db_query_factory(player_checkin=None, semester_enrollment=enrollment)

        with patch(f"{_SVC}._get_tournament_or_404", return_value=promo_tournament):
            checkin_player(db=db, tournament_id=5, user_id=17, team_id=None, by_user_id=42)

        # enrollment.tournament_checked_in_at must be stamped
        assert enrollment.tournament_checked_in_at is not None

    def test_chk_admin_02b_checkin_team_no_instructor_gate(self):
        """checkin_team likewise must not call _require_instructor_checked_in."""
        enrollment = MagicMock(spec=TournamentTeamEnrollment)
        enrollment.checked_in_at = None
        db = _db_query_factory(team_enrollment=enrollment)

        with patch(f"{_SVC}._get_enrollment_or_404", return_value=enrollment), \
             patch(f"{_SVC}._require_instructor_checked_in") as mock_gate:
            checkin_team(db=db, tournament_id=5, team_id=3, by_user_id=42)

        mock_gate.assert_not_called()
        assert enrollment.checked_in_at is not None


# ── CHK-ADMIN-03 ──────────────────────────────────────────────────────────────

class TestUncheckinPlayer:
    """CHK-ADMIN-03: uncheckin_player clears TournamentPlayerCheckin row AND
    nullifies SemesterEnrollment.tournament_checked_in_at.
    """

    def test_chk_admin_03_uncheckin_clears_enrollment_stamp(self):
        checkin_row = MagicMock(spec=TournamentPlayerCheckin)
        enrollment = MagicMock(spec=SemesterEnrollment)
        enrollment.tournament_checked_in_at = datetime.now(timezone.utc)

        db = _db_query_factory(player_checkin=checkin_row, semester_enrollment=enrollment)

        uncheckin_player(db=db, tournament_id=1, user_id=42)

        db.delete.assert_called_once_with(checkin_row)
        assert enrollment.tournament_checked_in_at is None
        db.flush.assert_called_once()

    def test_chk_admin_03b_uncheckin_no_existing_row_is_noop(self):
        """uncheckin when no check-in exists must not crash (idempotent)."""
        enrollment = MagicMock(spec=SemesterEnrollment)
        enrollment.tournament_checked_in_at = None

        db = _db_query_factory(player_checkin=None, semester_enrollment=enrollment)

        # Must not raise
        uncheckin_player(db=db, tournament_id=1, user_id=42)

        db.delete.assert_not_called()
        db.flush.assert_called_once()
