"""
Unit tests for sessions/results.py
Sprint 23 — coverage: 19% → ≥90%

3 endpoints:
1. submit_game_results      (PATCH /{session_id}/results)
2. get_game_results         (GET  /{session_id}/results)
3. submit_head_to_head_match_result (PATCH /{session_id}/head-to-head-results)
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.sessions.results import (
    submit_game_results,
    get_game_results,
    submit_head_to_head_match_result,
    GameResultEntry,
    SubmitGameResultsRequest,
    HeadToHeadParticipantResult,
    SubmitHeadToHeadMatchRequest,
)
from app.models.user import UserRole
from app.models.tournament_enums import TournamentPhase
from app.models.session import EventCategory

_BASE = "app.api.api_v1.endpoints.sessions.results"
_KPS = "app.services.tournament.knockout_progression_service.KnockoutProgressionService"


# ============================================================================
# Helpers
# ============================================================================

def _user(user_id=42, role=UserRole.INSTRUCTOR):
    u = MagicMock()
    u.id = user_id
    u.role = role
    u.name = "Test User"
    return u


def _admin():
    return _user(42, UserRole.ADMIN)


def _instructor(uid=42):
    return _user(uid, UserRole.INSTRUCTOR)


def _student():
    return _user(42, UserRole.STUDENT)


def _session(
    session_id=1,
    is_tournament_game=True,
    master_instructor_id=42,
    format_="HEAD_TO_HEAD",
    game_results=None,
    rounds_data=None,
    tournament_phase=TournamentPhase.KNOCKOUT,
    tournament_config=None,
):
    s = MagicMock()
    s.id = session_id
    s.is_tournament_game = is_tournament_game
    s.event_category = EventCategory.MATCH if is_tournament_game else EventCategory.TRAINING
    s.game_type = "HEAD_TO_HEAD"
    s.game_results = game_results
    s.rounds_data = rounds_data
    s.tournament_phase = tournament_phase
    s.session_status = "pending"

    sem = MagicMock()
    sem.master_instructor_id = master_instructor_id
    sem.format = format_
    sem.id = 1
    sem.tournament_config_obj = tournament_config
    s.semester = sem
    return s


def _q(first=None, all_=None):
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    q.count.return_value = 0
    return q


def _db_session(session_obj):
    db = MagicMock()
    db.query.return_value = _q(first=session_obj)
    return db


# ============================================================================
# 1. submit_game_results
# ============================================================================

class TestSubmitGameResults:

    def _make_request(self):
        entries = [
            GameResultEntry(user_id=10, score=85.0, rank=1),
            GameResultEntry(user_id=11, score=60.0, rank=2),
        ]
        return SubmitGameResultsRequest(results=entries)

    def test_session_not_found_raises_404(self):
        db = _db_session(None)
        with pytest.raises(HTTPException) as exc:
            submit_game_results(1, self._make_request(), db=db, current_user=_instructor())
        assert exc.value.status_code == 404

    def test_not_tournament_game_raises_400(self):
        s = _session(is_tournament_game=False)
        db = _db_session(s)
        with pytest.raises(HTTPException) as exc:
            submit_game_results(1, self._make_request(), db=db, current_user=_instructor())
        assert exc.value.status_code == 400
        assert "not a tournament game" in exc.value.detail

    def test_non_master_instructor_raises_403(self):
        s = _session(master_instructor_id=99)  # different from current user
        db = _db_session(s)
        with pytest.raises(HTTPException) as exc:
            submit_game_results(1, self._make_request(), db=db, current_user=_instructor(42))
        assert exc.value.status_code == 403

    def test_admin_can_submit_for_any_tournament(self):
        s = _session(master_instructor_id=99)  # different instructor
        db = _db_session(s)
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            result = submit_game_results(1, self._make_request(), db=db, current_user=_admin())
        assert result["results_count"] == 2
        assert result["message"] == "Game results submitted successfully"

    def test_success_stores_rounds_data(self):
        s = _session(master_instructor_id=42)
        db = _db_session(s)
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            result = submit_game_results(1, self._make_request(), db=db, current_user=_instructor(42))
        assert result["results_count"] == 2
        # rounds_data should be set on session
        assert s.rounds_data is not None
        assert "round_results" in s.rounds_data
        assert "1" in s.rounds_data["round_results"]
        # scores stored as strings
        assert s.rounds_data["round_results"]["1"]["10"] == "85.0"
        db.commit.assert_called_once()


# ============================================================================
# 2. get_game_results
# ============================================================================

class TestGetGameResults:

    def test_session_not_found_raises_404(self):
        db = _db_session(None)
        with pytest.raises(HTTPException) as exc:
            get_game_results(1, db=db, current_user=_instructor())
        assert exc.value.status_code == 404

    def test_not_tournament_game_raises_400(self):
        s = _session(is_tournament_game=False)
        db = _db_session(s)
        with pytest.raises(HTTPException) as exc:
            get_game_results(1, db=db, current_user=_instructor())
        assert exc.value.status_code == 400

    def test_no_results_returns_empty_list(self):
        s = _session(rounds_data=None, game_results=None)
        db = _db_session(s)
        result = get_game_results(1, db=db, current_user=_instructor())
        assert result["results"] == []
        assert result["finalized"] is False

    def test_returns_rounds_data_results(self):
        rounds = {
            "round_results": {
                "1": {"10": "85.0", "11": "60.0"}
            }
        }
        s = _session(rounds_data=rounds, game_results=None)
        db = _db_session(s)
        result = get_game_results(1, db=db, current_user=_instructor())
        assert len(result["results"]) == 2
        assert result["results"][0]["user_id"] == 10
        assert result["results"][0]["score"] == 85.0
        assert result["finalized"] is False

    def test_returns_finalized_game_results(self):
        finalized = json.dumps({
            "derived_rankings": [
                {"user_id": 10, "rank": 1},
                {"user_id": 11, "rank": 2},
            ]
        })
        s = _session(rounds_data=None, game_results=finalized)
        db = _db_session(s)
        result = get_game_results(1, db=db, current_user=_instructor())
        assert len(result["results"]) == 2
        assert result["finalized"] is True

    def test_finalized_missing_derived_rankings_returns_empty(self):
        finalized = json.dumps({"other_key": "value"})
        s = _session(rounds_data=None, game_results=finalized)
        db = _db_session(s)
        result = get_game_results(1, db=db, current_user=_instructor())
        assert result["results"] == []
        assert result["finalized"] is True

    def test_finalized_invalid_json_returns_empty(self):
        s = _session(rounds_data=None, game_results="not-valid-json{")
        db = _db_session(s)
        result = get_game_results(1, db=db, current_user=_instructor())
        assert result["results"] == []
        assert result["finalized"] is True

    def test_rounds_data_without_round_results_key_returns_empty(self):
        s = _session(rounds_data={"total_rounds": 0}, game_results=None)
        db = _db_session(s)
        result = get_game_results(1, db=db, current_user=_instructor())
        assert result["results"] == []

    def test_score_none_returns_zero(self):
        rounds = {"round_results": {"1": {"10": None}}}
        s = _session(rounds_data=rounds, game_results=None)
        db = _db_session(s)
        result = get_game_results(1, db=db, current_user=_instructor())
        assert result["results"][0]["score"] == 0.0


# ============================================================================
# 3. submit_head_to_head_match_result
# ============================================================================

class TestSubmitHeadToHeadMatchResult:

    def _req(self, score_a=3, score_b=1, notes=None):
        return SubmitHeadToHeadMatchRequest(
            results=[
                HeadToHeadParticipantResult(user_id=10, score=score_a),
                HeadToHeadParticipantResult(user_id=11, score=score_b),
            ],
            notes=notes,
        )

    def _make_db(self, session_obj, enrollments=None):
        """DB with session + enrollment query."""
        db = MagicMock()
        call_count = [0]

        def _side(model):
            idx = call_count[0]
            call_count[0] += 1
            if idx == 0:
                q = MagicMock()
                q.filter.return_value = q
                q.first.return_value = session_obj
                return q
            else:
                # Enrollment query
                q = MagicMock()
                q.filter.return_value = q
                q.all.return_value = enrollments if enrollments is not None else []
                return q

        db.query.side_effect = _side
        return db

    def test_session_not_found_raises_404(self):
        db = _db_session(None)
        with pytest.raises(HTTPException) as exc:
            submit_head_to_head_match_result(1, self._req(), db=db, current_user=_instructor())
        assert exc.value.status_code == 404

    def test_not_tournament_game_raises_400(self):
        s = _session(is_tournament_game=False)
        db = _db_session(s)
        with pytest.raises(HTTPException) as exc:
            submit_head_to_head_match_result(1, self._req(), db=db, current_user=_instructor())
        assert exc.value.status_code == 400

    def test_non_head_to_head_format_raises_400(self):
        s = _session(format_="INDIVIDUAL_RANKING")
        db = _db_session(s)
        with pytest.raises(HTTPException) as exc:
            submit_head_to_head_match_result(1, self._req(), db=db, current_user=_instructor())
        assert exc.value.status_code == 400
        assert "HEAD_TO_HEAD" in exc.value.detail

    def test_non_master_instructor_raises_403(self):
        s = _session(format_="HEAD_TO_HEAD", master_instructor_id=99)
        db = _db_session(s)
        with pytest.raises(HTTPException) as exc:
            submit_head_to_head_match_result(1, self._req(), db=db, current_user=_instructor(42))
        assert exc.value.status_code == 403

    def test_enrollment_missing_raises_400(self):
        s = _session(format_="HEAD_TO_HEAD", master_instructor_id=42)
        # Only 1 enrollment returned instead of 2
        db = self._make_db(s, enrollments=[MagicMock()])
        with pytest.raises(HTTPException) as exc:
            submit_head_to_head_match_result(1, self._req(), db=db, current_user=_instructor(42))
        assert exc.value.status_code == 400
        assert "enrolled" in exc.value.detail

    def test_success_a_wins(self):
        s = _session(format_="HEAD_TO_HEAD", master_instructor_id=42,
                     tournament_phase=TournamentPhase.KNOCKOUT)
        db = self._make_db(s, enrollments=[MagicMock(), MagicMock()])
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            with patch(_KPS) as MockKPS:
                MockKPS.return_value.process_knockout_progression.return_value = {
                    "message": "ok",
                    "updated_sessions": [2],
                }
                result = submit_head_to_head_match_result(
                    1, self._req(score_a=3, score_b=1), db=db, current_user=_instructor(42)
                )
        assert result["winner_user_id"] == 10
        assert result["result"] == "win/loss"
        assert s.session_status == "completed"
        assert s.game_results is not None

    def test_success_b_wins(self):
        s = _session(format_="HEAD_TO_HEAD", master_instructor_id=42,
                     tournament_phase=TournamentPhase.KNOCKOUT)
        db = self._make_db(s, enrollments=[MagicMock(), MagicMock()])
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            with patch(_KPS):
                result = submit_head_to_head_match_result(
                    1, self._req(score_a=1, score_b=3), db=db, current_user=_instructor(42)
                )
        assert result["winner_user_id"] == 11

    def test_success_tie(self):
        s = _session(format_="HEAD_TO_HEAD", master_instructor_id=42,
                     tournament_phase=TournamentPhase.KNOCKOUT)
        db = self._make_db(s, enrollments=[MagicMock(), MagicMock()])
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            with patch(_KPS):
                result = submit_head_to_head_match_result(
                    1, self._req(score_a=2, score_b=2), db=db, current_user=_instructor(42)
                )
        assert result["winner_user_id"] is None
        assert result["result"] == "tie"

    def test_non_knockout_phase_skips_progression(self):
        """GROUP_STAGE phase → no KnockoutProgressionService call"""
        s = _session(format_="HEAD_TO_HEAD", master_instructor_id=42,
                     tournament_phase=TournamentPhase.GROUP_STAGE)
        db = self._make_db(s, enrollments=[MagicMock(), MagicMock()])
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            result = submit_head_to_head_match_result(
                1, self._req(score_a=3, score_b=1), db=db, current_user=_instructor(42)
            )
        assert result["knockout_progression"] is None

    def test_knockout_progression_error_logged_not_raised(self):
        """Exception in progression service must NOT fail result submission."""
        s = _session(format_="HEAD_TO_HEAD", master_instructor_id=42,
                     tournament_phase=TournamentPhase.KNOCKOUT)
        db = self._make_db(s, enrollments=[MagicMock(), MagicMock()])
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            with patch(_KPS, side_effect=Exception("progression crash")):
                result = submit_head_to_head_match_result(
                    1, self._req(score_a=3, score_b=1), db=db, current_user=_instructor(42)
                )
        # Must still return successfully
        assert result["match_format"] == "HEAD_TO_HEAD"
        assert result["knockout_progression"] is None

    def test_tournament_config_none_skips_type_code(self):
        """tournament_config_obj is None → tournament_type_code = None."""
        s = _session(format_="HEAD_TO_HEAD", master_instructor_id=42,
                     tournament_phase=TournamentPhase.GROUP_STAGE,
                     tournament_config=None)
        s.semester.tournament_config_obj = None
        db = self._make_db(s, enrollments=[MagicMock(), MagicMock()])
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            result = submit_head_to_head_match_result(
                1, self._req(), db=db, current_user=_instructor(42)
            )
        assert result["tournament_type"] is None

    def test_tournament_config_with_type_sets_code(self):
        tournament_config = MagicMock()
        tournament_config.tournament_type.code = "league"
        s = _session(format_="HEAD_TO_HEAD", master_instructor_id=42,
                     tournament_phase=TournamentPhase.GROUP_STAGE,
                     tournament_config=tournament_config)
        s.semester.tournament_config_obj = tournament_config
        db = self._make_db(s, enrollments=[MagicMock(), MagicMock()])
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            result = submit_head_to_head_match_result(
                1, self._req(), db=db, current_user=_instructor(42)
            )
        assert result["tournament_type"] == "league"

    def test_admin_can_submit_for_any_tournament(self):
        s = _session(format_="HEAD_TO_HEAD", master_instructor_id=99)
        db = self._make_db(s, enrollments=[MagicMock(), MagicMock()])
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            result = submit_head_to_head_match_result(
                1, self._req(), db=db, current_user=_admin()
            )
        assert result["match_format"] == "HEAD_TO_HEAD"
