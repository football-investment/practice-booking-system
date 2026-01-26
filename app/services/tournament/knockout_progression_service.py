"""
Knockout Progression Service

Handles automatic creation of next-round matches in knockout tournaments:
- After semifinals: Creates bronze match (losers) and final (winners)
- After quarterfinals: Creates semifinals
- Ensures proper participant assignment based on match results
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.semester import Semester
from app.models.session import Session as SessionModel
import json


class KnockoutProgressionService:
    """Service for managing knockout bracket progression"""

    def __init__(self, db: Session):
        self.db = db

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
        # Only process if this is a knockout match
        if session.tournament_phase != "Knockout Stage":
            return None

        # Check which round this is
        round_num = session.tournament_round

        if round_num == 1:
            # This is a semifinal - check if both semifinals are complete
            return self._handle_semifinal_completion(session, tournament, game_results)

        # Add more round handling here if needed (quarterfinals, etc.)
        return None

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
                SessionModel.tournament_phase == "Knockout Stage",
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
                SessionModel.tournament_phase == "Knockout Stage",
                SessionModel.tournament_round == 2,
                SessionModel.title.ilike("%bronze%")
            )
        ).first()

        # Check if final already exists
        existing_final = self.db.query(SessionModel).filter(
            and_(
                SessionModel.semester_id == tournament.id,
                SessionModel.tournament_phase == "Knockout Stage",
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
            tournament_phase="Knockout Stage",
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
            tournament_phase="Knockout Stage",
            tournament_round=2,  # Round 2 (finals round)
            match_format=reference_session.match_format or "HEAD_TO_HEAD",
            participant_user_ids=winner_ids[:2]  # Take first 2 winners
        )

        self.db.add(final_session)
        self.db.flush()
        return final_session
