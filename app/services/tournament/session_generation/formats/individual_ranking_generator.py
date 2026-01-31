"""
Individual Ranking Format Generator

Generates sessions for simple individual ranking competitions.
"""
from typing import List, Dict, Any
from datetime import timedelta

from app.models.semester import Semester
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from .base_format_generator import BaseFormatGenerator
from ..utils import get_tournament_venue


class IndividualRankingGenerator(BaseFormatGenerator):
    """
    Generates INDIVIDUAL_RANKING sessions (simple competition format)

    INDIVIDUAL_RANKING tournaments have NO tournament type structure.
    All players compete in a simple competition and are ranked by their results:
    - TIME_BASED: Lowest time wins (e.g., 100m sprint - 3 rounds, best time counts)
    - SCORE_BASED: Highest score wins (e.g., push-ups in 1 minute)
    - DISTANCE_BASED: Longest distance wins (e.g., long jump)
    - PLACEMENT: Manual placement (1st, 2nd, 3rd...)
    """

    def generate(
        self,
        tournament: Semester,
        tournament_type: None,  # Individual ranking has no tournament type
        player_count: int,
        parallel_fields: int,
        session_duration: int,
        break_minutes: int,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate INDIVIDUAL_RANKING sessions

        Args:
            number_of_rounds: Number of rounds to generate (1-10). For example, 100m sprint with 3 attempts.
        """
        sessions = []
        number_of_rounds = kwargs.get('number_of_rounds', 1)

        # Get enrolled players
        enrolled_players = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament.id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).all()
        player_ids = [enrollment.user_id for enrollment in enrolled_players]

        # 🔄 NEW ARCHITECTURE: Create 1 session for ALL rounds (not N sessions)
        # Total duration = (number_of_rounds * session_duration) + ((number_of_rounds - 1) * break_minutes)
        total_duration = (number_of_rounds * session_duration) + ((number_of_rounds - 1) * break_minutes)

        session_start = tournament.start_date
        session_end = session_start + timedelta(minutes=total_duration)

        # Determine description based on scoring type
        scoring_descriptions = {
            'TIME_BASED': f'{number_of_rounds} rounds - All players compete - lowest time wins',
            'SCORE_BASED': f'{number_of_rounds} rounds - All players compete - highest score wins',
            'DISTANCE_BASED': f'{number_of_rounds} rounds - All players compete - longest distance wins',
            'PLACEMENT': f'{number_of_rounds} rounds - All players compete - ranked by placement'
        }
        description = scoring_descriptions.get(
            tournament.scoring_type,
            f'{number_of_rounds} rounds - All players compete and are ranked'
        )

        # Initialize rounds_data structure
        rounds_data = {
            'total_rounds': number_of_rounds,
            'completed_rounds': 0,
            'round_results': {}  # Will store: {'1': {'user_123': '12.5s', ...}, '2': {...}}
        }

        sessions.append({
            'title': f'{tournament.name}',
            'description': description,
            'date_start': session_start,
            'date_end': session_end,
            'game_type': 'Individual Ranking Competition',
            'tournament_phase': 'INDIVIDUAL_RANKING',
            'tournament_round': 1,  # Always 1 since this session contains all rounds
            'tournament_match_number': 1,
            'location': get_tournament_venue(tournament),
            'session_type': 'on_site',
            # ✅ INDIVIDUAL_RANKING metadata
            'ranking_mode': 'ALL_PARTICIPANTS',
            'round_number': 1,
            'expected_participants': player_count,
            'participant_filter': None,
            'group_identifier': None,
            'pod_tier': None,
            # ✅ MATCH STRUCTURE: INDIVIDUAL_RANKING with scoring type
            'match_format': tournament.format,  # INDIVIDUAL_RANKING
            'scoring_type': tournament.scoring_type,  # TIME_BASED, SCORE_BASED, etc.
            'structure_config': {
                'expected_participants': player_count,
                'scoring_method': tournament.scoring_type,
                'description': description,
                'number_of_rounds': number_of_rounds
            },
            # ✅ All enrolled players participate
            'participant_user_ids': player_ids,
            # 🔄 NEW: Rounds data for multi-round tracking
            'rounds_data': rounds_data
        })

        return sessions
