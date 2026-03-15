"""
Playwright E2E — Admin User Management UI Tests
================================================

Tests /admin/users and /admin/users/{id}/edit pages with:
  - Headed Playwright browser (PYTEST_HEADLESS=false)
  - Fresh test user per test (UUID-based, auto-cleaned)
  - Both UI state assertions and direct DB state assertions
  - Screenshots at every major step

Run:
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=400 pytest tests/e2e/admin_ui/ -v -s \\
        --html=tests/e2e/admin_ui/report.html --self-contained-html

Clean DB requirement:
    Admin user (admin@lfa.com) must exist — seeded from ADMIN_EMAIL/.env.
    Test target user is created fresh for each test class and deleted after.
"""

import os
import uuid
from pathlib import Path
from datetime import datetime, timezone

import pytest

from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.credit_transaction import CreditTransaction, TransactionType
from app.models.license import UserLicense, LicenseProgression
from app.models.specialization import SpecializationType

# ── Config ─────────────────────────────────────────────────────────────────────

APP_URL = os.environ.get("API_URL", "http://localhost:8000")
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


# ── Helpers ─────────────────────────────────────────────────────────────────────

def ss(page, name: str) -> None:
    """Save a timestamped screenshot."""
    ts = datetime.now().strftime("%H%M%S")
    path = SCREENSHOTS_DIR / f"{ts}_{name}.png"
    page.screenshot(path=str(path), full_page=True)


def admin_login(page) -> None:
    """Log in as admin and wait for redirect to dashboard.

    base.html JS handles CSRF automatically for all form submits:
      - Intercepts every form submit at the document level (useCapture=true)
      - Reads csrf_token cookie and adds X-CSRF-Token header via fetch()
    No extra Playwright route interceptor is needed.
    """
    page.goto(f"{APP_URL}/login")
    page.wait_for_load_state("networkidle")
    page.fill("input[name=email]", os.environ.get("ADMIN_EMAIL", "admin@lfa.com"))
    page.fill("input[name=password]", os.environ.get("ADMIN_PASSWORD", "admin123"))
    ss(page, "01_login_form_filled")
    page.click("button[type=submit]")
    page.wait_for_url(f"{APP_URL}/dashboard*", timeout=10000)
    ss(page, "02_logged_in_dashboard")


def reload_user(db_session: Session, user_id: int) -> User:
    """Expire session cache and return fresh user from DB."""
    db_session.expire_all()
    return db_session.query(User).filter(User.id == user_id).first()


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — /admin/users List Page
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminUsersListPage:
    """
    UI-01 through UI-05: /admin/users page load, table, and filters.

    Clean DB: admin user exists; target_user created fresh.
    """

    def test_ui01_admin_login(self, page):
        """UI-01: Admin logs in and lands on dashboard."""
        admin_login(page)
        assert "/dashboard" in page.url
        assert "Internal Server Error" not in page.content()
        ss(page, "UI01_dashboard")

    def test_ui02_users_page_loads_with_table(self, page, target_user):
        """UI-02: /admin/users renders table with expected headers."""
        admin_login(page)
        page.goto(f"{APP_URL}/admin/users")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert "Internal Server Error" not in content
        assert "Users" in content
        # Table headers
        for header in ["Name", "Email", "Role", "Status"]:
            assert header in content, f"Column '{header}' missing from users table"

        ss(page, "UI02_users_page")

    def test_ui03_search_by_email_finds_target_user(self, page, target_user):
        """UI-03: Search by target user's email shows only that user."""
        admin_login(page)

        # Navigate with search param (GET form — no CSRF needed)
        page.goto(f"{APP_URL}/admin/users?search={target_user.email}")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert target_user.name in content, f"Target user '{target_user.name}' not found in search results"
        assert target_user.email in content

        ss(page, "UI03_search_target_user")

    def test_ui04_filter_by_role_student(self, page, target_user):
        """UI-04: Filtering by role=student shows student users."""
        admin_login(page)
        page.goto(f"{APP_URL}/admin/users?role_filter=student&search={target_user.email}")
        page.wait_for_load_state("networkidle")

        content = page.content()
        # Target user is a student → should appear
        assert target_user.name in content
        # No admin users should be in results when filtered by student + specific email
        ss(page, "UI04_filter_role_student")

    def test_ui05_filter_by_status_active(self, page, target_user):
        """UI-05: Filtering by status=active includes the active target user."""
        admin_login(page)
        page.goto(f"{APP_URL}/admin/users?status_filter=active&search={target_user.email}")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert target_user.name in content, "Active target user not in active filter results"
        ss(page, "UI05_filter_status_active")

    def test_ui05b_filter_by_status_inactive_hides_active_user(self, page, target_user):
        """UI-05b: Filtering by status=inactive hides the active target user."""
        admin_login(page)
        page.goto(f"{APP_URL}/admin/users?status_filter=inactive&search={target_user.email}")
        page.wait_for_load_state("networkidle")

        content = page.content()
        # Active user should NOT appear in inactive filter
        assert target_user.name not in content, "Active user appeared in inactive filter"
        ss(page, "UI05b_filter_status_inactive_empty")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — /admin/users/{id}/edit Page
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminUserEditPage:
    """
    UI-06 through UI-12: /admin/users/{id}/edit page workflows.

    Each test:
      - Navigates directly to the edit page for target_user
      - Performs a UI action
      - Asserts both UI feedback AND DB state
    """

    def _go_edit(self, page, target_user):
        """Navigate to the edit page for target_user."""
        admin_login(page)
        page.goto(f"{APP_URL}/admin/users/{target_user.id}/edit")
        page.wait_for_load_state("networkidle")
        content = page.content()
        assert "Internal Server Error" not in content
        assert "Basic Information" in content
        assert "Credit Management" in content
        assert "License Management" in content
        return content

    def test_ui06_edit_page_renders_all_five_sections(self, page, target_user):
        """UI-06: Edit page shows all 5 sections."""
        content = self._go_edit(page, target_user)

        for section in [
            "Basic Information",
            "Reset Password",
            "Credit Management",
            "License Management",
            "Profile Status",
        ]:
            assert section in content, f"Section '{section}' missing from edit page"

        # Verify current balance displayed
        assert str(target_user.credit_balance or 0) in content

        ss(page, "UI06_edit_page_all_sections")

    def test_ui07_save_basic_info_changes_name(self, page, target_user, db_session):
        """UI-07: Changing user name and saving updates DB and redirects."""
        self._go_edit(page, target_user)

        new_name = f"Updated Name {uuid.uuid4().hex[:6]}"
        page.fill("input[name=name]", new_name)
        ss(page, "UI07a_name_filled")

        page.click("button[type=submit]:has-text('Save Changes')")
        page.wait_for_url(f"{APP_URL}/admin/users*", timeout=8000)

        ss(page, "UI07b_after_save")

        # DB assertion
        u = reload_user(db_session, target_user.id)
        assert u.name == new_name, f"Name not updated in DB: expected '{new_name}', got '{u.name}'"

    def test_ui08_reset_password_updates_hash(self, page, target_user, db_session):
        """UI-08: Reset password form updates password_hash in DB."""
        self._go_edit(page, target_user)

        old_hash = target_user.password_hash
        new_pw = "newSecurePass99"

        # Fill password reset form (Section 2)
        page.fill("input[name=new_password]", new_pw)
        ss(page, "UI08a_password_filled")

        # Server returns 303 → resp.redirected=true → window.location.href=resp.url
        with page.expect_navigation(timeout=10000):
            page.click("button:has-text('Reset Password')")
        page.wait_for_load_state("networkidle")

        ss(page, "UI08b_after_reset")

        # UI: success message in content or URL
        assert "Password has been reset" in page.content() or "reset" in page.url.lower()

        # DB assertion
        u = reload_user(db_session, target_user.id)
        assert u.password_hash != old_hash, "Password hash was not changed in DB"

    def test_ui09_grant_credit_increases_balance_and_shows_history(
        self, page, target_user, db_session
    ):
        """UI-09: Grant 300 credits → balance +300, CreditTransaction row in DB, history in UI."""
        initial_balance = target_user.credit_balance or 0
        self._go_edit(page, target_user)

        # Scroll to credit section
        page.evaluate("document.getElementById('credits')?.scrollIntoView()")
        page.wait_for_timeout(300)

        # Fill grant credit form
        # Grant section: the + form is inside the green box
        grant_form = page.locator("form[action*='grant-credit']")
        grant_form.locator("input[name=amount]").fill("300")
        grant_form.locator("input[name=reason]").fill("E2E test reward")
        ss(page, "UI09a_grant_credit_form_filled")

        with page.expect_navigation(timeout=8000):
            grant_form.locator("button[type=submit]").click()
        page.wait_for_load_state("networkidle")

        ss(page, "UI09b_after_grant_credit")

        # UI assertion: new balance displayed
        content = page.content()
        expected_balance = initial_balance + 300
        assert str(expected_balance) in content, f"Expected balance {expected_balance} not shown in UI"

        # UI assertion: history entry visible
        assert "E2E test reward" in content

        # DB assertion
        u = reload_user(db_session, target_user.id)
        assert u.credit_balance == expected_balance, f"DB balance mismatch: {u.credit_balance} != {expected_balance}"

        ct = (
            db_session.query(CreditTransaction)
            .filter(
                CreditTransaction.user_id == target_user.id,
                CreditTransaction.amount == 300,
            )
            .order_by(CreditTransaction.id.desc())
            .first()
        )
        assert ct is not None, "CreditTransaction row not created in DB"
        assert ct.transaction_type == TransactionType.ADMIN_ADJUSTMENT.value
        assert ct.balance_after == expected_balance

    def test_ui10_deduct_credit_decreases_balance(
        self, page, target_user, db_session
    ):
        """UI-10: Deduct 200 credits → balance -200, CreditTransaction in DB."""
        initial_balance = target_user.credit_balance or 0  # 1000
        self._go_edit(page, target_user)

        page.evaluate("document.getElementById('credits')?.scrollIntoView()")
        page.wait_for_timeout(300)

        # Fill deduct credit form (the red box)
        deduct_form = page.locator("form[action*='deduct-credit']")
        deduct_form.locator("input[name=amount]").fill("200")
        deduct_form.locator("input[name=reason]").fill("E2E test correction")
        ss(page, "UI10a_deduct_credit_form_filled")

        with page.expect_navigation(timeout=8000):
            deduct_form.locator("button[type=submit]").click()
        page.wait_for_load_state("networkidle")

        ss(page, "UI10b_after_deduct_credit")

        expected_balance = initial_balance - 200
        content = page.content()
        assert str(expected_balance) in content, f"Expected balance {expected_balance} not shown in UI"
        assert "E2E test correction" in content

        # DB assertion
        u = reload_user(db_session, target_user.id)
        assert u.credit_balance == expected_balance

        ct = (
            db_session.query(CreditTransaction)
            .filter(
                CreditTransaction.user_id == target_user.id,
                CreditTransaction.amount == -200,
            )
            .order_by(CreditTransaction.id.desc())
            .first()
        )
        assert ct is not None, "CreditTransaction row not created in DB"

    def test_ui11_grant_license_creates_license_in_db(
        self, page, target_user, db_session
    ):
        """UI-11: Grant LFA_FOOTBALL_PLAYER license → UserLicense + LicenseProgression in DB."""
        self._go_edit(page, target_user)

        page.evaluate("document.getElementById('licenses')?.scrollIntoView()")
        page.wait_for_timeout(300)

        # Find the grant-license form
        grant_form = page.locator("form[action*='grant-license']")
        grant_form.locator("select[name=specialization_type]").select_option("LFA_FOOTBALL_PLAYER")
        grant_form.locator("input[name=reason]").fill("E2E manual grant")
        ss(page, "UI11a_grant_license_form_filled")

        with page.expect_navigation(timeout=8000):
            grant_form.locator("button[type=submit]").click()
        page.wait_for_load_state("networkidle")

        ss(page, "UI11b_after_grant_license")

        # UI assertion: license badge visible
        content = page.content()
        assert "LFA_FOOTBALL_PLAYER" in content, "License badge not found in UI after grant"
        assert "INITIAL_GRANT" in content, "INITIAL_GRANT progression event not shown in UI"

        # DB assertions
        db_session.expire_all()
        lic = (
            db_session.query(UserLicense)
            .filter(
                UserLicense.user_id == target_user.id,
                UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
                UserLicense.is_active == True,
            )
            .first()
        )
        assert lic is not None, "UserLicense not created in DB"

        prog = (
            db_session.query(LicenseProgression)
            .filter(LicenseProgression.user_license_id == lic.id)
            .first()
        )
        assert prog is not None, "LicenseProgression not created in DB"
        assert prog.requirements_met == "INITIAL_GRANT"
        assert "E2E manual grant" in (prog.advancement_reason or "")

    def test_ui12_revoke_license_sets_inactive(
        self, page, target_user, db_session
    ):
        """UI-12: Revoke the license → is_active=False in DB, REVOKED badge in UI."""
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo

        # Setup: grant a license first (via DB directly so we can control it)
        lic = UserLicense(
            user_id=target_user.id,
            specialization_type="LFA_COACH",
            started_at=datetime.now(tz=ZoneInfo("UTC")),
            is_active=True,
        )
        db_session.add(lic)
        db_session.commit()
        db_session.refresh(lic)

        self._go_edit(page, target_user)
        page.evaluate("document.getElementById('licenses')?.scrollIntoView()")
        page.wait_for_timeout(300)

        ss(page, "UI12a_edit_page_with_license")

        # Find the revoke form for this license (by action URL)
        revoke_form = page.locator(f"form[action*='revoke-license/{lic.id}']")
        revoke_form.locator("input[name=reason]").fill("E2E policy violation")

        # Use page.once() + expect_navigation() for reliable dialog+navigation handling
        # (page.on() + wait_for_url() can race when the dialog accept triggers navigation)
        page.once("dialog", lambda dialog: dialog.accept())

        ss(page, "UI12b_revoke_form_filled")
        with page.expect_navigation(timeout=8000):
            revoke_form.locator("button[type=submit]").click()
        page.wait_for_load_state("networkidle")

        ss(page, "UI12c_after_revoke")

        # UI assertion: REVOKED badge visible
        content = page.content()
        assert "REVOKED" in content, "REVOKED badge not shown after license revocation"

        # DB assertion
        db_session.expire_all()
        lic_db = db_session.query(UserLicense).filter(UserLicense.id == lic.id).first()
        assert lic_db.is_active is False, "License still active in DB after revoke"

        prog = (
            db_session.query(LicenseProgression)
            .filter(
                LicenseProgression.user_license_id == lic.id,
            )
            .order_by(LicenseProgression.id.desc())
            .first()
        )
        assert prog is not None, "LicenseProgression not created after revoke"
        assert prog.requirements_met == "REVOKED"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — License Expiry & Renewal
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminLicenseExpiryRenewal:
    """
    UI-13 through UI-14: License expiry display and renewal workflow.

    UI-13: Grant license with expiry date → expires_at shown in UI, DB has value.
    UI-14: View expired license → EXPIRED badge; renew → RENEWED in UI + DB.
    """

    def _go_edit(self, page, target_user):
        admin_login(page)
        page.goto(f"{APP_URL}/admin/users/{target_user.id}/edit")
        page.wait_for_load_state("networkidle")
        assert "Internal Server Error" not in page.content()
        return page.content()

    def test_ui13_license_with_expiry_shows_expires_label_in_ui(
        self, page, target_user, db_session
    ):
        """UI-13: License with expires_at set shows 'Expires:' label and date in the license card.

        NOTE: Backend storage of expires_at from the grant form is covered by SMOKE-17j
        (integration test). This test focuses on the template rendering: given a license
        with expires_at in DB, the admin UI correctly displays it.

        Also verifies:
        - The grant form renders an expires_at date input (template has it)
        - issued_at is shown when set
        """
        from datetime import datetime, date, timedelta

        # Setup: create license with expires_at directly in DB (avoids browser date-input quirks)
        future_date = (date.today() + timedelta(days=365)).isoformat()
        future_dt = datetime.strptime(future_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        issued_now = datetime.now(timezone.utc).replace(tzinfo=None)
        lic = UserLicense(
            user_id=target_user.id,
            specialization_type="LFA_FOOTBALL_PLAYER",
            started_at=issued_now,
            issued_at=issued_now,
            is_active=True,
            expires_at=future_dt,
        )
        db_session.add(lic)
        db_session.commit()
        db_session.refresh(lic)

        # Navigate to edit page
        self._go_edit(page, target_user)
        page.evaluate("document.getElementById('licenses')?.scrollIntoView()")
        page.wait_for_timeout(300)
        ss(page, "UI13a_license_card_with_expiry")

        content = page.content()
        # License card must be visible
        assert "LFA_FOOTBALL_PLAYER" in content
        assert "ACTIVE" in content, "ACTIVE badge not shown"
        # Expiry date must appear
        assert "Expires:" in content, "Expiry date label not shown in UI"
        assert future_date in content, f"Expiry date {future_date} not shown in UI"
        # Issued date must appear (issued_at is set)
        assert "Issued:" in content, "Issued date label not shown in UI"
        # Grant form must have the expires_at input (template renders it)
        assert 'name="expires_at"' in content, "Grant form missing expires_at input"

    def test_ui14_expired_license_shows_badge_and_renewal_updates_db(
        self, page, target_user, db_session
    ):
        """UI-14: Expired license shows EXPIRED badge; renewing sets RENEWED badge + updates DB."""
        from datetime import datetime, date, timedelta
        from zoneinfo import ZoneInfo

        # Setup: create an expired license (is_active=True, expires_at in past)
        old_expiry = datetime(2024, 1, 1, 23, 59, 59)
        lic = UserLicense(
            user_id=target_user.id,
            specialization_type="LFA_COACH",
            started_at=datetime.now(tz=ZoneInfo("UTC")),
            is_active=True,
            expires_at=old_expiry,
        )
        db_session.add(lic)
        db_session.commit()
        db_session.refresh(lic)

        self._go_edit(page, target_user)
        page.evaluate("document.getElementById('licenses')?.scrollIntoView()")
        page.wait_for_timeout(400)

        content = page.content()
        assert "EXPIRED" in content, "EXPIRED badge not shown for past-expiry license"
        ss(page, "UI14a_expired_badge_visible")

        # Fill and submit the renewal form
        renew_form = page.locator(f"form[action*='renew-license/{lic.id}']")
        new_expiry = (date.today() + timedelta(days=365)).isoformat()
        # Date inputs require evaluate() — fill() is unreliable for input[type=date]
        renew_form.locator("input[name=new_expires_at]").evaluate(f"el => el.value = '{new_expiry}'")
        renew_form.locator("input[name=reason]").fill("E2E annual renewal UI-14")
        ss(page, "UI14b_renewal_form_filled")

        # expect_navigation() — same reason as UI-13 (same-base-URL redirect)
        with page.expect_navigation(timeout=8000):
            renew_form.locator("button[type=submit]").click()
        page.wait_for_load_state("networkidle")
        ss(page, "UI14c_after_renewal")

        content = page.content()
        assert "RENEWED" in content, "RENEWED badge not shown in progression history"

        # DB assertions
        db_session.expire_all()
        lic_db = db_session.query(UserLicense).filter(UserLicense.id == lic.id).first()
        assert lic_db.expires_at is not None
        assert lic_db.expires_at.strftime("%Y-%m-%d") == new_expiry, "expires_at not updated in DB"
        assert lic_db.last_renewed_at is not None, "last_renewed_at not set after renewal"

        prog = (
            db_session.query(LicenseProgression)
            .filter(LicenseProgression.user_license_id == lic.id)
            .order_by(LicenseProgression.id.desc())
            .first()
        )
        assert prog is not None, "LicenseProgression not created after renewal"
        assert prog.requirements_met == "RENEWED"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Responsive Layout
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminUsersResponsive:
    """
    UI-RESP-USERS-01: Mobile card layout on /admin/users at 375×812.

    Verifies that at mobile viewport:
    - Desktop table container is hidden (display: none)
    - Mobile user cards are visible
    - No horizontal scroll (scrollWidth ≤ viewport width)
    """

    def test_ui_resp_users_01_mobile_shows_cards_not_table(self, page, target_user):
        """UI-RESP-USERS-01: At 375×812 viewport, user cards render instead of table."""
        page.set_viewport_size({"width": 375, "height": 812})
        admin_login(page)
        page.goto(f"{APP_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        ss(page, "UI_RESP_USERS_01_mobile")

        # Desktop table must be hidden on mobile
        desktop = page.locator(".desktop-table-container")
        display = desktop.evaluate("el => getComputedStyle(el).display")
        assert display == "none", (
            f"Desktop table not hidden on mobile (display={display!r}). "
            "Expected display:none at 375px viewport."
        )

        # At least one mobile card must be visible
        card = page.locator(".mobile-user-card").nth(0)
        assert card.is_visible(), "Mobile user card not visible at 375×812"

        # No horizontal scroll: body.scrollWidth must not exceed viewport width
        scroll_width = page.evaluate("document.body.scrollWidth")
        assert scroll_width <= 380, (
            f"Horizontal scroll detected: scrollWidth={scroll_width} > 380. "
            "Mobile layout must not require horizontal scrolling."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Report generation hook
# ─────────────────────────────────────────────────────────────────────────────

def pytest_sessionfinish(session, exitstatus):
    """Generate HTML report listing all screenshots after test run."""
    screenshots = sorted(SCREENSHOTS_DIR.glob("*.png"))
    if not screenshots:
        return

    report_path = Path(__file__).parent / "report.html"
    passed = getattr(session, "_admin_ui_passed", 0)
    failed = getattr(session, "_admin_ui_failed", 0)

    lines = [
        "<!DOCTYPE html><html><head>",
        "<meta charset='UTF-8'>",
        "<title>Admin UI Playwright Test Report</title>",
        "<style>",
        "  body { font-family: -apple-system, sans-serif; margin: 2rem; background: #f5f7fa; }",
        "  h1 { color: #2c3e50; }",
        "  .summary { display: flex; gap: 2rem; margin: 1rem 0 2rem; }",
        "  .stat { padding: 1rem 2rem; border-radius: 10px; font-weight: 700; font-size: 1.2rem; }",
        "  .pass { background: #d4edda; color: #155724; }",
        "  .fail { background: #f8d7da; color: #721c24; }",
        "  .info { background: #d1ecf1; color: #0c5460; }",
        "  .screenshots { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 1rem; }",
        "  .screenshot { background: white; border-radius: 10px; padding: 0.75rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }",
        "  .screenshot img { width: 100%; border-radius: 6px; border: 1px solid #eee; }",
        "  .screenshot p { font-size: 0.8rem; color: #666; margin-top: 0.5rem; word-break: break-all; }",
        "</style></head><body>",
        "<h1>Admin UI Playwright Test Report</h1>",
        f"<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        "<p><strong>Clean DB:</strong> Admin user seeded from .env; test target user created fresh per test with UUID.</p>",
        "<div class='summary'>",
        f"  <div class='stat pass'>✅ Passed: {passed}</div>",
        f"  <div class='stat fail'>❌ Failed: {failed}</div>",
        f"  <div class='stat info'>📸 Screenshots: {len(screenshots)}</div>",
        "</div>",
        "<h2>Screenshots</h2>",
        "<div class='screenshots'>",
    ]

    for s in screenshots:
        # Use relative path for the image src
        lines.append(f"<div class='screenshot'>")
        lines.append(f"  <img src='screenshots/{s.name}' alt='{s.stem}'>")
        lines.append(f"  <p>{s.name}</p>")
        lines.append(f"</div>")

    lines += ["</div>", "</body></html>"]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📊 HTML Report: {report_path}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call":
        if rep.passed:
            item.session._admin_ui_passed = getattr(item.session, "_admin_ui_passed", 0) + 1
        elif rep.failed:
            item.session._admin_ui_failed = getattr(item.session, "_admin_ui_failed", 0) + 1
