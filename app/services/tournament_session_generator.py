"""
Tournament Session Generator Service

Generates tournament sessions AFTER enrollment closes based on tournament type configuration.

CRITICAL CONSTRAINT: This service is ONLY called after the enrollment period ends,
ensuring stable player count and preventing mid-tournament enrollment changes.
"""
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import math
import json

from app.models.semester import Semester
from app.models.tournament_type import TournamentType
from app.models.session import Session as SessionModel
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus


class TournamentSessionGenerator:
    """
    Generates tournament session structures based on tournament type and player count
    """

    def __init__(self, db: Session):
        self.db = db

    def can_generate_sessions(self, tournament_id: int) -> Tuple[bool, str]:
        """
        Check if tournament is ready for session generation

        Returns:
            (can_generate, reason)
        """
        tournament = self.db.query(Semester).filter(Semester.id == tournament_id).first()
        if not tournament:
            return False, "Tournament not found"

        # Check if already generated
        if tournament.sessions_generated:
            return False, f"Sessions already generated at {tournament.sessions_generated_at}"

        # Check if tournament has a type configured
        if not tournament.tournament_type_id:
            return False, "Tournament type not configured"

        # Check if enrollment is closed (tournament status must be IN_PROGRESS or later)
        if tournament.tournament_status not in ["IN_PROGRESS", "COMPLETED"]:
            return False, f"Tournament not ready for session generation. Current status: {tournament.tournament_status}. Sessions can only be generated when status is IN_PROGRESS."

        # Check if there are enough enrolled players
        active_enrollment_count = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).count()

        if active_enrollment_count < 4:
            return False, f"Not enough players enrolled. Need at least 4, have {active_enrollment_count}"

        return True, "Ready for session generation"

    def generate_sessions(
        self,
        tournament_id: int,
        parallel_fields: int = 1,
        session_duration_minutes: int = 90,
        break_minutes: int = 15
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Generate all tournament sessions based on tournament type and enrolled player count

        Args:
            tournament_id: Tournament (Semester) ID
            parallel_fields: Number of fields available for parallel matches
            session_duration_minutes: Duration of each session
            break_minutes: Break time between sessions

        Returns:
            (success, message, sessions_created)
        """
        # Validation
        can_generate, reason = self.can_generate_sessions(tournament_id)
        if not can_generate:
            return False, reason, []

        # Fetch tournament and config
        tournament = self.db.query(Semester).filter(Semester.id == tournament_id).first()
        tournament_type = self.db.query(TournamentType).filter(
            TournamentType.id == tournament.tournament_type_id
        ).first()

        # Get enrolled player count
        player_count = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).count()

        # Validate player count against tournament type constraints
        is_valid, error_msg = tournament_type.validate_player_count(player_count)
        if not is_valid:
            return False, error_msg, []

        # Generate session structure based on tournament type
        if tournament_type.code == "league":
            sessions = self._generate_league_sessions(
                tournament, tournament_type, player_count, parallel_fields,
                session_duration_minutes, break_minutes
            )
        elif tournament_type.code == "knockout":
            sessions = self._generate_knockout_sessions(
                tournament, tournament_type, player_count, parallel_fields,
                session_duration_minutes, break_minutes
            )
        elif tournament_type.code == "group_knockout":
            sessions = self._generate_group_knockout_sessions(
                tournament, tournament_type, player_count, parallel_fields,
                session_duration_minutes, break_minutes
            )
        elif tournament_type.code == "swiss":
            sessions = self._generate_swiss_sessions(
                tournament, tournament_type, player_count, parallel_fields,
                session_duration_minutes, break_minutes
            )
        else:
            return False, f"Unknown tournament type: {tournament_type.code}", []

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
            created_sessions.append(session_data)

        # Mark tournament as sessions_generated
        tournament.sessions_generated = True
        tournament.sessions_generated_at = datetime.utcnow()

        self.db.commit()

        return True, f"Successfully generated {len(created_sessions)} sessions", created_sessions

    def _generate_league_sessions(
        self,
        tournament: Semester,
        config: TournamentType,
        player_count: int,
        parallel_fields: int,
        session_duration: int,
        break_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Generate league (round robin) sessions

        Every player plays every other player once.
        Total matches = n*(n-1)/2
        """
        sessions = []
        total_matches = (player_count * (player_count - 1)) // 2
        rounds = player_count - 1 if player_count % 2 == 0 else player_count

        current_time = tournament.start_date
        match_counter = 1

        for round_num in range(1, rounds + 1):
            matches_in_round = player_count // 2

            for match_in_round in range(1, matches_in_round + 1):
                session_start = current_time
                session_end = session_start + timedelta(minutes=session_duration)

                sessions.append({
                    'title': f'{tournament.name} - Round {round_num} - Match {match_in_round}',
                    'description': f'League match {match_counter} of {total_matches}',
                    'date_start': session_start,
                    'date_end': session_end,
                    'game_type': f'Round {round_num}',
                    'tournament_phase': 'League',
                    'tournament_round': round_num,
                    'tournament_match_number': match_in_round,
                    'location': tournament.location_venue or 'TBD',
                    'session_type': 'on_site'
                })

                match_counter += 1

                # If we have parallel fields, schedule next match at same time
                if match_in_round % parallel_fields != 0:
                    continue
                else:
                    # Move to next time slot
                    current_time += timedelta(minutes=session_duration + break_minutes)

            # Move to next round
            current_time += timedelta(minutes=break_minutes)

        return sessions

    def _generate_knockout_sessions(
        self,
        tournament: Semester,
        config: TournamentType,
        player_count: int,
        parallel_fields: int,
        session_duration: int,
        break_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Generate knockout (single elimination) sessions

        Total matches = n - 1
        """
        sessions = []
        total_rounds = math.ceil(math.log2(player_count))
        round_names = config.config.get('round_names', {})

        current_time = tournament.start_date
        match_counter = 1

        for round_num in range(1, total_rounds + 1):
            players_in_round = player_count // (2 ** (round_num - 1))
            matches_in_round = players_in_round // 2

            round_name = round_names.get(str(players_in_round), f"Round of {players_in_round}")

            for match_in_round in range(1, matches_in_round + 1):
                session_start = current_time
                session_end = session_start + timedelta(minutes=session_duration)

                sessions.append({
                    'title': f'{tournament.name} - {round_name} - Match {match_in_round}',
                    'description': f'Knockout match {match_counter}',
                    'date_start': session_start,
                    'date_end': session_end,
                    'game_type': round_name,
                    'tournament_phase': 'Knockout',
                    'tournament_round': round_num,
                    'tournament_match_number': match_in_round,
                    'location': tournament.location_venue or 'TBD',
                    'session_type': 'on_site'
                })

                match_counter += 1

                # If we have parallel fields, schedule next match at same time
                if match_in_round % parallel_fields != 0:
                    continue
                else:
                    # Move to next time slot
                    current_time += timedelta(minutes=session_duration + break_minutes)

            # Break between rounds
            current_time += timedelta(minutes=break_minutes * 2)

        # Add 3rd place playoff if configured
        if config.config.get('third_place_playoff'):
            sessions.append({
                'title': f'{tournament.name} - 3rd Place Playoff',
                'description': '3rd place playoff match',
                'date_start': current_time,
                'date_end': current_time + timedelta(minutes=session_duration),
                'game_type': '3rd Place Playoff',
                'tournament_phase': 'Knockout',
                'tournament_round': total_rounds,
                'tournament_match_number': 999,  # Special match number
                'location': tournament.location_venue or 'TBD',
                'session_type': 'on_site'
            })

        return sessions

    def _generate_group_knockout_sessions(
        self,
        tournament: Semester,
        config: TournamentType,
        player_count: int,
        parallel_fields: int,
        session_duration: int,
        break_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Generate group stage + knockout sessions

        Hybrid format with group stage followed by knockout playoffs
        """
        sessions = []

        # Get group configuration
        group_config = config.config.get('group_configuration', {}).get(f'{player_count}_players')
        if not group_config:
            # Fallback: Create groups of 4
            groups_count = player_count // 4
            players_per_group = 4
            qualifiers_per_group = 2
        else:
            groups_count = group_config['groups']
            players_per_group = group_config['players_per_group']
            qualifiers_per_group = group_config['qualifiers']

        current_time = tournament.start_date

        # PHASE 1: GROUP STAGE
        match_counter = 1
        for group_num in range(1, groups_count + 1):
            # Each group plays round robin
            group_matches = (players_per_group * (players_per_group - 1)) // 2
            group_rounds = players_per_group - 1 if players_per_group % 2 == 0 else players_per_group

            for round_num in range(1, group_rounds + 1):
                matches_in_round = players_per_group // 2

                for match_in_round in range(1, matches_in_round + 1):
                    session_start = current_time
                    session_end = session_start + timedelta(minutes=session_duration)

                    sessions.append({
                        'title': f'{tournament.name} - Group {chr(64 + group_num)} - Round {round_num} - Match {match_in_round}',
                        'description': f'Group stage match {match_counter}',
                        'date_start': session_start,
                        'date_end': session_end,
                        'game_type': f'Group {chr(64 + group_num)} - Round {round_num}',
                        'tournament_phase': 'Group Stage',
                        'tournament_round': round_num,
                        'tournament_match_number': match_counter,
                        'location': tournament.location_venue or 'TBD',
                        'session_type': 'on_site'
                    })

                    match_counter += 1

                    # Schedule parallel matches
                    if match_in_round % parallel_fields != 0:
                        continue
                    else:
                        current_time += timedelta(minutes=session_duration + break_minutes)

        # Break between phases
        current_time += timedelta(minutes=break_minutes * 4)

        # PHASE 2: KNOCKOUT STAGE
        knockout_players = groups_count * qualifiers_per_group
        knockout_rounds = math.ceil(math.log2(knockout_players))
        round_names = config.config.get('round_names', {})

        for round_num in range(1, knockout_rounds + 1):
            players_in_round = knockout_players // (2 ** (round_num - 1))
            matches_in_round = players_in_round // 2

            round_name = round_names.get(str(players_in_round), f"Round of {players_in_round}")

            for match_in_round in range(1, matches_in_round + 1):
                session_start = current_time
                session_end = session_start + timedelta(minutes=session_duration)

                sessions.append({
                    'title': f'{tournament.name} - {round_name} - Match {match_in_round}',
                    'description': f'Knockout stage match',
                    'date_start': session_start,
                    'date_end': session_end,
                    'game_type': round_name,
                    'tournament_phase': 'Knockout Stage',
                    'tournament_round': round_num,
                    'tournament_match_number': match_in_round,
                    'location': tournament.location_venue or 'TBD',
                    'session_type': 'on_site'
                })

                match_counter += 1

                # Schedule parallel matches
                if match_in_round % parallel_fields != 0:
                    continue
                else:
                    current_time += timedelta(minutes=session_duration + break_minutes)

            # Break between rounds
            current_time += timedelta(minutes=break_minutes * 2)

        return sessions

    def _generate_swiss_sessions(
        self,
        tournament: Semester,
        config: TournamentType,
        player_count: int,
        parallel_fields: int,
        session_duration: int,
        break_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Generate Swiss system sessions

        Typical rounds = log2(n) rounded up
        """
        sessions = []
        total_rounds = math.ceil(math.log2(player_count))

        current_time = tournament.start_date
        match_counter = 1

        for round_num in range(1, total_rounds + 1):
            matches_in_round = player_count // 2

            for match_in_round in range(1, matches_in_round + 1):
                session_start = current_time
                session_end = session_start + timedelta(minutes=session_duration)

                sessions.append({
                    'title': f'{tournament.name} - Round {round_num} - Match {match_in_round}',
                    'description': f'Swiss system round {round_num}',
                    'date_start': session_start,
                    'date_end': session_end,
                    'game_type': f'Round {round_num}',
                    'tournament_phase': 'Swiss System',
                    'tournament_round': round_num,
                    'tournament_match_number': match_in_round,
                    'location': tournament.location_venue or 'TBD',
                    'session_type': 'on_site'
                })

                match_counter += 1

                # Schedule parallel matches
                if match_in_round % parallel_fields != 0:
                    continue
                else:
                    current_time += timedelta(minutes=session_duration + break_minutes)

            # Break between rounds
            current_time += timedelta(minutes=break_minutes * 2)

        return sessions
