"""
REWARDS_DISTRIBUTED Showcase Seed
===================================
Creates exactly ONE tournament per format (A–K, 11 total), each driven all the
way to REWARDS_DISTRIBUTED state with a complete, consistent dataset.

Before seeding:  ALL existing tournament semesters are deleted.
After seeding:   ONLY 11 REWARDS_DISTRIBUTED events remain.

Formats
-------
  A  H2H League          (TEAM,       SCORE_BASED,   4 teams)
  B  Knockout            (TEAM,       SCORE_BASED,   4 teams)
  C  Group Knockout      (INDIVIDUAL, SCORE_BASED,  16 players)
  D  Swiss               (INDIVIDUAL, SCORE_BASED,  16 players)
  E  IR Score            (INDIVIDUAL, SCORE_BASED,  16 players)
  F  H2H League IND      (INDIVIDUAL, SCORE_BASED,  16 players)
  G  Knockout IND        (INDIVIDUAL, SCORE_BASED,  16 players)
  H  Group Knockout TEAM (TEAM,       SCORE_BASED,   8 teams)
  I  IR Team             (TEAM,       SCORE_BASED,   4 teams)
  J  IR Time-Based       (INDIVIDUAL, TIME_BASED,   16 players)
  K  IR Placement        (INDIVIDUAL, PLACEMENT,    16 players)

Prerequisites
-------------
    PYTHONPATH=. python scripts/bootstrap_clean.py   # run once first

Usage
-----
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \\
        SECRET_KEY="dev-secret-key" PYTHONPATH=. \\
        python scripts/seed_rewards_distributed_showcase.py
"""

import os
import sys
import json as _json
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

def ok(msg):      print(f"  ✅  {msg}")
def info(msg):    print(f"       {msg}")
def err(msg):     print(f"  ❌  {msg}")
def warn(msg):    print(f"  ⚠️   {msg}")
def section(t):   print(f"\n{'='*60}\n  {t}\n{'='*60}")


# ─────────────────────────────────────────────────────────────────────────────
# Demo club / team / player definitions  (same as seed_comprehensive_demo.py)
# ─────────────────────────────────────────────────────────────────────────────

_DEMO_CLUB_CODE = "LFA-DEMO"
_DEMO_CLUB_NAME = "LFA Demo Club"

_DEMO_TEAMS = [
    {"name": "Demo U12",   "age_group_label": "U12",   "skill_base": 55.0, "dob": date(2013, 6, 1)},
    {"name": "Demo U15",   "age_group_label": "U15",   "skill_base": 62.0, "dob": date(2010, 6, 1)},
    {"name": "Demo U18",   "age_group_label": "U18",   "skill_base": 68.0, "dob": date(2007, 6, 1)},
    {"name": "Demo Adult", "age_group_label": "ADULT", "skill_base": 73.0, "dob": date(1995, 6, 1)},
]

_GK_EXTRA_TEAMS = [
    {"name": "Demo GK-1", "age_group_label": "U12"},
    {"name": "Demo GK-2", "age_group_label": "U15"},
    {"name": "Demo GK-3", "age_group_label": "U18"},
    {"name": "Demo GK-4", "age_group_label": "ADULT"},
]

_DEMO_PLAYERS: dict[str, list[tuple[str, str]]] = {
    "Demo U12":   [("Aaron", "Adams"), ("Billy", "Baker"), ("Charlie", "Cole"), ("David", "Dean")],
    "Demo U15":   [("Eddie", "Evans"), ("Frank", "Ford"), ("George", "Grant"), ("Henry", "Hall")],
    "Demo U18":   [("Isaac", "Irving"), ("Jack", "Jones"), ("Kevin", "King"), ("Leo", "Lee")],
    "Demo Adult": [("Mike", "Marsh"), ("Neil", "Nash"), ("Oscar", "Owen"), ("Peter", "Price")],
}

_REWARD_CONFIG = {
    "skill_mappings": [
        {"skill": "ball_control", "weight": 1.2, "category": "TECHNICAL", "enabled": True},
        {"skill": "passing",      "weight": 1.0, "category": "TECHNICAL", "enabled": True},
        {"skill": "finishing",    "weight": 1.2, "category": "TECHNICAL", "enabled": True},
        {"skill": "dribbling",    "weight": 1.0, "category": "TECHNICAL", "enabled": True},
        {"skill": "sprint_speed", "weight": 1.1, "category": "PHYSICAL",  "enabled": True},
        {"skill": "stamina",      "weight": 1.0, "category": "PHYSICAL",  "enabled": True},
        {"skill": "composure",    "weight": 1.0, "category": "MENTAL",    "enabled": True},
        {"skill": "reactions",    "weight": 1.1, "category": "MENTAL",    "enabled": True},
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# DB + auth setup
# ─────────────────────────────────────────────────────────────────────────────

db = SessionLocal()

admin      = db.query(User).filter(User.email == "admin@lfa.com").first()
instructor = db.query(User).filter(User.email == "instructor@lfa.com").first()
if not admin or not instructor:
    print("❌  admin@lfa.com or instructor@lfa.com not found — run bootstrap_clean.py first")
    sys.exit(1)

campus = db.query(Campus).first()
if not campus:
    print("❌  No campus found — run bootstrap_clean.py first")
    sys.exit(1)

preset = (
    db.query(GamePreset).filter(GamePreset.code == "outfield_default").first()
    or db.query(GamePreset).first()
)
if not preset:
    print("❌  No GamePreset found — run bootstrap_clean.py first")
    sys.exit(1)

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
# CLEANUP — delete ALL existing tournament semesters
# ─────────────────────────────────────────────────────────────────────────────

section("CLEANUP — deleting ALL tournament semesters")

_all_t_ids = [
    row[0] for row in db.execute(
        _sql("SELECT id FROM semesters WHERE semester_category = 'TOURNAMENT'")
    ).fetchall()
]

if _all_t_ids:
    id_list = ", ".join(str(i) for i in _all_t_ids)
    print(f"  🧹  Found {len(_all_t_ids)} tournament semester(s) — deleting...")

    def _del(tbl: str, col: str) -> None:
        """Delete rows and commit; warn but continue on failure."""
        try:
            db.execute(_sql(f"DELETE FROM {tbl} WHERE {col} IN ({id_list})"))
            db.commit()
        except Exception as exc:
            db.rollback()
            warn(f"Could not clean {tbl}: {exc.__class__.__name__}: {str(exc)[:120]}")

    # Tables keyed by semester_id
    _del("notifications",             "related_semester_id")
    _del("tournament_reward_configs",  "semester_id")
    _del("tournament_skill_mappings",  "semester_id")
    _del("tournament_configurations",  "semester_id")
    _del("game_configurations",        "semester_id")
    _del("semester_enrollments",       "semester_id")
    _del("tournament_team_enrollments","semester_id")
    _del("tournament_instructor_slots","semester_id")
    _del("tournament_participations",  "semester_id")

    # Tables keyed by tournament_id (= semester.id)
    _del("tournament_player_checkins", "tournament_id")
    _del("tournament_rankings",        "tournament_id")
    _del("tournament_rewards",         "tournament_id")
    _del("tournament_status_history",  "tournament_id")

    # bookings references sessions.id — must go before sessions
    try:
        db.execute(_sql(
            f"DELETE FROM bookings WHERE session_id IN "
            f"(SELECT id FROM sessions WHERE semester_id IN ({id_list}))"
        ))
        db.commit()
    except Exception as exc:
        db.rollback()
        warn(f"Could not clean bookings: {exc.__class__.__name__}: {str(exc)[:120]}")

    # Sessions must go before semesters (FK)
    _del("sessions",                   "semester_id")

    # Finally remove the semesters themselves
    try:
        db.execute(_sql(f"DELETE FROM semesters WHERE id IN ({id_list})"))
        db.commit()
        ok(f"Deleted {len(_all_t_ids)} tournament semester(s)")
    except Exception as exc:
        db.rollback()
        err(f"Could not delete semesters: {exc}")
        sys.exit(1)
else:
    ok("No tournament semesters found — DB is clean")


# ─────────────────────────────────────────────────────────────────────────────
# Demo Club + teams + players  (idempotent)
# ─────────────────────────────────────────────────────────────────────────────

section("Demo Club — LFA Demo Club (4 teams × 4 players)")

all_skill_keys = get_all_skill_keys()
now = datetime.now()

demo_club = db.query(Club).filter(Club.code == _DEMO_CLUB_CODE).first()
if not demo_club:
    demo_club = Club(
        name=_DEMO_CLUB_NAME, code=_DEMO_CLUB_CODE,
        city="Budapest", country="HU",
        contact_email="demo@lfa.com", is_active=True,
    )
    db.add(demo_club)
    db.flush()
    ok(f"Club '{_DEMO_CLUB_NAME}' created (id={demo_club.id})")
else:
    ok(f"Club '{_DEMO_CLUB_NAME}' already exists (id={demo_club.id})")

demo_teams: list[Team] = []
all_demo_players: list[User] = []

for tdef in _DEMO_TEAMS:
    team = db.query(Team).filter(Team.club_id == demo_club.id, Team.name == tdef["name"]).first()
    if not team:
        team = Team(
            name=tdef["name"], club_id=demo_club.id,
            age_group_label=tdef["age_group_label"], is_active=True,
        )
        db.add(team)
        db.flush()
    demo_teams.append(team)

    football_skills = {k: tdef["skill_base"] for k in all_skill_keys}
    age_slug = tdef["age_group_label"].lower()

    for idx, (first, last) in enumerate(_DEMO_PLAYERS[tdef["name"]]):
        email = f"demo-{age_slug}-{first.lower()}.{last.lower()}@lfa.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name=f"{first} {last}", first_name=first, last_name=last,
                nickname=first, email=email,
                password_hash=get_password_hash("Demo#1234"),
                role=UserRole.STUDENT, is_active=True,
                onboarding_completed=True, credit_balance=500,
                date_of_birth=tdef["dob"], nationality="British", gender="Male",
                phone=f"+44 7700 9{idx:05d}",
                street_address="2 Demo Lane", city="London",
                postal_code="EC2A 2BB", country="United Kingdom",
            )
            db.add(user)
            db.flush()
            db.add(UserLicense(
                user_id=user.id, specialization_type="LFA_FOOTBALL_PLAYER",
                current_level=1, max_achieved_level=1, started_at=now,
                payment_verified=True, payment_verified_at=now,
                onboarding_completed=True, onboarding_completed_at=now,
                is_active=True, football_skills=football_skills,
                motivation_scores={
                    "position": "MIDFIELDER", "goals": "improve_skills",
                    "motivation": "", "average_skill_level": tdef["skill_base"],
                    "onboarding_completed_at": now.isoformat(),
                },
                average_motivation_score=tdef["skill_base"],
            ))
            db.flush()

        member = db.query(TeamMember).filter(
            TeamMember.team_id == team.id, TeamMember.user_id == user.id
        ).first()
        if not member:
            db.add(TeamMember(team_id=team.id, user_id=user.id, role="PLAYER", is_active=True))
            db.flush()

        all_demo_players.append(user)

db.commit()
db.expire_all()

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
ok(f"Demo teams ready: {[t.name for t in demo_teams]}")
ok(f"Demo players ready: {len(all_demo_players)}")

# Extra teams for Format H (group_knockout × TEAM — needs 8 teams)
gk_extra_teams: list[Team] = []
for gdef in _GK_EXTRA_TEAMS:
    team = db.query(Team).filter(Team.club_id == demo_club.id, Team.name == gdef["name"]).first()
    if not team:
        team = Team(
            name=gdef["name"], club_id=demo_club.id,
            age_group_label=gdef["age_group_label"], is_active=True,
        )
        db.add(team)
        db.flush()
    gk_extra_teams.append(team)
db.commit()
db.expire_all()
gk_extra_teams = [
    db.query(Team).filter(Team.club_id == demo_club.id, Team.name == gdef["name"]).first()
    for gdef in _GK_EXTRA_TEAMS
]
gk_all_teams = demo_teams + gk_extra_teams
ok(f"GK extra teams ready: {[t.name for t in gk_extra_teams]} (8 total for Format H)")


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle helpers  (verbatim from seed_comprehensive_demo.py)
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
    t = Semester(
        name=name, code=f"SC-{_uid()}",
        master_instructor_id=instructor.id,
        campus_id=campus.id, location_id=campus.location_id,
        start_date=date(2026, 9, 1), end_date=date(2026, 9, 3),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status="DRAFT",
    )
    db.add(t)
    db.flush()
    db.add(TournamentConfiguration(
        semester_id=t.id, tournament_type_id=tt_id,
        participant_type=participant_type, max_players=64,
        number_of_rounds=1, parallel_fields=1,
        ranking_direction=ranking_direction, scoring_type=scoring_type,
    ))
    db.add(GameConfiguration(semester_id=t.id, game_preset_id=preset.id))
    db.add(TournamentRewardConfig(
        semester_id=t.id,
        reward_policy_name="Showcase Default",
        reward_config=_REWARD_CONFIG,
    ))
    db.commit()
    db.expire_all()
    ok(f"Created '{t.name}'  id={t.id}")
    return t


def enroll_teams(tid: int, teams: list[Team]) -> None:
    db.expire_all()
    for team in teams:
        ex = db.query(TournamentTeamEnrollment).filter(
            TournamentTeamEnrollment.semester_id == tid,
            TournamentTeamEnrollment.team_id == team.id,
        ).first()
        if not ex:
            db.add(TournamentTeamEnrollment(
                semester_id=tid, team_id=team.id, is_active=True, payment_verified=True,
            ))
    db.commit()
    info(f"Enrolled {len(teams)} teams")


def enroll_individual_players(tid: int, players: list[User]) -> None:
    db.expire_all()
    enrolled = 0
    for u in players:
        lic = db.query(UserLicense).filter(
            UserLicense.user_id == u.id,
            UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
            UserLicense.is_active == True,
        ).first()
        if not lic:
            continue
        ex = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tid,
            SemesterEnrollment.user_id == u.id,
        ).first()
        if not ex:
            db.add(SemesterEnrollment(
                semester_id=tid, user_id=u.id, user_license_id=lic.id,
                is_active=True, request_status=EnrollmentStatus.APPROVED,
            ))
            enrolled += 1
    db.commit()
    info(f"Enrolled {enrolled} individual players")


def transition(tid: int, new_status: str) -> bool:
    r = client.patch(
        f"/api/v1/tournaments/{tid}/status",
        json={"new_status": new_status, "reason": "showcase-seed"},
    )
    if r.status_code != 200:
        err(f"Transition → {new_status} failed: {r.status_code} {r.text[:200]}")
        return False
    db.expire_all()
    ok(f"→ {new_status}")
    return True


def _to_in_progress(tid: int, teams: list[Team] | None = None,
                    players: list[User] | None = None) -> bool:
    """Drive DRAFT → IN_PROGRESS, enrolling teams or players as required."""
    if teams:
        enroll_teams(tid, teams)
    elif players:
        enroll_individual_players(tid, players)
    for status in ("ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", "CHECK_IN_OPEN", "IN_PROGRESS"):
        if not transition(tid, status):
            return False
    db.expire_all()
    n = db.query(SessionModel).filter(SessionModel.semester_id == tid).count()
    info(f"Sessions generated: {n}")
    return True


def submit_team_results(tid: int) -> int:
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
    submitted = 0
    for sess in sessions:
        pids = list(sess.participant_team_ids or [])
        if len(pids) < 2:
            continue
        r = client.patch(
            f"/api/v1/sessions/{sess.id}/team-results",
            json={"results": [
                {"team_id": pids[0], "score": 2},
                {"team_id": pids[1], "score": 0},
            ], "round_number": 1},
        )
        if r.status_code in (200, 201):
            submitted += 1
        else:
            err(f"Team result session {sess.id}: {r.status_code} {r.text[:120]}")
    info(f"Team results: {submitted} session(s)")
    return submitted


def submit_knockout_team_results(tid: int, teams: list[Team]) -> int:
    db.expire_all()
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.semester_id == tid)
        .order_by(SessionModel.tournament_round.asc(), SessionModel.id.asc())
        .all()
    )
    # Group by round
    rounds_map: dict[int, list] = {}
    for s in sessions:
        rounds_map.setdefault(s.tournament_round or 1, []).append(s)

    submitted = 0
    rnd_winners: dict[int, list[int]] = {}
    rnd_losers:  dict[int, list[int]] = {}

    for rnd in sorted(rounds_map.keys()):
        slist = rounds_map[rnd]

        # Populate participants for R2+ from previous winners (or losers for bronze)
        if rnd > 1:
            prev_w = rnd_winners.get(rnd - 1, [])
            prev_l = rnd_losers.get(rnd - 1, [])
            prev_l2 = rnd_losers.get(rnd - 2, [])  # SF losers for bronze
            for sess in slist:
                if sess.participant_team_ids and len(sess.participant_team_ids) >= 2:
                    continue  # already seeded
                # Decide: if prev_w has enough → use winners; else try losers (bronze)
                if len(prev_w) >= 2:
                    pair = prev_w[:2]
                    prev_w = prev_w[2:]
                elif len(prev_l2) >= 2:
                    pair = prev_l2[:2]
                    prev_l2 = prev_l2[2:]
                elif len(prev_l) >= 2:
                    pair = prev_l[:2]
                    prev_l = prev_l[2:]
                else:
                    continue
                sess.participant_team_ids = pair
            db.commit()
            db.expire_all()

        rnd_winners[rnd] = []
        rnd_losers[rnd] = []
        for sess in slist:
            pids = list(sess.participant_team_ids or [])
            if len(pids) < 2:
                continue
            r = client.patch(
                f"/api/v1/sessions/{sess.id}/team-results",
                json={"results": [
                    {"team_id": pids[0], "score": 2},
                    {"team_id": pids[1], "score": 0},
                ], "round_number": 1},
            )
            if r.status_code in (200, 201):
                submitted += 1
                rnd_winners[rnd].append(pids[0])
                rnd_losers[rnd].append(pids[1])
            else:
                err(f"KO R{rnd} session {sess.id}: {r.status_code} {r.text[:120]}")

    info(f"Knockout results: {submitted} session(s)")
    return submitted


def write_gk_game_results(tid: int) -> int:
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
        sess.game_results = _json.dumps({
            "match_format": "HEAD_TO_HEAD",
            "participants": [
                {"user_id": pids[0], "score": 3.0, "result": "win"},
                {"user_id": pids[1], "score": 0.0, "result": "loss"},
            ],
        })
        sess.session_status = "completed"
        written += 1
    db.commit()
    info(f"GK group results written: {written} session(s)")
    return written


def seed_gk_knockout(tid: int) -> bool:
    r = client.post(f"/api/v1/tournaments/{tid}/finalize-group-stage")
    if r.status_code != 200 or not r.json().get("success"):
        err(f"finalize-group-stage failed: {r.status_code} {r.text[:120]}")
        return False
    ok(f"Group stage finalized: {r.json().get('knockout_sessions_updated', '?')} KO sessions seeded")

    db.expire_all()
    ko_sessions = (
        db.query(SessionModel)
        .filter(SessionModel.semester_id == tid, SessionModel.tournament_phase == "KNOCKOUT")
        .order_by(SessionModel.tournament_round.asc(), SessionModel.id.asc())
        .all()
    )
    rounds: dict[int, list] = {}
    for s in ko_sessions:
        rounds.setdefault(s.tournament_round or 0, []).append(s)

    rnd_winners: dict[int, list[int]] = {}
    rnd_losers:  dict[int, list[int]] = {}
    for rnd in sorted(rounds.keys()):
        slist = rounds[rnd]
        if rnd > 1:
            prev_w = rnd_winners.get(rnd - 1, [])
            prev = prev_w if len(prev_w) >= 2 * len(slist) else rnd_losers.get(rnd - 2, [])
            for i, sess in enumerate(slist):
                lo, hi = i * 2, i * 2 + 2
                if hi <= len(prev):
                    sess.participant_user_ids = prev[lo:hi]
            db.commit()
            db.expire_all()

        rnd_winners[rnd] = []
        rnd_losers[rnd] = []
        for sess in slist:
            pids = list(sess.participant_user_ids or [])
            if len(pids) < 2:
                continue
            sess.game_results = _json.dumps({
                "match_format": "HEAD_TO_HEAD",
                "participants": [
                    {"user_id": pids[0], "score": 2.0, "result": "win"},
                    {"user_id": pids[1], "score": 0.0, "result": "loss"},
                ],
            })
            sess.session_status = "completed"
            rnd_winners[rnd].append(pids[0])
            rnd_losers[rnd].append(pids[1])
        db.commit()
        db.expire_all()

    total = sum(len(v) for v in rounds.values())
    ok(f"GK knockout seeded: {total} session(s) in {len(rounds)} round(s)")
    return True


def submit_individual_results(tid: int, players: list[User]) -> int:
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
    submitted = 0
    for sess in sessions:
        results = [
            {"user_id": p.id, "score": float(100 - i * 5), "rank": i + 1}
            for i, p in enumerate(players)
        ]
        r = client.patch(f"/api/v1/sessions/{sess.id}/results", json={"results": results})
        if r.status_code in (200, 201):
            submitted += 1
        else:
            err(f"Individual result session {sess.id}: {r.status_code} {r.text[:120]}")
    info(f"Individual results: {submitted} session(s)")
    return submitted


def submit_h2h_individual_results(tid: int) -> int:
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
    submitted = 0
    for sess in sessions:
        pids = list(sess.participant_user_ids or [])
        if len(pids) < 2:
            err(f"H2H session {sess.id} <2 participants — skipping")
            continue
        r = client.patch(
            f"/api/v1/sessions/{sess.id}/head-to-head-results",
            json={"results": [
                {"user_id": pids[0], "score": 3},
                {"user_id": pids[1], "score": 1},
            ]},
        )
        if r.status_code in (200, 201):
            submitted += 1
        else:
            err(f"H2H session {sess.id}: {r.status_code} {r.text[:120]}")
    info(f"H2H individual results: {submitted}/{len(sessions)} session(s)")
    return submitted


def submit_h2h_results_by_round(tid: int) -> int:
    total = 0
    for rn in range(1, 6):
        db.expire_all()
        round_sessions = (
            db.query(SessionModel)
            .filter(SessionModel.semester_id == tid, SessionModel.tournament_round == rn)
            .all()
        )
        if not round_sessions:
            break
        sub = 0
        for sess in round_sessions:
            pids = list(sess.participant_user_ids or [])
            if len(pids) < 2:
                continue
            r = client.patch(
                f"/api/v1/sessions/{sess.id}/head-to-head-results",
                json={"results": [
                    {"user_id": pids[0], "score": 3},
                    {"user_id": pids[1], "score": 1},
                ]},
            )
            if r.status_code in (200, 201):
                sub += 1
                total += 1
            else:
                err(f"KO IND R{rn} session {sess.id}: {r.status_code} {r.text[:120]}")
        info(f"KO IND R{rn}: {sub}/{len(round_sessions)} submitted")
    return total


def submit_gk_team_results_api(tid: int) -> bool:
    db.expire_all()
    gs = db.query(SessionModel).filter(
        SessionModel.semester_id == tid,
        SessionModel.tournament_phase == "GROUP_STAGE",
    ).all()
    gs_sub = 0
    for sess in gs:
        pids = list(sess.participant_team_ids or [])
        if len(pids) < 2:
            continue
        r = client.patch(
            f"/api/v1/sessions/{sess.id}/team-results",
            json={"results": [
                {"team_id": pids[0], "score": 2},
                {"team_id": pids[1], "score": 0},
            ], "round_number": 1},
        )
        if r.status_code in (200, 201):
            gs_sub += 1
        else:
            err(f"GK GS session {sess.id}: {r.status_code} {r.text[:120]}")
    info(f"GK group stage: {gs_sub}/{len(gs)} submitted")

    r = client.post(f"/api/v1/tournaments/{tid}/finalize-group-stage")
    if r.status_code != 200 or not r.json().get("success"):
        err(f"finalize-group-stage: {r.status_code} {r.text[:120]}")
        return False
    ok(f"Group stage finalized: {r.json().get('knockout_sessions_updated', '?')} KO sessions seeded")

    for rn in range(1, 6):
        db.expire_all()
        ko = db.query(SessionModel).filter(
            SessionModel.semester_id == tid,
            SessionModel.tournament_phase == "KNOCKOUT",
            SessionModel.tournament_round == rn,
        ).all()
        if not ko:
            break
        sub = 0
        for sess in ko:
            pids = list(sess.participant_team_ids or [])
            if len(pids) < 2:
                continue
            r = client.patch(
                f"/api/v1/sessions/{sess.id}/team-results",
                json={"results": [
                    {"team_id": pids[0], "score": 2},
                    {"team_id": pids[1], "score": 0},
                ], "round_number": 1},
            )
            if r.status_code in (200, 201):
                sub += 1
            else:
                err(f"GK KO R{rn} session {sess.id}: {r.status_code} {r.text[:120]}")
        info(f"GK KO R{rn}: {sub}/{len(ko)} submitted")
    return True


def seed_individual_rankings(tid: int, players: list[User]) -> int:
    db.expire_all()
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == tid).delete()
    db.commit()
    for i, p in enumerate(players):
        db.add(TournamentRanking(
            tournament_id=tid, user_id=p.id,
            participant_type="INDIVIDUAL",
            rank=i + 1, points=float(max(0, 100 - i * 5)),
        ))
    db.commit()
    ok(f"Individual rankings seeded directly: {len(players)}")
    return len(players)


def seed_team_rankings(tid: int, teams: list[Team]) -> int:
    db.expire_all()
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == tid).delete()
    db.commit()
    for i, team in enumerate(teams):
        db.add(TournamentRanking(
            tournament_id=tid, team_id=team.id,
            participant_type="TEAM",
            rank=i + 1, points=float(max(0, 10 - i * 3)),
            wins=max(0, 3 - i), losses=i, draws=0,
        ))
    db.commit()
    ok(f"Team rankings seeded directly: {len(teams)}")
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
        ok(f"Rewards distributed → {final.tournament_status}")
        return True
    err(f"Rewards failed: {r.status_code} {r.text[:150]}")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Track all created events
# ─────────────────────────────────────────────────────────────────────────────

_created: list[dict] = []   # {"fmt": str, "name": str, "id": int, "ok": bool}


def _register(fmt: str, t: Semester, success: bool) -> None:
    _created.append({"fmt": fmt, "name": t.name, "id": t.id, "ok": success})


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT A — H2H LEAGUE (TEAM)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT A — H2H League (TEAM)")

t = create_tournament("Showcase: H2H League TEAM", tt_league.id, "TEAM")
ok_a = False
if _to_in_progress(t.id, teams=demo_teams):
    submit_team_results(t.id)
    if not calculate_rankings(t.id):
        seed_team_rankings(t.id, demo_teams)
    if transition(t.id, "COMPLETED"):
        ok_a = distribute_rewards(t.id)
_register("A", t, ok_a)


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT B — KNOCKOUT (TEAM)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT B — Knockout (TEAM)")

t = create_tournament("Showcase: Knockout TEAM", tt_knockout.id, "TEAM")
ok_b = False
if _to_in_progress(t.id, teams=demo_teams):
    submit_knockout_team_results(t.id, demo_teams)
    if not calculate_rankings(t.id):
        seed_team_rankings(t.id, demo_teams)
    if transition(t.id, "COMPLETED"):
        ok_b = distribute_rewards(t.id)
_register("B", t, ok_b)


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT C — GROUP KNOCKOUT (INDIVIDUAL)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT C — Group Knockout (INDIVIDUAL)")

t = create_tournament("Showcase: Group Knockout IND", tt_gk.id, "INDIVIDUAL")
ok_c = False
if _to_in_progress(t.id, players=all_demo_players):
    write_gk_game_results(t.id)
    if seed_gk_knockout(t.id):
        if not calculate_rankings(t.id):
            seed_individual_rankings(t.id, all_demo_players)
        if transition(t.id, "COMPLETED"):
            ok_c = distribute_rewards(t.id)
_register("C", t, ok_c)


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT D — SWISS (INDIVIDUAL)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT D — Swiss (INDIVIDUAL)")

t = create_tournament("Showcase: Swiss IND", tt_swiss.id, "INDIVIDUAL")
ok_d = False
if _to_in_progress(t.id, players=all_demo_players):
    submit_h2h_individual_results(t.id)
    # Swiss requires API-based ranking calculation; no direct-write fallback
    if calculate_rankings(t.id):
        if transition(t.id, "COMPLETED"):
            ok_d = distribute_rewards(t.id)
    else:
        # Fallback: seed rankings directly so the showcase is complete
        seed_individual_rankings(t.id, all_demo_players)
        if transition(t.id, "COMPLETED"):
            ok_d = distribute_rewards(t.id)
_register("D", t, ok_d)


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT E — INDIVIDUAL RANKING / SCORE_BASED (INDIVIDUAL)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT E — IR Score-Based (INDIVIDUAL)")

t = create_tournament(
    "Showcase: IR Score IND", tt_id=None,
    participant_type="INDIVIDUAL", scoring_type="SCORE_BASED",
)
ok_e = False
if _to_in_progress(t.id, players=all_demo_players):
    submit_individual_results(t.id, all_demo_players)
    if not calculate_rankings(t.id):
        seed_individual_rankings(t.id, all_demo_players)
    if transition(t.id, "COMPLETED"):
        ok_e = distribute_rewards(t.id)
_register("E", t, ok_e)


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT F — H2H LEAGUE (INDIVIDUAL)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT F — H2H League (INDIVIDUAL)")

t = create_tournament("Showcase: H2H League IND", tt_league.id, "INDIVIDUAL")
ok_f = False
if _to_in_progress(t.id, players=all_demo_players):
    submit_h2h_individual_results(t.id)
    if not calculate_rankings(t.id):
        seed_individual_rankings(t.id, all_demo_players)
    if transition(t.id, "COMPLETED"):
        ok_f = distribute_rewards(t.id)
_register("F", t, ok_f)


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT G — KNOCKOUT (INDIVIDUAL)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT G — Knockout (INDIVIDUAL)")

t = create_tournament("Showcase: Knockout IND", tt_knockout.id, "INDIVIDUAL")
ok_g = False
if _to_in_progress(t.id, players=all_demo_players):
    submit_h2h_results_by_round(t.id)
    if not calculate_rankings(t.id):
        seed_individual_rankings(t.id, all_demo_players)
    if transition(t.id, "COMPLETED"):
        ok_g = distribute_rewards(t.id)
_register("G", t, ok_g)


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT H — GROUP KNOCKOUT (TEAM, 8 teams)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT H — Group Knockout (TEAM, 8 teams)")

t = create_tournament("Showcase: Group Knockout TEAM", tt_gk.id, "TEAM")
ok_h = False
if _to_in_progress(t.id, teams=gk_all_teams):
    if submit_gk_team_results_api(t.id):
        if not calculate_rankings(t.id):
            seed_team_rankings(t.id, gk_all_teams)
        if transition(t.id, "COMPLETED"):
            ok_h = distribute_rewards(t.id)
_register("H", t, ok_h)


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT I — INDIVIDUAL RANKING (TEAM)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT I — IR Team")

t = create_tournament(
    "Showcase: IR TEAM", tt_id=None,
    participant_type="TEAM", scoring_type="SCORE_BASED",
)
ok_i = False
if _to_in_progress(t.id, teams=demo_teams):
    submit_team_results(t.id)
    if not calculate_rankings(t.id):
        seed_team_rankings(t.id, demo_teams)
    if transition(t.id, "COMPLETED"):
        ok_i = distribute_rewards(t.id)
_register("I", t, ok_i)


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT J — IR TIME_BASED (INDIVIDUAL, ASC)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT J — IR Time-Based (INDIVIDUAL, ASC)")

t = create_tournament(
    "Showcase: IR Time IND", tt_id=None,
    participant_type="INDIVIDUAL", scoring_type="TIME_BASED",
    ranking_direction="ASC",
)
ok_j = False
if _to_in_progress(t.id, players=all_demo_players):
    submit_individual_results(t.id, all_demo_players)
    if not calculate_rankings(t.id):
        seed_individual_rankings(t.id, all_demo_players)
    if transition(t.id, "COMPLETED"):
        ok_j = distribute_rewards(t.id)
_register("J", t, ok_j)


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT K — IR PLACEMENT (INDIVIDUAL, ASC)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT K — IR Placement (INDIVIDUAL, ASC)")

t = create_tournament(
    "Showcase: IR Placement IND", tt_id=None,
    participant_type="INDIVIDUAL", scoring_type="PLACEMENT",
    ranking_direction="ASC",
)
ok_k = False
if _to_in_progress(t.id, players=all_demo_players):
    submit_individual_results(t.id, all_demo_players)
    if not calculate_rankings(t.id):
        seed_individual_rankings(t.id, all_demo_players)
    if transition(t.id, "COMPLETED"):
        ok_k = distribute_rewards(t.id)
_register("K", t, ok_k)


# ─────────────────────────────────────────────────────────────────────────────
# POST-SEED VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

section("POST-SEED VALIDATION")

validation_errors: list[str] = []

for entry in _created:
    tid = entry["id"]
    fmt = entry["fmt"]
    t_obj = db.query(Semester).filter(Semester.id == tid).first()

    if not t_obj:
        validation_errors.append(f"{fmt}: Semester not found")
        continue

    # 1. Status must be REWARDS_DISTRIBUTED
    if t_obj.tournament_status != "REWARDS_DISTRIBUTED":
        validation_errors.append(f"{fmt}: status={t_obj.tournament_status} (expected REWARDS_DISTRIBUTED)")

    # 2. Rankings must exist
    ranking_count = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tid
    ).count()
    if ranking_count == 0:
        validation_errors.append(f"{fmt}: no rankings")
    else:
        # Check no NULL rank
        null_ranks = db.execute(_sql(
            f"SELECT COUNT(*) FROM tournament_rankings WHERE tournament_id={tid} AND rank IS NULL"
        )).scalar()
        if null_ranks:
            validation_errors.append(f"{fmt}: {null_ranks} NULL rank(s)")

    # 3. Reward distributions must exist
    dist_count = db.execute(_sql(
        f"SELECT COUNT(*) FROM tournament_participations WHERE semester_id={tid}"
    )).scalar()
    if dist_count == 0:
        validation_errors.append(f"{fmt}: no reward distributions")

    # 4. All sessions must be completed (if any)
    incomplete = db.execute(_sql(
        f"SELECT COUNT(*) FROM sessions WHERE semester_id={tid} AND session_status != 'completed'"
    )).scalar()
    if incomplete:
        validation_errors.append(f"{fmt}: {incomplete} incomplete session(s)")

    ok(f"{fmt}  status={t_obj.tournament_status}  rankings={ranking_count}  dists={dist_count}")

if validation_errors:
    print()
    for e in validation_errors:
        err(f"VALIDATION: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "─" * 52)
print("🏆  REWARDS DISTRIBUTED SHOWCASE — SUMMARY")
print("─" * 52)
for entry in _created:
    icon = "✅" if entry["ok"] else "❌"
    print(f"  {icon}  {entry['fmt']}  {entry['name']:<40}  id={entry['id']}")
print("─" * 52)

success_count = sum(1 for e in _created if e["ok"])
print(f"  📊  {success_count} / {len(_created)} event(s) → REWARDS_DISTRIBUTED")

if validation_errors:
    print(f"  ⚠️   {len(validation_errors)} validation error(s) — see above")
else:
    print(f"  ✅  Validáció: minden event helyes")

print("─" * 52)
print()

db.close()
