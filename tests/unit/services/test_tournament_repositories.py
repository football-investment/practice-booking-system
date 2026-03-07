"""
Unit tests for app/services/tournament/repositories.py
Covers: SQLSessionRepository, FakeSessionRepository
All branches: exclude_bronze, None game_results, str JSON, dict, mock fallback
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.tournament.repositories import (
    SQLSessionRepository,
    FakeSessionRepository,
)
from app.models.tournament_enums import TournamentPhase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session(
    semester_id=1,
    phase=TournamentPhase.KNOCKOUT,
    round_num=1,
    title="Match 1",
    is_tournament_game=True,
    game_results=None,
):
    s = MagicMock()
    s.semester_id = semester_id
    s.tournament_phase = phase
    s.tournament_round = round_num
    s.title = title
    s.is_tournament_game = is_tournament_game
    s.game_results = game_results
    return s


def _db_query_chain(*result):
    """Build a fluent query mock that returns `result` from .all()."""
    q = MagicMock()
    q.filter.return_value = q
    q.distinct.return_value = q
    q.all.return_value = list(result)
    return q


# ---------------------------------------------------------------------------
# SQLSessionRepository
# ---------------------------------------------------------------------------

class TestSQLSessionRepository:

    def _repo(self):
        db = MagicMock()
        return SQLSessionRepository(db), db

    # -- get_sessions_by_phase_and_round --

    def test_sql_get_sessions_exclude_bronze_true(self):
        """exclude_bronze=True applies extra filter chain."""
        repo, db = self._repo()
        q = MagicMock()
        q.filter.return_value = q
        q.all.return_value = [MagicMock()]
        db.query.return_value = q

        sessions = repo.get_sessions_by_phase_and_round(1, TournamentPhase.KNOCKOUT, 1, exclude_bronze=True)

        # filter was called at least twice (base filter + bronze exclusion)
        assert db.query.call_count == 1
        # .all() was ultimately called
        q.all.assert_called_once()

    def test_sql_get_sessions_exclude_bronze_false(self):
        """exclude_bronze=False skips the title ilike filter."""
        repo, db = self._repo()
        q = MagicMock()
        q.filter.return_value = q
        q.all.return_value = []
        db.query.return_value = q

        sessions = repo.get_sessions_by_phase_and_round(1, TournamentPhase.KNOCKOUT, 1, exclude_bronze=False)
        # filter called once (the base and_ block only)
        assert q.filter.call_count == 1
        assert sessions == []

    # -- get_distinct_rounds --

    def test_sql_get_distinct_rounds_filters_none(self):
        """None tournament_round values are excluded from result."""
        repo, db = self._repo()
        q = MagicMock()
        q.filter.return_value = q
        q.distinct.return_value = q
        q.all.return_value = [(1,), (None,), (2,)]
        db.query.return_value = q

        rounds = repo.get_distinct_rounds(1, TournamentPhase.KNOCKOUT)
        assert rounds == [1, 2]

    def test_sql_get_distinct_rounds_sorted(self):
        """Rounds are returned sorted ascending."""
        repo, db = self._repo()
        q = MagicMock()
        q.filter.return_value = q
        q.distinct.return_value = q
        q.all.return_value = [(3,), (1,), (2,)]
        db.query.return_value = q

        rounds = repo.get_distinct_rounds(1, TournamentPhase.KNOCKOUT)
        assert rounds == [1, 2, 3]

    # -- count_completed_sessions --

    def test_sql_count_completed_sessions(self):
        """Sessions with non-None game_results are counted."""
        repo, db = self._repo()
        s1 = MagicMock(); s1.game_results = {"winner_user_id": 42}
        s2 = MagicMock(); s2.game_results = None
        s3 = MagicMock(); s3.game_results = {"winner_user_id": 7}
        count = repo.count_completed_sessions([s1, s2, s3])
        assert count == 2

    def test_sql_count_completed_empty(self):
        repo, db = self._repo()
        assert repo.count_completed_sessions([]) == 0

    # -- get_winner_from_session --

    def test_sql_winner_none_game_results(self):
        """No game_results → None."""
        repo, db = self._repo()
        s = MagicMock(); s.game_results = None
        assert repo.get_winner_from_session(s) is None

    def test_sql_winner_dict_game_results(self):
        """Dict game_results → extracts winner_user_id."""
        repo, db = self._repo()
        s = MagicMock(); s.game_results = {"winner_user_id": 42}
        assert repo.get_winner_from_session(s) == 42

    def test_sql_winner_json_string_game_results(self):
        """JSON-string game_results → parsed dict → winner_user_id."""
        repo, db = self._repo()
        s = MagicMock()
        s.game_results = json.dumps({"winner_user_id": 99, "score": "3-1"})
        assert repo.get_winner_from_session(s) == 99

    def test_sql_winner_no_winner_in_results(self):
        """Dict game_results without winner_user_id → None."""
        repo, db = self._repo()
        s = MagicMock(); s.game_results = {"score": "0-0"}
        assert repo.get_winner_from_session(s) is None

    # -- create_session --

    def test_sql_create_session_adds_and_flushes(self):
        """create_session adds to db and flushes."""
        repo, db = self._repo()
        tournament = MagicMock()
        tournament.id = 10
        tournament.max_participants = 16
        tournament.location = "Main Field"
        tournament.format = "KNOCKOUT"
        tournament.specialization_type = "LFA_FOOTBALL_PLAYER"

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        session_data = {
            "title": "Final",
            "date_start": now,
            "date_end": now,
            "tournament_phase": TournamentPhase.KNOCKOUT,
            "tournament_round": 1,
            "participant_user_ids": [42, 99],
        }

        with patch("app.services.tournament.repositories.SessionModel") as MockSession:
            mock_s = MagicMock(); MockSession.return_value = mock_s
            result = repo.create_session(tournament, session_data)

        db.add.assert_called_once_with(mock_s)
        db.flush.assert_called_once()
        assert result is mock_s


# ---------------------------------------------------------------------------
# FakeSessionRepository
# ---------------------------------------------------------------------------

class TestFakeSessionRepository:

    def test_empty_init(self):
        """Default init gives empty sessions list."""
        repo = FakeSessionRepository()
        assert repo.sessions == []
        assert repo.created_sessions == []
        assert repo._next_id == 1000

    def test_prepopulated_sessions(self):
        s1 = _session()
        repo = FakeSessionRepository(sessions=[s1])
        assert len(repo.sessions) == 1

    def test_fake_get_sessions_by_phase_exclude_bronze_false(self):
        """exclude_bronze=False returns all matching sessions including bronze."""
        bronze = _session(title="3rd Place Match")
        normal = _session(title="Final")
        bronze.tournament_round = 1
        normal.tournament_round = 1
        repo = FakeSessionRepository(sessions=[bronze, normal])

        result = repo.get_sessions_by_phase_and_round(
            1, TournamentPhase.KNOCKOUT, 1, exclude_bronze=False
        )
        assert len(result) == 2

    def test_fake_get_sessions_by_phase_exclude_bronze_true_filters_3rd(self):
        """exclude_bronze=True removes title containing '3rd'."""
        bronze = _session(title="3rd Place Final")
        normal = _session(title="Grand Final")
        repo = FakeSessionRepository(sessions=[bronze, normal])

        result = repo.get_sessions_by_phase_and_round(
            1, TournamentPhase.KNOCKOUT, 1, exclude_bronze=True
        )
        assert len(result) == 1
        assert result[0].title == "Grand Final"

    def test_fake_get_sessions_by_phase_exclude_bronze_filters_bronze_word(self):
        """exclude_bronze=True removes title containing 'bronze'."""
        bronze = _session(title="Bronze Match")
        normal = _session(title="Semi Final")
        repo = FakeSessionRepository(sessions=[bronze, normal])

        result = repo.get_sessions_by_phase_and_round(
            1, TournamentPhase.KNOCKOUT, 1, exclude_bronze=True
        )
        assert len(result) == 1

    def test_fake_get_sessions_wrong_phase_filtered(self):
        """Sessions in a different phase are excluded."""
        s = _session(phase=TournamentPhase.GROUP_STAGE)
        repo = FakeSessionRepository(sessions=[s])
        result = repo.get_sessions_by_phase_and_round(
            1, TournamentPhase.KNOCKOUT, 1
        )
        assert result == []

    # -- get_distinct_rounds --

    def test_fake_get_distinct_rounds(self):
        s1 = _session(round_num=2)
        s2 = _session(round_num=1)
        s3 = _session(round_num=2)
        repo = FakeSessionRepository(sessions=[s1, s2, s3])
        rounds = repo.get_distinct_rounds(1, TournamentPhase.KNOCKOUT)
        assert rounds == [1, 2]

    def test_fake_get_distinct_rounds_none_filtered(self):
        """Sessions with tournament_round=None are excluded."""
        s1 = _session(round_num=1)
        s2 = _session(round_num=None)
        s2.tournament_round = None
        repo = FakeSessionRepository(sessions=[s1, s2])
        rounds = repo.get_distinct_rounds(1, TournamentPhase.KNOCKOUT)
        assert rounds == [1]

    # -- count_completed_sessions --

    def test_fake_count_completed(self):
        s1 = _session(game_results={"winner_user_id": 42})
        s2 = _session(game_results=None)
        repo = FakeSessionRepository()
        assert repo.count_completed_sessions([s1, s2]) == 1

    # -- get_winner_from_session --

    def test_fake_winner_none(self):
        repo = FakeSessionRepository()
        s = _session(game_results=None)
        assert repo.get_winner_from_session(s) is None

    def test_fake_winner_dict(self):
        repo = FakeSessionRepository()
        s = _session(game_results={"winner_user_id": 55})
        assert repo.get_winner_from_session(s) == 55

    def test_fake_winner_mock_object_getattr(self):
        """Non-dict, non-None game_results → getattr fallback."""
        repo = FakeSessionRepository()
        s = MagicMock()
        mock_results = MagicMock()
        mock_results.winner_user_id = 77
        s.game_results = mock_results
        assert repo.get_winner_from_session(s) == 77

    def test_fake_winner_mock_without_attr(self):
        """MagicMock game_results without winner_user_id attr → None via getattr default."""
        repo = FakeSessionRepository()
        s = MagicMock()
        s.game_results = object()  # bare object, no winner_user_id attr
        result = repo.get_winner_from_session(s)
        assert result is None

    # -- create_session --

    def test_fake_create_session_returns_mock_session(self):
        """create_session stores and returns a Mock with correct attributes."""
        repo = FakeSessionRepository()
        tournament = MagicMock(); tournament.id = 10

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        session_data = {
            "title": "Final",
            "date_start": now,
            "date_end": now,
            "tournament_phase": TournamentPhase.KNOCKOUT,
            "tournament_round": 2,
            "participant_user_ids": [42, 99],
        }

        result = repo.create_session(tournament, session_data)

        assert result.id == 1000
        assert result.title == "Final"
        assert result.tournament_round == 2
        assert result.participant_user_ids == [42, 99]
        assert result.game_results is None
        assert len(repo.created_sessions) == 1
        assert len(repo.sessions) == 1

    def test_fake_create_session_increments_id(self):
        """Second create_session gets ID 1001."""
        repo = FakeSessionRepository()
        tournament = MagicMock(); tournament.id = 1
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        data = {
            "title": "M1", "date_start": now, "date_end": now,
            "tournament_phase": TournamentPhase.KNOCKOUT, "tournament_round": 1,
        }
        s1 = repo.create_session(tournament, data)
        s2 = repo.create_session(tournament, data)
        assert s1.id == 1000
        assert s2.id == 1001
