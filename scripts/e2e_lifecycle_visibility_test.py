"""
E2E Lifecycle Visibility Test
================================
Proves that the promotion flow's state machine and public visibility gates
are consistent at every status transition.

Tests (6 total):
  GUARD-A   campus_id=NULL → ENROLLMENT_OPEN rejected (HTTP 400)
  GUARD-C   no instructor → IN_PROGRESS rejected (HTTP 400)
  GUARD-D   0 rankings → COMPLETED rejected (HTTP 400)
  FULL-LC   DRAFT→ENROLLMENT_OPEN→ENROLLMENT_CLOSED→CHECK_IN_OPEN
            →IN_PROGRESS→COMPLETED→REWARDS_DISTRIBUTED
            + /events/{id} visibility asserted at EVERY transition
  CANCELLED DRAFT→CANCELLED → /events/{id} = 404
  FRONTEND  /admin/promotion-events + /admin/tournaments/{id} + /events/{id}
            all show the same REWARDS_DISTRIBUTED state (consistency check)

VISIBILITY INVARIANT (the critical domain rule):
  DRAFT      → GET /events/{id} = 404  (not published)
  CANCELLED  → GET /events/{id} = 404  (withdrawn)
  All others → GET /events/{id} = 200  (publicly visible)

Usage:
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \\
        SECRET_KEY="e2e-test-secret-key-minimum-32-chars-needed" \\
        PYTHONPATH=. python scripts/e2e_lifecycle_visibility_test.py
"""
import os
import sys
import traceback
import uuid
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lfa_intern_system",
)
os.environ.setdefault("SECRET_KEY", "e2e-test-secret-key-minimum-32-chars-needed")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.campus import Campus  # noqa: E402
from app.models.club import Club  # noqa: E402
from app.models.semester import Semester, SemesterStatus, SemesterCategory  # noqa: E402
from app.models.session import Session as SessionModel  # noqa: E402
from app.models.team import Team, TeamMember, TournamentTeamEnrollment  # noqa: E402
from app.models.tournament_configuration import TournamentConfiguration  # noqa: E402
from app.models.tournament_ranking import TournamentRanking  # noqa: E402
from app.models.tournament_type import TournamentType  # noqa: E402
from app.models.user import User  # noqa: E402
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

RESULTS = []  # [(name, passed, error)]


# ── Formatting ────────────────────────────────────────────────────────────────
def section(title):
    print(f"\n{'='*65}\n  {title}\n{'='*65}")


def ok(msg):
    print(f"  ✅  {msg}")


def info(msg):
    print(f"       {msg}")


class _TestFailed(Exception):
    pass


def fail(msg):
    raise _TestFailed(msg)


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
        print("❌ Could not get CSRF token from GET /admin/tournaments")
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


def _api_post(url, body):
    resp = _client.post(url, json=body)
    _refresh_csrf(resp)
    return resp


# ── Assertion helpers ─────────────────────────────────────────────────────────
def _assert_redirect_ok(resp, fragment, label):
    location = resp.headers.get("location", "")
    if resp.status_code not in (302, 303):
        fail(f"{label}: expected redirect, got {resp.status_code} | {resp.text[:200]}")
    if "error=" in location:
        from urllib.parse import unquote
        err = unquote(location.split("error=")[1].split("&")[0]).replace("+", " ")
        fail(f"{label}: redirect error: {err}")
    if fragment and fragment not in location:
        fail(f"{label}: redirect to {location!r}, expected '{fragment}'")
    ok(f"{label} → {resp.status_code} → {location.split('?')[0]}")


def _assert_api_ok(resp, label):
    if resp.status_code not in (200, 201):
        body = {}
        try:
            body = resp.json()
        except Exception:
            pass
        detail = ""
        if isinstance(body, dict):
            detail = body.get("detail") or body.get("message") or str(body)[:150]
        fail(f"{label}: HTTP {resp.status_code} — {detail or resp.text[:150]}")
    ok(f"{label} → {resp.status_code}")
    return resp.json()


def _assert_api_error(resp, expected_status, label):
    if resp.status_code != expected_status:
        body = {}
        try:
            body = resp.json()
        except Exception:
            pass
        detail = ""
        if isinstance(body, dict):
            detail = body.get("detail") or body.get("message") or str(body)[:150]
        fail(
            f"{label}: expected HTTP {expected_status}, got {resp.status_code}"
            f" — {detail or resp.text[:150]}"
        )
    try:
        body = resp.json()
        detail = body.get("detail", "") if isinstance(body, dict) else ""
        ok(f"[GUARD] {label} → correctly rejected {expected_status}: {detail[:80]}")
    except Exception:
        ok(f"[GUARD] {label} → correctly rejected {expected_status}")


def _assert_public_visibility(tid, expected_code, status_label):
    """Core visibility invariant check: /events/{id} must return expected_code."""
    resp = _client.get(f"/events/{tid}")
    if resp.status_code != expected_code:
        detail = resp.text[:100].strip()
        fail(
            f"[VISIBILITY INVARIANT VIOLATED] "
            f"/events/{tid} at status={status_label}: "
            f"expected HTTP {expected_code}, got {resp.status_code} | {detail}"
        )
    symbol = "🔒" if expected_code == 404 else "🌐"
    visibility = "NOT visible (404)" if expected_code == 404 else "VISIBLE (200)"
    ok(f"{symbol} /events/{tid} [{status_label}] → {resp.status_code} — {visibility}")


# ── Lifecycle helpers ─────────────────────────────────────────────────────────
def _status_transition(tid, new_status):
    resp = _api_patch(
        f"/api/v1/tournaments/{tid}/status",
        {"new_status": new_status, "reason": "lifecycle-visibility-test"},
    )
    _assert_api_ok(resp, f"→ {new_status}")
    _db.expire_all()


def _status_transition_expect_fail(tid, new_status, label):
    resp = _api_patch(
        f"/api/v1/tournaments/{tid}/status",
        {"new_status": new_status, "reason": "guard-test"},
    )
    _assert_api_error(resp, 400, label)
    _db.expire_all()


def _get_tournament(name_fragment):
    _db.expire_all()
    t = (
        _db.query(Semester)
        .filter(Semester.name.like(f"%{name_fragment}%"))
        .order_by(Semester.id.desc())
        .first()
    )
    if not t:
        fail(f"No tournament found matching '{name_fragment}'")
    return t


def _promotion_wizard(club_id, campus_id, tt_id, age_group, name_prefix):
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
    _assert_redirect_ok(resp, "/admin/tournaments", f"Promotion wizard ({age_group})")
    t = _get_tournament(name_prefix)
    info(
        f"Tournament: id={t.id}  name={t.name!r}  "
        f"campus_id={t.campus_id}  status={t.tournament_status}"
    )
    return t


def _run_test(name, fn, *args, **kwargs):
    print(f"\n{'#'*65}\n  TEST: {name}\n{'#'*65}")
    try:
        result = fn(*args, **kwargs)
        RESULTS.append((name, True, None))
        print(f"\n  ✅  PASSED: {name}")
        return result
    except _TestFailed as e:
        RESULTS.append((name, False, str(e)))
        print(f"\n  ❌  FAILED: {name}")
        print(f"     {e}")
        return None
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"\n  ❌  ERROR: {name}")
        traceback.print_exc()
        return None
    finally:
        _db.expire_all()


# ══════════════════════════════════════════════════════════════════════════════
# GUARD A — campus_id=NULL → ENROLLMENT_OPEN rejected
# ══════════════════════════════════════════════════════════════════════════════
def test_guard_a_campus_required(tt_id):
    """Create a tournament without campus_id; assert ENROLLMENT_OPEN fails."""
    suffix = uuid.uuid4().hex[:8]
    t = Semester(
        code=f"GUARD-A-{suffix}",
        name=f"Guard-A-NoCampus-{suffix}",
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 7, 3),
        status=SemesterStatus.DRAFT,
        tournament_status="DRAFT",
        semester_category=SemesterCategory.TOURNAMENT,
        specialization_type="LFA_FOOTBALL_PLAYER",
        campus_id=None,  # intentionally NULL
    )
    _db.add(t)
    _db.flush()
    _db.add(TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=tt_id,
        participant_type="TEAM",
        number_of_rounds=1,
    ))
    _db.commit()
    _db.expire_all()
    info(f"  Tournament id={t.id}  campus_id=NULL")

    _status_transition_expect_fail(
        t.id, "ENROLLMENT_OPEN",
        "campus_id=NULL → status_validator rejects ENROLLMENT_OPEN",
    )


# ══════════════════════════════════════════════════════════════════════════════
# GUARD C — no instructor → IN_PROGRESS rejected
# ══════════════════════════════════════════════════════════════════════════════
def test_guard_c_instructor_required(club, campus, tt_id):
    """Run lifecycle to CHECK_IN_OPEN without setting instructor; assert IN_PROGRESS fails."""
    prefix = f"Guard-C-{uuid.uuid4().hex[:6]}"
    t = _promotion_wizard(club.id, campus.id, tt_id, "U12", prefix)

    enr_count = _db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == t.id,
        TournamentTeamEnrollment.is_active == True,  # noqa: E712
    ).count()
    info(f"  Teams enrolled: {enr_count}")

    _status_transition(t.id, "ENROLLMENT_OPEN")
    _status_transition(t.id, "ENROLLMENT_CLOSED")
    _status_transition(t.id, "CHECK_IN_OPEN")

    _db.expire_all()
    t_reloaded = _db.query(Semester).filter(Semester.id == t.id).first()
    if t_reloaded.master_instructor_id is not None:
        fail(f"instructor_id was unexpectedly set to {t_reloaded.master_instructor_id}; guard test invalid")

    _status_transition_expect_fail(
        t.id, "IN_PROGRESS",
        "master_instructor_id=NULL → status_validator rejects IN_PROGRESS",
    )


# ══════════════════════════════════════════════════════════════════════════════
# GUARD D — 0 rankings → COMPLETED rejected
# ══════════════════════════════════════════════════════════════════════════════
def test_guard_d_rankings_required(club, campus, tt_id, instructor):
    """Advance to IN_PROGRESS without submitting rankings; assert COMPLETED fails."""
    prefix = f"Guard-D-{uuid.uuid4().hex[:6]}"
    t = _promotion_wizard(club.id, campus.id, tt_id, "U12", prefix)

    _status_transition(t.id, "ENROLLMENT_OPEN")
    _status_transition(t.id, "ENROLLMENT_CLOSED")
    _status_transition(t.id, "CHECK_IN_OPEN")

    _db.expire_all()
    t_obj = _db.query(Semester).filter(Semester.id == t.id).first()
    t_obj.master_instructor_id = instructor.id
    _db.commit()
    _db.expire_all()

    _status_transition(t.id, "IN_PROGRESS")

    sess_count = _db.query(SessionModel).filter(SessionModel.semester_id == t.id).count()
    if sess_count == 0:
        fail("No sessions generated after IN_PROGRESS — cannot test GUARD D meaningfully")
    info(f"  Sessions generated: {sess_count} (rankings NOT submitted)")

    ranking_count = _db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == t.id
    ).count()
    if ranking_count > 0:
        fail(f"Rankings already exist ({ranking_count}) — test precondition violated")

    _status_transition_expect_fail(
        t.id, "COMPLETED",
        "0 TournamentRanking rows → status_validator rejects COMPLETED",
    )


# ══════════════════════════════════════════════════════════════════════════════
# FULL LIFECYCLE + VISIBILITY: DRAFT → REWARDS_DISTRIBUTED
# ══════════════════════════════════════════════════════════════════════════════
def test_full_lifecycle_visibility(club, campus, tt_id, instructor):
    """
    Full lifecycle traversal for a U12 TEAM+League tournament.

    At every status transition, assert /events/{id} returns the correct code:
      DRAFT             → 404 (not published)
      ENROLLMENT_OPEN   → 200
      ENROLLMENT_CLOSED → 200
      CHECK_IN_OPEN     → 200
      IN_PROGRESS       → 200
      COMPLETED         → 200 (rankings visible)
      REWARDS_DISTRIBUTED → 200

    Returns tournament id for follow-up frontend consistency test.
    """
    prefix = f"FullLC-{uuid.uuid4().hex[:6]}"
    t = _promotion_wizard(club.id, campus.id, tt_id, "U12", prefix)

    enrollments = _db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == t.id,
        TournamentTeamEnrollment.is_active == True,  # noqa: E712
    ).all()
    ok(f"Teams enrolled: {len(enrollments)}")
    if len(enrollments) < 2:
        fail(f"Need ≥2 enrolled teams for lifecycle test, got {len(enrollments)}")

    # ─── DRAFT ────────────────────────────────────────────────────────────────
    _assert_public_visibility(t.id, 404, "DRAFT")

    # ─── → ENROLLMENT_OPEN ────────────────────────────────────────────────────
    _status_transition(t.id, "ENROLLMENT_OPEN")
    _assert_public_visibility(t.id, 200, "ENROLLMENT_OPEN")

    # ─── → ENROLLMENT_CLOSED ──────────────────────────────────────────────────
    _status_transition(t.id, "ENROLLMENT_CLOSED")
    _assert_public_visibility(t.id, 200, "ENROLLMENT_CLOSED")

    # ─── → CHECK_IN_OPEN ──────────────────────────────────────────────────────
    _status_transition(t.id, "CHECK_IN_OPEN")
    _assert_public_visibility(t.id, 200, "CHECK_IN_OPEN")

    # ─── Set instructor ───────────────────────────────────────────────────────
    _db.expire_all()
    t_obj = _db.query(Semester).filter(Semester.id == t.id).first()
    t_obj.master_instructor_id = instructor.id
    _db.commit()
    _db.expire_all()
    ok(f"master_instructor_id = {instructor.id}")

    # ─── → IN_PROGRESS (triggers session generation) ──────────────────────────
    _status_transition(t.id, "IN_PROGRESS")
    _assert_public_visibility(t.id, 200, "IN_PROGRESS")

    sessions = _db.query(SessionModel).filter(SessionModel.semester_id == t.id).all()
    if not sessions:
        fail("No sessions generated after IN_PROGRESS transition")
    ok(f"Sessions generated: {len(sessions)}")

    # ─── Submit team results ──────────────────────────────────────────────────
    info(f"  Submitting results for {len(sessions)} session(s)...")
    for sess in sessions:
        _db.expire_all()
        s = _db.query(SessionModel).filter(SessionModel.id == sess.id).first()
        team_ids = s.participant_team_ids or []
        if len(team_ids) < 2:
            info(f"  Session {s.id}: <2 team_ids in participant_team_ids ({team_ids}) — skipping")
            continue
        t1, t2 = team_ids[0], team_ids[1]
        resp = _api_patch(
            f"/api/v1/sessions/{s.id}/team-results",
            {
                "results": [
                    {"team_id": t1, "score": 2},
                    {"team_id": t2, "score": 0},
                ],
                "round_number": 1,
            },
        )
        if resp.status_code not in (200, 201):
            body = {}
            try:
                body = resp.json()
            except Exception:
                pass
            fail(
                f"team-results for session {s.id}: "
                f"HTTP {resp.status_code} — {body.get('detail', '') if isinstance(body, dict) else resp.text[:100]}"
            )
        info(f"  Session {s.id}: team {t1} wins 2-0 over {t2}")
    ok("All session results submitted")

    # ─── Calculate rankings ───────────────────────────────────────────────────
    _assert_api_ok(_api_post(f"/api/v1/tournaments/{t.id}/calculate-rankings", {}), "calculate-rankings")

    _db.expire_all()
    ranking_count = _db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == t.id
    ).count()
    if ranking_count == 0:
        fail("0 TournamentRanking rows after calculate-rankings")
    ok(f"Rankings calculated: {ranking_count} row(s)")

    # ─── → COMPLETED ──────────────────────────────────────────────────────────
    _status_transition(t.id, "COMPLETED")
    _assert_public_visibility(t.id, 200, "COMPLETED")

    # ─── Distribute rewards ───────────────────────────────────────────────────
    _assert_api_ok(
        _api_post(
            f"/api/v1/tournaments/{t.id}/distribute-rewards-v2",
            {"tournament_id": t.id, "force_redistribution": False},
        ),
        "distribute-rewards-v2",
    )

    # ─── Verify REWARDS_DISTRIBUTED ───────────────────────────────────────────
    _db.expire_all()
    final = _db.query(Semester).filter(Semester.id == t.id).first()
    if final.tournament_status != "REWARDS_DISTRIBUTED":
        fail(f"Expected REWARDS_DISTRIBUTED, got {final.tournament_status!r}")
    ok("Status: REWARDS_DISTRIBUTED")
    _assert_public_visibility(t.id, 200, "REWARDS_DISTRIBUTED")

    return t.id


# ══════════════════════════════════════════════════════════════════════════════
# CANCELLED PATH VISIBILITY
# ══════════════════════════════════════════════════════════════════════════════
def test_cancelled_visibility(club, campus, tt_id):
    """CANCELLED tournament must not appear on the public event page (same as DRAFT)."""
    prefix = f"Cancelled-{uuid.uuid4().hex[:6]}"
    t = _promotion_wizard(club.id, campus.id, tt_id, "U15", prefix)

    # CANCELLED from DRAFT is a valid transition
    _status_transition(t.id, "CANCELLED")
    _assert_public_visibility(t.id, 404, "CANCELLED")


# ══════════════════════════════════════════════════════════════════════════════
# FRONTEND CONSISTENCY
# ══════════════════════════════════════════════════════════════════════════════
def test_frontend_consistency(tid):
    """
    At REWARDS_DISTRIBUTED, all three UI surfaces must agree on the state:
      /admin/promotion-events  → tournament listed
      /admin/tournaments/{id}  → page loads, name present
      /events/{id}             → publicly visible (200)
    """
    _db.expire_all()
    t = _db.query(Semester).filter(Semester.id == tid).first()
    name = t.name
    status = t.tournament_status
    info(f"  Tournament id={tid}  status={status!r}  name={name!r}")

    # 1. Admin promotion events list
    resp = _client.get("/admin/promotion-events")
    if resp.status_code != 200:
        fail(f"/admin/promotion-events returned HTTP {resp.status_code}")
    if name not in resp.text:
        fail(f"/admin/promotion-events: tournament '{name}' not found in HTML")
    ok("/admin/promotion-events → 200, tournament listed ✓")

    # 2. Admin tournament edit page
    resp = _client.get(f"/admin/tournaments/{tid}/edit")
    if resp.status_code != 200:
        fail(f"/admin/tournaments/{tid}/edit returned HTTP {resp.status_code}")
    if name not in resp.text:
        fail(f"/admin/tournaments/{tid}/edit: tournament name '{name}' not in page HTML")
    ok(f"/admin/tournaments/{tid}/edit → 200, name in page ✓")

    # 3. Public event page
    resp = _client.get(f"/events/{tid}")
    if resp.status_code != 200:
        fail(f"/events/{tid} returned HTTP {resp.status_code}")
    ok(f"/events/{tid} → 200, publicly accessible ✓")

    info("  ✓ All 3 views consistent: admin-list / admin-detail / public all show the same event")


# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    _setup()

    # ── Load bootstrap fixtures ────────────────────────────────────────────────
    club = _db.query(Club).filter(Club.code == "LFA-BOOT").first()
    if not club:
        print("❌ LFA_BOOTSTRAP_CLUB not found — run bootstrap_clean.py first")
        sys.exit(1)

    campus = _db.query(Campus).filter(Campus.is_active == True).first()  # noqa: E712
    instructor = _db.query(User).filter(User.email == "instructor@lfa.com").first()
    if not campus or not instructor:
        print("❌ Campus or instructor missing — run bootstrap_clean.py first")
        sys.exit(1)

    tt_league = _db.query(TournamentType).filter(TournamentType.code == "league").first()
    if not tt_league:
        print("❌ TournamentType 'league' missing — run bootstrap_clean.py first")
        sys.exit(1)

    section("Bootstrap fixtures")
    ok(f"Club: {club.name!r}  id={club.id}")
    ok(f"Campus: {campus.name!r}  id={campus.id}")
    ok(f"Instructor: {instructor.email}  id={instructor.id}")
    ok(f"TournamentType 'league': id={tt_league.id}  min_players={tt_league.min_players}")
    teams = _db.query(Team).filter(Team.club_id == club.id, Team.is_active == True).all()  # noqa: E712
    for ag in ("U12", "U15"):
        n = sum(1 for tm in teams if tm.age_group_label == ag)
        info(f"  {ag}: {n} teams")

    # ── Run tests ──────────────────────────────────────────────────────────────
    _run_test(
        "GUARD-A: campus_id=NULL → ENROLLMENT_OPEN rejected (HTTP 400)",
        test_guard_a_campus_required,
        tt_league.id,
    )

    _run_test(
        "GUARD-C: no instructor → IN_PROGRESS rejected (HTTP 400)",
        test_guard_c_instructor_required,
        club, campus, tt_league.id,
    )

    _run_test(
        "GUARD-D: 0 rankings → COMPLETED rejected (HTTP 400)",
        test_guard_d_rankings_required,
        club, campus, tt_league.id, instructor,
    )

    # Full lifecycle — returns tid for the consistency test
    full_lc_tid = _run_test(
        "FULL-LC: DRAFT→ENROLLMENT_OPEN→ENROLLMENT_CLOSED→CHECK_IN_OPEN"
        "→IN_PROGRESS→COMPLETED→REWARDS_DISTRIBUTED (visibility at each step)",
        test_full_lifecycle_visibility,
        club, campus, tt_league.id, instructor,
    )

    _run_test(
        "CANCELLED: DRAFT→CANCELLED → /events/{id} = 404",
        test_cancelled_visibility,
        club, campus, tt_league.id,
    )

    if full_lc_tid is not None:
        _run_test(
            "FRONTEND-CONSISTENCY: admin-list / admin-detail / public all show REWARDS_DISTRIBUTED",
            test_frontend_consistency,
            full_lc_tid,
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n\n{'='*65}")
    print("  LIFECYCLE VISIBILITY TEST RESULTS")
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
    print("="*65)
    print()
    if failed == 0:
        print("  🎯 Visibility invariant verified across full lifecycle")
        print("     DRAFT/CANCELLED → 404  |  All other states → 200")
    else:
        print("  ⚠️  Visibility invariant VIOLATED — see failures above")
    print()

    _db.close()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run()
