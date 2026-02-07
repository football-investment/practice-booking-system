"""
Result Processor Service

Converts structured performance data into derived rankings.

This service sits between raw match results and the points calculation system,
providing a clean separation between:
    - Performance input (scores, times, ratings)
    - Ranking derivation (who placed where)
    - Points calculation (how many points earned)

Architecture Flow:
    Match Results → ResultProcessor → Derived Rankings → PointsCalculatorService → Tournament Points
"""
from typing import List, Tuple, Dict, Optional, Protocol, Any
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal

from app.models.match_structure import MatchFormat, ScoringType, MatchStructure, MatchResult
from app.models.session import Session as SessionModel
from app.models.semester import Semester
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_enums import TournamentPhase
from app.services.tournament.leaderboard_service import get_or_create_ranking, calculate_ranks


# ============================================================================
# Extension Point: SKILL_RATING Processor Interface
# ============================================================================

class SkillRatingProcessor(Protocol):
    """
    🔌 EXTENSION POINT: Interface for SKILL_RATING processing

    This interface defines the contract for custom SKILL_RATING processors.
    Business logic for rating criteria, scoring scales, and ranking derivation
    will be implemented later.

    When ready to implement:
    1. Create a concrete class implementing this interface
    2. Define rating criteria and scales
    3. Implement ranking derivation logic
    4. Inject into ResultProcessor via set_skill_rating_processor()

    Example future implementation:
        class LFASkillRatingProcessor(SkillRatingProcessor):
            def derive_rankings(self, results: List[Dict]) -> List[Tuple[int, int]]:
                # Custom business logic here
                # Consider: technique, speed, accuracy weighted scoring
                # Return: [(user_id, rank), ...]
                pass
    """

    def derive_rankings(
        self,
        results: List[Dict],
        structure_config: Optional[Dict] = None
    ) -> List[Tuple[int, int]]:
        """
        Derive rankings from skill rating performance data.

        Args:
            results: List of performance data dicts with skill ratings
                Example: [{"user_id": 1, "rating": 9.5, "criteria_scores": {...}}]
            structure_config: Optional match structure configuration

        Returns:
            List of (user_id, rank) tuples sorted by rank
        """
        ...


class NotImplementedSkillRatingProcessor:
    """
    Default stub for SKILL_RATING processor.

    This placeholder raises an error if SKILL_RATING is used before
    the actual processor is implemented and injected.
    """

    def derive_rankings(
        self,
        results: List[Dict],
        structure_config: Optional[Dict] = None
    ) -> List[Tuple[int, int]]:
        raise NotImplementedError(
            "SKILL_RATING processor not yet implemented. "
            "Business logic for rating criteria and ranking derivation is pending. "
            "To implement: Create a SkillRatingProcessor and inject via "
            "result_processor.set_skill_rating_processor(custom_processor)"
        )


# ============================================================================
# Result Processor Service
# ============================================================================

class ResultProcessor:
    """
    Processes match results and derives rankings based on match format.

    Supports multiple match formats:
    - INDIVIDUAL_RANKING: Direct placement → ranking
    - HEAD_TO_HEAD: Winner/loser or score-based → ranking
    - TEAM_MATCH: Team scores → individual rankings
    - TIME_BASED: Performance times → ranking (fastest = 1st)
    - SKILL_RATING: Rating scores → ranking (🔌 Extension point)
    """

    def __init__(self, db: Session):
        self.db = db
        # 🔌 Extension point: SKILL_RATING processor (default: not implemented)
        self._skill_rating_processor: SkillRatingProcessor = NotImplementedSkillRatingProcessor()

    # ========================================================================
    # Extension Point Injection
    # ========================================================================

    def set_skill_rating_processor(self, processor: SkillRatingProcessor):
        """
        Inject a custom SKILL_RATING processor.

        This allows the business logic for skill ratings to be implemented
        and injected later without modifying the core ResultProcessor.

        Usage:
            custom_processor = LFASkillRatingProcessor()
            result_processor.set_skill_rating_processor(custom_processor)
        """
        self._skill_rating_processor = processor

    # ========================================================================
    # Main Match Results Processing (with TournamentRanking updates)
    # ========================================================================

    def process_match_results(
        self,
        db: Session,
        session: SessionModel,
        tournament: Semester,
        raw_results: List[Dict[str, Any]],
        match_notes: Optional[str] = None,
        recorded_by_user_id: Optional[int] = None,
        recorded_by_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process match results and update TournamentRanking table.

        This is the main entry point for recording match results. It:
        1. Validates raw results based on tournament format
        2. For INDIVIDUAL_RANKING: Stores measured values directly in TournamentRanking.points
        3. For HEAD_TO_HEAD: Derives rankings and calculates points
        4. Updates session.game_results JSONB field
        5. Recalculates tournament ranks

        Args:
            db: Database session
            session: Tournament session/match
            tournament: Tournament (Semester)
            raw_results: Raw result data (format depends on tournament.format)
            match_notes: Optional notes about the match
            recorded_by_user_id: ID of user recording results
            recorded_by_name: Name of user recording results

        Returns:
            Dict with derived_rankings and metadata
        """
        tournament_format = tournament.format or "HEAD_TO_HEAD"
        match_format = session.match_format or "INDIVIDUAL_RANKING"

        # Handle INDIVIDUAL_RANKING tournaments (measured values)
        if tournament_format == "INDIVIDUAL_RANKING":
            return self._process_individual_ranking_tournament(
                db=db,
                session=session,
                tournament=tournament,
                raw_results=raw_results,
                match_notes=match_notes,
                recorded_by_user_id=recorded_by_user_id,
                recorded_by_name=recorded_by_name
            )

        # Handle HEAD_TO_HEAD tournaments (match results)
        elif tournament_format == "HEAD_TO_HEAD":
            return self._process_head_to_head_tournament(
                db=db,
                session=session,
                tournament=tournament,
                raw_results=raw_results,
                match_notes=match_notes,
                recorded_by_user_id=recorded_by_user_id,
                recorded_by_name=recorded_by_name
            )

        else:
            raise ValueError(f"Unsupported tournament format: {tournament_format}")

    def _process_individual_ranking_tournament(
        self,
        db: Session,
        session: SessionModel,
        tournament: Semester,
        raw_results: List[Dict[str, Any]],
        match_notes: Optional[str] = None,
        recorded_by_user_id: Optional[int] = None,
        recorded_by_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process INDIVIDUAL_RANKING tournament results.

        For INDIVIDUAL_RANKING tournaments, the instructor records measured performance values
        (e.g., "10.5 seconds", "95 points", "15.2 meters") which are stored directly
        in TournamentRanking.points. The ranking is then calculated based on ranking_direction.

        Input format:
            [
                {"user_id": 1, "measured_value": 10.5},  # e.g., 10.5 seconds
                {"user_id": 2, "measured_value": 11.2},  # e.g., 11.2 seconds
                {"user_id": 3, "measured_value": 10.8},  # e.g., 10.8 seconds
            ]

        Args:
            db: Database session
            session: Tournament session
            tournament: Tournament (Semester)
            raw_results: List of {user_id, measured_value}
            match_notes: Optional notes
            recorded_by_user_id: Recorder ID
            recorded_by_name: Recorder name

        Returns:
            Dict with derived_rankings and metadata
        """
        # Validate input format
        for result in raw_results:
            if "user_id" not in result or "measured_value" not in result:
                raise ValueError(
                    "INDIVIDUAL_RANKING results must include 'user_id' and 'measured_value'. "
                    f"Example: [{{'user_id': 1, 'measured_value': 10.5}}]"
                )

        # Store measured values in TournamentRanking.points
        for result in raw_results:
            user_id = result["user_id"]
            measured_value = result["measured_value"]

            # Get or create ranking entry
            ranking = get_or_create_ranking(
                db=db,
                tournament_id=tournament.id,
                user_id=user_id,
                participant_type="INDIVIDUAL"
            )

            # Store measured value directly in points field
            ranking.points = Decimal(str(measured_value))

        db.flush()

        # Recalculate ranks based on measured values and ranking_direction
        calculate_ranks(db, tournament.id)

        # Get updated rankings for response
        rankings_updated = db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament.id,
            TournamentRanking.user_id.in_([r["user_id"] for r in raw_results])
        ).all()

        derived_rankings = [
            {
                "user_id": ranking.user_id,
                "rank": ranking.rank,
                "measured_value": float(ranking.points)
            }
            for ranking in rankings_updated
        ]

        # Store results in session.game_results
        recorded_at = datetime.utcnow().isoformat()
        game_results = {
            "recorded_at": recorded_at,
            "recorded_by": recorded_by_user_id,
            "recorded_by_name": recorded_by_name,
            "match_notes": match_notes,
            "tournament_format": "INDIVIDUAL_RANKING",
            "measurement_unit": tournament.measurement_unit,
            "ranking_direction": tournament.ranking_direction,
            "raw_results": raw_results,
            "derived_rankings": derived_rankings
        }

        import json
        session.game_results = json.dumps(game_results)

        db.flush()

        return {
            "derived_rankings": derived_rankings,
            "recorded_at": recorded_at
        }

    def _process_head_to_head_tournament(
        self,
        db: Session,
        session: SessionModel,
        tournament: Semester,
        raw_results: List[Dict[str, Any]],
        match_notes: Optional[str] = None,
        recorded_by_user_id: Optional[int] = None,
        recorded_by_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process HEAD_TO_HEAD tournament results.

        For HEAD_TO_HEAD tournaments, the system derives rankings from match results
        and calculates points based on placement.

        Args:
            db: Database session
            session: Tournament session
            tournament: Tournament (Semester)
            raw_results: Match result data
            match_notes: Optional notes
            recorded_by_user_id: Recorder ID
            recorded_by_name: Recorder name

        Returns:
            Dict with derived_rankings and metadata
        """
        # Use existing process_results logic for HEAD_TO_HEAD
        match_format = session.match_format or "HEAD_TO_HEAD"

        # Derive rankings from match results
        rankings = self.process_results(
            session_id=session.id,
            match_format=match_format,
            results=raw_results
        )

        # Calculate and store points
        from app.services.tournament.points_calculator_service import PointsCalculatorService
        points_calculator = PointsCalculatorService(db)

        # Extract scores from raw_results if SCORE_BASED
        scores_map = {}
        if raw_results and len(raw_results) > 0 and "score" in raw_results[0]:
            for result in raw_results:
                scores_map[result["user_id"]] = {
                    "goals_for": result.get("score", 0),
                    "goals_against": result.get("opponent_score", 0)
                }

        for user_id, rank in rankings:
            points = points_calculator.calculate_points(
                session_id=session.id,
                user_id=user_id,
                rank=rank
            )

            # Get or create ranking entry
            ranking = get_or_create_ranking(
                db=db,
                tournament_id=tournament.id,
                user_id=user_id,
                participant_type="INDIVIDUAL"
            )

            # Add points to total
            ranking.points += Decimal(str(points))

            # Update wins/losses/draws based on rank
            if len(rankings) == 2:  # HEAD_TO_HEAD 1v1
                if rank == 1:
                    ranking.wins += 1
                elif rank == 2:
                    ranking.losses += 1
                else:
                    # Both rank 1 = tie
                    ranking.draws += 1

            # Update goals for/against if SCORE_BASED
            if user_id in scores_map:
                ranking.goals_for += scores_map[user_id]["goals_for"]
                ranking.goals_against += scores_map[user_id]["goals_against"]

        db.flush()

        # Recalculate ranks
        calculate_ranks(db, tournament.id)

        # Get updated rankings for response
        rankings_updated = db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament.id,
            TournamentRanking.user_id.in_([user_id for user_id, _ in rankings])
        ).all()

        derived_rankings = [
            {
                "user_id": ranking.user_id,
                "rank": ranking.rank,
                "points": float(ranking.points)
            }
            for ranking in rankings_updated
        ]

        # Store results in session.game_results
        recorded_at = datetime.utcnow().isoformat()
        game_results = {
            "recorded_at": recorded_at,
            "recorded_by": recorded_by_user_id,
            "recorded_by_name": recorded_by_name,
            "match_notes": match_notes,
            "tournament_format": "HEAD_TO_HEAD",
            "raw_results": raw_results,
            "derived_rankings": derived_rankings
        }

        import json
        session.game_results = json.dumps(game_results)

        db.flush()

        # ========================================================================
        # KNOCKOUT PROGRESSION: Auto-create next round matches
        # ========================================================================
        knockout_info = None
        # ✅ Support both enum and legacy string values for backward compatibility
        if session.tournament_phase == TournamentPhase.KNOCKOUT:
            from app.services.tournament.knockout_progression_service import KnockoutProgressionService
            knockout_service = KnockoutProgressionService(db)
            knockout_info = knockout_service.process_knockout_progression(
                session=session,
                tournament=tournament,
                game_results=game_results
            )

        result = {
            "derived_rankings": derived_rankings,
            "recorded_at": recorded_at
        }

        # Include knockout progression info if available
        if knockout_info:
            result["knockout_progression"] = knockout_info

        return result

    # ========================================================================
    # Legacy Processing Method (for non-tournament contexts)
    # ========================================================================

    def process_results(
        self,
        session_id: int,
        match_format: str,
        results: List[Dict],
        structure_config: Optional[Dict] = None
    ) -> List[Tuple[int, int]]:
        """
        Process results based on match format and return derived rankings.

        Args:
            session_id: Session ID
            match_format: Match format type (INDIVIDUAL_RANKING, HEAD_TO_HEAD, etc.)
            results: List of result dicts (format depends on match_format)
            structure_config: Optional match structure configuration

        Returns:
            List of (user_id, rank) tuples

        Raises:
            ValueError: If match_format is invalid or results are malformed
            NotImplementedError: If SKILL_RATING is used without processor
        """
        # Convert string to enum
        try:
            format_enum = MatchFormat(match_format)
        except ValueError:
            raise ValueError(f"Invalid match_format: {match_format}")

        # Dispatch to appropriate processor
        if format_enum == MatchFormat.INDIVIDUAL_RANKING:
            return self._process_individual_ranking(results)

        elif format_enum == MatchFormat.HEAD_TO_HEAD:
            return self._process_head_to_head(results)

        elif format_enum == MatchFormat.TEAM_MATCH:
            return self._process_team_match(results, structure_config)

        elif format_enum == MatchFormat.TIME_BASED:
            return self._process_time_based(results)

        elif format_enum == MatchFormat.SKILL_RATING:
            # 🔌 Extension point: Delegate to injected processor
            return self._skill_rating_processor.derive_rankings(results, structure_config)

        else:
            raise ValueError(f"Unsupported match_format: {match_format}")

    # ========================================================================
    # Format-Specific Processors
    # ========================================================================

    def _process_individual_ranking(self, results: List[Dict]) -> List[Tuple[int, int]]:
        """
        Process INDIVIDUAL_RANKING results.

        Supports two input formats:
        1. PLACEMENT-BASED (legacy):
            [{"user_id": 1, "placement": 1}, {"user_id": 2, "placement": 2}, ...]

        2. SCORE-BASED ROUND-ROBIN (new):
            [{"player_a_id": 1, "player_b_id": 2, "score_a": 3, "score_b": 0}, ...]

        Returns:
            [(user_id, rank), ...] sorted by rank
        """
        # Check if this is score-based round-robin format
        if results and "player_a_id" in results[0]:
            return self._process_round_robin_scores(results)

        # Legacy placement-based format
        rankings = []
        for result in results:
            user_id = result.get("user_id")
            placement = result.get("placement")

            if user_id is None or placement is None:
                raise ValueError(f"Invalid INDIVIDUAL_RANKING result: {result}")

            rankings.append((user_id, placement))

        # Sort by rank (ascending)
        rankings.sort(key=lambda x: x[1])
        return rankings

    def _process_round_robin_scores(self, match_results: List[Dict]) -> List[Tuple[int, int]]:
        """
        Process round-robin score-based results.

        Input format:
            [
                {"player_a_id": 1, "player_b_id": 2, "score_a": 3, "score_b": 0},
                {"player_a_id": 1, "player_b_id": 3, "score_a": 2, "score_b": 2},
                {"player_a_id": 2, "player_b_id": 3, "score_a": 3, "score_b": 1},
                ...
            ]

        Logic:
            - Win (score_a > score_b): 3 points
            - Draw (score_a == score_b): 1 point
            - Loss (score_a < score_b): 0 points

        Returns:
            [(user_id, rank), ...] sorted by total points (descending)
        """
        # Calculate points for each player
        player_points = {}

        for match in match_results:
            player_a_id = match.get("player_a_id")
            player_b_id = match.get("player_b_id")
            score_a = match.get("score_a", 0)
            score_b = match.get("score_b", 0)

            if player_a_id is None or player_b_id is None:
                raise ValueError(f"Invalid round-robin result: {match}")

            # Initialize players if not seen
            if player_a_id not in player_points:
                player_points[player_a_id] = 0
            if player_b_id not in player_points:
                player_points[player_b_id] = 0

            # Award points based on score
            if score_a > score_b:
                # Player A wins
                player_points[player_a_id] += 3
            elif score_b > score_a:
                # Player B wins
                player_points[player_b_id] += 3
            else:
                # Draw
                player_points[player_a_id] += 1
                player_points[player_b_id] += 1

        # Sort by points (descending) and assign ranks
        sorted_players = sorted(player_points.items(), key=lambda x: x[1], reverse=True)

        # Assign ranks (handle ties by giving same rank)
        rankings = []
        current_rank = 1
        prev_points = None

        for i, (user_id, points) in enumerate(sorted_players):
            if prev_points is not None and points < prev_points:
                current_rank = i + 1
            rankings.append((user_id, current_rank))
            prev_points = points

        # Sort by rank for consistent output
        rankings.sort(key=lambda x: x[1])
        return rankings

    def _process_head_to_head(self, results: List[Dict]) -> List[Tuple[int, int]]:
        """
        Process HEAD_TO_HEAD results.

        Supports two scoring types:
        1. WIN_LOSS: {"user_id": 1, "result": "WIN"} or "LOSS"
        2. SCORE_BASED: {"user_id": 1, "score": 3, "opponent_score": 1}

        Returns:
            [(winner_user_id, 1), (loser_user_id, 2)]
        """
        if len(results) != 2:
            raise ValueError(f"HEAD_TO_HEAD requires exactly 2 results, got {len(results)}")

        # Check scoring type
        if "result" in results[0]:
            # WIN_LOSS scoring
            winner = next((r for r in results if r.get("result") == "WIN"), None)
            loser = next((r for r in results if r.get("result") == "LOSS"), None)

            if not winner or not loser:
                raise ValueError("HEAD_TO_HEAD WIN_LOSS requires one WIN and one LOSS")

            return [(winner["user_id"], 1), (loser["user_id"], 2)]

        elif "score" in results[0]:
            # SCORE_BASED: Compare scores
            result_a, result_b = results[0], results[1]

            score_a = result_a.get("score", 0)
            score_b = result_b.get("score", 0)

            if score_a > score_b:
                return [(result_a["user_id"], 1), (result_b["user_id"], 2)]
            elif score_b > score_a:
                return [(result_b["user_id"], 1), (result_a["user_id"], 2)]
            else:
                # Tie: both rank 1 (or handle differently based on business rules)
                return [(result_a["user_id"], 1), (result_b["user_id"], 1)]

        else:
            raise ValueError(f"HEAD_TO_HEAD result missing 'result' or 'score' field")

    def _process_team_match(
        self,
        results: List[Dict],
        structure_config: Optional[Dict] = None
    ) -> List[Tuple[int, int]]:
        """
        Process TEAM_MATCH results.

        Input format:
            [
                {"user_id": 1, "team": "A", "team_score": 5, "opponent_score": 3},
                {"user_id": 2, "team": "A", "team_score": 5, "opponent_score": 3},
                ...
            ]

        Logic:
            - All members of winning team get rank 1
            - All members of losing team get rank 2
            - Tie: all participants get rank 1 (or handle based on business rules)

        Returns:
            [(user_id, rank), ...] with winning team members first
        """
        if not results:
            return []

        # Determine winning team
        team_scores = {}
        for result in results:
            team = result.get("team")
            team_score = result.get("team_score")

            if team and team_score is not None:
                team_scores[team] = team_score

        if not team_scores:
            raise ValueError("TEAM_MATCH results missing team scores")

        # Find winning team
        sorted_teams = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)
        winning_team = sorted_teams[0][0]
        winning_score = sorted_teams[0][1]

        # Check for tie
        is_tie = len(sorted_teams) > 1 and sorted_teams[1][1] == winning_score

        # Assign rankings
        rankings = []
        for result in results:
            user_id = result.get("user_id")
            team = result.get("team")

            if user_id is None or team is None:
                continue

            if is_tie:
                # Tie: all rank 1
                rankings.append((user_id, 1))
            elif team == winning_team:
                # Winning team: rank 1
                rankings.append((user_id, 1))
            else:
                # Losing team: rank 2
                rankings.append((user_id, 2))

        # Sort: winners first, then losers
        rankings.sort(key=lambda x: x[1])
        return rankings

    def _process_time_based(self, results: List[Dict]) -> List[Tuple[int, int]]:
        """
        Process TIME_BASED results.

        Input format:
            [
                {"user_id": 1, "time_seconds": 11.23},
                {"user_id": 2, "time_seconds": 11.45},
                ...
            ]

        Logic:
            Fastest time = 1st place
            Slowest time = last place

        Returns:
            [(user_id, rank), ...] sorted by rank (fastest first)
        """
        # Extract times and sort
        timed_results = []
        for result in results:
            user_id = result.get("user_id")
            time_seconds = result.get("time_seconds")

            if user_id is None or time_seconds is None:
                raise ValueError(f"Invalid TIME_BASED result: {result}")

            timed_results.append((user_id, time_seconds))

        # Sort by time (ascending - fastest first)
        timed_results.sort(key=lambda x: x[1])

        # Assign ranks
        rankings = [(user_id, rank + 1) for rank, (user_id, _) in enumerate(timed_results)]
        return rankings

    # ========================================================================
    # Result Validation
    # ========================================================================

    def validate_results(
        self,
        match_format: str,
        results: List[Dict],
        expected_participants: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Validate that results are well-formed for the given match format.

        Args:
            match_format: Match format type
            results: List of result dicts
            expected_participants: Optional expected participant count

        Returns:
            (is_valid, error_message)
        """
        if not results:
            return False, "Results list is empty"

        try:
            format_enum = MatchFormat(match_format)
        except ValueError:
            return False, f"Invalid match_format: {match_format}"

        # Format-specific validation
        if format_enum == MatchFormat.INDIVIDUAL_RANKING:
            # Check if this is score-based round-robin format
            if results and "player_a_id" in results[0]:
                # Score-based round-robin validation
                for result in results:
                    if "player_a_id" not in result or "player_b_id" not in result:
                        return False, "Round-robin requires 'player_a_id' and 'player_b_id'"
                    if "score_a" not in result or "score_b" not in result:
                        return False, "Round-robin requires 'score_a' and 'score_b'"
                return True, "Valid"

            # Legacy placement-based validation
            for result in results:
                if "user_id" not in result or "placement" not in result:
                    return False, "INDIVIDUAL_RANKING requires 'user_id' and 'placement'"

            # Check for duplicate placements
            placements = [r["placement"] for r in results]
            if len(placements) != len(set(placements)):
                return False, "Duplicate placements detected"

            # Check that placements start from 1
            sorted_placements = sorted(placements)
            if sorted_placements[0] != 1:
                return False, "Placements must start from 1"

        elif format_enum == MatchFormat.HEAD_TO_HEAD:
            if len(results) != 2:
                return False, f"HEAD_TO_HEAD requires exactly 2 results, got {len(results)}"

        elif format_enum == MatchFormat.TIME_BASED:
            for result in results:
                if "user_id" not in result or "time_seconds" not in result:
                    return False, "TIME_BASED requires 'user_id' and 'time_seconds'"

        elif format_enum == MatchFormat.TEAM_MATCH:
            for result in results:
                if "user_id" not in result or "team" not in result:
                    return False, "TEAM_MATCH requires 'user_id' and 'team'"

        elif format_enum == MatchFormat.SKILL_RATING:
            # Basic validation - specific criteria TBD
            for result in results:
                if "user_id" not in result:
                    return False, "SKILL_RATING requires 'user_id'"

        # Check participant count if expected
        if expected_participants is not None:
            actual_participants = len(results)
            if actual_participants != expected_participants:
                return False, f"Expected {expected_participants} participants, got {actual_participants}"

        return True, "Valid"


# ============================================================================
# Usage Example
# ============================================================================

"""
EXAMPLE: Processing INDIVIDUAL_RANKING results

from app.services.tournament.result_processor import ResultProcessor

# Initialize processor
result_processor = ResultProcessor(db)

# Instructor submits results
results = [
    {"user_id": 1, "placement": 1},
    {"user_id": 2, "placement": 2},
    {"user_id": 3, "placement": 3},
    {"user_id": 4, "placement": 4}
]

# Validate
is_valid, error = result_processor.validate_results(
    match_format="INDIVIDUAL_RANKING",
    results=results,
    expected_participants=4
)

if not is_valid:
    raise ValueError(error)

# Process and get rankings
rankings = result_processor.process_results(
    session_id=session_id,
    match_format="INDIVIDUAL_RANKING",
    results=results
)

# rankings = [(1, 1), (2, 2), (3, 3), (4, 4)]

# Pass to PointsCalculatorService for points calculation
points_calculator = PointsCalculatorService(db)
points_map = points_calculator.calculate_points_batch(
    session_id=session_id,
    rankings=rankings
)
"""


"""
EXAMPLE: Future SKILL_RATING implementation

# Step 1: Implement custom processor
class LFASkillRatingProcessor:
    def derive_rankings(self, results, structure_config=None):
        # Custom business logic
        weighted_scores = []
        for result in results:
            rating = result.get("rating", 0)
            criteria = result.get("criteria_scores", {})

            # Example weighted scoring
            technique_weight = 0.4
            speed_weight = 0.3
            accuracy_weight = 0.3

            weighted_score = (
                criteria.get("technique", 0) * technique_weight +
                criteria.get("speed", 0) * speed_weight +
                criteria.get("accuracy", 0) * accuracy_weight
            )

            weighted_scores.append((result["user_id"], weighted_score))

        # Sort by score (descending)
        weighted_scores.sort(key=lambda x: x[1], reverse=True)

        # Assign ranks
        return [(user_id, rank + 1) for rank, (user_id, _) in enumerate(weighted_scores)]

# Step 2: Inject into ResultProcessor
custom_processor = LFASkillRatingProcessor()
result_processor.set_skill_rating_processor(custom_processor)

# Step 3: Use normally
results = [
    {
        "user_id": 1,
        "rating": 9.5,
        "criteria_scores": {"technique": 9, "speed": 10, "accuracy": 9}
    },
    {
        "user_id": 2,
        "rating": 8.0,
        "criteria_scores": {"technique": 8, "speed": 7, "accuracy": 9}
    }
]

rankings = result_processor.process_results(
    session_id=session_id,
    match_format="SKILL_RATING",
    results=results
)
"""
