"""
E2E Tournament Type Matrix Test
================================
Proves all 5 key flows work on a clean bootstrapped DB.

Scenarios:
  S1: TEAM + League          — U12, 2 teams, 1 round-robin leg
  S2: TEAM + Knockout        — U15, 4 teams, power-of-two bracket
  S3: TEAM + Group+Knockout  — U18, 8 teams, group stage → knockout
  S4: TEAM + League 2-leg    — ADULT, 2 teams, number_of_legs=2
  S5: INDIVIDUAL + League    — U12 players enrolled individually

Each scenario runs the full lifecycle:
  create → teams/players enrolled → ENROLLMENT_OPEN → ENROLLMENT_CLOSED
  → CHECK_IN_OPEN → (set instructor) → IN_PROGRESS → verify sessions

Usage:
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system_e2e_clean" \\
        SECRET_KEY="e2e-test-secret-key-minimum-32-chars-needed" \\
        PYTHONPATH=. python scripts/e2e_matrix_test.py
"""
import os
import sys
import traceback
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system_e2e_clean")
os.environ.setdefault("SECRET_KEY", "e2e-test-secret-key-minimum-32-chars-needed")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.campus import Campus  # noqa: E402
from app.models.club import Club  # noqa: E402
from app.models.semester import Semester  # noqa: E402
from app.models.session import Session as SessionModel  # noqa: E402
from app.models.team import Team, TeamMember, TournamentTeamEnrollment  # noqa: E402
from app.models.tournament_configuration import TournamentConfiguration  # noqa: E402
from app.models.tournament_type import TournamentType  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.dependencies import (  # noqa: E402
    get_current_user_web,
    get_current_admin_user_hybrid,
    get_current_admin_or_instructor_user_hybrid,
)

# ── State ─────────────────────────────────────────────────────────────────────
_db = None
_admin_user = None
_client = None
_csrf_token = None

RESULTS = []   # list of (scenario_name, passed: bool, error: str|None)


# ── Formatting ────────────────────────────────────────────────────────────────
def _sep(width=65):
    return "=" * width

def section(title):
    print(f"\n{_sep()}\n  {title}\n{_sep()}")

def ok(msg):
    print(f"  ✅  {msg}")

def fail_local(msg):
    """Raise to abort current scenario without killing the whole script."""
    raise _ScenarioFailed(msg)

def info(msg):
    print(f"       {msg}")


class _ScenarioFailed(Exception):
    pass


# ── Auth + CSRF helpers ───────────────────────────────────────────────────────
def _setup():
    global _db, _admin_user, _client, _csrf_token

    _db = SessionLocal()

    _admin_user = _db.query(User).filter(User.email == "admin@lfa.com").first()
    if not _admin_user:
        print("❌ admin@lfa.com not found — run bootstrap_clean.py first")
        sys.exit(1)

    def _get_admin():
        return _admin_user

    app.dependency_overrides[get_current_user_web] = _get_admin
    app.dependency_overrides[get_current_admin_user_hybrid] = _get_admin
    app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = _get_admin

    _client = TestClient(app, follow_redirects=False)

    r = _client.get("/admin/tournaments")
    _csrf_token = r.cookies.get("csrf_token", "")
    if not _csrf_token:
        print("❌ Could not get CSRF token")
        sys.exit(1)


def _refresh_csrf(resp):
    global _csrf_token
    new = resp.cookies.get("csrf_token")
    if new:
        _csrf_token = new


def _post_form(url, data):
    resp = _client.post(url, data=data, headers={"X-CSRF-Token": _csrf_token})
    _refresh_csrf(resp)
    return resp


def _api_patch(url, body):
    resp = _client.patch(url, json=body)
    _refresh_csrf(resp)
    return resp


# ── Assertion helpers ─────────────────────────────────────────────────────────
def _assert_redirect(resp, fragment, label):
    location = resp.headers.get("location", "")
    if resp.status_code not in (302, 303):
        fail_local(f"{label}: expected redirect, got {resp.status_code} | {resp.text[:200]}")
    if "error=" in location:
        from urllib.parse import unquote
        err = unquote(location.split("error=")[1].split("&")[0]).replace("+", " ")
        fail_local(f"{label}: redirect error: {err}")
    if fragment and fragment not in location:
        fail_local(f"{label}: redirect to {location!r}, expected '{fragment}'")
    ok(f"{label} → {resp.status_code} → {location.split('?')[0]}")


def _assert_api_ok(resp, label):
    if resp.status_code not in (200, 201):
        body = {}
        try:
            body = resp.json()
        except Exception:
            pass
        msg = body.get("error", {}).get("message", "") or body.get("detail", "") if isinstance(body, dict) else str(body)
        fail_local(f"{label}: {resp.status_code} — {msg or resp.text[:150]}")
    body = resp.json()
    keys = list(body.keys())[:3]
    brief = "{" + ", ".join(f"{k}:{str(body[k])[:25]!r}" for k in keys) + "}"
    ok(f"{label} → {resp.status_code}: {brief}")
    return body


def _status_transition(tid, new_status):
    resp = _api_patch(f"/api/v1/tournaments/{tid}/status",
                      {"new_status": new_status, "reason": "matrix-test"})
    _assert_api_ok(resp, f"→ {new_status}")


# ── Common lifecycle (after enrollment phase) ─────────────────────────────────
def _common_lifecycle(tid, instructor_id, expected_min_sessions=1):
    """ENROLLMENT_CLOSED → CHECK_IN_OPEN → (set instructor) → IN_PROGRESS → verify."""
    _status_transition(tid, "ENROLLMENT_CLOSED")
    _status_transition(tid, "CHECK_IN_OPEN")

    # Set instructor directly (simulates wizard Basic Info save)
    t = _db.query(Semester).filter(Semester.id == tid).first()
    t.master_instructor_id = instructor_id
    _db.commit()
    ok(f"master_instructor_id = {instructor_id}")

    _db.expire_all()
    _status_transition(tid, "IN_PROGRESS")

    _db.expire_all()
    sess_count = _db.query(SessionModel).filter(SessionModel.semester_id == tid).count()
    if sess_count < expected_min_sessions:
        fail_local(f"Sessions generated: {sess_count} < expected {expected_min_sessions}")
    ok(f"Sessions generated: {sess_count}")
    return sess_count


# ── Scenario helpers ──────────────────────────────────────────────────────────
def _run_scenario(name, fn, *args, **kwargs):
    print(f"\n{'#'*65}")
    print(f"  SCENARIO: {name}")
    print(f"{'#'*65}")
    try:
        fn(*args, **kwargs)
        RESULTS.append((name, True, None))
        print(f"\n  ✅  PASSED: {name}")
    except _ScenarioFailed as e:
        RESULTS.append((name, False, str(e)))
        print(f"\n  ❌  FAILED: {name}")
        print(f"     {e}")
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"\n  ❌  ERROR: {name}")
        traceback.print_exc()
    finally:
        _db.expire_all()


def _get_tournament_after_promotion(name_fragment):
    """Find the most recent tournament whose name contains name_fragment."""
    _db.expire_all()
    t = (
        _db.query(Semester)
        .filter(Semester.name.like(f"%{name_fragment}%"))
        .order_by(Semester.id.desc())
        .first()
    )
    if not t:
        fail_local(f"No tournament found matching '{name_fragment}'")
    return t


def _promotion_wizard(club_id, campus_id, tt_id, age_group, label, name_prefix):
    """Run the promotion wizard for a single age group. Returns tournament id."""
    resp = _post_form(
        f"/admin/clubs/{club_id}/promotion",
        data={
            "tournament_name": name_prefix,
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "campus_id": str(campus_id),
            "tournament_type_id": str(tt_id),
            "game_preset_id": "",
            "age_groups": [age_group],
        },
    )
    _assert_redirect(resp, "/admin/tournaments", f"Promotion wizard ({label})")
    t = _get_tournament_after_promotion(name_prefix)
    info(f"Tournament: id={t.id}  name={t.name!r}  status={t.tournament_status}")
    return t.id


# ══════════════════════════════════════════════════════════════════════════════
# S1: TEAM + League — U12, 2 teams
# ══════════════════════════════════════════════════════════════════════════════
def s1_team_league(club, campus, tt_by_code, instructor):
    prefix = f"S1-League-{uuid.uuid4().hex[:6]}"
    tid = _promotion_wizard(club.id, campus.id, tt_by_code["league"].id, "U12", "league/U12", prefix)

    enrollments = _db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == tid, TournamentTeamEnrollment.is_active == True,  # noqa: E712
    ).count()
    ok(f"Teams enrolled: {enrollments}")
    if enrollments < 2:
        fail_local(f"Need ≥2 teams, got {enrollments}")

    _status_transition(tid, "ENROLLMENT_OPEN")
    _common_lifecycle(tid, instructor.id, expected_min_sessions=1)


# ══════════════════════════════════════════════════════════════════════════════
# S2: TEAM + Knockout — U15, 4 teams, requires_power_of_two
# ══════════════════════════════════════════════════════════════════════════════
def s2_team_knockout(club, campus, tt_by_code, instructor):
    prefix = f"S2-Knockout-{uuid.uuid4().hex[:6]}"
    tid = _promotion_wizard(club.id, campus.id, tt_by_code["knockout"].id, "U15", "knockout/U15", prefix)

    enrollments = _db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == tid, TournamentTeamEnrollment.is_active == True,  # noqa: E712
    ).count()
    ok(f"Teams enrolled: {enrollments}")
    if enrollments < 4:
        fail_local(f"Knockout needs ≥4 teams (power-of-two), got {enrollments}")

    _status_transition(tid, "ENROLLMENT_OPEN")
    # Expected: 3 matches for a 4-team bracket (2 semis + 1 final)
    _common_lifecycle(tid, instructor.id, expected_min_sessions=3)


# ══════════════════════════════════════════════════════════════════════════════
# S3: TEAM + Group+Knockout — U18, 8 teams
# ══════════════════════════════════════════════════════════════════════════════
def s3_team_group_knockout(club, campus, tt_by_code, instructor):
    prefix = f"S3-GKO-{uuid.uuid4().hex[:6]}"
    tid = _promotion_wizard(club.id, campus.id, tt_by_code["group_knockout"].id, "U18", "gko/U18", prefix)

    enrollments = _db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == tid, TournamentTeamEnrollment.is_active == True,  # noqa: E712
    ).count()
    ok(f"Teams enrolled: {enrollments}")
    if enrollments < 8:
        fail_local(f"Group+Knockout needs ≥8 teams, got {enrollments}")

    _status_transition(tid, "ENROLLMENT_OPEN")
    # Group stage + knockout: ≥9 sessions for 8 teams (varies by config)
    _common_lifecycle(tid, instructor.id, expected_min_sessions=9)


# ══════════════════════════════════════════════════════════════════════════════
# S4: TEAM + League 2-leg — ADULT, 2 teams, number_of_legs=2
# ══════════════════════════════════════════════════════════════════════════════
def s4_team_league_2leg(club, campus, tt_by_code, instructor):
    prefix = f"S4-2Leg-{uuid.uuid4().hex[:6]}"
    tid = _promotion_wizard(club.id, campus.id, tt_by_code["league"].id, "ADULT", "2leg/ADULT", prefix)

    enrollments = _db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == tid, TournamentTeamEnrollment.is_active == True,  # noqa: E712
    ).count()
    ok(f"Teams enrolled: {enrollments}")

    # Set number_of_legs = 2 before generating sessions
    cfg = _db.query(TournamentConfiguration).filter(
        TournamentConfiguration.semester_id == tid
    ).first()
    if not cfg:
        fail_local("TournamentConfiguration not found")
    cfg.number_of_legs = 2
    _db.commit()
    ok("number_of_legs = 2 set on TournamentConfiguration")

    _status_transition(tid, "ENROLLMENT_OPEN")
    # 2 teams × 2 legs = 2 matches
    _common_lifecycle(tid, instructor.id, expected_min_sessions=2)

    # Verify exactly 2× matches (1 per leg)
    sess_count = _db.query(SessionModel).filter(SessionModel.semester_id == tid).count()
    if sess_count != 2:
        fail_local(f"Expected 2 sessions for 2-team 2-leg league, got {sess_count}")
    ok(f"2-leg session count correct: {sess_count}")


# ══════════════════════════════════════════════════════════════════════════════
# S5: INDIVIDUAL + League — players enrolled individually (U12 teams as source)
# ══════════════════════════════════════════════════════════════════════════════
def s5_individual_league(club, campus, tt_by_code, instructor):
    prefix = f"S5-Ind-{uuid.uuid4().hex[:6]}"

    # Create INDIVIDUAL tournament via admin form
    resp = _post_form(
        "/admin/tournaments",
        data={
            "name": prefix,
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "age_group": "AMATEUR",
            "enrollment_cost": "0",
            "campus_id": str(campus.id),
            "tournament_type_id": str(tt_by_code["league"].id),
            "game_preset_id": "",
            "participant_type": "INDIVIDUAL",
            "number_of_rounds": "1",
        },
    )
    _assert_redirect(resp, "/admin/tournaments/", f"Create INDIVIDUAL tournament")

    t = _get_tournament_after_promotion(prefix)
    info(f"Tournament: id={t.id}  participant_type=INDIVIDUAL  campus_id={t.campus_id}")

    # Verify TournamentConfiguration has participant_type=INDIVIDUAL
    cfg = _db.query(TournamentConfiguration).filter(
        TournamentConfiguration.semester_id == t.id
    ).first()
    if not cfg or cfg.participant_type != "INDIVIDUAL":
        fail_local(f"participant_type wrong: {cfg.participant_type if cfg else 'no config'}")
    ok(f"TournamentConfiguration: participant_type=INDIVIDUAL  tournament_type_id={cfg.tournament_type_id}")

    # Open enrollment
    _status_transition(t.id, "ENROLLMENT_OPEN")

    # Enroll players from Bootstrap U12 A and U12 B teams
    u12_teams = (
        _db.query(Team)
        .filter(Team.club_id == club.id, Team.age_group_label == "U12", Team.is_active == True)  # noqa: E712
        .all()
    )
    if len(u12_teams) < 2:
        fail_local(f"Need ≥2 U12 teams for INDIVIDUAL enrollment, got {len(u12_teams)}")

    # enroll-from-team accepts multiple team_ids as a list
    team_ids_str = [str(t2.id) for t2 in u12_teams[:2]]
    resp = _post_form(
        f"/admin/tournaments/{t.id}/players/enroll-from-team",
        data={"team_ids": team_ids_str},
    )
    _assert_redirect(resp, f"/admin/tournaments/{t.id}/players", "Enroll players from team")

    # Count enrollments
    from app.models.semester_enrollment import SemesterEnrollment
    enrolled_count = (
        _db.query(SemesterEnrollment)
        .filter(SemesterEnrollment.semester_id == t.id, SemesterEnrollment.is_active == True)  # noqa: E712
        .count()
    )
    ok(f"Individual players enrolled: {enrolled_count}")
    if enrolled_count < 2:
        fail_local(f"Need ≥2 players for ENROLLMENT_CLOSED, got {enrolled_count}")

    # Full lifecycle
    _common_lifecycle(t.id, instructor.id, expected_min_sessions=1)


# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    _setup()

    # Load shared fixtures
    club = _db.query(Club).filter(Club.code == "LFA-BOOT").first()
    if not club:
        print("❌ Bootstrap club not found")
        sys.exit(1)

    campus = _db.query(Campus).filter(Campus.is_active == True).first()  # noqa: E712
    instructor = _db.query(User).filter(User.email == "instructor@lfa.com").first()
    if not campus or not instructor:
        print("❌ Campus or instructor missing — run bootstrap_clean.py")
        sys.exit(1)

    tt_by_code = {
        tt.code: tt
        for tt in _db.query(TournamentType).all()
    }
    for code in ("league", "knockout", "group_knockout"):
        if code not in tt_by_code:
            print(f"❌ TournamentType '{code}' missing — run bootstrap_clean.py")
            sys.exit(1)

    section("Bootstrap fixtures")
    ok(f"Club: {club.name!r}  id={club.id}")
    ok(f"Campus: {campus.name!r}  id={campus.id}")
    ok(f"Instructor: {instructor.email}")
    teams = _db.query(Team).filter(Team.club_id == club.id).all()
    for ag in ("U12", "U15", "U18", "ADULT"):
        n = sum(1 for t in teams if t.age_group_label == ag)
        info(f"  {ag}: {n} teams")

    # ── Run scenarios ─────────────────────────────────────────────────────────
    _run_scenario("S1: TEAM + League (U12, 2 teams)",
                  s1_team_league, club, campus, tt_by_code, instructor)

    _run_scenario("S2: TEAM + Knockout (U15, 4 teams)",
                  s2_team_knockout, club, campus, tt_by_code, instructor)

    _run_scenario("S3: TEAM + Group+Knockout (U18, 8 teams)",
                  s3_team_group_knockout, club, campus, tt_by_code, instructor)

    _run_scenario("S4: TEAM + League 2-leg (ADULT, 2 teams)",
                  s4_team_league_2leg, club, campus, tt_by_code, instructor)

    _run_scenario("S5: INDIVIDUAL + League (U12 players individually)",
                  s5_individual_league, club, campus, tt_by_code, instructor)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n\n{'='*65}")
    print("  MATRIX RESULTS")
    print("="*65)
    passed = sum(1 for _, p, _ in RESULTS if p)
    failed = len(RESULTS) - passed
    for name, p, err in RESULTS:
        icon = "✅" if p else "❌"
        print(f"  {icon}  {name}")
        if err:
            print(f"         └─ {err}")
    print("="*65)
    print(f"  {passed}/{len(RESULTS)} passed  |  {failed} failed")
    print("="*65 + "\n")

    _db.close()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run()
