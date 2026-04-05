"""
PES Regression Scenario Seed
==============================
Deterministic seed that reproduces the three data shapes exercised by
PES-08, PES-09, and PES-10 on any clean database.

Creates:
  Scenario A — 3-team legacy tournament
                ALL sessions have participant_team_ids=NULL
                Team identity stored only in rounds_data as 'team_{id}' keys
                → Before fix: every round showed 'TBD vs TBD'
                → After  fix: 'LFA U15  3–2  LFA U18'  etc.

  Scenario B — 3-team new-style tournament
                ALL sessions have participant_team_ids=[t1, t2]
                → Regression baseline: must continue to resolve correctly

  Scenario C — mixed tournament (1 new-style + 1 legacy session)
                Round 1: participant_team_ids=[Alpha, Beta]   (new)
                Round 2: participant_team_ids=NULL            (legacy)
                → Both rounds must resolve names; no TBD anywhere

After seeding, a validation section queries each /events/{id} page, extracts
the schedule rows, and prints a before/after comparison table.

Usage (clean or existing DB — idempotent, deletes own prefix first):
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/<db>" \\
        SECRET_KEY="..." PYTHONPATH=. python scripts/seed_pes_regression_scenarios.py
"""
import os
import sys
import json
import re
import uuid
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
os.environ.setdefault("SECRET_KEY", "e2e-test-secret-key-minimum-32-chars-needed")

from sqlalchemy import text as _sql
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.core.security import get_password_hash
from app.models.campus import Campus
from app.models.club import Club
from app.models.game_configuration import GameConfiguration
from app.models.game_preset import GamePreset
from app.models.license import UserLicense
from app.models.semester import Semester, SemesterCategory, SemesterStatus
from app.models.session import Session as SessionModel, EventCategory
from app.models.team import Team, TeamMember, TournamentTeamEnrollment
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_reward_config import TournamentRewardConfig
from app.models.tournament_type import TournamentType
from app.models.user import User, UserRole
from app.dependencies import (
    get_current_admin_or_instructor_user_hybrid,
    get_current_admin_user_hybrid,
    get_current_user_web,
)

# ─────────────────────────────────────────────────────────────────────────────
# Output helpers
# ─────────────────────────────────────────────────────────────────────────────

W = 70

def _sep(char="─"): print(char * W)
def _hdr(title): _sep("═"); print(f"  {title}"); _sep("═")
def ok(msg):   print(f"  ✅  {msg}")
def info(msg): print(f"       {msg}")
def err(msg):  print(f"  ❌  {msg}")
def _uid(): return uuid.uuid4().hex[:6]


# ─────────────────────────────────────────────────────────────────────────────
# Prerequisite check
# ─────────────────────────────────────────────────────────────────────────────

db = SessionLocal()

admin = db.query(User).filter(User.email == "admin@lfa.com").first()
instructor = db.query(User).filter(User.email == "instructor@lfa.com").first()
if not admin or not instructor:
    print("❌  admin@lfa.com / instructor@lfa.com not found.")
    print("    Run: PYTHONPATH=. python scripts/bootstrap_clean.py")
    sys.exit(1)

campus = db.query(Campus).first()
preset = db.query(GamePreset).first()
tt_league = db.query(TournamentType).filter(TournamentType.code == "league").first()

if not campus or not preset or not tt_league:
    print("❌  Campus / GamePreset / TournamentType missing.")
    print("    Run: PYTHONPATH=. python scripts/bootstrap_clean.py")
    sys.exit(1)

app.dependency_overrides[get_current_user_web] = lambda: admin
app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin
app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = lambda: admin

client = TestClient(app, raise_server_exceptions=True)

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup: remove any previous PES-REGR- runs
# ─────────────────────────────────────────────────────────────────────────────

_hdr("Cleanup — removing previous PES-REGR- tournaments")

_existing = [
    row[0] for row in db.execute(
        _sql("SELECT id FROM semesters WHERE name LIKE 'PES-REGR-%'")
    ).fetchall()
]
if _existing:
    id_list = ", ".join(str(i) for i in _existing)
    for tbl in [
        "tournament_reward_configs", "tournament_configurations",
        "game_configurations", "tournament_team_enrollments",
        "tournament_rankings", "tournament_participations",
        "tournament_reward_distributions", "sessions",
    ]:
        try: db.execute(_sql(f"DELETE FROM {tbl} WHERE semester_id IN ({id_list})"))
        except Exception: db.rollback()
    try: db.execute(_sql(f"DELETE FROM tournament_status_history WHERE tournament_id IN ({id_list})"))
    except Exception: db.rollback()
    db.execute(_sql(f"DELETE FROM semesters WHERE id IN ({id_list})"))
    db.commit()
    ok(f"Removed {len(_existing)} previous run(s)")
else:
    ok("No previous PES-REGR runs found")


# ─────────────────────────────────────────────────────────────────────────────
# Local player / team factory helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_player(name: str, email: str) -> User:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            name=name, email=email,
            password_hash=get_password_hash("Test#123"),
            role=UserRole.STUDENT, is_active=True, onboarding_completed=True,
            credit_balance=100,
        )
        db.add(u)
        db.flush()
    return u


def _make_team(name: str, captain: User) -> Team:
    existing = db.query(Team).filter(
        Team.name == name, Team.captain_user_id == captain.id
    ).first()
    if existing:
        return existing
    t = Team(name=name, captain_user_id=captain.id, is_active=True)
    db.add(t)
    db.flush()
    db.add(TeamMember(team_id=t.id, user_id=captain.id, role="CAPTAIN", is_active=True))
    db.flush()
    return t


def _make_tournament(name: str) -> Semester:
    t = Semester(
        name=name,
        code=f"REGR-{_uid()}",
        master_instructor_id=instructor.id,
        campus_id=campus.id,
        location_id=campus.location_id,
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 3),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status="REWARDS_DISTRIBUTED",
    )
    db.add(t)
    db.flush()
    db.add(TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=tt_league.id,
        participant_type="TEAM",
        max_players=16, number_of_rounds=1, parallel_fields=1,
        ranking_direction="DESC", scoring_type="SCORE_BASED",
    ))
    db.add(GameConfiguration(semester_id=t.id, game_preset_id=preset.id))
    db.add(TournamentRewardConfig(
        semester_id=t.id,
        reward_policy_name="PES Regr Default",
        reward_config={"skill_mappings": []},
    ))
    db.flush()
    return t


def _make_session(
    tournament: Semester,
    round_number: int,
    participant_team_ids,   # list[int] | None
    rounds_data: dict,
) -> SessionModel:
    sess = SessionModel(
        semester_id=tournament.id,
        instructor_id=tournament.master_instructor_id,
        title=f"Match R{round_number}",
        event_category=EventCategory.MATCH,
        auto_generated=True,
        capacity=2,
        round_number=round_number,
        session_status="completed",
        participant_team_ids=participant_team_ids,
        rounds_data=rounds_data,
        date_start=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
        date_end=datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc),
    )
    db.add(sess)
    db.flush()
    return sess


def _make_team_rankings(tournament_id: int, standings: list[tuple]) -> None:
    """standings = [(team, pts, W, D, L, GF, GA), ...]"""
    for rank, (team, pts, w, d, l, gf, ga) in enumerate(standings, 1):
        db.add(TournamentRanking(
            tournament_id=tournament_id,
            team_id=team.id,
            participant_type="TEAM",
            rank=rank,
            points=float(pts),
            wins=w, draws=d, losses=l,
            goals_for=gf, goals_against=ga,
        ))
    db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Scenario A — ALL sessions legacy (participant_team_ids=NULL)
# Reproduces: PES-10 / 'H2H League — Rewards Distributed 2026' on dev DB
# ─────────────────────────────────────────────────────────────────────────────

_hdr("Scenario A — 3-team legacy tournament (ALL participant_team_ids=NULL)")

cap_a = _make_player("Cap U15",   "pes-regr-cap-u15@lfa-regr.test")
cap_b = _make_player("Cap U18",   "pes-regr-cap-u18@lfa-regr.test")
cap_c = _make_player("Cap Adult", "pes-regr-cap-adult@lfa-regr.test")

team_u15   = _make_team("Regr U15",   cap_a)
team_u18   = _make_team("Regr U18",   cap_b)
team_adult = _make_team("Regr Adult", cap_c)

t_A = _make_tournament("PES-REGR-A: 3-team legacy (all NULL participant_team_ids)")

_MATCHES_A = [
    # (team_a, team_b, score_a, score_b)
    (team_u15,   team_u18,   3, 2),   # Round 1: U15 beats U18
    (team_u15,   team_adult, 2, 3),   # Round 2: Adult beats U15
    (team_u18,   team_adult, 2, 3),   # Round 3: Adult beats U18
]
for rnd, (ta, tb, sa, sb) in enumerate(_MATCHES_A, 1):
    _make_session(
        t_A, rnd,
        participant_team_ids=None,          # ← LEGACY: NULL
        rounds_data={"total_rounds": 1, "round_results": {"1": {
            f"team_{ta.id}": str(sa),
            f"team_{tb.id}": str(sb),
        }}},
    )

_make_team_rankings(t_A.id, [
    (team_adult, 6, 2, 0, 0, 6, 4),
    (team_u15,   3, 1, 0, 1, 5, 5),
    (team_u18,   0, 0, 0, 2, 4, 6),
])
db.commit()
db.expire_all()
ok(f"Created '{t_A.name}'  id={t_A.id}")
info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t_A.id).count()}"
     "  (all participant_team_ids=NULL)")
info(f"Teams: {team_u15.name}(id={team_u15.id})  "
     f"{team_u18.name}(id={team_u18.id})  "
     f"{team_adult.name}(id={team_adult.id})")


# ─────────────────────────────────────────────────────────────────────────────
# Scenario B — ALL sessions new-style (participant_team_ids populated)
# Regression baseline: must continue to work after the fix
# ─────────────────────────────────────────────────────────────────────────────

_hdr("Scenario B — 3-team new-style tournament (participant_team_ids populated)")

t_B = _make_tournament("PES-REGR-B: 3-team new-style (participant_team_ids set)")

_MATCHES_B = [
    (team_u15,   team_u18,   3, 2),
    (team_u15,   team_adult, 2, 3),
    (team_u18,   team_adult, 2, 3),
]
for rnd, (ta, tb, sa, sb) in enumerate(_MATCHES_B, 1):
    _make_session(
        t_B, rnd,
        participant_team_ids=[ta.id, tb.id],    # ← NEW-STYLE: populated
        rounds_data={"total_rounds": 1, "round_results": {"1": {
            f"team_{ta.id}": str(sa),
            f"team_{tb.id}": str(sb),
        }}},
    )

_make_team_rankings(t_B.id, [
    (team_adult, 6, 2, 0, 0, 6, 4),
    (team_u15,   3, 1, 0, 1, 5, 5),
    (team_u18,   0, 0, 0, 2, 4, 6),
])
db.commit()
db.expire_all()
ok(f"Created '{t_B.name}'  id={t_B.id}")
info(f"Sessions: {db.query(SessionModel).filter(SessionModel.semester_id == t_B.id).count()}"
     "  (all participant_team_ids populated)")


# ─────────────────────────────────────────────────────────────────────────────
# Scenario C — MIXED: Round 1 new-style, Round 2 legacy
# Exercises PES-09: both must resolve, no TBD anywhere
# ─────────────────────────────────────────────────────────────────────────────

_hdr("Scenario C — mixed tournament (Round 1 new-style, Round 2 legacy)")

cap_x = _make_player("Cap X", "pes-regr-cap-x@lfa-regr.test")
cap_y = _make_player("Cap Y", "pes-regr-cap-y@lfa-regr.test")
cap_z = _make_player("Cap Z", "pes-regr-cap-z@lfa-regr.test")

team_x = _make_team("Mix Alpha", cap_x)
team_y = _make_team("Mix Beta",  cap_y)
team_z = _make_team("Mix Gamma", cap_z)

t_C = _make_tournament("PES-REGR-C: mixed (1 new + 1 legacy session)")

_make_session(
    t_C, 1,
    participant_team_ids=[team_x.id, team_y.id],    # new-style
    rounds_data={"total_rounds": 1, "round_results": {"1": {
        f"team_{team_x.id}": "2",
        f"team_{team_y.id}": "0",
    }}},
)
_make_session(
    t_C, 2,
    participant_team_ids=None,                       # legacy
    rounds_data={"total_rounds": 1, "round_results": {"1": {
        f"team_{team_x.id}": "1",
        f"team_{team_z.id}": "1",
    }}},
)

_make_team_rankings(t_C.id, [
    (team_x, 4, 1, 1, 0, 3, 1),
    (team_y, 0, 0, 0, 1, 0, 2),
    (team_z, 1, 0, 1, 0, 1, 1),
])
db.commit()
db.expire_all()
ok(f"Created '{t_C.name}'  id={t_C.id}")
info(f"Round 1: participant_team_ids=[{team_x.id}, {team_y.id}]  (new-style)")
info(f"Round 2: participant_team_ids=NULL                        (legacy)")


# ─────────────────────────────────────────────────────────────────────────────
# DB state summary
# ─────────────────────────────────────────────────────────────────────────────

_hdr("DB state — PES-REGR scenario sessions")

for t, label in [(t_A, "A-Legacy"), (t_B, "B-New"), (t_C, "C-Mixed")]:
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == t.id).order_by(SessionModel.round_number).all()
    print(f"\n  [{label}]  tournament id={t.id}  status={t.tournament_status}")
    for s in sessions:
        r1 = (s.rounds_data or {}).get("round_results", {}).get("1", {})
        team_keys = [k for k in r1 if k.startswith("team_")]
        print(f"    session {s.id}  R{s.round_number}  "
              f"participant_team_ids={s.participant_team_ids!s:<20s}  "
              f"rounds_data.keys={team_keys}")


# ─────────────────────────────────────────────────────────────────────────────
# Schedule rendering validation via actual HTTP
# ─────────────────────────────────────────────────────────────────────────────

_hdr("Schedule rendering — GET /events/{id}")

def _extract_schedule(html: str) -> list[tuple[str, str, str]]:
    """Extract (team_a, score, team_b) tuples from rendered HTML schedule rows."""
    results = []
    # Each match row contains: <span class="match-team team-a">NAME</span>
    #                           <span class="match-vs">SCORE (or vs)</span>
    #                           <span class="match-team team-b">NAME</span>
    pattern = (
        r'class="match-team team-a">(.*?)</span>'
        r'.*?class="match-vs">\s*(.*?)\s*</span>'
        r'.*?class="match-team team-b">(.*?)</span>'
    )
    for m in re.finditer(pattern, html, re.DOTALL):
        results.append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))
    return results


_EXPECTED: dict[str, list[tuple[str, str, str]]] = {
    "A": [
        ("Regr U15",   "3–2", "Regr U18"),
        ("Regr U15",   "2–3", "Regr Adult"),
        ("Regr U18",   "2–3", "Regr Adult"),
    ],
    "B": [
        ("Regr U15",   "3–2", "Regr U18"),
        ("Regr U15",   "2–3", "Regr Adult"),
        ("Regr U18",   "2–3", "Regr Adult"),
    ],
    "C": [
        ("Mix Alpha", "2–0", "Mix Beta"),   # new-style session
        ("Mix Alpha", "1–1", "Mix Gamma"),  # legacy session
    ],
}

all_pass = True
for scenario, tid, label in [("A", t_A.id, "3-team legacy"), ("B", t_B.id, "3-team new"), ("C", t_C.id, "mixed")]:
    print(f"\n  [{scenario}] /events/{tid} — {label}")
    resp = client.get(f"/events/{tid}")
    assert resp.status_code == 200, f"HTTP {resp.status_code} for /events/{tid}"

    html = resp.text
    rows = _extract_schedule(html)
    tbd_count = html.count(">TBD<")

    print(f"    Extracted schedule rows: {len(rows)}")
    for r in rows:
        print(f"      {r[0]:20s}  {r[1]:5s}  {r[2]}")

    expected = _EXPECTED[scenario]
    _sep()
    if tbd_count > 0:
        err(f"TBD appeared {tbd_count} time(s) — regression!")
        all_pass = False
    else:
        ok("TBD count = 0")

    if len(rows) != len(expected):
        err(f"Expected {len(expected)} rows, got {len(rows)}")
        all_pass = False
    else:
        for i, ((got_a, got_score, got_b), (exp_a, exp_score, exp_b)) in enumerate(zip(rows, expected), 1):
            if got_a != exp_a or got_score != exp_score or got_b != exp_b:
                err(f"Row {i}: got ({got_a!r}, {got_score!r}, {got_b!r}) "
                    f"expected ({exp_a!r}, {exp_score!r}, {exp_b!r})")
                all_pass = False
            else:
                ok(f"Row {i} ✓  {got_a}  {got_score}  {got_b}")


# ─────────────────────────────────────────────────────────────────────────────
# Before/after simulation — show what OLD code would have returned
# ─────────────────────────────────────────────────────────────────────────────

_hdr("Before/after comparison — old vs new route logic")

print(f"\n  {'Session':^10s}  {'participant_team_ids':^22s}  {'BEFORE fix':^22s}  {'AFTER fix':^26s}")
_sep()

for t, label in [(t_A, "A-Legacy"), (t_C, "C-Mixed")]:
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == t.id).order_by(SessionModel.round_number).all()
    for s in sessions:
        r1 = (s.rounds_data or {}).get("round_results", {}).get("1", {})
        team_keys = sorted(k for k in r1 if k.startswith("team_"))

        # OLD logic
        tids_old = list(s.participant_team_ids or [])
        if len(tids_old) >= 2:
            old_str = f"team[{tids_old[0]}] vs team[{tids_old[1]}]"
        else:
            old_str = "TBD vs TBD"

        # NEW logic
        tids_new = list(s.participant_team_ids or [])
        if not tids_new and r1:
            derived = sorted(int(k.split("_",1)[1]) for k in r1
                             if k.startswith("team_") and k.split("_",1)[1].isdigit())
            if len(derived) >= 2:
                tids_new = derived
        if len(tids_new) >= 2:
            from app.models.team import Team as T
            na = (db.query(T).filter(T.id == tids_new[0]).first() or type("", (), {"name": f"#{tids_new[0]}"})()).name
            nb = (db.query(T).filter(T.id == tids_new[1]).first() or type("", (), {"name": f"#{tids_new[1]}"})()).name
            sa = r1.get(f"team_{tids_new[0]}", "?")
            sb = r1.get(f"team_{tids_new[1]}", "?")
            new_str = f"{na} {sa}–{sb} {nb}"
        else:
            new_str = "TBD vs TBD"

        pid_str = str(s.participant_team_ids)[:20]
        print(f"  {label[:6]}-R{s.round_number}  {pid_str:<22s}  {old_str:<22s}  {new_str}")


# ─────────────────────────────────────────────────────────────────────────────
# Final result
# ─────────────────────────────────────────────────────────────────────────────

_hdr("Final result")

if all_pass:
    print("""
  ✅  ALL SCENARIOS PASS

  Scenario A (all-legacy):  3/3 rounds show real names + scores — no TBD
  Scenario B (all-new):     3/3 rounds show real names + scores — no TBD  (regression safe)
  Scenario C (mixed):       2/2 rounds show real names + scores — no TBD

  Steps to reproduce on any clean database:
    1. createdb lfa_clean_test
    2. DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_clean_test" \\
           PYTHONPATH=. python scripts/bootstrap_clean.py
    3. DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_clean_test" \\
           SECRET_KEY="..." PYTHONPATH=. python scripts/seed_pes_regression_scenarios.py
""")
else:
    print("  ❌  SOME SCENARIOS FAILED — see errors above")
    sys.exit(1)

db.close()
