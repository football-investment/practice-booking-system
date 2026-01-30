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
from sqlalchemy.orm.attributes import flag_modified
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


class SubmitRoundResultsRequest(BaseModel):
    """
    🔄 Round-based results submission for INDIVIDUAL_RANKING tournaments.

    This endpoint is idempotent - submitting the same round multiple times will overwrite previous results.

    Example for TIME_BASED:
    {
        "round_number": 1,
        "results": {"123": "12.5s", "456": "13.2s"}
    }

    Example for SCORE_BASED:
    {
        "round_number": 2,
        "results": {"123": "95", "456": "87"}
    }
    """
    round_number: int
    results: Dict[str, str]  # user_id -> measured_value (e.g., "12.5s", "95 points")
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
    processor = ResultProcessor(db)

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


# ============================================================================
# 🔄 ROUND-BASED RESULTS (INDIVIDUAL_RANKING with multiple rounds)
# ============================================================================

@router.post("/{tournament_id}/sessions/{session_id}/rounds/{round_number}/submit-results")
def submit_round_results(
    tournament_id: int,
    session_id: int,
    round_number: int,
    request: SubmitRoundResultsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🔄 Submit results for a specific round in an INDIVIDUAL_RANKING tournament.

    This endpoint is **idempotent** - submitting the same round multiple times will overwrite previous results.

    Authorization:
    - INSTRUCTOR assigned to tournament
    - ADMIN

    Workflow:
    1. Validate session exists and belongs to tournament
    2. Validate session is INDIVIDUAL_RANKING format
    3. Validate round_number is within range (1 to total_rounds)
    4. Update rounds_data.round_results[round_number] with new results
    5. Update rounds_data.completed_rounds count
    6. Return updated rounds_data

    Example Request:
    POST /api/v1/tournaments/18/sessions/187/rounds/1/submit-results
    {
        "round_number": 1,
        "results": {
            "123": "12.5s",
            "456": "13.2s",
            "789": "14.1s"
        },
        "notes": "Good weather, fast times"
    }
    """
    # Verify tournament exists
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Verify session exists and belongs to tournament
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.semester_id == tournament_id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found in tournament {tournament_id}"
        )

    # Verify session is INDIVIDUAL_RANKING
    if session.match_format != "INDIVIDUAL_RANKING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Round-based results only supported for INDIVIDUAL_RANKING tournaments (session format: {session.match_format})"
        )

    # Authorization check
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can submit round results"
        )

    # Verify instructor is assigned to this tournament
    if current_user.role == UserRole.INSTRUCTOR and session.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned instructor for this session"
        )

    # Get current rounds_data
    rounds_data = session.rounds_data or {}
    total_rounds = rounds_data.get('total_rounds', 1)

    # Validate round_number
    if round_number < 1 or round_number > total_rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid round_number {round_number}. Must be between 1 and {total_rounds}"
        )

    # Ensure rounds_data structure exists
    if 'round_results' not in rounds_data:
        rounds_data['round_results'] = {}

    # Update round results (idempotent - overwrites if exists)
    rounds_data['round_results'][str(round_number)] = request.results

    # Update completed_rounds count (count of unique round keys)
    rounds_data['completed_rounds'] = len(rounds_data['round_results'])

    # Save updated rounds_data
    session.rounds_data = rounds_data

    # ✅ CRITICAL: Tell SQLAlchemy that JSONB field was modified (required for dict mutations)
    flag_modified(session, 'rounds_data')

    db.commit()
    db.refresh(session)

    return {
        "success": True,
        "message": f"Round {round_number} results saved successfully",
        "session_id": session_id,
        "round_number": round_number,
        "rounds_data": session.rounds_data,
        "notes": request.notes
    }


@router.get("/{tournament_id}/sessions/{session_id}/rounds")
def get_rounds_status(
    tournament_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🔍 Get rounds status for an INDIVIDUAL_RANKING session.

    Returns:
    - total_rounds: Total number of rounds configured
    - completed_rounds: Number of rounds with results recorded
    - round_results: All recorded results by round
    - pending_rounds: List of round numbers without results
    """
    # Verify tournament exists
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Verify session exists and belongs to tournament
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.semester_id == tournament_id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found in tournament {tournament_id}"
        )

    # Verify session is INDIVIDUAL_RANKING
    if session.match_format != "INDIVIDUAL_RANKING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Round status only available for INDIVIDUAL_RANKING tournaments (session format: {session.match_format})"
        )

    # Get rounds_data
    rounds_data = session.rounds_data or {}
    total_rounds = rounds_data.get('total_rounds', 1)
    completed_rounds = rounds_data.get('completed_rounds', 0)
    round_results = rounds_data.get('round_results', {})

    # Calculate pending rounds
    completed_round_numbers = set(int(r) for r in round_results.keys())
    all_rounds = set(range(1, total_rounds + 1))
    pending_rounds = sorted(list(all_rounds - completed_round_numbers))

    return {
        "session_id": session_id,
        "tournament_id": tournament_id,
        "match_format": session.match_format,
        "total_rounds": total_rounds,
        "completed_rounds": completed_rounds,
        "pending_rounds": pending_rounds,
        "round_results": round_results,
        "is_complete": completed_rounds == total_rounds
    }


@router.post("/{tournament_id}/sessions/{session_id}/finalize")
def finalize_individual_ranking_session(
    tournament_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🏆 Finalize INDIVIDUAL_RANKING session and calculate final rankings.

    This endpoint:
    1. Validates all rounds are completed
    2. Aggregates results across all rounds (e.g., sum of times, average score, best time)
    3. Calculates final rankings based on tournament.ranking_direction:
       - ASC: Lowest value wins (e.g., fastest time)
       - DESC: Highest value wins (e.g., highest score)
    4. Saves final rankings to session.game_results
    5. Updates TournamentRanking table with final results
    6. Updates tournament status if all sessions finalized

    Authorization: INSTRUCTOR (assigned) or ADMIN

    Example Use Cases:
    - Time-based (ASC): Best (lowest) time across all rounds wins
    - Score-based (DESC): Highest total score across all rounds wins
    - Distance-based (DESC): Longest total distance across all rounds wins
    """
    # ============================================================================
    # AUTHORIZATION
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.semester_id == tournament_id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found in tournament {tournament_id}"
        )

    # Authorization check
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can finalize sessions"
        )

    if current_user.role == UserRole.INSTRUCTOR and session.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned instructor for this session"
        )

    # ============================================================================
    # VALIDATE SESSION TYPE
    # ============================================================================
    if session.match_format != "INDIVIDUAL_RANKING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Finalization only supported for INDIVIDUAL_RANKING sessions (current format: {session.match_format})"
        )

    if tournament.format != "INDIVIDUAL_RANKING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Finalization only supported for INDIVIDUAL_RANKING tournaments (current format: {tournament.format})"
        )

    # ============================================================================
    # VALIDATE ALL ROUNDS COMPLETED
    # ============================================================================
    rounds_data = session.rounds_data or {}
    total_rounds = rounds_data.get('total_rounds', 1)
    completed_rounds = rounds_data.get('completed_rounds', 0)
    round_results = rounds_data.get('round_results', {})

    if completed_rounds < total_rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot finalize: {total_rounds - completed_rounds} rounds remaining. All rounds must be completed first."
        )

    # ============================================================================
    # AGGREGATE RESULTS ACROSS ALL ROUNDS
    # ============================================================================
    from decimal import Decimal
    import re

    # Structure: {user_id: [value1, value2, value3, ...]}
    user_round_values = {}

    for round_num, results_dict in round_results.items():
        for user_id_str, measured_value_str in results_dict.items():
            user_id = int(user_id_str)

            # Parse measured value (e.g., "12.5s", "95 points", "15.2 meters")
            # Extract numeric value
            numeric_match = re.search(r'[\d.]+', measured_value_str)
            if not numeric_match:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Cannot parse measured value '{measured_value_str}' for user {user_id} in round {round_num}"
                )

            numeric_value = Decimal(numeric_match.group())

            if user_id not in user_round_values:
                user_round_values[user_id] = []
            user_round_values[user_id].append(numeric_value)

    # ============================================================================
    # CALCULATE FINAL AGGREGATE VALUE FOR EACH USER
    # ============================================================================
    # Aggregation logic: Use BEST value (for time-based: min, for score-based: max)
    ranking_direction = tournament.ranking_direction or "ASC"
    scoring_type = tournament.scoring_type or "TIME_BASED"

    user_final_values = {}

    for user_id, values in user_round_values.items():
        if ranking_direction == "ASC":
            # ASC: Lowest is best (e.g., fastest time) → take MIN
            final_value = min(values)
        else:
            # DESC: Highest is best (e.g., highest score) → take MAX
            final_value = max(values)

        user_final_values[user_id] = final_value

    # ============================================================================
    # CALCULATE PRIMARY RANKING: Best Individual Performance
    # ============================================================================
    # Sort by final value based on ranking_direction
    if ranking_direction == "ASC":
        # Sort ascending (lowest first)
        sorted_users_performance = sorted(user_final_values.items(), key=lambda x: x[1])
    else:
        # Sort descending (highest first)
        sorted_users_performance = sorted(user_final_values.items(), key=lambda x: x[1], reverse=True)

    # Assign ranks (handle ties by giving same rank)
    performance_rankings = []
    current_rank = 1
    prev_value = None

    for i, (user_id, final_value) in enumerate(sorted_users_performance):
        if prev_value is not None and final_value != prev_value:
            current_rank = i + 1

        performance_rankings.append({
            "user_id": user_id,
            "rank": current_rank,
            "final_value": float(final_value),
            "measurement_unit": tournament.measurement_unit or "units"
        })

        prev_value = final_value

    # ============================================================================
    # CALCULATE SECONDARY RANKING: Most Round Wins
    # ============================================================================
    # Count how many times each user won a round (had the best value in that round)
    user_round_wins = {user_id: 0 for user_id in user_round_values.keys()}

    for round_num, results_dict in round_results.items():
        # Parse all values in this round
        round_values = {}
        for user_id_str, measured_value_str in results_dict.items():
            user_id = int(user_id_str)
            numeric_match = re.search(r'[\d.]+', measured_value_str)
            if numeric_match:
                round_values[user_id] = Decimal(numeric_match.group())

        # Find winner(s) of this round
        if round_values:
            if ranking_direction == "ASC":
                best_value = min(round_values.values())
            else:
                best_value = max(round_values.values())

            # Award win to user(s) with best value (handle ties)
            for user_id, value in round_values.items():
                if value == best_value:
                    user_round_wins[user_id] += 1

    # Sort by number of wins (descending)
    sorted_users_wins = sorted(user_round_wins.items(), key=lambda x: x[1], reverse=True)

    # Assign ranks based on wins
    wins_rankings = []
    current_rank = 1
    prev_wins = None

    for i, (user_id, wins) in enumerate(sorted_users_wins):
        if prev_wins is not None and wins < prev_wins:
            current_rank = i + 1

        wins_rankings.append({
            "user_id": user_id,
            "rank": current_rank,
            "wins": wins,
            "total_rounds": total_rounds
        })

        prev_wins = wins

    # Use performance ranking as primary
    derived_rankings = performance_rankings

    # ============================================================================
    # SAVE TO session.game_results
    # ============================================================================
    recorded_at = datetime.utcnow().isoformat()
    game_results = {
        "recorded_at": recorded_at,
        "recorded_by": current_user.id,
        "recorded_by_name": current_user.name or current_user.email,
        "tournament_format": "INDIVIDUAL_RANKING",
        "scoring_type": scoring_type,
        "measurement_unit": tournament.measurement_unit,
        "ranking_direction": ranking_direction,
        "total_rounds": total_rounds,
        "aggregation_method": "BEST_VALUE",
        "rounds_data": rounds_data,
        # 🏆 DUAL RANKING SYSTEM
        "derived_rankings": derived_rankings,  # Primary: Best individual performance
        "performance_rankings": performance_rankings,  # Best individual value (fastest time)
        "wins_rankings": wins_rankings  # Most round wins (most 1st places)
    }

    session.game_results = json.dumps(game_results)

    # ============================================================================
    # UPDATE TournamentRanking TABLE
    # ============================================================================
    from app.services.tournament.leaderboard_service import get_or_create_ranking, calculate_ranks

    for ranking_entry in derived_rankings:
        user_id = ranking_entry["user_id"]
        final_value = ranking_entry["final_value"]

        # Get or create ranking entry
        ranking = get_or_create_ranking(
            db=db,
            tournament_id=tournament.id,
            user_id=user_id,
            participant_type="INDIVIDUAL"
        )

        # Store final aggregate value in points field
        ranking.points = Decimal(str(final_value))

    db.flush()

    # Recalculate ranks across entire tournament
    calculate_ranks(db, tournament.id)

    db.commit()
    db.refresh(session)

    # ============================================================================
    # CHECK IF ALL SESSIONS FINALIZED
    # ============================================================================
    # ⚠️ NOTE: For INDIVIDUAL_RANKING tournaments, we do NOT automatically set
    # tournament_status to "COMPLETED". The admin must explicitly close the tournament
    # via the tournament lifecycle endpoint. This allows instructors to review
    # final results before tournament closure.

    all_tournament_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True
    ).all()

    unfinalized_sessions = [s for s in all_tournament_sessions if not s.game_results]

    if not unfinalized_sessions:
        # All sessions finalized, but keep tournament open for admin review
        return {
            "success": True,
            "message": "🏆 Session finalized! All sessions completed. Awaiting admin closure.",
            "session_id": session.id,
            "tournament_id": tournament_id,
            "final_rankings": derived_rankings,
            "performance_rankings": performance_rankings,
            "wins_rankings": wins_rankings,
            "tournament_status": tournament.tournament_status,
            "all_sessions_finalized": True
        }

    return {
        "success": True,
        "message": f"✅ Session finalized successfully! {len(unfinalized_sessions)} sessions remaining.",
        "session_id": session.id,
        "tournament_id": tournament_id,
        "final_rankings": derived_rankings,
        "performance_rankings": performance_rankings,
        "wins_rankings": wins_rankings,
        "tournament_status": tournament.tournament_status,
        "all_sessions_finalized": False,
        "remaining_sessions": len(unfinalized_sessions)
    }
