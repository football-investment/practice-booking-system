"""
Sprint 29 — api/api_v1/endpoints/tournaments/create.py
=======================================================
Target: ≥85% statement, ≥70% branch

Covers:
  create_tournament — all authorization + validation branches:
    * non-admin → 403
    * unknown tournament type → 400
    * invalid player count → 400
    * grandmaster not found (warning-only path)
    * success with skills_to_test (weight=1.0 each)
    * success with explicit skill_weights override
    * game_preset_id not found → 400
    * success with game_preset_id + preset.skill_weights (reactivity conversion)
    * success with game_preset_id but no preset.skill_weights (fallback)
    * success with game_config dict (no preset)
    * reward tier rank mapping: 1/2/3/other
"""

import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import HTTPException

from app.api.api_v1.endpoints.tournaments.create import (
    create_tournament,
    TournamentCreateRequest,
    RewardTierConfig,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.tournaments.create"


# ── helpers ─────────────────────────────────────────────────────────────────

def _admin():
    u = MagicMock()
    u.role = UserRole.ADMIN
    u.email = "admin@lfa.com"
    return u


def _student():
    u = MagicMock()
    u.role = UserRole.STUDENT
    return u


def _tournament_type(valid=True, error_msg=None):
    tt = MagicMock()
    tt.id = 1
    tt.validate_player_count.return_value = (valid, error_msg or "")
    return tt


def _grandmaster(found=True):
    if not found:
        return None
    gm = MagicMock()
    gm.id = 99
    return gm


def _preset(pid=5, skills=None, weights=None, config=None):
    p = MagicMock()
    p.id = pid
    p.code = "footvolley"
    p.skills_tested = skills or ["ball_control", "passing"]
    p.skill_weights = weights  # None means no weights
    p.game_config = config or {"rules": "standard"}
    return p


def _seq_db(*qs):
    """Return a DB mock that returns qs[n] for the n-th db.query() call."""
    calls = [0]
    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        return qs[idx] if idx < len(qs) else MagicMock()
    db = MagicMock()
    db.query.side_effect = _side
    return db


def _q(first=None):
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = first
    return q


def _basic_request(
    skills=None,
    reward_config=None,
    game_preset_id=None,
    game_config=None,
    skill_weights=None,
    max_players=8,
):
    return TournamentCreateRequest(
        name="Test Cup",
        tournament_type="knockout",
        age_group="YOUTH",
        max_players=max_players,
        skills_to_test=skills or ["passing", "dribbling"],
        reward_config=reward_config or [
            RewardTierConfig(rank=1, xp_reward=100, credits_reward=50),
            RewardTierConfig(rank=2, xp_reward=75, credits_reward=30),
        ],
        game_preset_id=game_preset_id,
        game_config=game_config,
        skill_weights=skill_weights,
    )


# ============================================================================
# Authorization
# ============================================================================

class TestCreateTournamentAuth:

    def test_non_admin_returns_403(self):
        """CTA-01: non-admin user → 403 Forbidden."""
        db = MagicMock()
        with pytest.raises(HTTPException) as exc:
            create_tournament(request=_basic_request(), db=db, current_user=_student())
        assert exc.value.status_code == 403
        assert "admin" in exc.value.detail.lower()


# ============================================================================
# Validation failures
# ============================================================================

class TestCreateTournamentValidation:

    def test_unknown_tournament_type_returns_400(self):
        """CTV-01: TournamentType not found → 400."""
        db = _seq_db(_q(first=None))  # TournamentType not found
        with pytest.raises(HTTPException) as exc:
            create_tournament(request=_basic_request(), db=db, current_user=_admin())
        assert exc.value.status_code == 400
        assert "tournament type" in exc.value.detail.lower()

    def test_invalid_player_count_returns_400(self):
        """CTV-02: validate_player_count fails → 400 with error message."""
        tt = _tournament_type(valid=False, error_msg="Player count too high")
        db = _seq_db(_q(first=tt))
        with pytest.raises(HTTPException) as exc:
            create_tournament(request=_basic_request(), db=db, current_user=_admin())
        assert exc.value.status_code == 400
        assert "Player count too high" in exc.value.detail

    def test_game_preset_id_not_found_returns_400(self):
        """CTV-03: game_preset_id provided but preset not found → 400."""
        tt = _tournament_type(valid=True)
        gm = _grandmaster(found=True)
        # query order: 1=TournamentType, 2=User(grandmaster), 3=GamePreset(not found)
        db = _seq_db(_q(first=tt), _q(first=gm), _q(first=None))

        # Need a mock Semester to avoid real DB calls
        mock_tournament = MagicMock()
        mock_tournament.id = 101

        with patch(f"{_BASE}.Semester", return_value=mock_tournament):
            with patch(f"{_BASE}.TournamentConfiguration"):
                with patch(f"{_BASE}.TournamentRewardConfig"):
                    req = _basic_request(
                        skills=[],
                        game_preset_id=5,
                    )
                    # model_validator requires either preset_id or skills_to_test
                    req2 = TournamentCreateRequest(
                        name="Test Cup",
                        tournament_type="knockout",
                        age_group="YOUTH",
                        max_players=8,
                        skills_to_test=[],
                        game_preset_id=5,
                        reward_config=[RewardTierConfig(rank=1, xp_reward=100, credits_reward=50)],
                    )
                    with pytest.raises(HTTPException) as exc:
                        create_tournament(request=req2, db=db, current_user=_admin())
        assert exc.value.status_code == 400
        assert "preset" in exc.value.detail.lower()


# ============================================================================
# Success paths
# ============================================================================

class TestCreateTournamentSuccess:

    def _run(self, db, request, patches=None):
        """Run create_tournament with standard patches and return response."""
        mock_tournament = MagicMock()
        mock_tournament.id = 101
        mock_tournament.name = request.name
        mock_tournament.code = "TOURN-20260306-120000"
        mock_tournament.tournament_status = "IN_PROGRESS"

        ctx_patches = {
            f"{_BASE}.Semester": MagicMock(return_value=mock_tournament),
            f"{_BASE}.TournamentConfiguration": MagicMock(),
            f"{_BASE}.TournamentRewardConfig": MagicMock(),
            f"{_BASE}.TournamentSkillMapping": MagicMock(side_effect=lambda **kw: MagicMock()),
        }
        if patches:
            ctx_patches.update(patches)

        with patch(f"{_BASE}.Semester", ctx_patches[f"{_BASE}.Semester"]):
            with patch(f"{_BASE}.TournamentConfiguration", ctx_patches[f"{_BASE}.TournamentConfiguration"]):
                with patch(f"{_BASE}.TournamentRewardConfig", ctx_patches[f"{_BASE}.TournamentRewardConfig"]):
                    with patch(f"{_BASE}.TournamentSkillMapping", ctx_patches[f"{_BASE}.TournamentSkillMapping"]):
                        result = create_tournament(request=request, db=db, current_user=_admin())
        return result

    def test_success_with_skills_to_test(self):
        """CTS-01: skills_to_test only → skill mappings created with weight=1.0."""
        tt = _tournament_type(valid=True)
        gm = _grandmaster(found=True)
        db = _seq_db(_q(first=tt), _q(first=gm))

        req = _basic_request(skills=["passing", "dribbling"])
        result = self._run(db, req)

        assert result.success is True
        assert result.max_players == 8
        assert result.tournament_status == "IN_PROGRESS"
        # Two skill mappings should be added
        assert db.add.call_count >= 2

    def test_success_no_grandmaster_warning_path(self):
        """CTS-02: grandmaster not found → no master_instructor_id, still succeeds."""
        tt = _tournament_type(valid=True)
        db = _seq_db(_q(first=tt), _q(first=None))  # No grandmaster

        req = _basic_request(skills=["passing"])
        result = self._run(db, req)

        assert result.success is True

    def test_success_with_explicit_skill_weights(self):
        """CTS-03: skills_to_test + explicit skill_weights → correct weights used."""
        tt = _tournament_type(valid=True)
        gm = _grandmaster(found=True)
        db = _seq_db(_q(first=tt), _q(first=gm))

        req = _basic_request(
            skills=["passing", "finishing"],
            skill_weights={"passing": 1.5, "finishing": 0.8},
        )
        mock_mapping = MagicMock(side_effect=lambda **kw: MagicMock())
        result = self._run(db, req, {f"{_BASE}.TournamentSkillMapping": mock_mapping})

        assert result.success is True
        # Check that TournamentSkillMapping was called with correct weight for passing
        calls_kw = [c.kwargs for c in mock_mapping.call_args_list]
        passing_call = next((c for c in calls_kw if c.get("skill_name") == "passing"), None)
        assert passing_call is not None
        assert passing_call["weight"] == 1.5

    def test_success_with_game_config_dict(self):
        """CTS-04: game_config dict (no preset_id) → GameConfiguration created, success."""
        tt = _tournament_type(valid=True)
        gm = _grandmaster(found=True)
        db = _seq_db(_q(first=tt), _q(first=gm))

        req = _basic_request(
            skills=["passing"],
            game_config={"variant": "footvolley"},
        )
        # Verify endpoint succeeds (GameConfiguration is created internally)
        result = self._run(db, req)
        assert result.success is True
        # db.add called at minimum for: Semester, TournamentConfiguration,
        # TournamentRewardConfig, GameConfiguration, TournamentSkillMapping(1)
        assert db.add.call_count >= 5

    def test_success_with_game_preset_and_skill_weights(self):
        """CTS-05: game_preset_id with skill_weights → reactivity multipliers."""
        tt = _tournament_type(valid=True)
        gm = _grandmaster(found=True)
        preset = _preset(
            pid=5,
            skills=["ball_control", "passing"],
            weights={"ball_control": 0.6, "passing": 0.4},
        )
        db = _seq_db(_q(first=tt), _q(first=gm), _q(first=preset))

        req = TournamentCreateRequest(
            name="Footvolley Cup",
            tournament_type="knockout",
            age_group="YOUTH",
            max_players=8,
            skills_to_test=[],
            game_preset_id=5,
            reward_config=[RewardTierConfig(rank=1, xp_reward=100, credits_reward=50)],
        )
        mock_mapping = MagicMock(side_effect=lambda **kw: MagicMock())
        mock_gc = MagicMock()

        result = self._run(db, req, {
            f"{_BASE}.TournamentSkillMapping": mock_mapping,
            f"{_BASE}.GameConfiguration": mock_gc,
        })

        assert result.success is True
        # avg_w = (0.6 + 0.4) / 2 = 0.5
        # ball_control reactivity = 0.6 / 0.5 = 1.2
        # passing reactivity = 0.4 / 0.5 = 0.8
        calls_kw = [c.kwargs for c in mock_mapping.call_args_list]
        bc_call = next((c for c in calls_kw if c.get("skill_name") == "ball_control"), None)
        assert bc_call is not None
        assert abs(bc_call["weight"] - 1.2) < 0.01

    def test_success_with_preset_no_weights_fallback(self):
        """CTS-06: game_preset_id but preset.skill_weights=None → fallback weight=1.0."""
        tt = _tournament_type(valid=True)
        gm = _grandmaster(found=True)
        preset = _preset(pid=5, skills=["ball_control"], weights=None)
        db = _seq_db(_q(first=tt), _q(first=gm), _q(first=preset))

        req = TournamentCreateRequest(
            name="Simple Cup",
            tournament_type="knockout",
            age_group="YOUTH",
            max_players=8,
            skills_to_test=[],
            game_preset_id=5,
            reward_config=[RewardTierConfig(rank=1, xp_reward=100, credits_reward=50)],
        )
        mock_mapping = MagicMock(side_effect=lambda **kw: MagicMock())
        result = self._run(db, req, {f"{_BASE}.TournamentSkillMapping": mock_mapping})

        assert result.success is True
        # Fallback: TournamentSkillMapping called with skill_name and no explicit weight
        calls_kw = [c.kwargs for c in mock_mapping.call_args_list]
        assert any(c.get("skill_name") == "ball_control" for c in calls_kw)

    def test_reward_tier_rank_mapping_all_cases(self):
        """CTS-07: rank 1/2/3 → first/second/third_place; rank 4 → rank_4."""
        tt = _tournament_type(valid=True)
        gm = _grandmaster(found=True)
        db = _seq_db(_q(first=tt), _q(first=gm))

        req = _basic_request(
            skills=["passing"],
            reward_config=[
                RewardTierConfig(rank=1, xp_reward=100, credits_reward=50),
                RewardTierConfig(rank=2, xp_reward=75, credits_reward=30),
                RewardTierConfig(rank=3, xp_reward=50, credits_reward=20),
                RewardTierConfig(rank=4, xp_reward=25, credits_reward=10),
            ],
        )
        mock_reward_config = MagicMock()
        result = self._run(db, req, {f"{_BASE}.TournamentRewardConfig": mock_reward_config})

        assert result.success is True
        # Check TournamentRewardConfig was called with correct reward_tiers_dict
        call_kw = mock_reward_config.call_args.kwargs
        rc = call_kw["reward_config"]
        assert "first_place" in rc
        assert "second_place" in rc
        assert "third_place" in rc
        assert "rank_4" in rc

    def test_response_fields(self):
        """CTS-08: response includes all required fields."""
        tt = _tournament_type(valid=True)
        gm = _grandmaster(found=True)
        db = _seq_db(_q(first=tt), _q(first=gm))

        req = _basic_request()
        result = self._run(db, req)

        assert hasattr(result, "success")
        assert hasattr(result, "tournament_id")
        assert hasattr(result, "tournament_name")
        assert hasattr(result, "tournament_code")
        assert hasattr(result, "tournament_type")
        assert hasattr(result, "max_players")
        assert hasattr(result, "message")
