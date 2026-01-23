"""
Tournament Match Results Management Endpoints

This module handles match result submission and tournament finalization workflows.

Endpoints:
- POST /{tournament_id}/sessions/{session_id}/submit-results: Submit structured match results
- PATCH /{tournament_id}/sessions/{session_id}/results: Record match results (legacy)
- POST /{tournament_id}/finalize-group-stage: Finalize group stage and calculate standings
- POST /{tournament_id}/finalize-tournament: Finalize tournament and calculate final rankings

Authorization:
- Match results: INSTRUCTOR (assigned to tournament) or ADMIN
- Group stage finalization: INSTRUCTOR or ADMIN
- Tournament finalization: ADMIN only

Extracted from instructor.py as part of P0-1 refactoring (2026-01-23)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime
import json

from app.database import get_db
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.dependencies import get_current_user

# Import result processor service
from app.services.tournament.result_processor import ResultProcessor

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class MatchResultEntry(BaseModel):
    """Single player result entry"""
    user_id: int
    rank: int  # 1st, 2nd, 3rd, etc.
    score: Optional[float] = None  # Optional score/points
    notes: Optional[str] = None


class RecordMatchResultsRequest(BaseModel):
    """Request schema for recording match results"""
    results: list[MatchResultEntry]
    match_notes: Optional[str] = None


class SubmitMatchResultsRequest(BaseModel):
    """
    Structured match results submission

    Format depends on match_format:
    - INDIVIDUAL_RANKING: [{"user_id": 1, "placement": 1}, ...]
    - HEAD_TO_HEAD (WIN_LOSS): [{"user_id": 1, "result": "WIN"}, {"user_id": 2, "result": "LOSS"}]
    - HEAD_TO_HEAD (SCORE): [{"user_id": 1, "score": 3}, {"user_id": 2, "score": 1}]
    - TEAM_MATCH: [{"user_id": 1, "team": "A", "team_score": 5, "opponent_score": 3}, ...]
    - TIME_BASED: [{"user_id": 1, "time_seconds": 12.45}, ...]
    - SKILL_RATING: [{"user_id": 1, "rating": 8.5, "criteria_scores": {...}}, ...]  # Extension point
    """
    results: list[Dict[str, Any]]
    notes: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/{tournament_id}/sessions/{session_id}/submit-results")
def submit_structured_match_results(
    tournament_id: int,
    session_id: int,
    request: SubmitMatchResultsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    📊 Submit structured match results (supports all match formats).

    This endpoint processes match results and:
    1. Validates raw results based on match_format
    2. Derives rankings using format-specific processor
    3. Stores both raw_results and derived_rankings in session.game_results
    4. Returns success message with derived rankings

    Match Format Support:
    - INDIVIDUAL_RANKING: Placement-based (1st, 2nd, 3rd, ...)
    - HEAD_TO_HEAD: 1v1 with WIN_LOSS or SCORE_BASED
    - TEAM_MATCH: Team assignments with scoring
    - TIME_BASED: Time trial competitions
    - SKILL_RATING: Skill evaluation (extension point)

    Authorization: INSTRUCTOR (assigned to tournament) or ADMIN
    """
    # ============================================================================
    # AUTHORIZATION CHECK
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Check authorization
    if current_user.role == UserRole.ADMIN:
        pass  # Admin can access any tournament
    elif current_user.role == UserRole.INSTRUCTOR:
        if tournament.master_instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this tournament"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can record match results"
        )

    # ============================================================================
    # GET SESSION
    # ============================================================================
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.semester_id == tournament_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found in tournament {tournament_id}"
        )

    if not session.is_tournament_game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session is not a tournament match"
        )

    # ✅ Allow re-submission (overwrite existing results)
    # This is useful for correcting mistakes or updating results

    # ============================================================================
    # PROCESS RESULTS USING RESULT PROCESSOR
    # ============================================================================
    processor = ResultProcessor()

    try:
        result = processor.process_match_results(
            db=db,
            session=session,
            tournament=tournament,
            raw_results=request.results,
            match_notes=request.notes,
            recorded_by_user_id=current_user.id,
            recorded_by_name=current_user.name or current_user.email
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    db.commit()
    db.refresh(session)

    return {
        "success": True,
        "message": f"✅ Results recorded successfully for {len(result['derived_rankings'])} participants",
        "session_id": session.id,
        "tournament_id": tournament_id,
        "match_format": session.match_format,
        "rankings": result["derived_rankings"],
        "recorded_at": result["recorded_at"],
        "recorded_by": current_user.name or current_user.email
    }


@router.patch("/{tournament_id}/sessions/{session_id}/results")
async def record_match_results(
    tournament_id: int,
    session_id: int,
    result_data: RecordMatchResultsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Record results for a tournament match (session).

    - Stores results in session.game_results JSONB field
    - Updates tournament_rankings table with points
    - Auto-calculates standings based on points system

    Points System (default):
    - 1st place: 3 points
    - 2nd place: 2 points
    - 3rd place: 1 point
    - Participation: 0 points

    Authorization: INSTRUCTOR (must be assigned to tournament) or ADMIN

    ⚠️ LEGACY ENDPOINT: Consider using POST /submit-results instead
    """
    # ============================================================================
    # AUTHORIZATION CHECK
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Check authorization
    if current_user.role == UserRole.ADMIN:
        pass  # Admin can access any tournament
    elif current_user.role == UserRole.INSTRUCTOR:
        if tournament.master_instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this tournament"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can record match results"
        )

    # ============================================================================
    # GET SESSION
    # ============================================================================
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.semester_id == tournament_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found in tournament {tournament_id}"
        )

    if not session.is_tournament_game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session is not a tournament match"
        )

    if session.game_results is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Results have already been recorded for this match"
        )

    # ============================================================================
    # VALIDATE RESULTS
    # ============================================================================
    # Check that all users are enrolled in tournament
    user_ids = [r.user_id for r in result_data.results]
    enrollments = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.semester_id == tournament_id,
        SemesterEnrollment.user_id.in_(user_ids),
        SemesterEnrollment.is_active == True
    ).all()

    enrolled_user_ids = {e.user_id for e in enrollments}
    invalid_users = set(user_ids) - enrolled_user_ids

    if invalid_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Users {invalid_users} are not enrolled in this tournament"
        )

    # Check that ranks are valid (no duplicates)
    ranks = [r.rank for r in result_data.results]
    if len(ranks) != len(set(ranks)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate ranks are not allowed"
        )

    # ============================================================================
    # STORE RESULTS IN SESSION
    # ============================================================================
    results_dict = {
        "recorded_at": datetime.utcnow().isoformat(),
        "recorded_by": current_user.id,
        "recorded_by_name": current_user.name,
        "match_notes": result_data.match_notes,
        "results": [
            {
                "user_id": r.user_id,
                "rank": r.rank,
                "score": r.score,
                "notes": r.notes
            }
            for r in result_data.results
        ]
    }

    # Convert dict to JSON string (game_results is Text type, not JSONB)
    session.game_results = json.dumps(results_dict)
    db.flush()

    # ============================================================================
    # ⚠️ IMPORTANT: DO NOT UPDATE tournament_rankings HERE!
    # ============================================================================
    # Rankings are calculated ONLY at tournament finalization:
    # - Group Stage finalization: Calculate group standings
    # - Tournament finalization: Calculate final rankings (1st, 2nd, 3rd)
    #
    # This ensures that:
    # - Group+Knockout tournaments: Final ranking based on knockout results
    # - League tournaments: Final ranking based on total points after all matches
    # ============================================================================

    # ============================================================================
    # UPDATE RANKS (for reward distribution)
    # ============================================================================
    # After all points are recorded, update rank field based on points DESC
    db.execute(
        text("""
        UPDATE tournament_rankings tr
        SET rank = ranked.row_num
        FROM (
            SELECT
                id,
                ROW_NUMBER() OVER (ORDER BY COALESCE(points, 0) DESC, updated_at ASC) as row_num
            FROM tournament_rankings
            WHERE tournament_id = :tournament_id
        ) ranked
        WHERE tr.id = ranked.id
        """),
        {"tournament_id": tournament_id}
    )

    db.commit()
    db.refresh(session)

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    return {
        "message": "Match results recorded successfully",
        "session_id": session.id,
        "match_name": session.title,
        "tournament_id": tournament_id,
        "results": results_dict["results"],
        "recorded_at": results_dict["recorded_at"],
        "recorded_by": current_user.name
    }


@router.post("/{tournament_id}/finalize-group-stage")
def finalize_group_stage(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🏆 Finalize Group Stage and calculate group standings.

    This endpoint:
    1. Validates all group stage matches are completed
    2. Calculates group standings (points from game_results)
    3. Determines qualified participants for knockout stage
    4. Updates knockout session participant_user_ids with seeding

    Authorization: ADMIN or INSTRUCTOR
    """
    # Authorization check
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can finalize tournament stages"
        )

    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Get all group stage sessions
    group_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.tournament_phase == "Group Stage"
    ).all()

    if not group_sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No group stage matches found"
        )

    # Check if all group matches are completed
    incomplete_matches = [s for s in group_sessions if s.game_results is None]

    if incomplete_matches:
        return {
            "success": False,
            "message": f"{len(incomplete_matches)} group stage matches are not completed yet",
            "incomplete_matches": [
                {"session_id": s.id, "title": s.title} for s in incomplete_matches
            ]
        }

    # Calculate group standings (using same logic as /leaderboard endpoint)
    from collections import defaultdict

    # Structure: {group_id: {user_id: {wins, losses, draws, points, goals_for, goals_against}}}
    group_stats = defaultdict(lambda: defaultdict(lambda: {
        'wins': 0, 'losses': 0, 'draws': 0, 'points': 0,
        'goals_for': 0, 'goals_against': 0, 'matches_played': 0
    }))

    # Initialize all groups with all participants (even if no matches played yet)
    for session in group_sessions:
        if session.group_identifier and session.participant_user_ids:
            group_id = session.group_identifier
            for user_id in session.participant_user_ids:
                _ = group_stats[group_id][user_id]

    # Process completed matches
    for session in group_sessions:
        if not session.game_results or not session.group_identifier:
            continue

        results = session.game_results

        # Parse game_results if it's a JSON string
        if isinstance(results, str):
            try:
                results = json.loads(results)
            except json.JSONDecodeError:
                continue

        # game_results is a dict with "raw_results" key for HEAD_TO_HEAD
        if isinstance(results, dict):
            raw_results = results.get('raw_results', [])
        elif isinstance(results, list):
            raw_results = results  # Fallback for old format
        else:
            continue

        if len(raw_results) != 2:
            continue  # HEAD_TO_HEAD should have exactly 2 players

        group_id = session.group_identifier
        player1 = raw_results[0]
        player2 = raw_results[1]

        user1_id = player1['user_id']
        user2_id = player2['user_id']
        score1 = player1.get('score', 0)
        score2 = player2.get('score', 0)

        # Update goals
        group_stats[group_id][user1_id]['goals_for'] += score1
        group_stats[group_id][user1_id]['goals_against'] += score2
        group_stats[group_id][user1_id]['matches_played'] += 1

        group_stats[group_id][user2_id]['goals_for'] += score2
        group_stats[group_id][user2_id]['goals_against'] += score1
        group_stats[group_id][user2_id]['matches_played'] += 1

        # Determine win/loss/draw and update points (Football: 3 pts win, 1 pt draw, 0 loss)
        if score1 > score2:
            group_stats[group_id][user1_id]['wins'] += 1
            group_stats[group_id][user1_id]['points'] += 3
            group_stats[group_id][user2_id]['losses'] += 1
        elif score2 > score1:
            group_stats[group_id][user2_id]['wins'] += 1
            group_stats[group_id][user2_id]['points'] += 3
            group_stats[group_id][user1_id]['losses'] += 1
        else:  # Draw
            group_stats[group_id][user1_id]['draws'] += 1
            group_stats[group_id][user1_id]['points'] += 1
            group_stats[group_id][user2_id]['draws'] += 1
            group_stats[group_id][user2_id]['points'] += 1

    # Convert to sorted standings with user details
    from app.models.user import User as UserModel

    group_standings = {}
    qualified_participants = []  # List of qualified user_ids for knockout stage

    for group_id, stats in group_stats.items():
        # Get user details
        user_ids = list(stats.keys())
        users = db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()
        user_dict = {user.id: user for user in users}

        # Create standings list
        standings_list = []
        for user_id, user_stats in stats.items():
            user = user_dict.get(user_id)
            if not user:
                continue

            goal_difference = user_stats['goals_for'] - user_stats['goals_against']

            standings_list.append({
                'user_id': user_id,
                'name': user.name or user.email,
                'points': user_stats['points'],
                'wins': user_stats['wins'],
                'draws': user_stats['draws'],
                'losses': user_stats['losses'],
                'goals_for': user_stats['goals_for'],
                'goals_against': user_stats['goals_against'],
                'goal_difference': goal_difference,
                'matches_played': user_stats['matches_played']
            })

        # Sort by: points (desc), goal_difference (desc), goals_for (desc)
        standings_list.sort(
            key=lambda x: (x['points'], x['goal_difference'], x['goals_for']),
            reverse=True
        )

        # Add rank
        for rank, player in enumerate(standings_list, start=1):
            player['rank'] = rank

        group_standings[group_id] = standings_list

        # Top 2 from each group qualify for knockout stage
        qualified_from_group = [p['user_id'] for p in standings_list[:2]]
        qualified_participants.extend(qualified_from_group)

    # 📸 Save snapshot of group stage standings before transitioning to knockout
    snapshot_data = {
        "timestamp": datetime.now().isoformat(),
        "phase": "group_stage_complete",
        "group_standings": group_standings,
        "qualified_participants": qualified_participants,
        "total_groups": len(group_standings),
        "total_qualified": len(qualified_participants),
        "qualification_rule": "top_2_per_group"
    }

    # Save snapshot to tournament.enrollment_snapshot
    tournament.enrollment_snapshot = snapshot_data

    # Update knockout sessions with qualified participants
    knockout_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.tournament_phase == "Knockout Stage"
    ).order_by(SessionModel.tournament_round, SessionModel.id).all()

    # ✅ Seeding logic: Standard crossover bracket (A1 vs B2, B1 vs A2)
    # Get top 2 from each group
    sorted_groups = sorted(group_standings.items())  # Sort by group_id to ensure consistency

    if len(sorted_groups) >= 2:
        group_a_id, group_a_standings = sorted_groups[0]
        group_b_id, group_b_standings = sorted_groups[1]

        # Extract top 2 from each group
        a1 = group_a_standings[0]['user_id'] if len(group_a_standings) >= 1 else None
        a2 = group_a_standings[1]['user_id'] if len(group_a_standings) >= 2 else None
        b1 = group_b_standings[0]['user_id'] if len(group_b_standings) >= 1 else None
        b2 = group_b_standings[1]['user_id'] if len(group_b_standings) >= 2 else None

        # Get Round of 4 (Semifinal) sessions - tournament_round is Integer!
        # Round 1 = Semifinals (4 players), Round 2 = Final (2 players)
        semifinal_sessions = [s for s in knockout_sessions if s.tournament_round == 1]

        if len(semifinal_sessions) >= 2 and all([a1, a2, b1, b2]):
            # Semifinal 1: A1 vs B2 (crossover bracket)
            semifinal_sessions[0].participant_user_ids = [a1, b2]

            # Semifinal 2: B1 vs A2 (crossover bracket)
            semifinal_sessions[1].participant_user_ids = [b1, a2]

            # Note: Final match (round 2) participant_user_ids will be set after semifinals are completed

    db.commit()

    return {
        "success": True,
        "message": "✅ Group stage finalized successfully! Snapshot saved.",
        "group_standings": group_standings,
        "qualified_participants": qualified_participants,
        "knockout_sessions_updated": len(knockout_sessions),
        "snapshot_saved": True
    }


@router.post("/{tournament_id}/finalize-tournament")
def finalize_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🏆 Finalize Tournament and calculate FINAL RANKING.

    This endpoint:
    1. Validates ALL matches are completed
    2. Calculates final ranking based on tournament structure:
       - Group+Knockout: Based on final match (1st, 2nd, 3rd place match)
       - League: Based on total points
    3. Updates tournament_rankings table
    4. Sets tournament status to COMPLETED

    Authorization: ADMIN only
    """
    # Authorization check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can finalize tournaments"
        )

    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Get ALL tournament sessions
    all_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True
    ).all()

    if not all_sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tournament matches found"
        )

    # Check if all matches are completed
    incomplete_matches = [s for s in all_sessions if s.game_results is None]

    if incomplete_matches:
        return {
            "success": False,
            "message": f"{len(incomplete_matches)} matches are not completed yet",
            "incomplete_matches": [
                {"session_id": s.id, "title": s.title} for s in incomplete_matches
            ]
        }

    # Calculate final ranking
    # This is where we determine 1st, 2nd, 3rd place based on final match results

    # For Group+Knockout: Find final match and 3rd place match
    final_match = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.tournament_phase == "Knockout Stage",
        SessionModel.title.ilike("%final%")
    ).first()

    third_place_match = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.tournament_phase == "Knockout Stage",
        SessionModel.title.ilike("%3rd%")
    ).first()

    final_rankings = []

    if final_match and final_match.game_results:
        results = json.loads(final_match.game_results)
        for result in results.get("derived_rankings", []):
            if result["rank"] == 1:
                final_rankings.append({"user_id": result["user_id"], "final_rank": 1, "place": "1st"})
            elif result["rank"] == 2:
                final_rankings.append({"user_id": result["user_id"], "final_rank": 2, "place": "2nd"})

    if third_place_match and third_place_match.game_results:
        results = json.loads(third_place_match.game_results)
        for result in results.get("derived_rankings", []):
            if result["rank"] == 1:
                final_rankings.append({"user_id": result["user_id"], "final_rank": 3, "place": "3rd"})

    # Update tournament_rankings table
    # Clear existing rankings
    db.execute(
        text("DELETE FROM tournament_rankings WHERE tournament_id = :tournament_id"),
        {"tournament_id": tournament_id}
    )

    # Insert final rankings
    for ranking in final_rankings:
        db.execute(
            text("""
            INSERT INTO tournament_rankings (tournament_id, user_id, rank, points, participant_type)
            VALUES (:tournament_id, :user_id, :rank, :points, 'USER')
            """),
            {
                "tournament_id": tournament_id,
                "user_id": ranking["user_id"],
                "rank": ranking["final_rank"],
                "points": 0  # Points not used for final ranking
            }
        )

    # Update tournament status
    tournament.tournament_status = "COMPLETED"

    db.commit()

    return {
        "success": True,
        "message": "Tournament finalized successfully",
        "final_rankings": final_rankings,
        "tournament_status": "COMPLETED"
    }
