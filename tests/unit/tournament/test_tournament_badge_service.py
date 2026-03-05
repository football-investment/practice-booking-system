"""Sprint J — tournament_badge_service unit tests.

Covers all 6 public functions with mandatory happy + unhappy paths.

Branch requirements:
- award_badge: unknown type, fallback name, idempotency, new badge,
  IntegrityError→rollback→re-query, metadata count, no metadata
- award_placement_badges: placement 1/2/3/4, V2 reward_config path,
  disabled badge, existing badge duplicate prevention, parse error fallback
- award_participation_badge: first tournament (scalar=0), subsequent (scalar>0)
- check_and_award_milestone_badges: <5, exactly 5, veteran exists, ≥10 legend,
  triple crown (3 champions), triple crown already exists
- get_player_badges: no filter, tournament_id filter, integrity error, semester_id None
- get_player_badge_showcase: empty, rarity sort, category grouping, date sort

TestRewardPipelineSanity: distribute_rewards_for_user with badge_service NOT mocked.
Participation service mocked; DB mock handles all badge/semester queries.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call
from sqlalchemy.exc import IntegrityError

from app.services.tournament import tournament_badge_service as badge_service
from app.services.tournament import tournament_reward_orchestrator as orchestrator
from app.models.tournament_achievement import (
    TournamentBadge,
    TournamentBadgeType,
    TournamentBadgeCategory,
    TournamentBadgeRarity,
    TournamentParticipation,
)
from app.models.semester import Semester


# ─── DB Helpers ────────────────────────────────────────────────────────────────

def _db_simple():
    """Universal mock: all filter chains return None/0/[], savepoint works."""
    db = MagicMock()
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.with_for_update.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.first.return_value = None
    q.scalar.return_value = 0
    q.all.return_value = []
    db.begin_nested.return_value = MagicMock()
    return db


def _db_split(
    tournament_mock=None,
    badge_first=None,
    badge_scalar=0,
    badge_all=None,
    badge_wfu_first=None,  # what with_for_update().first() returns (duplicate check)
):
    """
    DB mock that discriminates Semester vs TournamentBadge/func.count queries.
    - tournament_mock: what Semester.first() returns
    - badge_first: what TournamentBadge.filter().first() returns (or side_effect list)
    - badge_scalar: what .scalar() returns
    - badge_all: what .all() returns
    - badge_wfu_first: what .filter().with_for_update().first() returns (award_badge dup check)
    """
    db = MagicMock()

    semester_q = MagicMock()
    semester_q.filter.return_value = semester_q
    semester_q.first.return_value = tournament_mock

    badge_q = MagicMock()
    badge_q.filter.return_value = badge_q
    badge_q.options.return_value = badge_q
    badge_q.order_by.return_value = badge_q
    badge_q.limit.return_value = badge_q

    # Separate chain for with_for_update (duplicate check in award_badge)
    wfu_q = MagicMock()
    wfu_q.first.return_value = badge_wfu_first  # None by default → create new badge
    badge_q.with_for_update.return_value = wfu_q

    if isinstance(badge_first, list):
        badge_q.first.side_effect = badge_first
    else:
        badge_q.first.return_value = badge_first

    badge_q.scalar.return_value = badge_scalar
    badge_q.all.return_value = badge_all or []

    def _qse(model):
        if model is Semester:
            return semester_q
        return badge_q

    db.query.side_effect = _qse
    db.begin_nested.return_value = MagicMock()
    return db


def _mock_badge(
    badge_type=TournamentBadgeType.CHAMPION,
    user_id=1,
    tournament_id=10,
    rarity=TournamentBadgeRarity.EPIC,
    category=TournamentBadgeCategory.PLACEMENT,
    semester_id_val=10,
    earned_at=None,
    has_tournament=True,
):
    b = MagicMock(spec=TournamentBadge)
    b.id = 1
    b.user_id = user_id
    b.semester_id = semester_id_val
    b.badge_type = badge_type
    b.badge_category = category
    b.title = "Mock Badge"
    b.description = "Mock description"
    b.icon = "🏆"
    b.rarity = rarity
    b.badge_metadata = {}
    b.tournament = MagicMock() if has_tournament else None
    b.earned_at = earned_at or datetime(2026, 3, 1, tzinfo=timezone.utc)
    b.to_dict.return_value = {"id": b.id, "badge_type": badge_type, "rarity": rarity}
    return b


# ─── TestAwardBadge ────────────────────────────────────────────────────────────

class TestAwardBadge:
    """Tests for award_badge() — core badge creation + duplicate prevention."""

    def test_unknown_type_raises_value_error(self):
        db = _db_simple()
        with pytest.raises(ValueError, match="Unknown badge type"):
            badge_service.award_badge(db, user_id=1, tournament_id=10, badge_type="DOES_NOT_EXIST")

    def test_tournament_not_found_uses_fallback_name(self):
        db = _db_simple()
        # Semester query returns None → fallback: "Tournament #10"
        badge_service.award_badge(db, 1, 10, TournamentBadgeType.CHAMPION)

        db.add.assert_called_once()
        created = db.add.call_args[0][0]
        assert "Tournament #10" in created.description

    def test_tournament_found_uses_real_name(self):
        tournament = MagicMock()
        tournament.name = "UEFA Cup"
        db = _db_split(tournament_mock=tournament)

        badge_service.award_badge(db, 1, 10, TournamentBadgeType.CHAMPION)

        created = db.add.call_args[0][0]
        assert "UEFA Cup" in created.description

    def test_existing_badge_returns_without_db_add(self):
        # Use _db_split so Semester query (first() → None) and badge dup check
        # (with_for_update().first() → existing) use separate mock chains.
        existing = _mock_badge()
        db = _db_split(tournament_mock=None, badge_wfu_first=existing)

        result = badge_service.award_badge(db, 1, 10, TournamentBadgeType.CHAMPION)

        assert result is existing
        db.add.assert_not_called()
        db.begin_nested.assert_not_called()

    def test_new_badge_creates_and_commits_savepoint(self):
        db = _db_simple()
        sp = MagicMock()
        db.begin_nested.return_value = sp

        result = badge_service.award_badge(db, 1, 10, TournamentBadgeType.RUNNER_UP)

        db.add.assert_called_once()
        db.begin_nested.assert_called_once()
        sp.commit.assert_called_once()
        assert isinstance(result, TournamentBadge)

    def test_integrity_error_rollbacks_and_returns_existing(self):
        existing = _mock_badge()
        sp = MagicMock()
        sp.commit.side_effect = IntegrityError("stmt", "params", Exception("orig"))

        # badge_first=existing: re-query after rollback returns existing
        # badge_wfu_first=None: initial duplicate check finds nothing → proceeds to create
        db = _db_split(tournament_mock=None, badge_first=existing, badge_wfu_first=None)
        db.begin_nested.return_value = sp

        result = badge_service.award_badge(db, 1, 10, TournamentBadgeType.CHAMPION)

        sp.rollback.assert_called_once()
        assert result is existing

    def test_metadata_count_in_description(self):
        db = _db_simple()
        badge_service.award_badge(
            db, 1, 10, TournamentBadgeType.TOURNAMENT_VETERAN, metadata={"count": 7}
        )
        created = db.add.call_args[0][0]
        assert "7" in created.description

    def test_no_metadata_uses_empty_string_for_count(self):
        """metadata=None → count="" → no error in format()."""
        db = _db_simple()
        badge_service.award_badge(
            db, 1, 10, TournamentBadgeType.TOURNAMENT_VETERAN, metadata=None
        )
        created = db.add.call_args[0][0]
        assert "Competed in" in created.description  # template filled without raising

    def test_badge_attributes_set_correctly(self):
        db = _db_simple()
        badge_service.award_badge(db, 1, 10, TournamentBadgeType.CHAMPION)
        created = db.add.call_args[0][0]

        assert created.user_id == 1
        assert created.semester_id == 10
        assert created.badge_type == TournamentBadgeType.CHAMPION
        assert created.badge_category == TournamentBadgeCategory.PLACEMENT
        assert created.icon == "🥇"
        assert created.rarity == TournamentBadgeRarity.EPIC


# ─── TestAwardPlacementBadges ──────────────────────────────────────────────────

class TestAwardPlacementBadges:
    """Tests for award_placement_badges() — V2 config path + hardcoded fallback."""

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_placement_4_awards_no_badges(self, mock_award):
        db = _db_simple()
        result = badge_service.award_placement_badges(db, 1, 10, placement=4, total_participants=10)
        assert result == []
        mock_award.assert_not_called()

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_placement_1_hardcoded_awards_champion_and_podium(self, mock_award):
        db = _db_simple()  # tournament.first() → None → no reward_config → hardcoded
        mock_award.return_value = MagicMock()

        badge_service.award_placement_badges(db, 1, 10, placement=1, total_participants=10)

        called_types = [c.args[3] for c in mock_award.call_args_list]
        assert TournamentBadgeType.CHAMPION in called_types
        assert TournamentBadgeType.PODIUM_FINISH in called_types

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_placement_2_hardcoded_awards_runner_up_and_podium(self, mock_award):
        db = _db_simple()
        mock_award.return_value = MagicMock()

        badge_service.award_placement_badges(db, 1, 10, placement=2, total_participants=10)

        called_types = [c.args[3] for c in mock_award.call_args_list]
        assert TournamentBadgeType.RUNNER_UP in called_types
        assert TournamentBadgeType.PODIUM_FINISH in called_types

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_placement_3_hardcoded_awards_third_and_podium(self, mock_award):
        db = _db_simple()
        mock_award.return_value = MagicMock()

        badge_service.award_placement_badges(db, 1, 10, placement=3, total_participants=10)

        called_types = [c.args[3] for c in mock_award.call_args_list]
        assert TournamentBadgeType.THIRD_PLACE in called_types
        assert TournamentBadgeType.PODIUM_FINISH in called_types

    def test_v2_path_awards_badge_from_reward_config(self):
        reward_config = {
            "first_place": {
                "badges": [{
                    "badge_type": TournamentBadgeType.CHAMPION,
                    "icon": "🥇",
                    "title": "V2 Champion",
                    "description": "Won {tournament_name}",
                    "rarity": "EPIC",
                    "enabled": True,
                }]
            }
        }
        tournament = MagicMock()
        tournament.name = "Test Cup"
        tournament.reward_config = reward_config
        db = _db_split(tournament_mock=tournament)

        result = badge_service.award_placement_badges(db, 1, 10, placement=1, total_participants=10)

        assert len(result) == 1
        assert result[0].badge_type == TournamentBadgeType.CHAMPION
        db.add.assert_called_once()

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_v2_disabled_badge_falls_back_to_hardcoded(self, mock_award):
        """
        All V2 badges disabled → badge_configs=[] → hardcoded fallback runs.
        Disabled V2 badge does NOT block rewards — hardcoded path takes over.
        """
        mock_award.return_value = MagicMock()
        reward_config = {
            "first_place": {
                "badges": [{
                    "badge_type": TournamentBadgeType.CHAMPION,
                    "icon": "🥇",
                    "title": "Champion",
                    "description": "Won {tournament_name}",
                    "rarity": "EPIC",
                    "enabled": False,  # disabled → badge_configs stays empty
                }]
            }
        }
        tournament = MagicMock()
        tournament.reward_config = reward_config
        db = _db_split(tournament_mock=tournament)

        badge_service.award_placement_badges(db, 1, 10, placement=1, total_participants=10)

        # Falls to hardcoded: CHAMPION + PODIUM_FINISH
        called_types = [c.args[3] for c in mock_award.call_args_list]
        assert TournamentBadgeType.CHAMPION in called_types
        assert TournamentBadgeType.PODIUM_FINISH in called_types

    def test_v2_existing_badge_prevents_duplicate(self):
        reward_config = {
            "first_place": {
                "badges": [{
                    "badge_type": TournamentBadgeType.CHAMPION,
                    "icon": "🥇",
                    "title": "Champion",
                    "description": "Won {tournament_name}",
                    "rarity": "EPIC",
                    "enabled": True,
                }]
            }
        }
        existing = _mock_badge()
        tournament = MagicMock()
        tournament.name = "Test Cup"
        tournament.reward_config = reward_config

        db = _db_split(tournament_mock=tournament, badge_first=existing)

        result = badge_service.award_placement_badges(db, 1, 10, placement=1, total_participants=10)

        assert result == []
        db.add.assert_not_called()

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_v2_parse_error_falls_back_to_hardcoded(self, mock_award):
        """reward_config that cannot be ** unpacked → TypeError → fallback."""
        mock_award.return_value = MagicMock()

        tournament = MagicMock()
        tournament.name = "Error Cup"
        tournament.reward_config = "not_a_dict"  # ** unpacking will raise TypeError
        db = _db_split(tournament_mock=tournament)

        badge_service.award_placement_badges(db, 1, 10, placement=1, total_participants=5)

        called_types = [c.args[3] for c in mock_award.call_args_list]
        assert TournamentBadgeType.CHAMPION in called_types  # hardcoded fallback

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_v2_no_placement_config_falls_back_to_hardcoded(self, mock_award):
        """reward_config present but placement 2 has no second_place → empty badge_configs → hardcoded."""
        mock_award.return_value = MagicMock()
        # Only first_place configured — no second_place
        reward_config = {"first_place": {"badges": []}}
        tournament = MagicMock()
        tournament.reward_config = reward_config
        db = _db_split(tournament_mock=tournament)

        badge_service.award_placement_badges(db, 1, 10, placement=2, total_participants=5)

        called_types = [c.args[3] for c in mock_award.call_args_list]
        assert TournamentBadgeType.RUNNER_UP in called_types


# ─── TestAwardParticipationBadge ───────────────────────────────────────────────

class TestAwardParticipationBadge:
    """Tests for award_participation_badge() — first tournament vs subsequent."""

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_first_tournament_awards_debut_badge(self, mock_award):
        db = _db_simple()
        db.query.return_value.filter.return_value.scalar.return_value = 0
        mock_award.return_value = MagicMock()

        badge_service.award_participation_badge(db, 1, 10)

        mock_award.assert_called_once_with(db, 1, 10, TournamentBadgeType.FIRST_TOURNAMENT)

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_subsequent_tournament_awards_participant_badge(self, mock_award):
        db = _db_simple()
        db.query.return_value.filter.return_value.scalar.return_value = 3
        mock_award.return_value = MagicMock()

        badge_service.award_participation_badge(db, 1, 10)

        mock_award.assert_called_once_with(db, 1, 10, TournamentBadgeType.TOURNAMENT_PARTICIPANT)

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_scalar_none_treated_as_zero(self, mock_award):
        """scalar() → None → 'or 0' → 0 → FIRST_TOURNAMENT."""
        db = _db_simple()
        db.query.return_value.filter.return_value.scalar.return_value = None
        mock_award.return_value = MagicMock()

        badge_service.award_participation_badge(db, 1, 10)

        mock_award.assert_called_once_with(db, 1, 10, TournamentBadgeType.FIRST_TOURNAMENT)

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_exactly_one_previous_awards_participant(self, mock_award):
        db = _db_simple()
        db.query.return_value.filter.return_value.scalar.return_value = 1
        mock_award.return_value = MagicMock()

        badge_service.award_participation_badge(db, 1, 10)

        mock_award.assert_called_once_with(db, 1, 10, TournamentBadgeType.TOURNAMENT_PARTICIPANT)


# ─── TestCheckAndAwardMilestoneBadges ─────────────────────────────────────────

class TestCheckAndAwardMilestoneBadges:
    """Tests for check_and_award_milestone_badges() — threshold + existence logic."""

    def _db(self, total_count=0, first_returns=None, champion_count=0):
        """
        DB mock for milestone tests. Patches award_badge separately.
        first_returns: side_effect list for existence checks (veteran/legend/triple_crown).
        """
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.scalar.return_value = total_count
        if first_returns is not None:
            q.first.side_effect = first_returns
        else:
            q.first.return_value = None
        q.all.return_value = [MagicMock() for _ in range(champion_count)]
        db.begin_nested.return_value = MagicMock()
        return db

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_below_5_no_milestone_badges(self, mock_award):
        db = self._db(total_count=4, champion_count=0)
        result = badge_service.check_and_award_milestone_badges(db, 1, 10)
        assert result == []
        mock_award.assert_not_called()

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_exactly_5_awards_veteran(self, mock_award):
        mock_award.return_value = MagicMock(badge_type=TournamentBadgeType.TOURNAMENT_VETERAN)
        # first() call: veteran check → None (doesn't exist)
        db = self._db(total_count=5, first_returns=[None], champion_count=0)

        result = badge_service.check_and_award_milestone_badges(db, 1, 10)

        mock_award.assert_called_once_with(
            db, 1, 10, TournamentBadgeType.TOURNAMENT_VETERAN, {"count": 5}
        )
        assert len(result) == 1

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_5_veteran_already_exists_skips(self, mock_award):
        existing = _mock_badge(badge_type=TournamentBadgeType.TOURNAMENT_VETERAN)
        # first() call: veteran check → existing (already has it)
        db = self._db(total_count=5, first_returns=[existing], champion_count=0)

        result = badge_service.check_and_award_milestone_badges(db, 1, 10)

        assert result == []
        mock_award.assert_not_called()

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_10_awards_both_veteran_and_legend(self, mock_award):
        vet = MagicMock(badge_type=TournamentBadgeType.TOURNAMENT_VETERAN)
        leg = MagicMock(badge_type=TournamentBadgeType.TOURNAMENT_LEGEND)
        mock_award.side_effect = [vet, leg]
        # first() calls: veteran=None, legend=None
        db = self._db(total_count=10, first_returns=[None, None], champion_count=0)

        result = badge_service.check_and_award_milestone_badges(db, 1, 10)

        assert len(result) == 2
        badge_types = [b.badge_type for b in result]
        assert TournamentBadgeType.TOURNAMENT_VETERAN in badge_types
        assert TournamentBadgeType.TOURNAMENT_LEGEND in badge_types

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_legend_already_exists_skips_legend_only(self, mock_award):
        existing_legend = _mock_badge(badge_type=TournamentBadgeType.TOURNAMENT_LEGEND)
        vet = MagicMock(badge_type=TournamentBadgeType.TOURNAMENT_VETERAN)
        mock_award.return_value = vet
        # veteran=None (doesn't exist), legend=existing
        db = self._db(total_count=10, first_returns=[None, existing_legend], champion_count=0)

        result = badge_service.check_and_award_milestone_badges(db, 1, 10)

        badge_types = [b.badge_type for b in result]
        assert TournamentBadgeType.TOURNAMENT_VETERAN in badge_types
        assert TournamentBadgeType.TOURNAMENT_LEGEND not in badge_types

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_3_champions_awards_triple_crown(self, mock_award):
        triple = MagicMock(badge_type=TournamentBadgeType.TRIPLE_CROWN)
        mock_award.return_value = triple
        # first() call: triple_crown check → None (doesn't exist)
        db = self._db(total_count=3, first_returns=[None], champion_count=3)

        result = badge_service.check_and_award_milestone_badges(db, 1, 10)

        assert any(b.badge_type == TournamentBadgeType.TRIPLE_CROWN for b in result)
        mock_award.assert_called_once_with(db, 1, 10, TournamentBadgeType.TRIPLE_CROWN)

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_fewer_than_3_champions_no_triple_crown(self, mock_award):
        db = self._db(total_count=2, champion_count=2)

        result = badge_service.check_and_award_milestone_badges(db, 1, 10)

        assert not any(b.badge_type == TournamentBadgeType.TRIPLE_CROWN for b in result)

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_triple_crown_already_exists_skips(self, mock_award):
        existing_triple = _mock_badge(badge_type=TournamentBadgeType.TRIPLE_CROWN)
        # first() call: triple_crown check → already exists
        db = self._db(total_count=3, first_returns=[existing_triple], champion_count=3)

        result = badge_service.check_and_award_milestone_badges(db, 1, 10)

        assert not any(b.badge_type == TournamentBadgeType.TRIPLE_CROWN for b in result)
        mock_award.assert_not_called()

    @patch("app.services.tournament.tournament_badge_service.award_badge")
    def test_zero_total_tournaments_no_badges(self, mock_award):
        db = self._db(total_count=0, champion_count=0)
        result = badge_service.check_and_award_milestone_badges(db, 1, 10)
        assert result == []
        mock_award.assert_not_called()


# ─── TestGetPlayerBadges ───────────────────────────────────────────────────────

class TestGetPlayerBadges:
    """Tests for get_player_badges() — query, filter, integrity guard."""

    def test_returns_empty_list_when_no_badges(self):
        db = _db_simple()
        result = badge_service.get_player_badges(db, user_id=1)
        assert result == []

    def test_without_tournament_id_filter_applies_only_user_filter(self):
        db = _db_simple()
        b = _mock_badge()
        db.query.return_value.options.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [b]

        result = badge_service.get_player_badges(db, user_id=1)

        assert len(result) == 1
        b.to_dict.assert_called_once()

    def test_with_tournament_id_applies_additional_filter(self):
        db = _db_simple()
        b = _mock_badge()
        # We check that .filter() is called twice (user + tournament_id)
        q = MagicMock()
        q.options.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = [b]
        db.query.return_value = q

        badge_service.get_player_badges(db, user_id=1, tournament_id=5)

        # filter() called at least twice: once for user_id, once for semester_id
        assert q.filter.call_count >= 2

    def test_data_integrity_badge_has_semester_id_but_no_tournament_raises(self):
        db = _db_simple()
        bad_badge = _mock_badge(semester_id_val=10, has_tournament=False)
        db.query.return_value.options.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [bad_badge]

        with pytest.raises(ValueError, match="Data integrity issue"):
            badge_service.get_player_badges(db, user_id=1)

    def test_data_integrity_no_semester_id_does_not_raise(self):
        """Badge with semester_id=None is allowed (no tournament link)."""
        db = _db_simple()
        b = _mock_badge(semester_id_val=None, has_tournament=False)
        db.query.return_value.options.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [b]

        result = badge_service.get_player_badges(db, user_id=1)

        assert len(result) == 1  # no ValueError raised

    def test_limit_parameter_passed_to_query(self):
        db = _db_simple()
        q = MagicMock()
        q.options.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []
        db.query.return_value = q

        badge_service.get_player_badges(db, user_id=1, limit=5)

        q.limit.assert_called_with(5)


# ─── TestGetPlayerBadgeShowcase ────────────────────────────────────────────────

class TestGetPlayerBadgeShowcase:
    """Tests for get_player_badge_showcase() — grouping, rarity sort, date sort."""

    def test_empty_showcase_structure(self):
        db = _db_simple()
        result = badge_service.get_player_badge_showcase(db, user_id=1)

        assert result["total_badges"] == 0
        assert result["rarest_badges"] == []
        assert result["recent_badges"] == []
        assert result["by_category"] == {}

    def test_rarity_sort_legendary_first(self):
        common = _mock_badge(rarity=TournamentBadgeRarity.COMMON)
        legendary = _mock_badge(rarity=TournamentBadgeRarity.LEGENDARY)
        epic = _mock_badge(rarity=TournamentBadgeRarity.EPIC)

        db = _db_simple()
        db.query.return_value.filter.return_value.all.return_value = [common, epic, legendary]

        result = badge_service.get_player_badge_showcase(db, user_id=1)

        rarest = result["rarest_badges"]
        assert len(rarest) == 3
        # First rarest badge should come from legendary
        rarities = [b["rarity"] for b in rarest]
        assert rarities[0] == TournamentBadgeRarity.LEGENDARY

    def test_recent_badges_most_recent_first(self):
        older = _mock_badge(earned_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        newer = _mock_badge(earned_at=datetime(2026, 3, 1, tzinfo=timezone.utc))

        db = _db_simple()
        db.query.return_value.filter.return_value.all.return_value = [older, newer]

        result = badge_service.get_player_badge_showcase(db, user_id=1)

        recent = result["recent_badges"]
        # Newer badge should be first
        assert recent[0]["id"] == newer.id

    def test_by_category_grouping(self):
        placement = _mock_badge(category=TournamentBadgeCategory.PLACEMENT)
        participation = _mock_badge(category=TournamentBadgeCategory.PARTICIPATION)

        db = _db_simple()
        db.query.return_value.filter.return_value.all.return_value = [placement, participation]

        result = badge_service.get_player_badge_showcase(db, user_id=1)

        assert TournamentBadgeCategory.PLACEMENT in result["by_category"]
        assert TournamentBadgeCategory.PARTICIPATION in result["by_category"]
        assert result["by_category"][TournamentBadgeCategory.PLACEMENT]["count"] == 1

    def test_rarest_badges_capped_at_5(self):
        badges = [
            _mock_badge(rarity=TournamentBadgeRarity.EPIC, earned_at=datetime(2026, i, 1, tzinfo=timezone.utc))
            for i in range(1, 8)
        ]
        db = _db_simple()
        db.query.return_value.filter.return_value.all.return_value = badges

        result = badge_service.get_player_badge_showcase(db, user_id=1)

        assert len(result["rarest_badges"]) == 5
        assert len(result["recent_badges"]) == 5

    def test_total_badges_count(self):
        badges = [_mock_badge() for _ in range(3)]
        db = _db_simple()
        db.query.return_value.filter.return_value.all.return_value = badges

        result = badge_service.get_player_badge_showcase(db, user_id=1)

        assert result["total_badges"] == 3


# ─── TestRewardPipelineSanity ──────────────────────────────────────────────────

class TestRewardPipelineSanity:
    """
    Integration sanity test: distribute_rewards_for_user with badge_service NOT mocked.

    DB mock handles all DB calls; participation_service mocked.
    Verifies the full orchestrator → badge_service flow produces badges.
    """

    def _db_for_sanity(self):
        """
        DB mock that handles all query types needed by distribute_rewards_for_user
        with is_sandbox_mode=True and placement=1.
        """
        db = MagicMock()

        tournament = MagicMock()
        tournament.name = "Sanity Cup"
        tournament.reward_config = None  # use hardcoded fallback

        semester_q = MagicMock()
        semester_q.filter.return_value = semester_q
        semester_q.first.return_value = tournament

        participation_q = MagicMock()
        participation_q.filter.return_value = participation_q
        participation_q.with_for_update.return_value = participation_q
        participation_q.first.return_value = None  # not yet distributed

        # TournamentBadge: separate with_for_update chain (no duplicate)
        badge_q = MagicMock()
        badge_q.filter.return_value = badge_q
        badge_q.options.return_value = badge_q
        badge_q.order_by.return_value = badge_q
        badge_q.limit.return_value = badge_q
        badge_q.scalar.return_value = 0   # no previous participation badges
        badge_q.all.return_value = []     # no recent champions
        badge_q.first.return_value = None  # no existing milestone badges

        wfu_q = MagicMock()
        wfu_q.first.return_value = None   # no duplicate badges
        badge_q.with_for_update.return_value = wfu_q

        def _qse(model):
            if model is Semester:
                return semester_q
            if model is TournamentParticipation:
                return participation_q
            return badge_q  # TournamentBadge and func.count(...)

        db.query.side_effect = _qse
        db.begin_nested.return_value = MagicMock()
        return db

    @patch("app.services.tournament.tournament_reward_orchestrator.participation_service")
    def test_placement_1_awards_champion_podium_and_debut_badges(self, mock_ps):
        """placement=1 → CHAMPION + PODIUM_FINISH + FIRST_TOURNAMENT → 3 db.add calls."""
        mock_ps.calculate_skill_points_for_placement.return_value = {}
        mock_ps.convert_skill_points_to_xp.return_value = 0
        participation_record = MagicMock()
        participation_record.skill_rating_delta = None
        mock_ps.record_tournament_participation.return_value = participation_record

        db = self._db_for_sanity()

        result = orchestrator.distribute_rewards_for_user(
            db, user_id=1, tournament_id=10,
            placement=1, total_participants=10,
            is_sandbox_mode=True
        )

        # badge_service.award_badge creates real TournamentBadge instances → db.add called
        # placement=1 → CHAMPION + PODIUM_FINISH (2) + FIRST_TOURNAMENT (1) = 3
        assert db.add.call_count == 3, (
            f"Expected 3 db.add calls (CHAMPION + PODIUM_FINISH + FIRST_TOURNAMENT), "
            f"got {db.add.call_count}"
        )

        # Verify badge types awarded
        awarded_types = [call.args[0].badge_type for call in db.add.call_args_list]
        assert TournamentBadgeType.CHAMPION in awarded_types
        assert TournamentBadgeType.PODIUM_FINISH in awarded_types
        assert TournamentBadgeType.FIRST_TOURNAMENT in awarded_types

    @patch("app.services.tournament.tournament_reward_orchestrator.participation_service")
    def test_placement_4_awards_only_participation_badge(self, mock_ps):
        """placement=4 → no placement badges → only FIRST_TOURNAMENT."""
        mock_ps.calculate_skill_points_for_placement.return_value = {}
        mock_ps.convert_skill_points_to_xp.return_value = 0
        participation_record = MagicMock()
        participation_record.skill_rating_delta = None
        mock_ps.record_tournament_participation.return_value = participation_record

        db = self._db_for_sanity()

        orchestrator.distribute_rewards_for_user(
            db, user_id=1, tournament_id=10,
            placement=4, total_participants=10,
            is_sandbox_mode=True
        )

        # Only FIRST_TOURNAMENT (no placement badges for 4th)
        assert db.add.call_count == 1
        awarded_type = db.add.call_args[0][0].badge_type
        assert awarded_type == TournamentBadgeType.FIRST_TOURNAMENT

    @patch("app.services.tournament.tournament_reward_orchestrator.participation_service")
    def test_result_contains_badge_reward_summary(self, mock_ps):
        """Result structure contains badges[] and total_badges_earned."""
        mock_ps.calculate_skill_points_for_placement.return_value = {}
        mock_ps.convert_skill_points_to_xp.return_value = 0
        participation_record = MagicMock()
        participation_record.skill_rating_delta = None
        mock_ps.record_tournament_participation.return_value = participation_record

        db = self._db_for_sanity()

        result = orchestrator.distribute_rewards_for_user(
            db, user_id=1, tournament_id=10,
            placement=1, total_participants=10,
            is_sandbox_mode=True
        )

        assert result.badges.total_badges_earned == 3
        badge_types = [b.badge_type for b in result.badges.badges]
        assert TournamentBadgeType.CHAMPION in badge_types
        assert result.badges.rarest_badge == TournamentBadgeRarity.EPIC  # CHAMPION is EPIC

    @patch("app.services.tournament.tournament_reward_orchestrator.participation_service")
    def test_idempotency_guard_returns_early_without_awarding(self, mock_ps):
        """If participation already exists, return early — no badges awarded."""
        existing_participation = MagicMock()

        db = MagicMock()
        # Separate with_for_update chain so it returns existing_participation
        # without interfering with other first() calls
        wfu_q = MagicMock()
        wfu_q.first.return_value = existing_participation

        q = MagicMock()
        q.filter.return_value = q
        q.with_for_update.return_value = wfu_q
        q.first.return_value = None   # get_user_reward_summary queries
        q.all.return_value = []
        db.query.return_value = q

        orchestrator.distribute_rewards_for_user(
            db, user_id=1, tournament_id=10,
            placement=1, total_participants=10,
            is_sandbox_mode=True,
            force_redistribution=False
        )

        # Returned early before badge section
        db.add.assert_not_called()
        mock_ps.record_tournament_participation.assert_not_called()

    @patch("app.services.tournament.tournament_reward_orchestrator.participation_service")
    def test_none_placement_awards_no_placement_badges(self, mock_ps):
        """placement=None → orchestrator skips placement badge section."""
        mock_ps.calculate_skill_points_for_placement.return_value = {}
        mock_ps.convert_skill_points_to_xp.return_value = 0
        participation_record = MagicMock()
        participation_record.skill_rating_delta = None
        mock_ps.record_tournament_participation.return_value = participation_record

        db = self._db_for_sanity()

        result = orchestrator.distribute_rewards_for_user(
            db, user_id=1, tournament_id=10,
            placement=None, total_participants=10,
            is_sandbox_mode=True
        )

        awarded_types = [call.args[0].badge_type for call in db.add.call_args_list]
        # No CHAMPION, RUNNER_UP, THIRD_PLACE, PODIUM_FINISH
        assert TournamentBadgeType.CHAMPION not in awarded_types
        assert TournamentBadgeType.PODIUM_FINISH not in awarded_types
        # Only participation badge
        assert TournamentBadgeType.FIRST_TOURNAMENT in awarded_types
