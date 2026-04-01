"""
Ranking Service

Modern replacement for RankingAggregator using Strategy Pattern.

This service:
1. Uses RankingStrategyFactory to get the correct strategy
2. Delegates ranking calculation to the strategy
3. Returns normalized RankGroup output with proper tied ranks

Replaces: app/services/tournament/results/calculators/ranking_aggregator.py
"""
import logging
from typing import Dict, List, Any, Tuple
from .strategies import RankingStrategyFactory, RankGroup

logger = logging.getLogger(__name__)


def calculate_and_store_rankings(db, tournament_id: int) -> dict:
    """
    Calculate and persist tournament rankings.

    Callable from within request handlers and background triggers
    (no HTTP context needed — raises ValueError instead of HTTPException).

    Returns {"rankings_count": N, "tournament_format": "..."}.
    Raises ValueError on any validation or strategy failure.
    """
    from sqlalchemy import and_
    from app.models.semester import Semester
    from app.models.session import Session as SessionModel, EventCategory
    from app.models.tournament_ranking import TournamentRanking

    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    tournament_format = tournament.format  # "INDIVIDUAL_RANKING" or "HEAD_TO_HEAD"

    all_sessions = db.query(SessionModel).filter(
        and_(
            SessionModel.semester_id == tournament_id,
            SessionModel.event_category == EventCategory.MATCH,
        )
    ).all()
    if not all_sessions:
        raise ValueError("No tournament sessions found. Generate sessions first.")

    tournament_type_code = None
    if tournament.tournament_config_obj and tournament.tournament_config_obj.tournament_type:
        tournament_type_code = tournament.tournament_config_obj.tournament_type.code

    # Swiss: no strategy available
    if tournament_type_code == "swiss":
        raise ValueError(
            "Swiss format does not support automatic ranking calculation. "
            "Rankings must be entered manually."
        )

    # Group+knockout: validate group stage only, pass all sessions to strategy
    if tournament_type_code == "group_knockout":
        group_sessions = [s for s in all_sessions if s.tournament_phase == "GROUP_STAGE"]
        knockout_sessions = [
            s for s in all_sessions
            if s.tournament_phase == "KNOCKOUT" and s.game_results
        ]
        if not group_sessions:
            raise ValueError("No GROUP_STAGE sessions found. Cannot calculate rankings.")
        missing = [s for s in group_sessions if not s.game_results]
        if missing:
            raise ValueError(f"{len(missing)} GROUP_STAGE session(s) do not have results yet.")
        sessions = group_sessions + knockout_sessions
    else:
        sessions = all_sessions
        sessions_with_results = [
            s for s in sessions
            if s.game_results or (s.rounds_data and s.rounds_data.get("round_results"))
        ]
        if len(sessions_with_results) < len(sessions):
            missing_count = len(sessions) - len(sessions_with_results)
            raise ValueError(
                f"{missing_count} session(s) do not have results submitted yet."
            )

    cfg = tournament.tournament_config_obj
    is_team = cfg and cfg.participant_type == "TEAM"
    ranking_direction = (cfg.ranking_direction or "ASC") if cfg else "ASC"
    pt_label = "TEAM" if is_team else "INDIVIDUAL"

    if tournament_format == "HEAD_TO_HEAD":
        if is_team:
            # TEAM HEAD_TO_HEAD: results stored in rounds_data (game_results is NULL).
            # Compute W/D/L points from per-session team scores.
            from collections import defaultdict as _dd
            team_stats: dict = _dd(lambda: {
                "points": 0, "wins": 0, "ties": 0, "losses": 0,
                "goals_scored": 0.0, "goals_conceded": 0.0,
            })
            for s in sessions:
                for round_data in (s.rounds_data or {}).get("round_results", {}).values():
                    team_scores: dict = {}
                    for key, val in (round_data or {}).items():
                        if key.startswith("team_"):
                            try:
                                tid = int(key.split("_", 1)[1])
                                team_scores[tid] = float(val)
                            except (ValueError, IndexError):
                                pass
                    if len(team_scores) != 2:
                        continue
                    (t1, s1), (t2, s2) = list(team_scores.items())
                    team_stats[t1]["goals_scored"] += s1
                    team_stats[t1]["goals_conceded"] += s2
                    team_stats[t2]["goals_scored"] += s2
                    team_stats[t2]["goals_conceded"] += s1
                    if s1 > s2:
                        team_stats[t1]["points"] += 3
                        team_stats[t1]["wins"] += 1
                        team_stats[t2]["losses"] += 1
                    elif s2 > s1:
                        team_stats[t2]["points"] += 3
                        team_stats[t2]["wins"] += 1
                        team_stats[t1]["losses"] += 1
                    else:
                        team_stats[t1]["points"] += 1
                        team_stats[t1]["ties"] += 1
                        team_stats[t2]["points"] += 1
                        team_stats[t2]["ties"] += 1
            if not team_stats:
                raise ValueError("No round results found in TEAM HEAD_TO_HEAD sessions.")
            ranked_teams = sorted(
                team_stats.items(),
                key=lambda x: (
                    -x[1]["points"],
                    -(x[1]["goals_scored"] - x[1]["goals_conceded"]),
                    -x[1]["goals_scored"],
                ),
            )
            rankings = [
                {
                    "team_id": tid, "user_id": None, "rank": i + 1,
                    "points": st["points"], "wins": st["wins"],
                    "ties": st["ties"], "losses": st["losses"],
                    "goals_for": st["goals_scored"], "goals_against": st["goals_conceded"],
                }
                for i, (tid, st) in enumerate(ranked_teams)
            ]
        else:
            strategy = RankingStrategyFactory.create(
                tournament_format="HEAD_TO_HEAD",
                tournament_type_code=tournament_type_code,
            )
            rankings = strategy.calculate_rankings(sessions, db)
    else:
        if is_team:
            combined: dict = {}
            for s in sessions:
                for rk, pv in (s.rounds_data or {}).get("round_results", {}).items():
                    if isinstance(pv, dict):
                        combined.setdefault(rk, {}).update(pv)
            if not combined:
                raise ValueError("No round results found in sessions.")
            team_scores: dict = {}
            for pv in combined.values():
                for key, val in pv.items():
                    if key.startswith("team_"):
                        try:
                            tid = int(key.split("_", 1)[1])
                            team_scores[tid] = team_scores.get(tid, 0.0) + float(val)
                        except (ValueError, IndexError):
                            pass
            ranked = sorted(
                team_scores.items(),
                key=lambda x: x[1],
                reverse=(ranking_direction == "DESC"),
            )
            rankings = [
                {"team_id": tid, "user_id": None, "rank": i + 1, "points": score}
                for i, (tid, score) in enumerate(ranked)
            ]
        else:
            from app.services.tournament.results.calculators.ranking_aggregator import RankingAggregator
            combined = {}
            for s in sessions:
                for rk, pv in (s.rounds_data or {}).get("round_results", {}).items():
                    if isinstance(pv, dict):
                        combined.setdefault(rk, {}).update(pv)
            if not combined:
                raise ValueError("No round results found in sessions.")
            finals = RankingAggregator.aggregate_user_values(combined, ranking_direction)
            perf = RankingAggregator.calculate_performance_rankings(finals, ranking_direction)
            rankings = [
                {"user_id": r["user_id"], "team_id": None, "rank": r["rank"], "points": r["final_value"]}
                for r in perf
            ]

    # Delete existing + insert new (idempotent)
    db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).delete()

    for rd in rankings:
        db.add(TournamentRanking(
            tournament_id=tournament_id,
            user_id=rd.get("user_id"),
            team_id=rd.get("team_id"),
            participant_type=pt_label,
            rank=rd["rank"],
            points=rd.get("points", 0),
            wins=rd.get("wins", 0),
            losses=rd.get("losses", 0),
            draws=rd.get("ties", 0),
            goals_for=rd.get("goals_for", rd.get("goals_scored", 0)),
            goals_against=rd.get("goals_against", rd.get("goals_conceded", 0)),
        ))
    db.flush()

    logger.info(
        f"[calculate_and_store_rankings] tournament_id={tournament_id} "
        f"format={tournament_format} rankings_count={len(rankings)}"
    )
    return {"rankings_count": len(rankings), "tournament_format": tournament_format}


class RankingService:
    """
    Modern ranking service using Strategy Pattern.

    Usage:
        service = RankingService()
        rank_groups = service.calculate_rankings(
            scoring_type="ROUNDS_BASED",
            round_results=round_results,
            participants=participants
        )
    """

    def calculate_rankings(
        self,
        scoring_type: str,
        round_results: Dict[str, Dict[str, str]],
        participants: List[Dict[str, Any]],
        ranking_direction: str = None
    ) -> List[RankGroup]:
        """
        Calculate rankings using the appropriate strategy.

        Args:
            scoring_type: One of 'TIME_BASED', 'SCORE_BASED', 'ROUNDS_BASED', 'PLACEMENT'
            round_results: {"1": {"13": "11 pts", ...}, "2": {...}, ...}
            participants: [{"user_id": 13, ...}, ...]
            ranking_direction: Optional override — 'ASC' (lower=better) or 'DESC' (higher=better).
                If None, each strategy uses its hardcoded default direction.
                Fixed: previously ignored (BUG-01). Now forwarded to the strategy.

        Returns:
            List[RankGroup] with proper tied ranks
        """
        # Get the appropriate strategy
        strategy = RankingStrategyFactory.create(scoring_type)

        # Calculate rankings — forward ranking_direction so strategies can override direction
        return strategy.calculate_rankings(round_results, participants, ranking_direction=ranking_direction)

    def get_aggregation_label(
        self,
        scoring_type: str,
        ranking_direction: str = None
    ) -> str:
        """
        Return the aggregation method label for a given scoring_type and direction.

        Used to populate session.game_results["aggregation_method"] accurately (fixes BUG-03).

        Args:
            scoring_type: e.g. 'TIME_BASED', 'SCORE_BASED', 'ROUNDS_BASED', 'PLACEMENT'
            ranking_direction: Optional 'ASC' or 'DESC' override

        Returns:
            Label string: 'MIN_VALUE', 'MAX_VALUE', 'SUM', 'SUM_PLACEMENT'
        """
        strategy = RankingStrategyFactory.create(scoring_type)
        return strategy.get_aggregation_label(ranking_direction=ranking_direction)

    def convert_to_legacy_format(
        self,
        rank_groups: List[RankGroup],
        measurement_unit: str = "units"
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Convert RankGroup output to legacy format for backward compatibility.

        This is TEMPORARY to maintain compatibility with existing code.
        Eventually, all code should work with RankGroup directly.

        Args:
            rank_groups: List of RankGroup objects
            measurement_unit: Unit label (e.g., "seconds", "points")

        Returns:
            Tuple of (performance_rankings, wins_rankings)
            - performance_rankings: Legacy format with individual ranks
            - wins_rankings: Empty list (not used in modern flow)
        """
        performance_rankings = []

        for rank_group in rank_groups:
            for user_id in rank_group.participants:
                performance_rankings.append({
                    "user_id": user_id,
                    "rank": rank_group.rank,
                    "final_value": rank_group.final_value,
                    "measurement_unit": measurement_unit,
                    "is_tied": rank_group.is_tied()
                })

        # wins_rankings not used in modern flow
        wins_rankings = []

        return performance_rankings, wins_rankings
