"""
League Format Generator

Generates sessions for league (round-robin) tournaments.
"""
from typing import List, Dict, Any
from datetime import timedelta

from app.models.semester import Semester
from app.models.tournament_type import TournamentType
from app.models.tournament_enums import TournamentPhase
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from .base_format_generator import BaseFormatGenerator
from ..algorithms import RoundRobinPairing
from ..utils import get_tournament_venue


class LeagueGenerator(BaseFormatGenerator):
    """
    Generates league tournament sessions

    INDIVIDUAL_RANKING: N rounds where ALL players compete and rank together.
    HEAD_TO_HEAD: Traditional round robin (1v1 pairing).
    """

    def generate(
        self,
        tournament: Semester,
        tournament_type: TournamentType,
        player_count: int,
        parallel_fields: int,
        session_duration: int,
        break_minutes: int,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate league sessions based on tournament format
        """
        sessions = []

        # ✅ Use tournament.format (from Semester table) to determine match structure
        # This is set by admin in UI and stored in semesters.format column
        tournament_format = tournament.format

        if tournament_format == 'HEAD_TO_HEAD':
            # ✅ HEAD_TO_HEAD: Traditional round robin (1v1 pairings)
            # Total matches = n*(n-1)/2
            # Use pairing algorithm for fair scheduling
            sessions = self._generate_head_to_head_pairings(
                tournament, tournament_type, player_count, parallel_fields, session_duration, break_minutes
            )
        else:
            # ✅ INDIVIDUAL_RANKING: Multi-player ranking rounds
            # Get number of ranking rounds from config (default: n-1 rounds)
            number_of_rounds = tournament_type.config.get('ranking_rounds', player_count - 1)

            # ✅ Get enrolled players for participant_user_ids
            enrolled_players = self.db.query(SemesterEnrollment).filter(
                SemesterEnrollment.semester_id == tournament.id,
                SemesterEnrollment.is_active == True,
                SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
            ).all()
            player_ids = [enrollment.user_id for enrollment in enrolled_players]

            current_time = tournament.start_date

            for round_num in range(1, number_of_rounds + 1):
                session_start = current_time
                session_end = session_start + timedelta(minutes=session_duration)

                sessions.append({
                    'title': f'{tournament.name} - Ranking Round {round_num}',
                    'description': f'All {player_count} players compete and rank in this round',
                    'date_start': session_start,
                    'date_end': session_end,
                    'game_type': f'Ranking Round {round_num}',
                    'tournament_phase': 'League - Multi-Player Ranking',
                    'tournament_round': round_num,
                    'tournament_match_number': round_num,
                    'location': get_tournament_venue(tournament),
                    'session_type': 'on_site',
                    # ✅ UNIFIED RANKING: Ranking metadata
                    'ranking_mode': 'ALL_PARTICIPANTS',
                    'round_number': round_num,  # ✅ MANDATORY: Round number for fixtures display
                    'expected_participants': player_count,
                    'participant_filter': None,
                    'group_identifier': None,
                    'pod_tier': None,
                    # ✅ MATCH STRUCTURE: Format and scoring metadata (from tournament config)
                    'match_format': tournament.format,
                    'scoring_type': tournament.scoring_type,
                    'structure_config': {
                        'expected_participants': player_count,
                        'ranking_criteria': 'final_placement'
                    },
                    # ✅ FIX: Add participant_user_ids with all enrolled players
                    'participant_user_ids': player_ids
                })

                # Move to next time slot
                current_time += timedelta(minutes=session_duration + break_minutes)

        return sessions

    def _generate_head_to_head_pairings(
        self,
        tournament: Semester,
        config: TournamentType,
        player_count: int,
        parallel_fields: int,
        session_duration: int,
        break_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Generate HEAD_TO_HEAD round robin sessions (1v1 pairings)

        Uses circle/rotation algorithm for fair scheduling.
        Total matches = n*(n-1)/2
        Total rounds = n-1 if even, n if odd

        With parallel_fields > 1, multiple matches can run simultaneously.
        """
        sessions = []

        # Get enrolled players
        enrolled_players = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament.id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).all()

        player_ids = [enrollment.user_id for enrollment in enrolled_players]

        # ✅ Round robin pairing algorithm (circle method)
        # For even number: n-1 rounds, for odd: n rounds (with byes)
        num_rounds = RoundRobinPairing.calculate_rounds(player_count)

        current_time = tournament.start_date
        field_slots = [current_time for _ in range(parallel_fields)]  # Track each field's next available time

        for round_num in range(1, num_rounds + 1):
            # Generate pairings for this round using circle method
            round_pairings = RoundRobinPairing.get_round_pairings(player_ids, round_num)

            field_index = 0  # Distribute matches across fields

            for match_num, (player1_id, player2_id) in enumerate(round_pairings, start=1):
                if player1_id is None or player2_id is None:
                    # Skip bye matches
                    continue

                # Assign to next available field
                session_start = field_slots[field_index]
                session_end = session_start + timedelta(minutes=session_duration)

                sessions.append({
                    'title': f'{tournament.name} - Round {round_num} - Match {match_num}',
                    'description': f'Round {round_num} head-to-head match (Field {field_index + 1})',
                    'date_start': session_start,
                    'date_end': session_end,
                    'game_type': f'Round {round_num}',
                    'tournament_phase': TournamentPhase.GROUP_STAGE.value,
                    'tournament_round': round_num,
                    'tournament_match_number': match_num,
                    'location': get_tournament_venue(tournament),
                    'session_type': 'on_site',
                    # ✅ HEAD_TO_HEAD: 1v1 match metadata
                    'ranking_mode': 'ALL_PARTICIPANTS',
                    'round_number': round_num,
                    'expected_participants': 2,
                    'participant_filter': None,
                    'group_identifier': None,
                    'pod_tier': None,
                    # ✅ MATCH STRUCTURE: HEAD_TO_HEAD format (from tournament config)
                    'match_format': tournament.format,  # Should be HEAD_TO_HEAD
                    'scoring_type': tournament.scoring_type,  # Usually SCORE_BASED for HEAD_TO_HEAD
                    'structure_config': {
                        'expected_participants': 2,
                        'match_type': 'round_robin',
                        'field_number': field_index + 1  # ✅ NEW: Track which field
                    },
                    # ✅ EXPLICIT PARTICIPANTS: 2 players
                    'participant_user_ids': [player1_id, player2_id]
                })

                # Update field slot to next available time
                field_slots[field_index] += timedelta(minutes=session_duration + break_minutes)

                # Move to next field (round-robin field assignment)
                field_index = (field_index + 1) % parallel_fields

        return sessions
