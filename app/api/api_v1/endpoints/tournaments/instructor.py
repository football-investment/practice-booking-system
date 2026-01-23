"""
Tournament Instructor Endpoints - Thin Router / Orchestration Layer

This module serves as a thin routing layer for instructor-related tournament operations.

⚠️ REFACTORING NOTE (P0-1 Phase 3 - 2026-01-23):
The following endpoints have been EXTRACTED to dedicated modules:

📦 instructor_assignment.py (Assignment Lifecycle):
- POST /{tournament_id}/instructor-assignment/accept
- POST /{tournament_id}/instructor-applications
- POST /{tournament_id}/instructor-applications/{application_id}/approve
- GET /{tournament_id}/instructor-applications
- GET /{tournament_id}/my-application
- GET /instructor/my-applications
- POST /{tournament_id}/direct-assign-instructor
- POST /{tournament_id}/instructor-applications/{application_id}/decline

📦 match_results.py (Match Results Management):
- POST /{tournament_id}/sessions/{session_id}/submit-results
- PATCH /{tournament_id}/sessions/{session_id}/results (legacy)
- POST /{tournament_id}/finalize-group-stage
- POST /{tournament_id}/finalize-tournament

This file now contains:
- Session queries (active-match, leaderboard)
- Debug utilities
- Orchestration logic

See: REFACTORING_IMPLEMENTATION_PLAN.md
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

router = APIRouter()


# ============================================================================
# MATCH COMMAND CENTER ENDPOINTS
# ============================================================================

@router.get("/{tournament_id}/active-match")
async def get_active_match(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the current active match (session) that needs attention.

    Returns the first tournament session where:
    - is_tournament_game = true
    - game_results IS NULL (not yet recorded)

    Includes:
    - Session details
    - List of enrolled participants with attendance status
    - Next upcoming matches (queue)

    Authorization: INSTRUCTOR (must be assigned to tournament) or ADMIN
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
            detail="Only instructors and admins can access match management"
        )

    # ============================================================================
    # GET ACTIVE MATCH (first session without results)
    # ============================================================================
    from app.models.attendance import Attendance
    from sqlalchemy.orm import joinedload

    active_session = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.game_results == None
    ).order_by(SessionModel.id).first()  # ✅ FIX: Order by ID for consistent match sequence (all sessions have same date_start with parallel fields)

    if not active_session:
        # No more matches to process
        return {
            "active_match": None,
            "message": "All matches have been completed",
            "tournament_id": tournament_id,
            "tournament_name": tournament.name
        }

    # ============================================================================
    # GET PARTICIPANTS - EXPLICIT participant_user_ids ONLY
    # ✅ MATCH STRUCTURE: No runtime filtering! Use explicit participant list.
    # ✅ NO BOOKINGS: Tournament sessions use participant_user_ids + semester_enrollments
    # ============================================================================

    # ⚠️ PREREQUISITE CHECK: participant_user_ids must be defined
    if active_session.participant_user_ids is None:
        # This match cannot start yet (e.g., knockout waiting for group stage results)
        return {
            "active_match": None,
            "message": "Match participants not yet determined. Prerequisites not met.",
            "prerequisite_status": {
                "ready": False,
                "reason": "Knockout matches require group stage results to determine qualified participants.",
                "action_required": "Complete all group stage matches first."
            },
            "tournament_id": tournament_id,
            "tournament_name": tournament.name
        }

    # Get EXPLICIT match participants (NO FILTERING, NO FALLBACK, NO BOOKINGS)
    match_participant_user_ids = active_session.participant_user_ids

    # Query users directly (NO bookings dependency)
    from app.models.user import User
    users = db.query(User).filter(
        User.id.in_(match_participant_user_ids)
    ).all()

    # Build MATCH participants list (EXPLICIT ONLY)
    match_participants = []
    for user in users:
        # Check if attendance has been marked (attendance links directly to session + user)
        attendance = db.query(Attendance).filter(
            Attendance.session_id == active_session.id,
            Attendance.user_id == user.id
        ).first()

        match_participants.append({
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "attendance_status": attendance.status.value if attendance else "PENDING",
            "is_present": attendance.status.value == "present" if attendance else False
        })

    # Get ALL tournament participants (TOURNAMENT SCOPE) for debugging/context
    # Get from semester_enrollments, not bookings
    tournament_enrollments = db.query(SemesterEnrollment).options(
        joinedload(SemesterEnrollment.user)
    ).filter(
        SemesterEnrollment.semester_id == tournament_id,
        SemesterEnrollment.is_active == True,
        SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
    ).all()

    tournament_participants = []
    for enrollment in tournament_enrollments:
        attendance = db.query(Attendance).filter(
            Attendance.session_id == active_session.id,
            Attendance.user_id == enrollment.user_id
        ).first()

        tournament_participants.append({
            "user_id": enrollment.user_id,
            "name": enrollment.user.name,
            "email": enrollment.user.email,
            "attendance_status": attendance.status.value if attendance else "PENDING",
            "is_present": attendance.status.value == "present" if attendance else False
        })

    # ============================================================================
    # GET UPCOMING MATCHES (next 5 sessions without results)
    # ============================================================================
    upcoming_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.game_results == None,
        SessionModel.id != active_session.id
    ).order_by(SessionModel.date_start).limit(5).all()

    upcoming_matches = [
        {
            "session_id": s.id,
            "match_name": s.title,
            "start_time": s.date_start.isoformat() if s.date_start else None,
            "location": s.location
        }
        for s in upcoming_sessions
    ]

    # ✅ NEW: Calculate tournament progress
    total_matches = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True
    ).count()

    completed_matches = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.game_results != None
    ).count()

    # ============================================================================
    # RETURN ACTIVE MATCH DATA
    # ✅ MATCH STRUCTURE: Explicit scope separation
    # ============================================================================
    return {
        "active_match": {
            "session_id": active_session.id,
            "match_name": active_session.title,
            "match_description": active_session.description,
            "start_time": active_session.date_start.isoformat() if active_session.date_start else None,
            "end_time": active_session.date_end.isoformat() if active_session.date_end else None,
            "location": active_session.location,
            # ✅ EXPLICIT SCOPE SEPARATION: Two participant lists
            "match_participants": match_participants,  # ⚠️ USE THIS FOR RESULT INPUT!
            "tournament_participants": tournament_participants,  # For debugging/context only
            "match_participants_count": len(match_participants),
            "tournament_participants_count": len(tournament_participants),
            "present_count": sum(1 for p in match_participants if p["is_present"]),
            "pending_count": sum(1 for p in match_participants if p["attendance_status"] == "PENDING"),
            # ✅ UNIFIED RANKING: Ranking metadata for frontend
            "ranking_mode": active_session.ranking_mode,
            "group_identifier": active_session.group_identifier,
            "expected_participants": active_session.expected_participants,
            "participant_filter": active_session.participant_filter,
            "pod_tier": active_session.pod_tier,
            "tournament_phase": active_session.tournament_phase,
            "tournament_round": active_session.tournament_round,
            # ✅ MATCH STRUCTURE: Format and scoring metadata
            "match_format": active_session.match_format or 'INDIVIDUAL_RANKING',  # Backward compatibility
            "scoring_type": active_session.scoring_type or 'PLACEMENT',
            "structure_config": active_session.structure_config
        },
        "upcoming_matches": upcoming_matches,
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        # ✅ NEW: Progress tracking
        "total_matches": total_matches,
        "completed_matches": completed_matches
    }


async def get_tournament_leaderboard(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get live tournament leaderboard/standings.

    Returns:
    - Ranked list of participants
    - Total points, matches played
    - Win/loss statistics (future enhancement)

    Authorization: Anyone can view (public leaderboard)
    But tournament must exist and be accessible to current user
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

    # Check if user has access (students must be enrolled, instructors must be assigned, admins always have access)
    if current_user.role == UserRole.ADMIN:
        pass
    elif current_user.role == UserRole.INSTRUCTOR:
        if tournament.master_instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this tournament"
            )
    elif current_user.role == UserRole.STUDENT:
        # Check if student is enrolled
        from app.models.semester_enrollment import SemesterEnrollment
        enrollment = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.user_id == current_user.id,
            SemesterEnrollment.is_active == True
        ).first()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this tournament"
            )

    # ============================================================================
    # GET LEADERBOARD DATA
    # ============================================================================
    rankings = db.execute(
        text("""
        SELECT
            tr.user_id,
            u.name as user_name,
            u.email as user_email,
            COALESCE(tr.points, 0) as points,
            COALESCE(tr.wins, 0) as wins,
            COALESCE(tr.losses, 0) as losses,
            COALESCE(tr.draws, 0) as draws,
            tr.updated_at
        FROM tournament_rankings tr
        JOIN users u ON tr.user_id = u.id
        WHERE tr.tournament_id = :tournament_id
        ORDER BY COALESCE(tr.points, 0) DESC, u.name ASC
        """),
        {"tournament_id": tournament_id}
    ).fetchall()

    leaderboard = []
    for rank, row in enumerate(rankings, start=1):
        leaderboard.append({
            "rank": rank,
            "user_id": row.user_id,
            "name": row.user_name,
            "email": row.user_email,
            "points": float(row.points) if row.points else 0.0,
            "wins": row.wins,
            "losses": row.losses,
            "draws": row.draws,
            "last_updated": row.updated_at.isoformat() if row.updated_at else None
        })

    # ============================================================================
    # ✅ NEW: GROUP STANDINGS (for Group + Knockout tournaments)
    # ============================================================================
    group_standings = {}

    # Check if this tournament has group stage sessions
    group_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.tournament_phase == 'Group Stage'
    ).all()

    # ============================================================================
    # GET TOURNAMENT STATS
    # ============================================================================
    # If tournament has group stages, only count group stage matches for progress
    # (because knockout matches can't start until group stage is finalized)
    if group_sessions:
        total_matches = len(group_sessions)
        completed_matches = sum(1 for s in group_sessions if s.game_results is not None)
    else:
        # For non-group tournaments, count all matches
        total_matches = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True
        ).count()

        completed_matches = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True,
            SessionModel.game_results != None
        ).count()

    if group_sessions:
        # Calculate group standings from game_results
        from collections import defaultdict

        # Structure: {group_id: {user_id: {wins, losses, draws, points, goals_for, goals_against}}}
        group_stats = defaultdict(lambda: defaultdict(lambda: {
            'wins': 0, 'losses': 0, 'draws': 0, 'points': 0,
            'goals_for': 0, 'goals_against': 0, 'matches_played': 0
        }))

        # ✅ NEW: Initialize all groups with all participants (even if no matches played yet)
        for session in group_sessions:
            if session.group_identifier and session.participant_user_ids:
                group_id = session.group_identifier
                # Initialize all participants in this group with 0 stats
                for user_id in session.participant_user_ids:
                    # This will create the entry with default values if not exists
                    _ = group_stats[group_id][user_id]

        # Process completed matches
        for session in group_sessions:
            if not session.game_results or not session.group_identifier:
                continue

            group_id = session.group_identifier
            results = session.game_results

            # ✅ FIX: Parse game_results if it's a JSON string
            import json
            if isinstance(results, str):
                try:
                    results = json.loads(results)
                except json.JSONDecodeError:
                    continue

            # ✅ FIX: game_results is now a dict with "raw_results" key
            if isinstance(results, dict):
                raw_results = results.get('raw_results', [])
            elif isinstance(results, list):
                raw_results = results  # Fallback for old format
            else:
                continue

            # Process HEAD_TO_HEAD SCORE_BASED results
            if isinstance(raw_results, list) and len(raw_results) == 2:
                # Expect format: [{"user_id": X, "score": A}, {"user_id": Y, "score": B}]
                if all('user_id' in r and 'score' in r for r in raw_results):
                    user1_id = raw_results[0]['user_id']
                    user2_id = raw_results[1]['user_id']
                    score1 = raw_results[0]['score']
                    score2 = raw_results[1]['score']

                    # Update stats
                    group_stats[group_id][user1_id]['goals_for'] += score1
                    group_stats[group_id][user1_id]['goals_against'] += score2
                    group_stats[group_id][user2_id]['goals_for'] += score2
                    group_stats[group_id][user2_id]['goals_against'] += score1

                    group_stats[group_id][user1_id]['matches_played'] += 1
                    group_stats[group_id][user2_id]['matches_played'] += 1

                    if score1 > score2:
                        # User 1 wins
                        group_stats[group_id][user1_id]['wins'] += 1
                        group_stats[group_id][user1_id]['points'] += 3
                        group_stats[group_id][user2_id]['losses'] += 1
                    elif score2 > score1:
                        # User 2 wins
                        group_stats[group_id][user2_id]['wins'] += 1
                        group_stats[group_id][user2_id]['points'] += 3
                        group_stats[group_id][user1_id]['losses'] += 1
                    else:
                        # Draw
                        group_stats[group_id][user1_id]['draws'] += 1
                        group_stats[group_id][user1_id]['points'] += 1
                        group_stats[group_id][user2_id]['draws'] += 1
                        group_stats[group_id][user2_id]['points'] += 1

        # Convert to sorted standings per group
        from app.models.user import User

        for group_id, stats in group_stats.items():
            standings = []

            for user_id, user_stats in stats.items():
                # Fetch user name
                user = db.query(User).filter(User.id == user_id).first()
                user_name = user.name if user else f"User {user_id}"

                goal_diff = user_stats['goals_for'] - user_stats['goals_against']

                standings.append({
                    'user_id': user_id,
                    'name': user_name,
                    'points': user_stats['points'],
                    'wins': user_stats['wins'],
                    'losses': user_stats['losses'],
                    'draws': user_stats['draws'],
                    'matches_played': user_stats['matches_played'],
                    'goals_for': user_stats['goals_for'],
                    'goals_against': user_stats['goals_against'],
                    'goal_difference': goal_diff
                })

            # Sort by: points DESC, goal_difference DESC, goals_for DESC
            standings.sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))

            # Add rank
            for rank, player in enumerate(standings, start=1):
                player['rank'] = rank

            group_standings[group_id] = standings

    # ============================================================================
    # CHECK IF GROUP STAGE IS FINALIZED
    # ============================================================================
    group_stage_finalized = False
    knockout_sessions = []

    if group_sessions:
        # Check if any knockout session has participants assigned
        knockout_sessions = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True,
            SessionModel.tournament_phase == "Knockout Stage"
        ).all()

        if any(s.participant_user_ids for s in knockout_sessions):
            group_stage_finalized = True

    # ============================================================================
    # CALCULATE FINAL STANDINGS (for knockout tournaments that are complete)
    # ============================================================================
    final_standings = None

    if group_stage_finalized and knockout_sessions:
        # Check if ALL knockout matches are completed
        all_knockout_complete = all(s.game_results is not None for s in knockout_sessions)

        if all_knockout_complete:
            # Find final and bronze matches
            final_match = None
            bronze_match = None

            for session in knockout_sessions:
                title_lower = session.title.lower()
                if 'bronze' in title_lower or '3rd place' in title_lower:
                    bronze_match = session
                elif session.tournament_round == max(s.tournament_round for s in knockout_sessions):
                    # Highest round = final
                    if final_match is None or 'final' in title_lower:
                        final_match = session

            if final_match and final_match.game_results:
                # Parse final match results
                final_results = final_match.game_results
                if isinstance(final_results, str):
                    final_results = json.loads(final_results)

                final_rankings = final_results.get('derived_rankings', [])

                # Get winner and runner-up from final
                champion_id = None
                runner_up_id = None

                for r in final_rankings:
                    if r['rank'] == 1:
                        champion_id = r['user_id']
                    elif r['rank'] == 2:
                        runner_up_id = r['user_id']

                # Get 3rd and 4th from bronze match
                third_place_id = None
                fourth_place_id = None

                if bronze_match and bronze_match.game_results:
                    bronze_results = bronze_match.game_results
                    if isinstance(bronze_results, str):
                        bronze_results = json.loads(bronze_results)

                    bronze_rankings = bronze_results.get('derived_rankings', [])

                    for r in bronze_rankings:
                        if r['rank'] == 1:
                            third_place_id = r['user_id']
                        elif r['rank'] == 2:
                            fourth_place_id = r['user_id']

                # Build final standings with user details
                from app.models.user import User as UserModel

                user_ids = [champion_id, runner_up_id, third_place_id, fourth_place_id]
                user_ids = [uid for uid in user_ids if uid is not None]

                users = db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()
                user_dict = {user.id: user for user in users}

                final_standings = []

                if champion_id and champion_id in user_dict:
                    final_standings.append({
                        'rank': 1,
                        'medal': '🥇',
                        'user_id': champion_id,
                        'name': user_dict[champion_id].name or user_dict[champion_id].email,
                        'title': 'Champion'
                    })

                if runner_up_id and runner_up_id in user_dict:
                    final_standings.append({
                        'rank': 2,
                        'medal': '🥈',
                        'user_id': runner_up_id,
                        'name': user_dict[runner_up_id].name or user_dict[runner_up_id].email,
                        'title': 'Runner-up'
                    })

                if third_place_id and third_place_id in user_dict:
                    final_standings.append({
                        'rank': 3,
                        'medal': '🥉',
                        'user_id': third_place_id,
                        'name': user_dict[third_place_id].name or user_dict[third_place_id].email,
                        'title': 'Third Place'
                    })

                if fourth_place_id and fourth_place_id in user_dict:
                    final_standings.append({
                        'rank': 4,
                        'medal': '',
                        'user_id': fourth_place_id,
                        'name': user_dict[fourth_place_id].name or user_dict[fourth_place_id].email,
                        'title': 'Fourth Place'
                    })

    # ============================================================================
    # RETURN LEADERBOARD
    # ============================================================================
    return {
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        "leaderboard": leaderboard,
        "group_standings": group_standings if group_standings else None,  # ✅ NEW
        "group_stage_finalized": group_stage_finalized,  # ✅ NEW
        "final_standings": final_standings,  # ✅ NEW
        "total_participants": len(leaderboard),
        "total_matches": total_matches,
        "completed_matches": completed_matches,
        "remaining_matches": total_matches - completed_matches,
        "tournament_status": tournament.tournament_status
    }


# ============================================================================
# DEBUG UTILITIES
# ============================================================================

def get_tournament_sessions_debug(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get all sessions for a tournament with participant_user_ids for debug purposes

    Authorization: INSTRUCTOR or ADMIN
    """
    try:
        print(f"🔍 DEBUG: get_tournament_sessions called for tournament_id={tournament_id}, user={current_user.email}")

        # Check authorization
        tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

        if not tournament:
            print(f"🔍 DEBUG: Tournament {tournament_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tournament {tournament_id} not found"
            )

        print(f"🔍 DEBUG: Tournament found: {tournament.name}, master_instructor_id={tournament.master_instructor_id}")

        if current_user.role == UserRole.ADMIN:
            print(f"🔍 DEBUG: User is ADMIN, access granted")
            pass  # Admin can access any tournament
        elif current_user.role == UserRole.INSTRUCTOR:
            print(f"🔍 DEBUG: User is INSTRUCTOR, checking assignment")
            if tournament.master_instructor_id != current_user.id:
                print(f"🔍 DEBUG: Access denied - instructor not assigned")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not assigned to this tournament"
                )
            print(f"🔍 DEBUG: Access granted - instructor is assigned")
        else:
            print(f"🔍 DEBUG: Access denied - role is {current_user.role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only instructors and admins can access tournament sessions"
            )

        # Get all sessions
        sessions = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True
        ).order_by(SessionModel.date_start).all()

        print(f"🔍 DEBUG: Found {len(sessions)} tournament sessions")

        result = []
        for idx, session in enumerate(sessions):
            print(f"🔍 DEBUG: Processing session {idx+1}/{len(sessions)}: id={session.id}, participant_user_ids={session.participant_user_ids}")

            # Get participant names from user IDs
            participant_names = []
            if session.participant_user_ids:
                for user_id in session.participant_user_ids:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        participant_names.append(user.name)
                    else:
                        participant_names.append(f"User {user_id}")

            # Extract matchup info from structure_config for knockout matches
            matchup_display = None
            if session.structure_config and isinstance(session.structure_config, dict):
                matchup_display = session.structure_config.get('matchup')

            # Parse game_results if it's a JSON string
            game_results_parsed = None
            if session.game_results:
                if isinstance(session.game_results, str):
                    try:
                        game_results_parsed = json.loads(session.game_results)
                    except:
                        game_results_parsed = session.game_results
                else:
                    game_results_parsed = session.game_results

            result.append({
                "session_id": session.id,
                "title": session.title,
                "tournament_phase": session.tournament_phase,
                "tournament_round": session.tournament_round,
                "group_identifier": session.group_identifier,
                "round_number": session.round_number,
                "match_format": session.match_format,
                "scoring_type": session.scoring_type,
                "expected_participants": session.expected_participants,
                "participant_user_ids": session.participant_user_ids,
                "participant_names": participant_names,
                "matchup_display": matchup_display,  # ADDED: For knockout matches (A1 vs B2, etc.)
                "date": session.date_start.isoformat() if session.date_start else None,
                "has_results": session.game_results is not None,
                "game_results": game_results_parsed  # ✅ ADDED
            })

        print(f"🔍 DEBUG: Returning {len(result)} sessions")
        return result

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        print(f"🔍 DEBUG: EXCEPTION in get_tournament_sessions: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
