"""
Seed All Lifecycle States
=========================
Creates one promotion event for every tournament status so the
/admin/promotion-events UI can be validated with real data.

States seeded:
  DRAFT              — already exists (id=1), skipped
  ENROLLMENT_OPEN    — already exists (id=2), skipped
  CANCELLED          — already exists (id=3), skipped
  ENROLLMENT_CLOSED  — U18, 8 teams enrolled, closed
  CHECK_IN_OPEN      — U15, 4 teams, check-in open
  IN_PROGRESS        — U15, 4 teams, 3/6 sessions played (live)
  COMPLETED          — U15, 4 teams, all sessions played + rankings
  REWARDS_DISTRIBUTED — U15, 4 teams, full pipeline + rewards

Usage:
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \\
        SECRET_KEY="..." PYTHONPATH=. python scripts/seed_all_lifecycle_states.py
"""
import os, sys, datetime, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
os.environ.setdefault("SECRET_KEY", "e2e-test-secret-key-minimum-32-chars-needed")

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.models.user import User
from app.models.team import TournamentTeamEnrollment
from app.dependencies import get_current_user_web, get_current_admin_user_hybrid, get_current_admin_or_instructor_user_hybrid

# ── Setup ──────────────────────────────────────────────────────────────────
db = SessionLocal()
admin = db.query(User).filter(User.email == "admin@lfa.com").first()
instructor = db.query(User).filter(User.email == "instructor@lfa.com").first()
if not admin or not instructor:
    print("❌ admin@lfa.com or instructor@lfa.com not found — run bootstrap_clean.py first")
    sys.exit(1)

app.dependency_overrides[get_current_user_web] = lambda: admin
app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin
app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = lambda: admin

client = TestClient(app, follow_redirects=False)
csrf = client.get("/admin/tournaments").cookies.get("csrf_token", "")

def _rf(resp): # refresh csrf
    global csrf
    t = resp.cookies.get("csrf_token")
    if t: csrf = t

def post_form(url, data):
    r = client.post(url, data=data, headers={"X-CSRF-Token": csrf}); _rf(r); return r

def api_patch(url, body):
    r = client.patch(url, json=body); _rf(r); return r

def api_post(url, body):
    r = client.post(url, json=body); _rf(r); return r

def ok(msg):  print(f"  ✅  {msg}")
def info(msg): print(f"       {msg}")
def err(msg):  print(f"  ❌  {msg}")

# ── Helpers ────────────────────────────────────────────────────────────────
def wizard(age_group, name_prefix, campus_id=1, tt_id=1):
    r = post_form("/admin/clubs/1/promotion", {
        "tournament_name": name_prefix,
        "start_date": "2026-07-01",
        "end_date": "2026-07-03",
        "campus_id": str(campus_id),
        "tournament_type_id": str(tt_id),
        "game_preset_id": "",
        "age_groups": [age_group],
    })
    if r.status_code not in (302, 303):
        err(f"Wizard failed: {r.status_code} {r.text[:200]}")
        return None
    db.expire_all()
    t = db.query(Semester).filter(Semester.name.like(f"%{name_prefix}%")).order_by(Semester.id.desc()).first()
    team_count = db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == t.id,
        TournamentTeamEnrollment.is_active == True,
    ).count()
    ok(f"Created '{t.name}'  id={t.id}  teams={team_count}")
    return t

def transition(tid, new_status):
    r = api_patch(f"/api/v1/tournaments/{tid}/status",
                  {"new_status": new_status, "reason": "seed"})
    if r.status_code != 200:
        err(f"Transition {tid} → {new_status} failed: {r.status_code} {r.text[:150]}")
        return False
    db.expire_all()
    ok(f"→ {new_status}")
    return True

def set_instructor(tid):
    db.expire_all()
    t = db.query(Semester).filter(Semester.id == tid).first()
    t.master_instructor_id = instructor.id
    db.commit(); db.expire_all()

def submit_results(tid, max_sessions=None):
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
    if max_sessions:
        sessions = sessions[:max_sessions]
    submitted = 0
    for s in sessions:
        db.expire_all()
        s = db.query(SessionModel).filter(SessionModel.id == s.id).first()
        team_ids = s.participant_team_ids or []
        if len(team_ids) < 2:
            continue
        r = api_patch(f"/api/v1/sessions/{s.id}/team-results", {
            "results": [{"team_id": team_ids[0], "score": 2},
                        {"team_id": team_ids[1], "score": 1}],
            "round_number": 1,
        })
        if r.status_code not in (200, 201):
            err(f"Result submit session {s.id}: {r.status_code}")
        else:
            submitted += 1
    info(f"Results submitted: {submitted} session(s)")
    return submitted

# ══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  SEEDING ALL LIFECYCLE STATES")
print("="*60)

# ── 1. ENROLLMENT_CLOSED — U18, 8 teams ───────────────────────────────────
print("\n[1/5] ENROLLMENT_CLOSED")
t = wizard("U18", "Autumn Cup 2026")
if t:
    transition(t.id, "ENROLLMENT_OPEN")
    transition(t.id, "ENROLLMENT_CLOSED")

# ── 2. CHECK_IN_OPEN — U15, 4 teams ──────────────────────────────────────
print("\n[2/5] CHECK_IN_OPEN")
t = wizard("U15", "Winter Tournament 2026")
if t:
    transition(t.id, "ENROLLMENT_OPEN")
    transition(t.id, "ENROLLMENT_CLOSED")
    transition(t.id, "CHECK_IN_OPEN")

# ── 3. IN_PROGRESS — U15, 4 teams, 3 sessions played ─────────────────────
print("\n[3/5] IN_PROGRESS")
t = wizard("U15", "Spring League 2026")
if t:
    transition(t.id, "ENROLLMENT_OPEN")
    transition(t.id, "ENROLLMENT_CLOSED")
    transition(t.id, "CHECK_IN_OPEN")
    set_instructor(t.id)
    if transition(t.id, "IN_PROGRESS"):
        db.expire_all()
        sess_count = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
        info(f"Sessions generated: {sess_count}")
        submit_results(t.id, max_sessions=3)  # partial — live tournament

# ── 4. COMPLETED — U15, 4 teams, all sessions + rankings ─────────────────
print("\n[4/5] COMPLETED")
t = wizard("U15", "Summer Championship 2026")
if t:
    transition(t.id, "ENROLLMENT_OPEN")
    transition(t.id, "ENROLLMENT_CLOSED")
    transition(t.id, "CHECK_IN_OPEN")
    set_instructor(t.id)
    if transition(t.id, "IN_PROGRESS"):
        db.expire_all()
        sess_count = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
        info(f"Sessions generated: {sess_count}")
        submit_results(t.id)   # all sessions
        r = api_post(f"/api/v1/tournaments/{t.id}/calculate-rankings", {})
        if r.status_code == 200:
            ok("Rankings calculated")
        else:
            err(f"Rankings failed: {r.status_code} {r.text[:120]}")
        transition(t.id, "COMPLETED")

# ── 5. REWARDS_DISTRIBUTED — U12, 2 teams, full pipeline ─────────────────
print("\n[5/5] REWARDS_DISTRIBUTED")
t = wizard("U12", "Year-End Cup 2026")
if t:
    transition(t.id, "ENROLLMENT_OPEN")
    transition(t.id, "ENROLLMENT_CLOSED")
    transition(t.id, "CHECK_IN_OPEN")
    set_instructor(t.id)
    if transition(t.id, "IN_PROGRESS"):
        db.expire_all()
        sess_count = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
        info(f"Sessions generated: {sess_count}")
        submit_results(t.id)
        r = api_post(f"/api/v1/tournaments/{t.id}/calculate-rankings", {})
        if r.status_code == 200:
            ok("Rankings calculated")
        else:
            err(f"Rankings failed: {r.status_code} {r.text[:120]}")
        if transition(t.id, "COMPLETED"):
            r = api_post(f"/api/v1/tournaments/{t.id}/distribute-rewards-v2",
                         {"tournament_id": t.id, "force_redistribution": False})
            if r.status_code == 200:
                db.expire_all()
                final = db.query(Semester).filter(Semester.id == t.id).first()
                ok(f"Rewards distributed → status: {final.tournament_status}")
            else:
                err(f"Rewards failed: {r.status_code} {r.text[:120]}")

# ── Summary ────────────────────────────────────────────────────────────────
db.expire_all()
print("\n" + "="*60)
print("  FINAL STATE SUMMARY")
print("="*60)
all_t = db.query(Semester).order_by(Semester.id).all()
for t in all_t:
    teams = db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == t.id,
        TournamentTeamEnrollment.is_active == True,
    ).count()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    print(f"  id={t.id:2d}  {t.tournament_status:22s}  teams={teams}  sessions={sessions}  {t.name}")

print()
print("  View: http://localhost:8000/admin/promotion-events")
print("="*60)
db.close()
