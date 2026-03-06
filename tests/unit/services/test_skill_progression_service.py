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
    _compute_match_performance_modifier,
    _extract_tournament_skills,
    calculate_skill_value_from_placement,
    calculate_tournament_skill_contribution,
    compute_single_tournament_skill_delta,
    get_baseline_skills,
    get_skill_timeline,
    get_skill_audit,
    DEFAULT_BASELINE,
)

_BASE = "app.services.skill_progression_service"


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


def _fluent_q(all_=None, first=None, count=None):
    """Fluent ORM query mock: handles filter/filter_by/order_by/all/first/count chains."""
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.order_by.return_value = q
    q.isnot.return_value = q
    q.all.return_value = all_ if all_ is not None else []
    q.first.return_value = first
    q.count.return_value = count if count is not None else 0
    return q


def _part(tournament=None, placement=1, user_id=42):
    """Mock TournamentParticipation with tournament + placement."""
    p = MagicMock()
    p.tournament = tournament
    p.placement = placement
    p.user_id = user_id
    p.achieved_at = MagicMock()
    p.achieved_at.isoformat.return_value = "2026-01-01T12:00:00"
    return p


def _tourn(tid=10, name="Test Cup"):
    """Mock tournament (Semester) with id/name/reward_config."""
    t = MagicMock()
    t.id = tid
    t.name = name
    t.reward_config = {}
    return t


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


# ===========================================================================
# _compute_match_performance_modifier
# ===========================================================================

@pytest.mark.unit
class TestComputeMatchPerformanceModifier:
    def _sess(self, participant_ids=None, game_results=None):
        s = MagicMock()
        s.participant_user_ids = participant_ids or []
        s.game_results = game_results
        return s

    def test_no_sessions_returns_zero(self):
        db = _db()
        q = _fluent_q(all_=[])
        db.query.return_value = q
        result = _compute_match_performance_modifier(db, tournament_id=1, user_id=42)
        assert result == 0.0

    def test_user_not_in_participants_returns_zero(self):
        db = _db()
        sess = self._sess(
            participant_ids=[99],  # user 42 not present → skipped
            game_results={"participants": [{"user_id": 99, "result": "WIN"}]},
        )
        q = _fluent_q(all_=[sess])
        db.query.return_value = q
        result = _compute_match_performance_modifier(db, tournament_id=1, user_id=42)
        assert result == 0.0

    def test_empty_results_skips_session(self):
        # Line 156: if not results: continue
        db = _db()
        sess = self._sess(participant_ids=[42], game_results={})
        q = _fluent_q(all_=[sess])
        db.query.return_value = q
        result = _compute_match_performance_modifier(db, tournament_id=1, user_id=42)
        assert result == 0.0

    def test_win_gives_positive_modifier(self):
        db = _db()
        sess = self._sess(
            participant_ids=[42, 99],
            game_results={
                "participants": [
                    {"user_id": 42, "result": "WIN", "score": 2},
                    {"user_id": 99, "result": "LOSS", "score": 0},
                ]
            },
        )
        q = _fluent_q(all_=[sess])
        db.query.return_value = q
        result = _compute_match_performance_modifier(db, tournament_id=1, user_id=42)
        assert result > 0.0

    def test_loss_gives_negative_modifier(self):
        db = _db()
        sess = self._sess(
            participant_ids=[42, 99],
            game_results={
                "participants": [
                    {"user_id": 42, "result": "LOSS", "score": 0},
                    {"user_id": 99, "result": "WIN", "score": 2},
                ]
            },
        )
        q = _fluent_q(all_=[sess])
        db.query.return_value = q
        result = _compute_match_performance_modifier(db, tournament_id=1, user_id=42)
        assert result < 0.0

    def test_json_string_results_parsed_correctly(self):
        import json
        db = _db()
        sess = self._sess(
            participant_ids=[42],
            game_results=json.dumps(
                {"participants": [{"user_id": 42, "result": "WIN", "score": 3}]}
            ),
        )
        q = _fluent_q(all_=[sess])
        db.query.return_value = q
        result = _compute_match_performance_modifier(db, tournament_id=1, user_id=42)
        assert result > 0.0


# ===========================================================================
# calculate_skill_value_from_placement
# ===========================================================================

@pytest.mark.unit
class TestCalculateSkillValueFromPlacement:
    def test_v3_first_place_positive_delta(self):
        # placement=1/4, prev=65 → percentile=0 → placement_skill=100
        # step=0.20, raw_delta=0.20*(100-65)=7.0 → new_val=72.0
        result = calculate_skill_value_from_placement(
            baseline=60.0, placement=1, total_players=4,
            tournament_count=1, prev_value=65.0,
        )
        assert result == 72.0

    def test_v3_last_place_negative_delta(self):
        # placement=4/4, prev=70 → percentile=1 → placement_skill=40
        # step=0.20, raw_delta=0.20*(40-70)=-6.0 → adj=-6/1=−6 → new_val=64.0
        result = calculate_skill_value_from_placement(
            baseline=60.0, placement=4, total_players=4,
            tournament_count=1, prev_value=70.0,
        )
        assert result == 64.0

    def test_v2_legacy_path_no_prev_value(self):
        # prev_value=None → legacy weighted-average formula
        result = calculate_skill_value_from_placement(
            baseline=60.0, placement=1, total_players=4,
            tournament_count=2, prev_value=None,
        )
        # baseline_weight=1/3, placement_weight=2/3
        # new_base=60/3+100*2/3=86.667, delta=26.667 → new_skill≈86.7
        assert result == 86.7

    def test_match_modifier_amplifies_positive_delta(self):
        # placement=1, prev=70 → raw_delta=6.0; modifier=0.5 (positive)
        # raw_delta *= (1+0.5)=1.5 → 9.0 → new_val=79.0
        result = calculate_skill_value_from_placement(
            baseline=60.0, placement=1, total_players=4,
            tournament_count=1, prev_value=70.0,
            match_performance_modifier=0.5,
        )
        assert result == 79.0

    def test_match_modifier_softens_negative_delta(self):
        # placement=4, prev=70 → raw_delta=-6.0; modifier=0.3 (positive, good perf)
        # raw_delta *= (1-0.3)=0.7 → -4.2 → new_val=65.8
        result = calculate_skill_value_from_placement(
            baseline=60.0, placement=4, total_players=4,
            tournament_count=1, prev_value=70.0,
            match_performance_modifier=0.3,
        )
        assert result == 65.8

    def test_single_player_percentile_zero(self):
        # total_players=1 → percentile=0.0 (special branch) → placement_skill=100
        result = calculate_skill_value_from_placement(
            baseline=60.0, placement=1, total_players=1,
            tournament_count=1, prev_value=80.0,
        )
        # step=0.20, raw_delta=0.20*(100-80)=4.0 → new_val=84.0
        assert result == 84.0


# ===========================================================================
# calculate_tournament_skill_contribution
# ===========================================================================

_PATCH_GBS = f"{_BASE}.get_baseline_skills"
_PATCH_ETS = f"{_BASE}._extract_tournament_skills"
_PATCH_OPP = f"{_BASE}._compute_opponent_factor"
_PATCH_MOD = f"{_BASE}._compute_match_performance_modifier"
_PATCH_SKV = f"{_BASE}.calculate_skill_value_from_placement"


@pytest.mark.unit
class TestCalculateTournamentSkillContribution:
    def test_no_participations_returns_baseline_data(self):
        db = _db()
        q = _fluent_q(all_=[])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"passing": 60.0}):
            result = calculate_tournament_skill_contribution(db, user_id=42, skill_keys=["passing"])
        assert result["passing"]["baseline"] == 60.0
        assert result["passing"]["current_value"] == 60.0
        assert result["passing"]["contribution"] == 0.0
        assert result["passing"]["tournament_count"] == 0

    def test_participation_no_tournament_skipped(self):
        db = _db()
        p = _part(tournament=None)
        q = _fluent_q(all_=[p])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"passing": 60.0}):
            result = calculate_tournament_skill_contribution(db, user_id=42, skill_keys=["passing"])
        assert result["passing"]["tournament_count"] == 0

    def test_participation_no_skills_skipped(self):
        db = _db()
        t = _tourn()
        p = _part(tournament=t)
        q = _fluent_q(all_=[p])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(_PATCH_ETS, return_value={}):
            result = calculate_tournament_skill_contribution(db, user_id=42, skill_keys=["passing"])
        assert result["passing"]["tournament_count"] == 0

    def test_participation_no_placement_skipped(self):
        db = _db()
        t = _tourn()
        p = _part(tournament=t, placement=None)
        q = _fluent_q(all_=[p])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(_PATCH_ETS, return_value={"passing": 1.0}):
            result = calculate_tournament_skill_contribution(db, user_id=42, skill_keys=["passing"])
        assert result["passing"]["tournament_count"] == 0

    def test_participation_zero_players_skipped(self):
        db = _db()
        t = _tourn()
        p = _part(tournament=t, placement=1)
        q1 = _fluent_q(all_=[p])   # participations
        q2 = _fluent_q(count=0)    # total_players → 0 → skip
        db.query.side_effect = [q1, q2]
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(_PATCH_ETS, return_value={"passing": 1.0}):
            result = calculate_tournament_skill_contribution(db, user_id=42, skill_keys=["passing"])
        assert result["passing"]["tournament_count"] == 0

    def test_happy_path_updates_skill_data(self):
        db = _db()
        t = _tourn()
        p = _part(tournament=t, placement=1)
        q1 = _fluent_q(all_=[p])
        q2 = _fluent_q(count=4)
        db.query.side_effect = [q1, q2]
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(_PATCH_ETS, return_value={"passing": 1.0}), \
             patch(_PATCH_OPP, return_value=1.0), \
             patch(_PATCH_MOD, return_value=0.0), \
             patch(_PATCH_SKV, return_value=72.0):
            result = calculate_tournament_skill_contribution(db, user_id=42, skill_keys=["passing"])
        assert result["passing"]["tournament_count"] == 1
        assert result["passing"]["current_value"] == 72.0
        assert result["passing"]["contribution"] == 12.0  # 72 - 60


# ===========================================================================
# compute_single_tournament_skill_delta
# ===========================================================================

@pytest.mark.unit
class TestComputeSingleTournamentSkillDelta:
    def test_no_participations_returns_empty(self):
        db = _db()
        q = _fluent_q(all_=[])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]):
            result = compute_single_tournament_skill_delta(db, user_id=42, tournament_id=10)
        assert result == {}

    def test_no_tournament_skipped(self):
        db = _db()
        p = _part(tournament=None)
        q = _fluent_q(all_=[p])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]):
            result = compute_single_tournament_skill_delta(db, user_id=42, tournament_id=10)
        assert result == {}

    def test_no_placement_skipped(self):
        db = _db()
        t = _tourn(tid=10)
        p = _part(tournament=t, placement=None)
        q = _fluent_q(all_=[p])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]):
            result = compute_single_tournament_skill_delta(db, user_id=42, tournament_id=10)
        assert result == {}

    def test_zero_players_skipped(self):
        db = _db()
        t = _tourn(tid=10)
        p = _part(tournament=t, placement=1)
        q1 = _fluent_q(all_=[p])
        q2 = _fluent_q(count=0)
        db.query.side_effect = [q1, q2]
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]), \
             patch(_PATCH_ETS, return_value={"passing": 1.0}):
            result = compute_single_tournament_skill_delta(db, user_id=42, tournament_id=10)
        assert result == {}

    def test_target_found_returns_nonzero_delta(self):
        db = _db()
        t = _tourn(tid=10)
        p = _part(tournament=t, placement=1)
        q1 = _fluent_q(all_=[p])
        q2 = _fluent_q(count=4)
        db.query.side_effect = [q1, q2]
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]), \
             patch(_PATCH_ETS, return_value={"passing": 1.0}), \
             patch(_PATCH_OPP, return_value=1.0), \
             patch(_PATCH_MOD, return_value=0.0), \
             patch(_PATCH_SKV, return_value=72.0):
            result = compute_single_tournament_skill_delta(db, user_id=42, tournament_id=10)
        assert result == {"passing": 12.0}  # 72.0 - 60.0

    def test_delta_zero_excluded_from_result(self):
        db = _db()
        t = _tourn(tid=10)
        p = _part(tournament=t, placement=1)
        q1 = _fluent_q(all_=[p])
        q2 = _fluent_q(count=4)
        db.query.side_effect = [q1, q2]
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]), \
             patch(_PATCH_ETS, return_value={"passing": 1.0}), \
             patch(_PATCH_OPP, return_value=1.0), \
             patch(_PATCH_MOD, return_value=0.0), \
             patch(_PATCH_SKV, return_value=60.0):  # same as prev → delta=0 → excluded
            result = compute_single_tournament_skill_delta(db, user_id=42, tournament_id=10)
        assert result == {}

    def test_target_not_in_participations_returns_empty(self):
        db = _db()
        t = _tourn(tid=5)   # different from tournament_id=10
        p = _part(tournament=t, placement=1)
        q1 = _fluent_q(all_=[p])
        q2 = _fluent_q(count=4)
        db.query.side_effect = [q1, q2]
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]), \
             patch(_PATCH_ETS, return_value={"passing": 1.0}), \
             patch(_PATCH_OPP, return_value=1.0), \
             patch(_PATCH_MOD, return_value=0.0), \
             patch(_PATCH_SKV, return_value=72.0):
            result = compute_single_tournament_skill_delta(db, user_id=42, tournament_id=10)
        assert result == {}  # tournament 5 != 10 → never was target


# ===========================================================================
# get_skill_timeline
# ===========================================================================

@pytest.mark.unit
class TestGetSkillTimeline:
    def test_unknown_skill_returns_none(self):
        db = _db()
        result = get_skill_timeline(db, user_id=42, skill_key="nonexistent_xyz_skill")
        assert result is None

    def test_no_participations_returns_empty_timeline(self):
        db = _db()
        q = _fluent_q(all_=[])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"ball_control": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["ball_control"]):
            result = get_skill_timeline(db, user_id=42, skill_key="ball_control")
        assert result == {
            "skill": "ball_control",
            "baseline": 60.0,
            "current_level": 60.0,
            "total_delta": 0.0,
            "timeline": [],
        }

    def test_participation_no_tournament_or_placement_skipped(self):
        db = _db()
        p = _part(tournament=None, placement=None)
        q = _fluent_q(all_=[p])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"ball_control": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["ball_control"]):
            result = get_skill_timeline(db, user_id=42, skill_key="ball_control")
        assert result["timeline"] == []

    def test_skill_not_in_tournament_skipped(self):
        db = _db()
        t = _tourn()
        p = _part(tournament=t, placement=1)
        q = _fluent_q(all_=[p])
        db.query.return_value = q
        # tournament has "shooting" skill, not "ball_control"
        with patch(_PATCH_GBS, return_value={"ball_control": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["ball_control"]), \
             patch(_PATCH_ETS, return_value={"shooting": 1.0}):
            result = get_skill_timeline(db, user_id=42, skill_key="ball_control")
        assert result["timeline"] == []

    def test_zero_players_skipped(self):
        db = _db()
        t = _tourn()
        p = _part(tournament=t, placement=1)
        q1 = _fluent_q(all_=[p])
        q2 = _fluent_q(count=0)
        db.query.side_effect = [q1, q2]
        with patch(_PATCH_GBS, return_value={"ball_control": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["ball_control"]), \
             patch(_PATCH_ETS, return_value={"ball_control": 1.0}):
            result = get_skill_timeline(db, user_id=42, skill_key="ball_control")
        assert result["timeline"] == []

    def test_happy_path_builds_timeline_entry(self):
        db = _db()
        t = _tourn(tid=10, name="Cup 2026")
        p = _part(tournament=t, placement=1)
        q1 = _fluent_q(all_=[p])
        q2 = _fluent_q(count=4)
        db.query.side_effect = [q1, q2]
        with patch(_PATCH_GBS, return_value={"ball_control": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["ball_control"]), \
             patch(_PATCH_ETS, return_value={"ball_control": 1.0}), \
             patch(_PATCH_OPP, return_value=1.0), \
             patch(_PATCH_SKV, return_value=67.0):
            result = get_skill_timeline(db, user_id=42, skill_key="ball_control")
        assert len(result["timeline"]) == 1
        entry = result["timeline"][0]
        assert entry["tournament_id"] == 10
        assert entry["tournament_name"] == "Cup 2026"
        assert entry["placement"] == 1
        assert entry["total_players"] == 4
        assert entry["skill_value_after"] == 67.0
        assert entry["delta_from_baseline"] == 7.0   # 67 - 60
        assert entry["delta_from_previous"] == 7.0   # 67 - 60 (first tournament)
        assert result["current_level"] == 67.0
        assert result["total_delta"] == 7.0


# ===========================================================================
# get_skill_audit
# ===========================================================================

@pytest.mark.unit
class TestGetSkillAudit:
    def test_no_participations_returns_empty_list(self):
        db = _db()
        q = _fluent_q(all_=[])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]):
            result = get_skill_audit(db, user_id=42)
        assert result == []

    def test_no_tournament_or_placement_skipped(self):
        db = _db()
        p = _part(tournament=None, placement=None)
        q = _fluent_q(all_=[p])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]):
            result = get_skill_audit(db, user_id=42)
        assert result == []

    def test_no_skills_in_tournament_skipped(self):
        db = _db()
        t = _tourn()
        p = _part(tournament=t, placement=1)
        q = _fluent_q(all_=[p])
        db.query.return_value = q
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]), \
             patch(_PATCH_ETS, return_value={}):
            result = get_skill_audit(db, user_id=42)
        assert result == []

    def test_zero_players_skipped(self):
        db = _db()
        t = _tourn()
        p = _part(tournament=t, placement=1)
        q1 = _fluent_q(all_=[p])
        q2 = _fluent_q(count=0)
        db.query.side_effect = [q1, q2]
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]), \
             patch(_PATCH_ETS, return_value={"passing": 1.0}):
            result = get_skill_audit(db, user_id=42)
        assert result == []

    def test_happy_path_returns_audit_row(self):
        db = _db()
        t = _tourn(tid=10, name="Cup 2026")
        p = _part(tournament=t, placement=1)
        q1 = _fluent_q(all_=[p])
        q2 = _fluent_q(count=4)
        db.query.side_effect = [q1, q2]
        # called twice per skill: delta compute + state advance
        with patch(_PATCH_GBS, return_value={"passing": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing"]), \
             patch(_PATCH_ETS, return_value={"passing": 1.0}), \
             patch(_PATCH_OPP, return_value=1.0), \
             patch(_PATCH_SKV, return_value=68.0):
            result = get_skill_audit(db, user_id=42)
        assert len(result) == 1
        row = result[0]
        assert row["tournament_id"] == 10
        assert row["skill"] == "passing"
        assert row["placement"] == 1
        assert row["total_players"] == 4
        assert row["delta_this_tournament"] == 8.0   # 68 - 60
        assert row["actual_changed"] is True
        assert row["fairness_ok"] is True             # single skill → no peers
        assert row["opponent_factor"] == 1.0

    def test_fairness_violation_flagged(self):
        # dominant skill ("passing", w=2.0) has tiny delta → peer ("shooting", w=1.0)
        # consumes more headroom → fairness_ok=False for passing row
        db = _db()
        t = _tourn(tid=10)
        p = _part(tournament=t, placement=1)
        q1 = _fluent_q(all_=[p])
        q2 = _fluent_q(count=4)
        db.query.side_effect = [q1, q2]
        # call order: passing_delta, shooting_delta, passing_advance, shooting_advance
        skv_returns = [60.5, 68.0, 60.5, 68.0]
        with patch(_PATCH_GBS, return_value={"passing": 60.0, "shooting": 60.0}), \
             patch(f"{_BASE}.get_all_skill_keys", return_value=["passing", "shooting"]), \
             patch(_PATCH_ETS, return_value={"passing": 2.0, "shooting": 1.0}), \
             patch(_PATCH_OPP, return_value=1.0), \
             patch(_PATCH_SKV, side_effect=skv_returns):
            result = get_skill_audit(db, user_id=42)
        passing_row = next(r for r in result if r["skill"] == "passing")
        assert passing_row["is_dominant"] is True
        # passing: delta=0.5, headroom=39, norm≈0.013
        # shooting: delta=8.0, headroom=39, norm≈0.205
        # 0.013+0.005 < 0.205 → fairness_ok=False
        assert passing_row["fairness_ok"] is False
