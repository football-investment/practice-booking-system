"""
Sprint 28 — endpoints/tournaments/results/submission.py
=========================================================
Target: ≥85% statement, ≥70% branch

Covers:
  check_instructor_access    — admin pass / instructor+correct / instructor+wrong / other role
  get_session_or_404         — found+is_tournament / not found / not is_tournament_game
  submit_structured_match_results — tournament 404 / unauthorized / session 404 /
                                    ValueError→400 / happy path
  record_match_results (async)    — tournament 404 / unauthorized / session 404 /
                                    already recorded / validator fails / happy path
  submit_round_results        — session format mismatch / require_admin raises /
                                instructor not assigned / round < 1 / round > total /
                                all_done=False / all_done+ranking aggregation /
                                all_done+exception caught

Mock strategy
-------------
* ``_BASE`` — module patch base
* ``_repo_mock(tournament)`` — mock TournamentRepository returning tournament or raising 404
* ``_session_mock(...)``    — lightweight session SimpleNamespace
* ``_user(role)``           — user with given UserRole
"""

import asyncio
import json
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from app.models.user import User, UserRole
from app.models.session import EventCategory

from app.api.api_v1.endpoints.tournaments.results.submission import (
    check_instructor_access,
    get_session_or_404,
    submit_structured_match_results,
    record_match_results,
    submit_round_results,
    SubmitMatchResultsRequest,
    RecordMatchResultsRequest,
    MatchResultEntry,
    SubmitRoundResultsRequest,
)

_BASE = "app.api.api_v1.endpoints.tournaments.results.submission"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user(role=UserRole.ADMIN, uid=42, name="Test", email="t@test.com"):
    u = MagicMock(spec=User)
    u.id = uid
    u.role = role
    u.name = name
    u.email = email
    return u


def _tournament(tid=1, master_instructor_id=42):
    t = MagicMock()
    t.id = tid
    t.master_instructor_id = master_instructor_id
    t.tournament_config_obj = None
    return t


def _session_mock(sid=10, tournament_id=1, is_tournament_game=True,
                  match_format="HEAD_TO_HEAD", game_results=None,
                  rounds_data=None, instructor_id=42):
    s = MagicMock()
    s.id = sid
    s.semester_id = tournament_id
    s.is_tournament_game = is_tournament_game
    s.event_category = EventCategory.MATCH if is_tournament_game else EventCategory.TRAINING
    s.match_format = match_format
    s.game_results = game_results
    s.rounds_data = rounds_data
    s.instructor_id = instructor_id
    s.title = "Match 1"
    return s


def _repo_mock(tournament):
    """Return a mock TournamentRepository class whose instance returns tournament."""
    MockRepo = MagicMock()
    MockRepo.return_value.get_or_404.return_value = tournament
    return MockRepo


def _repo_404():
    """Return a mock TournamentRepository that raises 404."""
    MockRepo = MagicMock()
    MockRepo.return_value.get_or_404.side_effect = HTTPException(status_code=404, detail="Not found")
    return MockRepo


def _run(coro):
    return asyncio.run(coro)


# ── check_instructor_access ───────────────────────────────────────────────────

class TestCheckInstructorAccess:

    def test_admin_always_passes(self):
        """CIA-01: ADMIN role → returns None (no exception)."""
        tournament = _tournament()
        result = check_instructor_access(_user(role=UserRole.ADMIN), tournament)
        assert result is None

    def test_instructor_assigned_passes(self):
        """CIA-02: INSTRUCTOR with matching master_instructor_id → passes."""
        tournament = _tournament(master_instructor_id=10)
        result = check_instructor_access(_user(role=UserRole.INSTRUCTOR, uid=10), tournament)
        assert result is None

    def test_instructor_not_assigned_raises_403(self):
        """CIA-03: INSTRUCTOR with wrong id → 403."""
        tournament = _tournament(master_instructor_id=99)
        with pytest.raises(HTTPException) as exc:
            check_instructor_access(_user(role=UserRole.INSTRUCTOR, uid=10), tournament)
        assert exc.value.status_code == 403

    def test_student_role_raises_403(self):
        """CIA-04: STUDENT role → 403."""
        tournament = _tournament()
        with pytest.raises(HTTPException) as exc:
            check_instructor_access(_user(role=UserRole.STUDENT), tournament)
        assert exc.value.status_code == 403


# ── get_session_or_404 ────────────────────────────────────────────────────────

class TestGetSessionOr404:

    def test_returns_session_when_found_and_is_tournament(self):
        """GS404-01: session found and is_tournament_game=True → returns session."""
        sess = _session_mock(is_tournament_game=True)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        result = get_session_or_404(db, tournament_id=1, session_id=10)
        assert result is sess

    def test_raises_404_when_session_not_found(self):
        """GS404-02: session not found → 404."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc:
            get_session_or_404(db, tournament_id=1, session_id=99)
        assert exc.value.status_code == 404

    def test_raises_400_when_not_tournament_game(self):
        """GS404-03: session found but is_tournament_game=False → 400."""
        sess = _session_mock(is_tournament_game=False)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        with pytest.raises(HTTPException) as exc:
            get_session_or_404(db, tournament_id=1, session_id=10)
        assert exc.value.status_code == 400


# ── submit_structured_match_results ───────────────────────────────────────────

class TestSubmitStructuredMatchResults:

    def test_tournament_not_found_raises_404(self):
        """SM-01: tournament not found → 404 propagated from repo."""
        db = MagicMock()
        request = SubmitMatchResultsRequest(results=[{"user_id": 1, "placement": 1}])

        with patch(f"{_BASE}.TournamentRepository", _repo_404()):
            with pytest.raises(HTTPException) as exc:
                submit_structured_match_results(
                    tournament_id=99, session_id=10,
                    request=request, db=db, current_user=_user()
                )
        assert exc.value.status_code == 404

    def test_unauthorized_user_raises_403(self):
        """SM-02: student role → check_instructor_access → 403."""
        tourn = _tournament()
        db = MagicMock()
        request = SubmitMatchResultsRequest(results=[])

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)):
            with pytest.raises(HTTPException) as exc:
                submit_structured_match_results(
                    tournament_id=1, session_id=10,
                    request=request, db=db,
                    current_user=_user(role=UserRole.STUDENT)
                )
        assert exc.value.status_code == 403

    def test_session_not_found_raises_404(self):
        """SM-03: session not found → 404."""
        tourn = _tournament()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        request = SubmitMatchResultsRequest(results=[])

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)):
            with pytest.raises(HTTPException) as exc:
                submit_structured_match_results(
                    tournament_id=1, session_id=99,
                    request=request, db=db, current_user=_user()
                )
        assert exc.value.status_code == 404

    def test_value_error_from_processor_raises_400(self):
        """SM-04: ResultProcessor.process_match_results raises ValueError → 400."""
        tourn = _tournament()
        sess = _session_mock()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        mock_processor = MagicMock()
        mock_processor.return_value.process_match_results.side_effect = ValueError("bad data")
        request = SubmitMatchResultsRequest(results=[{"user_id": 1, "placement": 1}])

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.ResultProcessor", mock_processor):
            with pytest.raises(HTTPException) as exc:
                submit_structured_match_results(
                    tournament_id=1, session_id=10,
                    request=request, db=db, current_user=_user()
                )
        assert exc.value.status_code == 400

    def test_happy_path_returns_success(self):
        """SM-05: all OK → result dict with success=True and rankings."""
        tourn = _tournament()
        sess = _session_mock(match_format="HEAD_TO_HEAD")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        process_result = {
            "derived_rankings": [{"user_id": 42, "rank": 1}],
            "recorded_at": "2025-06-01T10:00:00",
        }
        mock_processor = MagicMock()
        mock_processor.return_value.process_match_results.return_value = process_result
        request = SubmitMatchResultsRequest(
            results=[{"user_id": 42, "placement": 1}], notes="Good match"
        )

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.ResultProcessor", mock_processor):
            result = submit_structured_match_results(
                tournament_id=1, session_id=10,
                request=request, db=db, current_user=_user()
            )

        assert result["success"] is True
        assert result["tournament_id"] == 1
        assert result["session_id"] == sess.id
        assert len(result["rankings"]) == 1
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(sess)


# ── record_match_results (async) ──────────────────────────────────────────────

class TestRecordMatchResults:

    def test_tournament_not_found_raises_404(self):
        """RM-01: tournament not found → 404."""
        db = MagicMock()
        req = RecordMatchResultsRequest(results=[MatchResultEntry(user_id=42, rank=1)])

        with patch(f"{_BASE}.TournamentRepository", _repo_404()):
            with pytest.raises(HTTPException) as exc:
                _run(record_match_results(
                    tournament_id=99, session_id=10,
                    result_data=req, db=db, current_user=_user()
                ))
        assert exc.value.status_code == 404

    def test_unauthorized_student_raises_403(self):
        """RM-02: student → 403."""
        tourn = _tournament()
        db = MagicMock()
        req = RecordMatchResultsRequest(results=[MatchResultEntry(user_id=42, rank=1)])

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)):
            with pytest.raises(HTTPException) as exc:
                _run(record_match_results(
                    tournament_id=1, session_id=10,
                    result_data=req, db=db,
                    current_user=_user(role=UserRole.STUDENT)
                ))
        assert exc.value.status_code == 403

    def test_session_not_found_raises_404(self):
        """RM-03: session not found → 404."""
        tourn = _tournament()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        req = RecordMatchResultsRequest(results=[MatchResultEntry(user_id=42, rank=1)])

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)):
            with pytest.raises(HTTPException) as exc:
                _run(record_match_results(
                    tournament_id=1, session_id=99,
                    result_data=req, db=db, current_user=_user()
                ))
        assert exc.value.status_code == 404

    def test_already_recorded_raises_400(self):
        """RM-04: game_results is not None → 400."""
        tourn = _tournament()
        sess = _session_mock(game_results='{"existing": true}')
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess
        req = RecordMatchResultsRequest(results=[MatchResultEntry(user_id=42, rank=1)])

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)):
            with pytest.raises(HTTPException) as exc:
                _run(record_match_results(
                    tournament_id=1, session_id=10,
                    result_data=req, db=db, current_user=_user()
                ))
        assert exc.value.status_code == 400
        assert "already been recorded" in exc.value.detail

    def test_validator_fails_raises_400(self):
        """RM-05: ResultValidator.validate_match_results → (False, err) → 400."""
        tourn = _tournament()
        sess = _session_mock(game_results=None)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess
        req = RecordMatchResultsRequest(results=[MatchResultEntry(user_id=42, rank=1)])

        mock_validator = MagicMock()
        mock_validator.return_value.validate_match_results.return_value = (False, "invalid ranks")

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.ResultValidator", mock_validator):
            with pytest.raises(HTTPException) as exc:
                _run(record_match_results(
                    tournament_id=1, session_id=10,
                    result_data=req, db=db, current_user=_user()
                ))
        assert exc.value.status_code == 400
        assert "invalid ranks" in exc.value.detail

    def test_happy_path_stores_results_and_commits(self):
        """RM-06: all OK → game_results set, db committed, response dict."""
        tourn = _tournament()
        sess = _session_mock(game_results=None)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess
        req = RecordMatchResultsRequest(
            results=[MatchResultEntry(user_id=42, rank=1, score=3.0, notes="ok")],
            match_notes="GG"
        )

        mock_validator = MagicMock()
        mock_validator.return_value.validate_match_results.return_value = (True, None)

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.ResultValidator", mock_validator):
            result = _run(record_match_results(
                tournament_id=1, session_id=10,
                result_data=req, db=db, current_user=_user()
            ))

        assert result["message"] == "Match results recorded successfully"
        assert result["tournament_id"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["user_id"] == 42
        # game_results was set as JSON string
        stored = json.loads(sess.game_results)
        assert stored["match_notes"] == "GG"
        db.commit.assert_called_once()
        db.execute.assert_called_once()  # UPDATE tournament_rankings


# ── submit_round_results ──────────────────────────────────────────────────────

class TestSubmitRoundResults:

    def _req(self, round_number=1, results=None, notes=None):
        return SubmitRoundResultsRequest(
            round_number=round_number,
            results=results or {"42": "75 points"},
            notes=notes
        )

    def test_session_format_mismatch_raises_400(self):
        """SR-01: match_format != INDIVIDUAL_RANKING → 400."""
        tourn = _tournament()
        sess = _session_mock(match_format="HEAD_TO_HEAD")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)):
            with pytest.raises(HTTPException) as exc:
                submit_round_results(
                    tournament_id=1, session_id=10, round_number=1,
                    request=self._req(), db=db, current_user=_user()
                )
        assert exc.value.status_code == 400
        assert "INDIVIDUAL_RANKING" in exc.value.detail

    def test_require_admin_raises_403(self):
        """SR-02: require_admin_or_instructor raises → 403 propagated."""
        tourn = _tournament()
        sess = _session_mock(match_format="INDIVIDUAL_RANKING")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.require_admin_or_instructor",
                   side_effect=HTTPException(status_code=403, detail="Forbidden")):
            with pytest.raises(HTTPException) as exc:
                submit_round_results(
                    tournament_id=1, session_id=10, round_number=1,
                    request=self._req(), db=db, current_user=_user(role=UserRole.STUDENT)
                )
        assert exc.value.status_code == 403

    def test_instructor_not_assigned_raises_403(self):
        """SR-03: instructor not assigned to session or tournament → 403."""
        tourn = _tournament(master_instructor_id=99)
        sess = _session_mock(match_format="INDIVIDUAL_RANKING", instructor_id=99)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess
        user = _user(role=UserRole.INSTRUCTOR, uid=10)

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.require_admin_or_instructor"):  # passes
            with pytest.raises(HTTPException) as exc:
                submit_round_results(
                    tournament_id=1, session_id=10, round_number=1,
                    request=self._req(), db=db, current_user=user
                )
        assert exc.value.status_code == 403

    def test_round_number_less_than_1_raises_400(self):
        """SR-04: round_number=0 < 1 → 400."""
        tourn = _tournament()
        sess = _session_mock(
            match_format="INDIVIDUAL_RANKING",
            rounds_data={"total_rounds": 3}
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.require_admin_or_instructor"), \
             patch(f"{_BASE}.flag_modified"):
            with pytest.raises(HTTPException) as exc:
                submit_round_results(
                    tournament_id=1, session_id=10, round_number=0,
                    request=self._req(round_number=0), db=db, current_user=_user()
                )
        assert exc.value.status_code == 400

    def test_round_number_exceeds_total_raises_400(self):
        """SR-05: round_number > total_rounds → 400."""
        tourn = _tournament()
        sess = _session_mock(
            match_format="INDIVIDUAL_RANKING",
            rounds_data={"total_rounds": 2}
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.require_admin_or_instructor"), \
             patch(f"{_BASE}.flag_modified"):
            with pytest.raises(HTTPException) as exc:
                submit_round_results(
                    tournament_id=1, session_id=10, round_number=5,
                    request=self._req(round_number=5), db=db, current_user=_user()
                )
        assert exc.value.status_code == 400

    def test_happy_path_not_all_done(self):
        """SR-06: round submitted, not all rounds complete → rankings_calculated=False."""
        tourn = _tournament()
        sess = _session_mock(
            match_format="INDIVIDUAL_RANKING",
            rounds_data={"total_rounds": 3}
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.require_admin_or_instructor"), \
             patch(f"{_BASE}.flag_modified"):
            result = submit_round_results(
                tournament_id=1, session_id=10, round_number=1,
                request=self._req(results={"42": "75 points"}),
                db=db, current_user=_user()
            )

        assert result["success"] is True
        assert result["round_number"] == 1
        assert result["all_rounds_complete"] is False
        assert result["rankings_calculated"] is False
        db.commit.assert_called_once()

    def test_happy_path_all_done_no_combined_results(self):
        """SR-07: all rounds done but no combined_round_results → rankings_calculated=False."""
        tourn = _tournament()
        # rounds_data already has 2 of 2 rounds → after adding round 2 → all_done
        # The session we query for all_sessions_for_ranking returns sessions with no round_results
        sess = _session_mock(
            match_format="INDIVIDUAL_RANKING",
            rounds_data={"total_rounds": 1}  # total=1, we submit round 1 → complete
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        # For the all_sessions_for_ranking query (second db.query call), return sess with no round_results
        sess_no_rounds = _session_mock(rounds_data={})
        db.query.return_value.filter.return_value.all.return_value = [sess_no_rounds]

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.require_admin_or_instructor"), \
             patch(f"{_BASE}.flag_modified"):
            result = submit_round_results(
                tournament_id=1, session_id=10, round_number=1,
                request=self._req(results={"42": "75 points"}),
                db=db, current_user=_user()
            )

        assert result["all_rounds_complete"] is True
        assert result["rankings_calculated"] is False  # no combined_round_results

    def test_happy_path_all_done_with_ranking_aggregation(self):
        """SR-08: all done + combined results → RankingAggregator called → rankings_calculated=True."""
        tourn = _tournament()
        tourn.tournament_config_obj = MagicMock()
        tourn.tournament_config_obj.ranking_direction = "ASC"

        sess = _session_mock(
            match_format="INDIVIDUAL_RANKING",
            rounds_data={"total_rounds": 1}
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        # All sessions for ranking returns one session with round_results
        sess_with_results = _session_mock(
            rounds_data={"round_results": {"1": {"42": "10.5s", "99": "11.2s"}}}
        )
        db.query.return_value.filter.return_value.all.return_value = [sess_with_results]
        db.query.return_value.filter.return_value.delete.return_value = 0

        mock_tr = MagicMock()
        mock_aggregator = MagicMock()
        mock_aggregator.aggregate_user_values.return_value = {"42": 10.5}
        mock_aggregator.calculate_performance_rankings.return_value = [
            {"user_id": 42, "rank": 1, "final_value": 10.5}
        ]
        mock_ra_class = MagicMock()
        mock_ra_class.aggregate_user_values = mock_aggregator.aggregate_user_values
        mock_ra_class.calculate_performance_rankings = mock_aggregator.calculate_performance_rankings

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.require_admin_or_instructor"), \
             patch(f"{_BASE}.flag_modified"), \
             patch.dict("sys.modules", {
                 "app.models.tournament_ranking": MagicMock(TournamentRanking=mock_tr),
                 "app.services.tournament.results.calculators.ranking_aggregator": MagicMock(RankingAggregator=mock_ra_class),
             }):
            result = submit_round_results(
                tournament_id=1, session_id=10, round_number=1,
                request=self._req(results={"42": "10.5s"}),
                db=db, current_user=_user()
            )

        assert result["all_rounds_complete"] is True
        assert result["rankings_calculated"] is True

    def test_ranking_exception_caught_still_succeeds(self):
        """SR-09: RankingAggregator raises → exception caught → success with rankings_calculated=False."""
        tourn = _tournament()
        sess = _session_mock(
            match_format="INDIVIDUAL_RANKING",
            rounds_data={"total_rounds": 1}
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        sess_with_results = _session_mock(
            rounds_data={"round_results": {"1": {"42": "10.5s"}}}
        )
        db.query.return_value.filter.return_value.all.return_value = [sess_with_results]

        mock_ra_class = MagicMock()
        mock_ra_class.aggregate_user_values.side_effect = RuntimeError("ranking error")

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.require_admin_or_instructor"), \
             patch(f"{_BASE}.flag_modified"), \
             patch.dict("sys.modules", {
                 "app.models.tournament_ranking": MagicMock(),
                 "app.services.tournament.results.calculators.ranking_aggregator": MagicMock(RankingAggregator=mock_ra_class),
             }):
            result = submit_round_results(
                tournament_id=1, session_id=10, round_number=1,
                request=self._req(results={"42": "10.5s"}),
                db=db, current_user=_user()
            )

        assert result["success"] is True
        assert result["rankings_calculated"] is False  # exception was caught

    def test_round_results_existing_key_overwritten(self):
        """SR-10: existing round_results key → idempotent overwrite."""
        tourn = _tournament()
        existing = {"total_rounds": 2, "round_results": {"1": {"42": "old_value"}}}
        sess = _session_mock(
            match_format="INDIVIDUAL_RANKING",
            rounds_data=existing
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = sess

        with patch(f"{_BASE}.TournamentRepository", _repo_mock(tourn)), \
             patch(f"{_BASE}.require_admin_or_instructor"), \
             patch(f"{_BASE}.flag_modified"):
            result = submit_round_results(
                tournament_id=1, session_id=10, round_number=1,
                request=self._req(results={"42": "new_value"}, round_number=1),
                db=db, current_user=_user()
            )

        assert result["success"] is True
        assert result["all_rounds_complete"] is False  # only 1 of 2 done
        # completed_rounds updated
        assert sess.rounds_data["completed_rounds"] == 1
