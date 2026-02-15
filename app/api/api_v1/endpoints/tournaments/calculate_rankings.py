"""
Tournament Rankings Calculation Endpoint

Calculates and stores final tournament rankings for both INDIVIDUAL and HEAD_TO_HEAD tournaments.

For INDIVIDUAL tournaments:
- Uses existing ranking strategies (TIME_BASED, SCORE_BASED, ROUNDS_BASED, etc.)

For HEAD_TO_HEAD tournaments:
- League: Points-based ranking (Win=3, Tie=1, Loss=0) with tiebreakers
- Knockout: Bracket-based ranking (Final winner=1, Runner-up=2, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

import json

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.models.booking import Booking
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_achievement import TournamentParticipation
from app.services.tournament.ranking.strategies.factory import RankingStrategyFactory

router = APIRouter()


@router.post("/{tournament_id}/calculate-rankings", status_code=status.HTTP_200_OK)
def calculate_tournament_rankings(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate and store tournament rankings

    For INDIVIDUAL tournaments:
    - Reads session results (rounds_data or game_results)
    - Applies appropriate ranking strategy (TIME_BASED, SCORE_BASED, etc.)
    - Stores rankings in tournament_rankings table

    For HEAD_TO_HEAD tournaments:
    - Reads all match results from sessions
    - Applies league or knockout ranking logic
    - Stores rankings in tournament_rankings table

    Authorization: Master Instructor or Admin only
    Idempotent: Can be called multiple times (overwrites existing rankings)
    """
    # Get tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Authorization: Only master instructor or admin
    if current_user.role != UserRole.ADMIN and tournament.master_instructor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the tournament's master instructor can calculate rankings"
        )

    # Get tournament format
    tournament_format = tournament.format  # "INDIVIDUAL_RANKING" or "HEAD_TO_HEAD"

    # Get all sessions for this tournament
    all_sessions = db.query(SessionModel).filter(
        and_(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True
        )
    ).all()

    if not all_sessions:
        raise HTTPException(
            status_code=400,
            detail="No tournament sessions found. Generate sessions first."
        )

    # Get tournament type to determine which sessions to validate
    tournament_type_code = None
    if tournament.tournament_config_obj and tournament.tournament_config_obj.tournament_type:
        tournament_type_code = tournament.tournament_config_obj.tournament_type.code

    # DEBUG: Log tournament type detection
    print(f"🔍 [calculate_rankings] tournament_id={tournament_id}")
    print(f"🔍 [calculate_rankings] tournament_type_code={tournament_type_code}")
    print(f"🔍 [calculate_rankings] all_sessions count={len(all_sessions)}")

    # For group+knockout tournaments: use GROUP_STAGE sessions for validation,
    # but pass ALL completed sessions (group + knockout) to the ranking strategy
    # so final ranks reflect bracket position, not group stage points.
    if tournament_type_code == "group_knockout":
        group_sessions = [s for s in all_sessions if s.tournament_phase == "GROUP_STAGE"]
        knockout_sessions = [
            s for s in all_sessions
            if s.tournament_phase == "KNOCKOUT" and s.game_results
        ]
        print(f"🔍 [calculate_rankings] group_knockout: {len(group_sessions)} group, {len(knockout_sessions)} completed knockout sessions")
        if not group_sessions:
            raise HTTPException(
                status_code=400,
                detail="No GROUP_STAGE sessions found. Cannot calculate rankings."
            )
        # Validate only group stage sessions must all have results
        group_missing = [s for s in group_sessions if not s.game_results]
        if group_missing:
            raise HTTPException(
                status_code=400,
                detail=f"{len(group_missing)} GROUP_STAGE session(s) do not have results yet."
            )
        # Pass all sessions (group + completed knockout) to strategy
        sessions = group_sessions + knockout_sessions
    else:
        sessions = all_sessions
        print(f"🔍 [calculate_rankings] Using all sessions: {len(sessions)} sessions")
        # Validate all sessions have results
        sessions_with_results = [s for s in sessions if s.game_results or (s.rounds_data and s.rounds_data.get("round_results"))]
        if len(sessions_with_results) < len(sessions):
            missing_count = len(sessions) - len(sessions_with_results)
            raise HTTPException(
                status_code=400,
                detail=f"{missing_count} session(s) do not have results submitted yet. Submit all results first."
            )

    # Calculate rankings based on tournament format
    try:
        if tournament_format == "HEAD_TO_HEAD":
            # Get tournament type (league, knockout, etc.)
            tournament_type_code = None
            if tournament.tournament_config_obj and tournament.tournament_config_obj.tournament_type:
                tournament_type_code = tournament.tournament_config_obj.tournament_type.code

            if not tournament_type_code:
                raise HTTPException(
                    status_code=400,
                    detail="HEAD_TO_HEAD tournament missing tournament_type"
                )

            # Create ranking strategy
            strategy = RankingStrategyFactory.create(
                tournament_format="HEAD_TO_HEAD",
                tournament_type_code=tournament_type_code
            )

            # Calculate rankings
            rankings = strategy.calculate_rankings(sessions, db)

        else:
            # INDIVIDUAL tournament - use existing logic
            # Get scoring type from tournament configuration
            scoring_type = tournament.scoring_type
            if not scoring_type:
                raise HTTPException(
                    status_code=400,
                    detail="INDIVIDUAL tournament missing scoring_type"
                )

            # Create ranking strategy
            strategy = RankingStrategyFactory.create(scoring_type=scoring_type)

            # Calculate rankings (existing INDIVIDUAL logic)
            # Note: This may need adaptation based on existing implementation
            # For now, we'll use a simplified approach
            raise HTTPException(
                status_code=501,
                detail="INDIVIDUAL ranking calculation via this endpoint not yet implemented. Use existing finalization flow."
            )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ranking calculation error: {str(e)}"
        )

    # Delete existing rankings for this tournament (idempotency)
    db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).delete()

    # Insert new rankings
    for ranking_data in rankings:
        ranking_record = TournamentRanking(
            tournament_id=tournament_id,
            user_id=ranking_data["user_id"],
            participant_type="INDIVIDUAL",
            rank=ranking_data["rank"],
            points=ranking_data.get("points", 0),
            wins=ranking_data.get("wins", 0),
            losses=ranking_data.get("losses", 0),
            draws=ranking_data.get("ties", 0),
            goals_for=ranking_data.get("goals_for", ranking_data.get("goals_scored", 0)),
            goals_against=ranking_data.get("goals_against", ranking_data.get("goals_conceded", 0)),
        )
        db.add(ranking_record)

    db.commit()

    return {
        "tournament_id": tournament_id,
        "tournament_format": tournament_format,
        "rankings_count": len(rankings),
        "rankings": rankings,
        "message": "Tournament rankings calculated and stored successfully"
    }


@router.get("/{tournament_id}/rankings", status_code=status.HTTP_200_OK)
def get_tournament_rankings(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tournament rankings

    Returns stored rankings from tournament_rankings table
    """
    # Get tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Get rankings with player names (prefer nickname for uniqueness)
    rows = (
        db.query(TournamentRanking, User.nickname, User.name)
        .join(User, User.id == TournamentRanking.user_id, isouter=True)
        .filter(TournamentRanking.tournament_id == tournament_id)
        .order_by(TournamentRanking.rank)
        .all()
    )

    if not rows:
        return {
            "tournament_id": tournament_id,
            "rankings": [],
            "message": "No rankings calculated yet. Call /calculate-rankings first."
        }

    # Build user_id -> group_identifier map from GROUP_STAGE sessions
    user_group_map: dict = {}
    group_sessions = (
        db.query(SessionModel.group_identifier, SessionModel.participant_user_ids, SessionModel.id)
        .filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.group_identifier.isnot(None)
        )
        .all()
    )
    for gid, participant_user_ids_raw, session_id in group_sessions:
        if not gid:
            continue
        # Try participant_user_ids JSON column first
        if participant_user_ids_raw:
            try:
                uid_list = participant_user_ids_raw if isinstance(participant_user_ids_raw, list) else json.loads(participant_user_ids_raw)
                for uid in uid_list:
                    if uid not in user_group_map:
                        user_group_map[int(uid)] = gid
            except (ValueError, TypeError):
                pass
        # Fallback: derive from bookings
        if not participant_user_ids_raw:
            booking_uids = db.query(Booking.user_id).filter(Booking.session_id == session_id).all()
            for (uid,) in booking_uids:
                if uid not in user_group_map:
                    user_group_map[uid] = gid

    # Load reward data if tournament is REWARDS_DISTRIBUTED
    reward_map: dict = {}  # user_id -> {"xp_earned": int, "credits_earned": int}
    if tournament.tournament_status == "REWARDS_DISTRIBUTED":
        participation_rows = db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == tournament_id
        ).all()

        for p in participation_rows:
            if p.user_id:
                # skill_rating_delta is written at reward-distribution time and is
                # isolated to this tournament — authoritative, not derived from global state
                reward_map[p.user_id] = {
                    "xp_earned": p.xp_awarded or 0,
                    "credits_earned": p.credits_awarded or 0,
                    "skills_awarded": p.skill_points_awarded or {},
                    "skill_rating_delta": p.skill_rating_delta or {},
                }

    # Format response
    rankings_data = []
    for r, nickname, name in rows:
        display_name = nickname or name
        entry = {
            "user_id": r.user_id,
            "name": display_name,
            "rank": r.rank,
            "points": float(r.points) if r.points is not None else 0,
            "wins": r.wins,
            "losses": r.losses,
            "draws": r.draws,
            "goals_for": r.goals_for,
            "goals_against": r.goals_against,
            "goal_difference": (r.goals_for or 0) - (r.goals_against or 0),
            "group_identifier": user_group_map.get(r.user_id),
        }
        if reward_map:
            # Always include reward fields when tournament is REWARDS_DISTRIBUTED,
            # defaulting to empty/zero for users without a participation record
            defaults = {
                "xp_earned": 0,
                "credits_earned": 0,
                "skills_awarded": {},
                "skill_rating_delta": {},
            }
            defaults.update(reward_map.get(r.user_id, {}))
            entry.update(defaults)
        rankings_data.append(entry)

    return {
        "tournament_id": tournament_id,
        "tournament_format": tournament.format,
        "rankings_count": len(rankings_data),
        "rankings": rankings_data
    }
