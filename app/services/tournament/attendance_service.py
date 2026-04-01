"""
Attendance Service

Pre-tournament check-in management for promotion events.

Workflow:
  1. Admin marks instructors CHECKED_IN (via TournamentInstructorSlot system)
  2. Admin checks in teams (TournamentTeamEnrollment.checked_in_at)
  3. Admin checks in individual players (TournamentPlayerCheckin table)
  4. Session generator uses only checked-in participants (opt-in mode)
  5. During sessions: admin can postpone a match with a reason

All functions assume the caller is authenticated as admin (auth enforced at route layer).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.team import Team, TeamMember, TournamentTeamEnrollment, TournamentPlayerCheckin
from app.models.session import Session as SessionModel
from app.models.semester import Semester
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.user import User
from app.models.tournament_instructor_slot import TournamentInstructorSlot, SlotStatus


# ─────────────────────────────────────────────────────────────────────────────
# Instructor check-in gate
# ─────────────────────────────────────────────────────────────────────────────

def _require_instructor_checked_in(db: Session, tournament_id: int) -> None:
    """Raise HTTP 409 if no instructor is CHECKED_IN for this tournament.

    Player/team check-in is only allowed after at least one instructor has
    physically checked in (SlotStatus.CHECKED_IN).  This enforces the
    correct on-site workflow: instructors arrive and confirm readiness first,
    then participants are admitted.
    """
    count = (
        db.query(TournamentInstructorSlot)
        .filter(
            TournamentInstructorSlot.semester_id == tournament_id,
            TournamentInstructorSlot.status == SlotStatus.CHECKED_IN,
        )
        .count()
    )
    if count == 0:
        raise HTTPException(
            status_code=409,
            detail="At least one instructor must be checked in before player/team check-in.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Team check-in
# ─────────────────────────────────────────────────────────────────────────────

def checkin_team(
    db: Session,
    tournament_id: int,
    team_id: int,
    by_user_id: int,
) -> TournamentTeamEnrollment:
    """Mark a team as checked-in for the tournament."""
    enrollment = _get_enrollment_or_404(db, tournament_id, team_id)
    _require_instructor_checked_in(db, tournament_id)
    enrollment.checked_in_at = datetime.now(timezone.utc)
    enrollment.checked_in_by_id = by_user_id
    db.flush()
    return enrollment


def uncheckin_team(
    db: Session,
    tournament_id: int,
    team_id: int,
    by_user_id: int,
) -> TournamentTeamEnrollment:
    """Remove check-in for a team."""
    enrollment = _get_enrollment_or_404(db, tournament_id, team_id)
    enrollment.checked_in_at = None
    enrollment.checked_in_by_id = None
    db.flush()
    return enrollment


# ─────────────────────────────────────────────────────────────────────────────
# Player check-in
# ─────────────────────────────────────────────────────────────────────────────

def checkin_player(
    db: Session,
    tournament_id: int,
    user_id: int,
    team_id: Optional[int],
    by_user_id: int,
) -> TournamentPlayerCheckin:
    """Check in an individual player for the tournament (upsert).

    For INDIVIDUAL tournaments (team_id=None) also stamps
    SemesterEnrollment.tournament_checked_in_at so that the session
    generator — which reads that column — sees the check-in.
    """
    # Verify tournament exists
    _get_tournament_or_404(db, tournament_id)
    _require_instructor_checked_in(db, tournament_id)

    now_utc = datetime.now(timezone.utc)

    existing = db.query(TournamentPlayerCheckin).filter(
        TournamentPlayerCheckin.tournament_id == tournament_id,
        TournamentPlayerCheckin.user_id == user_id,
    ).first()

    if existing:
        existing.checked_in_at = now_utc
        existing.checked_in_by_id = by_user_id
        existing.team_id = team_id
    else:
        existing = TournamentPlayerCheckin(
            tournament_id=tournament_id,
            user_id=user_id,
            team_id=team_id,
            checked_in_by_id=by_user_id,
        )
        db.add(existing)

    # Sync SemesterEnrollment.tournament_checked_in_at for INDIVIDUAL check-ins.
    # The session generator reads this column to build the seeding pool; without
    # the sync it falls back to all approved enrollments, ignoring the check-in.
    if team_id is None:
        enrollment = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.user_id == user_id,
            SemesterEnrollment.is_active == True,
        ).first()
        if enrollment:
            enrollment.tournament_checked_in_at = now_utc

    db.flush()
    return existing


def uncheckin_player(
    db: Session,
    tournament_id: int,
    user_id: int,
) -> None:
    """Remove pre-tournament check-in for a player.

    Also clears SemesterEnrollment.tournament_checked_in_at so the
    session generator no longer counts this player as confirmed.
    """
    checkin = db.query(TournamentPlayerCheckin).filter(
        TournamentPlayerCheckin.tournament_id == tournament_id,
        TournamentPlayerCheckin.user_id == user_id,
    ).first()
    if checkin:
        db.delete(checkin)

    # Clear the SemesterEnrollment stamp (INDIVIDUAL path).
    enrollment = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.semester_id == tournament_id,
        SemesterEnrollment.user_id == user_id,
    ).first()
    if enrollment and enrollment.tournament_checked_in_at is not None:
        enrollment.tournament_checked_in_at = None

    db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Session postpone
# ─────────────────────────────────────────────────────────────────────────────

def postpone_session(
    db: Session,
    session_id: int,
    reason: str,
) -> SessionModel:
    """Record a postponement reason for a session/match."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    session.postponed_reason = reason.strip() if reason else None
    db.flush()
    return session


# ─────────────────────────────────────────────────────────────────────────────
# Attendance summary
# ─────────────────────────────────────────────────────────────────────────────

def get_attendance_summary(db: Session, tournament_id: int) -> Dict[str, Any]:
    """
    Build the full attendance picture for the attendance page.

    Branches on participant_type:
      TEAM      → teams list (with nested players per team)
      INDIVIDUAL → flat individual_players list (SemesterEnrollment-based)

    Returns:
        {
          participant_type: "TEAM" | "INDIVIDUAL",
          instructors: [{slot_id, instructor_id, instructor_name, role, status, checked_in_at}],
          teams: [                   # non-empty only for TEAM tournaments
            {
              team_id, team_name, enrollment_id, checked_in_at, checked_in_by_name,
              player_count, players_checked_in,
              players: [{user_id, name, checked_in_at}],
            }
          ],
          individual_players: [     # non-empty only for INDIVIDUAL tournaments
            {user_id, name, email, checked_in_at}
          ],
          summary: {
            instructors_total, instructors_checked_in,
            teams_total, teams_checked_in,
            players_total, players_checked_in,
            sessions_generated, sessions_postponed,
          },
        }
    """
    tournament = _get_tournament_or_404(db, tournament_id)
    participant_type = getattr(tournament, "participant_type", "INDIVIDUAL") or "INDIVIDUAL"

    # ── Instructors ─────────────────────────────────────────────────────────
    slots = (
        db.query(TournamentInstructorSlot)
        .filter(TournamentInstructorSlot.semester_id == tournament_id)
        .order_by(TournamentInstructorSlot.role, TournamentInstructorSlot.id)
        .all()
    )
    instructors_data: List[Dict] = []
    for slot in slots:
        instructors_data.append({
            "slot_id": slot.id,
            "instructor_id": slot.instructor_id,
            "instructor_name": slot.instructor.name if slot.instructor else None,
            "role": slot.role,
            "pitch_name": slot.pitch.name if slot.pitch else None,
            "status": slot.status,
            "checked_in_at": slot.checked_in_at.isoformat() if slot.checked_in_at else None,
        })

    instructors_checked_in = sum(1 for s in slots if s.status == "CHECKED_IN")

    teams_data: List[Dict] = []
    individual_players_data: List[Dict] = []
    total_players = 0
    total_players_checked_in = 0

    if participant_type == "TEAM":
        # ── Teams ─────────────────────────────────────────────────────────
        team_enrollments = (
            db.query(TournamentTeamEnrollment)
            .filter(
                TournamentTeamEnrollment.semester_id == tournament_id,
                TournamentTeamEnrollment.is_active == True,
            )
            .all()
        )

        # Pre-load player checkins for this tournament
        player_checkins = db.query(TournamentPlayerCheckin).filter(
            TournamentPlayerCheckin.tournament_id == tournament_id
        ).all()
        checkin_by_user: Dict[int, TournamentPlayerCheckin] = {
            c.user_id: c for c in player_checkins
        }

        for enrollment in team_enrollments:
            team = enrollment.team
            if not team:
                continue

            members = (
                db.query(TeamMember)
                .filter(TeamMember.team_id == team.id, TeamMember.is_active == True)
                .all()
            )

            if not members:
                logger.warning(
                    "Team %d (%s) is enrolled in tournament %d but has no active members",
                    team.id, team.name, tournament_id,
                )

            players: List[Dict] = []
            for member in members:
                user = member.user
                pc = checkin_by_user.get(member.user_id)
                players.append({
                    "user_id": member.user_id,
                    "name": user.name if user else f"User #{member.user_id}",
                    "checked_in_at": pc.checked_in_at.isoformat() if pc and pc.checked_in_at else None,
                })

            players_in = sum(1 for p in players if p["checked_in_at"])
            total_players += len(players)
            total_players_checked_in += players_in

            by_name = None
            if enrollment.checked_in_by_id:
                by_user = db.query(User).filter(User.id == enrollment.checked_in_by_id).first()
                by_name = by_user.name if by_user else None

            teams_data.append({
                "team_id": team.id,
                "team_name": team.name,
                "enrollment_id": enrollment.id,
                "checked_in_at": enrollment.checked_in_at.isoformat() if enrollment.checked_in_at else None,
                "checked_in_by_name": by_name,
                "player_count": len(players),
                "players_checked_in": players_in,
                "players": players,
            })

    else:
        # ── Individual players ─────────────────────────────────────────────
        ind_enrollments = (
            db.query(SemesterEnrollment)
            .filter(
                SemesterEnrollment.semester_id == tournament_id,
                SemesterEnrollment.is_active == True,
                SemesterEnrollment.request_status == EnrollmentStatus.APPROVED,
            )
            .order_by(SemesterEnrollment.user_id)
            .all()
        )

        # Pre-load player checkins (TournamentPlayerCheckin, team_id=NULL for individual)
        player_checkins = db.query(TournamentPlayerCheckin).filter(
            TournamentPlayerCheckin.tournament_id == tournament_id
        ).all()
        checkin_by_user_ind: Dict[int, TournamentPlayerCheckin] = {
            c.user_id: c for c in player_checkins
        }

        for enrollment in ind_enrollments:
            user = enrollment.user
            pc = checkin_by_user_ind.get(enrollment.user_id)
            individual_players_data.append({
                "user_id": enrollment.user_id,
                "name": user.name if user else f"User #{enrollment.user_id}",
                "email": user.email if user else None,
                "checked_in_at": pc.checked_in_at.isoformat() if pc and pc.checked_in_at else None,
            })

        total_players = len(individual_players_data)
        total_players_checked_in = sum(
            1 for p in individual_players_data if p["checked_in_at"]
        )

    # ── Session stats ────────────────────────────────────────────────────────
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.semester_id == tournament_id)
        .all()
    )
    sessions_generated = len(sessions)
    sessions_postponed = sum(1 for s in sessions if s.postponed_reason)

    # ── Summary ──────────────────────────────────────────────────────────────
    summary = {
        "instructors_total": len(slots),
        "instructors_checked_in": instructors_checked_in,
        "teams_total": len(teams_data),
        "teams_checked_in": sum(1 for t in teams_data if t["checked_in_at"]),
        "players_total": total_players,
        "players_checked_in": total_players_checked_in,
        "sessions_generated": sessions_generated,
        "sessions_postponed": sessions_postponed,
    }

    return {
        "participant_type": participant_type,
        "instructors": instructors_data,
        "teams": teams_data,
        "individual_players": individual_players_data,
        "summary": summary,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_tournament_or_404(db: Session, tournament_id: int) -> Semester:
    t = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not t:
        raise HTTPException(status_code=404, detail=f"Tournament {tournament_id} not found")
    return t


def _get_enrollment_or_404(
    db: Session,
    tournament_id: int,
    team_id: int,
) -> TournamentTeamEnrollment:
    enrollment = db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == tournament_id,
        TournamentTeamEnrollment.team_id == team_id,
        TournamentTeamEnrollment.is_active == True,
    ).first()
    if not enrollment:
        raise HTTPException(
            status_code=404,
            detail=f"Team {team_id} is not enrolled in tournament {tournament_id}",
        )
    return enrollment
