"""
P1 Scoring Pipeline Tests — Consolidation Phase
=================================================

Scope: BUG-03 fix verification + reward pathway consistency documentation.

All tests are [GREEN] — documenting correct behaviour after P1 fixes.
No xfail markers in this file.

Covers:
  BUG-03  aggregation_method JSONB now dynamic per strategy (was hardcoded "BEST_VALUE")
  DEBT-01 RankingAggregator dead code removed from SessionFinalizer.__init__
  REWARD  Reward pathway audit: IR vs H2H vs Group consistency documentation

All tests are DB-free (SimpleNamespace / MagicMock).
"""
import json
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.tournament.ranking.ranking_service import RankingService
from app.services.tournament.ranking.strategies.time_based import TimeBasedStrategy
from app.services.tournament.ranking.strategies.score_based import ScoreBasedStrategy
from app.services.tournament.ranking.strategies.rounds_based import RoundsBasedStrategy
from app.services.tournament.ranking.strategies.placement import PlacementStrategy
from app.services.tournament.ranking.strategies.factory import RankingStrategyFactory


# ─────────────────────────────────────────────────────────────────────────────
# 1. BUG-03: aggregation_method label per strategy  [GREEN]
# ─────────────────────────────────────────────────────────────────────────────

class TestAggregationLabels:
    """
    BUG-03 fixed: each strategy returns its own aggregation label via
    get_aggregation_label(ranking_direction=None).

    These labels are stored in session.game_results["aggregation_method"]
    so operators can understand how the final values were calculated.
    """

    # AG-01
    def test_time_based_asc_label_is_min_value(self):
        s = TimeBasedStrategy()
        assert s.get_aggregation_label() == "MIN_VALUE"
        assert s.get_aggregation_label(ranking_direction="ASC") == "MIN_VALUE"

    # AG-02
    def test_time_based_desc_override_label_is_max_value(self):
        s = TimeBasedStrategy()
        assert s.get_aggregation_label(ranking_direction="DESC") == "MAX_VALUE"

    # AG-03
    def test_score_based_label_is_sum_regardless_of_direction(self):
        s = ScoreBasedStrategy()
        assert s.get_aggregation_label() == "SUM"
        assert s.get_aggregation_label(ranking_direction="ASC") == "SUM"
        assert s.get_aggregation_label(ranking_direction="DESC") == "SUM"

    # AG-04
    def test_rounds_based_desc_label_is_max_value(self):
        s = RoundsBasedStrategy()
        assert s.get_aggregation_label() == "MAX_VALUE"
        assert s.get_aggregation_label(ranking_direction="DESC") == "MAX_VALUE"

    # AG-05
    def test_rounds_based_asc_override_label_is_min_value(self):
        s = RoundsBasedStrategy()
        assert s.get_aggregation_label(ranking_direction="ASC") == "MIN_VALUE"

    # AG-06
    def test_placement_label_is_sum_placement(self):
        s = PlacementStrategy()
        assert s.get_aggregation_label() == "SUM_PLACEMENT"
        assert s.get_aggregation_label(ranking_direction="ASC") == "SUM_PLACEMENT"

    # AG-07: RankingService facade
    def test_ranking_service_get_aggregation_label_delegates_to_strategy(self):
        service = RankingService()
        assert service.get_aggregation_label("TIME_BASED") == "MIN_VALUE"
        assert service.get_aggregation_label("TIME_BASED", ranking_direction="DESC") == "MAX_VALUE"
        assert service.get_aggregation_label("SCORE_BASED") == "SUM"
        assert service.get_aggregation_label("ROUNDS_BASED") == "MAX_VALUE"
        assert service.get_aggregation_label("ROUNDS_BASED", ranking_direction="ASC") == "MIN_VALUE"
        assert service.get_aggregation_label("PLACEMENT") == "SUM_PLACEMENT"

    # AG-08: JSONB stored label matches actual behaviour
    def test_bug03_aggregation_method_not_hardcoded_best_value(self):
        """
        BUG-03 fix: no scoring_type should return "BEST_VALUE" as aggregation label
        (the old hardcoded fallback).

        BEST_VALUE is only the fallback in the base class for H2H strategies —
        all INDIVIDUAL_RANKING strategies must return their specific label.
        """
        service = RankingService()
        for scoring_type in ["TIME_BASED", "SCORE_BASED", "ROUNDS_BASED", "PLACEMENT"]:
            label = service.get_aggregation_label(scoring_type)
            assert label != "BEST_VALUE", (
                f"scoring_type='{scoring_type}' still returns 'BEST_VALUE' — BUG-03 not fully fixed. "
                f"Got: '{label}'"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 2. DEBT-01: RankingAggregator removed from SessionFinalizer  [GREEN]
# ─────────────────────────────────────────────────────────────────────────────

class TestDebt01AggregatorRemoved:
    """
    DEBT-01 fixed: RankingAggregator (deprecated) is no longer instantiated
    in SessionFinalizer.__init__(). Dead code removed.
    """

    def test_session_finalizer_has_no_ranking_aggregator_attribute(self):
        """
        SessionFinalizer.__init__() must NOT create self.ranking_aggregator.
        """
        from app.services.tournament.results.finalization.session_finalizer import SessionFinalizer
        finalizer = SessionFinalizer(MagicMock())
        assert not hasattr(finalizer, 'ranking_aggregator'), (
            "ranking_aggregator attribute found on SessionFinalizer — DEBT-01 fix was reverted. "
            "Remove 'self.ranking_aggregator = RankingAggregator()' from __init__."
        )

    def test_session_finalizer_has_ranking_service(self):
        """SessionFinalizer still has self.ranking_service (the modern replacement)."""
        from app.services.tournament.results.finalization.session_finalizer import SessionFinalizer
        finalizer = SessionFinalizer(MagicMock())
        assert hasattr(finalizer, 'ranking_service')
        assert isinstance(finalizer.ranking_service, RankingService)

    def test_ranking_aggregator_not_imported_in_session_finalizer(self):
        """
        RankingAggregator import removed from session_finalizer module.
        """
        import app.services.tournament.results.finalization.session_finalizer as mod
        assert not hasattr(mod, 'RankingAggregator'), (
            "RankingAggregator is still imported in session_finalizer — remove the import."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. BUG-03 end-to-end: aggregation_method in game_results JSONB  [GREEN]
# ─────────────────────────────────────────────────────────────────────────────

class TestBUG03AggregationMethodInGameResults:
    """
    BUG-03 end-to-end: game_results["aggregation_method"] written by
    SessionFinalizer.finalize() must reflect the actual strategy used.
    """

    def _build_mock_db(self):
        mock_db = MagicMock()
        inner = MagicMock()
        inner.filter.return_value = inner
        inner.count.return_value = 0
        inner.all.return_value = []
        mock_db.query.return_value.filter.return_value = inner
        mock_db.flush.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        return mock_db

    def _build_tournament(self, scoring_type, ranking_direction="DESC"):
        return SimpleNamespace(
            id=999, format="INDIVIDUAL_RANKING",
            scoring_type=scoring_type,
            ranking_direction=ranking_direction,
            measurement_unit="units",
            tournament_status="IN_PROGRESS",
        )

    def _build_session(self):
        return SimpleNamespace(
            id=111, semester_id=999,
            match_format="INDIVIDUAL_RANKING",
            game_results=None,
            rounds_data={
                "total_rounds": 1, "completed_rounds": 1,
                "round_results": {"1": {"101": "10", "102": "7"}},
            },
        )

    @pytest.mark.parametrize("scoring_type,ranking_direction,expected_label", [
        ("TIME_BASED",    "ASC",  "MIN_VALUE"),
        ("TIME_BASED",    "DESC", "MAX_VALUE"),
        ("SCORE_BASED",   "DESC", "SUM"),
        ("SCORE_BASED",   "ASC",  "SUM"),
        ("ROUNDS_BASED",  "DESC", "MAX_VALUE"),
        ("ROUNDS_BASED",  "ASC",  "MIN_VALUE"),
        ("PLACEMENT",     "ASC",  "SUM_PLACEMENT"),
    ])
    @patch("app.services.tournament.results.finalization.session_finalizer.calculate_ranks")
    @patch("app.services.tournament.results.finalization.session_finalizer.get_or_create_ranking")
    def test_aggregation_method_in_jsonb_matches_strategy(
        self, mock_get_or_create, mock_calculate_ranks,
        scoring_type, ranking_direction, expected_label
    ):
        """
        For each (scoring_type, ranking_direction) combination, the stored
        game_results["aggregation_method"] must reflect the actual aggregation.
        """
        from app.services.tournament.results.finalization.session_finalizer import SessionFinalizer
        mock_get_or_create.return_value = MagicMock(points=0)

        db = self._build_mock_db()
        tournament = self._build_tournament(scoring_type, ranking_direction)
        session = self._build_session()

        finalizer = SessionFinalizer(db)
        result = finalizer.finalize(tournament, session, recorded_by_id=1, recorded_by_name="Test")

        assert result["success"] is True
        stored = json.loads(session.game_results)
        assert stored["aggregation_method"] == expected_label, (
            f"scoring_type={scoring_type}, ranking_direction={ranking_direction}: "
            f"expected aggregation_method='{expected_label}', got '{stored['aggregation_method']}'. "
            f"BUG-03 may not be fully fixed."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Reward pathway consistency audit  [GREEN]
# ─────────────────────────────────────────────────────────────────────────────

class TestRewardPathwayConsistency:
    """
    Documents the reward distribution pathway for all three finalizer types.

    Design contract:
      IR  (Individual Ranking):   SessionFinalizer → NO reward auto-trigger.
                                  Admin must call TournamentFinalizer separately.
      H2H (Head-to-Head):         TournamentFinalizer.finalize() → auto-distributes rewards.
      GK  (Group+Knockout):       GroupStageFinalizer → sets seeding only.
                                  TournamentFinalizer called later → auto-distributes rewards.

    The only source of reward distribution is TournamentFinalizer.finalize().
    """

    # RP-01
    @patch("app.services.tournament.tournament_reward_orchestrator.distribute_rewards_for_tournament")
    @patch("app.services.tournament.results.finalization.session_finalizer.calculate_ranks")
    @patch("app.services.tournament.results.finalization.session_finalizer.get_or_create_ranking")
    def test_rp01_session_finalizer_never_distributes_rewards(
        self, mock_get_or_create, mock_calculate_ranks, mock_distribute
    ):
        """IR pathway: SessionFinalizer must NOT call distribute_rewards_for_tournament."""
        from app.services.tournament.results.finalization.session_finalizer import SessionFinalizer
        mock_get_or_create.return_value = MagicMock(points=0)

        mock_db = MagicMock()
        inner = MagicMock()
        inner.filter.return_value = inner
        inner.count.return_value = 0
        inner.all.return_value = []
        mock_db.query.return_value.filter.return_value = inner

        tournament = SimpleNamespace(
            id=1, format="INDIVIDUAL_RANKING", scoring_type="SCORE_BASED",
            ranking_direction="DESC", measurement_unit="pts", tournament_status="IN_PROGRESS"
        )
        session = SimpleNamespace(
            id=10, semester_id=1, match_format="INDIVIDUAL_RANKING", game_results=None,
            rounds_data={"total_rounds": 1, "completed_rounds": 1,
                         "round_results": {"1": {"1": "5", "2": "3"}}}
        )

        SessionFinalizer(mock_db).finalize(tournament, session, 1, "Test")
        mock_distribute.assert_not_called()

    # RP-02
    def test_rp02_tournament_finalizer_calls_distribute_rewards_on_success(self):
        """
        H2H pathway: TournamentFinalizer.finalize() MUST call distribute_rewards_for_tournament
        after successfully updating tournament_status to COMPLETED.

        We verify this by patching the orchestrator at the lazy import path and
        confirming it IS called (the opposite of the IR test).
        """
        from app.services.tournament.results.finalization.tournament_finalizer import TournamentFinalizer

        mock_db = MagicMock()

        # Sessions with game_results set (all complete)
        mock_session = MagicMock()
        mock_session.game_results = '{"derived_rankings": [{"rank": 1, "user_id": 1}, {"rank": 2, "user_id": 2}]}'
        mock_session.match_format = "HEAD_TO_HEAD"
        mock_session.semester_id = 99
        mock_session.tournament_phase.value = "KNOCKOUT"

        # final match and 3rd-place match
        final_session = MagicMock()
        final_session.game_results = json.dumps({
            "derived_rankings": [
                {"rank": 1, "user_id": 10},
                {"rank": 2, "user_id": 11},
            ]
        })
        third_session = MagicMock()
        third_session.game_results = json.dumps({
            "derived_rankings": [{"rank": 1, "user_id": 12}]
        })

        # Mock DB: all_sessions query, final/3rd match queries, enrollment query
        # R01 fix: finalize() now re-fetches tournament with FOR UPDATE at start.
        # The locked tournament must have id=99, tournament_status="IN_PROGRESS" (not finalized).
        locked_tournament = SimpleNamespace(id=99, tournament_status="IN_PROGRESS")

        def _query_side(model):
            q = MagicMock()
            inner = MagicMock()
            inner.filter.return_value = inner
            inner.all.return_value = [mock_session]
            inner.first.return_value = None  # no final/3rd match found (simplify)
            inner.count.return_value = 0
            # Support .with_for_update().one() for the R01 tournament row lock
            inner.with_for_update.return_value.one.return_value = locked_tournament
            q.filter.return_value = inner
            return q
        mock_db.query.side_effect = _query_side
        mock_db.flush.return_value = None
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None

        tournament = SimpleNamespace(id=99, tournament_status="IN_PROGRESS")

        # patch and MagicMock are already imported at module level — no local re-import
        mock_reward_result = MagicMock()
        mock_reward_result.rewards_distributed = [1, 2, 3]

        # tournament_finalizer.py lazy-imports distribute_rewards_for_tournament inside
        # finalize() — patch at canonical source so the lazy import picks up the mock.
        with patch(
            "app.services.tournament.tournament_reward_orchestrator."
            "distribute_rewards_for_tournament",
            return_value=mock_reward_result
        ) as mock_distribute:
            result = TournamentFinalizer(mock_db).finalize(tournament)

        mock_distribute.assert_called_once_with(db=mock_db, tournament_id=99), (
            "TournamentFinalizer.finalize() must call distribute_rewards_for_tournament "
            "exactly once after setting tournament_status=COMPLETED."
        )

    # RP-03
    def test_rp03_ir_tournament_finalizer_check_accepts_complete_ir_sessions(self):
        """
        IR tournament can be finalized via TournamentFinalizer.finalize() if:
          (a) rounds_data shows all rounds completed, OR
          (b) TournamentRanking rows already exist (from SessionFinalizer)

        This test documents that the TournamentFinalizer can serve as the
        reward-trigger for IR tournaments even though SessionFinalizer doesn't.
        """
        from app.services.tournament.results.finalization.tournament_finalizer import TournamentFinalizer

        mock_db = MagicMock()

        # IR session: no game_results, but rounds_data complete
        ir_session = MagicMock()
        ir_session.game_results = None
        ir_session.match_format = "INDIVIDUAL_RANKING"
        ir_session.semester_id = 100
        ir_session.rounds_data = {"total_rounds": 3, "completed_rounds": 3}

        def _query_side(model):
            from app.models.tournament_ranking import TournamentRanking
            q = MagicMock()
            inner = MagicMock()
            inner.filter.return_value = inner
            if model is TournamentRanking:
                inner.count.return_value = 5  # TournamentRanking rows exist
            else:
                inner.count.return_value = 0
            inner.all.return_value = [ir_session]
            q.filter.return_value = inner
            return q
        mock_db.query.side_effect = _query_side

        finalizer = TournamentFinalizer(mock_db)
        all_completed, incomplete = finalizer.check_all_matches_completed([ir_session])

        assert all_completed is True, (
            "IR session with TournamentRanking rows should be accepted as complete. "
            f"Incomplete: {incomplete}"
        )
        assert incomplete == []

    # RP-04
    def test_rp04_group_stage_finalizer_does_not_call_distribute_rewards(self):
        """
        GroupStageFinalizer.finalize() must NOT distribute rewards.
        It only seeds knockout sessions — reward distribution happens later via TournamentFinalizer.
        """
        from app.services.tournament.results.finalization.group_stage_finalizer import GroupStageFinalizer

        mock_db = MagicMock()

        # Group session with game_results (complete)
        group_session = MagicMock()
        group_session.game_results = json.dumps({
            "raw_results": [
                {"user_id": 1, "score": 3},
                {"user_id": 2, "score": 1}
            ]
        })
        group_session.group_identifier = "Group A"
        group_session.participant_user_ids = [1, 2]
        group_session.tournament_phase = MagicMock()
        group_session.tournament_phase.value = "GROUP_STAGE"

        inner = MagicMock()
        inner.filter.return_value = inner
        inner.order_by.return_value = inner
        inner.all.return_value = [group_session]
        mock_db.query.return_value = inner
        mock_db.query.return_value.filter.return_value = inner

        tournament = SimpleNamespace(
            id=50, tournament_config_obj=MagicMock()
        )

        with patch(
            "app.services.tournament.tournament_reward_orchestrator.distribute_rewards_for_tournament"
        ) as mock_distribute:
            with patch(
                "app.services.tournament.results.finalization.group_stage_finalizer."
                "StandingsCalculator.calculate_group_standings",
                return_value={}
            ):
                with patch(
                    "app.services.tournament.results.finalization.group_stage_finalizer."
                    "AdvancementCalculator.calculate_advancement",
                    return_value=([], 0)
                ):
                    GroupStageFinalizer(mock_db).finalize(tournament)

        mock_distribute.assert_not_called(), (
            "GroupStageFinalizer must NOT call distribute_rewards_for_tournament. "
            "Only TournamentFinalizer does."
        )

    # RP-05: Design invariant document
    def test_rp05_reward_distribution_call_sites_are_known_and_intentional(self):
        """
        Documents the design invariant: distribute_rewards_for_tournament has exactly
        TWO legitimate call sites in production code:

          1. TournamentFinalizer.finalize()  — automatic, triggered during match result submission
          2. rewards_v2.py POST /{id}/rewards — manual admin API endpoint for already-COMPLETED
                                                 tournaments (explicit re-trigger / override)

        Any additional call site is a bug — it would mean reward logic leaked into an
        unexpected layer (e.g., session_finalizer, group_stage_finalizer, a Celery task).

        This is verified by source inspection.
        """
        import pathlib

        reward_callers = []
        source_root = pathlib.Path(__file__).parent.parent.parent.parent / "app"

        for py_file in source_root.rglob("*.py"):
            try:
                text = py_file.read_text()
            except Exception:
                continue
            for line in text.splitlines():
                stripped = line.strip()
                if (
                    "distribute_rewards_for_tournament(" in stripped
                    and not stripped.startswith("#")
                    and "def " not in stripped
                    and "import " not in stripped
                ):
                    reward_callers.append(f"{py_file.relative_to(source_root.parent)}: {stripped}")

        prod_callers = [c for c in reward_callers if "test" not in c.lower()]

        # Two known, intentional call sites
        EXPECTED_CALL_SITES = {"tournament_finalizer", "rewards_v2"}

        assert len(prod_callers) == len(EXPECTED_CALL_SITES), (
            f"Expected exactly {len(EXPECTED_CALL_SITES)} production call sites for "
            f"distribute_rewards_for_tournament, found {len(prod_callers)}:\n"
            + "\n".join(prod_callers)
        )

        for caller in prod_callers:
            assert any(site in caller for site in EXPECTED_CALL_SITES), (
                f"Unexpected call site for distribute_rewards_for_tournament: {caller}\n"
                f"Only {EXPECTED_CALL_SITES} are permitted."
            )
