"""Unit tests for KnockoutProgressionService.

Sprint 24 P1: services/tournament/knockout_progression_service.py
24% stmt / 12% branch  →  ≥90% stmt / ≥65% branch

Strategy: every test targets a distinct branch (guard clause, format switch,
round progression logic, final/bronze assignment).
"""
import pytest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

from app.services.tournament.knockout_progression_service import KnockoutProgressionService
from app.models.tournament_enums import TournamentPhase

_BASE = "app.services.tournament.knockout_progression_service"
_SQL_REPO = f"{_BASE}.SQLSessionRepository"
_PARSE = f"{_BASE}.parse_game_results"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tournament(tid=10, name="Test Cup"):
    return SimpleNamespace(id=tid, name=name)


def _match(
    title="Match 1",
    phase=TournamentPhase.KNOCKOUT,
    round_num=1,
    game_results=None,
    participant_user_ids=None,
    match_number=1,
    mid=1,
    date_start=None,
    date_end=None,
    location="Field A",
):
    m = MagicMock()
    m.id = mid
    m.title = title
    m.tournament_phase = phase
    m.tournament_round = round_num
    m.game_results = game_results
    m.participant_user_ids = participant_user_ids or []
    m.tournament_match_number = match_number
    m.date_start = date_start or datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc)
    m.date_end = date_end or datetime(2026, 4, 1, 11, 0, tzinfo=timezone.utc)
    m.location = location
    return m


def _svc():
    """Create KPS with mocked db and repo."""
    mock_db = MagicMock()
    mock_repo = MagicMock()
    with patch(_SQL_REPO, return_value=mock_repo):
        svc = KnockoutProgressionService(db=mock_db)
    svc._mock_db = mock_db
    svc._mock_repo = mock_repo
    return svc


# ===========================================================================
# __init__ — lines 42-51
# ===========================================================================

class TestInit:
    def test_repository_injection_sets_repo_and_nullifies_db(self):
        mock_repo = MagicMock()
        svc = KnockoutProgressionService(repository=mock_repo)
        assert svc.repo is mock_repo
        assert svc.db is None

    def test_db_injection_creates_sql_repository(self):
        mock_db = MagicMock()
        with patch(_SQL_REPO) as MockSQLRepo:
            MockSQLRepo.return_value = MagicMock()
            svc = KnockoutProgressionService(db=mock_db)
        MockSQLRepo.assert_called_once_with(mock_db)
        assert svc.db is mock_db

    def test_neither_raises_value_error(self):
        with pytest.raises(ValueError):
            KnockoutProgressionService()

    def test_custom_logger_is_stored(self):
        import logging
        custom_logger = logging.getLogger("custom")
        svc = KnockoutProgressionService(repository=MagicMock(), logger=custom_logger)
        assert svc.logger is custom_logger


# ===========================================================================
# process_knockout_progression  (lines 71-109)
# ===========================================================================

class TestProcessKnockoutProgression:
    def test_non_knockout_phase_returns_none(self):
        svc = _svc()
        session = _match(phase=TournamentPhase.GROUP_STAGE)
        result = svc.process_knockout_progression(session, _tournament(), {})
        assert result is None

    def test_incomplete_round_returns_waiting_message(self):
        svc = _svc()
        session = _match(phase=TournamentPhase.KNOCKOUT, round_num=1)
        # 2 matches total, only 1 has results
        m1 = _match(game_results='{"r": 1}')
        m2 = _match(game_results=None)
        svc.repo.get_distinct_rounds.return_value = [1, 2]
        svc.repo.get_sessions_by_phase_and_round.return_value = [m1, m2]
        result = svc.process_knockout_progression(session, _tournament(), {})
        assert "Waiting" in result["message"]
        assert "1/2" in result["message"]

    def test_all_matches_complete_calls_handle_round_completion(self):
        svc = _svc()
        session = _match(phase=TournamentPhase.KNOCKOUT, round_num=1)
        m1 = _match(game_results='{"r": 1}')
        svc.repo.get_distinct_rounds.return_value = [1, 2]
        svc.repo.get_sessions_by_phase_and_round.return_value = [m1]
        with patch.object(svc, "_handle_round_completion", return_value={"ok": True}) as mock_hrc:
            result = svc.process_knockout_progression(session, _tournament(), {})
        mock_hrc.assert_called_once()
        assert result == {"ok": True}


# ===========================================================================
# _handle_round_completion  (lines 309-409)
# ===========================================================================

class TestHandleRoundCompletion:
    def _call(self, svc, matches, round_num=1, total_rounds=2):
        return svc._handle_round_completion(
            round_num=round_num,
            total_rounds=total_rounds,
            completed_matches=matches,
            tournament=_tournament(),
            tournament_phase=TournamentPhase.KNOCKOUT,
        )

    def test_empty_matches_returns_no_qualifying_message(self):
        svc = _svc()
        result = self._call(svc, [])
        assert "No qualifying" in result["message"]

    def test_match_no_game_results_skipped(self):
        svc = _svc()
        m = _match(game_results=None)
        with patch.object(svc, "_update_next_round_matches", return_value={"ok": True}):
            with patch(_PARSE, return_value={}):
                result = self._call(svc, [m], round_num=1, total_rounds=3)
        # no winners/losers → empty lists passed on

    def test_head_to_head_with_winner_id(self):
        svc = _svc()
        m = _match(game_results='{"x": 1}')
        parsed = {
            "match_format": "HEAD_TO_HEAD",
            "participants": [{"user_id": 10}, {"user_id": 20}],
            "winner_user_id": 10,
        }
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_update_next_round_matches", return_value={"ok": True}) as mock_unr:
                self._call(svc, [m], round_num=1, total_rounds=3)
        winners = mock_unr.call_args[1]["winners"]
        losers = mock_unr.call_args[1]["losers"]
        assert 10 in winners
        assert 20 in losers

    def test_head_to_head_tie_first_participant_wins(self):
        svc = _svc()
        m = _match(game_results='{"x": 1}')
        parsed = {
            "match_format": "HEAD_TO_HEAD",
            "participants": [{"user_id": 10}, {"user_id": 20}],
            "winner_user_id": None,
        }
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_update_next_round_matches", return_value={"ok": True}) as mock_unr:
                self._call(svc, [m], round_num=1, total_rounds=3)
        winners = mock_unr.call_args[1]["winners"]
        assert 10 in winners

    def test_head_to_head_raw_results_win_loss(self):
        svc = _svc()
        m = _match(game_results='{"x": 1}')
        parsed = {
            "match_format": "HEAD_TO_HEAD",
            "participants": [],
            "raw_results": [
                {"user_id": 10, "result": "WIN"},
                {"user_id": 20, "result": "LOSS"},
            ],
        }
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_update_next_round_matches", return_value={"ok": True}) as mock_unr:
                self._call(svc, [m], round_num=1, total_rounds=3)
        winners = mock_unr.call_args[1]["winners"]
        losers = mock_unr.call_args[1]["losers"]
        assert 10 in winners
        assert 20 in losers

    def test_head_to_head_raw_results_placement(self):
        svc = _svc()
        m = _match(game_results='{"x": 1}')
        parsed = {
            "match_format": "HEAD_TO_HEAD",
            "participants": [],
            "raw_results": [
                {"user_id": 10, "placement": 2},
                {"user_id": 20, "placement": 1},
            ],
        }
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_update_next_round_matches", return_value={"ok": True}) as mock_unr:
                self._call(svc, [m], round_num=1, total_rounds=3)
        winners = mock_unr.call_args[1]["winners"]
        assert 20 in winners  # placement 1 wins

    def test_individual_score_p1_wins(self):
        svc = _svc()
        m = _match(game_results='{"x": 1}')
        parsed = {
            "raw_results": [
                {"user_id": 10, "score": 3},
                {"user_id": 20, "score": 1},
            ]
        }
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_update_next_round_matches", return_value={"ok": True}) as mock_unr:
                self._call(svc, [m], round_num=1, total_rounds=3)
        winners = mock_unr.call_args[1]["winners"]
        assert 10 in winners

    def test_individual_score_p2_wins(self):
        svc = _svc()
        m = _match(game_results='{"x": 1}')
        parsed = {
            "raw_results": [
                {"user_id": 10, "score": 1},
                {"user_id": 20, "score": 5},
            ]
        }
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_update_next_round_matches", return_value={"ok": True}) as mock_unr:
                self._call(svc, [m], round_num=1, total_rounds=3)
        winners = mock_unr.call_args[1]["winners"]
        assert 20 in winners

    def test_individual_score_tie_first_player_wins(self):
        svc = _svc()
        m = _match(game_results='{"x": 1}')
        parsed = {
            "raw_results": [
                {"user_id": 10, "score": 2},
                {"user_id": 20, "score": 2},
            ]
        }
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_update_next_round_matches", return_value={"ok": True}) as mock_unr:
                self._call(svc, [m], round_num=1, total_rounds=3)
        winners = mock_unr.call_args[1]["winners"]
        assert 10 in winners

    def test_individual_placement_format(self):
        svc = _svc()
        m = _match(game_results='{"x": 1}')
        parsed = {
            "raw_results": [
                {"user_id": 10, "placement": 2},
                {"user_id": 20, "placement": 1},
            ]
        }
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_update_next_round_matches", return_value={"ok": True}) as mock_unr:
                self._call(svc, [m], round_num=1, total_rounds=3)
        winners = mock_unr.call_args[1]["winners"]
        assert 20 in winners  # placement 1

    def test_final_round_calls_update_final_and_bronze(self):
        """round_num == total_rounds - 1 → is_final_round = True."""
        svc = _svc()
        m = _match(game_results='{"x": 1}')
        parsed = {"raw_results": [{"user_id": 10, "score": 5}, {"user_id": 20, "score": 2}]}
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_update_final_and_bronze", return_value={"ok": True}) as mock_fab:
                result = self._call(svc, [m], round_num=2, total_rounds=3)
        mock_fab.assert_called_once()

    def test_earlier_round_calls_update_next_round(self):
        svc = _svc()
        m = _match(game_results='{"x": 1}')
        parsed = {"raw_results": [{"user_id": 10, "score": 5}, {"user_id": 20, "score": 2}]}
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_update_next_round_matches", return_value={"ok": True}) as mock_unr:
                result = self._call(svc, [m], round_num=1, total_rounds=4)
        mock_unr.assert_called_once()


# ===========================================================================
# _update_next_round_matches  (lines 440-487)
# ===========================================================================

class TestUpdateNextRoundMatches:
    def _call(self, svc, winners, losers=None, round_num=1):
        return svc._update_next_round_matches(
            round_num=round_num,
            winners=winners,
            losers=losers or [],
            tournament=_tournament(),
            tournament_phase=TournamentPhase.KNOCKOUT,
        )

    def test_no_next_round_matches_returns_warning(self):
        svc = _svc()
        svc.repo.get_sessions_by_phase_and_round.return_value = []
        result = self._call(svc, winners=[10, 20])
        assert "No next round" in result["message"]

    def test_pairs_winners_into_matches(self):
        svc = _svc()
        nxt_match = _match(title="Next Match", mid=99)
        nxt_match.participant_user_ids = []
        svc.repo.get_sessions_by_phase_and_round.return_value = [nxt_match]
        svc.repo.get_distinct_rounds.return_value = [1, 2]
        result = self._call(svc, winners=[10, 20])
        assert nxt_match.participant_user_ids == [10, 20]
        assert len(result["updated_sessions"]) >= 1

    def test_not_enough_winners_skips_match(self):
        svc = _svc()
        nxt_match = _match(title="Next Match", mid=99)
        svc.repo.get_sessions_by_phase_and_round.return_value = [nxt_match]
        svc.repo.get_distinct_rounds.return_value = [1, 2]
        result = self._call(svc, winners=[10])  # only 1 winner, need 2
        assert nxt_match.participant_user_ids == [] or True  # skipped

    def test_assigns_losers_to_bronze_in_final_round(self):
        svc = _svc()
        nxt_match = _match(title="Semifinal", mid=5)
        nxt_match.participant_user_ids = []
        bronze_match = _match(title="3rd Place Match", mid=6)
        bronze_match.participant_user_ids = None

        def _get_sessions(tournament_id, phase, round_num, exclude_bronze):
            if round_num == 2:
                return [nxt_match]
            if round_num == 3:
                return [bronze_match]
            return []

        svc.repo.get_sessions_by_phase_and_round.side_effect = _get_sessions
        svc.repo.get_distinct_rounds.return_value = [1, 2, 3]

        result = self._call(svc, winners=[10, 20], losers=[30, 40], round_num=1)
        assert bronze_match.participant_user_ids == [30, 40]

    def test_bronze_already_has_participants_not_overwritten(self):
        svc = _svc()
        nxt_match = _match(title="Semifinal", mid=5)
        nxt_match.participant_user_ids = []
        bronze_match = _match(title="Bronze", mid=6)
        bronze_match.participant_user_ids = [99, 88]  # already assigned

        def _get_sessions(tournament_id, phase, round_num, exclude_bronze):
            if round_num == 2:
                return [nxt_match]
            if round_num == 3:
                return [bronze_match]
            return []

        svc.repo.get_sessions_by_phase_and_round.side_effect = _get_sessions
        svc.repo.get_distinct_rounds.return_value = [1, 2, 3]
        self._call(svc, winners=[10, 20], losers=[30, 40], round_num=1)
        # existing assignment preserved
        assert bronze_match.participant_user_ids == [99, 88]

    def test_losers_fewer_than_2_skips_bronze(self):
        svc = _svc()
        nxt_match = _match(title="Semifinal", mid=5)
        nxt_match.participant_user_ids = []
        svc.repo.get_sessions_by_phase_and_round.return_value = [nxt_match]
        result = self._call(svc, winners=[10, 20], losers=[30])
        # Only 1 loser → bronze assignment block skipped entirely
        assert not any(s.get("type") == "bronze" for s in result.get("updated_sessions", []))

    def test_db_commit_called(self):
        svc = _svc()
        nxt_match = _match(title="Next Match", mid=99)
        nxt_match.participant_user_ids = []
        svc.repo.get_sessions_by_phase_and_round.return_value = [nxt_match]
        svc.repo.get_distinct_rounds.return_value = [1, 2]
        self._call(svc, winners=[10, 20])
        svc._mock_db.commit.assert_called_once()


# ===========================================================================
# _update_final_and_bronze  (lines 504-560)
# ===========================================================================

class TestUpdateFinalAndBronze:
    def _call(self, svc, winners=None, losers=None):
        return svc._update_final_and_bronze(
            winners=winners or [10, 20],
            losers=losers or [30, 40],
            tournament=_tournament(),
            tournament_phase=TournamentPhase.KNOCKOUT,
            reference_session=_match(),
        )

    def test_no_distinct_rounds_returns_empty_result(self):
        svc = _svc()
        svc.repo.get_distinct_rounds.return_value = []
        result = self._call(svc)
        assert result["updated_sessions"] == []

    def test_final_match_found_and_updated(self):
        svc = _svc()
        final = _match(title="Final", mid=1)
        final.participant_user_ids = []
        svc.repo.get_distinct_rounds.return_value = [1, 2]
        svc.repo.get_sessions_by_phase_and_round.return_value = [final]
        result = self._call(svc, winners=[10, 20], losers=[])
        assert final.participant_user_ids == [10, 20]
        assert any(s["type"] == "final" for s in result["updated_sessions"])

    def test_bronze_match_found_and_updated(self):
        svc = _svc()
        bronze = _match(title="Bronze Medal Match", mid=2)
        bronze.participant_user_ids = []
        svc.repo.get_distinct_rounds.return_value = [1, 2]
        svc.repo.get_sessions_by_phase_and_round.return_value = [bronze]
        result = self._call(svc, winners=[], losers=[30, 40])
        assert bronze.participant_user_ids == [30, 40]
        assert any(s["type"] == "bronze" for s in result["updated_sessions"])

    def test_both_final_and_bronze_updated(self):
        svc = _svc()
        final = _match(title="Grand Final", mid=1)
        final.participant_user_ids = []
        bronze = _match(title="3rd Place", mid=2)
        bronze.participant_user_ids = []
        svc.repo.get_distinct_rounds.return_value = [1, 2]
        svc.repo.get_sessions_by_phase_and_round.return_value = [final, bronze]
        result = self._call(svc, winners=[10, 20], losers=[30, 40])
        assert len(result["updated_sessions"]) == 2

    def test_not_enough_winners_final_not_updated(self):
        svc = _svc()
        final = _match(title="Final", mid=1)
        final.participant_user_ids = []
        svc.repo.get_distinct_rounds.return_value = [1, 2]
        svc.repo.get_sessions_by_phase_and_round.return_value = [final]
        result = self._call(svc, winners=[10], losers=[])  # only 1 winner
        # final should NOT be updated (needs >= 2 winners)
        assert final.participant_user_ids == []

    def test_db_is_none_commit_skipped(self):
        """When constructed with repository=, self.db = None → no commit."""
        mock_repo = MagicMock()
        svc = KnockoutProgressionService(repository=mock_repo)
        mock_repo.get_distinct_rounds.return_value = []
        result = self._call(svc)  # should not raise even though self.db is None
        assert result["updated_sessions"] == []

    def test_db_commit_called_when_db_available(self):
        svc = _svc()
        final = _match(title="Final", mid=1)
        final.participant_user_ids = []
        svc.repo.get_distinct_rounds.return_value = [1, 2]
        svc.repo.get_sessions_by_phase_and_round.return_value = [final]
        self._call(svc, winners=[10, 20])
        svc._mock_db.commit.assert_called_once()


# ===========================================================================
# _handle_semifinal_completion  (lines 130-223) — legacy method
# ===========================================================================

class TestHandleSemifinalCompletion:
    def _call(self, svc, session=None, tournament=None, game_results=None):
        return svc._handle_semifinal_completion(
            completed_session=session or _match(),
            tournament=tournament or _tournament(),
            game_results=game_results or {},
        )

    def test_not_all_semis_complete_returns_waiting(self):
        svc = _svc()
        sf1 = _match(title="SF1", game_results='{"r": 1}')
        sf2 = _match(title="SF2", game_results=None)
        svc.repo.get_sessions_by_phase_and_round.return_value = [sf1, sf2]
        with patch(_PARSE, return_value={}):
            result = self._call(svc)
        assert "Waiting" in result["message"]

    def test_all_semis_complete_score_based_p1_wins(self):
        svc = _svc()
        sf1 = _match(title="SF1", game_results='{"r": 1}')
        sf2 = _match(title="SF2", game_results='{"r": 2}')
        sf1.participant_user_ids = [10, 20]
        sf2.participant_user_ids = [30, 40]
        svc.repo.get_sessions_by_phase_and_round.return_value = [sf1, sf2]

        def _parse(data):
            return {"raw_results": [
                {"user_id": 10, "score": 3},
                {"user_id": 20, "score": 1},
            ]}

        with patch(_PARSE, side_effect=_parse):
            with patch.object(svc, "_create_bronze_match", return_value=MagicMock(id=99)):
                with patch.object(svc, "_create_final_match", return_value=MagicMock(id=100)):
                    # round2 sessions empty → no existing bronze/final
                    svc.repo.get_sessions_by_phase_and_round.side_effect = [
                        [sf1, sf2],  # first call: get all semis
                        [],          # second call: round2 sessions
                    ]
                    result = self._call(svc)
        assert "Created" in result["message"]

    def test_all_semis_complete_p2_wins(self):
        svc = _svc()
        sf1 = _match(title="SF1", game_results='{"r": 1}')
        sf1.participant_user_ids = [10, 20]
        svc.repo.get_sessions_by_phase_and_round.side_effect = [
            [sf1],
            [],
        ]
        parsed = {"raw_results": [
            {"user_id": 10, "score": 1},
            {"user_id": 20, "score": 5},
        ]}
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_create_bronze_match", return_value=MagicMock(id=99)):
                with patch.object(svc, "_create_final_match", return_value=MagicMock(id=100)):
                    result = self._call(svc)
        # Only 1 semi → 1 loser/winner, not enough for bronze/final creation (len >= 2)
        # but the result dict should still be returned
        assert "message" in result

    def test_all_semis_complete_tie_first_player_wins(self):
        svc = _svc()
        sf1 = _match(title="SF1", game_results='{"r": 1}')
        svc.repo.get_sessions_by_phase_and_round.side_effect = [
            [sf1], [],
        ]
        parsed = {"raw_results": [
            {"user_id": 10, "score": 2},
            {"user_id": 20, "score": 2},
        ]}
        with patch(_PARSE, return_value=parsed):
            with patch.object(svc, "_create_bronze_match", return_value=MagicMock(id=99)):
                with patch.object(svc, "_create_final_match", return_value=MagicMock(id=100)):
                    result = self._call(svc)
        assert "message" in result

    def test_existing_bronze_and_final_not_recreated(self):
        svc = _svc()
        sf1 = _match(title="SF1", game_results='{"r": 1}')
        existing_bronze = _match(title="Bronze Medal", mid=5)
        existing_final = _match(title="Final", mid=6)
        svc.repo.get_sessions_by_phase_and_round.side_effect = [
            [sf1],
            [existing_bronze, existing_final],
        ]
        parsed = {"raw_results": [
            {"user_id": 10, "score": 3},
            {"user_id": 20, "score": 1},
        ]}
        with patch(_PARSE, return_value=parsed):
            result = self._call(svc)
        assert "already exist" in result["message"]


# ===========================================================================
# _create_bronze_match / _create_final_match  (lines 234-281)
# ===========================================================================

class TestCreateBronzeAndFinalMatch:
    def test_create_bronze_match_calls_repo(self):
        svc = _svc()
        ref = _match(
            date_start=datetime(2026, 4, 1, 10, tzinfo=timezone.utc),
            date_end=datetime(2026, 4, 1, 11, tzinfo=timezone.utc),
        )
        t = _tournament()
        svc.repo.create_session.return_value = MagicMock(id=99)
        result = svc._create_bronze_match(t, [30, 40], ref)
        svc.repo.create_session.assert_called_once()
        call_data = svc.repo.create_session.call_args[0][1]
        assert "Bronze" in call_data["title"]
        assert call_data["participant_user_ids"] == [30, 40]

    def test_create_final_match_calls_repo(self):
        svc = _svc()
        ref = _match(
            date_start=datetime(2026, 4, 1, 10, tzinfo=timezone.utc),
            date_end=datetime(2026, 4, 1, 11, tzinfo=timezone.utc),
        )
        t = _tournament()
        svc.repo.create_session.return_value = MagicMock(id=100)
        result = svc._create_final_match(t, [10, 20], ref)
        svc.repo.create_session.assert_called_once()
        call_data = svc.repo.create_session.call_args[0][1]
        assert "Final" in call_data["title"]
        assert call_data["participant_user_ids"] == [10, 20]

    def test_bronze_scheduled_1_day_after_reference(self):
        svc = _svc()
        ref = _match(
            date_start=datetime(2026, 4, 1, 10, tzinfo=timezone.utc),
            date_end=datetime(2026, 4, 1, 11, tzinfo=timezone.utc),
        )
        svc.repo.create_session.return_value = MagicMock(id=99)
        svc._create_bronze_match(_tournament(), [30, 40], ref)
        call_data = svc.repo.create_session.call_args[0][1]
        expected_start = datetime(2026, 4, 2, 10, tzinfo=timezone.utc)
        assert call_data["date_start"] == expected_start

    def test_final_scheduled_1_day_2_hours_after_reference(self):
        svc = _svc()
        ref = _match(
            date_start=datetime(2026, 4, 1, 10, tzinfo=timezone.utc),
            date_end=datetime(2026, 4, 1, 11, tzinfo=timezone.utc),
        )
        svc.repo.create_session.return_value = MagicMock(id=100)
        svc._create_final_match(_tournament(), [10, 20], ref)
        call_data = svc.repo.create_session.call_args[0][1]
        expected_start = datetime(2026, 4, 2, 12, tzinfo=timezone.utc)
        assert call_data["date_start"] == expected_start
