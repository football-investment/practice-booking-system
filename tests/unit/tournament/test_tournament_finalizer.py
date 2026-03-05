"""
Tests for tournament/results/finalization/tournament_finalizer.py

Missing coverage targets:
  Lines 277-287: finalize() idempotency guard (already COMPLETED/REWARDS_DISTRIBUTED)
  Lines 292-296: finalize() no sessions found
  Lines 303-308: finalize() incomplete matches
  Lines 135-149: extract_final_rankings — rank 1 and 2 from final match JSON
  Lines 152-160: extract_final_rankings — 3rd place match JSON → final_rank=3
  Lines 193-196: update_tournament_rankings_table — existing row update
  Lines 325-335: finalize() reward distribution success
  Lines 336-341: finalize() reward distribution failure (still completes)
  Lines 351-352: finalize() rewards_message added to result
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.tournament.results.finalization.tournament_finalizer import (
    TournamentFinalizer,
    _FINALIZED_STATUSES,
)


# ──────────────────── helpers ────────────────────


def _tournament(t_id=1, status="IN_PROGRESS"):
    t = MagicMock()
    t.id = t_id
    t.tournament_status = status
    return t


def _db_with_semester(tournament):
    """DB mock: query(Semester).filter().with_for_update().one() → tournament."""
    from app.models.semester import Semester

    db = MagicMock()
    t_q = MagicMock()
    t_q.filter.return_value = t_q
    wfu = MagicMock()
    wfu.one.return_value = tournament
    t_q.with_for_update.return_value = wfu

    db.query.return_value = t_q
    return db


def _lock_ctx():
    """Return a patched lock_timer that acts as a no-op context manager."""
    lt = MagicMock()
    lt.return_value.__enter__ = MagicMock(return_value=None)
    lt.return_value.__exit__ = MagicMock(return_value=False)
    return lt


# ──────────────────── idempotency guard ────────────────────


class TestFinalizerIdempotency:

    @pytest.mark.parametrize("status", list(_FINALIZED_STATUSES))
    def test_already_finalized_returns_idempotent_result(self, status):
        """Lines 277-287: finalize() called on already-finalized tournament."""
        tournament = _tournament(status=status)
        db = _db_with_semester(tournament)
        finalizer = TournamentFinalizer(db)

        with patch(
            "app.services.tournament.results.finalization.tournament_finalizer.lock_timer",
            _lock_ctx(),
        ):
            result = finalizer.finalize(tournament)

        assert result["success"] is True
        assert "idempotent" in result["message"]
        assert result["tournament_status"] == status


# ──────────────────── no sessions ────────────────────


class TestFinalizerNoSessions:

    def test_no_sessions_found_returns_failure(self):
        """Lines 292-296: get_all_sessions returns [] → success=False."""
        tournament = _tournament(status="IN_PROGRESS")
        db = _db_with_semester(tournament)
        finalizer = TournamentFinalizer(db)
        finalizer.get_all_sessions = MagicMock(return_value=[])

        with patch(
            "app.services.tournament.results.finalization.tournament_finalizer.lock_timer",
            _lock_ctx(),
        ):
            result = finalizer.finalize(tournament)

        assert result["success"] is False
        assert "No tournament matches" in result["message"]


# ──────────────────── incomplete matches ────────────────────


class TestFinalizerIncompleteMatches:

    def test_incomplete_matches_returns_failure_with_list(self):
        """Lines 303-308: 1 incomplete session → success=False + incomplete_matches."""
        tournament = _tournament(status="IN_PROGRESS")
        db = _db_with_semester(tournament)
        finalizer = TournamentFinalizer(db)

        finalizer.get_all_sessions = MagicMock(return_value=[MagicMock()])
        finalizer.check_all_matches_completed = MagicMock(
            return_value=(False, [{"session_id": 5, "title": "Final"}])
        )

        with patch(
            "app.services.tournament.results.finalization.tournament_finalizer.lock_timer",
            _lock_ctx(),
        ):
            result = finalizer.finalize(tournament)

        assert result["success"] is False
        assert "1 matches" in result["message"]
        assert len(result["incomplete_matches"]) == 1


# ──────────────────── reward distribution ────────────────────


class TestFinalizerRewardDistribution:

    def _setup_finalizer_mocked(self, tournament):
        db = _db_with_semester(tournament)
        finalizer = TournamentFinalizer(db)
        finalizer.get_all_sessions = MagicMock(return_value=[MagicMock()])
        finalizer.check_all_matches_completed = MagicMock(return_value=(True, []))
        finalizer.extract_final_rankings = MagicMock(return_value=[])
        finalizer.update_tournament_rankings_table = MagicMock()
        return finalizer

    def test_reward_success_sets_rewards_distributed_status(self):
        """Lines 325-335: reward distribution success → REWARDS_DISTRIBUTED + rewards_message."""
        tournament = _tournament(status="IN_PROGRESS")
        finalizer = self._setup_finalizer_mocked(tournament)

        mock_result = MagicMock()
        mock_result.rewards_distributed = [1, 2, 3]

        with patch(
            "app.services.tournament.results.finalization.tournament_finalizer.lock_timer",
            _lock_ctx(),
        ):
            with patch(
                "app.services.tournament.tournament_reward_orchestrator.distribute_rewards_for_tournament",
                return_value=mock_result,
            ):
                result = finalizer.finalize(tournament)

        assert result["success"] is True
        assert result["tournament_status"] == "REWARDS_DISTRIBUTED"
        # Lines 351-352: rewards_message in result
        assert "rewards_message" in result
        assert "3 players" in result["rewards_message"]

    def test_reward_failure_keeps_completed_status(self):
        """Lines 336-341: exception during reward distribution → status stays COMPLETED."""
        tournament = _tournament(status="IN_PROGRESS")
        finalizer = self._setup_finalizer_mocked(tournament)

        with patch(
            "app.services.tournament.results.finalization.tournament_finalizer.lock_timer",
            _lock_ctx(),
        ):
            with patch(
                "app.services.tournament.tournament_reward_orchestrator.distribute_rewards_for_tournament",
                side_effect=Exception("reward error"),
            ):
                result = finalizer.finalize(tournament)

        assert result["success"] is True
        assert result["tournament_status"] == "COMPLETED"
        assert "rewards_message" not in result

    def test_no_rewards_message_when_no_reward_distribution(self):
        """rewards_message only present when rewards were distributed."""
        tournament = _tournament(status="IN_PROGRESS")
        finalizer = self._setup_finalizer_mocked(tournament)

        with patch(
            "app.services.tournament.results.finalization.tournament_finalizer.lock_timer",
            _lock_ctx(),
        ):
            with patch(
                "app.services.tournament.tournament_reward_orchestrator.distribute_rewards_for_tournament",
                side_effect=RuntimeError("fail"),
            ):
                result = finalizer.finalize(tournament)

        # rewards_message only added when rewards_message is truthy (line 351)
        assert result.get("rewards_message") is None or "rewards_message" not in result


# ──────────────────── extract_final_rankings ────────────────────


class TestExtractFinalRankings:

    def _db_sessions(self, final_session, third_session):
        """DB returning final_session then third_session in sequence."""
        db = MagicMock()
        sess_q = MagicMock()
        sess_q.filter.return_value = sess_q
        sess_q.first.side_effect = [final_session, third_session]
        db.query.return_value = sess_q
        return db

    def test_extracts_rank_1_and_2_from_final_match(self):
        """Lines 135-149: final match JSON → rank 1 and 2 in result."""
        final = MagicMock()
        final.game_results = json.dumps(
            {
                "derived_rankings": [
                    {"rank": 1, "user_id": 10},
                    {"rank": 2, "user_id": 20},
                ]
            }
        )
        db = self._db_sessions(final_session=final, third_session=None)
        finalizer = TournamentFinalizer(db)

        result = finalizer.extract_final_rankings(1)

        assert len(result) == 2
        r1 = next(r for r in result if r["final_rank"] == 1)
        r2 = next(r for r in result if r["final_rank"] == 2)
        assert r1["user_id"] == 10
        assert r2["user_id"] == 20
        assert r1["place"] == "1st"
        assert r2["place"] == "2nd"

    def test_extracts_3rd_from_third_place_match(self):
        """Lines 152-160: 3rd place match winner (rank=1) → final_rank=3."""
        final = MagicMock()
        final.game_results = json.dumps(
            {"derived_rankings": [{"rank": 1, "user_id": 10}]}
        )
        third = MagicMock()
        third.game_results = json.dumps(
            {"derived_rankings": [{"rank": 1, "user_id": 30}]}
        )
        db = self._db_sessions(final_session=final, third_session=third)
        finalizer = TournamentFinalizer(db)

        result = finalizer.extract_final_rankings(1)

        third_place = next((r for r in result if r["final_rank"] == 3), None)
        assert third_place is not None
        assert third_place["user_id"] == 30
        assert third_place["place"] == "3rd"

    def test_no_sessions_returns_empty(self):
        """No final match, no 3rd place match → empty list."""
        db = self._db_sessions(final_session=None, third_session=None)
        finalizer = TournamentFinalizer(db)

        result = finalizer.extract_final_rankings(1)

        assert result == []


# ──────────────────── update_tournament_rankings_table ────────────────────


class TestUpdateRankingsTable:

    def test_updates_existing_ranking_row(self):
        """Lines 193-196: existing row → rank and points updated, no INSERT."""
        from app.models.tournament_ranking import TournamentRanking
        from app.models.semester_enrollment import SemesterEnrollment

        existing = MagicMock()
        existing.rank = 5
        existing.points = 99

        # Query sequence:
        # 1. TournamentRanking (check existing for user_id=99) → existing
        # 2. SemesterEnrollment.user_id (enrolled users) → [] (empty set)
        ranking_q = MagicMock()
        ranking_q.filter.return_value = ranking_q
        ranking_q.first.return_value = existing

        enrollment_q = MagicMock()
        enrollment_q.filter.return_value = enrollment_q
        enrollment_q.all.return_value = []  # no enrolled users outside podium

        query_iter = iter([ranking_q, enrollment_q])
        db = MagicMock()
        db.query.side_effect = lambda *a: next(query_iter)

        finalizer = TournamentFinalizer(db)
        finalizer.update_tournament_rankings_table(
            tournament_id=1,
            final_rankings=[{"user_id": 99, "final_rank": 1}],
        )

        # Existing row should be updated
        assert existing.rank == 1
        assert existing.points == 0
        # No INSERT should have been issued
        db.execute.assert_not_called()

    def test_inserts_new_ranking_when_no_existing_row(self):
        """Lines 197-208: no existing row → INSERT via db.execute(text(...))."""
        from app.models.tournament_ranking import TournamentRanking
        from app.models.semester_enrollment import SemesterEnrollment

        ranking_q = MagicMock()
        ranking_q.filter.return_value = ranking_q
        ranking_q.first.return_value = None  # no existing

        enrollment_q = MagicMock()
        enrollment_q.filter.return_value = enrollment_q
        enrollment_q.all.return_value = []

        query_iter = iter([ranking_q, enrollment_q])
        db = MagicMock()
        db.query.side_effect = lambda *a: next(query_iter)

        finalizer = TournamentFinalizer(db)
        finalizer.update_tournament_rankings_table(
            tournament_id=1,
            final_rankings=[{"user_id": 88, "final_rank": 2}],
        )

        db.execute.assert_called_once()
