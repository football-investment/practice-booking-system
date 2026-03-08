"""
Unit tests for app/api/api_v1/endpoints/tournaments/calculate_rankings.py

Coverage targets:
  calculate_tournament_rankings() — POST /{tournament_id}/calculate-rankings
    - 404: tournament not found
    - 403: non-admin, non-master-instructor user
    - Admin allowed regardless of master_instructor_id
    - Master instructor of the tournament allowed
    - 400: no sessions found
    - 400: sessions missing results (non-group_knockout default path)
    - 400: no GROUP_STAGE sessions (group_knockout tournament type)
    - 400: GROUP_STAGE sessions missing results (group_knockout)
    - group_knockout happy path: group + completed-knockout sessions passed to strategy
    - HEAD_TO_HEAD happy path: RankingStrategyFactory.create called
    - HEAD_TO_HEAD missing tournament_type → 400
    - INDIVIDUAL happy path: RankingAggregator used
    - INDIVIDUAL no round_results → 400
    - ValueError from strategy → 400 with detail
    - Idempotency: existing rankings deleted before insert
    - db.commit called on success
    - Response fields: tournament_id, tournament_format, rankings_count, rankings, message

  get_tournament_rankings() — GET /{tournament_id}/rankings
    - 404: tournament not found
    - Empty rankings list → early return with message
    - Basic response fields present
    - group_identifier map populated from GROUP_STAGE sessions
    - IR tournament: measured_value added to each entry
    - Reward map populated when tournament_status == REWARDS_DISTRIBUTED

Patch paths:
  _BASE = "app.api.api_v1.endpoints.tournaments.calculate_rankings"
  _FACTORY = f"{_BASE}.RankingStrategyFactory"
  _AGG = "app.services.tournament.results.calculators.ranking_aggregator.RankingAggregator"
"""

import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import HTTPException

from app.api.api_v1.endpoints.tournaments.calculate_rankings import (
    calculate_tournament_rankings,
    get_tournament_rankings,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.tournaments.calculate_rankings"
_FACTORY = f"{_BASE}.RankingStrategyFactory"
_AGG = "app.services.tournament.results.calculators.ranking_aggregator.RankingAggregator"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user(role: UserRole = UserRole.ADMIN, user_id: int = 42):
    u = MagicMock()
    u.id = user_id
    u.role = role
    return u


def _config(type_code=None, ranking_direction="DESC", scoring_type="SCORE_BASED"):
    cfg = MagicMock()
    if type_code:
        cfg.tournament_type = MagicMock()
        cfg.tournament_type.code = type_code
    else:
        cfg.tournament_type = None
    cfg.ranking_direction = ranking_direction
    cfg.scoring_type = scoring_type
    return cfg


def _tournament(
    tid=1,
    format_="INDIVIDUAL_RANKING",
    master_id=42,
    config=None,
    tournament_status="ACTIVE",
):
    t = MagicMock()
    t.id = tid
    t.format = format_
    t.master_instructor_id = master_id
    t.tournament_config_obj = config
    t.tournament_status = tournament_status
    return t


def _session(game_results=None, rounds_data=None, phase=None, group_id=None):
    s = MagicMock()
    s.game_results = game_results
    s.rounds_data = rounds_data
    s.tournament_phase = phase
    s.group_identifier = group_id
    s.match_format = "INDIVIDUAL_RANKING"
    s.participant_user_ids = []
    return s


def _q(first=None, all_=None):
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.join.return_value = q
    q.order_by.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ or []
    q.delete.return_value = 0
    q.count.return_value = 0
    return q


def _db(*queues):
    """Sequential db.query() mock — n-th call returns queues[n]."""
    db = MagicMock()
    db.query.side_effect = list(queues) + [MagicMock()] * 6
    return db


def _session_with_results():
    """Session with valid game_results."""
    return _session(game_results='{"participants":[]}')


def _session_with_rounds():
    """Session with valid rounds_data.round_results."""
    return _session(rounds_data={"round_results": {"1": {"10": "85", "20": "60"}}})


# ── calculate_tournament_rankings — 404 ────────────────────────────────────────

class TestCalculateRankings404:

    def test_raises_404_when_tournament_not_found(self):
        db = _db(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            calculate_tournament_rankings(
                tournament_id=9999, db=db, current_user=_user()
            )
        assert exc.value.status_code == 404


# ── calculate_tournament_rankings — 403 ────────────────────────────────────────

class TestCalculateRankings403:

    def test_instructor_not_master_raises_403(self):
        t = _tournament(master_id=99)  # current user is 42, not 99
        db = _db(_q(first=t))
        with pytest.raises(HTTPException) as exc:
            calculate_tournament_rankings(
                tournament_id=1, db=db,
                current_user=_user(role=UserRole.INSTRUCTOR, user_id=42),
            )
        assert exc.value.status_code == 403

    def test_admin_bypasses_master_check(self):
        t = _tournament(master_id=99, config=_config())
        s = _session_with_results()
        db = _db(_q(first=t), _q(all_=[s]), _q())
        with patch(_FACTORY) as mock_f:
            mock_f.create.return_value.calculate_rankings.return_value = [
                {"user_id": 10, "rank": 1, "points": 80, "wins": 0, "losses": 0, "ties": 0}
            ]
            t.format = "HEAD_TO_HEAD"
            t.tournament_config_obj = _config(type_code="league")
            result = calculate_tournament_rankings(
                tournament_id=1, db=db,
                current_user=_user(role=UserRole.ADMIN, user_id=42),  # ≠ master_id=99
            )
        assert result["tournament_id"] == 1

    def test_master_instructor_of_own_tournament_allowed(self):
        t = _tournament(master_id=42, format_="HEAD_TO_HEAD", config=_config(type_code="league"))
        s = _session_with_results()
        db = _db(_q(first=t), _q(all_=[s]), _q())
        with patch(_FACTORY) as mock_f:
            mock_f.create.return_value.calculate_rankings.return_value = [
                {"user_id": 10, "rank": 1, "points": 5, "wins": 1, "losses": 0, "ties": 0}
            ]
            result = calculate_tournament_rankings(
                tournament_id=1, db=db,
                current_user=_user(role=UserRole.INSTRUCTOR, user_id=42),
            )
        assert result["tournament_id"] == 1


# ── calculate_tournament_rankings — 400 sessions ──────────────────────────────

class TestCalculateRankings400Sessions:

    def test_raises_400_when_no_sessions(self):
        t = _tournament()
        db = _db(_q(first=t), _q(all_=[]))
        with pytest.raises(HTTPException) as exc:
            calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        assert exc.value.status_code == 400
        assert "sessions" in exc.value.detail.lower()

    def test_raises_400_when_sessions_missing_results(self):
        t = _tournament()
        s = _session(game_results=None, rounds_data=None)  # no results
        db = _db(_q(first=t), _q(all_=[s]))
        with pytest.raises(HTTPException) as exc:
            calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        assert exc.value.status_code == 400
        assert "results" in exc.value.detail.lower()

    def test_session_with_rounds_data_counts_as_having_results(self):
        """rounds_data.round_results qualifies as 'has results'."""
        t = _tournament(config=_config(ranking_direction="DESC"))
        s = _session_with_rounds()
        db = _db(_q(first=t), _q(all_=[s]), _q())
        with patch(_AGG) as mock_agg:
            mock_agg.aggregate_user_values.return_value = {"10": 85.0}
            mock_agg.calculate_performance_rankings.return_value = [
                {"user_id": 10, "rank": 1, "final_value": 85.0}
            ]
            result = calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        assert result["rankings_count"] == 1


# ── calculate_tournament_rankings — group_knockout path ───────────────────────

class TestCalculateRankingsGroupKnockout:

    def _gk_tournament(self):
        return _tournament(
            format_="HEAD_TO_HEAD",
            config=_config(type_code="group_knockout"),
        )

    def test_raises_400_when_no_group_stage_sessions(self):
        t = self._gk_tournament()
        s = _session(game_results='{}', phase="KNOCKOUT")
        db = _db(_q(first=t), _q(all_=[s]))
        with pytest.raises(HTTPException) as exc:
            calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        assert exc.value.status_code == 400
        assert "GROUP_STAGE" in exc.value.detail

    def test_raises_400_when_group_stage_sessions_missing_results(self):
        t = self._gk_tournament()
        gs = _session(game_results=None, phase="GROUP_STAGE")
        db = _db(_q(first=t), _q(all_=[gs]))
        with pytest.raises(HTTPException) as exc:
            calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        assert exc.value.status_code == 400
        assert "GROUP_STAGE" in exc.value.detail

    def test_group_knockout_happy_path_calls_strategy(self):
        t = self._gk_tournament()
        gs = _session(game_results='{}', phase="GROUP_STAGE")
        ks = _session(game_results='{}', phase="KNOCKOUT")
        db = _db(_q(first=t), _q(all_=[gs, ks]), _q())
        with patch(_FACTORY) as mock_f:
            mock_f.create.return_value.calculate_rankings.return_value = [
                {"user_id": 10, "rank": 1, "points": 3, "wins": 1, "losses": 0, "ties": 0}
            ]
            result = calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        mock_f.create.assert_called_once_with(
            tournament_format="HEAD_TO_HEAD",
            tournament_type_code="group_knockout",
        )
        assert result["rankings_count"] == 1


# ── calculate_tournament_rankings — HEAD_TO_HEAD path ─────────────────────────

class TestCalculateRankingsHeadToHead:

    def test_hth_uses_ranking_strategy_factory(self):
        t = _tournament(format_="HEAD_TO_HEAD", config=_config(type_code="league"))
        s = _session_with_results()
        db = _db(_q(first=t), _q(all_=[s]), _q())
        with patch(_FACTORY) as mock_f:
            mock_f.create.return_value.calculate_rankings.return_value = [
                {"user_id": 10, "rank": 1, "points": 9, "wins": 3, "losses": 0, "ties": 0}
            ]
            result = calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        mock_f.create.assert_called_once_with(
            tournament_format="HEAD_TO_HEAD",
            tournament_type_code="league",
        )
        assert result["rankings_count"] == 1

    def test_hth_raises_400_when_missing_tournament_type(self):
        cfg = MagicMock()
        cfg.tournament_type = None
        t = _tournament(format_="HEAD_TO_HEAD", config=cfg)
        s = _session_with_results()
        db = _db(_q(first=t), _q(all_=[s]))
        with pytest.raises(HTTPException) as exc:
            calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        assert exc.value.status_code == 400
        assert "tournament_type" in exc.value.detail

    def test_value_error_from_strategy_raises_400(self):
        t = _tournament(format_="HEAD_TO_HEAD", config=_config(type_code="knockout"))
        s = _session_with_results()
        db = _db(_q(first=t), _q(all_=[s]))
        with patch(_FACTORY) as mock_f:
            mock_f.create.return_value.calculate_rankings.side_effect = ValueError("bad data")
            with pytest.raises(HTTPException) as exc:
                calculate_tournament_rankings(
                    tournament_id=1, db=db, current_user=_user()
                )
        assert exc.value.status_code == 400
        assert "bad data" in exc.value.detail


# ── calculate_tournament_rankings — INDIVIDUAL path ───────────────────────────

class TestCalculateRankingsIndividual:

    def test_individual_uses_ranking_aggregator(self):
        t = _tournament(config=_config(ranking_direction="DESC"))
        s = _session_with_rounds()
        db = _db(_q(first=t), _q(all_=[s]), _q())
        with patch(_AGG) as mock_agg:
            mock_agg.aggregate_user_values.return_value = {"10": 85.0, "20": 60.0}
            mock_agg.calculate_performance_rankings.return_value = [
                {"user_id": 10, "rank": 1, "final_value": 85.0},
                {"user_id": 20, "rank": 2, "final_value": 60.0},
            ]
            result = calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        mock_agg.aggregate_user_values.assert_called_once()
        assert result["rankings_count"] == 2

    def test_individual_raises_400_when_no_round_results(self):
        # game_results is truthy → passes the "has results" session check,
        # but rounds_data is None → combined_round_results stays empty → 400
        t = _tournament(config=_config())
        s = _session(game_results='{"participants":[]}', rounds_data=None)
        db = _db(_q(first=t), _q(all_=[s]))
        with pytest.raises(HTTPException) as exc:
            calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        assert exc.value.status_code == 400
        assert "round results" in exc.value.detail.lower()

    def test_individual_response_has_all_fields(self):
        t = _tournament(config=_config(ranking_direction="ASC"))
        s = _session_with_rounds()
        db = _db(_q(first=t), _q(all_=[s]), _q())
        with patch(_AGG) as mock_agg:
            mock_agg.aggregate_user_values.return_value = {"10": 45.5}
            mock_agg.calculate_performance_rankings.return_value = [
                {"user_id": 10, "rank": 1, "final_value": 45.5}
            ]
            result = calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        assert "tournament_id" in result
        assert "tournament_format" in result
        assert "rankings_count" in result
        assert "rankings" in result
        assert "message" in result

    def test_individual_no_config_defaults_to_asc(self):
        t = _tournament(config=None)
        s = _session_with_rounds()
        db = _db(_q(first=t), _q(all_=[s]), _q())
        with patch(_AGG) as mock_agg:
            mock_agg.aggregate_user_values.return_value = {"10": 30.0}
            mock_agg.calculate_performance_rankings.return_value = [
                {"user_id": 10, "rank": 1, "final_value": 30.0}
            ]
            calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        # ASC is the default direction when config is None
        call_args = mock_agg.aggregate_user_values.call_args
        assert call_args[0][1] == "ASC"


# ── calculate_tournament_rankings — idempotency + commit ─────────────────────

class TestCalculateRankingsIdempotency:

    def test_existing_rankings_deleted_before_insert(self):
        t = _tournament(config=_config(ranking_direction="DESC"))
        s = _session_with_rounds()
        q_delete = _q()
        db = _db(_q(first=t), _q(all_=[s]), q_delete)
        with patch(_AGG) as mock_agg:
            mock_agg.aggregate_user_values.return_value = {"10": 85.0}
            mock_agg.calculate_performance_rankings.return_value = [
                {"user_id": 10, "rank": 1, "final_value": 85.0}
            ]
            calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        q_delete.delete.assert_called_once()

    def test_db_commit_called_on_success(self):
        t = _tournament(config=_config())
        s = _session_with_rounds()
        db = _db(_q(first=t), _q(all_=[s]), _q())
        with patch(_AGG) as mock_agg:
            mock_agg.aggregate_user_values.return_value = {"10": 70.0}
            mock_agg.calculate_performance_rankings.return_value = [
                {"user_id": 10, "rank": 1, "final_value": 70.0}
            ]
            calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        db.commit.assert_called_once()

    def test_db_add_called_for_each_ranking(self):
        t = _tournament(config=_config())
        s = _session_with_rounds()
        db = _db(_q(first=t), _q(all_=[s]), _q())
        with patch(_AGG) as mock_agg:
            mock_agg.aggregate_user_values.return_value = {"10": 85.0, "20": 60.0}
            mock_agg.calculate_performance_rankings.return_value = [
                {"user_id": 10, "rank": 1, "final_value": 85.0},
                {"user_id": 20, "rank": 2, "final_value": 60.0},
            ]
            calculate_tournament_rankings(
                tournament_id=1, db=db, current_user=_user()
            )
        assert db.add.call_count == 2


# ── get_tournament_rankings — 404 + empty ────────────────────────────────────

class TestGetTournamentRankings404:

    def test_raises_404_when_tournament_not_found(self):
        db = _db(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            get_tournament_rankings(tournament_id=9999, db=db, current_user=_user())
        assert exc.value.status_code == 404


class TestGetTournamentRankingsEmpty:

    def test_empty_rankings_returns_early_with_message(self):
        t = _tournament()
        db = _db(_q(first=t), _q(all_=[]))
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert result["tournament_id"] == 1
        assert result["rankings"] == []
        assert "No rankings" in result["message"]


# ── get_tournament_rankings — happy path ──────────────────────────────────────

class TestGetTournamentRankingsHappy:

    def _ranking_row(self, user_id=10, rank=1, points=85.0):
        r = MagicMock()
        r.user_id = user_id
        r.rank = rank
        r.points = points
        r.wins = 2
        r.losses = 0
        r.draws = 1
        r.goals_for = 5
        r.goals_against = 1
        return r

    def _make_db(self, tournament, rows, group_rows=None):
        """DB for GET: q1=tournament, q2=join-ranking-rows, q3=group-sessions."""
        return _db(
            _q(first=tournament),
            _q(all_=rows),
            _q(all_=group_rows or []),
        )

    def test_response_fields_present(self):
        t = _tournament(format_="HEAD_TO_HEAD")
        r = self._ranking_row()
        rows = [(r, "nick10", "User 10")]
        db = self._make_db(t, rows)
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert "tournament_id" in result
        assert "tournament_format" in result
        assert "rankings_count" in result
        assert "rankings" in result

    def test_rankings_count_matches_rows(self):
        t = _tournament(format_="HEAD_TO_HEAD")
        rows = [(self._ranking_row(user_id=10, rank=1), "n1", "U1"),
                (self._ranking_row(user_id=20, rank=2), "n2", "U2")]
        db = self._make_db(t, rows)
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert result["rankings_count"] == 2

    def test_nickname_used_as_display_name(self):
        t = _tournament(format_="HEAD_TO_HEAD")
        r = self._ranking_row()
        rows = [(r, "nick10", "Full Name")]
        db = self._make_db(t, rows)
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert result["rankings"][0]["name"] == "nick10"

    def test_name_fallback_when_no_nickname(self):
        t = _tournament(format_="HEAD_TO_HEAD")
        r = self._ranking_row()
        rows = [(r, None, "Full Name")]
        db = self._make_db(t, rows)
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert result["rankings"][0]["name"] == "Full Name"

    def test_goal_difference_calculated(self):
        t = _tournament(format_="HEAD_TO_HEAD")
        r = self._ranking_row()
        r.goals_for = 7
        r.goals_against = 3
        rows = [(r, "n", "U")]
        db = self._make_db(t, rows)
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert result["rankings"][0]["goal_difference"] == 4

    def test_ir_tournament_adds_measured_value(self):
        t = _tournament(format_="INDIVIDUAL_RANKING")
        r = self._ranking_row(points=72.5)
        rows = [(r, "n", "U")]
        # ir_sessions query (q4) returns empty list
        db = _db(_q(first=t), _q(all_=rows), _q(all_=[]), _q(all_=[]))
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert result["rankings"][0]["measured_value"] == 72.5

    def test_non_ir_tournament_no_measured_value(self):
        t = _tournament(format_="HEAD_TO_HEAD")
        r = self._ranking_row()
        rows = [(r, "n", "U")]
        db = self._make_db(t, rows)
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert "measured_value" not in result["rankings"][0]


# ── Standalone ranking-row helper for new GET tests ───────────────────────────

def _rrow(user_id=42, rank=1, points=80.0):
    r = MagicMock()
    r.user_id = user_id
    r.rank = rank
    r.points = points
    r.wins = 1
    r.losses = 0
    r.draws = 0
    r.goals_for = 3
    r.goals_against = 1
    return r


# ── get_tournament_rankings — group_identifier map (lines 274-290) ─────────────

class TestGetTournamentRankingsGroupIdentifier:

    def test_group_identifier_from_participant_list(self):
        """Lines 277-282: participant_user_ids_raw is already a list → parsed directly."""
        t = _tournament(format_="HEAD_TO_HEAD")
        r = _rrow(user_id=42)
        rows = [(r, "n42", "User42")]
        group_sess = [("GroupA", [42], 10)]
        db = _db(_q(first=t), _q(all_=rows), _q(all_=group_sess))
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert result["rankings"][0]["group_identifier"] == "GroupA"

    def test_group_identifier_from_json_string(self):
        """Lines 279: participant_user_ids_raw is a JSON string → json.loads path."""
        t = _tournament(format_="HEAD_TO_HEAD")
        r = _rrow(user_id=42)
        rows = [(r, "n42", "User42")]
        group_sess = [("GroupB", '[42]', 10)]
        db = _db(_q(first=t), _q(all_=rows), _q(all_=group_sess))
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert result["rankings"][0]["group_identifier"] == "GroupB"

    def test_group_identifier_booking_fallback_when_no_participant_ids(self):
        """Lines 286-290: participant_user_ids_raw is None → Booking query fallback."""
        t = _tournament(format_="HEAD_TO_HEAD")
        r = _rrow(user_id=42)
        rows = [(r, "n42", "User42")]
        group_sess = [("GroupC", None, 10)]
        booking_q = _q(all_=[(42,)])
        db = _db(_q(first=t), _q(all_=rows), _q(all_=group_sess), booking_q)
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert result["rankings"][0]["group_identifier"] == "GroupC"

    def test_group_identifier_none_gid_skipped(self):
        """Line 274: if not gid: continue — session with None gid leaves user unassigned."""
        t = _tournament(format_="HEAD_TO_HEAD")
        r = _rrow(user_id=42)
        rows = [(r, "n42", "User42")]
        group_sess = [(None, [42], 10)]  # gid=None → skipped by guard
        db = _db(_q(first=t), _q(all_=rows), _q(all_=group_sess))
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert result["rankings"][0]["group_identifier"] is None


# ── get_tournament_rankings — REWARDS_DISTRIBUTED reward_map (lines 295-308, 369-376) ─

class TestGetTournamentRankingsRewards:

    def _part(self, user_id=42, xp=100, credits=50):
        p = MagicMock()
        p.user_id = user_id
        p.xp_awarded = xp
        p.credits_awarded = credits
        p.skill_points_awarded = {}
        p.skill_rating_delta = {}
        return p

    def test_reward_fields_populated_when_rewards_distributed(self):
        """Lines 295-308: REWARDS_DISTRIBUTED → participation queried, reward_map built."""
        t = _tournament(format_="HEAD_TO_HEAD", tournament_status="REWARDS_DISTRIBUTED")
        r = _rrow(user_id=42)
        rows = [(r, "n42", "User42")]
        p = self._part(user_id=42, xp=120, credits=60)
        db = _db(_q(first=t), _q(all_=rows), _q(all_=[]), _q(all_=[p]))
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        entry = result["rankings"][0]
        assert entry["xp_earned"] == 120
        assert entry["credits_earned"] == 60

    def test_reward_defaults_when_user_not_in_participation(self):
        """Lines 369-376: user not in reward_map → defaults (xp=0, credits=0) applied."""
        t = _tournament(format_="HEAD_TO_HEAD", tournament_status="REWARDS_DISTRIBUTED")
        r = _rrow(user_id=99)  # user 99 has no participation record
        rows = [(r, "n99", "User99")]
        p = self._part(user_id=42, xp=100, credits=50)  # different user
        db = _db(_q(first=t), _q(all_=rows), _q(all_=[]), _q(all_=[p]))
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        entry = result["rankings"][0]
        assert entry["xp_earned"] == 0
        assert entry["credits_earned"] == 0


# ── get_tournament_rankings — IR round_results (lines 322-339, 365) ───────────

class TestGetTournamentRankingsIRRoundResults:

    def _ir_sess(self, rr_dict):
        s = MagicMock()
        s.rounds_data = {"round_results": rr_dict, "total_rounds": len(rr_dict)}
        return s

    def test_round_results_attached_to_ir_entry(self):
        """Lines 322-339, 365: IR session with dict round_results → entry gets round_results."""
        t = _tournament(format_="INDIVIDUAL_RANKING")
        r = _rrow(user_id=42, points=88.5)
        rows = [(r, "n42", "User42")]
        ir_sess = self._ir_sess({"1": {"42": "88.5"}})
        db = _db(_q(first=t), _q(all_=rows), _q(all_=[]), _q(all_=[ir_sess]))
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        entry = result["rankings"][0]
        assert "round_results" in entry
        assert entry["round_results"]["1"] == "88.5"
        assert entry["round_results"]["total_rounds"] == 1

    def test_round_results_skipped_when_rr_is_list(self):
        """Lines 325-327: round_results is a list (old format) → isinstance check fails, skipped."""
        t = _tournament(format_="INDIVIDUAL_RANKING")
        r = _rrow(user_id=42, points=75.0)
        rows = [(r, "n42", "User42")]
        s = MagicMock()
        s.rounds_data = {"round_results": [[42, 75.0]]}  # list, not dict
        db = _db(_q(first=t), _q(all_=rows), _q(all_=[]), _q(all_=[s]))
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert "round_results" not in result["rankings"][0]

    def test_round_results_skipped_when_player_values_is_list(self):
        """Lines 330-331: player_values for a round is a list → isinstance check fails, skipped."""
        t = _tournament(format_="INDIVIDUAL_RANKING")
        r = _rrow(user_id=42, points=75.0)
        rows = [(r, "n42", "User42")]
        s = MagicMock()
        s.rounds_data = {"round_results": {"1": [42, 75.0]}}  # list pv, not dict
        db = _db(_q(first=t), _q(all_=rows), _q(all_=[]), _q(all_=[s]))
        result = get_tournament_rankings(tournament_id=1, db=db, current_user=_user())
        assert "round_results" not in result["rankings"][0]


# ── calculate_tournament_rankings — multi-session round key merge (lines 166-171) ─

class TestCalculateRankingsMultiSessionMerge:

    def test_two_sessions_overlapping_round_key_merged(self):
        """Lines 169-171: two IR sessions with same round key → combined_round_results merged."""
        t = _tournament(format_="INDIVIDUAL_RANKING", config=_config(ranking_direction="ASC"))
        sess1 = _session(
            game_results='{"p":[42]}',
            rounds_data={"round_results": {"1": {"42": "18.5"}}},
        )
        sess2 = _session(
            game_results='{"p":[99]}',
            rounds_data={"round_results": {"1": {"99": "17.0"}}},
        )
        db = _db(
            _q(first=t),
            _q(all_=[sess1, sess2]),
            _q(),  # TournamentRanking.delete
        )
        with patch(_AGG) as mock_agg:
            mock_agg.aggregate_user_values.return_value = {"42": 18.5, "99": 17.0}
            mock_agg.calculate_performance_rankings.return_value = [
                {"user_id": 42, "rank": 1, "final_value": 18.5},
                {"user_id": 99, "rank": 2, "final_value": 17.0},
            ]
            result = calculate_tournament_rankings(
                tournament_id=1, current_user=_user(), db=db
            )
        # Both users are present in merged round "1"
        combined = mock_agg.aggregate_user_values.call_args[0][0]
        assert "42" in combined["1"]
        assert "99" in combined["1"]
        assert result["rankings_count"] == 2
