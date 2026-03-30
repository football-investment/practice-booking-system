"""
Seed All Lifecycle States — TEAM formats (H2H League, Group Knockout, Swiss)
=============================================================================
Creates one tournament for every lifecycle state for each of 3 team-based formats.
Uses the 3 bootstrap teams (LFA U15, LFA U18, LFA Adult) and their 36 players.

Formats seeded (each with 8 states):
  H2H LEAGUE     — TEAM participant_type, 3 teams round-robin
  GROUP_KNOCKOUT — INDIVIDUAL participant_type, 36 bootstrap players
  SWISS          — INDIVIDUAL participant_type, 36 bootstrap players

Requires: bootstrap_clean.py must have been run first (admin, instructor,
          campus, game preset, LFA-BOOT club with 3 teams × 12 players).

Usage:
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \\
        SECRET_KEY="..." PYTHONPATH=. python scripts/seed_all_lifecycle_states_team.py
"""
import os
import sys
import uuid

from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
os.environ.setdefault("SECRET_KEY", "e2e-test-secret-key-minimum-32-chars-needed")

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.session import Session as SessionModel
from app.models.tournament_configuration import TournamentConfiguration
from app.models.game_configuration import GameConfiguration
from app.models.game_preset import GamePreset
from app.models.tournament_type import TournamentType
from app.models.campus import Campus
from app.models.club import Club
from app.models.team import Team, TeamMember
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.tournament_reward_config import TournamentRewardConfig
from app.models.user import User
from app.models.team import TournamentTeamEnrollment
from app.models.tournament_ranking import TournamentRanking
from app.dependencies import (
    get_current_user_web,
    get_current_admin_user_hybrid,
    get_current_admin_or_instructor_user_hybrid,
)

# ── Setup ──────────────────────────────────────────────────────────────────
db = SessionLocal()

admin = db.query(User).filter(User.email == "admin@lfa.com").first()
instructor = db.query(User).filter(User.email == "instructor@lfa.com").first()
if not admin or not instructor:
    print("❌ admin@lfa.com or instructor@lfa.com not found — run bootstrap_clean.py first")
    sys.exit(1)

campus = db.query(Campus).first()
if not campus:
    print("❌ No campus found — run bootstrap_clean.py first")
    sys.exit(1)

preset = db.query(GamePreset).first()
if not preset:
    print("❌ No GamePreset found — run bootstrap_clean.py first")
    sys.exit(1)

boot_club = db.query(Club).filter(Club.code == "LFA-BOOT").first()
if not boot_club:
    print("❌ LFA-BOOT club not found — run bootstrap_clean.py first")
    sys.exit(1)

boot_teams = db.query(Team).filter(
    Team.club_id == boot_club.id,
    Team.name.in_(["LFA U15", "LFA U18", "LFA Adult"]),
).order_by(Team.name).all()
if len(boot_teams) != 3:
    print(f"❌ Expected 3 named bootstrap teams (LFA U15/U18/Adult), found {len(boot_teams)} — run bootstrap_clean.py first")
    sys.exit(1)

# All 36 bootstrap players (individual enrollments)
all_boot_players: list[User] = (
    db.query(User)
    .join(TeamMember, TeamMember.user_id == User.id)
    .join(Team, Team.id == TeamMember.team_id)
    .filter(Team.id.in_([t.id for t in boot_teams]))
    .all()
)

# TournamentType lookups
tt_league = db.query(TournamentType).filter(TournamentType.code == "league").first()
tt_gk = db.query(TournamentType).filter(TournamentType.code == "group_knockout").first()
tt_swiss = db.query(TournamentType).filter(TournamentType.code == "swiss").first()
if not tt_league or not tt_gk or not tt_swiss:
    print("❌ TournamentType rows missing — run bootstrap_clean.py first")
    sys.exit(1)

app.dependency_overrides[get_current_user_web] = lambda: admin
app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin
app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = lambda: admin

client = TestClient(app, follow_redirects=False)


def ok(msg):   print(f"  ✅  {msg}")
def info(msg): print(f"       {msg}")
def err(msg):  print(f"  ❌  {msg}")


def _uid():
    return uuid.uuid4().hex[:6]


# ── Shared reward config ────────────────────────────────────────────────────
_REWARD_CONFIG = {
    "skill_mappings": [
        {"skill": "ball_control",  "weight": 1.2, "category": "TECHNICAL", "enabled": True},
        {"skill": "passing",       "weight": 1.0, "category": "TECHNICAL", "enabled": True},
        {"skill": "finishing",     "weight": 1.2, "category": "TECHNICAL", "enabled": True},
        {"skill": "dribbling",     "weight": 1.0, "category": "TECHNICAL", "enabled": True},
        {"skill": "sprint_speed",  "weight": 1.1, "category": "PHYSICAL",  "enabled": True},
        {"skill": "stamina",       "weight": 1.0, "category": "PHYSICAL",  "enabled": True},
        {"skill": "composure",     "weight": 1.0, "category": "MENTAL",    "enabled": True},
        {"skill": "reactions",     "weight": 1.1, "category": "MENTAL",    "enabled": True},
    ],
}


# ── Tournament factory ──────────────────────────────────────────────────────
def create_tournament(name: str, tt_id: int, participant_type: str,
                      scoring_type: str = "SCORE_BASED",
                      ranking_direction: str = "DESC",
                      status: str = "DRAFT") -> Semester:
    t = Semester(
        name=name,
        code=f"SEED-{_uid()}",
        master_instructor_id=instructor.id,
        campus_id=campus.id,
        location_id=campus.location_id,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 3),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status=status,
    )
    db.add(t)
    db.flush()
    db.add(TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=tt_id,
        participant_type=participant_type,
        max_players=64,
        number_of_rounds=1,
        parallel_fields=1,
        ranking_direction=ranking_direction,
        scoring_type=scoring_type,
    ))
    db.add(GameConfiguration(semester_id=t.id, game_preset_id=preset.id))
    db.add(TournamentRewardConfig(
        semester_id=t.id,
        reward_policy_name="Seed Default",
        reward_config=_REWARD_CONFIG,
    ))
    db.commit()
    db.expire_all()
    ok(f"Created '{t.name}'  id={t.id}  status={t.tournament_status}")
    return t


def enroll_teams(tid: int) -> list[Team]:
    """Enroll all 3 bootstrap teams into a TEAM-type tournament."""
    db.expire_all()
    enrolled = []
    for team in boot_teams:
        existing = db.query(TournamentTeamEnrollment).filter(
            TournamentTeamEnrollment.semester_id == tid,
            TournamentTeamEnrollment.team_id == team.id,
        ).first()
        if not existing:
            db.add(TournamentTeamEnrollment(
                semester_id=tid,
                team_id=team.id,
                is_active=True,
                payment_verified=True,
            ))
        enrolled.append(team)
    db.commit()
    info(f"Enrolled {len(enrolled)} teams")
    return enrolled


def enroll_individual_players(tid: int) -> list[User]:
    """Enroll all 36 bootstrap players individually."""
    db.expire_all()
    from app.models.license import UserLicense
    enrolled = []
    for u in all_boot_players:
        lic = db.query(UserLicense).filter(
            UserLicense.user_id == u.id,
            UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
            UserLicense.is_active == True,
        ).first()
        if not lic:
            continue
        existing = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tid,
            SemesterEnrollment.user_id == u.id,
        ).first()
        if not existing:
            db.add(SemesterEnrollment(
                semester_id=tid,
                user_id=u.id,
                user_license_id=lic.id,
                is_active=True,
                request_status=EnrollmentStatus.APPROVED,
            ))
        enrolled.append(u)
    db.commit()
    info(f"Enrolled {len(enrolled)} individual players")
    return enrolled


def transition(tid: int, new_status: str) -> bool:
    r = client.patch(
        f"/api/v1/tournaments/{tid}/status",
        json={"new_status": new_status, "reason": "seed"},
    )
    if r.status_code != 200:
        err(f"Transition {tid} → {new_status} failed: {r.status_code} {r.text[:200]}")
        return False
    db.expire_all()
    ok(f"→ {new_status}")
    return True


def submit_team_results(tid: int, teams: list[Team]) -> int:
    """Submit head-to-head team results for all sessions."""
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
    submitted = 0
    for sess in sessions:
        enrolled_team_ids = list(sess.participant_team_ids or [])
        if len(enrolled_team_ids) < 2:
            continue
        results = [{"team_id": tid, "score": 3 - i} for i, tid in enumerate(enrolled_team_ids[:2])]
        r = client.patch(
            f"/api/v1/sessions/{sess.id}/team-results",
            json={"results": results, "round_number": 1},
        )
        if r.status_code in (200, 201):
            submitted += 1
        else:
            err(f"Team result session {sess.id}: {r.status_code} {r.text[:120]}")
    info(f"Results submitted: {submitted} session(s)")
    return submitted


def submit_individual_results(tid: int, players: list[User]) -> int:
    """Submit individual score results for all sessions."""
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
    submitted = 0
    for sess in sessions:
        results = [
            {"user_id": p.id, "score": float(100 - i * 2), "rank": i + 1}
            for i, p in enumerate(players)
        ]
        r = client.patch(
            f"/api/v1/sessions/{sess.id}/results",
            json={"results": results},
        )
        if r.status_code in (200, 201):
            submitted += 1
        else:
            err(f"Individual result session {sess.id}: {r.status_code} {r.text[:120]}")
    info(f"Results submitted: {submitted} session(s)")
    return submitted


def write_gk_game_results(tid: int) -> int:
    """Write game_results directly to GROUP_STAGE sessions for GROUP_KNOCKOUT ranking.

    The calculate-rankings endpoint reads game_results (not rounds_data) for
    group_knockout format.  This helper writes the expected format directly
    rather than going through the individual results API.
    """
    import json as _json
    db.expire_all()
    sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tid,
        SessionModel.tournament_phase == "GROUP_STAGE",
    ).all()
    written = 0
    for sess in sessions:
        pids = list(sess.participant_user_ids or [])
        if len(pids) < 2:
            continue
        p1, p2 = pids[0], pids[1]
        data = {
            "match_format": "HEAD_TO_HEAD",
            "participants": [
                {"user_id": p1, "score": 3.0, "result": "win"},
                {"user_id": p2, "score": 1.0, "result": "loss"},
            ],
        }
        sess.game_results = _json.dumps(data)
        sess.session_status = "completed"
        written += 1
    db.commit()
    info(f"GK group results written: {written} session(s)")
    return written


def seed_individual_rankings(tid: int, players: list[User]) -> int:
    """Write TournamentRanking rows directly for formats without API ranking support (Swiss)."""
    db.expire_all()
    # Delete existing rankings first
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == tid).delete()
    db.commit()
    for i, p in enumerate(players):
        db.add(TournamentRanking(
            tournament_id=tid,
            user_id=p.id,
            participant_type="INDIVIDUAL",
            rank=i + 1,
            points=float(max(0, 100 - i * 2)),
        ))
    db.commit()
    ok(f"Rankings seeded: {len(players)} player(s)")
    return len(players)


def calculate_rankings(tid: int) -> bool:
    r = client.post(f"/api/v1/tournaments/{tid}/calculate-rankings", json={})
    if r.status_code == 200:
        ok("Rankings calculated")
        return True
    err(f"Rankings failed: {r.status_code} {r.text[:150]}")
    return False


def distribute_rewards(tid: int) -> bool:
    r = client.post(
        f"/api/v1/tournaments/{tid}/distribute-rewards-v2",
        json={"tournament_id": tid, "force_redistribution": False},
    )
    if r.status_code == 200:
        db.expire_all()
        final = db.query(Semester).filter(Semester.id == tid).first()
        ok(f"Rewards distributed → status: {final.tournament_status}")
        return True
    err(f"Rewards failed: {r.status_code} {r.text[:150]}")
    return False


# ── Cleanup ────────────────────────────────────────────────────────────────
from sqlalchemy import text as _sql

_SEED_PATTERNS = ["H2H League —", "Group Knockout —", "Swiss Cup —"]
_existing_ids = []
for pattern in _SEED_PATTERNS:
    rows = db.execute(
        _sql(f"SELECT id FROM semesters WHERE name LIKE '{pattern}%'")
    ).fetchall()
    _existing_ids.extend(r[0] for r in rows)

if _existing_ids:
    print(f"\n🧹 Deleting {len(_existing_ids)} existing team seed tournament(s)...")
    id_list = ", ".join(str(i) for i in _existing_ids)
    for tbl in [
        "tournament_reward_configs", "tournament_skill_mappings", "tournament_configurations",
        "game_configurations", "semester_enrollments", "tournament_team_enrollments",
        "tournament_player_checkins", "tournament_rankings", "tournament_participations",
        "tournament_reward_distributions", "tournament_instructor_slots", "sessions",
    ]:
        try:
            db.execute(_sql(f"DELETE FROM {tbl} WHERE semester_id IN ({id_list})"))
        except Exception:
            db.rollback()
    try:
        db.execute(_sql(f"DELETE FROM tournament_status_history WHERE tournament_id IN ({id_list})"))
    except Exception:
        db.rollback()
    try:
        db.execute(_sql(f"DELETE FROM notifications WHERE related_semester_id IN ({id_list})"))
    except Exception:
        db.rollback()
    db.execute(_sql(f"DELETE FROM semesters WHERE id IN ({id_list})"))
    db.commit()
    print("   Done.")


# ══════════════════════════════════════════════════════════════════════════
# ── FORMAT A: H2H LEAGUE (TEAM participant_type) ──────────────────────────
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  H2H LEAGUE — TEAM — 8 LIFECYCLE STATES")
print("="*60)

print("\n[A1/8] DRAFT")
t = create_tournament("H2H League — Draft 2026", tt_league.id, "TEAM")

print("\n[A2/8] ENROLLMENT_OPEN")
t = create_tournament("H2H League — Enrollment Open 2026", tt_league.id, "TEAM")
enroll_teams(t.id)
transition(t.id, "ENROLLMENT_OPEN")

print("\n[A3/8] ENROLLMENT_CLOSED")
t = create_tournament("H2H League — Enrollment Closed 2026", tt_league.id, "TEAM")
enroll_teams(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")

print("\n[A4/8] CHECK_IN_OPEN")
t = create_tournament("H2H League — Check-In Open 2026", tt_league.id, "TEAM")
enroll_teams(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
db.expire_all()
info(f"Sessions auto-generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")

print("\n[A5/8] IN_PROGRESS")
t = create_tournament("H2H League — In Progress 2026", tt_league.id, "TEAM")
teams = enroll_teams(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    info("No results submitted — tournament stays live")

print("\n[A6/8] COMPLETED")
t = create_tournament("H2H League — Completed 2026", tt_league.id, "TEAM")
teams = enroll_teams(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_team_results(t.id, teams)
    calculate_rankings(t.id)
    transition(t.id, "COMPLETED")

print("\n[A7/8] REWARDS_DISTRIBUTED")
t = create_tournament("H2H League — Rewards Distributed 2026", tt_league.id, "TEAM")
teams = enroll_teams(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_team_results(t.id, teams)
    calculate_rankings(t.id)
    if transition(t.id, "COMPLETED"):
        distribute_rewards(t.id)

print("\n[A8/8] CANCELLED")
t = create_tournament("H2H League — Cancelled 2026", tt_league.id, "TEAM")
transition(t.id, "CANCELLED")


# ══════════════════════════════════════════════════════════════════════════
# ── FORMAT B: GROUP KNOCKOUT (INDIVIDUAL, 36 players) ─────────────────────
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  GROUP KNOCKOUT — INDIVIDUAL — 8 LIFECYCLE STATES")
print("="*60)

print("\n[B1/8] DRAFT")
t = create_tournament("Group Knockout — Draft 2026", tt_gk.id, "INDIVIDUAL")

print("\n[B2/8] ENROLLMENT_OPEN")
t = create_tournament("Group Knockout — Enrollment Open 2026", tt_gk.id, "INDIVIDUAL")
enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")

print("\n[B3/8] ENROLLMENT_CLOSED")
t = create_tournament("Group Knockout — Enrollment Closed 2026", tt_gk.id, "INDIVIDUAL")
enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")

print("\n[B4/8] CHECK_IN_OPEN")
t = create_tournament("Group Knockout — Check-In Open 2026", tt_gk.id, "INDIVIDUAL")
enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
db.expire_all()
info(f"Sessions auto-generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")

print("\n[B5/8] IN_PROGRESS")
t = create_tournament("Group Knockout — In Progress 2026", tt_gk.id, "INDIVIDUAL")
players = enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    info("No results submitted — tournament stays live")

print("\n[B6/8] COMPLETED")
t = create_tournament("Group Knockout — Completed 2026", tt_gk.id, "INDIVIDUAL")
players = enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    write_gk_game_results(t.id)
    calculate_rankings(t.id)
    transition(t.id, "COMPLETED")

print("\n[B7/8] REWARDS_DISTRIBUTED")
t = create_tournament("Group Knockout — Rewards Distributed 2026", tt_gk.id, "INDIVIDUAL")
players = enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    write_gk_game_results(t.id)
    calculate_rankings(t.id)
    if transition(t.id, "COMPLETED"):
        distribute_rewards(t.id)

print("\n[B8/8] CANCELLED")
t = create_tournament("Group Knockout — Cancelled 2026", tt_gk.id, "INDIVIDUAL")
transition(t.id, "CANCELLED")


# ══════════════════════════════════════════════════════════════════════════
# ── FORMAT C: SWISS (INDIVIDUAL, 36 players) ──────────────────────────────
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  SWISS CUP — INDIVIDUAL — 8 LIFECYCLE STATES")
print("="*60)

print("\n[C1/8] DRAFT")
t = create_tournament("Swiss Cup — Draft 2026", tt_swiss.id, "INDIVIDUAL")

print("\n[C2/8] ENROLLMENT_OPEN")
t = create_tournament("Swiss Cup — Enrollment Open 2026", tt_swiss.id, "INDIVIDUAL")
enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")

print("\n[C3/8] ENROLLMENT_CLOSED")
t = create_tournament("Swiss Cup — Enrollment Closed 2026", tt_swiss.id, "INDIVIDUAL")
enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")

print("\n[C4/8] CHECK_IN_OPEN")
t = create_tournament("Swiss Cup — Check-In Open 2026", tt_swiss.id, "INDIVIDUAL")
enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
db.expire_all()
info(f"Sessions auto-generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")

print("\n[C5/8] IN_PROGRESS")
t = create_tournament("Swiss Cup — In Progress 2026", tt_swiss.id, "INDIVIDUAL")
players = enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    info("No results submitted — tournament stays live")

print("\n[C6/8] COMPLETED")
t = create_tournament("Swiss Cup — Completed 2026", tt_swiss.id, "INDIVIDUAL")
players = enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_individual_results(t.id, players)
    seed_individual_rankings(t.id, players)   # Swiss: no API ranking strategy
    transition(t.id, "COMPLETED")

print("\n[C7/8] REWARDS_DISTRIBUTED")
t = create_tournament("Swiss Cup — Rewards Distributed 2026", tt_swiss.id, "INDIVIDUAL")
players = enroll_individual_players(t.id)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions generated: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_individual_results(t.id, players)
    seed_individual_rankings(t.id, players)   # Swiss: no API ranking strategy
    if transition(t.id, "COMPLETED"):
        distribute_rewards(t.id)

print("\n[C8/8] CANCELLED")
t = create_tournament("Swiss Cup — Cancelled 2026", tt_swiss.id, "INDIVIDUAL")
transition(t.id, "CANCELLED")


# ── Summary ────────────────────────────────────────────────────────────────
db.expire_all()
print("\n" + "="*60)
print("  FINAL SUMMARY — TEAM FORMAT LIFECYCLE STATES")
print("="*60)
for pattern in _SEED_PATTERNS:
    rows = db.query(Semester).filter(Semester.name.like(f"{pattern}%")).order_by(Semester.id).all()
    print(f"\n  {pattern.strip()}")
    for row in rows:
        sessions = db.query(SessionModel).filter(SessionModel.semester_id == row.id).count()
        print(f"    id={row.id:4d}  {row.tournament_status:22s}  sessions={sessions}  {row.name}")

print()
print("  View: http://localhost:8000/admin/promotion-events")
print("="*60)
