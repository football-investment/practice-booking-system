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
from .utils import get_campus_schedule


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
        number_of_rounds: int = 1,
        campus_ids: List[int] = None
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Generate all tournament sessions based on tournament type and enrolled player count

        Args:
            tournament_id: Tournament (Semester) ID
            parallel_fields: Number of fields available for parallel matches
            session_duration_minutes: Duration of each session
            break_minutes: Break time between sessions
            number_of_rounds: Number of rounds for INDIVIDUAL_RANKING tournaments (1-10)
            campus_ids: List of campus IDs for multi-venue round-robin distribution (all formats)

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

            # Resolve per-campus schedule parameters (campus-level overrides take priority)
            campus_id = tournament.campus_id if hasattr(tournament, 'campus_id') else None

            if campus_ids and len(campus_ids) > 0:
                # Multi-campus: resolve config independently for each campus
                campus_configs = {}
                for cid in campus_ids:
                    cfg = get_campus_schedule(
                        db=self.db,
                        tournament_id=tournament_id,
                        campus_id=cid,
                        global_match_duration=session_duration_minutes,
                        global_break_duration=break_minutes,
                        global_parallel_fields=parallel_fields,
                    )
                    campus_configs[cid] = cfg
                # Use first campus as the baseline for fallback / knockout-stage params
                first_cfg = campus_configs[campus_ids[0]]
                session_duration_minutes = first_cfg["match_duration_minutes"]
                break_minutes = first_cfg["break_duration_minutes"]
                parallel_fields = first_cfg["parallel_fields"]
                logger.info(f"📐 Multi-campus schedule resolved ({len(campus_configs)} campuses):")
                for cid, cfg in campus_configs.items():
                    logger.info(
                        f"   Campus {cid}: duration={cfg['match_duration_minutes']}min, "
                        f"break={cfg['break_duration_minutes']}min, "
                        f"parallel_fields={cfg['parallel_fields']}"
                    )
            else:
                campus_configs = None
                campus_schedule = get_campus_schedule(
                    db=self.db,
                    tournament_id=tournament_id,
                    campus_id=campus_id,
                    global_match_duration=session_duration_minutes,
                    global_break_duration=break_minutes,
                    global_parallel_fields=parallel_fields,
                )
                session_duration_minutes = campus_schedule["match_duration_minutes"]
                break_minutes = campus_schedule["break_duration_minutes"]
                parallel_fields = campus_schedule["parallel_fields"]
                logger.info(
                    f"📐 Resolved campus schedule (campus_id={campus_id}): "
                    f"match_duration={session_duration_minutes}min, "
                    f"break={break_minutes}min, "
                    f"parallel_fields={parallel_fields}"
                )

            # Determine seeding pool: prefer pre-tournament check-in confirmed players.
            # If no check-ins exist (OPS auto-mode, legacy data), fall back to all APPROVED enrollments.
            _base_filter = [
                SemesterEnrollment.semester_id == tournament_id,
                SemesterEnrollment.is_active == True,
                SemesterEnrollment.request_status == EnrollmentStatus.APPROVED,
            ]
            checked_in_count = self.db.query(SemesterEnrollment).filter(
                *_base_filter,
                SemesterEnrollment.tournament_checked_in_at.isnot(None),
            ).count()

            if checked_in_count > 0:
                # REGRESSION FIX: bracket seeded from confirmed check-in pool only
                _player_filter = _base_filter + [
                    SemesterEnrollment.tournament_checked_in_at.isnot(None),
                ]
                logger.info(
                    f"✅ Pre-tournament check-in active: {checked_in_count} confirmed players "
                    f"(seeding from confirmed pool only)"
                )
            else:
                # Backward compat: no check-ins recorded → use all APPROVED enrollments
                _player_filter = _base_filter
                logger.info(
                    "⚠️  No pre-tournament check-ins found — falling back to all APPROVED enrollments "
                    "(OPS auto-mode or legacy tournament)"
                )

            total_approved = self.db.query(SemesterEnrollment).filter(*_base_filter).count()
            player_count = self.db.query(SemesterEnrollment).filter(*_player_filter).count()

            # Monitoring snapshot: always log seeding pool composition
            _pool_label = 'check-in confirmed' if checked_in_count > 0 else 'fallback: all approved'
            logger.info(
                f"📊 SEEDING POOL SNAPSHOT | tournament={tournament_id} | "
                f"total_approved={total_approved} | "
                f"total_checked_in={checked_in_count} | "
                f"seeded_count={player_count} | "
                f"pool={_pool_label}"
            )

            # ⚠️ INTEGRITY ALERT: when check-ins exist, seeded_count MUST equal total_checked_in.
            # Any divergence indicates a filter bug (e.g. concurrent enrollment approval
            # between the two queries, or a corrupted filter list).
            if checked_in_count > 0 and player_count != checked_in_count:
                logger.error(
                    f"🚨 SEEDING POOL INTEGRITY VIOLATION | tournament={tournament_id} | "
                    f"total_checked_in={checked_in_count} != seeded_count={player_count} | "
                    f"Bracket will be generated with {player_count} players — "
                    f"investigate _player_filter and concurrent DB state before proceeding."
                )

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
                    number_of_rounds=number_of_rounds,
                    campus_ids=campus_ids,
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
                        break_minutes=break_minutes,
                        campus_ids=campus_ids,
                    )
                elif tournament_type.code == "knockout":
                    sessions = self.knockout_generator.generate(
                        tournament=tournament,
                        tournament_type=tournament_type,
                        player_count=player_count,
                        parallel_fields=parallel_fields,
                        session_duration=session_duration_minutes,
                        break_minutes=break_minutes,
                        campus_ids=campus_ids,
                    )
                elif tournament_type.code == "group_knockout":
                    sessions = self.group_knockout_generator.generate(
                        tournament=tournament,
                        tournament_type=tournament_type,
                        player_count=player_count,
                        parallel_fields=parallel_fields,
                        session_duration=session_duration_minutes,
                        break_minutes=break_minutes,
                        campus_ids=campus_ids,
                        campus_configs=campus_configs,
                    )
                elif tournament_type.code == "swiss":
                    sessions = self.swiss_generator.generate(
                        tournament=tournament,
                        tournament_type=tournament_type,
                        player_count=player_count,
                        parallel_fields=parallel_fields,
                        session_duration=session_duration_minutes,
                        break_minutes=break_minutes,
                        campus_ids=campus_ids,
                    )
                else:
                    return False, f"Unknown tournament type: {tournament_type.code}", []

            # Fetch seeding pool (mirrors the player_count query above)
            enrolled_players = self.db.query(SemesterEnrollment).filter(
                *_player_filter
            ).all()
            logger.info(f"👥 Fetched {len(enrolled_players)} players in seeding pool from database")

            # Create session records in database (bulk insert — no per-session flush)
            created_sessions = []
            logger.info(f"🔨 Creating {len(sessions)} session records in database (bulk)...")
            session_objects = []
            for idx, session_data in enumerate(sessions, 1):
                # DEBUG: Log first session to verify group_identifier is present
                if idx == 1:
                    logger.info(f"🔍 DEBUG: First session_data keys: {list(session_data.keys())}")
                    logger.info(f"🔍 DEBUG: group_identifier value: {session_data.get('group_identifier')}")
                    logger.info(f"🔍 DEBUG: tournament_phase value: {session_data.get('tournament_phase')}")
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
                    session_objects.append(session)
                    created_sessions.append(session_data)
                except Exception as session_error:
                    logger.error(f"❌ Failed to build session {idx}: {str(session_error)}")
                    logger.error(f"   Session data that caused error: {session_data}")
                    raise

            # Single flush to assign IDs to all sessions in one round-trip
            self.db.flush()
            logger.info(f"✅ Bulk flush complete — {len(session_objects)} sessions assigned IDs")

            # ✅ TOURNAMENT SESSIONS: NO bookings creation
            # Tournament sessions use:
            #   - semester_enrollments (tournament enrollment)
            #   - participant_user_ids (explicit match participants)
            # Bookings are ONLY for regular practice sessions, NOT tournaments

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
