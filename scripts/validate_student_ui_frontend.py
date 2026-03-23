"""
Frontend validation script — Student UI/UX Optimization (2026-03-18)

Verifies that all 7 modules' changes are present in the actual HTML rendered
by the live FastAPI app via TestClient. Checks:
  - Module 1: nav links in unified_header.html pages
  - Module 2: achievements page redesign elements
  - Module 3: sessions flash banner (no alert())
  - Module 4: progress.html mobile breakpoints in CSS
  - Module 5: notifications.html mobile breakpoints in CSS
  - Module 6: calendar error fallback div
  - Viewport check: CSS breakpoint rules actually present in rendered HTML

Run: python scripts/validate_student_ui_frontend.py
"""

import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event as sa_event

from app.main import app
from app.database import engine, get_db
from app.dependencies import get_current_user_web, get_current_user_optional
from app.models.user import User, UserRole
from app.core.security import get_password_hash

# ── helpers ──────────────────────────────────────────────────────────────────

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
INFO = "\033[94m→\033[0m"

results = []

def check(label: str, condition: bool, detail: str = ""):
    icon = PASS if condition else FAIL
    status = "PASS" if condition else "FAIL"
    msg = f"  {icon} {label}"
    if detail and not condition:
        msg += f"\n      {detail}"
    print(msg)
    results.append((label, condition))
    return condition


def make_client(db_session, user: User):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user_web] = lambda: user
    # /credits uses get_current_user_optional — override it too
    app.dependency_overrides[get_current_user_optional] = lambda: user
    client = TestClient(
        app,
        headers={"Authorization": "Bearer test-csrf-bypass"},
        follow_redirects=False,
    )
    return client


# ── DB setup (SAVEPOINT-isolated) ────────────────────────────────────────────

connection = engine.connect()
transaction = connection.begin()
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=connection)
db = TestSession()
connection.begin_nested()

@sa_event.listens_for(db, "after_transaction_end")
def restart_savepoint(session, txn):
    if txn.nested and not txn._parent.nested:
        session.begin_nested()


def make_student(onboarding=True) -> User:
    u = User(
        email=f"validate-ui-{uuid.uuid4().hex[:8]}@lfa.com",
        name="UI Validator Student",
        password_hash=get_password_hash("test"),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=onboarding,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def make_admin() -> User:
    u = User(
        email=f"validate-ui-admin-{uuid.uuid4().hex[:8]}@lfa.com",
        name="UI Validator Admin",
        password_hash=get_password_hash("test"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ── Run validations ───────────────────────────────────────────────────────────

try:
    student = make_student(onboarding=True)
    admin   = make_admin()

    with make_client(db, student) as c:

        # ──────────────────────────────────────────────────────────────────
        print("\n── MODULE 1: Student Navigation Links (student_base.html) ──")
        # All student pages now extend student_base.html (student-nav class)
        for path in ["/achievements", "/notifications"]:
            resp = c.get(path)
            html = resp.text
            check(f"GET {path} → 200",            resp.status_code == 200)
            check(f"GET {path} → nav: /sessions",  'href="/sessions"'     in html)
            check(f"GET {path} → nav: /progress",  'href="/progress"'     in html)
            check(f"GET {path} → nav: /skills",    'href="/skills"'       in html)
            check(f"GET {path} → nav: /achievements", 'href="/achievements"' in html)
            check(f"GET {path} → student-nav class", 'student-nav' in html)

        # /credits has its own header (not unified_header.html) — check nav links separately
        resp = c.get("/credits")
        html = resp.text
        check("GET /credits → 200",                 resp.status_code == 200)
        check("GET /credits → nav: /sessions",      'href="/sessions"'     in html)
        check("GET /credits → nav: /progress",      'href="/progress"'     in html)
        check("GET /credits → nav: /skills",        'href="/skills"'       in html)
        check("GET /credits → nav: /achievements",  'href="/achievements"' in html)

        # ──────────────────────────────────────────────────────────────────
        print("\n── MODULE 2: Achievements Page Redesign ──")
        resp = c.get("/achievements")
        html = resp.text
        check("achievements → 200",                 resp.status_code == 200)
        check("achievements → gradient header",     "linear-gradient(135deg, #1a1a2e" in html)
        check("achievements → nav links /progress present", 'href="/progress"' in html)
        check("achievements → stats-grid",          "stats-grid" in html)
        check("achievements → achievement-grid",    "achievement-grid" in html)
        check("achievements → unlocked card class", "achievement-card" in html)
        check("achievements → XP badge",            "xp-badge" in html or "XP" in html)
        check("achievements → mobile bp 640px",     "@media (max-width: 640px)" in html)
        check("achievements → empty state OR grid", "empty-state" in html or "achievement-card" in html)
        # Ensure OLD style (from style.css .cards-grid fixed 4-col) is gone
        check("achievements → no fixed 4-col grid", "grid-template-columns: repeat(4, 1fr)" not in html)

        # ──────────────────────────────────────────────────────────────────
        print("\n── MODULE 3: Sessions Flash Banner (no alert dialogs) ──")
        resp = c.get("/sessions")
        html = resp.text
        check("sessions → 200",                     resp.status_code == 200)
        check("sessions → flash-banner div present", 'id="flash-banner"' in html)
        check("sessions → no alert('✅ ...",         "alert('✅" not in html)
        check("sessions → no alert('ℹ️ ...",         "alert('ℹ️" not in html)
        check("sessions → no alert('❌ ...",         "alert('❌" not in html)
        check("sessions → mobile bp 640px",         "@media (max-width: 640px)" in html)
        check("sessions → session-actions class",   "session-actions" in html)

        # ──────────────────────────────────────────────────────────────────
        print("\n── MODULE 4: Progress Mobile Breakpoints ──")
        resp = c.get("/progress")
        html = resp.text
        check("progress → 200",                     resp.status_code == 200)
        check("progress → Skill Snapshot widget",   "Skill Snapshot" in html)
        check("progress → mobile bp 768px",         "@media (max-width: 768px)" in html)
        check("progress → mobile bp 480px",         "@media (max-width: 480px)" in html)
        check("progress → stats-grid class",        "stats-grid" in html)
        check("progress → semester-card class",     "semester-card" in html)

        # ──────────────────────────────────────────────────────────────────
        print("\n── MODULE 5: Notifications Mobile Breakpoints ──")
        resp = c.get("/notifications")
        html = resp.text
        check("notifications → 200",                resp.status_code == 200)
        check("notifications → mobile bp 640px",    "@media (max-width: 640px)" in html)
        check("notifications → page-content class", "page-content" in html)
        check("notifications → notif-card class",   "notif-card" in html)
        check("notifications → flex-direction: column", "flex-direction: column" in html)

        # ──────────────────────────────────────────────────────────────────
        print("\n── MODULE 6: Calendar Error Fallback ──")
        resp = c.get("/calendar")
        html = resp.text
        check("calendar → 200",                     resp.status_code == 200)
        check("calendar → error fallback div",      'id="calendar-error"' in html)
        check("calendar → fallback link to /sessions", 'href="/sessions"' in html)
        check("calendar → fallback initially hidden", "display:none" in html or "display: none" in html)
        check("calendar → FullCalendar undefined check + show fallback",
              "calendar-error" in html and "FullCalendar" in html and "display = 'block'" in html)

        # ──────────────────────────────────────────────────────────────────
        print("\n── VIEWPORT: CSS Breakpoint Coverage Audit ──")
        viewport_checks = {
            "/achievements":  ["640px", "380px"],
            "/sessions":      ["640px"],
            "/progress":      ["768px", "480px"],
            "/notifications": ["640px"],
            "/calendar":      ["768px"],
        }
        for path, expected_bps in viewport_checks.items():
            resp = c.get(path)
            html = resp.text
            for bp in expected_bps:
                check(f"Viewport {bp} in {path}", bp in html)

    # ──────────────────────────────────────────────────────────────────────
    print("\n── ACCESS CONTROL: Admin cannot access achievements ──")
    with make_client(db, admin) as ca:
        resp = ca.get("/achievements")
        check("achievements (admin) → 303 redirect",  resp.status_code == 303)
        check("achievements (admin) → redirects to /dashboard",
              resp.headers.get("location", "").endswith("/dashboard"))

    # ──────────────────────────────────────────────────────────────────────
    print("\n── SKILLS page: still intact after UI changes ──")
    with make_client(db, student) as c:
        resp = c.get("/skills")
        html = resp.text
        check("skills → 200",                       resp.status_code == 200)
        check("skills → Skill Progression header",  "Skill Progression" in html)
        check("skills → lazy-load JS present",      "fetch('/skills/data')" in html)
        check("skills → tier colors in CSS",        "#6b7280" in html and "#3b82f6" in html)  # BEGINNER + DEVELOPING (matches --tier-* tokens)

finally:
    db.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()

# ── Summary ───────────────────────────────────────────────────────────────────

total  = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed

print(f"\n{'═'*55}")
print(f"  Frontend Validation: {passed}/{total} checks passed")
if failed:
    print(f"\n  FAILED checks:")
    for label, ok in results:
        if not ok:
            print(f"    ✗ {label}")
print(f"{'═'*55}\n")

sys.exit(0 if failed == 0 else 1)
