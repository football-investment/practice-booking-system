"""
Tournament Participant Filter Service

Determines which users should participate in a given tournament session
based on ranking_mode and participant_filter metadata.

This service supports the Unified Multi-Player Ranking System where:
- League: All players rank together in each round
- Group Stage: Only group members rank in group sessions
- Knockout: Qualified players or all players (tiered ranking)
- Swiss: Performance-matched pods
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Any, Optional
from app.models.session import Session as SessionModel
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.tournament_ranking import TournamentRanking


class ParticipantFilterService:
    """
    Determines which users should participate in a given tournament session
    based on ranking_mode and participant_filter.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_session_participants(
        self,
        session_id: int
    ) -> List[int]:
        """
        Get list of user_ids who should participate in this session.

        Args:
            session_id: Session ID to filter participants for

        Returns:
            List[int]: user_ids eligible for this session
        """
        session = self.db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            return []

        tournament_id = session.semester_id
        ranking_mode = session.ranking_mode or 'ALL_PARTICIPANTS'

        # Get all enrolled users
        enrollments = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).all()

        all_user_ids = [e.user_id for e in enrollments]

        if not all_user_ids:
            return []

        # Apply filtering based on ranking_mode
        if ranking_mode == 'ALL_PARTICIPANTS':
            return all_user_ids

        elif ranking_mode == 'GROUP_ISOLATED':
            return self._filter_by_group(session, all_user_ids)

        elif ranking_mode == 'QUALIFIED_ONLY':
            return self._filter_qualified_players(session, all_user_ids)

        elif ranking_mode == 'PERFORMANCE_POD':
            return self._filter_by_performance_pod(session, all_user_ids)

        elif ranking_mode == 'TIERED':
            # Knockout: all players participate but tier affects point distribution
            return all_user_ids

        else:
            # Default: all participants
            return all_user_ids

    def _filter_by_group(
        self,
        session: SessionModel,
        all_user_ids: List[int]
    ) -> List[int]:
        """
        Filter participants for group stage sessions.

        Group assignment logic:
        - Use session.group_identifier (A, B, C, D)
        - Divide all_user_ids into N equal groups based on sorted order
        - Return only users assigned to this session's group

        Args:
            session: Session model with group_identifier
            all_user_ids: All enrolled user IDs

        Returns:
            List[int]: User IDs for this group
        """
        group_identifier = session.group_identifier
        expected_participants = session.expected_participants or 4

        if not group_identifier:
            # Fallback: return all if no group specified
            return all_user_ids

        # Calculate number of groups based on expected_participants
        total_players = len(all_user_ids)
        groups_count = max(1, total_players // expected_participants)

        # Sort user IDs for deterministic assignment
        sorted_user_ids = sorted(all_user_ids)

        # Assign groups using round-robin
        # Group A = indices 0, groups_count, 2*groups_count, ...
        # Group B = indices 1, groups_count+1, 2*groups_count+1, ...
        group_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

        if group_identifier not in group_letters:
            return all_user_ids

        group_index = group_letters.index(group_identifier)

        # Filter users for this group
        group_user_ids = []
        for idx, user_id in enumerate(sorted_user_ids):
            assigned_group_idx = idx % groups_count
            if assigned_group_idx == group_index:
                group_user_ids.append(user_id)

        return group_user_ids

    def _filter_qualified_players(
        self,
        session: SessionModel,
        all_user_ids: List[int]
    ) -> List[int]:
        """
        Filter for knockout stage: only top group qualifiers.

        Logic:
        - Get tournament rankings from group stage
        - Take top N qualifiers based on session.expected_participants

        Args:
            session: Session model with expected_participants
            all_user_ids: All enrolled user IDs

        Returns:
            List[int]: Top qualified user IDs
        """
        tournament_id = session.semester_id
        expected_participants = session.expected_participants or 8

        # Get current rankings (from group stage or previous rounds)
        rankings = self.db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament_id,
            TournamentRanking.user_id.in_(all_user_ids)
        ).order_by(TournamentRanking.points.desc()).all()

        # Take top N qualifiers
        qualified_user_ids = [r.user_id for r in rankings[:expected_participants]]

        # If not enough rankings yet, include all players
        if len(qualified_user_ids) < expected_participants:
            return all_user_ids

        return qualified_user_ids

    def _filter_by_performance_pod(
        self,
        session: SessionModel,
        all_user_ids: List[int]
    ) -> List[int]:
        """
        Swiss System: Assign players to performance-based pods.

        Logic:
        - Sort all players by cumulative points
        - Divide into pods (top pod, middle pod, bottom pod)
        - Return players for this session's pod_tier

        Args:
            session: Session model with pod_tier and expected_participants
            all_user_ids: All enrolled user IDs

        Returns:
            List[int]: User IDs for this performance pod
        """
        tournament_id = session.semester_id
        pod_tier = session.pod_tier or 1
        expected_participants = session.expected_participants or 4

        # Get current rankings
        rankings = self.db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament_id,
            TournamentRanking.user_id.in_(all_user_ids)
        ).order_by(TournamentRanking.points.desc()).all()

        # If no rankings yet (first round), use all players
        if not rankings:
            return all_user_ids

        # Calculate pod ranges
        pod_start = (pod_tier - 1) * expected_participants
        pod_end = pod_start + expected_participants

        pod_user_ids = [r.user_id for r in rankings[pod_start:pod_end]]

        # If pod is incomplete, fill with remaining unranked players
        if len(pod_user_ids) < expected_participants:
            ranked_user_ids = {r.user_id for r in rankings}
            unranked = [uid for uid in all_user_ids if uid not in ranked_user_ids]
            pod_user_ids.extend(unranked[:expected_participants - len(pod_user_ids)])

        return pod_user_ids

    def get_group_assignment(
        self,
        tournament_id: int,
        user_id: int
    ) -> Optional[str]:
        """
        Get the group assignment (A, B, C, D) for a user in a tournament.

        Args:
            tournament_id: Tournament ID
            user_id: User ID

        Returns:
            Optional[str]: Group letter (A, B, C, D) or None
        """
        # Get all enrolled users
        enrollments = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).all()

        all_user_ids = sorted([e.user_id for e in enrollments])

        if user_id not in all_user_ids:
            return None

        # Find a group stage session to determine group configuration
        group_session = self.db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.ranking_mode == 'GROUP_ISOLATED'
        ).first()

        if not group_session:
            return None

        expected_participants = group_session.expected_participants or 4
        total_players = len(all_user_ids)
        groups_count = max(1, total_players // expected_participants)

        # Calculate group assignment
        user_index = all_user_ids.index(user_id)
        group_index = user_index % groups_count

        group_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

        if group_index < len(group_letters):
            return group_letters[group_index]

        return None
