"""
Unit tests for skill_progression_service (DB-dependent functions)

NOTE: calculate_skill_value_from_placement and get_all_skill_keys are already
covered by existing integration tests that use the service. This file covers
the DB-dependent private helpers via MagicMock db:

  _compute_opponent_factor    — no opponents, opponent with no license,
                                opponent with dict-format skills, player_baseline<=0,
                                normal case with valid opponent
  _extract_tournament_skills  — list-format enabled, list-format disabled (→ DB fallback),
                                dict-format, empty reward_config (→ DB fallback),
                                DB fallback returns results
  get_baseline_skills         — no license, not-dict football_skills, dict-format,
                                scalar-format, missing skills get DEFAULT_BASELINE
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.skill_progression_service import (
    _compute_opponent_factor,
    _extract_tournament_skills,
    get_baseline_skills,
    DEFAULT_BASELINE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db():
    return MagicMock()


def _q(db, first=None, all_=None):
    """Wire db.query().filter().first() / .all() to return given values."""
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    db.query.return_value = q
    return q


def _multi_q(db, specs):
    """Return different mocks on successive db.query() calls."""
    mocks = []
    for spec in specs:
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = spec.get("first")
        q.all.return_value = spec.get("all_", [])
        mocks.append(q)
    db.query.side_effect = mocks
    return mocks


def _make_opponent(user_id=99, football_skills=None):
    opp = MagicMock()
    opp.user_id = user_id
    return opp


def _make_license(football_skills):
    lic = MagicMock()
    lic.football_skills = football_skills
    return lic


# ===========================================================================
# _compute_opponent_factor
# ===========================================================================

@pytest.mark.unit
class TestComputeOpponentFactor:
    def test_no_opponents_returns_one(self):
        db = _db()
        _q(db, all_=[])  # No opponents in tournament
        result = _compute_opponent_factor(db, tournament_id=1, player_user_id=42, player_baseline_avg=60.0)
        assert result == 1.0

    def test_opponent_with_no_license_returns_one(self):
        db = _db()
        opp = _make_opponent(user_id=2)
        # First query: opponents list; Second query: opponent's license → None
        _multi_q(db, [
            {"all_": [opp]},  # opponents
            {"first": None},  # license not found
        ])
        result = _compute_opponent_factor(db, tournament_id=1, player_user_id=42, player_baseline_avg=60.0)
        assert result == 1.0  # no baseline_avgs → neutral

    def test_opponent_with_non_dict_football_skills_returns_one(self):
        db = _db()
        opp = _make_opponent(user_id=2)
        lic = _make_license(football_skills="invalid_string")  # not a dict
        _multi_q(db, [
            {"all_": [opp]},
            {"first": lic},
        ])
        result = _compute_opponent_factor(db, tournament_id=1, player_user_id=42, player_baseline_avg=60.0)
        assert result == 1.0

    def test_player_baseline_zero_returns_one(self):
        db = _db()
        opp = _make_opponent(user_id=2)
        lic = _make_license(football_skills={"passing": 70.0})  # scalar format
        _multi_q(db, [
            {"all_": [opp]},
            {"first": lic},
        ])
        result = _compute_opponent_factor(db, tournament_id=1, player_user_id=42, player_baseline_avg=0.0)
        assert result == 1.0

    def test_opponent_with_scalar_skills_normal_case(self):
        db = _db()
        opp = _make_opponent(user_id=2)
        # opponent avg = 80.0; player_baseline_avg = 60.0 → factor = 80/60 ≈ 1.3333
        lic = _make_license(football_skills={"passing": 80.0, "shooting": 80.0})
        _multi_q(db, [
            {"all_": [opp]},
            {"first": lic},
        ])
        result = _compute_opponent_factor(db, tournament_id=1, player_user_id=42, player_baseline_avg=60.0)
        assert result == round(80.0 / 60.0, 4)

    def test_opponent_with_dict_format_skills(self):
        db = _db()
        opp = _make_opponent(user_id=2)
        # dict-format: {"passing": {"baseline": 75, "current_level": 80, ...}}
        lic = _make_license(football_skills={"passing": {"baseline": 75.0, "current_level": 80.0}})
        _multi_q(db, [
            {"all_": [opp]},
            {"first": lic},
        ])
        result = _compute_opponent_factor(db, tournament_id=1, player_user_id=42, player_baseline_avg=50.0)
        # baseline = 75.0, avg_opponent = 75.0, factor = 75/50 = 1.5
        assert result == 1.5

    def test_opponent_factor_clamped_to_two(self):
        db = _db()
        opp = _make_opponent(user_id=2)
        # Opponent baseline 200 (unrealistically high) → factor 200/10 = 20, clamped to 2.0
        lic = _make_license(football_skills={"skill": 200.0})
        _multi_q(db, [
            {"all_": [opp]},
            {"first": lic},
        ])
        result = _compute_opponent_factor(db, tournament_id=1, player_user_id=42, player_baseline_avg=10.0)
        assert result == 2.0

    def test_opponent_factor_clamped_to_half(self):
        db = _db()
        opp = _make_opponent(user_id=2)
        # Opponent baseline 5.0 vs player 200.0 → factor 5/200 = 0.025, clamped to 0.5
        lic = _make_license(football_skills={"skill": 5.0})
        _multi_q(db, [
            {"all_": [opp]},
            {"first": lic},
        ])
        result = _compute_opponent_factor(db, tournament_id=1, player_user_id=42, player_baseline_avg=200.0)
        assert result == 0.5


# ===========================================================================
# _extract_tournament_skills
# ===========================================================================

@pytest.mark.unit
class TestExtractTournamentSkills:
    def _tournament_with_config(self, skill_mappings):
        t = MagicMock()
        t.reward_config = {"skill_mappings": skill_mappings}
        return t

    def test_list_format_enabled_skill(self):
        db = _db()
        tournament = self._tournament_with_config([
            {"skill": "passing", "enabled": True, "weight": 1.5},
            {"skill": "shooting", "enabled": False, "weight": 1.0},
        ])
        result = _extract_tournament_skills(db, tournament, skill_keys={"passing", "shooting"})
        assert result == {"passing": 1.5}
        # "shooting" disabled → not included

    def test_list_format_no_enabled_skills_falls_through_to_db(self):
        db = _db()
        tournament = self._tournament_with_config([
            {"skill": "passing", "enabled": False},
        ])
        # DB fallback: TournamentSkillMapping table returns empty
        _q(db, all_=[])
        result = _extract_tournament_skills(db, tournament, skill_keys={"passing"})
        assert result == {}

    def test_list_format_skill_not_in_skill_keys(self):
        db = _db()
        tournament = self._tournament_with_config([
            {"skill": "unknown_skill", "enabled": True, "weight": 1.0},
        ])
        _q(db, all_=[])
        result = _extract_tournament_skills(db, tournament, skill_keys={"passing"})
        assert result == {}

    def test_dict_format_legacy(self):
        db = _db()
        t = MagicMock()
        t.reward_config = {"skill_mappings": {"passing": {"some": "config"}, "dribbling": {}}}
        result = _extract_tournament_skills(db, t, skill_keys={"passing", "dribbling", "unknown"})
        assert result == {"passing": 1.0, "dribbling": 1.0}

    def test_empty_reward_config_uses_db_fallback(self):
        db = _db()
        t = MagicMock()
        t.reward_config = {}  # No skill_mappings key
        tm = MagicMock()
        tm.skill_name = "passing"
        tm.weight = 2.0
        _q(db, all_=[tm])
        result = _extract_tournament_skills(db, t, skill_keys={"passing"})
        assert result == {"passing": 2.0}

    def test_db_fallback_with_none_weight(self):
        db = _db()
        t = MagicMock()
        t.reward_config = None  # No config
        tm = MagicMock()
        tm.skill_name = "shooting"
        tm.weight = None  # None weight → defaults to 1.0
        _q(db, all_=[tm])
        result = _extract_tournament_skills(db, t, skill_keys={"shooting"})
        assert result == {"shooting": 1.0}

    def test_db_fallback_skill_not_in_skill_keys(self):
        db = _db()
        t = MagicMock()
        t.reward_config = {}
        tm = MagicMock()
        tm.skill_name = "unknown_skill"
        tm.weight = 1.0
        _q(db, all_=[tm])
        result = _extract_tournament_skills(db, t, skill_keys={"passing"})
        assert result == {}  # unknown_skill not in skill_keys → excluded


# ===========================================================================
# get_baseline_skills
# ===========================================================================

@pytest.mark.unit
class TestGetBaselineSkills:
    def test_no_license_returns_all_defaults(self):
        db = _db()
        _q(db, first=None)  # No license
        result = get_baseline_skills(db, user_id=42)
        # All skills should equal DEFAULT_BASELINE
        assert all(v == DEFAULT_BASELINE for v in result.values())
        assert len(result) > 0  # Has entries for all skill keys

    def test_license_with_empty_football_skills_returns_defaults(self):
        db = _db()
        lic = MagicMock()
        lic.football_skills = {}  # Empty dict → falsy
        _q(db, first=lic)
        result = get_baseline_skills(db, user_id=42)
        assert all(v == DEFAULT_BASELINE for v in result.values())

    def test_license_with_non_dict_football_skills_returns_defaults(self):
        db = _db()
        lic = MagicMock()
        lic.football_skills = "corrupted_string"
        _q(db, first=lic)
        result = get_baseline_skills(db, user_id=42)
        assert all(v == DEFAULT_BASELINE for v in result.values())

    def test_license_with_scalar_format_skills(self):
        db = _db()
        lic = MagicMock()
        # Old format: {"ball_control": 70, "dribbling": 65}
        lic.football_skills = {"ball_control": 70, "dribbling": 65}
        _q(db, first=lic)
        result = get_baseline_skills(db, user_id=42)
        # Skills explicitly set should have their values
        assert result["ball_control"] == 70.0
        assert result["dribbling"] == 65.0
        # Skills not in football_skills should default to DEFAULT_BASELINE
        # (at least some keys should be DEFAULT_BASELINE since there are ~29 skills)

    def test_license_with_dict_format_skills(self):
        db = _db()
        lic = MagicMock()
        # New format: {"passing": {"baseline": 75.0, "current_level": 80.0, ...}}
        lic.football_skills = {
            "passing": {"baseline": 75.0, "current_level": 80.0},
        }
        _q(db, first=lic)
        result = get_baseline_skills(db, user_id=42)
        assert result["passing"] == 75.0

    def test_missing_skill_gets_default_baseline(self):
        db = _db()
        lic = MagicMock()
        # Only one skill present; all others should fall back to DEFAULT_BASELINE
        lic.football_skills = {"ball_control": 80.0}
        _q(db, first=lic)
        result = get_baseline_skills(db, user_id=42)
        assert result["ball_control"] == 80.0
        # A skill not in football_skills → DEFAULT_BASELINE
        missing_skill_values = [v for k, v in result.items() if k != "ball_control"]
        assert all(v == DEFAULT_BASELINE for v in missing_skill_values)
