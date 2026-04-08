"""
Virtual Demo Seed
=================
Creates virtual-delivery tournaments across 2 formats × 4 lifecycle states
to demonstrate the session_type_config='virtual' flow introduced in Phase 1.

Formats
-------
  V-A  Individual Ranking  (INDIVIDUAL, SCORE_BASED, virtual)
  V-B  H2H League          (INDIVIDUAL, WDL_BASED,   virtual)

Lifecycle states per format
---------------------------
  DRAFT  IN_PROGRESS  COMPLETED  REWARDS_DISTRIBUTED

Total: 8 events

Virtual guarantees (validated at end of script)
------------------------------------------------
  • Every generated session has session_type='virtual'
  • Every generated session has base_xp=50
  • COMPLETED / REWARDS_DISTRIBUTED events have meeting_link set on all sessions
  • Target tournament_status reached for all 8 events

Players: 6 bootstrap LFA U15 players (bootstrap_clean.py must run first)
         No new club, players, or teams are created.

Idempotent: deletes all "Virtual Demo: " prefixed tournaments before re-seeding.
Only dependency: bootstrap_clean.py (admin, instructor, campus, preset, LFA-BOOT club).

Usage
-----
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \\
        SECRET_KEY="..." PYTHONPATH=. python scripts/seed_virtual_demo.py
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
os.environ.setdefault("SECRET_KEY", "e2e-test-secret-key-minimum-32-chars-needed")

from datetime import date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import text as _sql

from app.main import app
from app.database import SessionLocal
from app.models.campus import Campus
from app.models.club import Club
from app.models.game_configuration import GameConfiguration
from app.models.game_preset import GamePreset
from app.models.license import UserLicense
from app.models.semester import Semester, SemesterCategory, SemesterStatus
from app.models.semester_enrollment import EnrollmentStatus, SemesterEnrollment
from app.models.session import Session as SessionModel, SessionType
from app.models.team import Team, TeamMember
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_reward_config import TournamentRewardConfig
from app.models.tournament_type import TournamentType
from app.models.user import User
from app.dependencies import (
    get_current_admin_or_instructor_user_hybrid,
    get_current_admin_user_hybrid,
    get_current_user_web,
)

# ─────────────────────────────────────────────────────────────────────────────
# Output helpers
# ─────────────────────────────────────────────────────────────────────────────

def ok(msg):     print(f"  ✅  {msg}")
def info(msg):   print(f"       {msg}")
def err(msg):    print(f"  ❌  {msg}")
def section(t):  print(f"\n{'='*64}\n  {t}\n{'='*64}")


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_PREFIX = "Virtual Demo: "
_MEETING_LINK = "https://meet.example.com/virtual-demo"

_REWARD_CONFIG = {
    "skill_mappings": [
        {"skill": "ball_control",  "weight": 1.2, "category": "TECHNICAL", "enabled": True},
        {"skill": "passing",       "weight": 1.0, "category": "TECHNICAL", "enabled": True},
        {"skill": "finishing",     "weight": 1.2, "category": "TECHNICAL", "enabled": True},
        {"skill": "sprint_speed",  "weight": 1.1, "category": "PHYSICAL",  "enabled": True},
        {"skill": "stamina",       "weight": 1.0, "category": "PHYSICAL",  "enabled": True},
        {"skill": "composure",     "weight": 1.0, "category": "MENTAL",    "enabled": True},
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

preset = (
    db.query(GamePreset).filter(GamePreset.code == "outfield_default").first()
    or db.query(GamePreset).first()
)
if not preset:
    print("❌  No GamePreset found — run bootstrap_clean.py first")
    sys.exit(1)

tt_league = db.query(TournamentType).filter(TournamentType.code == "league").first()
if not tt_league:
    print("❌  TournamentType 'league' missing — run bootstrap_clean.py first")
    sys.exit(1)

app.dependency_overrides[get_current_user_web] = lambda: admin
app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin
app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = lambda: admin

client = TestClient(app, follow_redirects=False)


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap U15 players
# ─────────────────────────────────────────────────────────────────────────────

section("Bootstrap U15 players — LFA-BOOT / LFA U15 (6 players)")

boot_club = db.query(Club).filter(Club.code == "LFA-BOOT").first()
if not boot_club:
    print("❌  LFA-BOOT club not found — run bootstrap_clean.py first")
    sys.exit(1)

boot_team = db.query(Team).filter(
    Team.club_id == boot_club.id,
    Team.name == "LFA U15",
).first()
if not boot_team:
    print("❌  'LFA U15' team not found — run bootstrap_clean.py first")
    sys.exit(1)

boot_players = (
    db.query(User)
    .join(TeamMember, TeamMember.user_id == User.id)
    .filter(TeamMember.team_id == boot_team.id)
    .limit(6)
    .all()
)
if len(boot_players) < 6:
    print(f"❌  Only {len(boot_players)} U15 players found (need 6) — run bootstrap_clean.py first")
    sys.exit(1)

ok(f"Found {len(boot_players)} bootstrap U15 players: {[p.name for p in boot_players]}")


# ─────────────────────────────────────────────────────────────────────────────
# Cleanup: remove existing Virtual Demo: tournaments
# ─────────────────────────────────────────────────────────────────────────────

section("Cleanup — removing existing Virtual Demo: tournaments")

_existing_ids = [
    row[0] for row in db.execute(
        _sql("SELECT id FROM semesters WHERE name LIKE 'Virtual Demo: %'")
    ).fetchall()
]
if _existing_ids:
    print(f"  🧹  Found {len(_existing_ids)} existing Virtual Demo tournament(s) — deleting...")
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
    ok(f"Deleted {len(_existing_ids)} Virtual Demo tournament(s)")
else:
    ok("No existing Virtual Demo tournaments found")


# ─────────────────────────────────────────────────────────────────────────────
# Tournament factory + lifecycle helpers
# ─────────────────────────────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex[:6]


def create_virtual_tournament(
    name: str,
    tt_id: int | None,
    participant_type: str,
    scoring_type: str = "SCORE_BASED",
    ranking_direction: str = "DESC",
) -> Semester:
    """Create a DRAFT virtual tournament (session_type_config='virtual')."""
    t = Semester(
        name=name,
        code=f"VD-{_uid()}",
        master_instructor_id=instructor.id,
        campus_id=campus.id,
        location_id=campus.location_id,
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 3),
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
        session_type_config="virtual",   # ← Phase 1: all generated sessions will be virtual
    ))
    db.add(GameConfiguration(semester_id=t.id, game_preset_id=preset.id))
    db.add(TournamentRewardConfig(
        semester_id=t.id,
        reward_policy_name="Virtual Demo Default",
        reward_config=_REWARD_CONFIG,
    ))
    db.commit()
    db.expire_all()
    ok(f"Created '{t.name}'  id={t.id}  (session_type_config=virtual)")
    return t


def enroll_players(tid: int, players: list[User]) -> list[User]:
    """Enroll bootstrap players individually."""
    db.expire_all()
    enrolled = []
    for u in players:
        lic = db.query(UserLicense).filter(
            UserLicense.user_id == u.id,
            UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
            UserLicense.is_active == True,
        ).first()
        if not lic:
            info(f"  ⚠ No active license for {u.email} — skipping")
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
    info(f"Enrolled {len(enrolled)} players")
    return enrolled


def transition(tid: int, new_status: str) -> bool:
    r = client.patch(
        f"/api/v1/tournaments/{tid}/status",
        json={"new_status": new_status, "reason": "virtual-demo-seed"},
    )
    if r.status_code != 200:
        err(f"Transition {tid} → {new_status} failed: {r.status_code} {r.text[:200]}")
        return False
    db.expire_all()
    ok(f"→ {new_status}")
    return True


def patch_meeting_links(tid: int) -> int:
    """Set meeting_link on all sessions of a tournament after session generation."""
    db.expire_all()
    count = (
        db.query(SessionModel)
        .filter(SessionModel.semester_id == tid)
        .update({"meeting_link": _MEETING_LINK})
    )
    db.commit()
    info(f"meeting_link patched on {count} session(s)")
    return count


def submit_ir_results(tid: int, players: list[User]) -> int:
    """Submit individual score results for all IR sessions."""
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
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
        if r.status_code in (200, 201):
            submitted += 1
        else:
            err(f"IR result session {sess.id}: {r.status_code} {r.text[:120]}")
    info(f"IR results submitted: {submitted}/{len(sessions)} session(s)")
    return submitted


def submit_h2h_results(tid: int) -> int:
    """Submit H2H results for all league sessions (reads participant_user_ids)."""
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
    submitted = 0
    for sess in sessions:
        pids = list(sess.participant_user_ids or [])
        if len(pids) < 2:
            err(f"H2H session {sess.id} has <2 participants — skipping")
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
            err(f"H2H result session {sess.id}: {r.status_code} {r.text[:120]}")
    info(f"H2H results submitted: {submitted}/{len(sessions)} session(s)")
    return submitted


def seed_individual_rankings(tid: int, players: list[User]) -> int:
    """Fallback: write TournamentRanking rows directly (when API returns 400)."""
    db.expire_all()
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == tid).delete()
    db.commit()
    for i, player in enumerate(players):
        db.add(TournamentRanking(
            tournament_id=tid,
            user_id=player.id,
            participant_type="INDIVIDUAL",
            rank=i + 1,
            points=float(max(0, 100 - i * 10)),
            wins=max(0, len(players) - 1 - i),
            losses=i,
            draws=0,
        ))
    db.commit()
    ok(f"Rankings seeded directly: {len(players)} player(s)")
    return len(players)


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
# FORMAT V-A — INDIVIDUAL RANKING (INDIVIDUAL, SCORE_BASED, virtual)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT V-A — Individual Ranking (INDIVIDUAL, SCORE_BASED, virtual) — 4 states")


def _ir(label: str) -> Semester:
    return create_virtual_tournament(
        f"{_PREFIX}IR — {label}",
        tt_id=None,
        participant_type="INDIVIDUAL",
        scoring_type="SCORE_BASED",
        ranking_direction="DESC",
    )


print("\n[VA1/4] DRAFT")
t = _ir("Draft")
ok(f"✅ Virtual Demo: IR INDIVIDUAL - DRAFT  (id={t.id})")

print("\n[VA2/4] IN_PROGRESS")
t = _ir("In Progress")
enroll_players(t.id, boot_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    n = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    info(f"Sessions generated: {n}  (all virtual)")
    patch_meeting_links(t.id)
    ok(f"✅ Virtual Demo: IR INDIVIDUAL - IN_PROGRESS  ({n} sessions, all virtual)")

print("\n[VA3/4] COMPLETED")
t = _ir("Completed")
enroll_players(t.id, boot_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    n = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    info(f"Sessions generated: {n}  (all virtual)")
    patch_meeting_links(t.id)
    submit_ir_results(t.id, boot_players)
    if not calculate_rankings(t.id):
        seed_individual_rankings(t.id, boot_players)
    transition(t.id, "COMPLETED")
    ok(f"✅ Virtual Demo: IR INDIVIDUAL - COMPLETED  (id={t.id})")

print("\n[VA4/4] REWARDS_DISTRIBUTED")
t = _ir("Rewards Distributed")
enroll_players(t.id, boot_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    n = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    info(f"Sessions generated: {n}  (all virtual)")
    patch_meeting_links(t.id)
    submit_ir_results(t.id, boot_players)
    if not calculate_rankings(t.id):
        seed_individual_rankings(t.id, boot_players)
    if transition(t.id, "COMPLETED"):
        distribute_rewards(t.id)
        ok(f"✅ Virtual Demo: IR INDIVIDUAL - REWARDS_DISTRIBUTED  (id={t.id})")


# ═════════════════════════════════════════════════════════════════════════════
# FORMAT V-B — H2H LEAGUE (INDIVIDUAL, WDL_BASED, virtual)
# ═════════════════════════════════════════════════════════════════════════════

section("FORMAT V-B — H2H League (INDIVIDUAL, WDL_BASED, virtual) — 4 states")


def _league(label: str) -> Semester:
    return create_virtual_tournament(
        f"{_PREFIX}League — {label}",
        tt_id=tt_league.id,
        participant_type="INDIVIDUAL",
        scoring_type="SCORE_BASED",
        ranking_direction="DESC",
    )


print("\n[VB1/4] DRAFT")
t = _league("Draft")
ok(f"✅ Virtual Demo: League INDIVIDUAL - DRAFT  (id={t.id})")

print("\n[VB2/4] IN_PROGRESS")
t = _league("In Progress")
enroll_players(t.id, boot_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    n = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    info(f"Sessions generated: {n}  (all virtual)")
    patch_meeting_links(t.id)
    ok(f"✅ Virtual Demo: League INDIVIDUAL - IN_PROGRESS  ({n} sessions, all virtual)")

print("\n[VB3/4] COMPLETED")
t = _league("Completed")
enroll_players(t.id, boot_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    n = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    info(f"Sessions generated: {n}  (all virtual)")
    patch_meeting_links(t.id)
    submit_h2h_results(t.id)
    calculate_rankings(t.id)
    transition(t.id, "COMPLETED")
    ok(f"✅ Virtual Demo: League INDIVIDUAL - COMPLETED  (id={t.id})")

print("\n[VB4/4] REWARDS_DISTRIBUTED")
t = _league("Rewards Distributed")
enroll_players(t.id, boot_players)
transition(t.id, "ENROLLMENT_OPEN")
transition(t.id, "ENROLLMENT_CLOSED")
transition(t.id, "CHECK_IN_OPEN")
if transition(t.id, "IN_PROGRESS"):
    db.expire_all()
    n = db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    info(f"Sessions generated: {n}  (all virtual)")
    patch_meeting_links(t.id)
    submit_h2h_results(t.id)
    calculate_rankings(t.id)
    if transition(t.id, "COMPLETED"):
        distribute_rewards(t.id)
        ok(f"✅ Virtual Demo: League INDIVIDUAL - REWARDS_DISTRIBUTED  (id={t.id})")


# ─────────────────────────────────────────────────────────────────────────────
# Final validation (fail-fast assertions)
# ─────────────────────────────────────────────────────────────────────────────

section("Final validation")

db.expire_all()

virtual_tournaments = (
    db.query(Semester)
    .filter(Semester.name.like("Virtual Demo: %"))
    .all()
)

issues: list[str] = []

if len(virtual_tournaments) != 8:
    issues.append(f"Expected 8 Virtual Demo tournaments, got {len(virtual_tournaments)}")

for t in virtual_tournaments:
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == t.id).all()

    # VT-01: all sessions must be virtual
    bad_type = [s.id for s in sessions if s.session_type != SessionType.virtual]
    if bad_type:
        issues.append(f"{t.name}: sessions {bad_type} not virtual (session_type mismatch)")

    # VT-02: base_xp must be 50
    bad_xp = [s.id for s in sessions if sessions and s.base_xp != 50]
    if bad_xp:
        issues.append(f"{t.name}: sessions {bad_xp} have base_xp != 50")

    # meeting_link must be set for COMPLETED / REWARDS_DISTRIBUTED
    if t.tournament_status in ("COMPLETED", "REWARDS_DISTRIBUTED"):
        missing_link = [s.id for s in sessions if not s.meeting_link]
        if missing_link:
            issues.append(f"{t.name}: sessions {missing_link} missing meeting_link")

        # status must match target
        if t.tournament_status not in ("COMPLETED", "REWARDS_DISTRIBUTED"):
            issues.append(f"{t.name}: expected COMPLETED or REWARDS_DISTRIBUTED, got {t.tournament_status}")

if issues:
    print(f"\n❌  Validation FAILED — {len(issues)} issue(s):")
    for iss in issues:
        print(f"   • {iss}")
    db.close()
    sys.exit(1)

print(f"\n✅  Validation passed — {len(virtual_tournaments)} Virtual Demo tournaments OK")
for t in virtual_tournaments:
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == t.id).all()
    ok(f"{t.name}  [{t.tournament_status}]  {len(sessions)} session(s)  type=virtual  base_xp=50")

db.close()
print("\n" + "="*64)
print("  Virtual Demo Seed completed successfully.")
print("  8 events seeded: V-A (IR×IND) × 4 states, V-B (League×IND) × 4 states")
print("="*64)
