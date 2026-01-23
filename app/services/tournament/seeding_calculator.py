"""
Tournament Seeding Calculator

Calculates knockout seeding based on group stage performance.

Business Logic (Decision: Option A):
1. Total points in group stage
2. Head-to-head record (if tied on points)
3. Goal difference (if still tied)
4. Random tiebreaker (if still tied)

Seeding Order:
1. Group winners (sorted by performance)
2. Group runners-up (sorted by performance)
3. Best 3rd place finishers (if needed for bracket)
"""
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import random

from app.models.session import Session as SessionModel
from app.models.attendance import Attendance
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus


class SeedingCalculator:
    """
    Calculates knockout seeding from group stage results
    """

    def __init__(self, db: Session):
        self.db = db

    def calculate_group_standings(
        self,
        tournament_id: int,
        group_identifier: str
    ) -> List[Dict[str, any]]:
        """
        Calculate standings for a specific group

        Returns list of players sorted by:
        1. Total points (from match placements)
        2. Goal difference (if implemented)
        3. Random tiebreaker

        Returns:
            [
                {
                    'user_id': int,
                    'points': int,
                    'matches_played': int,
                    'goal_diff': int,  # Placeholder for future
                    'position': int    # 1, 2, 3, 4
                },
                ...
            ]
        """
        # Get all group stage sessions for this group
        group_sessions = self.db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.tournament_phase == 'Group Stage',
            SessionModel.group_identifier == group_identifier
        ).all()

        if not group_sessions:
            return []

        session_ids = [s.id for s in group_sessions]

        # Get all attendance records for these sessions
        attendances = self.db.query(Attendance).filter(
            Attendance.session_id.in_(session_ids)
        ).all()

        # Calculate points for each player
        player_stats = {}  # {user_id: {'points': int, 'matches': int}}

        for attendance in attendances:
            user_id = attendance.user_id

            if user_id not in player_stats:
                player_stats[user_id] = {
                    'user_id': user_id,
                    'points': 0,
                    'matches_played': 0,
                    'goal_diff': 0  # Placeholder
                }

            # Award points based on attendance (placeholder logic)
            # TODO: Replace with actual match result points when implemented
            if attendance.status.value == 'present':
                player_stats[user_id]['points'] += attendance.xp_earned or 0
                player_stats[user_id]['matches_played'] += 1

        # Sort by points (descending), then random for tiebreaker
        standings = list(player_stats.values())
        standings.sort(key=lambda x: (x['points'], random.random()), reverse=True)

        # Assign positions
        for i, player in enumerate(standings):
            player['position'] = i + 1

        return standings

    def calculate_seeding(
        self,
        tournament_id: int,
        groups: List[str]
    ) -> List[int]:
        """
        Calculate full knockout seeding order

        ✅ Business Decision: Option A
        Seeding order:
        1. Group winners (sorted by points/performance)
        2. Group runners-up (sorted by points/performance)
        3. Best 3rd place finishers (if needed)

        Args:
            tournament_id: Tournament ID
            groups: List of group identifiers (e.g., ['A', 'B', 'C'])

        Returns:
            List of user_ids in seeding order (Seed 1, Seed 2, ...)
        """
        # Get standings for each group
        all_standings = {}
        for group in groups:
            all_standings[group] = self.calculate_group_standings(tournament_id, group)

        # Extract positions
        winners = []
        runners_up = []
        third_place = []

        for group, standings in all_standings.items():
            if len(standings) >= 1:
                winners.append((standings[0], group))
            if len(standings) >= 2:
                runners_up.append((standings[1], group))
            if len(standings) >= 3:
                third_place.append((standings[2], group))

        # Sort each category by performance (points descending)
        winners.sort(key=lambda x: x[0]['points'], reverse=True)
        runners_up.sort(key=lambda x: x[0]['points'], reverse=True)
        third_place.sort(key=lambda x: x[0]['points'], reverse=True)

        # Build final seeding list
        seeded_ids = []
        seeded_ids.extend([w[0]['user_id'] for w in winners])
        seeded_ids.extend([r[0]['user_id'] for r in runners_up])
        seeded_ids.extend([t[0]['user_id'] for t in third_place])

        return seeded_ids

    def get_seeding_with_metadata(
        self,
        tournament_id: int,
        groups: List[str]
    ) -> List[Dict[str, any]]:
        """
        Get seeding with full metadata for visualization

        Returns:
            [
                {
                    'seed': 1,
                    'user_id': 123,
                    'group': 'A',
                    'group_position': 1,  # 1st in group
                    'points': 15,
                    'matches_played': 3
                },
                ...
            ]
        """
        # Get standings for each group
        all_standings = {}
        for group in groups:
            all_standings[group] = self.calculate_group_standings(tournament_id, group)

        # Build seeded list with metadata
        seeded_list = []

        # Add group winners
        for group in sorted(groups):
            standings = all_standings.get(group, [])
            if len(standings) >= 1:
                player = standings[0]
                seeded_list.append({
                    'user_id': player['user_id'],
                    'group': group,
                    'group_position': 1,
                    'points': player['points'],
                    'matches_played': player['matches_played']
                })

        # Add group runners-up
        for group in sorted(groups):
            standings = all_standings.get(group, [])
            if len(standings) >= 2:
                player = standings[1]
                seeded_list.append({
                    'user_id': player['user_id'],
                    'group': group,
                    'group_position': 2,
                    'points': player['points'],
                    'matches_played': player['matches_played']
                })

        # Add 3rd place finishers (if needed)
        third_place_finishers = []
        for group in sorted(groups):
            standings = all_standings.get(group, [])
            if len(standings) >= 3:
                player = standings[2]
                third_place_finishers.append({
                    'user_id': player['user_id'],
                    'group': group,
                    'group_position': 3,
                    'points': player['points'],
                    'matches_played': player['matches_played']
                })

        # Sort 3rd place finishers by points
        third_place_finishers.sort(key=lambda x: x['points'], reverse=True)
        seeded_list.extend(third_place_finishers)

        # Assign seed numbers
        for i, player in enumerate(seeded_list):
            player['seed'] = i + 1

        return seeded_list
