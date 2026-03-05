"""
Unit tests for app/services/tournament/session_generation/session_generator.py

Covers TournamentSessionGenerator.generate_sessions decision branches:
  - validation fail → early return
  - campus_ids provided (multi-campus) vs empty (single-campus)
  - checked_in_count > 0 (check-in pool) vs 0 (fallback)
  - seeding pool integrity violation
  - INDIVIDUAL_RANKING with player_count < 2 → fail
  - INDIVIDUAL_RANKING success
  - HEAD_TO_HEAD: no tournament_type → fail
  - HEAD_TO_HEAD: invalid player count → fail
  - HEAD_TO_HEAD: league / knockout / group_knockout / swiss / unknown
  - tournament_config_obj missing → raises ValueError
  - exception → rollback and re-raise
"""
import pytest
from unittest.mock import MagicMock, patch, call

from app.services.tournament.session_generation.session_generator import TournamentSessionGenerator


# ── helpers ──────────────────────────────────────────────────────────────────

PATCH_BASE = "app.services.tournament.session_generation.session_generator"


def _make_svc():
    db = MagicMock()
    with patch(f"{PATCH_BASE}.TournamentRepository"), \
         patch(f"{PATCH_BASE}.GenerationValidator"), \
         patch(f"{PATCH_BASE}.LeagueGenerator"), \
         patch(f"{PATCH_BASE}.KnockoutGenerator"), \
         patch(f"{PATCH_BASE}.SwissGenerator"), \
         patch(f"{PATCH_BASE}.GroupKnockoutGenerator"), \
         patch(f"{PATCH_BASE}.IndividualRankingGenerator"):
        svc = TournamentSessionGenerator(db)
    return svc, db


def _mock_tournament(fmt="INDIVIDUAL_RANKING", type_id=None):
    t = MagicMock()
    t.id = 1
    t.name = "Test Cup"
    t.format = fmt
    t.tournament_type_id = type_id
    t.master_instructor_id = 10
    t.campus_id = None
    t.location = MagicMock()
    t.campus = MagicMock()
    t.tournament_config_obj = MagicMock()
    t.tournament_config_obj.sessions_generated = False
    t.tournament_config_obj.sessions_generated_at = None
    if hasattr(t, 'tournament_config_obj') and t.tournament_config_obj:
        pass
    return t


def _campus_schedule(duration=90, break_m=15, fields=1):
    return {
        "match_duration_minutes": duration,
        "break_duration_minutes": break_m,
        "parallel_fields": fields,
    }


# ─────────────────────────────────────────────────────────────────────────────
# can_generate_sessions — delegates to validator
# ─────────────────────────────────────────────────────────────────────────────

class TestCanGenerateSessions:

    def test_delegates_to_validator(self):
        svc, _ = _make_svc()
        svc.validator.can_generate_sessions.return_value = (True, "OK")
        result = svc.can_generate_sessions(1)
        assert result == (True, "OK")


# ─────────────────────────────────────────────────────────────────────────────
# generate_sessions — validation fail
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateSessionsValidationFail:

    def test_cannot_generate_returns_false_early(self):
        svc, db = _make_svc()
        svc.validator.can_generate_sessions.return_value = (False, "Enrollment still open")
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is False
        assert "Enrollment still open" in msg
        assert sessions == []
        # tournament_repo should not have been called
        svc.tournament_repo.get_or_404.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# generate_sessions — single-campus path
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateSessionsSingleCampus:

    def _setup(self, fmt="INDIVIDUAL_RANKING", checked_in=5, player_count=5, type_id=None):
        svc, db = _make_svc()
        svc.validator.can_generate_sessions.return_value = (True, "OK")
        t = _mock_tournament(fmt=fmt, type_id=type_id)
        svc.tournament_repo.get_or_404.return_value = t
        db.refresh.return_value = None

        # SemesterEnrollment query chains:
        # checked_in_count = first count(), player_count = second count()
        db.query.return_value.filter.return_value.count.side_effect = [checked_in, player_count, player_count]
        db.query.return_value.filter.return_value.all.return_value = [MagicMock() for _ in range(player_count)]
        db.flush.return_value = None
        db.commit.return_value = None
        return svc, db, t

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_individual_ranking_success(self, mock_schedule):
        svc, db, t = self._setup(fmt="INDIVIDUAL_RANKING", checked_in=0, player_count=5)
        session_data = {"title": "Round 1", "date_start": None, "date_end": None}
        svc.individual_ranking_generator.generate.return_value = [session_data]
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is True
        assert len(sessions) == 1
        svc.individual_ranking_generator.generate.assert_called_once()

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_individual_ranking_not_enough_players(self, mock_schedule):
        svc, db, t = self._setup(fmt="INDIVIDUAL_RANKING", checked_in=0, player_count=1)
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is False
        assert "2" in msg
        assert sessions == []

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_head_to_head_no_tournament_type_fails(self, mock_schedule):
        svc, db, t = self._setup(fmt="HEAD_TO_HEAD", checked_in=0, player_count=4, type_id=None)
        db.query.return_value.filter.return_value.first.return_value = None
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is False
        assert "tournament type" in msg.lower()

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_head_to_head_invalid_player_count_fails(self, mock_schedule):
        svc, db, t = self._setup(fmt="HEAD_TO_HEAD", checked_in=0, player_count=4, type_id=5)
        tt = MagicMock()
        tt.validate_player_count.return_value = (False, "Need at least 8 players")
        db.query.return_value.filter.return_value.first.return_value = tt
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is False
        assert "8 players" in msg

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_head_to_head_league_dispatches_correctly(self, mock_schedule):
        svc, db, t = self._setup(fmt="HEAD_TO_HEAD", checked_in=0, player_count=6, type_id=5)
        tt = MagicMock()
        tt.code = "league"
        tt.validate_player_count.return_value = (True, "OK")
        db.query.return_value.filter.return_value.first.return_value = tt
        svc.league_generator.generate.return_value = [{"title": "Match 1"}]
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is True
        svc.league_generator.generate.assert_called_once()

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_head_to_head_knockout_dispatches_correctly(self, mock_schedule):
        svc, db, t = self._setup(fmt="HEAD_TO_HEAD", checked_in=0, player_count=8, type_id=5)
        tt = MagicMock()
        tt.code = "knockout"
        tt.validate_player_count.return_value = (True, "OK")
        db.query.return_value.filter.return_value.first.return_value = tt
        svc.knockout_generator.generate.return_value = [{"title": "QF1"}]
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is True
        svc.knockout_generator.generate.assert_called_once()

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_head_to_head_group_knockout_dispatches(self, mock_schedule):
        svc, db, t = self._setup(fmt="HEAD_TO_HEAD", checked_in=0, player_count=8, type_id=5)
        tt = MagicMock()
        tt.code = "group_knockout"
        tt.validate_player_count.return_value = (True, "OK")
        db.query.return_value.filter.return_value.first.return_value = tt
        svc.group_knockout_generator.generate.return_value = [{"title": "Group A"}]
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is True
        svc.group_knockout_generator.generate.assert_called_once()

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_head_to_head_swiss_dispatches(self, mock_schedule):
        svc, db, t = self._setup(fmt="HEAD_TO_HEAD", checked_in=0, player_count=6, type_id=5)
        tt = MagicMock()
        tt.code = "swiss"
        tt.validate_player_count.return_value = (True, "OK")
        db.query.return_value.filter.return_value.first.return_value = tt
        svc.swiss_generator.generate.return_value = [{"title": "Swiss R1"}]
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is True
        svc.swiss_generator.generate.assert_called_once()

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_head_to_head_unknown_type_fails(self, mock_schedule):
        svc, db, t = self._setup(fmt="HEAD_TO_HEAD", checked_in=0, player_count=6, type_id=5)
        tt = MagicMock()
        tt.code = "unknown_format"
        tt.validate_player_count.return_value = (True, "OK")
        db.query.return_value.filter.return_value.first.return_value = tt
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is False
        assert "Unknown" in msg


# ─────────────────────────────────────────────────────────────────────────────
# check-in seeding pool
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckInSeedingPool:

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_check_in_pool_used_when_check_ins_exist(self, mock_schedule):
        svc, db = _make_svc()
        svc.validator.can_generate_sessions.return_value = (True, "OK")
        t = _mock_tournament(fmt="INDIVIDUAL_RANKING")
        svc.tournament_repo.get_or_404.return_value = t
        db.refresh.return_value = None
        # checked_in_count = 3, player_count = 3
        db.query.return_value.filter.return_value.count.side_effect = [3, 3, 3]
        db.query.return_value.filter.return_value.all.return_value = [MagicMock() for _ in range(3)]
        svc.individual_ranking_generator.generate.return_value = [{"title": "R1"}]
        ok, msg, _ = svc.generate_sessions(tournament_id=1)
        assert ok is True

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_integrity_violation_logged_but_continues(self, mock_schedule):
        """checked_in_count != player_count triggers integrity warning but generation continues."""
        svc, db = _make_svc()
        svc.validator.can_generate_sessions.return_value = (True, "OK")
        t = _mock_tournament(fmt="INDIVIDUAL_RANKING")
        svc.tournament_repo.get_or_404.return_value = t
        db.refresh.return_value = None
        # checked_in=5 but player_count query returns 3 (divergence)
        db.query.return_value.filter.return_value.count.side_effect = [5, 3, 3]
        db.query.return_value.filter.return_value.all.return_value = [MagicMock() for _ in range(3)]
        svc.individual_ranking_generator.generate.return_value = [{"title": "R1"}]
        ok, msg, _ = svc.generate_sessions(tournament_id=1)
        assert ok is True  # divergence logged but does not abort


# ─────────────────────────────────────────────────────────────────────────────
# multi-campus path
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateSessionsMultiCampus:

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule(duration=75, break_m=10, fields=2))
    def test_multi_campus_resolves_per_campus_config(self, mock_schedule):
        svc, db = _make_svc()
        svc.validator.can_generate_sessions.return_value = (True, "OK")
        t = _mock_tournament(fmt="INDIVIDUAL_RANKING")
        svc.tournament_repo.get_or_404.return_value = t
        db.refresh.return_value = None
        db.query.return_value.filter.return_value.count.side_effect = [0, 4, 4]
        db.query.return_value.filter.return_value.all.return_value = [MagicMock() for _ in range(4)]
        svc.individual_ranking_generator.generate.return_value = [{"title": "R1"}]
        ok, msg, _ = svc.generate_sessions(tournament_id=1, campus_ids=[1, 2])
        assert ok is True
        # get_campus_schedule called twice (once per campus)
        assert mock_schedule.call_count == 2


# ─────────────────────────────────────────────────────────────────────────────
# tournament_config_obj missing
# ─────────────────────────────────────────────────────────────────────────────

class TestTournamentConfigObjMissing:

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_no_config_obj_raises_value_error(self, mock_schedule):
        svc, db = _make_svc()
        svc.validator.can_generate_sessions.return_value = (True, "OK")
        t = _mock_tournament(fmt="INDIVIDUAL_RANKING")
        t.tournament_config_obj = None  # Missing config
        svc.tournament_repo.get_or_404.return_value = t
        db.refresh.return_value = None
        db.query.return_value.filter.return_value.count.side_effect = [0, 4, 4]
        db.query.return_value.filter.return_value.all.return_value = [MagicMock() for _ in range(4)]
        svc.individual_ranking_generator.generate.return_value = [{"title": "R1"}]
        with pytest.raises(ValueError, match="TournamentConfiguration"):
            svc.generate_sessions(tournament_id=1)
        db.rollback.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# exception handling
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateSessionsException:

    @patch(f"{PATCH_BASE}.get_campus_schedule", side_effect=RuntimeError("Campus DB error"))
    def test_exception_rollback_and_reraise(self, mock_schedule):
        svc, db = _make_svc()
        svc.validator.can_generate_sessions.return_value = (True, "OK")
        t = _mock_tournament(fmt="INDIVIDUAL_RANKING")
        svc.tournament_repo.get_or_404.return_value = t
        db.refresh.return_value = None
        db.query.return_value.filter.return_value.count.side_effect = [0, 4]
        with pytest.raises(RuntimeError, match="Campus DB error"):
            svc.generate_sessions(tournament_id=1)
        db.rollback.assert_called_once()
