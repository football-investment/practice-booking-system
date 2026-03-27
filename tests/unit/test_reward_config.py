"""
Unit tests for app/api/api_v1/endpoints/tournaments/reward_config.py

Coverage targets (97 stmts, ~17% → ≥95%):
  get_reward_config_templates()       — GET /templates
    - returns all 3 templates as model_dump'd dicts

  get_tournament_reward_config()      — GET /{id}/reward-config
    - has reward_config → returns it
    - no reward_config → returns {}

  save_tournament_reward_config()     — POST /{id}/reward-config
    - 403: not admin
    - 400: no enabled skills
    - happy path: new config created (no existing TournamentRewardConfig)
    - happy path: existing config updated (no db.add)
    - 400: DB exception during save → rollback
    - template_name=None → policy_name = "Custom"

  update_tournament_reward_config()   — PUT /{id}/reward-config
    - delegates to save (alias verification)

  delete_tournament_reward_config()   — DELETE /{id}/reward-config
    - 403: non-admin  (uses string comparison role != "ADMIN")
    - happy path: config reset to None + commit

  preview_tournament_rewards()        — GET /{id}/reward-config/preview
    - 404: tournament has no reward_config
    - 400: TournamentRewardConfig parse error
    - happy path: all 5 placement tiers → totals calculated
    - happy path: partial tiers (only 1st place) → others contribute 0

NOTE: delete_tournament_reward_config now uses UserRole enum comparison (fixed in Issue #11).
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.tournaments.reward_config import (
    get_reward_config_templates,
    get_tournament_reward_config,
    save_tournament_reward_config,
    update_tournament_reward_config,
    delete_tournament_reward_config,
    preview_tournament_rewards,
)
from app.schemas.reward_config import (
    TournamentRewardConfig,
    SkillMappingConfig,
    PlacementRewardConfig,
    BadgeConfig,
)
from app.models.user import UserRole

_RC   = "app.api.api_v1.endpoints.tournaments.reward_config"
_REPO = f"{_RC}.TournamentRepository"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _admin():
    u = MagicMock()
    u.role = UserRole.ADMIN
    u.id = 42
    return u


def _non_admin():
    u = MagicMock()
    u.role = UserRole.INSTRUCTOR
    u.id = 42
    return u


def _tournament(has_config=True):
    t = MagicMock()
    t.id = 1
    t.name = "Test Tournament"
    t.reward_config = {"template_name": "Standard"} if has_config else None
    return t


def _valid_config():
    """Minimal TournamentRewardConfig with 1 enabled skill."""
    return TournamentRewardConfig(
        skill_mappings=[
            SkillMappingConfig(skill="speed", weight=1.5, category="PHYSICAL", enabled=True)
        ],
        first_place=PlacementRewardConfig(
            badges=[BadgeConfig(badge_type="CHAMPION", title="Champion", enabled=True)],
            credits=500,
            xp_multiplier=1.5,
        ),
        participation=PlacementRewardConfig(
            badges=[BadgeConfig(badge_type="DEBUT", title="Debut", enabled=True)],
            credits=50,
            xp_multiplier=1.0,
        ),
        template_name="Test",
    )


def _invalid_config():
    """Config with no enabled skills → validate_enabled_skills fails."""
    return TournamentRewardConfig(
        skill_mappings=[
            SkillMappingConfig(skill="speed", weight=1.5, category="PHYSICAL", enabled=False)
        ]
    )


def _q(first=None, all_=None, count_=0):
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = first
    q.count.return_value = count_
    q.all.return_value = all_ or []
    return q


def _db_seq(*qs):
    db = MagicMock()
    db.query.side_effect = list(qs) + [MagicMock()] * 4
    return db


# ── get_reward_config_templates ─────────────────────────────────────────────────

class TestGetRewardConfigTemplates:

    def test_returns_all_three_templates_as_dicts(self):
        result = get_reward_config_templates(current_user=_admin())
        assert "STANDARD" in result
        assert "CHAMPIONSHIP" in result
        assert "FRIENDLY" in result
        # Each is serialised by model_dump(mode="json")
        assert isinstance(result["STANDARD"], dict)
        assert "skill_mappings" in result["STANDARD"]
        assert "first_place" in result["STANDARD"]


# ── get_tournament_reward_config ────────────────────────────────────────────────

class TestGetTournamentRewardConfig:

    def test_returns_existing_reward_config(self):
        t = _tournament(has_config=True)
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            result = get_tournament_reward_config(1, db=MagicMock(), current_user=_admin())
        assert result == t.reward_config

    def test_returns_empty_dict_when_no_config(self):
        t = _tournament(has_config=False)
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            result = get_tournament_reward_config(1, db=MagicMock(), current_user=_admin())
        assert result == {}


# ── save_tournament_reward_config ───────────────────────────────────────────────

class TestSaveTournamentRewardConfig:

    def test_403_non_admin(self):
        with pytest.raises(HTTPException) as exc:
            save_tournament_reward_config(
                1, _valid_config(), db=MagicMock(), current_user=_non_admin()
            )
        assert exc.value.status_code == 403
        assert "admin" in exc.value.detail.lower()

    def test_no_enabled_skills_saves_successfully(self):
        # Skill validation was removed — game preset (mandatory) drives skill_weights.
        # Config with disabled skills is now accepted; no 400 is raised.
        t = _tournament()
        t.reward_config = None
        db = _db_seq(_q(first=None))
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            # Should not raise — no 400 guard for disabled skills anymore
            save_tournament_reward_config(
                1, _invalid_config(), db=db, current_user=_admin()
            )

    def test_creates_new_config_when_none_exists(self):
        t = _tournament()
        t.reward_config = {"saved": True}
        db = _db_seq(_q(first=None))    # no existing TournamentRewardConfig
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            result = save_tournament_reward_config(1, _valid_config(), db=db, current_user=_admin())
        db.add.assert_called_once()
        db.commit.assert_called_once()
        assert result == {"saved": True}

    def test_updates_existing_config_without_add(self):
        t = _tournament()
        t.reward_config = {"updated": True}
        existing = MagicMock()
        db = _db_seq(_q(first=existing))    # existing found
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            result = save_tournament_reward_config(1, _valid_config(), db=db, current_user=_admin())
        db.add.assert_not_called()          # update path, not create
        db.commit.assert_called_once()
        assert existing.reward_config is not None

    def test_400_on_db_exception_triggers_rollback(self):
        t = _tournament()
        db = MagicMock()
        db.query.side_effect = Exception("DB boom")
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            with pytest.raises(HTTPException) as exc:
                save_tournament_reward_config(1, _valid_config(), db=db, current_user=_admin())
        assert exc.value.status_code == 400
        db.rollback.assert_called_once()

    def test_template_name_none_defaults_to_custom(self):
        """When template_name is None, the new config's policy_name is 'Custom'."""
        t = _tournament()
        t.reward_config = {}
        db = _db_seq(_q(first=None))
        cfg = _valid_config()
        cfg.template_name = None
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            save_tournament_reward_config(1, cfg, db=db, current_user=_admin())
        added_obj = db.add.call_args[0][0]
        assert added_obj.reward_policy_name == "Custom"


# ── update_tournament_reward_config ─────────────────────────────────────────────

class TestUpdateTournamentRewardConfig:

    def test_delegates_to_save(self):
        t = _tournament()
        t.reward_config = {"delegated": True}
        db = _db_seq(_q(first=None))
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            result = update_tournament_reward_config(
                1, _valid_config(), db=db, current_user=_admin()
            )
        assert result == {"delegated": True}


# ── delete_tournament_reward_config ─────────────────────────────────────────────

class TestDeleteTournamentRewardConfig:

    def test_403_non_admin(self):
        with pytest.raises(HTTPException) as exc:
            delete_tournament_reward_config(
                1, db=MagicMock(), current_user=_non_admin()
            )
        assert exc.value.status_code == 403

    def test_happy_path_resets_config_and_commits(self):
        t = _tournament(has_config=True)
        db = MagicMock()
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            result = delete_tournament_reward_config(1, db=db, current_user=_admin())
        assert t.reward_config_obj is None
        db.commit.assert_called_once()
        assert "deleted" in result["message"].lower()


# ── preview_tournament_rewards ──────────────────────────────────────────────────

class TestPreviewTournamentRewards:

    def test_404_when_no_reward_config(self):
        t = _tournament(has_config=False)
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            with pytest.raises(HTTPException) as exc:
                preview_tournament_rewards(1, db=MagicMock(), current_user=_admin())
        assert exc.value.status_code == 404

    def test_400_when_config_parse_fails(self):
        t = _tournament(has_config=True)    # reward_config is truthy
        with patch(_REPO) as MockRepo, \
             patch(f"{_RC}.TournamentRewardConfig") as MockConfig:
            MockRepo.return_value.get_or_404.return_value = t
            MockConfig.side_effect = ValueError("parse error")
            with pytest.raises(HTTPException) as exc:
                preview_tournament_rewards(1, db=MagicMock(), current_user=_admin())
        assert exc.value.status_code == 400

    def test_all_five_tiers_contribute_to_totals(self):
        cfg = TournamentRewardConfig(
            skill_mappings=[
                SkillMappingConfig(skill="speed", weight=1.0, category="PHYSICAL", enabled=True)
            ],
            first_place=PlacementRewardConfig(
                badges=[BadgeConfig(badge_type="CHAMPION", title="Champion", enabled=True)],
                credits=500,
                xp_multiplier=1.5,
            ),
            second_place=PlacementRewardConfig(badges=[], credits=300, xp_multiplier=1.3),
            third_place=PlacementRewardConfig(badges=[], credits=200, xp_multiplier=1.2),
            top_25_percent=PlacementRewardConfig(badges=[], credits=100, xp_multiplier=1.1),
            participation=PlacementRewardConfig(
                badges=[BadgeConfig(badge_type="DEBUT", title="Debut", enabled=True)],
                credits=50,
                xp_multiplier=1.0,
            ),
        )
        t = _tournament()
        t.reward_config = cfg.model_dump(mode="json")
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            result = preview_tournament_rewards(1, db=MagicMock(), current_user=_admin())
        # 1st: 1 badge + 500cr; participation: 8 badges + 8*50=400cr; 2nd+3rd: 0 badges
        assert result["total_badges"] >= 1
        assert result["total_credits"] >= 500
        assert result["tournament_id"] == 1
        assert result["tournament_name"] == t.name
        assert result["estimated_participants"] == 8

    def test_partial_tiers_only_first_place(self):
        """Only first_place set; second/third/top25/participation all None."""
        cfg = TournamentRewardConfig(
            skill_mappings=[
                SkillMappingConfig(skill="speed", weight=1.0, category="PHYSICAL", enabled=True)
            ],
            first_place=PlacementRewardConfig(
                badges=[BadgeConfig(badge_type="CHAMPION", title="Champion", enabled=True)],
                credits=500,
                xp_multiplier=1.5,
            ),
            # other tiers default to None
        )
        t = _tournament()
        t.reward_config = cfg.model_dump(mode="json")
        with patch(_REPO) as MockRepo:
            MockRepo.return_value.get_or_404.return_value = t
            result = preview_tournament_rewards(1, db=MagicMock(), current_user=_admin())
        assert result["total_badges"] == 1
        assert result["total_credits"] == 500
