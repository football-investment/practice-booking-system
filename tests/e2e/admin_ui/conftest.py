"""
Playwright E2E fixtures for Admin User Management UI tests.

Strategy:
- Each test class creates its own test target user (UUID-based → no collision with baseline data)
- DB assertions use a direct SQLAlchemy session (same DB the running app uses)
- Screenshots are saved to tests/e2e/admin_ui/screenshots/
- Cleanup: test users are deleted from the DB after each test class

Run with headed mode:
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=600 pytest tests/e2e/admin_ui/ -v -s \
        --html=tests/e2e/admin_ui/report.html --self-contained-html
"""

import os
import uuid
from pathlib import Path
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.credit_transaction import CreditTransaction
from app.models.license import UserLicense, LicenseProgression

# ── Config ────────────────────────────────────────────────────────────────────

APP_URL = os.environ.get("API_URL", "http://localhost:8000")
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@lfa.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


# ── Direct DB engine (bypasses app session — for test data + assertions) ──────

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(DB_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def purge_stale_e2e_users(db_engine):
    """
    Session-scoped autouse: delete ALL leftover e2etgt-*@lfa-test.com users
    at session START before any test runs.

    Protects against residue from previously interrupted test runs where the
    function-scoped target_user teardown never executed (e.g. SIGKILL).

    Cascade order (mirrors target_user teardown):
      1. LicenseProgression  (FK → user_licenses.id)
      2. CreditTransaction   WHERE user_id IN (stale ids)
      3. CreditTransaction   WHERE user_license_id IN (stale license ids)
      4. UserLicense
      5. User
    """
    Session = sessionmaker(bind=db_engine)
    session = Session()
    try:
        stale = session.query(User).filter(User.email.like("e2etgt-%@lfa-test.com")).all()
        if not stale:
            return
        stale_ids = [u.id for u in stale]
        stale_lic_ids = [
            lic.id
            for lic in session.query(UserLicense)
            .filter(UserLicense.user_id.in_(stale_ids))
            .all()
        ]
        if stale_lic_ids:
            session.query(LicenseProgression).filter(
                LicenseProgression.user_license_id.in_(stale_lic_ids)
            ).delete(synchronize_session=False)
            session.query(CreditTransaction).filter(
                CreditTransaction.user_license_id.in_(stale_lic_ids)
            ).delete(synchronize_session=False)
        session.query(CreditTransaction).filter(
            CreditTransaction.user_id.in_(stale_ids)
        ).delete(synchronize_session=False)
        session.query(UserLicense).filter(
            UserLicense.user_id.in_(stale_ids)
        ).delete(synchronize_session=False)
        session.query(User).filter(User.id.in_(stale_ids)).delete(synchronize_session=False)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


# ── Test target user (created fresh, deleted after test) ─────────────────────

@pytest.fixture(scope="function")
def target_user(db_session):
    """Create a fresh test user for the current test; delete after."""
    suffix = uuid.uuid4().hex[:8]
    user = User(
        email=f"e2etgt-{suffix}@lfa-test.com",
        name=f"E2ETgt-{suffix}",
        password_hash=get_password_hash("oldpass123"),
        role=UserRole.STUDENT,
        is_active=True,
        credit_balance=1000,
        credit_purchased=1000,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    # Cleanup: delete dependent rows first to avoid check constraint violations.
    # credit_transactions.user_id is nullable but check_one_credit_reference
    # forbids both user_id and user_license_id being NULL simultaneously,
    # so we must delete credit_transactions before deleting the user.
    db_session.expire_all()
    licenses = (
        db_session.query(UserLicense)
        .filter(UserLicense.user_id == user.id)
        .all()
    )
    for lic in licenses:
        db_session.query(LicenseProgression).filter(
            LicenseProgression.user_license_id == lic.id
        ).delete(synchronize_session=False)
    db_session.query(CreditTransaction).filter(
        CreditTransaction.user_id == user.id
    ).delete(synchronize_session=False)
    db_session.query(UserLicense).filter(
        UserLicense.user_id == user.id
    ).delete(synchronize_session=False)
    db_session.delete(user)
    db_session.commit()


# ── Screenshot helper ─────────────────────────────────────────────────────────

def screenshot(page, name: str) -> Path:
    """Save a timestamped screenshot and return the path."""
    ts = datetime.now().strftime("%H%M%S")
    path = SCREENSHOTS_DIR / f"{ts}_{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return path


# ── Admin login helper ────────────────────────────────────────────────────────

def admin_login(page, app_url: str = APP_URL) -> None:
    """Log in as admin and wait for dashboard."""
    page.goto(f"{app_url}/login")
    page.wait_for_load_state("networkidle")
    page.fill("input[name=email]", ADMIN_EMAIL)
    page.fill("input[name=password]", ADMIN_PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(f"{app_url}/dashboard*", timeout=8000)


# ── Re-export for test files ──────────────────────────────────────────────────

__all__ = ["APP_URL", "screenshot", "admin_login", "SCREENSHOTS_DIR"]


# ── Playwright video recording ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Enable video recording when PLAYWRIGHT_VIDEO_DIR env var is set."""
    video_dir = os.environ.get("PLAYWRIGHT_VIDEO_DIR")
    if video_dir:
        Path(video_dir).mkdir(parents=True, exist_ok=True)
        return {**browser_context_args, "record_video_dir": video_dir}
    return browser_context_args
