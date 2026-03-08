"""
Unit tests for app/services/tournament/points_calculator_service.py

Covers PointsCalculatorService: all ranking_mode branches, tier/pod modifiers,
batch calculation, validation, summary, and tournament type config loading.
"""
import pytest
from unittest.mock import MagicMock

from app.services.tournament.points_calculator_service import PointsCalculatorService


# ── helpers ──────────────────────────────────────────────────────────────────

def _svc():
    db = MagicMock()
    return PointsCalculatorService(db), db


def _mock_session(ranking_mode="ALL_PARTICIPANTS", pod_tier=None, tournament_round=None, semester_id=1):
    s = MagicMock()
    s.ranking_mode = ranking_mode
    s.pod_tier = pod_tier
    s.tournament_round = tournament_round
    s.semester_id = semester_id
    s.title = "Session A"
    s.tournament_phase = "GROUP"
    return s


def _q_session(db, session):
    db.query.return_value.filter.return_value.first.return_value = session


# ─────────────────────────────────────────────────────────────────────────────
# calculate_points — session not found
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculatePointsNoSession:

    def test_session_not_found_returns_zero(self):
        svc, db = _svc()
        _q_session(db, None)
        assert svc.calculate_points(session_id=99, user_id=42, rank=1) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# calculate_points — ranking_mode branches
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculatePointsRankingModes:

    def test_all_participants_rank1_returns_3(self):
        svc, db = _svc()
        _q_session(db, _mock_session("ALL_PARTICIPANTS"))
        assert svc.calculate_points(1, 1, rank=1) == 3.0

    def test_all_participants_rank2_returns_2(self):
        svc, db = _svc()
        _q_session(db, _mock_session("ALL_PARTICIPANTS"))
        assert svc.calculate_points(1, 1, rank=2) == 2.0

    def test_all_participants_rank4_returns_0(self):
        svc, db = _svc()
        _q_session(db, _mock_session("ALL_PARTICIPANTS"))
        assert svc.calculate_points(1, 1, rank=4) == 0.0

    def test_group_isolated_same_as_all_participants(self):
        svc, db = _svc()
        _q_session(db, _mock_session("GROUP_ISOLATED"))
        assert svc.calculate_points(1, 1, rank=1) == 3.0

    def test_tiered_finals_applies_2x_multiplier(self):
        svc, db = _svc()
        session = _mock_session("TIERED", pod_tier=3)  # tier 3 → 2.0x
        _q_session(db, session)
        # rank=1 → base=3, tier_multiplier=2.0 → 6.0
        assert svc.calculate_points(1, 1, rank=1) == 6.0

    def test_tiered_semis_applies_1_5x_multiplier(self):
        svc, db = _svc()
        session = _mock_session("TIERED", pod_tier=2)  # tier 2 → 1.5x
        _q_session(db, session)
        assert svc.calculate_points(1, 1, rank=1) == 4.5

    def test_tiered_falls_back_to_tournament_round(self):
        svc, db = _svc()
        session = _mock_session("TIERED", pod_tier=None, tournament_round=3)
        _q_session(db, session)
        # tournament_round=3 → tier multiplier 2.0
        assert svc.calculate_points(1, 1, rank=1) == 6.0

    def test_tiered_unknown_tier_defaults_1x(self):
        svc, db = _svc()
        session = _mock_session("TIERED", pod_tier=99)
        _q_session(db, session)
        assert svc.calculate_points(1, 1, rank=1) == 3.0

    def test_qualified_only_applies_tier_multiplier(self):
        svc, db = _svc()
        session = _mock_session("QUALIFIED_ONLY", pod_tier=2)
        _q_session(db, session)
        assert svc.calculate_points(1, 1, rank=1) == 4.5

    def test_performance_pod_top_pod_bonus(self):
        svc, db = _svc()
        session = _mock_session("PERFORMANCE_POD", pod_tier=1)  # modifier 1.2
        _q_session(db, session)
        assert svc.calculate_points(1, 1, rank=1) == pytest.approx(3.6)

    def test_performance_pod_bottom_penalty(self):
        svc, db = _svc()
        session = _mock_session("PERFORMANCE_POD", pod_tier=3)  # modifier 0.8
        _q_session(db, session)
        assert svc.calculate_points(1, 1, rank=1) == pytest.approx(2.4)

    def test_performance_pod_unknown_uses_1x(self):
        svc, db = _svc()
        session = _mock_session("PERFORMANCE_POD", pod_tier=99)
        _q_session(db, session)
        assert svc.calculate_points(1, 1, rank=1) == 3.0

    def test_unknown_ranking_mode_returns_base(self):
        svc, db = _svc()
        _q_session(db, _mock_session("UNKNOWN_MODE"))
        assert svc.calculate_points(1, 1, rank=1) == 3.0


# ─────────────────────────────────────────────────────────────────────────────
# _get_base_points — custom point scheme
# ─────────────────────────────────────────────────────────────────────────────

class TestGetBasePoints:

    def test_default_scheme_rank1(self):
        svc, _ = _svc()
        assert svc._get_base_points(1) == 3

    def test_default_scheme_rank_outside_returns_0(self):
        svc, _ = _svc()
        assert svc._get_base_points(10) == 0

    def test_custom_scheme_with_int_keys(self):
        svc, _ = _svc()
        config = {"point_scheme": {1: 10, 2: 5}}
        assert svc._get_base_points(1, config) == 10

    def test_custom_scheme_with_string_keys_converted(self):
        svc, _ = _svc()
        config = {"point_scheme": {"1": 10, "2": 5, "3": 2}}
        assert svc._get_base_points(1, config) == 10
        assert svc._get_base_points(2, config) == 5

    def test_no_point_scheme_in_config_uses_default(self):
        svc, _ = _svc()
        config = {"other_key": "value"}
        assert svc._get_base_points(1, config) == 3


# ─────────────────────────────────────────────────────────────────────────────
# calculate_points_batch
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculatePointsBatch:

    def test_batch_returns_dict_per_user(self):
        svc, db = _svc()
        _q_session(db, _mock_session("ALL_PARTICIPANTS"))
        rankings = [(1, 1), (2, 2), (3, 3)]
        result = svc.calculate_points_batch(session_id=1, rankings=rankings)
        assert result[1] == 3.0
        assert result[2] == 2.0
        assert result[3] == 1.0

    def test_batch_empty_returns_empty_dict(self):
        svc, db = _svc()
        _q_session(db, _mock_session())
        result = svc.calculate_points_batch(session_id=1, rankings=[])
        assert result == {}


# ─────────────────────────────────────────────────────────────────────────────
# validate_ranking
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateRanking:

    def test_empty_rankings_invalid(self):
        svc, _ = _svc()
        valid, msg = svc.validate_ranking(session_id=1, rankings=[])
        assert valid is False
        assert "empty" in msg.lower()

    def test_duplicate_ranks_invalid(self):
        svc, _ = _svc()
        valid, msg = svc.validate_ranking(1, [(1, 1), (2, 1)])
        assert valid is False
        assert "Duplicate" in msg

    def test_ranks_not_starting_from_1_invalid(self):
        svc, _ = _svc()
        valid, msg = svc.validate_ranking(1, [(1, 2), (2, 3)])
        assert valid is False
        assert "start from 1" in msg

    def test_valid_ranking(self):
        svc, _ = _svc()
        valid, msg = svc.validate_ranking(1, [(1, 1), (2, 2), (3, 3)])
        assert valid is True


# ─────────────────────────────────────────────────────────────────────────────
# get_tournament_type_config
# ─────────────────────────────────────────────────────────────────────────────

class TestGetTournamentTypeConfig:

    def test_tournament_not_found_returns_none(self):
        svc, db = _svc()
        db.query.return_value.filter.return_value.first.return_value = None
        assert svc.get_tournament_type_config(99) is None

    def test_tournament_no_type_id_returns_none(self):
        svc, db = _svc()
        t = MagicMock()
        t.tournament_type_id = None
        db.query.return_value.filter.return_value.first.return_value = t
        assert svc.get_tournament_type_config(1) is None

    def test_tournament_type_not_found_returns_none(self):
        svc, db = _svc()
        t = MagicMock()
        t.tournament_type_id = 5
        db.query.return_value.filter.return_value.first.side_effect = [t, None]
        assert svc.get_tournament_type_config(1) is None

    def test_returns_config_dict(self):
        svc, db = _svc()
        t = MagicMock()
        t.tournament_type_id = 5
        tt = MagicMock()
        tt.config = {"point_scheme": {1: 5, 2: 3}}
        db.query.return_value.filter.return_value.first.side_effect = [t, tt]
        result = svc.get_tournament_type_config(1)
        assert result == {"point_scheme": {1: 5, 2: 3}}


# ─────────────────────────────────────────────────────────────────────────────
# get_points_summary
# ─────────────────────────────────────────────────────────────────────────────

class TestGetPointsSummary:

    def test_session_not_found_returns_error(self):
        svc, db = _svc()
        db.query.return_value.filter.return_value.first.return_value = None
        result = svc.get_points_summary(session_id=99, rankings=[(1, 1)])
        assert "error" in result

    def test_returns_summary_dict(self):
        svc, db = _svc()
        session = _mock_session("ALL_PARTICIPANTS")
        session.pod_tier = None
        # First call: get session (calculate_points inside); we need consistent returns.
        # Use a counter to route: summary needs session (first call in get_points_summary),
        # then tournament_type_config (needs tournament + type), then calculate_points_batch
        # (needs session for each user). Simplest: return session on every .first() call.
        db.query.return_value.filter.return_value.first.return_value = session
        result = svc.get_points_summary(session_id=1, rankings=[(1, 1), (2, 2)])
        assert "session_id" in result
        assert "points_distribution" in result
        assert result["total_points_awarded"] == 5.0  # 3 + 2
