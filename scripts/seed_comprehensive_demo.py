"""
Comprehensive Demo Seed
=======================
Creates one tournament for every format × lifecycle-state combination to
demonstrate the full ranking_type / standings_state logic on a clean database.

5 tournament types × 8 lifecycle states = 40 events

Formats
-------
  A  H2H League     (TEAM,       WDL_BASED,    4 demo teams)
  B  Knockout       (TEAM,       WDL_BASED,    4 demo teams)
  C  Group Knockout (INDIVIDUAL, WDL_BASED,   16 demo players)
  D  Swiss          (INDIVIDUAL, SCORING_ONLY, 16 demo players)
  E  IR (Ind. Rank) (INDIVIDUAL, SCORING_ONLY, 16 demo players)

Lifecycle states per format
---------------------------
  DRAFT  ENROLLMENT_OPEN  ENROLLMENT_CLOSED  CHECK_IN_OPEN
  IN_PROGRESS  COMPLETED  REWARDS_DISTRIBUTED  CANCELLED

Club created: LFA Demo Club (LFA-DEMO)
Teams:        Demo U12  Demo U15  Demo U18  Demo Adult  (4 players each)

Idempotent: deletes all existing "Demo:" named tournaments before re-seeding.

Prerequisites
-------------
    PYTHONPATH=. python scripts/bootstrap_clean.py   # run once first

Usage
-----
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \\
        SECRET_KEY="..." PYTHONPATH=. python scripts/seed_comprehensive_demo.py
"""
import os
import sys
import uuid
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
os.environ.setdefault("SECRET_KEY", "e2e-test-secret-key-minimum-32-chars-needed")

from fastapi.testclient import TestClient
from sqlalchemy import text as _sql

from app.main import app
from app.database import SessionLocal
from app.core.security import get_password_hash
from app.models.campus import Campus
from app.models.club import Club
from app.models.game_configuration import GameConfiguration
from app.models.game_preset import GamePreset
from app.models.license import UserLicense
from app.models.semester import Semester, SemesterCategory, SemesterStatus
from app.models.semester_enrollment import EnrollmentStatus, SemesterEnrollment
from app.models.session import Session as SessionModel
from app.models.team import Team, TeamMember, TournamentTeamEnrollment
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_reward_config import TournamentRewardConfig
from app.models.tournament_type import TournamentType
from app.models.user import User, UserRole
from app.skills_config import get_all_skill_keys
from app.dependencies import (
    get_current_admin_or_instructor_user_hybrid,
    get_current_admin_user_hybrid,
    get_current_user_web,
)

# ─────────────────────────────────────────────────────────────────────────────
# Output helpers
# ─────────────────────────────────────────────────────────────────────────────

def ok(msg):   print(f"  ✅  {msg}")
def info(msg): print(f"       {msg}")
def err(msg):  print(f"  ❌  {msg}")
def section(title): print(f"\n{'='*64}\n  {title}\n{'='*64}")


# ─────────────────────────────────────────────────────────────────────────────
# Demo club definition
# ─────────────────────────────────────────────────────────────────────────────

_DEMO_CLUB_CODE = "LFA-DEMO"
_DEMO_CLUB_NAME = "LFA Demo Club"

_DEMO_TEAMS = [
    {"name": "Demo U12", "age_group_label": "U12", "skill_base": 55.0,
     "dob": date(2013, 6, 1)},
    {"name": "Demo U15", "age_group_label": "U15", "skill_base": 62.0,
     "dob": date(2010, 6, 1)},
    {"name": "Demo U18", "age_group_label": "U18", "skill_base": 68.0,
     "dob": date(2007, 6, 1)},
    {"name": "Demo Adult", "age_group_label": "ADULT", "skill_base": 73.0,
     "dob": date(1995, 6, 1)},
]

# 4 players per team — unique names per age group
_DEMO_PLAYERS: dict[str, list[tuple[str, str]]] = {
    "Demo U12":    [("Aaron", "Adams"), ("Billy", "Baker"), ("Charlie", "Cole"), ("David", "Dean")],
    "Demo U15":    [("Eddie", "Evans"), ("Frank", "Ford"), ("George", "Grant"), ("Henry", "Hall")],
    "Demo U18":    [("Isaac", "Irving"), ("Jack", "Jones"), ("Kevin", "King"), ("Leo", "Lee")],
    "Demo Adult":  [("Mike", "Marsh"), ("Neil", "Nash"), ("Oscar", "Owen"), ("Peter", "Price")],
}

# ─────────────────────────────────────────────────────────────────────────────
# Reward config shared across all demo tournaments
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# DB + auth setup
# ─────────────────────────────────────────────────────────────────────────────

db = SessionLocal()

admin = db.query(User).filter(User.email == "admin@lfa.com").first()
instructor = db.query(User).filter(User.email == "instructor@lfa.com").first()
if not admin or not instructor:
    print("❌  admin@lfa.com or instructor@lfa.com not found — run bootstrap_clean.py first")
    sys.exit(1)

campus = db.query(Campus).first()
if not campus:
    print("❌  No campus found — run bootstrap_clean.py first")
    sys.exit(1)

preset = db.query(GamePreset).filter(GamePreset.code == "outfield_default").first() or \
         db.query(GamePreset).first()
if not preset:
    print("❌  No GamePreset found — run bootstrap_clean.py first")
    sys.exit(1)

# TournamentType lookups
tt_league   = db.query(TournamentType).filter(TournamentType.code == "league").first()
tt_knockout = db.query(TournamentType).filter(TournamentType.code == "knockout").first()
tt_gk       = db.query(TournamentType).filter(TournamentType.code == "group_knockout").first()
tt_swiss    = db.query(TournamentType).filter(TournamentType.code == "swiss").first()
if not all([tt_league, tt_knockout, tt_gk, tt_swiss]):
    print("❌  TournamentType rows missing — run bootstrap_clean.py first")
    sys.exit(1)

app.dependency_overrides[get_current_user_web] = lambda: admin
app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin
app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = lambda: admin

client = TestClient(app, follow_redirects=False)


# ─────────────────────────────────────────────────────────────────────────────
# Cleanup: delete all existing "Demo:" prefixed tournaments
# ─────────────────────────────────────────────────────────────────────────────

section("Cleanup — removing existing Demo: tournaments")

_existing_ids = [
    row[0] for row in db.execute(
        _sql("SELECT id FROM semesters WHERE name LIKE 'Demo: %'")
    ).fetchall()
]
if _existing_ids:
    print(f"  🧹  Found {len(_existing_ids)} existing Demo tournament(s) — deleting...")
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
    ok(f"Deleted {len(_existing_ids)} tournament(s)")
else:
    ok("No existing Demo tournaments found")


# ─────────────────────────────────────────────────────────────────────────────
# Create Demo Club + 4 teams × 4 players
# ─────────────────────────────────────────────────────────────────────────────

section("Demo Club — LFA Demo Club (4 teams × 4 players)")

all_skill_keys = get_all_skill_keys()
now = datetime.now()

demo_club = db.query(Club).filter(Club.code == _DEMO_CLUB_CODE).first()
if demo_club:
    ok(f"Club '{_DEMO_CLUB_NAME}' already exists (id={demo_club.id})")
else:
    demo_club = Club(
        name=_DEMO_CLUB_NAME,
        code=_DEMO_CLUB_CODE,
        city="Budapest",
        country="HU",
        contact_email="demo@lfa.com",
        is_active=True,
    )
    db.add(demo_club)
    db.flush()
    ok(f"Club '{_DEMO_CLUB_NAME}' created (id={demo_club.id})")

demo_teams: list[Team] = []
all_demo_players: list[User] = []

for tdef in _DEMO_TEAMS:
    team = db.query(Team).filter(
        Team.club_id == demo_club.id,
        Team.name == tdef["name"],
    ).first()
    if not team:
        team = Team(
            name=tdef["name"],
            club_id=demo_club.id,
            age_group_label=tdef["age_group_label"],
            is_active=True,
        )
        db.add(team)
        db.flush()
        ok(f"  Team '{tdef['name']}' created (id={team.id})")
    else:
        ok(f"  Team '{tdef['name']}' already exists (id={team.id})")

    demo_teams.append(team)
    football_skills = {k: tdef["skill_base"] for k in all_skill_keys}
    age_slug = tdef["age_group_label"].lower()

    for idx, (first, last) in enumerate(_DEMO_PLAYERS[tdef["name"]]):
        email = f"demo-{age_slug}-{first.lower()}.{last.lower()}@lfa.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name=f"{first} {last}",
                first_name=first,
                last_name=last,
                nickname=first,
                email=email,
                password_hash=get_password_hash("Demo#1234"),
                role=UserRole.STUDENT,
                is_active=True,
                onboarding_completed=True,
                credit_balance=500,
                date_of_birth=tdef["dob"],
                nationality="British",
                gender="Male",
                phone=f"+44 7700 8{idx:05d}",
                street_address="2 Demo Lane",
                city="London",
                postal_code="EC2A 2BB",
                country="United Kingdom",
            )
            db.add(user)
            db.flush()

            lic = UserLicense(
                user_id=user.id,
                specialization_type="LFA_FOOTBALL_PLAYER",
                current_level=1,
                max_achieved_level=1,
                started_at=now,
                payment_verified=True,
                payment_verified_at=now,
                onboarding_completed=True,
                onboarding_completed_at=now,
                is_active=True,
                football_skills=football_skills,
                motivation_scores={
                    "position": "MIDFIELDER",
                    "goals": "improve_skills",
                    "motivation": "",
                    "average_skill_level": tdef["skill_base"],
                    "onboarding_completed_at": now.isoformat(),
                },
                average_motivation_score=tdef["skill_base"],
            )
            db.add(lic)
            db.flush()

        member = db.query(TeamMember).filter(
            TeamMember.team_id == team.id,
            TeamMember.user_id == user.id,
        ).first()
        if not member:
            db.add(TeamMember(team_id=team.id, user_id=user.id, role="PLAYER", is_active=True))
            db.flush()

        all_demo_players.append(user)

db.commit()
db.expire_all()

# Reload team objects + all players (in case they already existed)
demo_teams = [
    db.query(Team).filter(Team.club_id == demo_club.id, Team.name == tdef["name"]).first()
    for tdef in _DEMO_TEAMS
]
all_demo_players = (
    db.query(User)
    .join(TeamMember, TeamMember.user_id == User.id)
    .filter(TeamMember.team_id.in_([t.id for t in demo_teams]))
    .all()
)
print(f"  → Demo teams: {[t.name for t in demo_teams]}")
print(f"  → Demo players: {len(all_demo_players)} total")


# ─────────────────────────────────────────────────────────────────────────────
# Shared tournament factory + lifecycle helpers
# ─────────────────────────────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex[:6]


def create_tournament(
    name: str,
    tt_id: int | None,
    participant_type: str,
    scoring_type: str = "SCORE_BASED",
    ranking_direction: str = "DESC",
) -> Semester:
    """Create a DRAFT tournament with all required related rows."""
    t = Semester(
        name=name,
        code=f"DEMO-{_uid()}",
        master_instructor_id=instructor.id,
        campus_id=campus.id,
        location_id=campus.location_id,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 3),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status="DRAFT",
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
        reward_policy_name="Demo Default",
        reward_config=_REWARD_CONFIG,
    ))
    db.commit()
    db.expire_all()
    ok(f"Created '{t.name}'  id={t.id}")
    return t


def enroll_teams(tid: int, teams: list[Team]) -> list[Team]:
    """Enroll demo teams (TEAM participant_type)."""
    db.expire_all()
    enrolled = []
    for team in teams:
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


def enroll_individual_players(tid: int, players: list[User]) -> list[User]:
    """Enroll demo players individually."""
    db.expire_all()
    enrolled = []
    for u in players:
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
        json={"new_status": new_status, "reason": "demo-seed"},
    )
    if r.status_code != 200:
        err(f"Transition {tid} → {new_status} failed: {r.status_code} {r.text[:200]}")
        return False
    db.expire_all()
    ok(f"→ {new_status}")
    return True


def _reach(tid: int, target: str, teams: list[Team] | None = None,
           players: list[User] | None = None) -> bool:
    """Advance from DRAFT to the given target state, enrolling as needed."""
    chain = [
        ("ENROLLMENT_OPEN",   lambda: teams and enroll_teams(tid, teams)
                                      or players and enroll_individual_players(tid, players)),
        ("ENROLLMENT_CLOSED", None),
        ("CHECK_IN_OPEN",     None),
        ("IN_PROGRESS",       None),
    ]
    for status, prep in chain:
        if prep:
            prep()
        if not transition(tid, status):
            return False
        if status == target:
            db.expire_all()
            n = db.query(SessionModel).filter(SessionModel.semester_id == tid).count()
            if n:
                info(f"Sessions generated: {n}")
            return True
    return True


def submit_team_results(tid: int) -> int:
    """Submit 1-0 H2H results for Round-1 sessions (participant_team_ids already set)."""
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
    submitted = 0
    for sess in sessions:
        pids = list(sess.participant_team_ids or [])
        if len(pids) < 2:
            continue
        r = client.patch(
            f"/api/v1/sessions/{sess.id}/team-results",
            json={
                "results": [
                    {"team_id": pids[0], "score": 2},
                    {"team_id": pids[1], "score": 0},
                ],
                "round_number": 1,
            },
        )
        if r.status_code in (200, 201):
            submitted += 1
        else:
            err(f"Team result session {sess.id}: {r.status_code} {r.text[:120]}")
    info(f"Team results submitted: {submitted} session(s)")
    return submitted


def submit_knockout_team_results(tid: int, teams: list[Team]) -> int:
    """Submit knockout results: Round 1 via API, then manually seed Round 2."""
    db.expire_all()
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.semester_id == tid)
        .order_by(SessionModel.id)
        .all()
    )

    # Round 1: sessions that already have participant_team_ids
    r1 = [s for s in sessions if s.participant_team_ids and len(s.participant_team_ids) >= 2]
    winners: list[int] = []
    for sess in r1:
        pids = list(sess.participant_team_ids)
        winner_id, loser_id = pids[0], pids[1]
        winners.append(winner_id)
        r = client.patch(
            f"/api/v1/sessions/{sess.id}/team-results",
            json={
                "results": [
                    {"team_id": winner_id, "score": 2},
                    {"team_id": loser_id,  "score": 0},
                ],
                "round_number": 1,
            },
        )
        if r.status_code not in (200, 201):
            err(f"Knockout R1 session {sess.id}: {r.status_code} {r.text[:120]}")

    # Round 2+: fill participant_team_ids with winners and submit
    r2_plus = [s for s in sessions if not s.participant_team_ids or len(s.participant_team_ids) < 2]
    submitted = len(r1)
    for i, sess in enumerate(r2_plus):
        w_pair = winners[i * 2: i * 2 + 2] if len(winners) >= i * 2 + 2 else winners[-2:]
        if len(w_pair) < 2:
            break
        sess.participant_team_ids = w_pair
        db.commit()
        db.expire_all()
        r = client.patch(
            f"/api/v1/sessions/{sess.id}/team-results",
            json={
                "results": [
                    {"team_id": w_pair[0], "score": 1},
                    {"team_id": w_pair[1], "score": 0},
                ],
                "round_number": 1,
            },
        )
        if r.status_code in (200, 201):
            submitted += 1
        else:
            err(f"Knockout R2 session {sess.id}: {r.status_code} {r.text[:120]}")
        winners = [w_pair[0]]   # winner advances

    info(f"Knockout results submitted: {submitted} session(s) "
         f"(R1={len(r1)}, R2+={len(r2_plus)})")
    return submitted


def write_gk_game_results(tid: int) -> int:
    """Write game_results directly to GROUP_STAGE sessions for Group Knockout."""
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
        data = {
            "match_format": "HEAD_TO_HEAD",
            "participants": [
                {"user_id": pids[0], "score": 3.0, "result": "win"},
                {"user_id": pids[1], "score": 0.0, "result": "loss"},
            ],
        }
        sess.game_results = _json.dumps(data)
        sess.session_status = "completed"
        written += 1
    db.commit()
    info(f"GK group results written: {written} session(s)")
    return written


def submit_individual_results(tid: int, players: list[User]) -> int:
    """Submit individual score results for all sessions (Swiss / IR)."""
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
    submitted = 0
    for sess in sessions:
        results = [
            {"user_id": p.id, "score": float(100 - i * 5), "rank": i + 1}
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
    info(f"Individual results submitted: {submitted} session(s)")
    return submitted


def seed_individual_rankings(tid: int, players: list[User]) -> int:
    """Directly write TournamentRanking rows (used for Swiss — no API strategy)."""
    db.expire_all()
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == tid).delete()
    db.commit()
    for i, p in enumerate(players):
        db.add(TournamentRanking(
            tournament_id=tid,
            user_id=p.id,
            participant_type="INDIVIDUAL",
            rank=i + 1,
            points=float(max(0, 100 - i * 5)),
        ))
    db.commit()
    ok(f"Swiss rankings seeded: {len(players)} player(s)")
    return len(players)


def seed_team_rankings(tid: int, teams: list[Team]) -> int:
    """Directly write TournamentRanking rows for TEAM format (fallback)."""
    db.expire_all()
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == tid).delete()
    db.commit()
    for i, team in enumerate(teams):
        db.add(TournamentRanking(
            tournament_id=tid,
            team_id=team.id,
            participant_type="TEAM",
            rank=i + 1,
            points=float(max(0, 10 - i * 3)),
            wins=max(0, 3 - i),
            losses=i,
            draws=0,
        ))
    db.commit()
    ok(f"Team rankings seeded directly: {len(teams)} team(s)")
    return len(teams)


def calculate_rankings(tid: int) -> bool:
    r = client.post(f"/api/v1/tournaments/{tid}/calculate-rankings", json={})
    if r.status_code == 200:
        ok("Rankings calculated via API")
        return True
    err(f"Rankings API failed ({r.status_code}): {r.text[:150]}")
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


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT A — H2H LEAGUE (TEAM, WDL_BASED)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT A — H2H League (TEAM, WDL_BASED) — 8 states")

def _league(label: str) -> Semester:
    return create_tournament(
        f"Demo: H2H League — {label}",
        tt_id=tt_league.id,
        participant_type="TEAM",
        scoring_type="SCORE_BASED",
        ranking_direction="DESC",
    )

print("\n[A1/8] DRAFT")
_league("Draft")

print("\n[A2/8] ENROLLMENT_OPEN")
t = _league("Enrollment Open")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")

print("\n[A3/8] ENROLLMENT_CLOSED")
t = _league("Enrollment Closed")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")

print("\n[A4/8] CHECK_IN_OPEN")
t = _league("Check-In Open")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
db.expire_all()
info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")

print("\n[A5/8] IN_PROGRESS")
t = _league("In Progress")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    info("No results submitted — standings_state=NONE")

print("\n[A6/8] COMPLETED")
t = _league("Completed")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_team_results(t.id)
    if not calculate_rankings(t.id):
        seed_team_rankings(t.id, demo_teams)
    transition(t.id, "COMPLETED")

print("\n[A7/8] REWARDS_DISTRIBUTED")
t = _league("Rewards Distributed")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_team_results(t.id)
    if not calculate_rankings(t.id):
        seed_team_rankings(t.id, demo_teams)
    if transition(t.id, "COMPLETED"):
        distribute_rewards(t.id)

print("\n[A8/8] CANCELLED")
t = _league("Cancelled")
transition(t.id, "CANCELLED")


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT B — KNOCKOUT (TEAM, WDL_BASED)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT B — Knockout (TEAM, WDL_BASED) — 8 states")

def _knockout(label: str) -> Semester:
    return create_tournament(
        f"Demo: Knockout — {label}",
        tt_id=tt_knockout.id,
        participant_type="TEAM",
        scoring_type="SCORE_BASED",
        ranking_direction="DESC",
    )

print("\n[B1/8] DRAFT")
_knockout("Draft")

print("\n[B2/8] ENROLLMENT_OPEN")
t = _knockout("Enrollment Open")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")

print("\n[B3/8] ENROLLMENT_CLOSED")
t = _knockout("Enrollment Closed")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")

print("\n[B4/8] CHECK_IN_OPEN")
t = _knockout("Check-In Open")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
db.expire_all()
info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")

print("\n[B5/8] IN_PROGRESS")
t = _knockout("In Progress")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    info("No results — standings_state=NONE")

print("\n[B6/8] COMPLETED")
t = _knockout("Completed")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_knockout_team_results(t.id, demo_teams)
    if not calculate_rankings(t.id):
        seed_team_rankings(t.id, demo_teams)
    transition(t.id, "COMPLETED")

print("\n[B7/8] REWARDS_DISTRIBUTED")
t = _knockout("Rewards Distributed")
enroll_teams(t.id, demo_teams)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_knockout_team_results(t.id, demo_teams)
    if not calculate_rankings(t.id):
        seed_team_rankings(t.id, demo_teams)
    if transition(t.id, "COMPLETED"):
        distribute_rewards(t.id)

print("\n[B8/8] CANCELLED")
t = _knockout("Cancelled")
transition(t.id, "CANCELLED")


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT C — GROUP KNOCKOUT (INDIVIDUAL, WDL_BASED)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT C — Group Knockout (INDIVIDUAL, WDL_BASED) — 8 states")

def _gk(label: str) -> Semester:
    return create_tournament(
        f"Demo: Group Knockout — {label}",
        tt_id=tt_gk.id,
        participant_type="INDIVIDUAL",
        scoring_type="SCORE_BASED",
        ranking_direction="DESC",
    )

print("\n[C1/8] DRAFT")
_gk("Draft")

print("\n[C2/8] ENROLLMENT_OPEN")
t = _gk("Enrollment Open")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")

print("\n[C3/8] ENROLLMENT_CLOSED")
t = _gk("Enrollment Closed")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")

print("\n[C4/8] CHECK_IN_OPEN")
t = _gk("Check-In Open")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
db.expire_all()
info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")

print("\n[C5/8] IN_PROGRESS")
t = _gk("In Progress")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    info("No results — standings_state=NONE")

print("\n[C6/8] COMPLETED")
t = _gk("Completed")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    write_gk_game_results(t.id)
    if not calculate_rankings(t.id):
        seed_individual_rankings(t.id, all_demo_players)
    transition(t.id, "COMPLETED")

print("\n[C7/8] REWARDS_DISTRIBUTED")
t = _gk("Rewards Distributed")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    write_gk_game_results(t.id)
    if not calculate_rankings(t.id):
        seed_individual_rankings(t.id, all_demo_players)
    if transition(t.id, "COMPLETED"):
        distribute_rewards(t.id)

print("\n[C8/8] CANCELLED")
t = _gk("Cancelled")
transition(t.id, "CANCELLED")


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT D — SWISS (INDIVIDUAL, SCORING_ONLY)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT D — Swiss (INDIVIDUAL, SCORING_ONLY) — 8 states")

def _swiss(label: str) -> Semester:
    return create_tournament(
        f"Demo: Swiss — {label}",
        tt_id=tt_swiss.id,
        participant_type="INDIVIDUAL",
        scoring_type="SCORE_BASED",
        ranking_direction="DESC",
    )

print("\n[D1/8] DRAFT")
_swiss("Draft")

print("\n[D2/8] ENROLLMENT_OPEN")
t = _swiss("Enrollment Open")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")

print("\n[D3/8] ENROLLMENT_CLOSED")
t = _swiss("Enrollment Closed")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")

print("\n[D4/8] CHECK_IN_OPEN")
t = _swiss("Check-In Open")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
db.expire_all()
info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")

print("\n[D5/8] IN_PROGRESS")
t = _swiss("In Progress")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    info("No results — standings_state=NONE")

print("\n[D6/8] COMPLETED")
t = _swiss("Completed")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_individual_results(t.id, all_demo_players)
    seed_individual_rankings(t.id, all_demo_players)   # Swiss has no API ranking strategy
    transition(t.id, "COMPLETED")

print("\n[D7/8] REWARDS_DISTRIBUTED")
t = _swiss("Rewards Distributed")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_individual_results(t.id, all_demo_players)
    seed_individual_rankings(t.id, all_demo_players)
    if transition(t.id, "COMPLETED"):
        distribute_rewards(t.id)

print("\n[D8/8] CANCELLED")
t = _swiss("Cancelled")
transition(t.id, "CANCELLED")


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT E — INDIVIDUAL RANKING (INDIVIDUAL, SCORING_ONLY)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT E — Individual Ranking (INDIVIDUAL, SCORING_ONLY) — 8 states")

def _ir(label: str) -> Semester:
    # tournament_type_id=None → format resolved as INDIVIDUAL_RANKING
    return create_tournament(
        f"Demo: IR — {label}",
        tt_id=None,
        participant_type="INDIVIDUAL",
        scoring_type="SCORE_BASED",
        ranking_direction="DESC",
    )

print("\n[E1/8] DRAFT")
_ir("Draft")

print("\n[E2/8] ENROLLMENT_OPEN")
t = _ir("Enrollment Open")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")

print("\n[E3/8] ENROLLMENT_CLOSED")
t = _ir("Enrollment Closed")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")

print("\n[E4/8] CHECK_IN_OPEN")
t = _ir("Check-In Open")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
db.expire_all()
info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")

print("\n[E5/8] IN_PROGRESS")
t = _ir("In Progress")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    info("No results — standings_state=NONE")

print("\n[E6/8] COMPLETED")
t = _ir("Completed")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_individual_results(t.id, all_demo_players)
    calculate_rankings(t.id)
    transition(t.id, "COMPLETED")

print("\n[E7/8] REWARDS_DISTRIBUTED")
t = _ir("Rewards Distributed")
enroll_individual_players(t.id, all_demo_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()}")
    submit_individual_results(t.id, all_demo_players)
    calculate_rankings(t.id)
    if transition(t.id, "COMPLETED"):
        distribute_rewards(t.id)

print("\n[E8/8] CANCELLED")
t = _ir("Cancelled")
transition(t.id, "CANCELLED")


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

db.expire_all()
section("FINAL SUMMARY — 40 Demo Events")

_FORMATS = [
    ("A", "Demo: H2H League —",     "TEAM"),
    ("B", "Demo: Knockout —",       "TEAM"),
    ("C", "Demo: Group Knockout —", "INDIVIDUAL"),
    ("D", "Demo: Swiss —",          "INDIVIDUAL"),
    ("E", "Demo: IR —",             "INDIVIDUAL"),
]

total = 0
for fmt_id, prefix, pt in _FORMATS:
    rows = (
        db.query(Semester)
        .filter(Semester.name.like(f"{prefix}%"))
        .order_by(Semester.id)
        .all()
    )
    print(f"\n  [{fmt_id}] {prefix.strip()}")
    for row in rows:
        sessions = db.query(SessionModel).filter(SessionModel.semester_id == row.id).count()
        rankings = db.query(TournamentRanking).filter(TournamentRanking.tournament_id == row.id).count()
        print(
            f"    id={row.id:4d}  {row.tournament_status:22s}"
            f"  sessions={sessions:3d}  rankings={rankings:3d}  {row.name}"
        )
        total += 1

print(f"\n  Total events seeded: {total}")
print(f"  Demo Club:  {demo_club.name}  (id={demo_club.id})")
print(f"  Demo Teams: {[t.name for t in demo_teams]}")
print(f"  Demo Players: {len(all_demo_players)} total (4 per team)")
print()
print("  View events : http://localhost:8000/admin/promotion-events")
print("  Public page : http://localhost:8000/events/<id>")
print("="*64)

db.close()
