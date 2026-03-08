"""
Sprint 30 — app/models/semester.py
===================================
Target: ≥85% statement, ≥70% branch

Covers:
  Semester.format property:
    * tournament_config_obj with tournament_type_id + tournament_type → type.format
    * tournament_config_obj with scoring_type != HEAD_TO_HEAD → INDIVIDUAL_RANKING
    * tournament_config_obj with scoring_type == HEAD_TO_HEAD → falls through
    * tournament_config_obj present but type_id=None and no scoring_type → falls through
    * game_config_obj with game_preset_id + game_preset + format_config → preset format
    * game_config_obj present but game_preset_id=None → falls through
    * game_config_obj with preset but format_config empty → default
    * no config_obj at all → default INDIVIDUAL_RANKING

  Semester.validate_tournament_format_logic:
    * INDIVIDUAL_RANKING + tournament_type_id is None → OK (no error)
    * INDIVIDUAL_RANKING + tournament_type_id not None → ValueError
    * HEAD_TO_HEAD + tournament_type_id set → OK
    * HEAD_TO_HEAD + tournament_type_id is None → ValueError
    * other format → ValueError

  Backward-compat properties (P2 tournament config):
    * tournament_type_id — with/without tournament_config_obj
    * participant_type — with/without tournament_config_obj
    * is_multi_day — with/without tournament_config_obj
    * max_players — with/without tournament_config_obj
    * parallel_fields — with/without tournament_config_obj
    * scoring_type — with/without tournament_config_obj
    * measurement_unit — with/without tournament_config_obj
    * ranking_direction — with/without tournament_config_obj
    * number_of_rounds — with/without tournament_config_obj
    * assignment_type — with/without tournament_config_obj
    * sessions_generated — with/without tournament_config_obj
    * sessions_generated_at — with/without tournament_config_obj
    * enrollment_snapshot — with/without tournament_config_obj (+ None value)

  Backward-compat properties (P1 reward config):
    * reward_config — with/without reward_config_obj (+ None value)
    * reward_policy_name — with/without reward_config_obj
    * reward_policy_snapshot — with/without reward_config_obj (+ None value)

  Backward-compat properties (P3 game config):
    * game_preset_id — with/without game_config_obj
    * game_config — with/without game_config_obj (+ None value)
    * game_config_overrides — with/without game_config_obj (+ None value)
    * game_preset — with/without game_config_obj
"""

import pytest
from types import SimpleNamespace

from app.models.semester import Semester, SemesterStatus


# ── helpers ─────────────────────────────────────────────────────────────────

def _fake(**kwargs):
    """Create a SimpleNamespace with defaults for all relationship attrs."""
    defaults = {
        "tournament_config_obj": None,
        "reward_config_obj": None,
        "game_config_obj": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _config(**kwargs):
    """Create a mock TournamentConfiguration-like object."""
    return SimpleNamespace(**kwargs)


def _prop(prop_name, fake):
    """Call a Semester property getter on a fake object."""
    return getattr(Semester, prop_name).fget(fake)


# ============================================================================
# format property
# ============================================================================

class TestSemesterFormat:

    def test_default_when_no_config_objs(self):
        """FMT-01: no tournament_config_obj, no game_config_obj → INDIVIDUAL_RANKING."""
        f = _fake()
        assert Semester.format.fget(f) == "INDIVIDUAL_RANKING"

    def test_uses_tournament_type_format(self):
        """FMT-02: tournament_config_obj with type_id + type → returns type.format."""
        tc = _config(
            tournament_type_id=5,
            tournament_type=SimpleNamespace(format="HEAD_TO_HEAD"),
            scoring_type="HEAD_TO_HEAD"
        )
        f = _fake(tournament_config_obj=tc)
        assert Semester.format.fget(f) == "HEAD_TO_HEAD"

    def test_scoring_type_not_h2h_returns_individual(self):
        """FMT-03: scoring_type != HEAD_TO_HEAD → INDIVIDUAL_RANKING."""
        tc = _config(
            tournament_type_id=None,
            tournament_type=None,
            scoring_type="TIME_BASED"
        )
        f = _fake(tournament_config_obj=tc)
        assert Semester.format.fget(f) == "INDIVIDUAL_RANKING"

    def test_scoring_type_h2h_falls_through(self):
        """FMT-04: scoring_type=HEAD_TO_HEAD + no type_id → falls through to default."""
        tc = _config(
            tournament_type_id=None,
            tournament_type=None,
            scoring_type="HEAD_TO_HEAD"
        )
        f = _fake(tournament_config_obj=tc)
        # Falls through (no game_config_obj either) → INDIVIDUAL_RANKING
        assert Semester.format.fget(f) == "INDIVIDUAL_RANKING"

    def test_no_scoring_type_falls_through(self):
        """FMT-05: tournament_config_obj present but no type_id and no scoring_type → falls through."""
        tc = _config(tournament_type_id=None, tournament_type=None, scoring_type=None)
        f = _fake(tournament_config_obj=tc)
        assert Semester.format.fget(f) == "INDIVIDUAL_RANKING"

    def test_game_preset_format_config_used(self):
        """FMT-06: game_config_obj with game_preset + format_config → preset format returned."""
        gc = SimpleNamespace(
            game_preset_id=1,
            game_preset=SimpleNamespace(
                game_config={"format_config": {"HEAD_TO_HEAD": {}}}
            )
        )
        f = _fake(game_config_obj=gc)
        assert Semester.format.fget(f) == "HEAD_TO_HEAD"

    def test_game_preset_no_format_config_falls_through(self):
        """FMT-07: game_config_obj with preset but format_config empty → default."""
        gc = SimpleNamespace(
            game_preset_id=1,
            game_preset=SimpleNamespace(
                game_config={"format_config": {}}  # empty dict → falsy
            )
        )
        f = _fake(game_config_obj=gc)
        assert Semester.format.fget(f) == "INDIVIDUAL_RANKING"

    def test_game_config_obj_no_preset_id(self):
        """FMT-08: game_config_obj present but game_preset_id=None → falls through."""
        gc = SimpleNamespace(game_preset_id=None, game_preset=None)
        f = _fake(game_config_obj=gc)
        assert Semester.format.fget(f) == "INDIVIDUAL_RANKING"

    def test_game_config_obj_no_preset_object(self):
        """FMT-09: game_preset_id set but game_preset=None → falls through."""
        gc = SimpleNamespace(game_preset_id=5, game_preset=None)
        f = _fake(game_config_obj=gc)
        assert Semester.format.fget(f) == "INDIVIDUAL_RANKING"


# ============================================================================
# validate_tournament_format_logic
# ============================================================================

class TestValidateTournamentFormatLogic:

    def _fake_with_format(self, fmt, type_id=None):
        """Fake that exposes format and tournament_type_id as plain attrs."""
        ns = SimpleNamespace(format=fmt, tournament_type_id=type_id)
        return ns

    def test_individual_ranking_no_type_id_ok(self):
        """VTF-01: INDIVIDUAL_RANKING + tournament_type_id=None → no error."""
        f = self._fake_with_format("INDIVIDUAL_RANKING", type_id=None)
        Semester.validate_tournament_format_logic(f)  # should not raise

    def test_individual_ranking_with_type_id_raises(self):
        """VTF-02: INDIVIDUAL_RANKING + tournament_type_id set → ValueError."""
        f = self._fake_with_format("INDIVIDUAL_RANKING", type_id=5)
        with pytest.raises(ValueError, match="INDIVIDUAL_RANKING"):
            Semester.validate_tournament_format_logic(f)

    def test_head_to_head_with_type_id_ok(self):
        """VTF-03: HEAD_TO_HEAD + tournament_type_id set → no error."""
        f = self._fake_with_format("HEAD_TO_HEAD", type_id=2)
        Semester.validate_tournament_format_logic(f)  # should not raise

    def test_head_to_head_no_type_id_raises(self):
        """VTF-04: HEAD_TO_HEAD + tournament_type_id=None → ValueError."""
        f = self._fake_with_format("HEAD_TO_HEAD", type_id=None)
        with pytest.raises(ValueError, match="HEAD_TO_HEAD"):
            Semester.validate_tournament_format_logic(f)

    def test_invalid_format_raises(self):
        """VTF-05: unknown format string → ValueError."""
        f = self._fake_with_format("UNKNOWN_FORMAT", type_id=None)
        with pytest.raises(ValueError, match="Invalid format"):
            Semester.validate_tournament_format_logic(f)


# ============================================================================
# P2 Backward-compat properties — tournament_config_obj
# ============================================================================

class TestP2TournamentConfigProperties:
    """Each property: test with config_obj=None (default) and config_obj set."""

    def test_tournament_type_id_no_config(self):
        assert _prop("tournament_type_id", _fake()) is None

    def test_tournament_type_id_with_config(self):
        tc = _config(tournament_type_id=7)
        assert _prop("tournament_type_id", _fake(tournament_config_obj=tc)) == 7

    def test_participant_type_no_config(self):
        assert _prop("participant_type", _fake()) == "INDIVIDUAL"

    def test_participant_type_with_config(self):
        tc = _config(participant_type="TEAM")
        assert _prop("participant_type", _fake(tournament_config_obj=tc)) == "TEAM"

    def test_is_multi_day_no_config(self):
        assert _prop("is_multi_day", _fake()) is False

    def test_is_multi_day_with_config(self):
        tc = _config(is_multi_day=True)
        assert _prop("is_multi_day", _fake(tournament_config_obj=tc)) is True

    def test_max_players_no_config(self):
        assert _prop("max_players", _fake()) is None

    def test_max_players_with_config(self):
        tc = _config(max_players=16)
        assert _prop("max_players", _fake(tournament_config_obj=tc)) == 16

    def test_match_duration_minutes_no_config(self):
        assert _prop("match_duration_minutes", _fake()) is None

    def test_match_duration_minutes_with_config(self):
        tc = _config(match_duration_minutes=45)
        assert _prop("match_duration_minutes", _fake(tournament_config_obj=tc)) == 45

    def test_break_duration_minutes_no_config(self):
        assert _prop("break_duration_minutes", _fake()) is None

    def test_break_duration_minutes_with_config(self):
        tc = _config(break_duration_minutes=10)
        assert _prop("break_duration_minutes", _fake(tournament_config_obj=tc)) == 10

    def test_parallel_fields_no_config(self):
        assert _prop("parallel_fields", _fake()) == 1

    def test_parallel_fields_with_config(self):
        tc = _config(parallel_fields=3)
        assert _prop("parallel_fields", _fake(tournament_config_obj=tc)) == 3

    def test_scoring_type_no_config(self):
        assert _prop("scoring_type", _fake()) == "PLACEMENT"

    def test_scoring_type_with_config(self):
        tc = _config(scoring_type="HEAD_TO_HEAD")
        assert _prop("scoring_type", _fake(tournament_config_obj=tc)) == "HEAD_TO_HEAD"

    def test_measurement_unit_no_config(self):
        assert _prop("measurement_unit", _fake()) is None

    def test_measurement_unit_with_config(self):
        tc = _config(measurement_unit="SECONDS")
        assert _prop("measurement_unit", _fake(tournament_config_obj=tc)) == "SECONDS"

    def test_ranking_direction_no_config(self):
        assert _prop("ranking_direction", _fake()) is None

    def test_ranking_direction_with_config(self):
        tc = _config(ranking_direction="ASC")
        assert _prop("ranking_direction", _fake(tournament_config_obj=tc)) == "ASC"

    def test_number_of_rounds_no_config(self):
        assert _prop("number_of_rounds", _fake()) == 1

    def test_number_of_rounds_with_config(self):
        tc = _config(number_of_rounds=5)
        assert _prop("number_of_rounds", _fake(tournament_config_obj=tc)) == 5

    def test_assignment_type_no_config(self):
        assert _prop("assignment_type", _fake()) is None

    def test_assignment_type_with_config(self):
        tc = _config(assignment_type="OPEN_ASSIGNMENT")
        assert _prop("assignment_type", _fake(tournament_config_obj=tc)) == "OPEN_ASSIGNMENT"

    def test_sessions_generated_no_config(self):
        assert _prop("sessions_generated", _fake()) is False

    def test_sessions_generated_with_config(self):
        tc = _config(sessions_generated=True)
        assert _prop("sessions_generated", _fake(tournament_config_obj=tc)) is True

    def test_sessions_generated_at_no_config(self):
        assert _prop("sessions_generated_at", _fake()) is None

    def test_sessions_generated_at_with_config(self):
        from datetime import datetime
        ts = datetime(2026, 3, 1, 12, 0, 0)
        tc = _config(sessions_generated_at=ts)
        assert _prop("sessions_generated_at", _fake(tournament_config_obj=tc)) == ts

    def test_enrollment_snapshot_no_config(self):
        assert _prop("enrollment_snapshot", _fake()) == {}

    def test_enrollment_snapshot_with_config_none_value(self):
        """enrollment_snapshot=None on config → returns {} (or None fallback)."""
        tc = _config(enrollment_snapshot=None)
        result = _prop("enrollment_snapshot", _fake(tournament_config_obj=tc))
        assert result == {}

    def test_enrollment_snapshot_with_config_dict(self):
        snap = {"player_1": {"enrolled_at": "2026-03-01"}}
        tc = _config(enrollment_snapshot=snap)
        assert _prop("enrollment_snapshot", _fake(tournament_config_obj=tc)) == snap


# ============================================================================
# P1 Backward-compat properties — reward_config_obj
# ============================================================================

class TestP1RewardConfigProperties:

    def test_reward_config_no_obj(self):
        assert _prop("reward_config", _fake()) == {}

    def test_reward_config_none_value(self):
        rc = SimpleNamespace(reward_config=None, reward_policy_name="default", reward_policy_snapshot=None)
        result = _prop("reward_config", _fake(reward_config_obj=rc))
        assert result == {}

    def test_reward_config_with_value(self):
        cfg = {"first_place": {"xp": 100, "credits": 50}}
        rc = SimpleNamespace(reward_config=cfg, reward_policy_name="custom", reward_policy_snapshot=None)
        assert _prop("reward_config", _fake(reward_config_obj=rc)) == cfg

    def test_reward_policy_name_no_obj(self):
        assert _prop("reward_policy_name", _fake()) == "default"

    def test_reward_policy_name_with_obj(self):
        rc = SimpleNamespace(reward_policy_name="custom", reward_config=None, reward_policy_snapshot=None)
        assert _prop("reward_policy_name", _fake(reward_config_obj=rc)) == "custom"

    def test_reward_policy_snapshot_no_obj(self):
        assert _prop("reward_policy_snapshot", _fake()) == {}

    def test_reward_policy_snapshot_none_value(self):
        rc = SimpleNamespace(reward_policy_snapshot=None, reward_config=None, reward_policy_name="default")
        result = _prop("reward_policy_snapshot", _fake(reward_config_obj=rc))
        assert result == {}

    def test_reward_policy_snapshot_with_value(self):
        snap = {"policy": "v2"}
        rc = SimpleNamespace(reward_policy_snapshot=snap, reward_config=None, reward_policy_name="default")
        assert _prop("reward_policy_snapshot", _fake(reward_config_obj=rc)) == snap


# ============================================================================
# P3 Backward-compat properties — game_config_obj
# ============================================================================

class TestP3GameConfigProperties:

    def test_game_preset_id_no_obj(self):
        assert _prop("game_preset_id", _fake()) is None

    def test_game_preset_id_with_obj(self):
        gc = SimpleNamespace(game_preset_id=3, game_config=None, game_config_overrides=None, game_preset=None)
        assert _prop("game_preset_id", _fake(game_config_obj=gc)) == 3

    def test_game_config_no_obj(self):
        assert _prop("game_config", _fake()) == {}

    def test_game_config_none_value(self):
        gc = SimpleNamespace(game_preset_id=None, game_config=None, game_config_overrides=None, game_preset=None)
        result = _prop("game_config", _fake(game_config_obj=gc))
        assert result == {}

    def test_game_config_with_value(self):
        cfg = {"rules": "standard"}
        gc = SimpleNamespace(game_preset_id=None, game_config=cfg, game_config_overrides=None, game_preset=None)
        assert _prop("game_config", _fake(game_config_obj=gc)) == cfg

    def test_game_config_overrides_no_obj(self):
        assert _prop("game_config_overrides", _fake()) == {}

    def test_game_config_overrides_none_value(self):
        gc = SimpleNamespace(game_preset_id=None, game_config=None, game_config_overrides=None, game_preset=None)
        result = _prop("game_config_overrides", _fake(game_config_obj=gc))
        assert result == {}

    def test_game_config_overrides_with_value(self):
        ov = {"field_size": "small"}
        gc = SimpleNamespace(game_preset_id=None, game_config=None, game_config_overrides=ov, game_preset=None)
        assert _prop("game_config_overrides", _fake(game_config_obj=gc)) == ov

    def test_game_preset_no_obj(self):
        assert _prop("game_preset", _fake()) is None

    def test_game_preset_with_obj(self):
        preset = SimpleNamespace(code="footvolley")
        gc = SimpleNamespace(game_preset_id=1, game_config=None, game_config_overrides=None, game_preset=preset)
        result = _prop("game_preset", _fake(game_config_obj=gc))
        assert result is preset
