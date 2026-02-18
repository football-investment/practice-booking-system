"""
Knockout Progression Service

Handles automatic creation of next-round matches in knockout tournaments:
- After semifinals: Creates bronze match (losers) and final (winners)
- After quarterfinals: Creates semifinals
- Ensures proper participant assignment based on match results

Phase 2.1: Uses TournamentPhase enum for type safety and consistency
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.models.tournament_enums import TournamentPhase  # Phase 2.1: Import enum
from app.services.tournament.repositories import SessionRepository, SQLSessionRepository  # Phase 2.2: DI
from app.utils.game_results import parse_game_results


class KnockoutProgressionService:
    """
    Service for managing knockout bracket progression

    Phase 2.2: Dependency injection for testability and maintainability
    """

    def __init__(self, db: Session = None, repository: SessionRepository = None, logger=None):
        """
        Initialize service with dependency injection support.

        Args:
            db: SQLAlchemy session (legacy, for backward compatibility)
            repository: SessionRepository implementation (new, preferred)
            logger: Logger instance (optional)
        """
        # Phase 2.2: Support both old (db) and new (repository) patterns
        if repository is not None:
            self.repo = repository
            self.db = None  # Don't use direct DB access when repository provided
        elif db is not None:
            self.repo = SQLSessionRepository(db)
            self.db = db  # Keep for backward compatibility in non-refactored methods
        else:
            raise ValueError("Either 'db' or 'repository' must be provided")

        self.logger = logger or logging.getLogger(__name__)

    def process_knockout_progression(
        self,
        session: SessionModel,
        tournament: Semester,
        game_results: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if this knockout match completion triggers next round creation.

        Args:
            session: The completed knockout session
            tournament: The tournament
            game_results: The processed game results with rankings

        Returns:
            Dict with created sessions info, or None if no progression needed
        """
        # Phase 2.1: Use TournamentPhase enum for type-safe comparison
        if session.tournament_phase != TournamentPhase.KNOCKOUT:
            return None

        # Phase 2.2: Use repository for data access
        # Determine tournament structure to handle progression correctly
        distinct_rounds = self.repo.get_distinct_rounds(tournament.id, TournamentPhase.KNOCKOUT)
        total_rounds = len(distinct_rounds)

        # Check which round this is
        round_num = session.tournament_round

        # ✅ Handle different tournament sizes dynamically
        # - 4 players: 2 rounds (R1=Semis, R2=Final+Bronze)
        # - 8 players: 3 rounds (R1=Quarters, R2=Semis, R3=Final+Bronze)
        # - 16 players: 4 rounds (R1=R16, R2=Quarters, R3=Semis, R4=Final+Bronze)

        # Check if all matches in current round are complete
        all_matches_in_round = self.repo.get_sessions_by_phase_and_round(
            tournament_id=tournament.id,
            phase=TournamentPhase.KNOCKOUT,
            round_num=round_num,
            exclude_bronze=True
        )

        completed_count = sum(1 for m in all_matches_in_round if m.game_results)

        if completed_count < len(all_matches_in_round):
            return {
                "message": f"Match completed. Waiting for other matches in round {round_num} ({completed_count}/{len(all_matches_in_round)} done)"
            }

        # All matches in this round complete - create next round matches
        return self._handle_round_completion(
            round_num=round_num,
            total_rounds=total_rounds,
            completed_matches=all_matches_in_round,
            tournament=tournament,
            tournament_phase=session.tournament_phase
        )

    def _handle_semifinal_completion(
        self,
        completed_session: SessionModel,
        tournament: Semester,
        game_results: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Handle semifinal completion - create bronze match and final when both semis are done.

        Args:
            completed_session: The just-completed semifinal session
            tournament: The tournament
            game_results: Results of the completed match

        Returns:
            Dict with info about created sessions
        """
        # Phase 2.2: Use repository for data access
        # Find all semifinal sessions (round 1)
        all_semifinals = self.repo.get_sessions_by_phase_and_round(
            tournament_id=tournament.id,
            phase=TournamentPhase.KNOCKOUT,
            round_num=1,
            exclude_bronze=False  # Include all round 1 matches
        )

        # Check if all semifinals have results
        completed_semifinals = []
        for sf in all_semifinals:
            if sf.game_results:
                # Parse game_results
                results = parse_game_results(sf.game_results)
                if results and "raw_results" in results and len(results["raw_results"]) > 0:
                    completed_semifinals.append({
                        "session": sf,
                        "results": results
                    })

        # Need all semifinals complete (typically 2 for 4-player knockout)
        if len(completed_semifinals) < len(all_semifinals):
            return {
                "message": f"Semifinal completed. Waiting for other semifinals ({len(completed_semifinals)}/{len(all_semifinals)} done)"
            }

        # All semifinals complete - determine winners and losers
        winners = []
        losers = []

        for sf_data in completed_semifinals:
            raw_results = sf_data["results"]["raw_results"]
            participant_ids = sf_data["session"].participant_user_ids

            # Determine winner and loser
            if len(raw_results) == 2 and "score" in raw_results[0]:
                # SCORE_BASED format
                p1_id = raw_results[0]["user_id"]
                p1_score = raw_results[0]["score"]
                p2_id = raw_results[1]["user_id"]
                p2_score = raw_results[1]["score"]

                if p1_score > p2_score:
                    winners.append(p1_id)
                    losers.append(p2_id)
                elif p2_score > p1_score:
                    winners.append(p2_id)
                    losers.append(p1_id)
                else:
                    # Tie - shouldn't happen in knockout, but handle gracefully
                    winners.append(p1_id)
                    losers.append(p2_id)

        # Phase 2.2: Use repository to check for existing matches
        # Check if bronze match already exists
        round2_sessions = self.repo.get_sessions_by_phase_and_round(
            tournament_id=tournament.id,
            phase=TournamentPhase.KNOCKOUT,
            round_num=2,
            exclude_bronze=False
        )

        existing_bronze = next((s for s in round2_sessions if "bronze" in s.title.lower()), None)
        existing_final = next((s for s in round2_sessions if "final" in s.title.lower() and "bronze" not in s.title.lower()), None)

        created_sessions = []

        # Create bronze match if needed
        if not existing_bronze and len(losers) >= 2:
            bronze_session = self._create_bronze_match(tournament, losers, completed_session)
            created_sessions.append({
                "type": "bronze",
                "session_id": bronze_session.id,
                "participants": losers
            })

        # Create final if needed
        if not existing_final and len(winners) >= 2:
            final_session = self._create_final_match(tournament, winners, completed_session)
            created_sessions.append({
                "type": "final",
                "session_id": final_session.id,
                "participants": winners
            })

        if created_sessions:
            self.db.commit()
            return {
                "message": f"✅ Semifinals complete! Created {len(created_sessions)} next-round matches",
                "created_sessions": created_sessions
            }

        return {
            "message": "All semifinals complete, but next round matches already exist"
        }

    def _create_bronze_match(
        self,
        tournament: Semester,
        loser_ids: List[int],
        reference_session: SessionModel
    ) -> SessionModel:
        """Create bronze medal match for semifinal losers"""

        # Use reference session's datetime as base, add 1 day
        bronze_start = reference_session.date_start + timedelta(days=1)

        # Calculate duration
        session_duration = (reference_session.date_end - reference_session.date_start).total_seconds() / 60
        bronze_end = bronze_start + timedelta(minutes=session_duration)

        # Phase 2.2: Use repository for session creation
        session_data = {
            "title": f"{tournament.name} - Bronze Medal Match",
            "date_start": bronze_start,
            "date_end": bronze_end,
            "location": reference_session.location,
            "tournament_phase": TournamentPhase.KNOCKOUT,
            "tournament_round": 2,  # Round 2 (finals round)
            "participant_user_ids": loser_ids[:2]  # Take first 2 losers
        }

        bronze_session = self.repo.create_session(tournament, session_data)
        return bronze_session

    def _create_final_match(
        self,
        tournament: Semester,
        winner_ids: List[int],
        reference_session: SessionModel
    ) -> SessionModel:
        """Create final match for semifinal winners"""

        # Use reference session's datetime as base, add 1 day + 2 hours (after bronze)
        final_start = reference_session.date_start + timedelta(days=1, hours=2)

        # Calculate duration
        session_duration = (reference_session.date_end - reference_session.date_start).total_seconds() / 60
        final_end = final_start + timedelta(minutes=session_duration)

        # Phase 2.2: Use repository for session creation
        session_data = {
            "title": f"{tournament.name} - Final",
            "date_start": final_start,
            "date_end": final_end,
            "location": reference_session.location,
            "tournament_phase": TournamentPhase.KNOCKOUT,
            "tournament_round": 2,  # Round 2 (finals round)
            "participant_user_ids": winner_ids[:2]  # Take first 2 winners
        }

        final_session = self.repo.create_session(tournament, session_data)
        return final_session

    def _handle_round_completion(
        self,
        round_num: int,
        total_rounds: int,
        completed_matches: List[SessionModel],
        tournament: Semester,
        tournament_phase: str
    ) -> Dict[str, Any]:
        """
        ✅ NEW: Handle completion of any knockout round dynamically.

        Determines winners from completed matches and updates participant_user_ids
        for existing next-round matches (which were pre-generated with NULL participants).

        Args:
            round_num: Current round number (1 = first round)
            total_rounds: Total rounds in tournament
            completed_matches: All completed matches from this round
            tournament: Tournament object
            tournament_phase: TournamentPhase.KNOCKOUT (canonical enum value)

        Returns:
            Dict with progression status and updated sessions
        """
        # Guard: if completed_matches is empty (e.g. the triggering session was a
        # bronze/3rd-place match excluded by exclude_bronze=True), nothing to do.
        if not completed_matches:
            return {"message": f"No qualifying non-bronze matches in round {round_num} to process"}

        # Determine winners from completed matches
        winners = []
        losers = []

        for match in completed_matches:
            if not match.game_results:
                continue

            # Parse game_results
            results = parse_game_results(match.game_results)

            # ✅ NATIVE SUPPORT: Handle both HEAD_TO_HEAD and INDIVIDUAL formats
            if "match_format" in results and results["match_format"] == "HEAD_TO_HEAD":
                # ✅ HEAD_TO_HEAD format (from HEAD_TO_HEAD endpoint)
                # Structure: {"participants": [{"user_id": X, "score": Y, "result": "win/loss/tie"}], "winner_user_id": Z}
                # OR from submit-results: {"participants": [], "raw_results": [{"user_id": X, "result": "WIN/LOSS"}]}
                participants = results.get("participants", [])
                winner_id = results.get("winner_user_id")

                if len(participants) == 2 and winner_id:
                    # Determine winner and loser from participants
                    for p in participants:
                        if p["user_id"] == winner_id:
                            winners.append(winner_id)
                        else:
                            losers.append(p["user_id"])
                elif len(participants) == 2:
                    # No winner (tie) - use first participant as tiebreaker
                    winners.append(participants[0]["user_id"])
                    losers.append(participants[1]["user_id"])
                else:
                    # Fallback: parse raw_results for WIN/LOSS or placement format
                    # (produced by /submit-results endpoint which leaves participants=[])
                    raw = results.get("raw_results", [])
                    has_result_field = any(r.get("result") for r in raw)
                    has_placement = any("placement" in r for r in raw)
                    if has_result_field:
                        for r in raw:
                            result_str = str(r.get("result", "")).upper()
                            if result_str == "WIN":
                                winners.append(r["user_id"])
                            elif result_str == "LOSS":
                                losers.append(r["user_id"])
                    elif has_placement and len(raw) >= 2:
                        # Placement-based: rank 1 is winner
                        sorted_raw = sorted(raw, key=lambda r: r.get("placement", 99))
                        winners.append(sorted_raw[0]["user_id"])
                        losers.append(sorted_raw[1]["user_id"])
            else:
                # ✅ INDIVIDUAL format (from INDIVIDUAL endpoint - legacy)
                # Supports SCORE_BASED: {"raw_results": [{"user_id": X, "score": Y}]}
                # Supports PLACEMENT:   {"raw_results": [{"user_id": X, "placement": Y}]}
                raw_results = results.get("raw_results", [])

                if len(raw_results) == 2 and "score" in raw_results[0]:
                    # SCORE_BASED format
                    p1_id = raw_results[0]["user_id"]
                    p1_score = raw_results[0]["score"]
                    p2_id = raw_results[1]["user_id"]
                    p2_score = raw_results[1]["score"]

                    if p1_score > p2_score:
                        winners.append(p1_id)
                        losers.append(p2_id)
                    elif p2_score > p1_score:
                        winners.append(p2_id)
                        losers.append(p1_id)
                    else:
                        # Tie - use tiebreaker or first player
                        winners.append(p1_id)
                        losers.append(p2_id)
                elif len(raw_results) == 2 and "placement" in raw_results[0]:
                    # Placement-based format: rank 1 is winner
                    sorted_by_placement = sorted(raw_results, key=lambda r: r.get("placement", 99))
                    winners.append(sorted_by_placement[0]["user_id"])
                    losers.append(sorted_by_placement[1]["user_id"])

        # Check if this is the final round (before final+bronze)
        is_final_round = (round_num == total_rounds - 1)

        if is_final_round:
            # This is semifinals - create/update Final and Bronze matches
            return self._update_final_and_bronze(
                winners=winners,
                losers=losers,
                tournament=tournament,
                tournament_phase=tournament_phase,
                reference_session=completed_matches[0]
            )
        else:
            # This is earlier round (QF, R16, etc.) - update next round matches
            return self._update_next_round_matches(
                round_num=round_num,
                winners=winners,
                losers=losers,
                tournament=tournament,
                tournament_phase=tournament_phase
            )

    def _update_next_round_matches(
        self,
        round_num: int,
        winners: List[int],
        tournament: Semester,
        tournament_phase: str,
        losers: List[int] = None
    ) -> Dict[str, Any]:
        """
        ✅ NEW: Update participant_user_ids for next round matches.

        Next round matches already exist (created during tournament generation),
        but participant_user_ids is NULL. We populate them with winners.
        Also assigns losers to the bronze/3rd place match in the final round.
        """
        next_round = round_num + 1
        losers = losers or []

        # Phase 2.2: Use repository for data access
        # Get next round matches (ordered by match_number)
        next_round_matches = self.repo.get_sessions_by_phase_and_round(
            tournament_id=tournament.id,
            phase=TournamentPhase.KNOCKOUT,
            round_num=next_round,
            exclude_bronze=True
        )
        # Sort by match number (repository returns unordered list)
        next_round_matches = sorted(next_round_matches, key=lambda s: s.tournament_match_number or 0)

        if not next_round_matches:
            return {"message": f"⚠️ No next round matches found for round {next_round}"}

        # Pair winners into matches (winner[0] vs winner[1], winner[2] vs winner[3], etc.)
        updated_sessions = []
        for idx, match in enumerate(next_round_matches):
            # Calculate which winners go into this match
            p1_idx = idx * 2
            p2_idx = idx * 2 + 1

            if p1_idx < len(winners) and p2_idx < len(winners):
                match.participant_user_ids = [winners[p1_idx], winners[p2_idx]]
                updated_sessions.append({
                    "session_id": match.id,
                    "title": match.title,
                    "participants": [winners[p1_idx], winners[p2_idx]]
                })

        # Assign losers to the bronze/3rd place match if it exists in a later round
        if len(losers) >= 2:
            distinct_rounds = self.repo.get_distinct_rounds(tournament.id, TournamentPhase.KNOCKOUT)
            if distinct_rounds:
                final_round = max(distinct_rounds)
                if final_round > next_round:
                    final_round_sessions = self.repo.get_sessions_by_phase_and_round(
                        tournament_id=tournament.id,
                        phase=TournamentPhase.KNOCKOUT,
                        round_num=final_round,
                        exclude_bronze=False
                    )
                    for session in final_round_sessions:
                        title_lower = session.title.lower()
                        if "bronze" in title_lower or "3rd" in title_lower:
                            if not session.participant_user_ids:
                                session.participant_user_ids = losers[:2]
                                updated_sessions.append({
                                    "session_id": session.id,
                                    "title": session.title,
                                    "type": "bronze",
                                    "participants": losers[:2]
                                })
                            break

        self.db.commit()

        return {
            "message": f"✅ Round {round_num} complete! Updated {len(updated_sessions)} matches for round {next_round}",
            "updated_sessions": updated_sessions
        }

    def _update_final_and_bronze(
        self,
        winners: List[int],
        losers: List[int],
        tournament: Semester,
        tournament_phase: str,
        reference_session: SessionModel
    ) -> Dict[str, Any]:
        """
        ✅ NEW: Update Final and Bronze match participants after semifinals.

        These matches were already created during tournament generation,
        but participant_user_ids is NULL. We populate them with winners/losers.
        """
        updated_sessions = []

        # Phase 2.2: Use repository for data access
        # Get all knockout sessions for this tournament (no specific round - find final round)
        all_knockout_sessions = []
        distinct_rounds = self.repo.get_distinct_rounds(tournament.id, TournamentPhase.KNOCKOUT)
        if distinct_rounds:
            final_round = max(distinct_rounds)
            all_knockout_sessions = self.repo.get_sessions_by_phase_and_round(
                tournament_id=tournament.id,
                phase=TournamentPhase.KNOCKOUT,
                round_num=final_round,
                exclude_bronze=False
            )

        # Find Final match (exclude bronze, semi-finals, quarter-finals)
        final_match = None
        for session in all_knockout_sessions:
            title_lower = session.title.lower()
            if ("final" in title_lower or "round of 2" in title_lower) and \
               "quarter" not in title_lower and "semi" not in title_lower and \
               "bronze" not in title_lower and "3rd" not in title_lower:
                final_match = session
                break

        if final_match and len(winners) >= 2:
            final_match.participant_user_ids = winners[:2]
            updated_sessions.append({
                "type": "final",
                "session_id": final_match.id,
                "participants": winners[:2]
            })

        # Find Bronze match
        bronze_match = None
        for session in all_knockout_sessions:
            title_lower = session.title.lower()
            if "bronze" in title_lower or "3rd" in title_lower:
                bronze_match = session
                break

        if bronze_match and len(losers) >= 2:
            bronze_match.participant_user_ids = losers[:2]
            updated_sessions.append({
                "type": "bronze",
                "session_id": bronze_match.id,
                "participants": losers[:2]
            })

        # Phase 2.2: Still need db access for commit (will be moved to repository later)
        if self.db:
            self.db.commit()

        return {
            "message": f"✅ Semifinals complete! Updated {len(updated_sessions)} final round matches",
            "updated_sessions": updated_sessions
        }
