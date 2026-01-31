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
        import logging
        logger = logging.getLogger(__name__)

        try:
            logger.info(f"🔍 SESSION GENERATION START - Tournament ID: {tournament_id}")
            logger.info(f"📊 Input params: parallel_fields={parallel_fields}, session_duration={session_duration_minutes}, break_minutes={break_minutes}, number_of_rounds={number_of_rounds}")

            # Validation
            can_generate, reason = self.can_generate_sessions(tournament_id)
            logger.info(f"✅ Validation result: can_generate={can_generate}, reason={reason}")
            if not can_generate:
                return False, reason, []

            # Fetch tournament
            tournament = self.tournament_repo.get_or_404(tournament_id)
            logger.info(f"🏆 Tournament fetched: id={tournament.id}, name={tournament.name}")

            # Log tournament configuration details
            logger.info(f"📋 Tournament config: tournament_type_id={tournament.tournament_type_id if hasattr(tournament, 'tournament_type_id') else 'N/A'}")
            logger.info(f"📋 Tournament format property: {tournament.format}")

            # Log config objects
            if hasattr(tournament, 'tournament_config_obj') and tournament.tournament_config_obj:
                logger.info(f"📋 TournamentConfiguration exists: id={tournament.tournament_config_obj.id}, tournament_type_id={tournament.tournament_config_obj.tournament_type_id}")
            else:
                logger.info(f"⚠️ No TournamentConfiguration found")

            if hasattr(tournament, 'game_config_obj') and tournament.game_config_obj:
                logger.info(f"🎮 GameConfiguration exists: id={tournament.game_config_obj.id}, game_preset_id={tournament.game_config_obj.game_preset_id}")
            else:
                logger.info(f"⚠️ No GameConfiguration found")

            # Eager load location relationships to prevent N+1 queries
            # Required for get_tournament_venue() helper function
            self.db.refresh(tournament, ['location', 'campus'])
            logger.info(f"📍 Location refreshed: location={tournament.location}, campus={tournament.campus}")

            # Get enrolled player count
            player_count = self.db.query(SemesterEnrollment).filter(
                SemesterEnrollment.semester_id == tournament_id,
                SemesterEnrollment.is_active == True,
                SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
            ).count()
            logger.info(f"👥 Enrolled player count: {player_count}")

            # ✅ CRITICAL: Check tournament format
            logger.info(f"🔀 Checking tournament format: {tournament.format}")
            if tournament.format == "INDIVIDUAL_RANKING":
                logger.info(f"🎯 INDIVIDUAL_RANKING tournament detected")
                # INDIVIDUAL_RANKING: No tournament type needed, simple competition
                if player_count < 2:
                    logger.warning(f"❌ Not enough players for INDIVIDUAL_RANKING: need 2, have {player_count}")
                    return False, f"Not enough players. Need at least 2, have {player_count}", []

                logger.info(f"🔧 Calling individual_ranking_generator.generate() with:")
                logger.info(f"   - tournament_id: {tournament.id}")
                logger.info(f"   - player_count: {player_count}")
                logger.info(f"   - parallel_fields: {parallel_fields}")
                logger.info(f"   - session_duration: {session_duration_minutes}")
                logger.info(f"   - break_minutes: {break_minutes}")
                logger.info(f"   - number_of_rounds: {number_of_rounds}")

                sessions = self.individual_ranking_generator.generate(
                    tournament=tournament,
                    tournament_type=None,
                    player_count=player_count,
                    parallel_fields=parallel_fields,
                    session_duration=session_duration_minutes,
                    break_minutes=break_minutes,
                    number_of_rounds=number_of_rounds
                )
                logger.info(f"✅ individual_ranking_generator.generate() returned {len(sessions)} sessions")
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
            logger.info(f"👥 Fetched {len(enrolled_players)} enrolled players from database")

            # Create session records in database
            created_sessions = []
            logger.info(f"🔨 Creating {len(sessions)} session records in database...")
            for idx, session_data in enumerate(sessions, 1):
                logger.info(f"📝 Creating session {idx}/{len(sessions)}: {session_data.get('title', 'N/A')}")
                logger.info(f"   Session data keys: {list(session_data.keys())}")

                try:
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
                    logger.info(f"✅ Session {idx} created successfully with ID: {session.id}")
                except Exception as session_error:
                    logger.error(f"❌ Failed to create session {idx}: {str(session_error)}")
                    logger.error(f"   Session data that caused error: {session_data}")
                    raise

                # ✅ TOURNAMENT SESSIONS: NO bookings creation
                # Tournament sessions use:
                #   - semester_enrollments (tournament enrollment)
                #   - participant_user_ids (explicit match participants)
                # Bookings are ONLY for regular practice sessions, NOT tournaments

                created_sessions.append(session_data)

            # Mark tournament as sessions_generated
            # 🎯 FIX: sessions_generated is a read-only property, update the config object directly
            if tournament.tournament_config_obj:
                tournament.tournament_config_obj.sessions_generated = True
                tournament.tournament_config_obj.sessions_generated_at = datetime.utcnow()
                logger.info(f"✅ Marked tournament as sessions_generated at {tournament.tournament_config_obj.sessions_generated_at}")
            else:
                logger.error(f"❌ No tournament_config_obj found for tournament {tournament_id}")
                raise ValueError(f"Tournament {tournament_id} has no TournamentConfiguration object")

            self.db.commit()
            logger.info(f"✅ Database commit successful")

            logger.info(f"🎉 SESSION GENERATION COMPLETE - Generated {len(created_sessions)} sessions for {len(enrolled_players)} players")
            return True, f"Successfully generated {len(created_sessions)} tournament sessions for {len(enrolled_players)} enrolled players", created_sessions

        except Exception as e:
            logger.error(f"❌❌❌ EXCEPTION IN SESSION GENERATION ❌❌❌")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception message: {str(e)}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            # Rollback database changes
            self.db.rollback()
            logger.error(f"🔄 Database rolled back")

            # Re-raise the exception so FastAPI can handle it
            raise
