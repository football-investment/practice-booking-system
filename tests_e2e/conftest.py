"""
Pytest Configuration for E2E Tests
===================================

Shared fixtures and configuration for Playwright E2E tests.

Environment Variables:
    PYTEST_HEADLESS=true (default) | false
        - true: Run browsers in headless mode (CI/automation)
        - false: Show browser window (local debugging)

    PYTEST_BROWSER=chromium (default) | firefox | webkit
        - Browser engine to use for tests

    PYTEST_SLOW_MO=0 (default) | <milliseconds>
        - Delay between Playwright actions (useful for debugging)
        - Recommended: 1000-1500ms for headed mode

    BASE_URL=http://localhost:8501 (default)
        - Streamlit application URL

    API_URL=http://localhost:8000 (default)
        - FastAPI backend URL

Usage Examples:
    # CI mode (headless, fast)
    pytest tests_e2e/

    # Debug mode (headed, slow motion)
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=1200 pytest tests_e2e/test_01_quick_test_full_flow.py -v -s

    # Firefox instead of Chromium
    PYTEST_BROWSER=firefox pytest tests_e2e/

    # Smoke tests only (fast regression)
    pytest -m smoke --tb=short

    # Golden path tests (build blockers)
    pytest -m golden_path --tb=short
"""

import os
import pytest
from playwright.sync_api import sync_playwright
from pathlib import Path
import sys

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.snapshot_manager import SnapshotManager


# ============================================================================
# HEADLESS-FIRST ARCHITECTURE (CRITICAL REQUIREMENT)
# ============================================================================

# Verify headless mode is enabled by default
_HEADLESS_DEFAULT = os.environ.get("PYTEST_HEADLESS", "true")
if _HEADLESS_DEFAULT.lower() not in ("true", "1", "yes"):
    print("\n" + "="*80)
    print("⚠️  WARNING: Headless mode is DISABLED")
    print("="*80)
    print("Headless execution is the canonical path for:")
    print("  - CI/CD pipelines")
    print("  - Local automation")
    print("  - Reproducible testing")
    print("\nHeaded mode should ONLY be used for debugging.")
    print("To suppress this warning, set: PYTEST_HEADLESS=true")
    print("="*80 + "\n")


# ============================================================================
# Environment Configuration
# ============================================================================

def get_bool_env(key: str, default: str = "true") -> bool:
    """Parse boolean environment variable."""
    return os.environ.get(key, default).lower() in ("true", "1", "yes")


def get_int_env(key: str, default: int = 0) -> int:
    """Parse integer environment variable."""
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


# ============================================================================
# Shared Configuration
# ============================================================================

@pytest.fixture(scope="session")
def browser_config():
    """
    Central browser configuration for all E2E tests.

    Returns dict with keys:
        - headless: bool - Run browser in headless mode
        - slow_mo: int - Milliseconds to delay between actions
        - browser_type: str - Browser engine (chromium, firefox, webkit)
    """
    config = {
        "headless": get_bool_env("PYTEST_HEADLESS", "true"),
        "slow_mo": get_int_env("PYTEST_SLOW_MO", 0),
        "browser_type": os.environ.get("PYTEST_BROWSER", "chromium"),
    }

    # Log configuration (helpful for CI debugging)
    print(f"\n🌐 Browser Config: {config['browser_type']} "
          f"(headless={config['headless']}, slow_mo={config['slow_mo']}ms)")

    return config


@pytest.fixture(scope="session")
def base_url():
    """Streamlit application URL."""
    return os.environ.get("BASE_URL", "http://localhost:8501")


@pytest.fixture(scope="session")
def api_url():
    """FastAPI backend URL."""
    return os.environ.get("API_URL", "http://localhost:8000")


# ============================================================================
# Browser Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def playwright_instance():
    """
    Playwright instance (scope: function).

    Creates a new Playwright instance for each test.
    Automatically cleans up after test completes.
    """
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="function")
def browser(playwright_instance, browser_config):
    """
    Playwright browser instance with environment-aware config.

    Usage in tests:
        def test_my_feature(browser):
            page = browser.new_page()
            page.goto("http://localhost:8501")
            # ... test logic ...
            # browser.close() handled automatically

    Scope: function (new browser per test)
    """
    browser_type = getattr(playwright_instance, browser_config["browser_type"])
    browser = browser_type.launch(
        headless=browser_config["headless"],
        slow_mo=browser_config["slow_mo"],
    )

    yield browser

    browser.close()


@pytest.fixture(scope="function")
def page(browser):
    """
    Playwright page instance (new page in browser context).

    Usage in tests:
        def test_my_feature(page):
            page.goto("http://localhost:8501")
            page.fill("input", "test@example.com")
            # ... test logic ...
            # page.close() handled automatically

    Scope: function (new page per test)
    """
    page = browser.new_page()

    yield page

    page.close()


# ============================================================================
# Snapshot Management Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def snapshot_manager():
    """
    Snapshot manager for DB state management across lifecycle phases.

    Performance: <3 seconds for snapshot restore (architectural requirement)
    """
    return SnapshotManager(
        db_url=os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    )


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_user_credentials():
    """
    Default test user credentials.

    Returns dict with keys:
        - email: str
        - password: str

    Override with environment variables:
        TEST_USER_EMAIL=custom@example.com
        TEST_USER_PASSWORD=custompass
    """
    return {
        "email": os.environ.get("TEST_USER_EMAIL", "junior.intern@lfa.com"),
        "password": os.environ.get("TEST_USER_PASSWORD", "password123"),
    }


@pytest.fixture(scope="session", autouse=True)
def e2e_test_users():
    """
    E2E test users fixture — creates required test users directly in database.

    Eliminates seed data dependency by creating test users on-demand via SQLAlchemy.
    Users are created once per test session (autouse=True ensures availability).

    Returns dict with user credentials:
        - junior_intern: Student user (junior.intern@lfa.com)
        - admin: Admin user (admin@lfa.com)
        - instructor: Instructor user (grandmaster@lfa.com)

    Usage in tests:
        Tests can use hardcoded credentials directly since this fixture
        ensures the users exist:
            - junior.intern@lfa.com / password123
            - admin@lfa.com / admin123
            - grandmaster@lfa.com / GrandMaster2026!

    See E2E_ISSUES.md Phase 1 for context.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from datetime import datetime, timezone

    # Import models and utilities
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from app.models.user import User
    from app.core.security import get_password_hash
    from app.config import settings

    print("\n🏗️  E2E Test Users Setup...")

    # Get database URL
    db_url = settings.DATABASE_URL
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    created_users = {}

    # User definitions (email, password, role)
    users_to_create = [
        {
            "key": "junior_intern",
            "email": "junior.intern@lfa.com",
            "password": "password123",
            "role": "STUDENT",
            "name": "Junior Intern",
            "nickname": "JuniorE2E"
        },
        {
            "key": "admin",
            "email": "admin@lfa.com",
            "password": "admin123",
            "role": "ADMIN",
            "name": "Admin User",
            "nickname": "AdminE2E"
        },
        {
            "key": "instructor",
            "email": "grandmaster@lfa.com",
            "password": "GrandMaster2026!",
            "role": "INSTRUCTOR",
            "name": "Grand Master",
            "nickname": "GrandMasterE2E"
        },
    ]

    try:
        for user_spec in users_to_create:
            # Check if user already exists
            existing = db.query(User).filter(User.email == user_spec["email"]).first()

            if existing:
                # User exists - UPDATE to ensure deterministic state (fixture = authority)
                existing.password_hash = get_password_hash(user_spec["password"])
                existing.role = user_spec["role"]
                existing.is_active = True
                existing.onboarding_completed = True
                db.flush()

                created_users[user_spec["key"]] = {
                    "id": existing.id,
                    "email": user_spec["email"],
                    "password": user_spec["password"],
                    "role": user_spec["role"]
                }
                print(f"   ♻️  {user_spec['key']}: {user_spec['email']} (updated, id={existing.id})")
            else:
                # Create new user
                new_user = User(
                    email=user_spec["email"],
                    password_hash=get_password_hash(user_spec["password"]),
                    name=user_spec["name"],
                    nickname=user_spec["nickname"],
                    role=user_spec["role"],
                    is_active=True,
                    onboarding_completed=True,  # Skip onboarding for E2E tests
                    date_of_birth=datetime(2000, 1, 1),  # Dummy DOB
                    phone="+36201234567"  # Dummy phone
                )
                db.add(new_user)
                db.flush()  # Get ID without committing

                created_users[user_spec["key"]] = {
                    "id": new_user.id,
                    "email": user_spec["email"],
                    "password": user_spec["password"],
                    "role": user_spec["role"]
                }
                print(f"   ✅ {user_spec['key']}: {user_spec['email']} (created, id={new_user.id})")

        # Commit all changes
        db.commit()
        print(f"   📊 E2E test users ready: {len(created_users)} users available")

    except Exception as exc:
        db.rollback()
        print(f"   ❌ Error setting up E2E test users: {exc}")
        import traceback
        traceback.print_exc()
        # Return empty dict on failure - tests will use seed data if available
        created_users = {}
    finally:
        db.close()

    yield created_users

    # No cleanup - E2E test users persist for reuse across test runs


# ============================================================================
# OPS Seed Players (64 @lfa-seed.hu users for Tournament Monitor API tests)
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def seed_ops_players(request):
    """
    OPS seed players fixture — creates 64 @lfa-seed.hu test players for OPS scenarios.

    **Activation:** Auto-activates when tests marked with @pytest.mark.ops_seed are collected.
    **Scope:** Session (created once, cleaned up after all tests)
    **Idempotent:** Checks if users exist, skips creation if already present.

    Creates:
        - 64 active users with @lfa-seed.hu emails
        - Deterministic emails: ops.player.001@lfa-seed.hu ... ops.player.064@lfa-seed.hu
        - LFA_FOOTBALL_PLAYER licenses with baseline skills
        - Password: "opstest123" (all users)

    Cleanup:
        - Deletes created users and licenses after session ends

    Usage:
        @pytest.mark.ops_seed
        def test_api_knockout_16_players(api_url):
            # Fixture ensures 64 @lfa-seed.hu users exist
            # OPS scenario auto-selects from pool
            ...
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from datetime import datetime, timezone

    # Import models
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from app.models.user import User
    from app.models.license import UserLicense
    from app.core.security import get_password_hash
    from app.config import settings

    # Check if any ops_seed tests are collected
    if not any(item.get_closest_marker("ops_seed") for item in request.session.items):
        pytest.skip("No ops_seed tests collected - skipping OPS player seed")
        return  # Won't execute, but satisfies static analysis

    print("\n🌱 OPS Seed Players Setup (64 @lfa-seed.hu users)...")

    # Database setup
    db_url = settings.DATABASE_URL
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    created_user_ids = []
    created_license_ids = []
    created_campus_id = None

    try:
        # Ensure at least one active campus exists (required for OPS scenarios with campus_ids)
        from app.models.campus import Campus
        from app.models.location import Location

        existing_campus = db.query(Campus).filter(Campus.is_active == True).first()

        if not existing_campus:
            # Create minimal location + campus for testing
            location = Location(
                name="E2E Test Location",
                city="Budapest",
                country="Hungary",
                is_active=True,
                location_type="PARTNER"  # Valid enum: PARTNER or CENTER
            )
            db.add(location)
            db.flush()

            campus = Campus(
                name="E2E Test Campus",
                location_id=location.id,
                is_active=True,
                address="Test Address 123"
            )
            db.add(campus)
            db.flush()
            created_campus_id = campus.id
            print(f"   ✅ Created test campus (ID={campus.id})")
        else:
            print(f"   ✅ Using existing campus (ID={existing_campus.id})")

        db.commit()

        # Create 64 players with deterministic emails
        for i in range(1, 65):  # ops.player.001 ... ops.player.064
            email = f"ops.player.{i:03d}@lfa-seed.hu"
            password = "opstest123"

            # Check if user already exists (idempotent)
            existing = db.query(User).filter(User.email == email).first()

            if existing:
                # User exists - skip creation
                continue

            # Create new player
            player = User(
                email=email,
                password_hash=get_password_hash(password),
                name=f"OPS Player {i:03d}",
                nickname=f"OPS{i:03d}",
                role="STUDENT",
                is_active=True,
                onboarding_completed=True,
                date_of_birth=datetime(2000, 1, 1),
                phone=f"+3620{i:07d}"
            )
            db.add(player)
            db.flush()
            created_user_ids.append(player.id)

            # Create LFA_FOOTBALL_PLAYER license with baseline skills
            baseline_skills = {
                "finishing": {"baseline": 50.0, "current_level": 50.0, "tournament_delta": 0.0, "total_delta": 0.0, "tournament_count": 0},
                "dribbling": {"baseline": 50.0, "current_level": 50.0, "tournament_delta": 0.0, "total_delta": 0.0, "tournament_count": 0},
                "passing": {"baseline": 50.0, "current_level": 50.0, "tournament_delta": 0.0, "total_delta": 0.0, "tournament_count": 0}
            }
            license = UserLicense(
                user_id=player.id,
                specialization_type="LFA_FOOTBALL_PLAYER",
                is_active=True,
                started_at=datetime.now(timezone.utc),
                football_skills=baseline_skills
            )
            db.add(license)
            db.flush()
            created_license_ids.append(license.id)

        db.commit()
        print(f"   ✅ OPS seed complete: {len(created_user_ids)} players created, {64 - len(created_user_ids)} already existed")

    except Exception as exc:
        db.rollback()
        print(f"   ❌ Error creating OPS seed players: {exc}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

    yield  # Tests run here

    # Cleanup: Delete created players and licenses
    print("\n🧹 Cleaning up OPS seed players...")
    db = SessionLocal()
    try:
        # Delete licenses first (foreign key constraint)
        for lic_id in created_license_ids:
            lic = db.query(UserLicense).filter(UserLicense.id == lic_id).first()
            if lic:
                db.delete(lic)

        # Delete players
        for user_id in created_user_ids:
            player = db.query(User).filter(User.id == user_id).first()
            if player:
                db.delete(player)

        # Delete campus if we created it
        if created_campus_id:
            campus = db.query(Campus).filter(Campus.id == created_campus_id).first()
            if campus:
                location_id = campus.location_id
                db.delete(campus)
                # Delete location too
                location = db.query(Location).filter(Location.id == location_id).first()
                if location:
                    db.delete(location)

        db.commit()
        cleanup_msg = f"{len(created_user_ids)} players"
        if created_campus_id:
            cleanup_msg += f", test campus (ID={created_campus_id})"
        print(f"   ✅ Cleanup complete: {cleanup_msg} deleted")

    except Exception as cleanup_err:
        db.rollback()
        print(f"   ⚠️  Cleanup warning: {cleanup_err}")
    finally:
        db.close()


# ============================================================================
# Scale Suite Players (128-1024 @lfa-scale.hu users for capacity validation)
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def seed_scale_suite_players(request):
    """
    Scale Suite players fixture — creates 128-1024 @lfa-scale.hu test players for capacity validation.

    **Activation:** Auto-activates when tests marked with @pytest.mark.scale_suite are collected.
    **Scope:** Session (created once, cleaned up after all tests)
    **Idempotent:** Checks if users exist, skips creation if already present.

    Creates:
        - 1024 active users with @lfa-scale.hu emails (deterministic pool)
        - Emails: scale.player.0001@lfa-scale.hu ... scale.player.1024@lfa-scale.hu
        - LFA_FOOTBALL_PLAYER licenses with baseline skills
        - Password: "scaletest123" (all users)

    Cleanup:
        - Deletes created users and licenses after session ends

    Performance Benchmarks:
        - Measures player creation time
        - Tracks memory usage (heap size)
        - Logs fixture setup duration

    Usage:
        @pytest.mark.scale_suite
        def test_api_safety_threshold_boundary_127(api_url):
            # Fixture ensures 1024 @lfa-scale.hu users exist
            # Test can select 127 players from pool
            ...
    """
    import psutil
    import time
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from datetime import datetime, timezone

    # Import models
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from app.models.user import User
    from app.models.license import UserLicense
    from app.core.security import get_password_hash
    from app.config import settings

    # Check if any scale_suite tests are collected
    if not any(item.get_closest_marker("scale_suite") for item in request.session.items):
        pytest.skip("No scale_suite tests collected - skipping Scale Suite player seed")
        return  # Won't execute, but satisfies static analysis

    print("\n🌱 Scale Suite Players Setup (1024 @lfa-scale.hu users)...")

    # Performance benchmarking
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    start_time = time.time()

    # Database setup
    db_url = settings.DATABASE_URL
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    created_user_ids = []
    created_license_ids = []

    try:
        # Create 1024 players with deterministic emails
        batch_size = 100
        total_players = 1024

        for batch_start in range(1, total_players + 1, batch_size):
            batch_end = min(batch_start + batch_size, total_players + 1)

            for i in range(batch_start, batch_end):
                email = f"scale.player.{i:04d}@lfa-scale.hu"
                password = "scaletest123"

                # Check if user already exists (idempotent)
                existing = db.query(User).filter(User.email == email).first()

                if existing:
                    # User exists - skip creation
                    continue

                # Create new player
                player = User(
                    email=email,
                    password_hash=get_password_hash(password),
                    name=f"Scale Player {i:04d}",
                    nickname=f"SCALE{i:04d}",
                    role="STUDENT",
                    is_active=True,
                    onboarding_completed=True,
                    date_of_birth=datetime(2000, 1, 1),
                    phone=f"+3630{i:08d}"
                )
                db.add(player)
                db.flush()
                created_user_ids.append(player.id)

                # Create LFA_FOOTBALL_PLAYER license with baseline skills
                baseline_skills = {
                    "finishing": {"baseline": 50.0, "current_level": 50.0, "tournament_delta": 0.0, "total_delta": 0.0, "tournament_count": 0},
                    "dribbling": {"baseline": 50.0, "current_level": 50.0, "tournament_delta": 0.0, "total_delta": 0.0, "tournament_count": 0},
                    "passing": {"baseline": 50.0, "current_level": 50.0, "tournament_delta": 0.0, "total_delta": 0.0, "tournament_count": 0}
                }
                license = UserLicense(
                    user_id=player.id,
                    specialization_type="LFA_FOOTBALL_PLAYER",
                    is_active=True,
                    started_at=datetime.now(timezone.utc),
                    football_skills=baseline_skills
                )
                db.add(license)
                db.flush()
                created_license_ids.append(license.id)

            # Commit batch
            db.commit()
            print(f"   ✅ Batch {batch_start}-{batch_end-1} committed")

        # Performance metrics
        end_time = time.time()
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        duration = end_time - start_time
        mem_delta = mem_after - mem_before

        print(f"   ✅ Scale Suite seed complete: {len(created_user_ids)} players created, {total_players - len(created_user_ids)} already existed")
        print(f"   📊 Performance: {duration:.2f}s, Memory delta: {mem_delta:.2f} MB")

    except Exception as exc:
        db.rollback()
        print(f"   ❌ Error creating Scale Suite seed players: {exc}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

    yield  # Tests run here

    # Cleanup: Delete created players and licenses
    print("\n🧹 Cleaning up Scale Suite seed players...")
    db = SessionLocal()
    try:
        # Delete licenses first (foreign key constraint)
        batch_size = 100
        for i in range(0, len(created_license_ids), batch_size):
            batch = created_license_ids[i:i+batch_size]
            db.query(UserLicense).filter(UserLicense.id.in_(batch)).delete(synchronize_session=False)
            db.commit()

        # Delete players
        for i in range(0, len(created_user_ids), batch_size):
            batch = created_user_ids[i:i+batch_size]
            db.query(User).filter(User.id.in_(batch)).delete(synchronize_session=False)
            db.commit()

        print(f"   ✅ Cleanup complete: {len(created_user_ids)} players deleted")

    except Exception as cleanup_err:
        db.rollback()
        print(f"   ⚠️  Cleanup warning: {cleanup_err}")
    finally:
        db.close()


# ============================================================================
# Screenshot Helpers
# ============================================================================

@pytest.fixture(scope="session")
def screenshot_dir():
    """Directory for test screenshots."""
    dir_path = os.path.join(os.path.dirname(__file__), "screenshots")
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def pytest_runtest_makereport(item, call):
    """
    Pytest hook: Take screenshot on test failure.

    Automatically captures full-page screenshot when a test fails.
    Screenshot saved to tests_e2e/screenshots/<test_name>_FAILED.png
    """
    if call.when == "call" and call.excinfo is not None:
        # Test failed - try to take screenshot
        try:
            # Get page fixture if available
            if "page" in item.funcargs:
                page = item.funcargs["page"]
                screenshot_dir = os.path.join(
                    os.path.dirname(__file__), "screenshots"
                )
                os.makedirs(screenshot_dir, exist_ok=True)

                screenshot_path = os.path.join(
                    screenshot_dir,
                    f"{item.name}_FAILED.png"
                )

                page.screenshot(path=screenshot_path, full_page=True)
                print(f"\n📸 Failure screenshot: {screenshot_path}")
        except Exception as e:
            print(f"\n⚠️  Could not capture failure screenshot: {e}")


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """
    Register custom markers for test organization.

    Markers are defined in pytest.ini but registered here for IDE support.
    """
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests with Playwright"
    )
    config.addinivalue_line(
        "markers", "golden_path: Production critical tests (deployment blocker)"
    )
    config.addinivalue_line(
        "markers", "smoke: Fast smoke tests for CI regression"
    )
    config.addinivalue_line(
        "markers", "slow: Tests with runtime >30 seconds"
    )
    config.addinivalue_line(
        "markers", "genesis: Clean database to full flow tests"
    )
    config.addinivalue_line(
        "markers", "tournament_monitor: Headless Playwright tests for OPS Tournament Monitor UI, wizard flow, and live tracking panel"
    )
