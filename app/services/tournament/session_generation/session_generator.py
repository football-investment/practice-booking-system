"""
Tournament Session Generator (Coordinator)

Main entry point for tournament session generation.
Delegates to specific format generators based on tournament type.

CRITICAL CONSTRAINT: This service is ONLY called after the enrollment period ends,
ensuring stable player count and preventing mid-tournament enrollment changes.
"""
from typing import List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.semester import Semester
from app.models.tournament_type import TournamentType
from app.models.session import Session as SessionModel
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.repositories.tournament_repository import TournamentRepository

from .validators import GenerationValidator
from .formats import (
    LeagueGenerator,
    KnockoutGenerator,
    SwissGenerator,
    GroupKnockoutGenerator,
    IndividualRankingGenerator,
)


class TournamentSessionGenerator:
    """
    Coordinates tournament session generation by delegating to format-specific generators
    """

    def __init__(self, db: Session):
        self.db = db
        self.tournament_repo = TournamentRepository(db)
        self.validator = GenerationValidator(db)

        # Initialize format generators
        self.league_generator = LeagueGenerator(db)
        self.knockout_generator = KnockoutGenerator(db)
        self.swiss_generator = SwissGenerator(db)
        self.group_knockout_generator = GroupKnockoutGenerator(db)
        self.individual_ranking_generator = IndividualRankingGenerator(db)

    def can_generate_sessions(self, tournament_id: int) -> Tuple[bool, str]:
        """
        Check if tournament is ready for session generation

        Returns:
            (can_generate, reason)
        """
        return self.validator.can_generate_sessions(tournament_id)

    def generate_sessions(
        self,
        tournament_id: int,
        parallel_fields: int = 1,
        session_duration_minutes: int = 90,
        break_minutes: int = 15,
        number_of_rounds: int = 1
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Generate all tournament sessions based on tournament type and enrolled player count

        Args:
            tournament_id: Tournament (Semester) ID
            parallel_fields: Number of fields available for parallel matches
            session_duration_minutes: Duration of each session
            break_minutes: Break time between sessions
            number_of_rounds: Number of rounds for INDIVIDUAL_RANKING tournaments (1-10)

        Returns:
            (success, message, sessions_created)
        """
        # Validation
        can_generate, reason = self.can_generate_sessions(tournament_id)
        if not can_generate:
            return False, reason, []

        # Fetch tournament
        tournament = self.tournament_repo.get_or_404(tournament_id)

        # Eager load location relationships to prevent N+1 queries
        # Required for get_tournament_venue() helper function
        self.db.refresh(tournament, ['location', 'campus'])

        # Get enrolled player count
        player_count = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).count()

        # ✅ CRITICAL: Check tournament format
        if tournament.format == "INDIVIDUAL_RANKING":
            # INDIVIDUAL_RANKING: No tournament type needed, simple competition
            if player_count < 2:
                return False, f"Not enough players. Need at least 2, have {player_count}", []

            sessions = self.individual_ranking_generator.generate(
                tournament=tournament,
                tournament_type=None,
                player_count=player_count,
                parallel_fields=parallel_fields,
                session_duration=session_duration_minutes,
                break_minutes=break_minutes,
                number_of_rounds=number_of_rounds
            )
        else:
            # HEAD_TO_HEAD: Requires tournament type (Swiss, League, Knockout, etc.)
            tournament_type = self.db.query(TournamentType).filter(
                TournamentType.id == tournament.tournament_type_id
            ).first()

            if not tournament_type:
                return False, "HEAD_TO_HEAD tournaments require a tournament type", []

            # Validate player count against tournament type constraints
            is_valid, error_msg = tournament_type.validate_player_count(player_count)
            if not is_valid:
                return False, error_msg, []

            # Generate session structure based on tournament type
            if tournament_type.code == "league":
                sessions = self.league_generator.generate(
                    tournament=tournament,
                    tournament_type=tournament_type,
                    player_count=player_count,
                    parallel_fields=parallel_fields,
                    session_duration=session_duration_minutes,
                    break_minutes=break_minutes
                )
            elif tournament_type.code == "knockout":
                sessions = self.knockout_generator.generate(
                    tournament=tournament,
                    tournament_type=tournament_type,
                    player_count=player_count,
                    parallel_fields=parallel_fields,
                    session_duration=session_duration_minutes,
                    break_minutes=break_minutes
                )
            elif tournament_type.code == "group_knockout":
                sessions = self.group_knockout_generator.generate(
                    tournament=tournament,
                    tournament_type=tournament_type,
                    player_count=player_count,
                    parallel_fields=parallel_fields,
                    session_duration=session_duration_minutes,
                    break_minutes=break_minutes
                )
            elif tournament_type.code == "swiss":
                sessions = self.swiss_generator.generate(
                    tournament=tournament,
                    tournament_type=tournament_type,
                    player_count=player_count,
                    parallel_fields=parallel_fields,
                    session_duration=session_duration_minutes,
                    break_minutes=break_minutes
                )
            else:
                return False, f"Unknown tournament type: {tournament_type.code}", []

        # Get all enrolled players
        enrolled_players = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).all()

        # Create session records in database
        created_sessions = []
        for session_data in sessions:
            session = SessionModel(
                semester_id=tournament_id,
                instructor_id=tournament.master_instructor_id,
                is_tournament_game=True,
                auto_generated=True,
                capacity=player_count,  # Tournament sessions support all enrolled players
                **session_data
            )
            self.db.add(session)
            self.db.flush()  # Get session.id

            # ✅ TOURNAMENT SESSIONS: NO bookings creation
            # Tournament sessions use:
            #   - semester_enrollments (tournament enrollment)
            #   - participant_user_ids (explicit match participants)
            # Bookings are ONLY for regular practice sessions, NOT tournaments

            created_sessions.append(session_data)

        # Mark tournament as sessions_generated
        tournament.sessions_generated = True
        tournament.sessions_generated_at = datetime.utcnow()

        self.db.commit()

        return True, f"Successfully generated {len(created_sessions)} tournament sessions for {len(enrolled_players)} enrolled players", created_sessions
