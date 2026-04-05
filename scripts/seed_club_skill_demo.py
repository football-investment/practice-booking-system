"""
Club Skill Demo Seed
====================
Skill delta validáció bootstrap játékosokkal — VALÓS club use-case szimuláció.

NEM hoz létre új játékosokat.  A meglévő LFA_BOOTSTRAP_CLUB (LFA-BOOT) 36
játékosát használja:
  • 3 × IR (Individual Ranking) event — LFA U15, outfield_default preset
  • 1 × H2H League (TEAM) event     — mind 3 bootstrap csapat, passing_focus preset

IR rotáció (3 csoport × 3 cup):
  G1 = U15 players[0:4]   Cup1: Győz (R1–4)   Cup2: Veszít (R9–12)  Cup3: Közepes (R5–8)
  G2 = U15 players[4:8]   Cup1: Közepes(R5–8)  Cup2: Győz (R1–4)    Cup3: Veszít (R9–12)
  G3 = U15 players[8:12]  Cup1: Veszít(R9–12)  Cup2: Közepes(R5–8)  Cup3: Győz (R1–4)

H2H eredmény: LFA U15 > LFA U18 > LFA Adult (1. / 2. / 3.)

Garancia (IR): minden U15 játékosnak ≥1 erős győzelem ÉS ≥1 erős vereség.

Előfeltétel:
    PYTHONPATH=. python scripts/bootstrap_clean.py

Futtatás:
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \\
        SECRET_KEY="..." PYTHONPATH=. python scripts/seed_club_skill_demo.py
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
from app.models.campus import Campus
from app.models.club import Club
from app.models.game_configuration import GameConfiguration
from app.models.game_preset import GamePreset
from app.models.license import UserLicense
from app.models.semester import Semester, SemesterCategory, SemesterStatus
from app.models.semester_enrollment import EnrollmentStatus, SemesterEnrollment
from app.models.session import Session as SessionModel
from app.models.team import Team, TeamMember, TournamentTeamEnrollment
from app.models.tournament_achievement import TournamentParticipation
from app.models.tournament_configuration import TournamentConfiguration
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

def ok(msg):    print(f"  ✅  {msg}")
def info(msg):  print(f"       {msg}")
def err(msg):   print(f"  ❌  {msg}")
def section(t): print(f"\n{'═' * 64}\n  {t}\n{'═' * 64}")


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

_SEED_PREFIX     = "Club Skill Demo"
_IR_PRESET_CODE  = "outfield_default"
_H2H_PRESET_CODE = "passing_focus"

# 3-group rotation: ROTATION[cup_idx][pos] = group_index
# pos 0 = win (ranks 1–4), pos 1 = middle (ranks 5–8), pos 2 = lose (ranks 9–12)
ROTATION = [
    [0, 1, 2],   # Cup1: G1 wins,  G2 middle, G3 loses
    [1, 2, 0],   # Cup2: G2 wins,  G3 middle, G1 loses
    [2, 0, 1],   # Cup3: G3 wins,  G1 middle, G2 loses
]

# Scores (DESC ranking: higher score → better rank)
SCORES = [1200, 1100, 1000, 900,   # rank  1– 4  strong  +
           800,  700,  600, 500,   # rank  5– 8  mild   +/−
           400,  300,  200, 100]   # rank  9–12  strong  −

_IR_REWARD_CONFIG = {
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
    "first_place":   {"xp": 500, "credits": 100},
    "second_place":  {"xp": 300, "credits":  50},
    "third_place":   {"xp": 200, "credits":  25},
    "participation": {"xp":  50, "credits":   0},
}

_H2H_REWARD_CONFIG = {
    "skill_mappings": [
        {"skill": "passing",        "weight": 1.8, "category": "TECHNICAL", "enabled": True},
        {"skill": "vision",         "weight": 1.6, "category": "TECHNICAL", "enabled": True},
        {"skill": "ball_control",   "weight": 1.4, "category": "TECHNICAL", "enabled": True},
        {"skill": "positioning_off","weight": 1.3, "category": "TECHNICAL", "enabled": True},
        {"skill": "agility",        "weight": 1.0, "category": "PHYSICAL",  "enabled": True},
        {"skill": "stamina",        "weight": 0.8, "category": "PHYSICAL",  "enabled": True},
    ],
    "first_place":   {"xp": 600, "credits": 120},
    "second_place":  {"xp": 350, "credits":  60},
    "third_place":   {"xp": 150, "credits":  20},
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

ir_preset = db.query(GamePreset).filter(GamePreset.code == _IR_PRESET_CODE).first()
if not ir_preset:
    print(f"❌  GamePreset '{_IR_PRESET_CODE}' not found — run bootstrap_clean.py first")
    sys.exit(1)

h2h_preset = db.query(GamePreset).filter(GamePreset.code == _H2H_PRESET_CODE).first()
if not h2h_preset:
    print(f"❌  GamePreset '{_H2H_PRESET_CODE}' not found — run bootstrap_clean.py first")
    sys.exit(1)

boot_club = db.query(Club).filter(Club.code == "LFA-BOOT").first()
if not boot_club:
    print("❌  LFA-BOOT club not found — run bootstrap_clean.py first")
    sys.exit(1)

# Bootstrap teams — filter by explicit name to avoid stale duplicates
boot_teams = db.query(Team).filter(
    Team.club_id == boot_club.id,
    Team.name.in_(["LFA U15", "LFA U18", "LFA Adult"]),
).order_by(Team.name).all()   # alphabetical: Adult / U15 / U18
if len(boot_teams) != 3:
    print(f"❌  Expected 3 named bootstrap teams, found {len(boot_teams)} — run bootstrap_clean.py first")
    sys.exit(1)

# Identify teams by name
_team_by_name = {t.name: t for t in boot_teams}
team_u15   = _team_by_name["LFA U15"]
team_u18   = _team_by_name["LFA U18"]
team_adult = _team_by_name["LFA Adult"]

# U15 players (12) — stable order by user id
u15_players: list[User] = (
    db.query(User)
    .join(TeamMember, TeamMember.user_id == User.id)
    .filter(TeamMember.team_id == team_u15.id)
    .order_by(User.id)
    .all()
)
if len(u15_players) != 12:
    print(f"❌  Expected 12 LFA U15 players, found {len(u15_players)} — run bootstrap_clean.py first")
    sys.exit(1)

tt_league = db.query(TournamentType).filter(TournamentType.code == "league").first()
if not tt_league:
    print("❌  TournamentType 'league' not found — run bootstrap_clean.py first")
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
        json={"new_status": new_status, "reason": "club-skill-demo-seed"},
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
# Cleanup — idempotent (only semesters, bootstrap players untouched)
# ─────────────────────────────────────────────────────────────────────────────

section(f"Cleanup — removing previous '{_SEED_PREFIX}' seed data")

_old_ids = [
    row[0] for row in db.execute(
        _sql(f"SELECT id FROM semesters WHERE name LIKE '{_SEED_PREFIX}%'")
    ).fetchall()
]

if _old_ids:
    id_list = ", ".join(str(i) for i in _old_ids)
    print(f"  🧹  Found {len(_old_ids)} previous semester(s) — deleting...")
    for tbl in [
        "tournament_reward_configs", "tournament_configurations",
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
        ("notifications",             "related_semester_id"),
    ]:
        try:
            db.execute(_sql(f"DELETE FROM {extra_tbl} WHERE {col} IN ({id_list})"))
        except Exception:
            db.rollback()
    db.execute(_sql(f"DELETE FROM semesters WHERE id IN ({id_list})"))
    db.commit()
    ok(f"Deleted {len(_old_ids)} previous semester(s)")
else:
    ok("No previous seed semesters found")


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap info
# ─────────────────────────────────────────────────────────────────────────────

section("Bootstrap state")
ok(f"Club : {boot_club.name} ({boot_club.code})")
ok(f"Teams: U15 id={team_u15.id} / U18 id={team_u18.id} / Adult id={team_adult.id}")
ok(f"U15 players ({len(u15_players)}): {', '.join(p.first_name for p in u15_players)}")
ok(f"Preset IR : {ir_preset.name} ({ir_preset.code})")
ok(f"Preset H2H: {h2h_preset.name} ({h2h_preset.code})")

# Build license map for U15 players
u15_license: dict[int, int] = {}   # user_id → license_id
for p in u15_players:
    lic = db.query(UserLicense).filter(
        UserLicense.user_id == p.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
        UserLicense.is_active == True,
    ).first()
    if not lic:
        err(f"No active LFA license for {p.email} — re-run bootstrap_clean.py")
        sys.exit(1)
    u15_license[p.id] = lic.id

# 3 groups of 4
GROUPS: list[list[User]] = [
    u15_players[0:4],
    u15_players[4:8],
    u15_players[8:12],
]
info(f"IR groups:")
for gi, g in enumerate(GROUPS):
    info(f"  G{gi+1}: {', '.join(p.first_name for p in g)}")


# ─────────────────────────────────────────────────────────────────────────────
# Part A: 3 × IR events (U15 players, outfield_default)
# ─────────────────────────────────────────────────────────────────────────────

ir_tournament_ids: list[int] = []

for cup_idx in range(3):
    cup_num = cup_idx + 1
    cup_name = f"{_SEED_PREFIX}: U15 Cup #{cup_num}"
    section(f"IR Cup #{cup_num} — {cup_name}")

    rotation = ROTATION[cup_idx]
    win_grp  = rotation[0]
    lose_grp = rotation[2]
    info(f"Rotation: G{win_grp+1} wins (R1–4), G{rotation[1]+1} middle (R5–8), G{lose_grp+1} loses (R9–12)")

    # a) Create tournament
    t = Semester(
        name=cup_name,
        code=f"CSD-IR{cup_num}-{_uid()}",
        master_instructor_id=admin.id,
        campus_id=campus.id,
        location_id=campus.location_id,
        start_date=date(2026, 10, cup_num),
        end_date=date(2026, 10, cup_num),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status="DRAFT",
    )
    db.add(t)
    db.flush()
    db.add(TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=None,        # None → Individual Ranking format
        participant_type="INDIVIDUAL",
        max_players=16,
        number_of_rounds=1,
        parallel_fields=1,
        ranking_direction="DESC",
        scoring_type="SCORE_BASED",
    ))
    db.add(GameConfiguration(semester_id=t.id, game_preset_id=ir_preset.id))
    db.add(TournamentRewardConfig(
        semester_id=t.id,
        reward_policy_name="Club Skill Demo IR",
        reward_config=_IR_REWARD_CONFIG,
    ))
    db.commit()
    db.expire_all()
    ok(f"Created tournament id={t.id}")
    ir_tournament_ids.append(t.id)

    # b) ENROLLMENT_OPEN
    if not transition(t.id, "ENROLLMENT_OPEN"):
        sys.exit(1)

    # c) Enroll all 12 U15 players
    for p in u15_players:
        db.add(SemesterEnrollment(
            semester_id=t.id,
            user_id=p.id,
            user_license_id=u15_license[p.id],
            is_active=True,
            request_status=EnrollmentStatus.APPROVED,
        ))
    db.commit()
    info(f"Enrolled {len(u15_players)} U15 players")

    # d) Lifecycle
    for status in ("ENROLLMENT_CLOSED", "CHECK_IN_OPEN", "IN_PROGRESS"):
        if not transition(t.id, status):
            sys.exit(1)

    # e) Get generated sessions
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == t.id).all()
    if not sessions:
        err(f"No sessions generated for cup #{cup_num}")
        sys.exit(1)
    info(f"Sessions generated: {len(sessions)}")

    # f) Build ordered player list from rotation
    ordered: list[User] = []
    for grp_idx in rotation:          # pos 0=win, 1=mid, 2=lose
        ordered.extend(GROUPS[grp_idx])

    results = [
        {"user_id": p.id, "score": float(SCORES[i]), "rank": i + 1}
        for i, p in enumerate(ordered)
    ]

    info("Rank assignments:")
    for i, p in enumerate(ordered):
        grp_num = next(gi + 1 for gi, g in enumerate(GROUPS) if p in g)
        sign = "++" if i < 4 else ("+" if i < 8 else "−−")
        info(f"  R{i+1:2d} {sign}  {p.first_name:<12} (G{grp_num})  score={SCORES[i]}")

    for sess in sessions:
        r = client.patch(
            f"/api/v1/sessions/{sess.id}/results",
            json={"results": results},
        )
        if r.status_code not in (200, 201):
            err(f"Results session {sess.id}: {r.status_code} {r.text[:200]}")
            sys.exit(1)
    ok(f"Results submitted ({len(sessions)} session(s))")

    # g) Rankings + complete + rewards
    if not calculate_rankings(t.id):
        sys.exit(1)
    if not transition(t.id, "COMPLETED"):
        sys.exit(1)
    if not distribute_rewards(t.id):
        sys.exit(1)

ok(f"All 3 IR cups seeded: {ir_tournament_ids}")


# ─────────────────────────────────────────────────────────────────────────────
# Part B: 1 × H2H League (3 bootstrap teams, passing_focus)
# ─────────────────────────────────────────────────────────────────────────────

section(f"H2H League — {_SEED_PREFIX}: H2H League 2026")

h2h_name = f"{_SEED_PREFIX}: H2H League 2026"

t_h2h = Semester(
    name=h2h_name,
    code=f"CSD-H2H-{_uid()}",
    master_instructor_id=admin.id,
    campus_id=campus.id,
    location_id=campus.location_id,
    start_date=date(2026, 11, 1),
    end_date=date(2026, 11, 3),
    status=SemesterStatus.ONGOING,
    semester_category=SemesterCategory.TOURNAMENT,
    tournament_status="DRAFT",
)
db.add(t_h2h)
db.flush()
db.add(TournamentConfiguration(
    semester_id=t_h2h.id,
    tournament_type_id=tt_league.id,
    participant_type="TEAM",
    max_players=6,
    number_of_rounds=1,
    parallel_fields=1,
    ranking_direction="DESC",
    scoring_type="SCORE_BASED",
))
db.add(GameConfiguration(semester_id=t_h2h.id, game_preset_id=h2h_preset.id))
db.add(TournamentRewardConfig(
    semester_id=t_h2h.id,
    reward_policy_name="Club Skill Demo H2H",
    reward_config=_H2H_REWARD_CONFIG,
))
db.commit()
db.expire_all()
ok(f"Created H2H tournament id={t_h2h.id}")

# Enroll all 3 teams
for team in boot_teams:
    db.add(TournamentTeamEnrollment(
        semester_id=t_h2h.id,
        team_id=team.id,
        is_active=True,
        payment_verified=True,
    ))
db.commit()
info(f"Enrolled 3 teams: {', '.join(t.name for t in boot_teams)}")

# Lifecycle
for status in ("ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", "CHECK_IN_OPEN"):
    if not transition(t_h2h.id, status):
        sys.exit(1)

if not transition(t_h2h.id, "IN_PROGRESS"):
    sys.exit(1)

db.expire_all()
h2h_sessions = db.query(SessionModel).filter(SessionModel.semester_id == t_h2h.id).all()
if not h2h_sessions:
    err("No H2H sessions generated")
    sys.exit(1)
info(f"H2H sessions generated: {len(h2h_sessions)}")

# Submit results: U15 always wins; U18 beats Adult
_team_id_to_name = {
    team_u15.id:   "LFA U15",
    team_u18.id:   "LFA U18",
    team_adult.id: "LFA Adult",
}

def _h2h_winner(id_a: int, id_b: int):
    """Return (winner_id, loser_id) for the U15>U18>Adult hierarchy."""
    rank = {team_u15.id: 1, team_u18.id: 2, team_adult.id: 3}
    if rank.get(id_a, 9) < rank.get(id_b, 9):
        return id_a, id_b
    return id_b, id_a

submitted = 0
for sess in h2h_sessions:
    pids = list(sess.participant_team_ids or [])
    if len(pids) < 2:
        continue
    winner_id, loser_id = _h2h_winner(pids[0], pids[1])
    results = [
        {"team_id": winner_id, "score": 3},
        {"team_id": loser_id,  "score": 1},
    ]
    w_name = _team_id_to_name.get(winner_id, str(winner_id))
    l_name = _team_id_to_name.get(loser_id,  str(loser_id))
    r = client.patch(
        f"/api/v1/sessions/{sess.id}/team-results",
        json={"results": results, "round_number": 1},
    )
    if r.status_code in (200, 201):
        info(f"  Session {sess.id}: {w_name} 3–1 {l_name}  ✓")
        submitted += 1
    else:
        err(f"  Session {sess.id}: {r.status_code} {r.text[:150]}")

ok(f"H2H results submitted: {submitted}/{len(h2h_sessions)} session(s)")

if not calculate_rankings(t_h2h.id):
    sys.exit(1)
if not transition(t_h2h.id, "COMPLETED"):
    sys.exit(1)
if not distribute_rewards(t_h2h.id):
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

section("CLUB SKILL DEMO — ÖSSZEFOGLALÓ")

db.expire_all()

# ── IR events: U15 players ──────────────────────────────────────────────────
print()
print(f"IR Events — LFA U15 ({len(u15_players)} játékos, outfield_default preset)")
print()

col_w = 14
header = f"{'Játékos':<22} │"
for cn in range(1, 4):
    header += f" {'Cup #' + str(cn):^{col_w}} │"
header += f" {'ball_control (nettó)':^24}"
print(header)
print("─" * 22 + "─┼─" + "─┼─".join(["─" * col_w] * 3) + "─┼─" + "─" * 24)

all_ir_guarantee_ok = True

for p in u15_players:
    grp_num = next(gi + 1 for gi, g in enumerate(GROUPS) if p in g)
    cells: list[str] = []
    has_pos = has_neg = False

    for cup_tid in ir_tournament_ids:
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

    lic = db.query(UserLicense).filter(
        UserLicense.user_id == p.id,
        UserLicense.is_active == True,
    ).first()
    net_str = "n/a"
    if lic and lic.football_skills:
        fs = lic.football_skills.get("ball_control")
        if isinstance(fs, dict):
            curr = fs.get("current_level", 63.0)
            net_str = f"{curr:.1f} ({curr - 63.0:+.1f})"
        elif fs is not None:
            net_str = f"{float(fs):.1f}"

    guarantee = "✓" if (has_pos and has_neg) else "✗"
    row = f"{p.first_name} {p.last_name:<14} G{grp_num} {guarantee} │"
    for cell in cells:
        row += f" {cell:^{col_w}} │"
    row += f" {net_str:^24}"
    print(row)

    if not (has_pos and has_neg):
        all_ir_guarantee_ok = False

# ── H2H event: per-team summary ──────────────────────────────────────────────
print()
print(f"H2H League — 3 bootstrap csapat (passing_focus preset)")
print()
print(f"{'Csapat':<14} │ {'Hely':^6} │ {'passing delta (per játékos)':^30}")
print("─" * 14 + "─┼─" + "─" * 6 + "─┼─" + "─" * 30)

for team in [team_u15, team_u18, team_adult]:
    team_players = (
        db.query(User)
        .join(TeamMember, TeamMember.user_id == User.id)
        .filter(TeamMember.team_id == team.id)
        .order_by(User.id)
        .all()
    )
    # Sample one player's placement and delta from H2H
    sample_placement = None
    sample_delta = "n/a"
    for pl in team_players:
        tp = db.query(TournamentParticipation).filter(
            TournamentParticipation.user_id == pl.id,
            TournamentParticipation.semester_id == t_h2h.id,
        ).first()
        if tp:
            sample_placement = tp.placement
            if tp.skill_rating_delta and "passing" in (tp.skill_rating_delta or {}):
                d = tp.skill_rating_delta["passing"]
                sample_delta = f"{d:+.2f} per player"
            break
    place_str = f"{sample_placement}/3" if sample_placement else "n/a"
    print(f"{team.name:<14} │ {place_str:^6} │ {sample_delta:^30}")

# ── Final guarantee ───────────────────────────────────────────────────────────
print()
if all_ir_guarantee_ok:
    ok("IR GARANCIA TELJESÍTVE: minden U15 játékosnak van pozitív ÉS negatív skill delta ✓")
else:
    err("IR GARANCIA MEGSÉRTVE — ellenőrizd a rotation logikát")
    sys.exit(1)

print(f"\n{'═' * 64}")
print(f"  Seed kész.")
print(f"  IR cups  : {ir_tournament_ids}")
print(f"  H2H      : {t_h2h.id}")
print(f"  Club     : {boot_club.name} ({boot_club.code})")
print(f"  Players  : {len(u15_players)} U15 + 3 teams (36 total)")
print(f"{'═' * 64}\n")
