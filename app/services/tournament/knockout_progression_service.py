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
import json


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

        # ✅ NEW: Determine tournament structure to handle progression correctly
        # Check total number of knockout rounds to identify tournament size
        # ✅ TACTICAL FIX: Use canonical "KNOCKOUT" (uppercase) to match database value
        total_rounds = self.db.query(SessionModel.tournament_round).filter(
            and_(
                SessionModel.semester_id == tournament.id,
                SessionModel.is_tournament_game == True,
                SessionModel.tournament_phase == TournamentPhase.KNOCKOUT
            )
        ).distinct().count()

        # Check which round this is
        round_num = session.tournament_round

        # ✅ NEW: Handle different tournament sizes dynamically
        # - 4 players: 2 rounds (R1=Semis, R2=Final+Bronze)
        # - 8 players: 3 rounds (R1=Quarters, R2=Semis, R3=Final+Bronze)
        # - 16 players: 4 rounds (R1=R16, R2=Quarters, R3=Semis, R4=Final+Bronze)

        # Check if all matches in current round are complete
        all_matches_in_round = self.db.query(SessionModel).filter(
            and_(
                SessionModel.semester_id == tournament.id,
                SessionModel.tournament_phase == TournamentPhase.KNOCKOUT,
                SessionModel.tournament_round == round_num,
                SessionModel.is_tournament_game == True,
                # Exclude bronze match from count (it has same round as final)
                ~SessionModel.title.ilike("%bronze%"),
                ~SessionModel.title.ilike("%3rd%")
            )
        ).all()

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
        # Find all semifinal sessions (round 1)
        all_semifinals = self.db.query(SessionModel).filter(
            and_(
                SessionModel.semester_id == tournament.id,
                SessionModel.tournament_phase == TournamentPhase.KNOCKOUT,
                SessionModel.tournament_round == 1,
                SessionModel.is_tournament_game == True
            )
        ).all()

        # Check if all semifinals have results
        completed_semifinals = []
        for sf in all_semifinals:
            if sf.game_results:
                # Parse game_results
                results = json.loads(sf.game_results) if isinstance(sf.game_results, str) else sf.game_results
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

        # Check if bronze match already exists
        existing_bronze = self.db.query(SessionModel).filter(
            and_(
                SessionModel.semester_id == tournament.id,
                SessionModel.tournament_phase == TournamentPhase.KNOCKOUT,
                SessionModel.tournament_round == 2,
                SessionModel.title.ilike("%bronze%")
            )
        ).first()

        # Check if final already exists
        existing_final = self.db.query(SessionModel).filter(
            and_(
                SessionModel.semester_id == tournament.id,
                SessionModel.tournament_phase == TournamentPhase.KNOCKOUT,
                SessionModel.tournament_round == 2,
                SessionModel.title.ilike("%final%"),
                ~SessionModel.title.ilike("%bronze%")
            )
        ).first()

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

        bronze_session = SessionModel(
            semester_id=tournament.id,
            title=f"{tournament.name} - Bronze Medal Match",
            date_start=bronze_start,
            date_end=bronze_end,
            location=reference_session.location,
            instructor_id=reference_session.instructor_id,
            session_status="scheduled",
            is_tournament_game=True,
            tournament_phase=TournamentPhase.KNOCKOUT.value,
            tournament_round=2,  # Round 2 (finals round)
            match_format=reference_session.match_format or "HEAD_TO_HEAD",
            participant_user_ids=loser_ids[:2]  # Take first 2 losers
        )

        self.db.add(bronze_session)
        self.db.flush()
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

        final_session = SessionModel(
            semester_id=tournament.id,
            title=f"{tournament.name} - Final",
            date_start=final_start,
            date_end=final_end,
            location=reference_session.location,
            instructor_id=reference_session.instructor_id,
            session_status="scheduled",
            is_tournament_game=True,
            tournament_phase=TournamentPhase.KNOCKOUT.value,
            tournament_round=2,  # Round 2 (finals round)
            match_format=reference_session.match_format or "HEAD_TO_HEAD",
            participant_user_ids=winner_ids[:2]  # Take first 2 winners
        )

        self.db.add(final_session)
        self.db.flush()
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
        # Determine winners from completed matches
        winners = []
        losers = []

        for match in completed_matches:
            if not match.game_results:
                continue

            # Parse game_results
            results = json.loads(match.game_results) if isinstance(match.game_results, str) else match.game_results

            # ✅ NATIVE SUPPORT: Handle both HEAD_TO_HEAD and INDIVIDUAL formats
            if "match_format" in results and results["match_format"] == "HEAD_TO_HEAD":
                # ✅ HEAD_TO_HEAD format (from HEAD_TO_HEAD endpoint)
                # Structure: {"participants": [{"user_id": X, "score": Y, "result": "win/loss/tie"}], "winner_user_id": Z}
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
                # ✅ INDIVIDUAL format (from INDIVIDUAL endpoint - legacy)
                # Structure: {"raw_results": [{"user_id": X, "score": Y, "rank": Z}]}
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
                tournament=tournament,
                tournament_phase=tournament_phase
            )

    def _update_next_round_matches(
        self,
        round_num: int,
        winners: List[int],
        tournament: Semester,
        tournament_phase: str
    ) -> Dict[str, Any]:
        """
        ✅ NEW: Update participant_user_ids for next round matches.

        Next round matches already exist (created during tournament generation),
        but participant_user_ids is NULL. We populate them with winners.
        """
        next_round = round_num + 1

        # Get next round matches (ordered by match_number)
        next_round_matches = self.db.query(SessionModel).filter(
            and_(
                SessionModel.semester_id == tournament.id,
                SessionModel.tournament_phase == TournamentPhase.KNOCKOUT,
                SessionModel.tournament_round == next_round,
                SessionModel.is_tournament_game == True,
                ~SessionModel.title.ilike("%bronze%"),
                ~SessionModel.title.ilike("%3rd%")
            )
        ).order_by(SessionModel.tournament_match_number).all()

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

        # Find existing Final match
        # ✅ FIX: Match "Final" OR "Round of 2" but exclude "Quarter-finals", "Semi-finals", "Bronze", "3rd Place"
        final_match = self.db.query(SessionModel).filter(
            and_(
                SessionModel.semester_id == tournament.id,
                SessionModel.tournament_phase == TournamentPhase.KNOCKOUT,
                (
                    SessionModel.title.ilike("%final%") |
                    SessionModel.title.ilike("%round of 2%")
                ),
                ~SessionModel.title.ilike("%quarter-final%"),
                ~SessionModel.title.ilike("%semi-final%"),
                ~SessionModel.title.ilike("%bronze%"),
                ~SessionModel.title.ilike("%3rd%")
            )
        ).first()

        if final_match and len(winners) >= 2:
            final_match.participant_user_ids = winners[:2]
            updated_sessions.append({
                "type": "final",
                "session_id": final_match.id,
                "participants": winners[:2]
            })

        # Find existing Bronze match
        bronze_match = self.db.query(SessionModel).filter(
            and_(
                SessionModel.semester_id == tournament.id,
                SessionModel.tournament_phase == TournamentPhase.KNOCKOUT,
                SessionModel.title.ilike("%bronze%")
            )
        ).first()

        # Alternative: Check for "3rd Place" in title
        if not bronze_match:
            bronze_match = self.db.query(SessionModel).filter(
                and_(
                    SessionModel.semester_id == tournament.id,
                    SessionModel.tournament_phase == TournamentPhase.KNOCKOUT,
                    SessionModel.title.ilike("%3rd%")
                )
            ).first()

        if bronze_match and len(losers) >= 2:
            bronze_match.participant_user_ids = losers[:2]
            updated_sessions.append({
                "type": "bronze",
                "session_id": bronze_match.id,
                "participants": losers[:2]
            })

        self.db.commit()

        return {
            "message": f"✅ Semifinals complete! Updated {len(updated_sessions)} final round matches",
            "updated_sessions": updated_sessions
        }
