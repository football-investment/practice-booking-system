"""
Group + Knockout Format Generator

Generates sessions for group stage followed by knockout stage tournaments.
"""
import math
from typing import List, Dict, Any
from datetime import timedelta

from app.models.semester import Semester
from app.models.tournament_type import TournamentType
from app.models.tournament_enums import TournamentPhase
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from .base_format_generator import BaseFormatGenerator
from ..algorithms import RoundRobinPairing, GroupDistribution, KnockoutBracket
from ..utils import get_tournament_venue


class GroupKnockoutGenerator(BaseFormatGenerator):
    """
    Generates group stage + knockout tournament sessions

    ✅ MATCH PARTICIPANTS: Explicit participant_user_ids for each match
    ✅ FIX: Group sessions ONLY include group members (not all tournament players)

    Group Stage: Players divided into groups, each group ranks separately.
    Knockout Stage: Top qualifiers from each group advance to multi-player knockout.
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
        Generate group stage + knockout tournament sessions
        """
        sessions = []

        # ✅ CRITICAL: Get enrolled players first
        enrolled_players = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament.id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).all()

        player_ids = [enrollment.user_id for enrollment in enrolled_players]

        # ✅ CRITICAL FIX: Use actual enrolled player count, not configured max
        actual_player_count = len(player_ids)

        # ✅ NEW: Use dynamic group distribution (supports odd player counts)
        # Try config first, then fall back to dynamic calculation
        group_config = tournament_type.config.get('group_configuration', {}).get(f'{actual_player_count}_players')

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
            distribution = GroupDistribution.calculate_optimal_distribution(actual_player_count)
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
        tournament_format = getattr(tournament, 'format', None) or getattr(tournament_type, 'format', 'INDIVIDUAL_RANKING')

        if tournament_format == 'HEAD_TO_HEAD':
            # ✅ HEAD_TO_HEAD: Generate round robin pairings within each group
            for group_num in range(1, groups_count + 1):
                group_name = chr(64 + group_num)  # A, B, C, D
                group_participant_ids = group_assignments.get(group_name, [])
                group_size = len(group_participant_ids)

                # Calculate rounds for this group
                num_rounds = RoundRobinPairing.calculate_rounds(group_size)

                for round_num in range(1, num_rounds + 1):
                    # Generate pairings for this round
                    round_pairings = RoundRobinPairing.get_round_pairings(group_participant_ids, round_num)

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
                            'tournament_phase': TournamentPhase.GROUP_STAGE.value,
                            'tournament_round': round_num,
                            'tournament_match_number': match_num,
                            'location': get_tournament_venue(tournament),
                            'session_type': 'on_site',
                            # ✅ HEAD_TO_HEAD: Group stage metadata
                            'ranking_mode': 'GROUP_ISOLATED',
                            'group_identifier': group_name,
                            'round_number': round_num,
                            'expected_participants': 2,
                            'participant_filter': 'group_membership',
                            'pod_tier': None,
                            # ✅ MATCH STRUCTURE: HEAD_TO_HEAD format (from tournament config)
                            'match_format': tournament.format,  # Should be HEAD_TO_HEAD
                            'scoring_type': tournament.scoring_type,
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
                        'tournament_phase': TournamentPhase.GROUP_STAGE.value,
                        'tournament_round': round_num,
                        'tournament_match_number': (group_num - 1) * group_rounds + round_num,
                        'location': get_tournament_venue(tournament),
                        'session_type': 'on_site',
                        # ✅ UNIFIED RANKING: Group isolation metadata
                        'ranking_mode': 'GROUP_ISOLATED',
                        'group_identifier': group_name,
                        'round_number': round_num,  # ✅ MANDATORY: Round number for fixtures display
                        'expected_participants': len(group_participant_ids),
                        'participant_filter': 'group_membership',
                        'pod_tier': None,
                        # ✅ MATCH STRUCTURE: Format and scoring metadata (from tournament config)
                        'match_format': tournament.format,  # Should be INDIVIDUAL_RANKING for group stage
                        'scoring_type': tournament.scoring_type,
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
        round_names = tournament_type.config.get('round_names', {})

        # ✅ NEW: Calculate knockout structure (byes, play-in, bronze)
        structure = KnockoutBracket.calculate_structure(knockout_players)
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
                    'tournament_phase': TournamentPhase.KNOCKOUT.value,
                    'tournament_round': 0,  # Play-in is round 0
                    'tournament_match_number': match_num,
                    'location': get_tournament_venue(tournament),
                    'session_type': 'on_site',
                    # ✅ UNIFIED RANKING: Play-in metadata
                    'ranking_mode': 'QUALIFIED_ONLY',
                    'round_number': 0,  # ✅ MANDATORY: Round number for fixtures display (play-in = round 0)
                    'expected_participants': 2,  # Head-to-head
                    'participant_filter': 'seeded_qualifiers',
                    'group_identifier': None,
                    'pod_tier': None,
                    # ✅ MATCH STRUCTURE: Format and scoring metadata (play-in is always HEAD_TO_HEAD)
                    'match_format': 'HEAD_TO_HEAD',  # 1v1 elimination
                    'scoring_type': tournament.scoring_type,
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
                    'tournament_phase': TournamentPhase.KNOCKOUT.value,
                    'tournament_round': round_num,
                    'tournament_match_number': match_in_round,
                    'location': get_tournament_venue(tournament),
                    'session_type': 'on_site',
                    # ✅ UNIFIED RANKING: Knockout stage metadata
                    'ranking_mode': 'QUALIFIED_ONLY',
                    'round_number': round_num,  # ✅ MANDATORY: Round number for fixtures display
                    'expected_participants': 2 if round_num >= knockout_rounds - 1 else players_in_round,
                    'participant_filter': 'seeded_qualifiers',
                    'group_identifier': None,
                    'pod_tier': None,
                    # ✅ MATCH STRUCTURE: Format and scoring metadata (business logic: finals use HEAD_TO_HEAD)
                    'match_format': 'HEAD_TO_HEAD' if round_num >= knockout_rounds - 1 else 'INDIVIDUAL_RANKING',
                    'scoring_type': tournament.scoring_type,
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
                'tournament_phase': TournamentPhase.KNOCKOUT.value,
                'tournament_round': knockout_rounds + 1,  # After final
                'tournament_match_number': 1,
                'location': get_tournament_venue(tournament),
                'session_type': 'on_site',
                # ✅ UNIFIED RANKING: Bronze match metadata
                'ranking_mode': 'QUALIFIED_ONLY',
                'round_number': knockout_rounds + 1,  # ✅ MANDATORY: Round number for fixtures display (bronze = after final)
                'expected_participants': 2,
                'participant_filter': 'semifinal_losers',
                'group_identifier': None,
                'pod_tier': None,
                # ✅ MATCH STRUCTURE: Format and scoring metadata (bronze is always HEAD_TO_HEAD)
                'match_format': 'HEAD_TO_HEAD',
                'scoring_type': tournament.scoring_type,
                'structure_config': {
                    'expected_participants': 2,
                    'round_name': '3rd Place Match',
                    'qualified_count': knockout_players
                },
                # ⚠️ participant_user_ids = NULL until semifinal completes
                'participant_user_ids': None
            })

        return sessions
