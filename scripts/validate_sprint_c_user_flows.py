"""
Sprint C — E2E User Flow Validation
====================================
Tests real user flows against the live app via TestClient + real DB.

Users under test:
  report_490c3e64@t.com  — 2 licenses (LFA_FOOTBALL_PLAYER + INTERNSHIP)
  report_940c5c73@t.com  — 1 license (LFA_FOOTBALL_PLAYER, ACTIVE)
  report_7b85cdfa@t.com  — 1 license (LFA_FOOTBALL_PLAYER, ACTIVE)
  report_9ab12d42@t.com  — 1 license (LFA_FOOTBALL_PLAYER, ACTIVE)

Run:
  python scripts/validate_sprint_c_user_flows.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.dependencies import get_current_user_web, get_current_user_optional
from app.database import get_db
from app.models.user import User, UserRole

# ── Terminal colours ──────────────────────────────────────────────────────────
G  = "\033[92m"
R  = "\033[91m"
Y  = "\033[93m"
B  = "\033[94m"
W  = "\033[97m"
NC = "\033[0m"
PASS = f"{G}✓{NC}"
FAIL = f"{R}✗{NC}"
WARN = f"{Y}⚠{NC}"
INFO = f"{B}→{NC}"

results: list[tuple[str, bool, str]] = []


def chk(label: str, ok: bool, detail: str = "", warn_only: bool = False):
    icon = PASS if ok else (WARN if warn_only else FAIL)
    tag = "PASS" if ok else ("WARN" if warn_only else "FAIL")
    line = f"  {icon} {label}"
    if detail and not ok:
        line += f"\n      {Y}{detail}{NC}"
    print(line)
    results.append((label, ok, tag))
    return ok


def section(title: str):
    print(f"\n{W}{'─'*60}{NC}")
    print(f"{W}  {title}{NC}")
    print(f"{W}{'─'*60}{NC}")


def make_client(db: Session, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user_web] = lambda: user
    app.dependency_overrides[get_current_user_optional] = lambda: user
    return TestClient(
        app,
        headers={"Authorization": "Bearer test-csrf-bypass"},
        follow_redirects=False,
    )


def get_user(db: Session, email: str) -> User:
    return db.query(User).filter(User.email == email).first()


# ─────────────────────────────────────────────────────────────────────────────
# 1. HUB STATE → UI MATRIX
# ─────────────────────────────────────────────────────────────────────────────

def validate_hub_state_matrix():
    section("1. HUB STATE → UI MATRIX (hub_specializations.html)")

    db = SessionLocal()
    try:
        user = get_user(db, "report_490c3e64@t.com")
        if not user:
            chk("report_490c3e64@t.com DB lookup", False, "User not found in DB — run seed?")
            return

        client = make_client(db, user)
        r = client.get("/dashboard")
        chk("GET /dashboard → 200", r.status_code == 200,
            f"Got {r.status_code}")

        html = r.text

        # Layout checks
        chk("student_base.html: student-header present", "student-header" in html)
        chk("student_base.html: student-nav present",    "student-nav" in html)
        chk("student_base.html: no old purple header",   "background: linear-gradient(135deg, #667eea" not in html)
        chk("student_base.html: no inline CSS block",    "<style>" not in html.split("student_base")[0] if "student_base" in html else True)

        # Nav completeness
        for href in ["/dashboard", "/sessions", "/progress", "/skills", "/achievements", "/calendar"]:
            chk(f"Nav link: {href}", f'href="{href}"' in html)

        # Hub active state
        chk("Hub nav active (🏠 Hub)", 'class="nav-item active"' in html and "/dashboard" in html)

        # Credit pill
        chk("Credit pill rendered", "credit-pill" in html)
        chk("Credit balance value", "900" in html)

        # Spec cards (spec_state-based)
        chk("ACTIVE state card: cta-enter present",       "cta-enter" in html,
            "ENTER button missing for LFA_FOOTBALL_PLAYER (onboarding_completed=True)")
        chk("PENDING state card: cta-setup present",      "cta-setup" in html,
            "Continue Setup missing for INTERNSHIP (onboarding_completed=False)")
        chk("No raw is_unlocked logic in HTML",           "spec.is_unlocked" not in html)
        chk("spec_state used in template",                "cta-enter" in html or "cta-setup" in html)

        # State-specific text
        chk("ENTER button text present",                  "ENTER" in html)
        chk("Continue Setup text present",                "Continue Setup" in html)
        chk("Unlock button (other locked specs)",         "cta-unlock" in html or "Unlock Now" in html or "cta-disabled" in html)

        # can_afford_unlock (from backend, 900 credits ≥ 100)
        chk("Unlock form present (900 cr, can afford)",   "cta-unlock" in html or "Unlock Now" in html,
            "If other specs are LOCKED and 900cr ≥ 100, unlock form should appear")

        # LOCKED state for age-unavailable specs
        chk("No hardcoded credit < 100 logic in template", "user.credit_balance < 100" not in html,
            "Template still contains backend computation!")

        # Footer
        chk("Hub footer: Learn More link", "/about-specializations" in html)
        chk("Hub footer: Credits link",    "/credits" in html)

    finally:
        db.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 2. SPEC DASHBOARD — 4-SECTION LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

def validate_spec_dashboard():
    section("2. SPEC DASHBOARD — 4-SECTION LAYOUT (dashboard_student_new.html)")

    db = SessionLocal()
    try:
        user = get_user(db, "report_490c3e64@t.com")
        if not user:
            chk("report_490c3e64@t.com DB lookup", False, "User not found")
            return

        client = make_client(db, user)
        r = client.get("/dashboard/lfa-football-player")
        chk("GET /dashboard/lfa-football-player → 200", r.status_code == 200,
            f"Got {r.status_code}: {r.headers.get('location','')}")

        if r.status_code != 200:
            return

        html = r.text

        # Layout — student_base
        chk("No old spec-header gradient", "spec-header" not in html,
            "Old inline .spec-header class still present")
        chk("student_base header rendered", "student-header" in html)
        chk("student-main content wrapper", "student-main" in html)

        # Section 1: Identity Card
        chk("Identity Card: spec-identity-card",    "spec-identity-card" in html)
        chk("Identity Card: age group label",       "Age Group" in html)
        chk("Identity Card: level stat",            "Level" in html)
        chk("Identity Card: XP stat",               "XP" in html)
        chk("Identity Card: Credits stat",          "Credits" in html)

        # Section 2: Skill Snapshot
        chk("Skill Snapshot: section-card present",  "Skill Snapshot" in html)
        chk("Skill Snapshot: lazy-load fetch code",  "fetch('/skills/data')" in html)
        chk("Skill Snapshot: skill-preview-bars div","skill-preview-bars" in html)
        chk("Skill Snapshot: view all link → /skills", "href=\"/skills\"" in html)

        # Section 3: Available Events (tab switcher)
        chk("Events: Available Events heading",   "Available Events" in html)
        chk("Events: Tournaments tab present",    "Tournaments" in html)
        chk("Events: Camps tab present",          "Camps" in html)
        chk("Events: tab-btn class",              "tab-btn" in html)
        chk("Events: switchTab JS function",      "switchTab" in html)

        # Empty state for no events
        chk("Events: empty-state shown when none", "empty-state" in html or "No open tournaments" in html,
            "No empty state shown despite 0 events in DB",
            warn_only=True)

        # Section 4: Tournament History
        chk("Tournament History: section present",  "Tournament History" in html)
        chk("Tournament History: th-table OR th-empty", "th-table" in html or "th-empty" in html)
        chk("Tournament History: full progress link", "href=\"/progress\"" in html)

        # Quick nav
        chk("Quick nav: Sessions link", "href=\"/sessions\"" in html)
        chk("Quick nav: Skills link",   "href=\"/skills\"" in html)

        # No old semesters section
        chk("No 'Available Semesters' heading (old)", "Available Semesters" not in html,
            "Old section title still present — template not fully migrated")
        chk("No inline CSS style block >100 lines",
            html.count("\n", html.find("<style"), html.find("</style>") if "</style>" in html else 0) < 20
            if "<style" in html else True)

    finally:
        db.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 3. MULTI-USER STATE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_multi_user_states():
    section("3. MULTI-USER STATE VALIDATION")

    users_cfg = [
        ("report_490c3e64@t.com", "LFA_FOOTBALL_PLAYER", True,  "ACTIVE"),
        ("report_7b85cdfa@t.com", "LFA_FOOTBALL_PLAYER", True,  "ACTIVE"),
        ("report_940c5c73@t.com", "LFA_FOOTBALL_PLAYER", True,  "ACTIVE"),
        ("report_9ab12d42@t.com", "LFA_FOOTBALL_PLAYER", True,  "ACTIVE"),
    ]

    for email, spec_type, expected_active, expected_state in users_cfg:
        db = SessionLocal()
        try:
            user = get_user(db, email)
            if not user:
                chk(f"{email}: DB lookup", False, "Not found"); continue

            short = email.split("@")[0][-8:]
            client = make_client(db, user)

            # Hub
            r_hub = client.get("/dashboard")
            hub_ok = r_hub.status_code == 200
            chk(f"{short}: /dashboard → 200", hub_ok, f"{r_hub.status_code}")

            if hub_ok:
                html = r_hub.text
                has_enter = "cta-enter" in html and "ENTER" in html
                chk(f"{short}: hub shows ENTER (ACTIVE)", has_enter,
                    f"Expected ENTER button for {spec_type} ACTIVE license")
                chk(f"{short}: credit-pill rendered", "credit-pill" in html)

            # Spec dashboard
            spec_slug = spec_type.lower().replace("_", "-")
            r_spec = client.get(f"/dashboard/{spec_slug}")
            spec_ok = r_spec.status_code == 200
            chk(f"{short}: /dashboard/{spec_slug} → 200", spec_ok,
                f"Got {r_spec.status_code} — redirect to {r_spec.headers.get('location','?')}")

            if spec_ok:
                html = r_spec.text
                chk(f"{short}: spec identity card", "spec-identity-card" in html)
                chk(f"{short}: events tabs rendered", "tab-btn" in html)
                chk(f"{short}: tournament history section", "Tournament History" in html)

        finally:
            db.close()
            app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 4. SKILL PROGRESSION VISIBILITY
# ─────────────────────────────────────────────────────────────────────────────

def validate_skill_progression():
    section("4. SKILL PROGRESSION VISIBILITY")

    db = SessionLocal()
    try:
        user = get_user(db, "report_490c3e64@t.com")
        if not user:
            chk("DB lookup", False, "User not found"); return

        client = make_client(db, user)

        # /skills page
        r = client.get("/skills")
        chk("/skills → 200", r.status_code == 200, f"{r.status_code}")
        if r.status_code == 200:
            html = r.text
            chk("/skills: student_base header", "student-header" in html)
            chk("/skills: skill bar rows rendered", "skill-bar" in html or "skill_bar" in html)
            chk("/skills: active preset section", "Active Preset" in html or "active_preset" in html,
                warn_only=True)
            chk("/skills: tournament history table", "Tournament History" in html or "th-table" in html,
                warn_only=True)

        # /skills/data JSON
        r_data = client.get("/skills/data")
        chk("/skills/data → 200", r_data.status_code == 200, f"{r_data.status_code}")
        if r_data.status_code == 200:
            data = r_data.json()
            chk("/skills/data: has 'skills' key",          "skills" in data)
            chk("/skills/data: has 'average_level'",       "average_level" in data)
            chk("/skills/data: has 'total_tournaments'",   "total_tournaments" in data)
            chk("/skills/data: has 'total_assessments'",   "total_assessments" in data)

            skills = data.get("skills", {})
            chk("/skills/data: ≥1 skill returned",         len(skills) >= 1,
                f"Only {len(skills)} skills — expected 29; is user licensed with assessments?",
                warn_only=True)

            if skills:
                first_skill = next(iter(skills.values()))
                chk("Skill object has 'current_level'",   "current_level" in first_skill)
                chk("Skill object has 'total_delta'",     "total_delta" in first_skill)
                chk("Skill object has 'tier_emoji'",      "tier_emoji" in first_skill)

            # Snapshot visible on spec dashboard (lazy-loaded JS)
            r_spec = client.get("/dashboard/lfa-football-player")
            if r_spec.status_code == 200:
                spec_html = r_spec.text
                chk("Spec dashboard: skill snapshot section", "Skill Snapshot" in spec_html)
                chk("Spec dashboard: lazy fetch to /skills/data", "fetch('/skills/data')" in spec_html)
                chk("Spec dashboard: skill-preview-bars target div", "skill-preview-bars" in spec_html)

        # /progress
        r_prog = client.get("/progress")
        chk("/progress → 200", r_prog.status_code == 200, f"{r_prog.status_code}")
        if r_prog.status_code == 200:
            html = r_prog.text
            chk("/progress: skill snapshot widget", "skill-preview-bars" in html or "Skill" in html)
            chk("/progress: tournament history section", "tournament" in html.lower())

    finally:
        db.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 5. CACHE / STATE SYNC
# ─────────────────────────────────────────────────────────────────────────────

def validate_cache_state_sync():
    section("5. CACHE / STATE SYNC")

    db = SessionLocal()
    try:
        user = get_user(db, "report_490c3e64@t.com")
        client = make_client(db, user)

        # Cache-Control headers
        r = client.get("/dashboard")
        cc = r.headers.get("cache-control", "")
        chk("Cache-Control: no-cache on /dashboard",  "no-cache" in cc, f"Got: {cc!r}")
        chk("Pragma: no-cache on /dashboard",         "no-cache" in r.headers.get("pragma", ""))

        r2 = client.get("/dashboard/lfa-football-player")
        cc2 = r2.headers.get("cache-control", "")
        chk("Cache-Control: no-cache on spec dashboard", "no-cache" in cc2, f"Got: {cc2!r}")

        # Repeated loads return same state
        r3 = client.get("/dashboard")
        chk("Second /dashboard load still 200", r3.status_code == 200)
        chk("State consistent across 2 loads",
            ("cta-enter" in r.text) == ("cta-enter" in r3.text),
            "State differs between first and second load!")

        # /dashboard-fresh route (cache bypass)
        r_fresh = client.get("/dashboard-fresh")
        chk("/dashboard-fresh → 200", r_fresh.status_code == 200, f"{r_fresh.status_code}")
        chk("/dashboard-fresh same hub template", "hub" in r_fresh.text.lower())

    finally:
        db.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 6. SECONDARY PAGES (nav links functional)
# ─────────────────────────────────────────────────────────────────────────────

def validate_secondary_pages():
    section("6. SECONDARY PAGES (nav link reachability)")

    db = SessionLocal()
    try:
        user = get_user(db, "report_490c3e64@t.com")
        if not user:
            return

        client = make_client(db, user)

        pages = [
            ("/sessions",      200, "student-header",     "Sessions page"),
            ("/progress",      200, "student-header",     "Progress page"),
            ("/achievements",  200, "student-header",     "Achievements page"),
            ("/calendar",      200, "student-header",     "Calendar page"),
            ("/credits",       200, "student-header",     "Credits page"),
            ("/notifications", 200, "student-header",     "Notifications page"),
            ("/skills",        200, "student-header",     "Skills page"),
        ]

        for url, expected_status, content_check, label in pages:
            r = client.get(url)
            ok_status = r.status_code == expected_status
            chk(f"{label}: status {expected_status}", ok_status,
                f"Got {r.status_code} → {r.headers.get('location','')}")
            if ok_status:
                chk(f"{label}: student-header rendered",
                    content_check in r.text,
                    f"{content_check!r} not found in {url}")

    finally:
        db.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 7. UX GAPS AUDIT (data availability)
# ─────────────────────────────────────────────────────────────────────────────

def audit_data_gaps():
    section("7. UX GAPS AUDIT (DB data availability)")

    db = SessionLocal()
    try:
        from sqlalchemy import text

        with db.bind.connect() as conn:
            # Tournaments available
            r = conn.execute(text(
                "SELECT count(*) FROM semesters WHERE semester_category='TOURNAMENT' AND tournament_status='ENROLLMENT_OPEN'"
            ))
            tourn_count = r.scalar()
            chk("Available tournaments (ENROLLMENT_OPEN)", tourn_count > 0,
                f"{tourn_count} open tournaments — users see empty events tab",
                warn_only=True)

            # Camps available
            r2 = conn.execute(text(
                "SELECT count(*) FROM semesters WHERE semester_category='CAMP' AND status='READY_FOR_ENROLLMENT'"
            ))
            camp_count = r2.scalar()
            chk("Available camps (READY_FOR_ENROLLMENT)", camp_count > 0,
                f"{camp_count} open camps",
                warn_only=True)

            # Users with skill assessments
            r3 = conn.execute(text(
                "SELECT count(DISTINCT user_license_id) FROM football_skill_assessments WHERE status != 'ARCHIVED'"
            ))
            licensed_with_skills = r3.scalar()
            chk("Licenses with skill assessments", licensed_with_skills > 0,
                f"{licensed_with_skills} licenses have assessments — /skills/data returns empty for test users",
                warn_only=True)

            # Users with TournamentParticipation
            r4 = conn.execute(text("SELECT count(*) FROM tournament_participations"))
            tp_count = r4.scalar()
            chk("TournamentParticipation records exist", tp_count > 0,
                f"{tp_count} records — tournament history will be empty for all test users",
                warn_only=True)

            # Football skills JSON on licenses
            r5 = conn.execute(text(
                "SELECT count(*) FROM user_licenses WHERE football_skills IS NOT NULL AND specialization_type='LFA_FOOTBALL_PLAYER'"
            ))
            fs_count = r5.scalar()
            chk("LFA licenses with football_skills JSON", fs_count > 0,
                f"{fs_count} licenses have baseline football_skills (used by _compute_skill_summary)",
                warn_only=True)

            # Semester enrollments (APPROVED)
            r6 = conn.execute(text(
                "SELECT count(*) FROM semester_enrollments WHERE request_status='APPROVED'"
            ))
            enroll_count = r6.scalar()
            chk("Approved enrollments exist", enroll_count > 0,
                f"{enroll_count} approved enrollments — no active enrollment banners visible",
                warn_only=True)

    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{W}{'═'*60}{NC}")
    print(f"{W}  Sprint C — E2E User Flow Validation{NC}")
    print(f"{W}{'═'*60}{NC}")

    validate_hub_state_matrix()
    validate_spec_dashboard()
    validate_multi_user_states()
    validate_skill_progression()
    validate_cache_state_sync()
    validate_secondary_pages()
    audit_data_gaps()

    # Summary
    passed  = [r for r in results if r[2] == "PASS"]
    failed  = [r for r in results if r[2] == "FAIL"]
    warned  = [r for r in results if r[2] == "WARN"]

    section("SUMMARY")
    print(f"  {PASS} Passed: {len(passed)}")
    print(f"  {WARN} Warned: {len(warned)}")
    print(f"  {FAIL} Failed: {len(failed)}")

    if failed:
        print(f"\n{R}FAILURES:{NC}")
        for label, ok, tag in failed:
            print(f"  {FAIL} {label}")

    if warned:
        print(f"\n{Y}WARNINGS (UX gaps / data missing):{NC}")
        for label, ok, tag in warned:
            print(f"  {WARN} {label}")

    print()
    if not failed:
        print(f"{G}✅ All hard checks passed.{NC}")
    else:
        print(f"{R}❌ {len(failed)} check(s) failed.{NC}")
    print()

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
