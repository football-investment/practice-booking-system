"""
Public tournament/event detail page — no authentication required.
URL: GET /events/{tournament_id}
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.semester import Semester
from app.models.tournament_ranking import TournamentRanking
from app.models.user import User
from app.models.team import Team, TournamentTeamEnrollment
from app.models.club import Club
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.session import Session as SessionModel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

_STATUS_LABEL = {
    "DRAFT": "Coming Soon",
    "ENROLLMENT_OPEN": "Enrollment Open",
    "ENROLLMENT_CLOSED": "Enrollment Closed",
    "CHECK_IN_OPEN": "Check-In Open",
    "IN_PROGRESS": "In Progress",
    "COMPLETED": "Completed",
    "REWARDS_DISTRIBUTED": "Rewards Distributed",
    "CANCELLED": "Cancelled",
}

_STATUS_COLOR = {
    "DRAFT": "#a0aec0",
    "ENROLLMENT_OPEN": "#48bb78",
    "ENROLLMENT_CLOSED": "#ed8936",
    "CHECK_IN_OPEN": "#667eea",
    "IN_PROGRESS": "#e53e3e",
    "COMPLETED": "#38a169",
    "REWARDS_DISTRIBUTED": "#d69e2e",
    "CANCELLED": "#718096",
}


@router.get("/events/{tournament_id}", response_class=HTMLResponse)
def public_event_detail(
    request: Request,
    tournament_id: int,
    db: Session = Depends(get_db),
):
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        return HTMLResponse("<h2>Event not found</h2>", status_code=404)

    # Every existing event has a public page — visibility is state-driven, not binary.
    # 404 is reserved for non-existent IDs only.
    status = tournament.tournament_status or "DRAFT"

    cfg = tournament.tournament_config_obj
    participant_type = cfg.participant_type if cfg else "INDIVIDUAL"
    tournament_format = tournament.format  # HEAD_TO_HEAD / INDIVIDUAL_RANKING
    max_players = cfg.max_players if cfg else None
    match_duration = cfg.match_duration_minutes if cfg else None
    number_of_legs = cfg.number_of_legs if cfg and hasattr(cfg, "number_of_legs") else 1

    # Location / Campus (multi-campus aware)
    location_name = None
    campus_name = None
    extra_campuses: list[dict] = []
    try:
        from app.models.location import Location
        from app.models.campus import Campus as CampusModel
        if tournament.location_id:
            loc = db.query(Location).filter(Location.id == tournament.location_id).first()
            location_name = loc.city if loc else None
        if tournament.campus_id:
            camp = db.query(CampusModel).filter(CampusModel.id == tournament.campus_id).first()
            campus_name = camp.name if camp else None
            if camp and not location_name and camp.location_id:
                loc = db.query(Location).filter(Location.id == camp.location_id).first()
                location_name = loc.city if loc else None
        # Additional campuses from sessions (multi-campus tournaments)
        session_campus_ids = (
            db.query(SessionModel.campus_id)
            .filter(
                SessionModel.semester_id == tournament_id,
                SessionModel.campus_id.isnot(None),
                SessionModel.campus_id != tournament.campus_id,
            )
            .distinct()
            .all()
        )
        for (cid,) in session_campus_ids:
            c = db.query(CampusModel).filter(CampusModel.id == cid).first()
            if not c:
                continue
            loc2 = db.query(Location).filter(Location.id == c.location_id).first() if c.location_id else None
            extra_campuses.append({
                "name": c.name,
                "location_name": loc2.city if loc2 else None,
            })
    except Exception:
        pass

    # Tournament type display name
    type_name = ""
    try:
        if cfg and cfg.tournament_type:
            type_name = cfg.tournament_type.name
    except Exception:
        pass

    # ── Rankings ──────────────────────────────────────────────────────────────
    ranking_rows = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).order_by(TournamentRanking.rank.asc().nulls_last()).all()

    rankings = []
    if participant_type == "TEAM":
        for row in ranking_rows:
            team = db.query(Team).filter(Team.id == row.team_id).first() if row.team_id else None
            club = db.query(Club).filter(Club.id == team.club_id).first() if team and team.club_id else None
            rankings.append({
                "rank": row.rank,
                "name": team.name if team else f"Team #{row.team_id}",
                "club_name": club.name if club else None,
                "points": row.points,
                "wins": row.wins,
                "draws": row.draws,
                "losses": row.losses,
                "goals_for": row.goals_for,
                "goals_against": row.goals_against,
                "team_id": row.team_id,
                "user_id": None,
            })
    else:
        for row in ranking_rows:
            user = db.query(User).filter(User.id == row.user_id).first() if row.user_id else None
            rankings.append({
                "rank": row.rank,
                "name": user.name if user and user.name else (user.email if user else f"Player #{row.user_id}"),
                "club_name": None,
                "points": row.points,
                "wins": row.wins,
                "draws": row.draws,
                "losses": row.losses,
                "goals_for": row.goals_for,
                "goals_against": row.goals_against,
                "team_id": None,
                "user_id": row.user_id,
            })

    has_rankings = len(rankings) > 0

    # ── Enrolled participants (shown when no final rankings yet) ──────────────
    enrolled_count = 0
    participants = []  # [{name, club_name}] for pre-result display

    if participant_type == "TEAM":
        team_enrollments = db.query(TournamentTeamEnrollment).filter(
            TournamentTeamEnrollment.semester_id == tournament_id,
            TournamentTeamEnrollment.is_active == True,
        ).all()
        enrolled_count = len(team_enrollments)
        if not has_rankings:
            for te in team_enrollments:
                team = db.query(Team).filter(Team.id == te.team_id).first()
                club = db.query(Club).filter(Club.id == team.club_id).first() if team and team.club_id else None
                participants.append({
                    "name": team.name if team else f"Team #{te.team_id}",
                    "club_name": club.name if club else None,
                })
    else:
        enrolled_count = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED,
        ).count()
        if not has_rankings:
            rows = db.query(SemesterEnrollment, User).join(
                User, SemesterEnrollment.user_id == User.id
            ).filter(
                SemesterEnrollment.semester_id == tournament_id,
                SemesterEnrollment.is_active == True,
                SemesterEnrollment.request_status == EnrollmentStatus.APPROVED,
            ).all()
            for enr, user in rows:
                participants.append({
                    "name": user.name if user.name else user.email,
                    "club_name": None,
                })

    # ── Schedule (shown when sessions exist, any state) ───────────────────────
    raw_sessions = (
        db.query(SessionModel)
        .filter(SessionModel.semester_id == tournament_id)
        .order_by(SessionModel.round_number.asc().nulls_last(), SessionModel.id)
        .all()
    )
    sessions_total = len(raw_sessions)

    # Build a team-name cache to avoid N+1 queries
    all_team_ids: set[int] = set()
    for sess in raw_sessions:
        for tid in (sess.participant_team_ids or []):
            all_team_ids.add(tid)
    team_cache: dict[int, str] = {}
    for team in db.query(Team).filter(Team.id.in_(all_team_ids)).all():
        team_cache[team.id] = team.name

    schedule: list[dict] = []
    for sess in raw_sessions:
        tids = sess.participant_team_ids or []
        name_a = team_cache.get(tids[0], f"Team #{tids[0]}") if len(tids) > 0 else "TBD"
        name_b = team_cache.get(tids[1], f"Team #{tids[1]}") if len(tids) > 1 else "TBD"
        score_a = score_b = None
        rr = (sess.rounds_data or {}).get("round_results", {})
        if rr and len(tids) >= 2:
            r1 = rr.get("1", {})
            raw_a = r1.get(f"team_{tids[0]}")
            raw_b = r1.get(f"team_{tids[1]}")
            if raw_a is not None:
                score_a = int(float(raw_a))
            if raw_b is not None:
                score_b = int(float(raw_b))
        schedule.append({
            "round":   sess.round_number,
            "date":    sess.date_start,
            "team_a":  name_a,
            "team_b":  name_b,
            "score_a": score_a,
            "score_b": score_b,
            "done":    sess.session_status == "completed",
        })

    # ── Prize pool (all states — motivational) ────────────────────────────────
    from app.services.tournament.tournament_reward_orchestrator import load_reward_policy_from_config
    prize_pool: list[dict] = []
    try:
        policy = load_reward_policy_from_config(db, tournament_id)
        entries = [
            {"placement": 1, "xp": policy.first_place_xp,  "credits": policy.first_place_credits},
            {"placement": 2, "xp": policy.second_place_xp, "credits": policy.second_place_credits},
            {"placement": 3, "xp": policy.third_place_xp,  "credits": policy.third_place_credits},
        ]
        if policy.participant_xp > 0 or policy.participant_credits > 0:
            entries.append({"placement": 0, "xp": policy.participant_xp, "credits": policy.participant_credits})
        prize_pool = [e for e in entries if e["xp"] > 0 or e["credits"] > 0]
    except Exception:
        prize_pool = []
    has_prize_pool = len(prize_pool) > 0

    # ── Awards (COMPLETED + REWARDS_DISTRIBUTED) ──────────────────────────────
    awards: list[dict] = []
    if status in ("COMPLETED", "REWARDS_DISTRIBUTED"):
        from app.models.tournament_achievement import TournamentParticipation
        parts = db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == tournament_id
        ).order_by(TournamentParticipation.placement.asc()).all()

        placement_map: dict[int, dict] = {}
        for p in parts:
            pl = p.placement
            if pl not in placement_map:
                placement_map[pl] = {
                    "placement": pl,
                    "xp": p.xp_awarded,
                    "credits": p.credits_awarded,
                    "count": 0,
                    "names": [],
                    "players": [],  # [{name, user_id}] for individual; [{name}] for team
                }
            placement_map[pl]["count"] += 1
            if p.team_id:
                team = db.query(Team).filter(Team.id == p.team_id).first()
                name = team.name if team else f"Team #{p.team_id}"
                if name and name not in placement_map[pl]["names"]:
                    placement_map[pl]["names"].append(name)
                    placement_map[pl]["players"].append({"name": name, "user_id": None})
            elif p.user_id:
                user = db.query(User).filter(User.id == p.user_id).first()
                name = (user.name or user.email) if user else f"Player #{p.user_id}"
                if name and name not in placement_map[pl]["names"]:
                    placement_map[pl]["names"].append(name)
                    placement_map[pl]["players"].append({"name": name, "user_id": p.user_id})
            else:
                name = None
        awards = sorted(placement_map.values(), key=lambda x: x["placement"])

    has_awards = len(awards) > 0

    return templates.TemplateResponse(request, "public/tournament_detail.html", {
        "t": tournament,
        "status": status,
        "status_label": _STATUS_LABEL.get(status, status),
        "status_color": _STATUS_COLOR.get(status, "#a0aec0"),
        "theme": tournament.theme or "",
        "focus_description": tournament.focus_description or "",
        "participant_type": participant_type,
        "tournament_format": tournament_format,
        "type_name": type_name,
        "max_players": max_players,
        "match_duration": match_duration,
        "number_of_legs": number_of_legs,
        "location_name": location_name,
        "campus_name": campus_name,
        "extra_campuses": extra_campuses,
        "rankings": rankings,
        "has_rankings": has_rankings,
        "enrolled_count": enrolled_count,
        "participants": participants,
        "sessions_total": sessions_total,
        "schedule": schedule,
        "prize_pool": prize_pool,
        "has_prize_pool": has_prize_pool,
        "awards": awards,
        "has_awards": has_awards,
        "is_draft": status == "DRAFT",
        "is_cancelled": status == "CANCELLED",
    })
