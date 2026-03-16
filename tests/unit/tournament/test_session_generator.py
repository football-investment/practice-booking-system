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


def _mock_tournament(fmt="INDIVIDUAL_RANKING", type_id=None, preset_min=None):
    """Build a mock Semester (tournament) object.

    Args:
        fmt: tournament format ("INDIVIDUAL_RANKING" or "HEAD_TO_HEAD")
        type_id: tournament_type_id (None for INDIVIDUAL_RANKING)
        preset_min: if set, attaches a GamePreset mock with
                    game_config["metadata"]["min_players"] = preset_min.
                    If None, game_config_obj.game_preset is explicitly set to
                    None so the new preset guard is NOT triggered accidentally.
    """
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

    if preset_min is not None:
        _preset = MagicMock()
        _preset.name = "Test Preset"
        _preset.game_config = {"metadata": {"min_players": preset_min}}
        t.game_config_obj = MagicMock()
        t.game_config_obj.game_preset = _preset
    else:
        # Explicit None prevents MagicMock truthiness from triggering preset guard
        t.game_config_obj = MagicMock()
        t.game_config_obj.game_preset = None

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


# ─────────────────────────────────────────────────────────────────────────────
# IRGV-01–04  Individual Ranking Generator Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestIndividualRankingPlayerCountValidation:
    """IRGV — Individual Ranking Generator Validation.

    Tests the two guards that apply to INDIVIDUAL_RANKING tournaments:
      1. Hardcoded >= 2 minimum (line 223 of session_generator.py)
      2. GamePreset.metadata.min_players guard (fires FIRST, before >= 2 check)
    """

    def _setup(self, player_count, preset_min=None, checked_in=0):
        svc, db = _make_svc()
        svc.validator.can_generate_sessions.return_value = (True, "OK")
        t = _mock_tournament(fmt="INDIVIDUAL_RANKING", preset_min=preset_min)
        svc.tournament_repo.get_or_404.return_value = t
        db.refresh.return_value = None
        db.query.return_value.filter.return_value.count.side_effect = [
            checked_in, player_count, player_count
        ]
        db.query.return_value.filter.return_value.all.return_value = [
            MagicMock() for _ in range(player_count)
        ]
        return svc, db, t

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_irgv01_no_preset_below_minimum_of_2(self, _sched):
        """IRGV-01: no preset, player_count=1 → fail on hardcoded >= 2 guard."""
        svc, db, _ = self._setup(player_count=1)
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is False
        assert "2" in msg
        assert sessions == []
        # Format-specific generator must NOT be called
        svc.individual_ranking_generator.generate.assert_not_called()

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_irgv02_no_preset_exactly_minimum_of_2(self, _sched):
        """IRGV-02: no preset, player_count=2 → succeeds (passes >= 2 guard)."""
        svc, db, _ = self._setup(player_count=2)
        svc.individual_ranking_generator.generate.return_value = [{"title": "R1"}]
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is True
        svc.individual_ranking_generator.generate.assert_called_once()

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_irgv03_preset_min_blocks_generation(self, _sched):
        """IRGV-03: preset min=8, player_count=5 → fail on preset guard.

        The preset guard fires BEFORE the format-routing branch, so even
        INDIVIDUAL_RANKING tournaments are blocked when they have too few players
        for their game preset.
        """
        svc, db, _ = self._setup(player_count=5, preset_min=8)
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is False
        assert "Test Preset" in msg
        assert "8" in msg        # preset minimum cited
        assert "5" in msg        # actual count cited
        assert sessions == []
        svc.individual_ranking_generator.generate.assert_not_called()

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_irgv04_preset_min_satisfied(self, _sched):
        """IRGV-04: preset min=8, player_count=8 → succeeds (preset guard passes)."""
        svc, db, _ = self._setup(player_count=8, preset_min=8)
        svc.individual_ranking_generator.generate.return_value = [{"title": "R1"}]
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is True
        svc.individual_ranking_generator.generate.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# GPV-01–05  GamePreset Player Count Validation (both formats)
# ─────────────────────────────────────────────────────────────────────────────

class TestGamePresetPlayerCountValidation:
    """GPV — GamePreset player count validation across HEAD_TO_HEAD and INDIVIDUAL_RANKING.

    The preset guard runs BEFORE format-routing, so it applies equally to both
    formats. In HEAD_TO_HEAD tournaments, preset guard fires BEFORE TournamentType
    validate_player_count() is reached.
    """

    def _setup_h2h(self, player_count, preset_min=None, type_min=4):
        """Set up a HEAD_TO_HEAD tournament with optional preset and a mock TournamentType."""
        svc, db = _make_svc()
        svc.validator.can_generate_sessions.return_value = (True, "OK")
        t = _mock_tournament(fmt="HEAD_TO_HEAD", type_id=5, preset_min=preset_min)
        svc.tournament_repo.get_or_404.return_value = t
        db.refresh.return_value = None
        db.query.return_value.filter.return_value.count.side_effect = [
            0, player_count, player_count
        ]
        db.query.return_value.filter.return_value.all.return_value = [
            MagicMock() for _ in range(max(player_count, 1))
        ]
        # Mock TournamentType for HEAD_TO_HEAD
        tt = MagicMock()
        tt.code = "league"
        tt.validate_player_count.return_value = (
            (True, "") if player_count >= type_min
            else (False, f"requires at least {type_min} players")
        )
        db.query.return_value.filter.return_value.first.return_value = tt
        return svc, db, t, tt

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_gpv01_preset_guard_fires_before_type_guard(self, _sched):
        """GPV-01: HEAD_TO_HEAD, preset_min=8, type_min=4, player_count=5.

        Preset guard fires and returns error before validate_player_count() is
        ever called on the TournamentType — confirms guard ordering.
        """
        svc, db, t, tt = self._setup_h2h(player_count=5, preset_min=8, type_min=4)
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is False
        assert "Test Preset" in msg   # preset error message
        assert "8" in msg             # preset minimum
        assert sessions == []
        # TournamentType.validate_player_count must NOT be reached
        tt.validate_player_count.assert_not_called()

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_gpv02_preset_and_type_both_satisfied(self, _sched):
        """GPV-02: HEAD_TO_HEAD, preset_min=4, type_min=4, player_count=4 → ok."""
        svc, db, t, tt = self._setup_h2h(player_count=4, preset_min=4, type_min=4)
        svc.league_generator.generate.return_value = [{"title": "Match 1"}]
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is True
        svc.league_generator.generate.assert_called_once()

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_gpv03_no_preset_type_guard_applies(self, _sched):
        """GPV-03: HEAD_TO_HEAD, no preset, type_min=4, player_count=3 → type guard fires."""
        svc, db, t, tt = self._setup_h2h(player_count=3, preset_min=None, type_min=4)
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is False
        assert "4" in msg             # type minimum cited
        assert "Test Preset" not in msg  # no preset error
        tt.validate_player_count.assert_called_once_with(3)

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_gpv04_preset_min_zero_is_skipped(self, _sched):
        """GPV-04: preset with min_players=0 (or absent) → guard skipped, type check applies.

        A preset min_players of 0 is treated as 'no constraint' — the guard
        uses `if _preset_min and ...` so falsy values (0, None) are skipped.
        """
        svc, db, t, tt = self._setup_h2h(player_count=4, preset_min=0, type_min=4)
        svc.league_generator.generate.return_value = [{"title": "Match 1"}]
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is True
        tt.validate_player_count.assert_called_once_with(4)

    @patch(f"{PATCH_BASE}.get_campus_schedule", return_value=_campus_schedule())
    def test_gpv05_preset_min_satisfied_type_check_still_runs(self, _sched):
        """GPV-05: preset_min=8, player_count=8, type_min=4 → both pass, generation succeeds.

        Confirms preset guard does not short-circuit type validation when it passes —
        HEAD_TO_HEAD still calls validate_player_count() after the preset guard succeeds.
        """
        svc, db, t, tt = self._setup_h2h(player_count=8, preset_min=8, type_min=4)
        svc.league_generator.generate.return_value = [{"title": "Match 1"}]
        ok, msg, sessions = svc.generate_sessions(tournament_id=1)
        assert ok is True
        tt.validate_player_count.assert_called_once_with(8)
