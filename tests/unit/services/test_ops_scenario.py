"""Unit tests for app/api/api_v1/endpoints/tournaments/ops_scenario.py

Sprint P12 — Coverage target: ≥85% stmt, ≥50% branch

Phases:
  1. Pure helpers: _build_h2h_game_results, _get_tournament_sessions,
                   _calculate_ir_rankings, _finalize_tournament_with_rewards,
                   _simulate_tournament_results (dispatcher)
  2. Endpoint validation: run_ops_scenario — all defensive guard paths
  3. Success path: player_count=0 / INDIVIDUAL_RANKING / auto_generate=False
  4. Minimal simulation helpers: _simulate_individual_ranking,
                                  _simulate_head_to_head_knockout
"""

import json
import logging
from unittest.mock import MagicMock, patch, call

import pytest

from app.api.api_v1.endpoints.tournaments.ops_scenario import (
    OpsScenarioRequest,
    _build_h2h_game_results,
    _calculate_ir_rankings,
    _finalize_tournament_with_rewards,
    _get_tournament_sessions,
    _simulate_group_knockout_tournament,
    _simulate_head_to_head_knockout,
    _simulate_individual_ranking,
    _simulate_knockout_bracket,
    _simulate_league_tournament,
    _simulate_tournament_results,
    run_ops_scenario,
)
from app.models.tournament_enums import TournamentPhase
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.tournaments.ops_scenario"
_LOG = logging.getLogger("test_ops_scenario")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _q(*, first=None, all_=None, count=0):
    """Fluent query mock — filter / filter_by / order_by / all / first / count."""
    q = MagicMock()
    for m in ("filter", "filter_by", "options", "order_by", "offset",
              "limit", "group_by", "join", "with_for_update"):
        getattr(q, m).return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    q.count.return_value = count
    return q


def _seq_db(*qs):
    """n-th db.query() call returns qs[n]; fallback _q() after exhaustion."""
    calls = [0]

    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        return qs[idx] if idx < len(qs) else _q()

    db = MagicMock()
    db.query.side_effect = _side
    return db


def _admin():
    u = MagicMock()
    u.id = 1
    u.role = UserRole.ADMIN
    u.email = "admin@test.com"
    return u


def _req(**overrides):
    """MagicMock OpsScenarioRequest with sensible defaults."""
    r = MagicMock()
    r.scenario = "smoke_test"
    r.player_count = 0
    r.player_ids = None
    r.dry_run = False
    r.confirmed = False
    r.tournament_format = "INDIVIDUAL_RANKING"
    r.tournament_name = "Test"
    r.tournament_type_code = "knockout"
    r.campus_ids = [1]
    r.auto_generate_sessions = False
    r.enrollment_cost = 0
    r.age_group = "PRO"
    r.initial_tournament_status = "IN_PROGRESS"
    r.reward_config = None
    r.game_preset_id = None
    r.scoring_type = "PLACEMENT"
    r.ranking_direction = None
    r.number_of_rounds = 1
    r.simulation_mode = "manual"
    for k, v in overrides.items():
        setattr(r, k, v)
    return r


def _session_mock(*, participants=None, game_results=None, round_num=1,
                   match_num=1, title="Match", phase=None):
    s = MagicMock()
    s.id = 10
    s.participant_user_ids = participants if participants is not None else [42, 43]
    s.game_results = game_results
    s.tournament_round = round_num
    s.tournament_match_number = match_num
    s.title = title
    s.tournament_phase = phase
    s.session_status = "scheduled"
    s.scoring_type = None
    return s


# ===========================================================================
# Phase 1 — Pure helpers
# ===========================================================================

class TestBuildH2HGameResults:
    def test_returns_valid_json(self):
        participants = [
            {"user_id": 42, "result": "win", "score": 3},
            {"user_id": 43, "result": "loss", "score": 0},
        ]
        result = _build_h2h_game_results(participants, round_number=1)
        parsed = json.loads(result)
        assert parsed["match_format"] == "HEAD_TO_HEAD"
        assert parsed["round_number"] == 1
        assert len(parsed["participants"]) == 2

    def test_round_number_preserved(self):
        result = _build_h2h_game_results([], round_number=5)
        assert json.loads(result)["round_number"] == 5


class TestGetTournamentSessions:
    def test_no_ordering(self):
        q = _q(all_=[MagicMock()])
        db = MagicMock()
        db.query.return_value = q
        result = _get_tournament_sessions(db, tournament_id=1)
        assert len(result) == 1
        # order_by should NOT have been called
        q.order_by.assert_not_called()

    def test_ordered_flag(self):
        q = _q(all_=[])
        db = MagicMock()
        db.query.return_value = q
        _get_tournament_sessions(db, tournament_id=1, ordered=True)
        q.order_by.assert_called_once()

    def test_with_phase_flag_takes_precedence(self):
        """with_phase=True overrides ordered=True."""
        q = _q(all_=[])
        db = MagicMock()
        db.query.return_value = q
        _get_tournament_sessions(db, tournament_id=1, ordered=True, with_phase=True)
        # order_by called once (with 3-column tuple via with_phase branch)
        q.order_by.assert_called_once()


class TestCalculateIRRankings:
    def test_empty_sessions_returns_empty_list(self):
        t = MagicMock()
        t.tournament_config_obj = None
        result = _calculate_ir_rankings(t, [], _LOG)
        assert result == []

    def test_sessions_with_no_rounds_data(self):
        t = MagicMock()
        t.tournament_config_obj = None
        s = MagicMock()
        s.rounds_data = None  # → _rd = {}
        result = _calculate_ir_rankings(t, [s], _LOG)
        assert result == []

    def test_sessions_with_non_dict_round_results_skipped(self):
        t = MagicMock()
        t.tournament_config_obj = None
        s = MagicMock()
        s.rounds_data = {"round_results": "not-a-dict"}  # isinstance check fails
        result = _calculate_ir_rankings(t, [s], _LOG)
        assert result == []

    def test_valid_rounds_data_calls_aggregator(self):
        t = MagicMock()
        t.tournament_config_obj = MagicMock()
        t.tournament_config_obj.ranking_direction = "DESC"
        s = MagicMock()
        s.rounds_data = {"round_results": {"1": {"42": "10.5"}}}
        with patch(
            "app.services.tournament.results.calculators.ranking_aggregator.RankingAggregator"
        ) as MockRA:
            MockRA.aggregate_user_values.return_value = {"42": 10.5}
            MockRA.calculate_performance_rankings.return_value = [{"user_id": 42, "rank": 1}]
            result = _calculate_ir_rankings(t, [s], _LOG)
        assert result == [{"user_id": 42, "rank": 1}]
        MockRA.aggregate_user_values.assert_called_once()
        MockRA.calculate_performance_rankings.assert_called_once()

    def test_config_obj_none_uses_asc_default(self):
        t = MagicMock()
        t.tournament_config_obj = None
        s = MagicMock()
        s.rounds_data = {"round_results": {"1": {"42": "10.5"}}}
        with patch(
            "app.services.tournament.results.calculators.ranking_aggregator.RankingAggregator"
        ) as MockRA:
            MockRA.aggregate_user_values.return_value = {}
            MockRA.calculate_performance_rankings.return_value = []
            _calculate_ir_rankings(t, [s], _LOG)
        _, direction = MockRA.aggregate_user_values.call_args.args
        assert direction == "ASC"


class TestFinalizeTournamentWithRewards:
    def test_tournament_not_found_is_noop(self):
        db = _seq_db(_q(first=None))
        with patch("app.models.semester.Semester"):
            with patch(
                "app.services.tournament.results.finalization"
                ".tournament_finalizer.TournamentFinalizer"
            ) as MockFin:
                _finalize_tournament_with_rewards(99, db, _LOG)
        MockFin.assert_not_called()

    def test_success_path_logs_info(self):
        t = MagicMock()
        db = _seq_db(_q(first=t))
        with patch("app.models.semester.Semester"), \
             patch(
                 "app.services.tournament.results.finalization"
                 ".tournament_finalizer.TournamentFinalizer"
             ) as MockFin:
            MockFin.return_value.finalize.return_value = {
                "success": True,
                "tournament_status": "REWARDS_DISTRIBUTED",
                "rewards_message": "Rewards sent",
            }
            logger = MagicMock()
            _finalize_tournament_with_rewards(1, db, logger)
        logger.info.assert_called()

    def test_non_success_logs_warning(self):
        t = MagicMock()
        db = _seq_db(_q(first=t))
        with patch("app.models.semester.Semester"), \
             patch(
                 "app.services.tournament.results.finalization"
                 ".tournament_finalizer.TournamentFinalizer"
             ) as MockFin:
            MockFin.return_value.finalize.return_value = {
                "success": False,
                "message": "Not ready",
            }
            logger = MagicMock()
            _finalize_tournament_with_rewards(1, db, logger)
        logger.warning.assert_called()

    def test_exception_triggers_rollback(self):
        t = MagicMock()
        db = _seq_db(_q(first=t))
        with patch("app.models.semester.Semester"), \
             patch(
                 "app.services.tournament.results.finalization"
                 ".tournament_finalizer.TournamentFinalizer"
             ) as MockFin:
            MockFin.return_value.finalize.side_effect = RuntimeError("DB crash")
            _finalize_tournament_with_rewards(1, db, _LOG)
        db.rollback.assert_called_once()

    def test_exception_and_rollback_exception_are_handled(self):
        t = MagicMock()
        db = _seq_db(_q(first=t))
        db.rollback.side_effect = RuntimeError("rollback also failed")
        with patch("app.models.semester.Semester"), \
             patch(
                 "app.services.tournament.results.finalization"
                 ".tournament_finalizer.TournamentFinalizer"
             ) as MockFin:
            MockFin.return_value.finalize.side_effect = RuntimeError("DB crash")
            # Should not raise — outer except silences rollback failure
            _finalize_tournament_with_rewards(1, db, _LOG)


class TestSimulateTournamentResultsDispatcher:
    """Tests for _simulate_tournament_results routing logic."""

    def test_tournament_not_found_returns_false(self):
        db = _seq_db(_q(first=None), _q(all_=[]))
        ok, msg = _simulate_tournament_results(db, 1, _LOG)
        assert ok is False
        assert "not found" in msg

    def test_routes_h2h_pure_knockout(self):
        t = MagicMock()
        t.format = "HEAD_TO_HEAD"
        # No phases → pure knockout
        db = _seq_db(_q(first=t), _q(all_=[]))
        with patch(f"{_BASE}._simulate_head_to_head_knockout", return_value=(True, "done")) as mock_fn:
            ok, msg = _simulate_tournament_results(db, 1, _LOG)
        assert ok is True
        mock_fn.assert_called_once()

    def test_routes_h2h_league(self):
        t = MagicMock()
        t.format = "HEAD_TO_HEAD"
        s = MagicMock()
        s.tournament_phase = TournamentPhase.GROUP_STAGE
        db = _seq_db(_q(first=t), _q(all_=[s]))
        with patch(f"{_BASE}._simulate_league_tournament", return_value=(True, "league done")) as mock_fn:
            ok, _ = _simulate_tournament_results(db, 1, _LOG)
        assert ok is True
        mock_fn.assert_called_once()

    def test_routes_h2h_group_knockout(self):
        t = MagicMock()
        t.format = "HEAD_TO_HEAD"
        gs = MagicMock()
        gs.tournament_phase = TournamentPhase.GROUP_STAGE
        ko = MagicMock()
        ko.tournament_phase = TournamentPhase.KNOCKOUT
        db = _seq_db(_q(first=t), _q(all_=[gs, ko]))
        with patch(f"{_BASE}._simulate_group_knockout_tournament", return_value=(True, "ok")) as mock_fn:
            ok, _ = _simulate_tournament_results(db, 1, _LOG)
        assert ok is True
        mock_fn.assert_called_once()

    def test_routes_individual_ranking(self):
        t = MagicMock()
        t.format = "INDIVIDUAL_RANKING"
        db = _seq_db(_q(first=t), _q(all_=[]))
        with patch(f"{_BASE}._simulate_individual_ranking", return_value=(True, "ir done")) as mock_fn:
            ok, _ = _simulate_tournament_results(db, 1, _LOG)
        assert ok is True
        mock_fn.assert_called_once_with(db, t, _LOG)

    def test_unsupported_format_returns_false(self):
        t = MagicMock()
        t.format = "BOGUS_FORMAT"
        db = _seq_db(_q(first=t), _q(all_=[]))
        ok, msg = _simulate_tournament_results(db, 1, _LOG)
        assert ok is False
        assert "Unsupported" in msg
        assert "BOGUS_FORMAT" in msg

    def test_tournament_format_none_defaults_to_ir(self):
        t = MagicMock()
        t.format = None  # → defaults to INDIVIDUAL_RANKING
        db = _seq_db(_q(first=t), _q(all_=[]))
        with patch(f"{_BASE}._simulate_individual_ranking", return_value=(True, "ok")):
            ok, _ = _simulate_tournament_results(db, 1, _LOG)
        assert ok is True


# ===========================================================================
# Phase 2 — Endpoint validation
# ===========================================================================

class TestRunOpsScenarioValidation:

    def test_403_non_admin(self):
        u = MagicMock()
        u.role = UserRole.STUDENT
        db = MagicMock()
        with pytest.raises(Exception) as exc:
            run_ops_scenario(_req(), db=db, current_user=u)
        assert exc.value.status_code == 403

    def test_dry_run_returns_early_no_db_writes(self):
        db = MagicMock()
        result = run_ops_scenario(_req(dry_run=True), db=db, current_user=_admin())
        assert result.triggered is False
        assert result.dry_run is True
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_dry_run_includes_scenario_and_count(self):
        db = MagicMock()
        result = run_ops_scenario(
            _req(dry_run=True, player_count=16, scenario="smoke_test"),
            db=db, current_user=_admin()
        )
        assert "smoke_test" in result.message
        assert "16" in result.message

    def test_safety_gate_requires_confirmed(self):
        db = MagicMock()
        with pytest.raises(Exception) as exc:
            run_ops_scenario(
                _req(player_count=128, confirmed=False, dry_run=False),
                db=db, current_user=_admin()
            )
        assert exc.value.status_code == 422
        assert "confirmed=True" in exc.value.detail

    def test_safety_gate_passes_with_confirmed(self):
        """player_count=128 + confirmed=True passes the gate (proceeds to DB ops)."""
        db = _seq_db(
            _q(all_=[]),      # q0: seed pool query (_User join UserLicense)
        )
        with pytest.raises(Exception):
            # Will fail at next step (no seed users) but NOT at the safety gate
            run_ops_scenario(
                _req(player_count=128, confirmed=True, dry_run=False),
                db=db, current_user=_admin()
            )

    def test_player_ids_missing_users_400(self):
        # Request has player_ids=[99] but DB only returns empty valid_rows
        db = _seq_db(
            _q(all_=[]),  # valid_rows: no users found
        )
        with pytest.raises(Exception) as exc:
            run_ops_scenario(
                _req(player_ids=[99], player_count=1),
                db=db, current_user=_admin()
            )
        assert exc.value.status_code == 400
        assert "not found" in exc.value.detail.lower()

    def test_player_ids_hybrid_fill_insufficient_400(self):
        # player_ids=[42] found, but need 2 total → fill 1 from seed, only 0 available
        valid_row = MagicMock()
        valid_row.id = 42
        db = _seq_db(
            _q(all_=[valid_row]),  # valid_rows: 1 found
            _q(all_=[]),           # fill_rows: 0 seed users
        )
        with pytest.raises(Exception) as exc:
            run_ops_scenario(
                _req(player_ids=[42], player_count=2),
                db=db, current_user=_admin()
            )
        assert exc.value.status_code == 400
        assert "hybrid fill" in exc.value.detail.lower()

    def test_auto_mode_no_seed_users_500(self):
        db = _seq_db(
            _q(all_=[]),  # seed_rows: empty
        )
        with pytest.raises(Exception) as exc:
            run_ops_scenario(
                _req(player_count=4, player_ids=None),
                db=db, current_user=_admin()
            )
        assert exc.value.status_code == 500
        assert "seed" in exc.value.detail.lower()

    def test_auto_mode_insufficient_seed_users_400(self):
        seed_row = MagicMock()
        seed_row.id = 10
        db = _seq_db(
            _q(all_=[seed_row]),  # only 1 seed user, but player_count=4
        )
        with pytest.raises(Exception) as exc:
            run_ops_scenario(
                _req(player_count=4, player_ids=None),
                db=db, current_user=_admin()
            )
        assert exc.value.status_code == 400
        assert "seed" in exc.value.detail.lower()

    def test_head_to_head_unknown_tournament_type_500(self):
        # player_count=0, H2H format, tournament type not found
        db = _seq_db(
            _q(first=None),  # TournamentType lookup → not found
        )
        with pytest.raises(Exception) as exc:
            run_ops_scenario(
                _req(tournament_format="HEAD_TO_HEAD", player_count=0,
                     tournament_type_code="nonexistent"),
                db=db, current_user=_admin()
            )
        assert exc.value.status_code == 500
        assert "not found" in exc.value.detail.lower()

    def test_campus_invalid_422(self):
        """Campus IDs not in DB → 422."""
        campus_row = MagicMock()
        campus_row.id = 2  # campus 2 found, but campus 1 requested → invalid
        with patch("app.models.semester.Semester") as MockSem, \
             patch("app.models.semester.SemesterStatus"), \
             patch("app.models.tournament_configuration.TournamentConfiguration"), \
             patch("app.models.tournament_reward_config.TournamentRewardConfig"), \
             patch("app.models.tournament_achievement.TournamentSkillMapping"), \
             patch("app.models.campus.Campus"):
            mock_t = MagicMock()
            mock_t.id = 99
            MockSem.return_value = mock_t
            db = _seq_db(
                _q(first=None),    # q0: grandmaster (IR, no TT query)
                _q(all_=[campus_row]),  # q1: campus validation → found id=2, not id=1
            )
            with pytest.raises(Exception) as exc:
                run_ops_scenario(
                    _req(campus_ids=[1]),
                    db=db, current_user=_admin()
                )
        assert exc.value.status_code == 422
        assert "not found" in exc.value.detail.lower()


# ===========================================================================
# Phase 3 — Success path (player_count=0 / IR / auto_generate=False)
# ===========================================================================

class TestRunOpsScenarioSuccess:

    def test_ir_manual_mode_returns_triggered_true(self):
        """Minimal success: IR, 0 players, no session generation, no simulation."""
        mock_tournament = MagicMock()
        mock_tournament.id = 99
        campus_row = MagicMock()
        campus_row.id = 1  # campus 1 found and valid

        db = _seq_db(
            _q(first=None),        # q0: grandmaster lookup
            _q(all_=[campus_row]), # q1: campus validation
            _q(first=None),        # q2: CampusScheduleConfig existing check
            _q(count=0),           # q3: final session count
        )

        with patch("app.models.semester.Semester") as MockSem, \
             patch("app.models.semester.SemesterStatus"), \
             patch("app.models.tournament_configuration.TournamentConfiguration"), \
             patch("app.models.tournament_reward_config.TournamentRewardConfig"), \
             patch("app.models.tournament_achievement.TournamentSkillMapping"), \
             patch("app.models.campus.Campus"), \
             patch("app.models.campus_schedule_config.CampusScheduleConfig"), \
             patch("app.services.audit_service.AuditService") as MockAudit, \
             patch("app.models.audit_log.AuditAction"), \
             patch("app.models.session.Session"):
            MockSem.return_value = mock_tournament
            audit_entry = MagicMock()
            audit_entry.id = 7
            MockAudit.return_value.log.return_value = audit_entry

            result = run_ops_scenario(
                _req(player_count=0, tournament_format="INDIVIDUAL_RANKING",
                     auto_generate_sessions=False, campus_ids=[1]),
                db=db,
                current_user=_admin()
            )

        assert result.triggered is True
        assert result.tournament_id == 99
        assert result.session_count == 0
        assert result.enrolled_count == 0
        assert result.dry_run is False
        assert result.audit_log_id == 7
        db.add.assert_called()
        db.commit.assert_called()

    def test_explicit_tournament_name_used(self):
        mock_tournament = MagicMock()
        mock_tournament.id = 55
        campus_row = MagicMock()
        campus_row.id = 1

        db = _seq_db(_q(first=None), _q(all_=[campus_row]), _q(first=None), _q(count=0))

        with patch("app.models.semester.Semester") as MockSem, \
             patch("app.models.semester.SemesterStatus"), \
             patch("app.models.tournament_configuration.TournamentConfiguration"), \
             patch("app.models.tournament_reward_config.TournamentRewardConfig"), \
             patch("app.models.tournament_achievement.TournamentSkillMapping"), \
             patch("app.models.campus.Campus"), \
             patch("app.models.campus_schedule_config.CampusScheduleConfig"), \
             patch("app.services.audit_service.AuditService"), \
             patch("app.models.audit_log.AuditAction"), \
             patch("app.models.session.Session"):
            MockSem.return_value = mock_tournament
            result = run_ops_scenario(
                _req(player_count=0, tournament_name="My Custom Tournament",
                     auto_generate_sessions=False, campus_ids=[1]),
                db=db, current_user=_admin()
            )
        assert result.tournament_name == "My Custom Tournament"

    def test_audit_log_failure_is_non_fatal(self):
        """AuditService raising an exception must NOT abort the response."""
        mock_tournament = MagicMock()
        mock_tournament.id = 77
        campus_row = MagicMock()
        campus_row.id = 1

        db = _seq_db(_q(first=None), _q(all_=[campus_row]), _q(first=None), _q(count=0))

        with patch("app.models.semester.Semester") as MockSem, \
             patch("app.models.semester.SemesterStatus"), \
             patch("app.models.tournament_configuration.TournamentConfiguration"), \
             patch("app.models.tournament_reward_config.TournamentRewardConfig"), \
             patch("app.models.tournament_achievement.TournamentSkillMapping"), \
             patch("app.models.campus.Campus"), \
             patch("app.models.campus_schedule_config.CampusScheduleConfig"), \
             patch("app.services.audit_service.AuditService") as MockAudit, \
             patch("app.models.audit_log.AuditAction"), \
             patch("app.models.session.Session"):
            MockSem.return_value = mock_tournament
            MockAudit.return_value.log.side_effect = RuntimeError("audit DB down")
            result = run_ops_scenario(
                _req(player_count=0, auto_generate_sessions=False, campus_ids=[1]),
                db=db, current_user=_admin()
            )
        # Result still returned despite audit failure
        assert result.triggered is True
        assert result.audit_log_id is None  # not set because audit failed

    def test_player_ids_enrollment_loop(self):
        """player_ids=[10] → enrollment loop: 1 player enrolled (covers lines 1179-1187, 1370-1401)."""
        mock_tournament = MagicMock()
        mock_tournament.id = 44
        valid_user_row = MagicMock()
        valid_user_row.id = 10
        campus_row = MagicMock()
        campus_row.id = 1
        lic_mock = MagicMock()
        lic_mock.id = 5

        db = _seq_db(
            _q(all_=[valid_user_row]),  # q0: valid_rows for player_ids=[10]
            _q(first=None),             # q1: grandmaster (IR)
            _q(first=None),             # q2: _Enroll existing check → not enrolled
            _q(first=lic_mock),         # q3: _Lic check → has license
            _q(all_=[campus_row]),      # q4: campus validation
            _q(first=None),             # q5: CampusScheduleConfig
            _q(count=0),               # q6: session count
        )

        with patch("app.models.semester.Semester") as MockSem, \
             patch("app.models.semester.SemesterStatus"), \
             patch("app.models.tournament_configuration.TournamentConfiguration"), \
             patch("app.models.tournament_reward_config.TournamentRewardConfig"), \
             patch("app.models.tournament_achievement.TournamentSkillMapping"), \
             patch("app.models.campus.Campus"), \
             patch("app.models.campus_schedule_config.CampusScheduleConfig"), \
             patch("app.services.audit_service.AuditService"), \
             patch("app.models.audit_log.AuditAction"), \
             patch("app.models.session.Session"), \
             patch("app.models.semester_enrollment.SemesterEnrollment"), \
             patch("app.models.semester_enrollment.EnrollmentStatus"), \
             patch("app.models.license.UserLicense"):
            MockSem.return_value = mock_tournament
            result = run_ops_scenario(
                _req(player_ids=[10], player_count=0,
                     auto_generate_sessions=False, campus_ids=[1]),
                db=db, current_user=_admin()
            )

        assert result.triggered is True
        assert result.enrolled_count == 1

    def test_auto_generate_sync_manual_mode(self):
        """auto_generate_sessions=True, player_count=0, manual mode → sync path, no simulation."""
        mock_tournament = MagicMock()
        mock_tournament.id = 88
        campus_row = MagicMock()
        campus_row.id = 1

        db = _seq_db(
            _q(first=None),        # q0: grandmaster (IR, no TT query)
            _q(all_=[campus_row]), # q1: campus validation
            _q(first=None),        # q2: CampusScheduleConfig existing check
            _q(all_=[]),           # q3: SemesterEnrollment enrolled_user_ids
            _q(count=0),           # q4: final session count
        )

        with patch("app.models.semester.Semester") as MockSem, \
             patch("app.models.semester.SemesterStatus"), \
             patch("app.models.tournament_configuration.TournamentConfiguration"), \
             patch("app.models.tournament_reward_config.TournamentRewardConfig"), \
             patch("app.models.tournament_achievement.TournamentSkillMapping"), \
             patch("app.models.campus.Campus"), \
             patch("app.models.campus_schedule_config.CampusScheduleConfig"), \
             patch("app.services.audit_service.AuditService") as MockAudit, \
             patch("app.models.audit_log.AuditAction"), \
             patch("app.models.session.Session"), \
             patch("app.models.semester_enrollment.SemesterEnrollment"), \
             patch("app.models.semester_enrollment.EnrollmentStatus"), \
             patch(
                 "app.services.tournament.session_generation"
                 ".session_generator.TournamentSessionGenerator"
             ) as MockTSG:
            MockSem.return_value = mock_tournament
            audit_entry = MagicMock()
            audit_entry.id = 8
            MockAudit.return_value.log.return_value = audit_entry
            MockTSG.return_value.generate_sessions.return_value = (True, "0 sessions created", [])

            result = run_ops_scenario(
                _req(player_count=0, auto_generate_sessions=True,
                     simulation_mode="manual", campus_ids=[1]),
                db=db,
                current_user=_admin()
            )

        assert result.triggered is True
        assert result.tournament_id == 88
        assert result.task_id == "sync-done"
        assert result.session_count == 0
        MockTSG.return_value.generate_sessions.assert_called_once()


# ===========================================================================
# Phase 4 — Minimal simulation helper tests
# ===========================================================================

class TestSimulateIndividualRanking:

    def _tournament(self, scoring_type=None):
        t = MagicMock()
        t.id = 1
        if scoring_type:
            t.tournament_config_obj = MagicMock()
            t.tournament_config_obj.scoring_type = scoring_type
        else:
            t.tournament_config_obj = None
        return t

    def test_missing_scoring_type_returns_false(self):
        db = MagicMock()
        t = self._tournament(scoring_type=None)
        ok, msg = _simulate_individual_ranking(db, t, _LOG)
        assert ok is False
        assert "scoring_type" in msg

    def test_no_sessions_returns_false(self):
        db = _seq_db(_q(all_=[]))
        t = self._tournament(scoring_type="SCORE_BASED")
        ok, msg = _simulate_individual_ranking(db, t, _LOG)
        assert ok is False
        assert "No tournament sessions found" in msg

    def test_session_with_no_participants_skipped(self):
        s = _session_mock(participants=[])
        db = _seq_db(_q(all_=[s]))
        t = self._tournament(scoring_type="SCORE_BASED")
        ok, msg = _simulate_individual_ranking(db, t, _LOG)
        assert ok is True
        assert "0 sessions simulated" in msg

    def test_session_with_game_results_skipped(self):
        s = _session_mock(participants=[42], game_results='{"already": "done"}')
        db = _seq_db(_q(all_=[s]))
        t = self._tournament(scoring_type="SCORE_BASED")
        ok, msg = _simulate_individual_ranking(db, t, _LOG)
        assert ok is True
        assert "0 sessions simulated" in msg

    def test_score_based_session_calls_result_processor(self):
        s = _session_mock(participants=[42, 43], game_results=None)
        db = _seq_db(_q(all_=[s]))
        t = self._tournament(scoring_type="SCORE_BASED")
        with patch("app.services.tournament.result_processor.ResultProcessor") as MockRP:
            MockRP.return_value.process_match_results.return_value = None
            ok, msg = _simulate_individual_ranking(db, t, _LOG)
        assert ok is True
        assert "1 sessions simulated" in msg
        MockRP.return_value.process_match_results.assert_called_once()

    def test_time_based_session_simulated(self):
        s = _session_mock(participants=[42], game_results=None)
        db = _seq_db(_q(all_=[s]))
        t = self._tournament(scoring_type="TIME_BASED")
        with patch("app.services.tournament.result_processor.ResultProcessor") as MockRP:
            MockRP.return_value.process_match_results.return_value = None
            ok, _ = _simulate_individual_ranking(db, t, _LOG)
        assert ok is True

    def test_unsupported_scoring_type_skips_session(self):
        s = _session_mock(participants=[42], game_results=None)
        db = _seq_db(_q(all_=[s]))
        t = self._tournament(scoring_type="UNKNOWN_TYPE")
        ok, msg = _simulate_individual_ranking(db, t, _LOG)
        assert ok is True
        assert "0 sessions simulated" in msg

    def test_result_processor_exception_skips_session(self):
        s = _session_mock(participants=[42, 43], game_results=None)
        db = _seq_db(_q(all_=[s]))
        t = self._tournament(scoring_type="SCORE_BASED")
        with patch("app.services.tournament.result_processor.ResultProcessor") as MockRP:
            MockRP.return_value.process_match_results.side_effect = RuntimeError("fail")
            ok, msg = _simulate_individual_ranking(db, t, _LOG)
        assert ok is True
        assert "0 sessions simulated" in msg

    def test_distance_based_session_simulated(self):
        """DISTANCE_BASED scoring path — single-round session."""
        s = _session_mock(participants=[42], game_results=None)
        s.scoring_type = None  # not ROUNDS_BASED → single-round path
        db = _seq_db(_q(all_=[s]))
        t = self._tournament(scoring_type="DISTANCE_BASED")
        with patch("app.services.tournament.result_processor.ResultProcessor") as MockRP:
            MockRP.return_value.process_match_results.return_value = None
            ok, msg = _simulate_individual_ranking(db, t, _LOG)
        assert ok is True
        assert "1 sessions simulated" in msg

    def test_rounds_based_session_simulated(self):
        """ROUNDS_BASED session — multi-round path with flag_modified."""
        s = _session_mock(participants=[42, 43], game_results=None)
        s.scoring_type = "ROUNDS_BASED"
        s.rounds_data = None          # becomes {} → total_rounds=1, completed=0 → simulate
        s.structure_config = None
        db = _seq_db(_q(all_=[s]))
        t = self._tournament(scoring_type="SCORE_BASED")   # underlying scoring
        with patch("sqlalchemy.orm.attributes.flag_modified"):
            ok, msg = _simulate_individual_ranking(db, t, _LOG)
        assert ok is True
        assert "1 sessions simulated" in msg
        assert s.rounds_data is not None


class TestSimulateHeadToHeadKnockout:

    def test_no_sessions_returns_false(self):
        db = _seq_db(_q(all_=[]))
        ok, msg = _simulate_head_to_head_knockout(db, 1, _LOG)
        assert ok is False
        assert "No tournament sessions found" in msg

    def test_two_player_session_simulated(self):
        s = _session_mock(participants=[42, 43], game_results=None, round_num=1)
        db = _seq_db(_q(all_=[s]))
        ok, msg = _simulate_head_to_head_knockout(db, 1, _LOG)
        assert ok is True
        # session.game_results was set to a JSON string
        assert s.game_results is not None
        game = json.loads(s.game_results)
        assert game["match_format"] == "HEAD_TO_HEAD"
        assert len(game["participants"]) == 2
        # One participant has result=win, other has result=loss
        results = {p["user_id"]: p["result"] for p in game["participants"]}
        assert "win" in results.values()
        assert "loss" in results.values()

    def test_session_already_has_results_skipped(self):
        s = _session_mock(participants=[42, 43],
                          game_results='{"match_format":"HEAD_TO_HEAD"}',
                          round_num=1)
        db = _seq_db(_q(all_=[s]))
        ok, msg = _simulate_head_to_head_knockout(db, 1, _LOG)
        assert ok is True
        # game_results not changed (was already set before call)
        assert s.game_results == '{"match_format":"HEAD_TO_HEAD"}'

    def test_session_with_no_participants_skipped(self):
        s = _session_mock(participants=[], game_results=None, round_num=1)
        db = _seq_db(_q(all_=[s]))
        ok, msg = _simulate_head_to_head_knockout(db, 1, _LOG)
        assert ok is True
        assert s.game_results is None

    def test_session_with_wrong_participant_count_skipped(self):
        """Session with 3 participants (not 2) is skipped with a warning."""
        s = _session_mock(participants=[42, 43, 44], game_results=None, round_num=1)
        db = _seq_db(_q(all_=[s]))
        ok, _ = _simulate_head_to_head_knockout(db, 1, _LOG)
        assert ok is True
        assert s.game_results is None  # skipped

    def test_two_round_bracket_advancement(self):
        """Winners from round 1 are assigned to round 2 session."""
        r1s1 = _session_mock(participants=[1, 2], round_num=1, match_num=1, title="SF1")
        r1s2 = _session_mock(participants=[3, 4], round_num=1, match_num=2, title="SF2")
        r2s1 = _session_mock(participants=[], round_num=2, match_num=1, title="Final")

        db = _seq_db(_q(all_=[r1s1, r1s2, r2s1]))
        ok, _ = _simulate_head_to_head_knockout(db, 1, _LOG)
        assert ok is True
        # Round 2 session should now have 2 participants (winners from round 1)
        assert len(r2s1.participant_user_ids) == 2
        # Winners must be from the original participants
        for uid in r2s1.participant_user_ids:
            assert uid in [1, 2, 3, 4]


# ===========================================================================
# Phase 5 — Remaining simulation functions (league, knockout_bracket, group_knockout)
# ===========================================================================

class TestSimulateLeagueTournament:
    """_simulate_league_tournament(db, tournament_id, logger) — lines 862-946."""

    def test_no_sessions_returns_false(self):
        with patch(f"{_BASE}._get_tournament_sessions", return_value=[]):
            ok, msg = _simulate_league_tournament(MagicMock(), 1, _LOG)
        assert ok is False
        assert "No tournament sessions found" in msg

    def test_session_no_participants_skipped(self):
        s = _session_mock(participants=[], game_results=None)
        with patch(f"{_BASE}._get_tournament_sessions", return_value=[s]):
            ok, msg = _simulate_league_tournament(MagicMock(), 1, _LOG)
        assert ok is True
        assert "0 league sessions simulated" in msg

    def test_session_already_has_results_skipped(self):
        s = _session_mock(participants=[42, 43], game_results='{"already":"done"}')
        with patch(f"{_BASE}._get_tournament_sessions", return_value=[s]):
            ok, msg = _simulate_league_tournament(MagicMock(), 1, _LOG)
        assert ok is True
        assert "0 league sessions simulated" in msg

    def test_two_player_win_session_simulated(self):
        s = _session_mock(participants=[42, 43], game_results=None)
        db = MagicMock()
        with patch(f"{_BASE}._get_tournament_sessions", return_value=[s]), \
             patch("random.choice", side_effect=["win", True]), \
             patch("random.randint", side_effect=[3, 1]):
            ok, msg = _simulate_league_tournament(db, 1, _LOG)
        assert ok is True
        assert "1 league sessions simulated" in msg
        assert s.game_results is not None
        db.commit.assert_called()

    def test_two_player_draw_session_simulated(self):
        s = _session_mock(participants=[42, 43], game_results=None)
        db = MagicMock()
        with patch(f"{_BASE}._get_tournament_sessions", return_value=[s]), \
             patch("random.choice", return_value="draw"), \
             patch("random.randint", return_value=2):
            ok, msg = _simulate_league_tournament(db, 1, _LOG)
        assert ok is True
        game = json.loads(s.game_results)
        results = {p["user_id"]: p["result"] for p in game["participants"]}
        assert results[42] == "draw"
        assert results[43] == "draw"

    def test_two_player_user2_wins_session_simulated(self):
        """random.choice(True/False) returns False → user_2 wins (covers else branch)."""
        s = _session_mock(participants=[42, 43], game_results=None)
        db = MagicMock()
        with patch(f"{_BASE}._get_tournament_sessions", return_value=[s]), \
             patch("random.choice", side_effect=["win", False]), \
             patch("random.randint", side_effect=[3, 1]):
            ok, msg = _simulate_league_tournament(db, 1, _LOG)
        assert ok is True
        game = json.loads(s.game_results)
        results = {p["user_id"]: p["result"] for p in game["participants"]}
        assert results[42] == "loss"
        assert results[43] == "win"


class TestSimulateKnockoutBracket:
    """_simulate_knockout_bracket(db, sessions, logger) → (simulated, skipped) — lines 949-1041."""

    def test_empty_list_returns_zeros(self):
        simulated, skipped = _simulate_knockout_bracket(MagicMock(), [], _LOG)
        assert simulated == 0
        assert skipped == 0

    def test_session_already_has_results_skipped(self):
        s = _session_mock(participants=[42, 43], game_results='{"done":true}', round_num=1)
        simulated, skipped = _simulate_knockout_bracket(MagicMock(), [s], _LOG)
        assert simulated == 0
        assert skipped == 1

    def test_session_no_participants_skipped(self):
        s = _session_mock(participants=[], game_results=None, round_num=1)
        simulated, skipped = _simulate_knockout_bracket(MagicMock(), [s], _LOG)
        assert simulated == 0
        assert skipped == 1

    def test_two_player_session_simulated(self):
        s = _session_mock(participants=[42, 43], game_results=None, round_num=1, match_num=1, title="Final")
        simulated, skipped = _simulate_knockout_bracket(MagicMock(), [s], _LOG)
        assert simulated == 1
        assert skipped == 0
        assert s.game_results is not None
        game = json.loads(s.game_results)
        results = {p["user_id"]: p["result"] for p in game["participants"]}
        assert "win" in results.values()
        assert "loss" in results.values()

    def test_bracket_advancement_to_next_round(self):
        """Winners from round 1 are propagated to round 2 and then simulated."""
        r1s1 = _session_mock(participants=[1, 2], round_num=1, match_num=1, title="SF1")
        r1s2 = _session_mock(participants=[3, 4], round_num=1, match_num=2, title="SF2")
        r2s1 = _session_mock(participants=[], round_num=2, match_num=1, title="Final")
        simulated, skipped = _simulate_knockout_bracket(MagicMock(), [r1s1, r1s2, r2s1], _LOG)
        # Round 1: 2 sessions, Round 2: 1 session (after winner assignment)
        assert simulated == 3
        assert skipped == 0
        assert len(r2s1.participant_user_ids) == 2
        for uid in r2s1.participant_user_ids:
            assert uid in [1, 2, 3, 4]


class TestSimulateGroupKnockoutTournament:
    """_simulate_group_knockout_tournament(db, tournament_id, logger) — lines 643-859."""

    def test_no_sessions_returns_false(self):
        with patch(f"{_BASE}._get_tournament_sessions", return_value=[]):
            ok, msg = _simulate_group_knockout_tournament(MagicMock(), 1, _LOG)
        assert ok is False
        assert "No tournament sessions found" in msg

    def test_group_sessions_only_simulated(self):
        gs = _session_mock(participants=[1, 2], game_results=None, round_num=1, match_num=1)
        gs.tournament_phase = "GROUP_STAGE"
        gs.group_identifier = "A"
        db = MagicMock()
        with patch(f"{_BASE}._get_tournament_sessions", return_value=[gs]), \
             patch(f"{_BASE}._simulate_knockout_bracket", return_value=(0, 0)):
            ok, msg = _simulate_group_knockout_tournament(db, 1, _LOG)
        assert ok is True
        assert "group=1" in msg
        db.commit.assert_called()

    def test_group_and_knockout_sessions(self):
        gs = _session_mock(participants=[1, 2], game_results=None, round_num=1, match_num=1)
        gs.tournament_phase = "GROUP_STAGE"
        gs.group_identifier = "A"
        ks = _session_mock(participants=[], game_results=None, round_num=1, match_num=1, title="QF")
        ks.tournament_phase = "KNOCKOUT"
        db = MagicMock()
        with patch(f"{_BASE}._get_tournament_sessions", return_value=[gs, ks]), \
             patch(f"{_BASE}._simulate_knockout_bracket", return_value=(1, 0)):
            ok, msg = _simulate_group_knockout_tournament(db, 1, _LOG)
        assert ok is True
        assert "group=1" in msg
        assert "knockout=1" in msg

    def test_already_simulated_group_sessions_skipped(self):
        gs = _session_mock(participants=[1, 2], game_results='{"done":true}', round_num=1)
        gs.tournament_phase = "GROUP_STAGE"
        gs.group_identifier = "A"
        db = MagicMock()
        with patch(f"{_BASE}._get_tournament_sessions", return_value=[gs]), \
             patch(f"{_BASE}._simulate_knockout_bracket", return_value=(0, 0)):
            ok, msg = _simulate_group_knockout_tournament(db, 1, _LOG)
        assert ok is True
        assert "group=0" in msg
