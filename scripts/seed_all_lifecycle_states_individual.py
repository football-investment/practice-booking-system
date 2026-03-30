"""
Seed All Lifecycle States — INDIVIDUAL RANKING format
======================================================
Creates one INDIVIDUAL_RANKING promotion event for every tournament status
so the /admin/promotion-events UI shows Individual Ranking in all 8 states.

States seeded (8 total):
  DRAFT              — minimal tournament, no transitions
  ENROLLMENT_OPEN    — 4 players visible in enrollment
  ENROLLMENT_CLOSED  — enrollment closed, sessions not yet generated
  CHECK_IN_OPEN      — sessions auto-generated on this transition
  IN_PROGRESS        — sessions running, partial results submitted
  COMPLETED          — all results + rankings calculated
  REWARDS_DISTRIBUTED — full pipeline including rewards
  CANCELLED          — cancelled from DRAFT

Usage:
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \\
        SECRET_KEY="..." PYTHONPATH=. python scripts/seed_all_lifecycle_states_individual.py
"""
import os, sys, uuid
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
from app.models.campus import Campus
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.license import UserLicense
from app.models.tournament_reward_config import TournamentRewardConfig
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.skills_config import get_all_skill_keys
from app.dependencies import (
    get_current_user_web,
    get_current_admin_user_hybrid,
    get_current_admin_or_instructor_user_hybrid,
)

# Baseline football_skills for seed players (flat format, 65.0 adult beginner)
_IR_FOOTBALL_SKILLS = {k: 65.0 for k in get_all_skill_keys()}

# Reward config for IR tournaments: 8 core skills enabled
_IR_REWARD_CONFIG = {
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

app.dependency_overrides[get_current_user_web] = lambda: admin
app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin
app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = lambda: admin

client = TestClient(app, follow_redirects=False)

def ok(msg):   print(f"  ✅  {msg}")
def info(msg): print(f"       {msg}")
def err(msg):  print(f"  ❌  {msg}")


# ── Helpers ────────────────────────────────────────────────────────────────

def _uid():
    return uuid.uuid4().hex[:6]


def create_ir_tournament(name: str, status: str = "DRAFT") -> Semester:
    """Create an INDIVIDUAL_RANKING tournament with campus + instructor pre-set."""
    t = Semester(
        name=name,
        code=f"IR-{_uid()}",
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
        tournament_type_id=None,      # None → INDIVIDUAL_RANKING format
        participant_type="INDIVIDUAL",
        max_players=32,
        number_of_rounds=1,
        parallel_fields=1,
        ranking_direction="DESC",
        scoring_type="SCORE_BASED",
    ))
    db.add(GameConfiguration(
        semester_id=t.id,
        game_preset_id=preset.id,
    ))
    db.add(TournamentRewardConfig(
        semester_id=t.id,
        reward_policy_name="IR Default",
        reward_config=_IR_REWARD_CONFIG,
    ))
    db.commit()
    db.expire_all()
    ok(f"Created '{t.name}'  id={t.id}  status={t.tournament_status}")
    return t


def enroll_players(tid: int, count: int = 4) -> list:
    """Create `count` test users + LFA licenses + approved enrollments."""
    db.expire_all()
    players = []
    for i in range(count):
        u = User(
            email=f"ir-player-{_uid()}@lfa-seed.com",
            name=f"IR Player {i+1}",
            password_hash=get_password_hash("seed123"),
            role=UserRole.STUDENT,
            is_active=True,
        )
        db.add(u)
        db.flush()
        lic = UserLicense(
            user_id=u.id,
            specialization_type="LFA_FOOTBALL_PLAYER",
            started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            onboarding_completed=True,
            onboarding_completed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            is_active=True,
            football_skills=_IR_FOOTBALL_SKILLS,
        )
        db.add(lic)
        db.flush()
        enr = SemesterEnrollment(
            semester_id=tid,
            user_id=u.id,
            user_license_id=lic.id,
            is_active=True,
            request_status=EnrollmentStatus.APPROVED,
        )
        db.add(enr)
        db.flush()
        players.append(u)
    db.commit()
    info(f"Enrolled {count} players")
    return players


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


def submit_ir_results(tid: int, players: list, max_sessions: int = None) -> int:
    """Submit INDIVIDUAL_RANKING results for all (or first `max_sessions`) sessions."""
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
    if max_sessions:
        sessions = sessions[:max_sessions]
    submitted = 0
    for sess in sessions:
        results = [
            {"user_id": p.id, "score": float(100 - i * 10), "rank": i + 1}
            for i, p in enumerate(players)
        ]
        r = client.patch(
            f"/api/v1/sessions/{sess.id}/results",
            json={"results": results},
        )
        if r.status_code not in (200, 201):
            err(f"IR result session {sess.id}: {r.status_code} {r.text[:150]}")
        else:
            submitted += 1
    info(f"Results submitted: {submitted} session(s)")
    return submitted


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


# ── Cleanup: delete existing IR seed tournaments (raw SQL → respects FK order) ─
from sqlalchemy import text as _sql

_existing_ids = [
    row[0] for row in db.execute(
        _sql("SELECT s.id FROM semesters s JOIN tournament_configurations tc ON tc.semester_id = s.id WHERE s.name LIKE 'IR Skills Cup%' AND tc.participant_type = 'INDIVIDUAL'")
    ).fetchall()
]
if _existing_ids:
    print(f"\n🧹 Deleting {len(_existing_ids)} existing IR seed tournament(s)...")
    id_list = ", ".join(str(i) for i in _existing_ids)
    # Tables that reference semesters via semester_id
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
    # tournament_status_history uses tournament_id column
    try:
        db.execute(_sql(f"DELETE FROM tournament_status_history WHERE tournament_id IN ({id_list})"))
    except Exception:
        db.rollback()
    db.execute(_sql(f"DELETE FROM semesters WHERE id IN ({id_list})"))
    db.commit()
    print("   Done.")

# ══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  SEEDING INDIVIDUAL RANKING — ALL 8 LIFECYCLE STATES")
print("="*60)

# ── 1. DRAFT ───────────────────────────────────────────────────────────────
print("\n[1/8] DRAFT")
t = create_ir_tournament("IR Skills Cup — Draft 2026")
# No transitions needed; stays in DRAFT

# ── 2. ENROLLMENT_OPEN ─────────────────────────────────────────────────────
print("\n[2/8] ENROLLMENT_OPEN")
t = create_ir_tournament("IR Skills Cup — Enrollment Open 2026")
players = enroll_players(t.id, count=4)
transition(t.id, "ENROLLMENT_OPEN")

# ── 3. ENROLLMENT_CLOSED ───────────────────────────────────────────────────
print("\n[3/8] ENROLLMENT_CLOSED")
t = create_ir_tournament("IR Skills Cup — Enrollment Closed 2026")
players = enroll_players(t.id, count=4)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")

# ── 4. CHECK_IN_OPEN (sessions auto-generated) ────────────────────────────
print("\n[4/8] CHECK_IN_OPEN")
t = create_ir_tournament("IR Skills Cup — Check-In Open 2026")
players = enroll_players(t.id, count=4)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
db.expire_all()
sess_count = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
info(f"Sessions auto-generated: {sess_count}")

# ── 5. IN_PROGRESS (partial results) ──────────────────────────────────────
print("\n[5/8] IN_PROGRESS")
t = create_ir_tournament("IR Skills Cup — In Progress 2026")
players = enroll_players(t.id, count=4)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    sess_count = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    info(f"Sessions generated: {sess_count}")
    # Submit results for 0 sessions — keeps it "live" with no complete results yet
    info("No results submitted — tournament stays live")

# ── 6. COMPLETED (all results + rankings) ─────────────────────────────────
print("\n[6/8] COMPLETED")
t = create_ir_tournament("IR Skills Cup — Completed 2026")
players = enroll_players(t.id, count=4)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    sess_count = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    info(f"Sessions generated: {sess_count}")
    submit_ir_results(t.id, players)
    calculate_rankings(t.id)
    transition(t.id, "COMPLETED")

# ── 7. REWARDS_DISTRIBUTED ────────────────────────────────────────────────
print("\n[7/8] REWARDS_DISTRIBUTED")
t = create_ir_tournament("IR Skills Cup — Rewards Distributed 2026")
players = enroll_players(t.id, count=4)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    sess_count = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    info(f"Sessions generated: {sess_count}")
    submit_ir_results(t.id, players)
    calculate_rankings(t.id)
    if transition(t.id, "COMPLETED"):
        distribute_rewards(t.id)

# ── 8. CANCELLED ──────────────────────────────────────────────────────────
print("\n[8/8] CANCELLED")
t = create_ir_tournament("IR Skills Cup — Cancelled 2026")
transition(t.id, "CANCELLED")

# ── Summary ────────────────────────────────────────────────────────────────
db.expire_all()
print("\n" + "="*60)
print("  FINAL STATE SUMMARY — INDIVIDUAL RANKING")
print("="*60)
all_t = (
    db.query(Semester)
    .join(TournamentConfiguration, TournamentConfiguration.semester_id == Semester.id)
    .filter(
        TournamentConfiguration.participant_type == "INDIVIDUAL",
        Semester.name.like("IR Skills Cup%"),
    )
    .order_by(Semester.id)
    .all()
)
for t in all_t:
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    enrollments = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.semester_id == t.id,
        SemesterEnrollment.is_active == True,
    ).count()
    print(f"  id={t.id:3d}  {t.tournament_status:22s}  players={enrollments}  sessions={sessions}  {t.name}")

print()
print("  View: http://localhost:8000/admin/promotion-events")
print("="*60)
