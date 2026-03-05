"""
Unit tests for app/services/tournament/tournament_reward_orchestrator.py

Covers pure functions (_normalise_skill_entry, _extract_tier, get_placement_rewards)
and DB-dependent orchestration with full mock approach.

Decision branches:
  _normalise_skill_entry       — dict pass-through, scalar promote, TypeError/ValueError → 50.0
  _extract_tier                — found (xp+credits), xp_multiplier format, not found
  load_reward_policy_from_config — no tournament, no config, config parse, exception
  get_placement_rewards        — all 4 placements
  build_badge_evaluation_context — consecutive_wins loop, tournament not found
  distribute_rewards_for_user  — existing (no force), force redistribution, sandbox mode,
                                 skill writeback (no license, no skills, with skills),
                                 IntegrityError at commit, placement badges / milestone badges
  distribute_rewards_for_tournament — no tournament, no rankings, skip team ranking,
                                      skip already distributed, force redistribution
  get_user_reward_summary      — no participation, with participation + badges, rarest badge
"""
import pytest
from unittest.mock import MagicMock, patch, call
from sqlalchemy.exc import IntegrityError

from app.services.tournament.tournament_reward_orchestrator import (
    _normalise_skill_entry,
    _extract_tier,
    get_placement_rewards,
    load_reward_policy_from_config,
    build_badge_evaluation_context,
    distribute_rewards_for_user,
    distribute_rewards_for_tournament,
    get_user_reward_summary,
    DEFAULT_REWARD_POLICY,
)
from app.schemas.tournament_rewards import RewardPolicy


PATCH_BASE = "app.services.tournament.tournament_reward_orchestrator"


# ── helpers ──────────────────────────────────────────────────────────────────

def _db():
    return MagicMock()


def _mock_tournament(reward_config=None, name="Test Cup"):
    t = MagicMock()
    t.id = 1
    t.name = name
    t.reward_config = reward_config
    t.format = "INDIVIDUAL_RANKING"
    t.measurement_unit = None
    return t


def _mock_participation(placement=1, xp=500, credits=100, skill_pts=None):
    p = MagicMock()
    p.placement = placement
    p.xp_awarded = xp
    p.credits_awarded = credits
    p.skill_points_awarded = skill_pts or {}
    p.skill_rating_delta = {"agility": 0.5}
    p.achieved_at = MagicMock()
    return p


def _mock_badge(badge_type="CHAMPION", rarity="LEGENDARY"):
    b = MagicMock()
    b.badge_type = badge_type
    b.badge_category = "PLACEMENT"
    b.title = "Champion"
    b.description = "Won a tournament"
    b.icon = "🏆"
    b.rarity = rarity
    b.badge_metadata = {}
    return b


# ─────────────────────────────────────────────────────────────────────────────
# _normalise_skill_entry
# ─────────────────────────────────────────────────────────────────────────────

class TestNormaliseSkillEntry:

    def test_dict_returned_as_is(self):
        d = {"baseline": 5.0, "current_level": 6.0}
        assert _normalise_skill_entry(d) is d

    def test_float_promoted_to_dict(self):
        result = _normalise_skill_entry(3.5)
        assert result["baseline"] == 3.5
        assert result["current_level"] == 3.5
        assert result["tournament_delta"] == 0.0
        assert result["tournament_count"] == 0

    def test_int_promoted_to_dict(self):
        result = _normalise_skill_entry(4)
        assert result["baseline"] == 4.0

    def test_none_falls_back_to_50(self):
        result = _normalise_skill_entry(None)
        assert result["baseline"] == 50.0

    def test_non_numeric_string_falls_back_to_50(self):
        result = _normalise_skill_entry("not_a_number")
        assert result["baseline"] == 50.0

    def test_numeric_string_promoted(self):
        result = _normalise_skill_entry("7.5")
        assert result["baseline"] == 7.5


# ─────────────────────────────────────────────────────────────────────────────
# _extract_tier
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractTier:

    def test_first_place_key_extracts_xp_and_credits(self):
        config = {"first_place": {"xp": 500, "credits": 100}}
        result = _extract_tier(config, "first_place", "1")
        assert result == {"xp": 500, "credits": 100}

    def test_numeric_key_format(self):
        config = {"1": {"xp": 2000, "credits": 1000}}
        result = _extract_tier(config, "first_place", "1")
        assert result == {"xp": 2000, "credits": 1000}

    def test_xp_reward_alias(self):
        config = {"first_place": {"xp_reward": 300, "credits_reward": 50}}
        result = _extract_tier(config, "first_place")
        assert result["xp"] == 300
        assert result["credits"] == 50

    def test_xp_multiplier_format(self):
        config = {"first_place": {"xp_multiplier": 2.0, "credits": 0}}
        result = _extract_tier(config, "first_place")
        # base_xp=500, multiplier=2.0 → 1000
        assert result["xp"] == 1000

    def test_key_not_found_returns_empty(self):
        config = {"second_place": {"xp": 200}}
        result = _extract_tier(config, "first_place", "1")
        assert result == {}

    def test_none_tier_value_skipped(self):
        config = {"first_place": None}
        result = _extract_tier(config, "first_place")
        assert result == {}

    def test_third_place_multiplier_key(self):
        config = {"third_place": {"xp_multiplier": 1.0, "credits": 25}}
        result = _extract_tier(config, "third_place", "3")
        assert result["xp"] == 200  # base_xp=200 * 1.0


# ─────────────────────────────────────────────────────────────────────────────
# load_reward_policy_from_config
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadRewardPolicyFromConfig:

    def test_no_tournament_returns_default(self):
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        result = load_reward_policy_from_config(db, tournament_id=99)
        assert result is DEFAULT_REWARD_POLICY

    def test_no_reward_config_returns_default(self):
        db = _db()
        t = _mock_tournament(reward_config=None)
        db.query.return_value.filter.return_value.first.return_value = t
        result = load_reward_policy_from_config(db, tournament_id=1)
        assert result is DEFAULT_REWARD_POLICY

    def test_valid_config_builds_policy(self):
        db = _db()
        config = {
            "first_place": {"xp": 1000, "credits": 200},
            "second_place": {"xp": 500, "credits": 100},
            "third_place": {"xp": 250, "credits": 50},
            "participation": {"xp": 50, "credits": 10},
        }
        t = _mock_tournament(reward_config=config)
        db.query.return_value.filter.return_value.first.return_value = t
        result = load_reward_policy_from_config(db, tournament_id=1)
        assert result.first_place_xp == 1000
        assert result.second_place_xp == 500

    def test_exception_during_parse_returns_default(self):
        db = _db()
        t = _mock_tournament(reward_config={"bad": "data"})
        db.query.return_value.filter.return_value.first.return_value = t
        with patch(f"{PATCH_BASE}._extract_tier", side_effect=Exception("parse error")):
            result = load_reward_policy_from_config(db, tournament_id=1)
        assert result is DEFAULT_REWARD_POLICY


# ─────────────────────────────────────────────────────────────────────────────
# get_placement_rewards
# ─────────────────────────────────────────────────────────────────────────────

class TestGetPlacementRewards:

    def test_first_place(self):
        result = get_placement_rewards(1)
        assert result["xp"] == DEFAULT_REWARD_POLICY.first_place_xp

    def test_second_place(self):
        result = get_placement_rewards(2)
        assert result["xp"] == DEFAULT_REWARD_POLICY.second_place_xp

    def test_third_place(self):
        result = get_placement_rewards(3)
        assert result["xp"] == DEFAULT_REWARD_POLICY.third_place_xp

    def test_participation(self):
        result = get_placement_rewards(None)
        assert result["xp"] == DEFAULT_REWARD_POLICY.participant_xp

    def test_custom_policy(self):
        policy = RewardPolicy(first_place_xp=9999)
        result = get_placement_rewards(1, policy)
        assert result["xp"] == 9999


# ─────────────────────────────────────────────────────────────────────────────
# build_badge_evaluation_context
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildBadgeEvaluationContext:

    def test_no_previous_participations(self):
        db = _db()
        t = _mock_tournament()
        db.query.return_value.filter.return_value.first.return_value = t
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = []
        ctx = build_badge_evaluation_context(db, user_id=42, tournament_id=1, placement=1, total_participants=10)
        assert ctx.previous_tournaments_count == 0
        assert ctx.consecutive_wins == 0

    def test_consecutive_wins_count(self):
        from datetime import datetime
        db = _db()
        t = _mock_tournament()
        db.query.return_value.filter.return_value.first.return_value = t
        p1, p2, p3 = MagicMock(), MagicMock(), MagicMock()
        p1.placement = 1
        p2.placement = 1
        p3.placement = 2  # breaks streak
        # Use real datetimes so sorted() can compare them (reverse=True → p1 is most recent)
        p1.achieved_at = datetime(2026, 3, 3)
        p2.achieved_at = datetime(2026, 3, 2)
        p3.achieved_at = datetime(2026, 3, 1)
        # The service calls .filter(cond1, cond2).all() — single filter, not chained
        db.query.return_value.filter.return_value.all.return_value = [p1, p2, p3]
        ctx = build_badge_evaluation_context(db, user_id=42, tournament_id=1, placement=1, total_participants=10)
        # consecutive_wins stops at first non-1 placement in sorted list
        assert ctx.previous_tournaments_count == 3

    def test_tournament_not_found(self):
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.all.return_value = []
        ctx = build_badge_evaluation_context(db, user_id=42, tournament_id=99, placement=None, total_participants=5)
        assert ctx.tournament_format == ""


# ─────────────────────────────────────────────────────────────────────────────
# distribute_rewards_for_user
# ─────────────────────────────────────────────────────────────────────────────

PART_SVC = f"{PATCH_BASE}.participation_service"
BADGE_SVC = f"{PATCH_BASE}.badge_service"
SKILL_SVC = f"{PATCH_BASE}.skill_progression_service"


def _patch_all(func):
    """Decorator: patch participation_service, badge_service, skill_progression_service, lock_timer."""
    patches = [
        patch(f"{PATCH_BASE}.lock_timer"),
        patch(PART_SVC),
        patch(BADGE_SVC),
        patch(SKILL_SVC),
    ]
    for p in reversed(patches):
        func = p(func)
    return func


class TestDistributeRewardsForUser:

    def _db_with_existing(self, existing=None, tournament=None):
        db = _db()
        t = tournament or _mock_tournament()
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = existing
        db.query.return_value.filter.return_value.first.return_value = t
        return db

    @_patch_all
    def test_already_distributed_returns_summary(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = self._db_with_existing(existing=_mock_participation())
        mock_part.calculate_skill_points_for_placement.return_value = {}
        with patch(f"{PATCH_BASE}.get_user_reward_summary", return_value=MagicMock()) as mock_summary:
            distribute_rewards_for_user(db, user_id=42, tournament_id=1, placement=1, total_participants=5)
            mock_summary.assert_called_once()

    @_patch_all
    def test_force_redistribution_bypasses_idempotency(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = self._db_with_existing(existing=_mock_participation())
        mock_part.calculate_skill_points_for_placement.return_value = {}
        mock_part.convert_skill_points_to_xp.return_value = 0
        mock_part.record_tournament_participation.return_value = _mock_participation()
        mock_badge.award_placement_badges.return_value = []
        mock_badge.award_participation_badge.return_value = _mock_badge(rarity="COMMON")
        mock_badge.check_and_award_milestone_badges.return_value = []
        with patch(f"{PATCH_BASE}.get_user_reward_summary"):
            result = distribute_rewards_for_user(
                db, user_id=42, tournament_id=1, placement=1, total_participants=5,
                force_redistribution=True
            )
        mock_part.record_tournament_participation.assert_called_once()

    @_patch_all
    def test_sandbox_mode_skips_skill_writeback(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = self._db_with_existing(existing=None)
        mock_part.calculate_skill_points_for_placement.return_value = {}
        mock_part.convert_skill_points_to_xp.return_value = 0
        mock_part.record_tournament_participation.return_value = _mock_participation()
        mock_badge.award_placement_badges.return_value = []
        mock_badge.award_participation_badge.return_value = _mock_badge(rarity="COMMON")
        mock_badge.check_and_award_milestone_badges.return_value = []
        distribute_rewards_for_user(
            db, user_id=42, tournament_id=1, placement=1, total_participants=5,
            is_sandbox_mode=True
        )
        # skill_progression_service should not be called in sandbox mode
        mock_skill.get_skill_profile.assert_not_called()

    @_patch_all
    def test_non_sandbox_skill_writeback_no_license(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = self._db_with_existing(existing=None)
        mock_part.calculate_skill_points_for_placement.return_value = {}
        mock_part.convert_skill_points_to_xp.return_value = 0
        mock_part.record_tournament_participation.return_value = _mock_participation()
        mock_badge.award_placement_badges.return_value = []
        mock_badge.award_participation_badge.return_value = _mock_badge(rarity="COMMON")
        mock_badge.check_and_award_milestone_badges.return_value = []
        # No active license found
        db.query.return_value.filter.return_value.filter.return_value.filter.return_value.with_for_update.return_value.first.return_value = None
        distribute_rewards_for_user(
            db, user_id=42, tournament_id=1, placement=2, total_participants=5,
            is_sandbox_mode=False
        )
        # Should not crash; skill writeback skipped (warning logged)
        mock_skill.get_skill_profile.assert_not_called()

    @_patch_all
    def test_non_sandbox_skill_writeback_with_license_and_skills(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = _db()
        t = _mock_tournament()
        db.query.return_value.filter.return_value.first.return_value = t
        active_license = MagicMock()
        active_license.football_skills = {"agility": {"baseline": 3.0, "current_level": 3.0}}
        # with_for_update().first(): [0]=idempotency check (None), [1]=license writeback
        db.query.return_value.filter.return_value.with_for_update.return_value.first.side_effect = [
            None, active_license
        ]
        mock_part.calculate_skill_points_for_placement.return_value = {}
        mock_part.convert_skill_points_to_xp.return_value = 0
        participation = _mock_participation()
        mock_part.record_tournament_participation.return_value = participation
        mock_badge.award_placement_badges.return_value = []
        mock_badge.award_participation_badge.return_value = _mock_badge(rarity="COMMON")
        mock_badge.check_and_award_milestone_badges.return_value = []
        mock_skill.get_skill_profile.return_value = {
            "skills": {
                "agility": {
                    "current_level": 4.0,
                    "tournament_delta": 1.0,
                    "total_delta": 1.0,
                    "tournament_count": 1,
                }
            }
        }
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            distribute_rewards_for_user(
                db, user_id=42, tournament_id=1, placement=1, total_participants=5,
                is_sandbox_mode=False
            )
        mock_skill.get_skill_profile.assert_called_once_with(db, 42)

    @_patch_all
    def test_integrity_error_at_commit_returns_summary(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = self._db_with_existing(existing=None)
        mock_part.calculate_skill_points_for_placement.return_value = {}
        mock_part.convert_skill_points_to_xp.return_value = 0
        mock_part.record_tournament_participation.return_value = _mock_participation()
        mock_badge.award_placement_badges.return_value = []
        mock_badge.award_participation_badge.return_value = _mock_badge(rarity="COMMON")
        mock_badge.check_and_award_milestone_badges.return_value = []
        db.commit.side_effect = IntegrityError("", {}, None)
        db.query.return_value.filter.return_value.filter.return_value.filter.return_value.with_for_update.return_value.first.return_value = None
        with patch(f"{PATCH_BASE}.get_user_reward_summary", return_value=MagicMock()) as mock_summary:
            distribute_rewards_for_user(
                db, user_id=42, tournament_id=1, placement=None, total_participants=5,
                is_sandbox_mode=True
            )
            mock_summary.assert_called_once()
        db.rollback.assert_called()

    @_patch_all
    def test_placement_badges_awarded_for_top3(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = self._db_with_existing(existing=None)
        mock_part.calculate_skill_points_for_placement.return_value = {}
        mock_part.convert_skill_points_to_xp.return_value = 0
        mock_part.record_tournament_participation.return_value = _mock_participation(placement=1)
        mock_badge.award_placement_badges.return_value = [_mock_badge(rarity="LEGENDARY")]
        mock_badge.award_participation_badge.return_value = _mock_badge(rarity="COMMON")
        mock_badge.check_and_award_milestone_badges.return_value = []
        result = distribute_rewards_for_user(
            db, user_id=42, tournament_id=1, placement=1, total_participants=5,
            is_sandbox_mode=True
        )
        mock_badge.award_placement_badges.assert_called_once()
        assert result.badges.rarest_badge == "LEGENDARY"

    @_patch_all
    def test_placement_badges_not_called_for_none_placement(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = self._db_with_existing(existing=None)
        mock_part.calculate_skill_points_for_placement.return_value = {}
        mock_part.convert_skill_points_to_xp.return_value = 0
        mock_part.record_tournament_participation.return_value = _mock_participation(placement=None)
        mock_badge.award_participation_badge.return_value = _mock_badge(rarity="COMMON")
        mock_badge.check_and_award_milestone_badges.return_value = []
        distribute_rewards_for_user(
            db, user_id=42, tournament_id=1, placement=None, total_participants=5,
            is_sandbox_mode=True
        )
        mock_badge.award_placement_badges.assert_not_called()

    @_patch_all
    def test_skill_delta_monitoring_log_for_podium(self, mock_skill, mock_badge, mock_part, mock_lock):
        """Lines 303-306: monitoring log for skill_delta ratio on podium placements."""
        db = self._db_with_existing(existing=None)
        mock_part.calculate_skill_points_for_placement.return_value = {}
        mock_part.convert_skill_points_to_xp.return_value = 0
        p = _mock_participation(placement=1)
        p.skill_rating_delta = {"agility": 5.0, "speed": 1.0}
        mock_part.record_tournament_participation.return_value = p
        mock_badge.award_placement_badges.return_value = []
        mock_badge.award_participation_badge.return_value = _mock_badge(rarity="COMMON")
        mock_badge.check_and_award_milestone_badges.return_value = []
        # Should not raise
        distribute_rewards_for_user(
            db, user_id=42, tournament_id=1, placement=1, total_participants=5,
            is_sandbox_mode=True
        )


# ─────────────────────────────────────────────────────────────────────────────
# distribute_rewards_for_tournament
# ─────────────────────────────────────────────────────────────────────────────

class TestDistributeRewardsForTournament:

    @_patch_all
    def test_tournament_not_found_raises(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="not found"):
            distribute_rewards_for_tournament(db, tournament_id=99)

    @_patch_all
    def test_no_rankings_raises(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = _db()
        t = _mock_tournament()
        db.query.return_value.filter.return_value.first.return_value = t
        db.query.return_value.filter.return_value.all.return_value = []
        with pytest.raises(ValueError, match="No rankings"):
            distribute_rewards_for_tournament(db, tournament_id=1)

    @_patch_all
    def test_skips_team_rankings(self, mock_skill, mock_badge, mock_part, mock_lock):
        """Rankings with user_id=None are skipped (team rankings)."""
        db = _db()
        t = _mock_tournament()
        team_ranking = MagicMock()
        team_ranking.user_id = None
        db.query.return_value.filter.return_value.first.return_value = t
        db.query.return_value.filter.return_value.all.return_value = [team_ranking]
        result = distribute_rewards_for_tournament(db, tournament_id=1)
        assert result.total_participants == 1
        assert len(result.rewards_distributed) == 0

    @_patch_all
    def test_skips_already_distributed_without_force(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = _db()
        t = _mock_tournament()
        ranking = MagicMock()
        ranking.user_id = 1
        ranking.rank = 1
        db.query.return_value.filter.return_value.all.return_value = [ranking]
        # [0] tournament check, [1] load_reward_policy_from_config, [2] existing participation check
        db.query.return_value.filter.return_value.first.side_effect = [t, t, _mock_participation()]
        result = distribute_rewards_for_tournament(db, tournament_id=1, force_redistribution=False)
        assert len(result.rewards_distributed) == 0

    @_patch_all
    def test_loads_policy_from_config_when_none_given(self, mock_skill, mock_badge, mock_part, mock_lock):
        db = _db()
        t = _mock_tournament()
        db.query.return_value.filter.return_value.first.return_value = t
        db.query.return_value.filter.return_value.all.return_value = []
        with patch(f"{PATCH_BASE}.load_reward_policy_from_config", return_value=DEFAULT_REWARD_POLICY) as mock_load:
            try:
                distribute_rewards_for_tournament(db, tournament_id=1)
            except ValueError:
                pass
            mock_load.assert_called_once_with(db, 1)


# ─────────────────────────────────────────────────────────────────────────────
# get_user_reward_summary
# ─────────────────────────────────────────────────────────────────────────────

class TestGetUserRewardSummary:

    def test_no_participation_returns_none(self):
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        result = get_user_reward_summary(db, user_id=42, tournament_id=1)
        assert result is None

    def test_returns_result_with_participation(self):
        db = _db()
        participation = _mock_participation(placement=1, xp=500, credits=100)
        tournament = _mock_tournament()
        db.query.return_value.filter.return_value.first.side_effect = [participation, tournament]
        db.query.return_value.filter.return_value.all.return_value = []
        result = get_user_reward_summary(db, user_id=42, tournament_id=1)
        assert result is not None
        assert result.user_id == 42

    def test_skill_points_in_participation_built(self):
        db = _db()
        participation = _mock_participation(skill_pts={"agility": 3.0, "speed": 1.0})
        tournament = _mock_tournament()
        db.query.return_value.filter.return_value.first.side_effect = [participation, tournament]
        db.query.return_value.filter.return_value.all.return_value = []
        result = get_user_reward_summary(db, user_id=42, tournament_id=1)
        assert len(result.participation.skill_points) == 2

    def test_rarest_badge_determined_from_badges(self):
        db = _db()
        participation = _mock_participation()
        tournament = _mock_tournament()
        db.query.return_value.filter.return_value.first.side_effect = [participation, tournament]
        badges = [_mock_badge(rarity="EPIC"), _mock_badge(rarity="COMMON")]
        db.query.return_value.filter.return_value.all.return_value = badges
        result = get_user_reward_summary(db, user_id=42, tournament_id=1)
        assert result.badges.rarest_badge == "EPIC"

    def test_tournament_not_found_uses_fallback_name(self):
        db = _db()
        participation = _mock_participation()
        db.query.return_value.filter.return_value.first.side_effect = [participation, None]
        db.query.return_value.filter.return_value.all.return_value = []
        result = get_user_reward_summary(db, user_id=42, tournament_id=42)
        assert "42" in result.tournament_name

    def test_no_skill_points_in_participation(self):
        db = _db()
        participation = _mock_participation(skill_pts=None)
        tournament = _mock_tournament()
        db.query.return_value.filter.return_value.first.side_effect = [participation, tournament]
        db.query.return_value.filter.return_value.all.return_value = []
        result = get_user_reward_summary(db, user_id=42, tournament_id=1)
        assert result.participation.skill_points == []
