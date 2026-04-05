"""
Skill Delta Demo Seed
=====================
Creates 16 fresh players and 4 Individual Ranking tournaments with a
cyclic rotation design that guarantees every player has both positive
and negative skill deltas across the 4 events.

Design
------
  16 players split into 4 groups of 4 (G1–G4).
  4 tournaments, each with a different group winning (ranks 1–4)
  and a different group losing (ranks 13–16):

    Cup #1: G1 wins  / G4 loses
    Cup #2: G2 wins  / G1 loses
    Cup #3: G3 wins  / G2 loses
    Cup #4: G4 wins  / G3 loses

  Outcome per player: exactly 1 win round (ranks 1–4, strong +)
  and exactly 1 loss round (ranks 13–16, strong −) → guaranteed
  both positive AND negative skill delta for every player.

Skill delta formula (V3 EMA, baseline 65.0, 16 players):
  Rank  1 → +7 pt   Rank  4 → +5 pt
  Rank  9 → +1 pt   Rank 10 → −0.2 pt
  Rank 13 → −3 pt   Rank 16 → −5 pt

Prerequisites
-------------
    PYTHONPATH=. python scripts/bootstrap_clean.py

Usage
-----
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \\
        SECRET_KEY="..." PYTHONPATH=. python scripts/seed_skill_delta_demo.py
"""
import os
import sys
import uuid
from datetime import date, datetime, timezone

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
from app.models.tournament_achievement import TournamentParticipation
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_reward_config import TournamentRewardConfig
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

def ok(msg):    print(f"  ✅  {msg}")
def info(msg):  print(f"       {msg}")
def err(msg):   print(f"  ❌  {msg}")
def section(t): print(f"\n{'═' * 64}\n  {t}\n{'═' * 64}")


# ─────────────────────────────────────────────────────────────────────────────
# Rotation design
# ─────────────────────────────────────────────────────────────────────────────

# ROTATION[cup_idx] = [win_group, 2nd_group, 3rd_group, lose_group]
ROTATION = [
    [0, 1, 2, 3],   # Cup #1: G1 wins,  G4 loses
    [1, 2, 3, 0],   # Cup #2: G2 wins,  G1 loses
    [2, 3, 0, 1],   # Cup #3: G3 wins,  G2 loses
    [3, 0, 1, 2],   # Cup #4: G4 wins,  G3 loses
]

# Scores for ranks 1–16 (higher score → higher rank, ranking_direction="DESC")
SCORES = [
    1600, 1500, 1400, 1300,   # rank  1– 4  strong  +
    1200, 1100, 1000,  900,   # rank  5– 8  moderate +
     800,  700,  600,  500,   # rank  9–12  mild    −
     400,  300,  200,  100,   # rank 13–16  strong  −
]

# 16 player names
_PLAYER_NAMES = [
    ("Alpha",    "Archer"),   ("Beta",     "Baker"),
    ("Gamma",    "Cole"),     ("Delta",    "Dean"),
    ("Echo",     "Evans"),    ("Foxtrot",  "Ford"),
    ("Golf",     "Grant"),    ("Hotel",    "Hall"),
    ("India",    "Irving"),   ("Juliet",   "Jones"),
    ("Kilo",     "King"),     ("Lima",     "Lee"),
    ("Mike",     "Morris"),   ("November", "Nash"),
    ("Oscar",    "Owen"),     ("Papa",     "Price"),
]

_SKILL_BASELINE = 65.0
_CUP_NAME_PREFIX = "Skill Delta Cup"
_EMAIL_DOMAIN = "@skill-delta.local"
_CLUB_CODE = "SDC-DEMO"
_CLUB_NAME = "Skill Delta Demo Club"

_REWARD_CONFIG = {
    "skill_mappings": [
        {"skill": "ball_control", "weight": 1.2, "category": "TECHNICAL", "enabled": True},
        {"skill": "passing",      "weight": 1.0, "category": "TECHNICAL", "enabled": True},
        {"skill": "finishing",    "weight": 1.0, "category": "TECHNICAL", "enabled": True},
        {"skill": "sprint_speed", "weight": 0.8, "category": "PHYSICAL",  "enabled": True},
        {"skill": "stamina",      "weight": 0.8, "category": "PHYSICAL",  "enabled": True},
    ],
    "first_place":   {"xp": 500, "credits": 100},
    "second_place":  {"xp": 300, "credits":  50},
    "third_place":   {"xp": 200, "credits":  25},
    "participation": {"xp":  50, "credits":   0},
}


# ─────────────────────────────────────────────────────────────────────────────
# DB + auth setup
# ─────────────────────────────────────────────────────────────────────────────

db = SessionLocal()

admin = db.query(User).filter(User.email == "admin@lfa.com").first()
if not admin:
    print("❌  admin@lfa.com not found — run bootstrap_clean.py first")
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

app.dependency_overrides[get_current_user_web] = lambda: admin
app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin
app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = lambda: admin

client = TestClient(app, follow_redirects=False)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex[:6]


def transition(tid: int, new_status: str) -> bool:
    r = client.patch(
        f"/api/v1/tournaments/{tid}/status",
        json={"new_status": new_status, "reason": "skill-delta-seed"},
    )
    if r.status_code != 200:
        err(f"Transition → {new_status} failed: {r.status_code} {r.text[:200]}")
        return False
    db.expire_all()
    ok(f"→ {new_status}")
    return True


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
        t = db.query(Semester).filter(Semester.id == tid).first()
        ok(f"Rewards distributed → status: {t.tournament_status}")
        return True
    err(f"Rewards failed: {r.status_code} {r.text[:150]}")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Cleanup: delete previous seed data (idempotent)
# ─────────────────────────────────────────────────────────────────────────────

section("Cleanup — removing previous Skill Delta seed data")

_cup_ids = [
    row[0] for row in db.execute(
        _sql(f"SELECT id FROM semesters WHERE name LIKE '{_CUP_NAME_PREFIX}%'")
    ).fetchall()
]
if _cup_ids:
    print(f"  🧹  Found {len(_cup_ids)} previous cup(s) — deleting...")
    id_list = ", ".join(str(i) for i in _cup_ids)
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
    for extra_tbl, col in [
        ("tournament_status_history", "tournament_id"),
        ("notifications", "related_semester_id"),
    ]:
        try:
            db.execute(_sql(f"DELETE FROM {extra_tbl} WHERE {col} IN ({id_list})"))
        except Exception:
            db.rollback()
    db.execute(_sql(f"DELETE FROM semesters WHERE id IN ({id_list})"))
    db.commit()
    ok(f"Deleted {len(_cup_ids)} cup tournament(s)")
else:
    ok("No previous cups found")

_old_user_ids = [
    row[0] for row in db.execute(
        _sql(f"SELECT id FROM users WHERE email LIKE '%{_EMAIL_DOMAIN}'")
    ).fetchall()
]
if _old_user_ids:
    uid_list = ", ".join(str(i) for i in _old_user_ids)
    try:
        db.execute(_sql(f"DELETE FROM user_licenses WHERE user_id IN ({uid_list})"))
    except Exception:
        db.rollback()
    db.execute(_sql(f"DELETE FROM users WHERE id IN ({uid_list})"))
    db.commit()
    ok(f"Deleted {len(_old_user_ids)} previous seed player(s)")
else:
    ok("No previous seed players found")


# ─────────────────────────────────────────────────────────────────────────────
# Create club + 16 players
# ─────────────────────────────────────────────────────────────────────────────

section(f"Creating {_CLUB_NAME} + 16 players")

all_skill_keys = get_all_skill_keys()
now = datetime.now(timezone.utc)
football_skills_initial = {k: _SKILL_BASELINE for k in all_skill_keys}

# Find-or-create club
seed_club = db.query(Club).filter(Club.code == _CLUB_CODE).first()
if not seed_club:
    seed_club = Club(
        name=_CLUB_NAME,
        code=_CLUB_CODE,
        city="Budapest",
        country="HU",
        contact_email="skill-delta@lfa.com",
        is_active=True,
    )
    db.add(seed_club)
    db.flush()
    ok(f"Club created (id={seed_club.id})")
else:
    ok(f"Club already exists (id={seed_club.id})")

players: list[User] = []
player_licenses: dict[int, int] = {}  # user_id → license_id

for idx, (first, last) in enumerate(_PLAYER_NAMES):
    num = idx + 1
    email = f"sdemo-{num:02d}{_EMAIL_DOMAIN}"
    user = User(
        name=f"{first} {last}",
        first_name=first,
        last_name=last,
        nickname=first.lower(),
        email=email,
        password_hash=get_password_hash("SkillDelta#1234"),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,
        credit_balance=1000,
        date_of_birth=date(2005, 1, num),
        nationality="Hungarian",
        gender="Male",
        phone=f"+36 70 {num:07d}",
        street_address=f"{num} Skill Street",
        city="Budapest",
        postal_code="1011",
        country="Hungary",
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
        football_skills=football_skills_initial.copy(),
        motivation_scores={
            "position": "MIDFIELDER",
            "goals": "improve_skills",
            "motivation": "competitive",
            "average_skill_level": _SKILL_BASELINE,
            "onboarding_completed_at": now.isoformat(),
        },
        average_motivation_score=_SKILL_BASELINE,
    )
    db.add(lic)
    db.flush()
    player_licenses[user.id] = lic.id
    players.append(user)

db.commit()
db.expire_all()
ok(f"Created {len(players)} players (sdemo-01 … sdemo-16{_EMAIL_DOMAIN})")

# Reload license IDs after commit
player_licenses = {}
for p in players:
    lic = db.query(UserLicense).filter(
        UserLicense.user_id == p.id,
        UserLicense.is_active == True,
    ).first()
    player_licenses[p.id] = lic.id

# Groups of 4
GROUPS: list[list[User]] = [
    players[0:4],    # G1: sdemo-01..04
    players[4:8],    # G2: sdemo-05..08
    players[8:12],   # G3: sdemo-09..12
    players[12:16],  # G4: sdemo-13..16
]

info("Groups:")
for gi, g in enumerate(GROUPS):
    info(f"  G{gi+1}: {', '.join(p.first_name for p in g)}")


# ─────────────────────────────────────────────────────────────────────────────
# Seed 4 tournaments
# ─────────────────────────────────────────────────────────────────────────────

cup_tournament_ids: list[int] = []

for cup_idx in range(4):
    cup_num = cup_idx + 1
    cup_name = f"{_CUP_NAME_PREFIX} #{cup_num}"
    section(f"Cup #{cup_num} — {cup_name}")

    rotation = ROTATION[cup_idx]
    win_grp  = rotation[0]
    lose_grp = rotation[3]
    info(f"Rotation: G{win_grp+1} wins (R1–4), G{lose_grp+1} loses (R13–16)")

    # ── a) Create tournament ────────────────────────────────────────────────
    t = Semester(
        name=cup_name,
        code=f"SDC-{cup_num:02d}-{_uid()}",
        master_instructor_id=admin.id,
        campus_id=campus.id,
        location_id=campus.location_id,
        start_date=date(2026, 9, cup_num),
        end_date=date(2026, 9, cup_num),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status="DRAFT",
    )
    db.add(t)
    db.flush()
    db.add(TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=None,          # None → Individual Ranking format
        participant_type="INDIVIDUAL",
        max_players=64,
        number_of_rounds=1,
        parallel_fields=1,
        ranking_direction="DESC",
        scoring_type="SCORE_BASED",
    ))
    db.add(GameConfiguration(semester_id=t.id, game_preset_id=preset.id))
    db.add(TournamentRewardConfig(
        semester_id=t.id,
        reward_policy_name="Skill Delta Demo",
        reward_config=_REWARD_CONFIG,
    ))
    db.commit()
    db.expire_all()
    ok(f"Created tournament id={t.id}")
    cup_tournament_ids.append(t.id)

    # ── b) ENROLLMENT_OPEN ──────────────────────────────────────────────────
    if not transition(t.id, "ENROLLMENT_OPEN"):
        sys.exit(1)

    # ── c) Enroll all 16 players (DB direct) ────────────────────────────────
    for p in players:
        db.add(SemesterEnrollment(
            semester_id=t.id,
            user_id=p.id,
            user_license_id=player_licenses[p.id],
            is_active=True,
            request_status=EnrollmentStatus.APPROVED,
        ))
    db.commit()
    info(f"Enrolled {len(players)} players")

    # ── d) Lifecycle: ENROLLMENT_CLOSED → CHECK_IN_OPEN → IN_PROGRESS ──────
    for status in ("ENROLLMENT_CLOSED", "CHECK_IN_OPEN", "IN_PROGRESS"):
        if not transition(t.id, status):
            sys.exit(1)

    # ── e) Get generated sessions ────────────────────────────────────────────
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == t.id).all()
    if not sessions:
        err(f"No sessions generated for cup #{cup_num}")
        sys.exit(1)
    info(f"Sessions generated: {len(sessions)}")

    # ── f) Build result list from rotation ───────────────────────────────────
    ordered_players: list[User] = []
    for grp_idx in rotation:
        ordered_players.extend(GROUPS[grp_idx])

    results = [
        {"user_id": p.id, "score": float(SCORES[i]), "rank": i + 1}
        for i, p in enumerate(ordered_players)
    ]

    info("Rank assignments (G=group, score, expected delta direction):")
    for i, p in enumerate(ordered_players):
        grp_num = next(gi + 1 for gi, g in enumerate(GROUPS) if p in g)
        sign = "++" if i < 4 else ("+" if i < 8 else ("~−" if i < 12 else "−−"))
        info(f"  Rank {i+1:2d} {sign}  {p.name:<20} (G{grp_num})  score={SCORES[i]}")

    # Submit results to all sessions (normally 1 for number_of_rounds=1)
    for sess in sessions:
        r = client.patch(
            f"/api/v1/sessions/{sess.id}/results",
            json={"results": results},
        )
        if r.status_code not in (200, 201):
            err(f"Results session {sess.id}: {r.status_code} {r.text[:200]}")
            sys.exit(1)
    ok(f"Results submitted ({len(sessions)} session(s))")

    # ── g) Rankings + COMPLETED + Rewards ───────────────────────────────────
    if not calculate_rankings(t.id):
        sys.exit(1)
    if not transition(t.id, "COMPLETED"):
        sys.exit(1)
    if not distribute_rewards(t.id):
        sys.exit(1)

ok(f"All 4 cups seeded: {cup_tournament_ids}")


# ─────────────────────────────────────────────────────────────────────────────
# Summary table
# ─────────────────────────────────────────────────────────────────────────────

section("SKILL DELTA DEMO — ÖSSZEFOGLALÓ")

db.expire_all()

col_w = 16
header = f"{'Játékos':<22} │"
for cn in range(1, 5):
    header += f" {'Cup #' + str(cn):^{col_w}} │"
header += f" {'ball_control':^22}"
print()
print(header)
print("─" * 22 + "─┼─" + "─┼─".join(["─" * col_w] * 4) + "─┼─" + "─" * 22)

all_guarantee_ok = True

for p in players:
    grp_num = next(gi + 1 for gi, g in enumerate(GROUPS) if p in g)
    cells: list[str] = []
    has_pos = has_neg = False

    for cup_tid in cup_tournament_ids:
        tp = db.query(TournamentParticipation).filter(
            TournamentParticipation.user_id == p.id,
            TournamentParticipation.semester_id == cup_tid,
        ).first()
        if tp and tp.skill_rating_delta and "ball_control" in (tp.skill_rating_delta or {}):
            d = tp.skill_rating_delta["ball_control"]
            cells.append(f"R{tp.placement:2d} {d:+.1f}")
            if d > 0:
                has_pos = True
            elif d < 0:
                has_neg = True
        else:
            cells.append("  n/a  ")

    # Net from license
    lic = db.query(UserLicense).filter(
        UserLicense.user_id == p.id,
        UserLicense.is_active == True,
    ).first()
    net_str = "n/a"
    if lic and lic.football_skills:
        fs = lic.football_skills.get("ball_control")
        if isinstance(fs, dict):
            curr = fs.get("current_level", _SKILL_BASELINE)
            net_str = f"{curr:.1f} ({curr - _SKILL_BASELINE:+.1f})"
        elif fs is not None:
            net_str = f"{float(fs):.1f}"

    guarantee = "✓" if (has_pos and has_neg) else "✗"
    row = f"{p.name:<18} G{grp_num} {guarantee} │"
    for cell in cells:
        row += f" {cell:^{col_w}} │"
    row += f" {net_str:^22}"
    print(row)

    if not (has_pos and has_neg):
        all_guarantee_ok = False


# ─────────────────────────────────────────────────────────────────────────────
# Final guarantee check
# ─────────────────────────────────────────────────────────────────────────────

print()
if all_guarantee_ok:
    ok("GARANCIA TELJESÍTVE: minden játékosnak van pozitív ÉS negatív skill delta ✓")
else:
    err("GARANCIA MEGSÉRTVE — ellenőrizd a rotation logikát vagy a skill delta küszöböt")
    sys.exit(1)

print(f"\n{'═' * 64}")
print(f"  Seed kész.")
print(f"  Club   : {_CLUB_NAME}  ({_CLUB_CODE})")
print(f"  Players: sdemo-01 … sdemo-16{_EMAIL_DOMAIN}")
print(f"  Cups   : {cup_tournament_ids}")
print(f"{'═' * 64}\n")
