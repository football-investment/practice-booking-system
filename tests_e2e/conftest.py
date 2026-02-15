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
