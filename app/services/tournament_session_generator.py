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
        Generate league sessions based on tournament format

        INDIVIDUAL_RANKING: N rounds where ALL players compete and rank together.
        HEAD_TO_HEAD: Traditional round robin (1v1 pairing).
        """
        sessions = []

        # ✅ NEW: Use tournament_type.format to determine match structure
        tournament_format = getattr(config, 'format', 'INDIVIDUAL_RANKING')

        if tournament_format == 'HEAD_TO_HEAD':
            # ✅ HEAD_TO_HEAD: Traditional round robin (1v1 pairings)
            # Total matches = n*(n-1)/2
            # Use pairing algorithm for fair scheduling
            sessions = self._generate_round_robin_pairings(
                tournament, config, player_count, parallel_fields, session_duration, break_minutes
            )
        else:
            # ✅ INDIVIDUAL_RANKING: Multi-player ranking rounds
            # Get number of ranking rounds from config (default: n-1 rounds)
            number_of_rounds = config.config.get('ranking_rounds', player_count - 1)

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
                    'location': tournament.location_venue or 'TBD',
                    'session_type': 'on_site',
                    # ✅ UNIFIED RANKING: Ranking metadata
                    'ranking_mode': 'ALL_PARTICIPANTS',
                    'round_number': round_num,  # ✅ MANDATORY: Round number for fixtures display
                    'expected_participants': player_count,
                    'participant_filter': None,
                    'group_identifier': None,
                    'pod_tier': None,
                    # ✅ MATCH STRUCTURE: Format and scoring metadata
                    'match_format': 'INDIVIDUAL_RANKING',
                    'scoring_type': 'PLACEMENT',
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

    def _calculate_optimal_group_distribution(self, player_count: int) -> Dict[str, Any]:
        """
        Calculate optimal group distribution for any player count.

        Business Rules:
        - Minimum group size: 3 players
        - Maximum group size: 5 players
        - Prefer balanced groups (4 players ideal)
        - Top 2 from each group advance to knockout

        Examples:
        - 8 players → 2 groups of 4
        - 9 players → 3 groups of 3
        - 10 players → 2 groups of 5
        - 11 players → 2 groups of 4, 1 group of 3
        - 12 players → 3 groups of 4
        - 13 players → 2 groups of 5, 1 group of 3

        Returns:
            {
                'groups_count': int,
                'group_sizes': List[int],  # Size of each group
                'qualifiers_per_group': int,  # Always 2
                'group_rounds': int  # Matches per group
            }
        """
        if player_count < 6:
            # Special case: less than 6 players
            # Use single group or reject
            return {
                'groups_count': 1,
                'group_sizes': [player_count],
                'qualifiers_per_group': min(2, player_count - 1),
                'group_rounds': max(1, player_count - 1)
            }

        # Strategy: Try to create balanced groups
        # Prefer groups of 4, but allow 3 and 5

        # Try different group counts and find best distribution
        best_distribution = None
        best_score = float('inf')  # Lower score = more balanced

        for num_groups in range(2, player_count // 3 + 2):
            # Calculate base size and remainder
            base_size = player_count // num_groups
            remainder = player_count % num_groups

            # Check if base_size is valid (3-5)
            if base_size < 3 or base_size > 5:
                continue

            # Check if we can distribute remainder (some groups get +1)
            max_size = base_size + (1 if remainder > 0 else 0)
            if max_size > 5:
                continue

            # Create group sizes
            group_sizes = [base_size + 1 if i < remainder else base_size for i in range(num_groups)]

            # Calculate balance score (variance in group sizes)
            # Lower variance = better balance
            avg_size = sum(group_sizes) / len(group_sizes)
            variance = sum((size - avg_size) ** 2 for size in group_sizes)

            # Prefer 4-player groups (add bonus if close to 4)
            size_4_bonus = sum(abs(size - 4) for size in group_sizes)
            score = variance + size_4_bonus * 0.1

            if score < best_score:
                best_score = score
                best_distribution = {
                    'groups_count': num_groups,
                    'group_sizes': group_sizes,
                    'qualifiers_per_group': 2,
                    'group_rounds': max(group_sizes) - 1  # Rounds = max_size - 1
                }

        return best_distribution

    def _calculate_knockout_structure(self, qualifiers: int) -> Dict[str, Any]:
        """
        Calculate knockout bracket structure based on number of qualifiers

        Implements the business logic decisions:
        - 4 qualifiers: No byes, no bronze
        - 6 qualifiers: 2 byes (seeds 1-2), bronze match
        - 8 qualifiers: No byes, bronze match
        - 10 qualifiers: 4 byes (seeds 1-4), bronze match
        - 12 qualifiers: 4 byes (seeds 1-4), bronze match
        - Other: Round up to next power of 2, bronze for 8+

        Returns:
            {
                'play_in_matches': int,  # Number of play-in matches
                'byes': int,             # Number of byes
                'bracket_size': int,     # Final bracket size (power of 2)
                'has_bronze': bool       # Whether to include 3rd place match
            }
        """
        if qualifiers == 4:
            return {
                'play_in_matches': 0,
                'byes': 0,
                'bracket_size': 4,
                'has_bronze': False  # ✅ Decision: No bronze for 4-player knockout
            }

        elif qualifiers == 6:
            # ✅ Decision: 6 → 4 bracket with byes
            return {
                'play_in_matches': 2,  # Seeds 3-6 play (2 matches)
                'byes': 2,             # Seeds 1-2 bye to semifinals
                'bracket_size': 4,
                'has_bronze': True     # ✅ Decision: Bronze for 8+ knockouts (bracket_size=4 but qualifiers=6)
            }

        elif qualifiers == 8:
            return {
                'play_in_matches': 0,
                'byes': 0,
                'bracket_size': 8,
                'has_bronze': True
            }

        elif qualifiers == 10:
            # ✅ Decision: 10 → 8 bracket with byes
            return {
                'play_in_matches': 3,  # Seeds 5-10 play (3 matches: 5v10, 6v9, 7v8)
                'byes': 4,             # Seeds 1-4 bye to quarterfinals
                'bracket_size': 8,
                'has_bronze': True
            }

        elif qualifiers == 12:
            # ✅ Decision: 12 → 8 bracket with byes
            return {
                'play_in_matches': 4,  # Seeds 5-12 play (4 matches)
                'byes': 4,             # Seeds 1-4 bye to quarterfinals
                'bracket_size': 8,
                'has_bronze': True
            }

        else:
            # For other sizes, round up to next power of 2
            bracket_size = 2 ** math.ceil(math.log2(qualifiers))
            byes = bracket_size - qualifiers
            play_in_matches = (qualifiers - byes) // 2

            return {
                'play_in_matches': play_in_matches,
                'byes': byes,
                'bracket_size': bracket_size,
                'has_bronze': bracket_size >= 8  # ✅ Decision: Bronze only for 8+ brackets
            }

    def _generate_round_robin_pairings(
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
        num_rounds = player_count if player_count % 2 == 1 else player_count - 1

        current_time = tournament.start_date
        field_slots = [current_time for _ in range(parallel_fields)]  # Track each field's next available time

        for round_num in range(1, num_rounds + 1):
            # Generate pairings for this round using circle method
            round_pairings = self._get_round_robin_round_pairings(player_ids, round_num)

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
                    'tournament_phase': 'League - Round Robin',
                    'tournament_round': round_num,
                    'tournament_match_number': match_num,
                    'location': tournament.location_venue or 'TBD',
                    'session_type': 'on_site',
                    # ✅ HEAD_TO_HEAD: 1v1 match metadata
                    'ranking_mode': 'ALL_PARTICIPANTS',
                    'round_number': round_num,
                    'expected_participants': 2,
                    'participant_filter': None,
                    'group_identifier': None,
                    'pod_tier': None,
                    # ✅ MATCH STRUCTURE: HEAD_TO_HEAD format
                    'match_format': 'HEAD_TO_HEAD',
                    'scoring_type': 'SCORE_BASED',
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

    def _get_round_robin_round_pairings(self, player_ids: List[int], round_num: int) -> List[Tuple[int, int]]:
        """
        Generate pairings for a specific round using circle/rotation algorithm

        Args:
            player_ids: List of player IDs
            round_num: Round number (1-indexed)

        Returns:
            List of (player1_id, player2_id) tuples for this round
        """
        n = len(player_ids)
        pairings = []

        if n % 2 == 1:
            # Odd number: add dummy player for bye
            players = player_ids + [None]
            n += 1
        else:
            players = player_ids[:]

        # Circle method: fix first player, rotate others
        # Round 1: [1,2,3,4,5,6] → pairs: (1,6), (2,5), (3,4)
        # Round 2: [1,3,4,5,6,2] → pairs: (1,2), (3,6), (4,5)
        # etc.

        # Rotation offset based on round_num
        rotated = [players[0]] + players[1:][round_num - 1:] + players[1:][:round_num - 1]

        # Pair first with last, second with second-to-last, etc.
        for i in range(n // 2):
            player1 = rotated[i]
            player2 = rotated[n - 1 - i]
            pairings.append((player1, player2))

        return pairings

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

        ✅ UNIFIED RANKING: All players participate in each round and are ranked.
        The tier (round level) affects point distribution, but everyone competes.

        Total matches = n - 1 rounds (progressive elimination structure)
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
                    'description': f'All {player_count} players compete - {round_name} tier',
                    'date_start': session_start,
                    'date_end': session_end,
                    'game_type': round_name,
                    'tournament_phase': 'Knockout',
                    'tournament_round': round_num,
                    'tournament_match_number': match_in_round,
                    'location': tournament.location_venue or 'TBD',
                    'session_type': 'on_site',
                    # ✅ UNIFIED RANKING: Tiered ranking metadata (all players compete, tier affects points)
                    'ranking_mode': 'TIERED',
                    'round_number': round_num,  # ✅ MANDATORY: Round number for fixtures display
                    'expected_participants': player_count,
                    'participant_filter': None,
                    'group_identifier': None,
                    'pod_tier': round_num,  # Tier indicates knockout stage level
                    # ✅ MATCH STRUCTURE: Format and scoring metadata
                    'match_format': 'INDIVIDUAL_RANKING',  # All compete together, ranked by placement
                    'scoring_type': 'PLACEMENT',
                    'structure_config': {
                        'expected_participants': player_count,
                        'round_name': round_name,
                        'tier': round_num
                    }
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
                'description': 'All players compete for 3rd place tier',
                'date_start': current_time,
                'date_end': current_time + timedelta(minutes=session_duration),
                'game_type': '3rd Place Playoff',
                'tournament_phase': 'Knockout',
                'tournament_round': total_rounds,
                'tournament_match_number': 999,  # Special match number
                'location': tournament.location_venue or 'TBD',
                'session_type': 'on_site',
                # ✅ UNIFIED RANKING: 3rd place playoff metadata
                'ranking_mode': 'TIERED',
                'round_number': total_rounds,  # ✅ MANDATORY: Round number for fixtures display
                'expected_participants': player_count,
                'participant_filter': None,
                'group_identifier': None,
                'pod_tier': total_rounds,  # Same tier as finals
                # ✅ MATCH STRUCTURE: Format and scoring metadata
                'match_format': 'INDIVIDUAL_RANKING',
                'scoring_type': 'PLACEMENT',
                'structure_config': {
                    'expected_participants': player_count,
                    'round_name': '3rd Place Playoff',
                    'tier': total_rounds
                }
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

        ✅ MATCH PARTICIPANTS: Explicit participant_user_ids for each match
        ✅ FIX: Group sessions ONLY include group members (not all tournament players)

        Group Stage: Players divided into groups, each group ranks separately.
        Knockout Stage: Top qualifiers from each group advance to multi-player knockout.
        """
        sessions = []

        # ✅ CRITICAL: Get enrolled players first
        enrolled_players = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament.id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).all()

        player_ids = [enrollment.user_id for enrollment in enrolled_players]

        # ✅ NEW: Use dynamic group distribution (supports odd player counts)
        # Try config first, then fall back to dynamic calculation
        group_config = config.config.get('group_configuration', {}).get(f'{player_count}_players')

        if group_config:
            # Use predefined config from tournament_type
            groups_count = group_config['groups']
            qualifiers_per_group = group_config['qualifiers']
            group_rounds = group_config.get('rounds', 3)
            # Sequential distribution (config doesn't specify sizes)
            group_sizes = [len(player_ids) // groups_count] * groups_count
            remainder = len(player_ids) % groups_count
            for i in range(remainder):
                group_sizes[i] += 1
        else:
            # ✅ NEW: Dynamic calculation for flexible player counts
            distribution = self._calculate_optimal_group_distribution(player_count)
            groups_count = distribution['groups_count']
            group_sizes = distribution['group_sizes']
            qualifiers_per_group = distribution['qualifiers_per_group']
            group_rounds = distribution['group_rounds']

        # ✅ NEW: Assign players to groups with variable sizes
        group_assignments = {}  # {group_name: [user_id1, user_id2, ...]}
        player_index = 0

        for group_num in range(1, groups_count + 1):
            group_name = chr(64 + group_num)  # A, B, C, D, E, ...
            group_size = group_sizes[group_num - 1]
            group_assignments[group_name] = player_ids[player_index:player_index + group_size]
            player_index += group_size

        current_time = tournament.start_date

        # ============================================================================
        # PHASE 1: GROUP STAGE (ISOLATED GROUPS)
        # ============================================================================
        # ✅ NEW: Use semester.format first (admin override), fallback to tournament_type.format
        tournament_format = getattr(tournament, 'format', None) or getattr(config, 'format', 'INDIVIDUAL_RANKING')

        if tournament_format == 'HEAD_TO_HEAD':
            # ✅ HEAD_TO_HEAD: Generate round robin pairings within each group
            for group_num in range(1, groups_count + 1):
                group_name = chr(64 + group_num)  # A, B, C, D
                group_participant_ids = group_assignments.get(group_name, [])
                group_size = len(group_participant_ids)

                # Calculate rounds for this group
                num_rounds = group_size if group_size % 2 == 1 else group_size - 1

                for round_num in range(1, num_rounds + 1):
                    # Generate pairings for this round
                    round_pairings = self._get_round_robin_round_pairings(group_participant_ids, round_num)

                    for match_num, (player1_id, player2_id) in enumerate(round_pairings, start=1):
                        if player1_id is None or player2_id is None:
                            # Skip bye matches
                            continue

                        session_start = current_time
                        session_end = session_start + timedelta(minutes=session_duration)

                        sessions.append({
                            'title': f'{tournament.name} - Group {group_name} - Round {round_num} - Match {match_num}',
                            'description': f'Group {group_name} head-to-head match',
                            'date_start': session_start,
                            'date_end': session_end,
                            'game_type': f'Group {group_name} - Round {round_num}',
                            'tournament_phase': 'Group Stage',
                            'tournament_round': round_num,
                            'tournament_match_number': match_num,
                            'location': tournament.location_venue or 'TBD',
                            'session_type': 'on_site',
                            # ✅ HEAD_TO_HEAD: Group stage metadata
                            'ranking_mode': 'GROUP_ISOLATED',
                            'group_identifier': group_name,
                            'round_number': round_num,
                            'expected_participants': 2,
                            'participant_filter': 'group_membership',
                            'pod_tier': None,
                            # ✅ MATCH STRUCTURE: HEAD_TO_HEAD format
                            'match_format': 'HEAD_TO_HEAD',
                            'scoring_type': 'SCORE_BASED',
                            'structure_config': {
                                'group': group_name,
                                'group_size': group_size,
                                'expected_participants': 2
                            },
                            # ✅ EXPLICIT PARTICIPANTS: 2 players
                            'participant_user_ids': [player1_id, player2_id]
                        })

                        current_time += timedelta(minutes=session_duration + break_minutes)
        else:
            # ✅ INDIVIDUAL_RANKING: Multi-player ranking within each group
            for group_num in range(1, groups_count + 1):
                group_name = chr(64 + group_num)  # A, B, C, D

                # ✅ CRITICAL: Get explicit participant list for this group
                group_participant_ids = group_assignments.get(group_name, [])

                for round_num in range(1, group_rounds + 1):
                    session_start = current_time
                    session_end = session_start + timedelta(minutes=session_duration)

                    sessions.append({
                        'title': f'{tournament.name} - Group {group_name} - Round {round_num}',
                        'description': f'Group {group_name} ranking round ({len(group_participant_ids)} players)',
                        'date_start': session_start,
                        'date_end': session_end,
                        'game_type': f'Group {group_name} - Round {round_num}',
                        'tournament_phase': 'Group Stage',
                        'tournament_round': round_num,
                        'tournament_match_number': (group_num - 1) * group_rounds + round_num,
                        'location': tournament.location_venue or 'TBD',
                        'session_type': 'on_site',
                        # ✅ UNIFIED RANKING: Group isolation metadata
                        'ranking_mode': 'GROUP_ISOLATED',
                        'group_identifier': group_name,
                        'round_number': round_num,  # ✅ MANDATORY: Round number for fixtures display
                        'expected_participants': len(group_participant_ids),
                        'participant_filter': 'group_membership',
                        'pod_tier': None,
                        # ✅ MATCH STRUCTURE: Format and scoring metadata
                        'match_format': 'INDIVIDUAL_RANKING',  # Within group
                        'scoring_type': 'PLACEMENT',
                        'structure_config': {
                            'group': group_name,
                            'group_size': len(group_participant_ids),
                            'expected_participants': len(group_participant_ids)
                        },
                        # ✅ EXPLICIT PARTICIPANTS: No runtime filtering!
                        'participant_user_ids': group_participant_ids
                    })

                    current_time += timedelta(minutes=session_duration + break_minutes)

        # Break between phases
        current_time += timedelta(minutes=break_minutes * 4)

        # ============================================================================
        # PHASE 2: KNOCKOUT STAGE (TOP QUALIFIERS ONLY) - WITH BYE LOGIC
        # ============================================================================
        knockout_players = groups_count * qualifiers_per_group
        round_names = config.config.get('round_names', {})

        # ✅ NEW: Calculate knockout structure (byes, play-in, bronze)
        structure = self._calculate_knockout_structure(knockout_players)
        bracket_size = structure['bracket_size']
        play_in_matches = structure['play_in_matches']
        has_bronze = structure['has_bronze']

        # ============================================================================
        # PHASE 2A: PLAY-IN ROUND (if needed)
        # ============================================================================
        if play_in_matches > 0:
            # Seeds (byes + 1) onwards compete in play-in
            for match_num in range(1, play_in_matches + 1):
                seed_high = structure['byes'] + match_num
                seed_low = knockout_players - (match_num - 1)

                session_start = current_time
                session_end = session_start + timedelta(minutes=session_duration)

                sessions.append({
                    'title': f'{tournament.name} - Play-in - Match {match_num}',
                    'description': f'Play-in match: Seed {seed_high} vs Seed {seed_low}',
                    'date_start': session_start,
                    'date_end': session_end,
                    'game_type': 'Play-in Round',
                    'tournament_phase': 'Knockout Stage',
                    'tournament_round': 0,  # Play-in is round 0
                    'tournament_match_number': match_num,
                    'location': tournament.location_venue or 'TBD',
                    'session_type': 'on_site',
                    # ✅ UNIFIED RANKING: Play-in metadata
                    'ranking_mode': 'QUALIFIED_ONLY',
                    'round_number': 0,  # ✅ MANDATORY: Round number for fixtures display (play-in = round 0)
                    'expected_participants': 2,  # Head-to-head
                    'participant_filter': 'seeded_qualifiers',
                    'group_identifier': None,
                    'pod_tier': None,
                    # ✅ MATCH STRUCTURE: Format and scoring metadata
                    'match_format': 'HEAD_TO_HEAD',  # 1v1 elimination
                    'scoring_type': 'PLACEMENT',
                    'structure_config': {
                        'expected_participants': 2,
                        'round_name': 'Play-in Round',
                        'seed_high': seed_high,
                        'seed_low': seed_low,
                        'qualified_count': knockout_players
                    },
                    # ⚠️ participant_user_ids = NULL until group stage completes
                    'participant_user_ids': None
                })

                # ✅ SEQUENTIAL SCHEDULING: All matches happen one after another (one-day tournament)
                current_time += timedelta(minutes=session_duration + break_minutes)

            # Break after play-in round
            current_time += timedelta(minutes=break_minutes * 2)

        # ============================================================================
        # PHASE 2B: MAIN KNOCKOUT BRACKET
        # ============================================================================
        knockout_rounds = math.ceil(math.log2(bracket_size))

        # ✅ Calculate seeding placeholders for first round (based on group results)
        # For 2 groups (A, B): A1 vs B2, B1 vs A2
        # For 3 groups (A, B, C): A1 vs C2, B1 vs A2, C1 vs B2
        # etc.
        group_letters = [chr(65 + i) for i in range(groups_count)]  # ['A', 'B', 'C', ...]

        for round_num in range(1, knockout_rounds + 1):
            players_in_round = bracket_size // (2 ** (round_num - 1))
            matches_in_round = players_in_round // 2

            round_name = round_names.get(str(players_in_round), f"Round of {players_in_round}")

            for match_in_round in range(1, matches_in_round + 1):
                session_start = current_time
                session_end = session_start + timedelta(minutes=session_duration)

                # ✅ Calculate seeding placeholders for first knockout round
                seeding_info = {}
                if round_num == 1:
                    # First round uses group qualifiers
                    # Standard bracket seeding: 1 vs last, 2 vs second-to-last, etc.
                    # For 4 qualifiers (2 groups): A1 vs B2, B1 vs A2
                    # For 8 qualifiers (4 groups): A1 vs D2, B1 vs C2, C1 vs B2, D1 vs A2

                    if knockout_players == 4:  # 2 groups
                        if match_in_round == 1:
                            seeding_info = {'matchup': 'A1 vs B2', 'seed_1': 'A1', 'seed_2': 'B2'}
                        elif match_in_round == 2:
                            seeding_info = {'matchup': 'B1 vs A2', 'seed_1': 'B1', 'seed_2': 'A2'}
                    elif knockout_players == 8:  # 4 groups
                        matchups = [
                            ('A1', 'D2'), ('B1', 'C2'), ('C1', 'B2'), ('D1', 'A2')
                        ]
                        if match_in_round <= len(matchups):
                            seed_1, seed_2 = matchups[match_in_round - 1]
                            seeding_info = {'matchup': f'{seed_1} vs {seed_2}', 'seed_1': seed_1, 'seed_2': seed_2}
                else:
                    # Later rounds use previous match winners
                    seeding_info = {'matchup': f'Winner of previous matches', 'round': round_num}

                sessions.append({
                    'title': f'{tournament.name} - {round_name} - Match {match_in_round}',
                    'description': f'Knockout stage match - top {knockout_players} qualifiers',
                    'date_start': session_start,
                    'date_end': session_end,
                    'game_type': round_name,
                    'tournament_phase': 'Knockout Stage',
                    'tournament_round': round_num,
                    'tournament_match_number': match_in_round,
                    'location': tournament.location_venue or 'TBD',
                    'session_type': 'on_site',
                    # ✅ UNIFIED RANKING: Knockout stage metadata
                    'ranking_mode': 'QUALIFIED_ONLY',
                    'round_number': round_num,  # ✅ MANDATORY: Round number for fixtures display
                    'expected_participants': 2 if round_num >= knockout_rounds - 1 else players_in_round,
                    'participant_filter': 'seeded_qualifiers',
                    'group_identifier': None,
                    'pod_tier': None,
                    # ✅ MATCH STRUCTURE: Format and scoring metadata
                    'match_format': 'HEAD_TO_HEAD' if round_num >= knockout_rounds - 1 else 'INDIVIDUAL_RANKING',
                    'scoring_type': 'PLACEMENT',
                    'structure_config': {
                        'expected_participants': players_in_round,
                        'round_name': round_name,
                        'qualified_count': knockout_players,
                        **seeding_info  # ✅ Add seeding placeholders (A1 vs B2, etc.)
                    },
                    # ⚠️ participant_user_ids = NULL until previous round completes
                    'participant_user_ids': None
                })

                # ✅ SEQUENTIAL SCHEDULING: All matches happen one after another (one-day tournament)
                # Each match gets: session_duration + break_minutes
                current_time += timedelta(minutes=session_duration + break_minutes)

            # Break between rounds
            current_time += timedelta(minutes=break_minutes * 2)

        # ============================================================================
        # PHASE 2C: BRONZE MATCH (3rd place playoff)
        # ============================================================================
        # ✅ Decision: Bronze match ONLY for 8+ knockout brackets
        if has_bronze:
            session_start = current_time
            session_end = session_start + timedelta(minutes=session_duration)

            sessions.append({
                'title': f'{tournament.name} - 3rd Place Match',
                'description': '3rd place playoff (bronze medal match)',
                'date_start': session_start,
                'date_end': session_end,
                'game_type': '3rd Place Match',
                'tournament_phase': 'Knockout Stage',
                'tournament_round': knockout_rounds + 1,  # After final
                'tournament_match_number': 1,
                'location': tournament.location_venue or 'TBD',
                'session_type': 'on_site',
                # ✅ UNIFIED RANKING: Bronze match metadata
                'ranking_mode': 'QUALIFIED_ONLY',
                'round_number': knockout_rounds + 1,  # ✅ MANDATORY: Round number for fixtures display (bronze = after final)
                'expected_participants': 2,
                'participant_filter': 'semifinal_losers',
                'group_identifier': None,
                'pod_tier': None,
                # ✅ MATCH STRUCTURE: Format and scoring metadata
                'match_format': 'HEAD_TO_HEAD',
                'scoring_type': 'PLACEMENT',
                'structure_config': {
                    'expected_participants': 2,
                    'round_name': '3rd Place Match',
                    'qualified_count': knockout_players
                },
                # ⚠️ participant_user_ids = NULL until semifinal completes
                'participant_user_ids': None
            })

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

        ✅ UNIFIED RANKING: Performance-based pods (top performers vs top, middle vs middle, etc.)

        Typical rounds = log2(n) rounded up
        Pod size configurable (default: 4 players per pod)
        """
        sessions = []
        total_rounds = math.ceil(math.log2(player_count))

        # Get pod configuration from config (default: 4 players per pod)
        pod_size = config.config.get('pod_size', 4)
        pods_count = max(1, player_count // pod_size)

        # ✅ Get enrolled players for participant_user_ids
        enrolled_players = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament.id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).all()
        player_ids = [enrollment.user_id for enrollment in enrolled_players]

        current_time = tournament.start_date

        for round_num in range(1, total_rounds + 1):
            # In Swiss System, players are divided into performance-based pods after Round 1
            for pod_num in range(1, pods_count + 1):
                session_start = current_time
                session_end = session_start + timedelta(minutes=session_duration)

                # Pod tier naming: Pod 1 = Top performers, Pod 2 = Mid-tier, etc.
                pod_name = f"Pod {pod_num}" if pods_count > 1 else "Main"

                sessions.append({
                    'title': f'{tournament.name} - Round {round_num} - {pod_name}',
                    'description': f'Swiss system round {round_num} - {pod_name} ({pod_size} players)',
                    'date_start': session_start,
                    'date_end': session_end,
                    'game_type': f'Round {round_num}',
                    'tournament_phase': 'Swiss System',
                    'tournament_round': round_num,
                    'tournament_match_number': pod_num,
                    'location': tournament.location_venue or 'TBD',
                    'session_type': 'on_site',
                    # ✅ UNIFIED RANKING: Swiss performance pod metadata
                    'ranking_mode': 'PERFORMANCE_POD',
                    'round_number': round_num,  # ✅ MANDATORY: Round number for fixtures display
                    'expected_participants': pod_size,
                    'participant_filter': 'dynamic_swiss_pairing',
                    'group_identifier': None,
                    'pod_tier': pod_num,  # Pod tier (1=top performers, 2=middle, etc.)
                    # ✅ MATCH STRUCTURE: Format and scoring metadata
                    'match_format': 'INDIVIDUAL_RANKING',  # Pod members compete together
                    'scoring_type': 'PLACEMENT',
                    'structure_config': {
                        'pod': pod_num,
                        'pod_size': pod_size,
                        'expected_participants': pod_size,
                        'performance_tier': pod_num
                    },
                    # ✅ FIX: Add participant_user_ids - Initially all players in Round 1, then dynamic allocation by performance
                    'participant_user_ids': player_ids if round_num == 1 else player_ids[(pod_num-1)*pod_size:pod_num*pod_size] if len(player_ids) >= pod_num*pod_size else player_ids[(pod_num-1)*pod_size:]
                })

                # Schedule parallel pods
                if pod_num % parallel_fields != 0:
                    continue
                else:
                    current_time += timedelta(minutes=session_duration + break_minutes)

            # Break between rounds
            current_time += timedelta(minutes=break_minutes * 2)

        return sessions
