"""
E2E Test Configuration

This file makes fixtures from fixtures.py available to all E2E tests
and configures Playwright for headed mode with slowmo.
"""

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

# Import all fixtures to make them available
from .fixtures import (
    admin_token,
    test_instructor,
    test_players,
    create_tournament,
    tournament_in_draft,
    tournament_with_instructor,
    complete_tournament_setup
)


# ================================================================
# PLAYWRIGHT CONFIGURATION FOR HEADED MODE
# ================================================================

@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, pytestconfig):
    """
    Configure Playwright browser launch arguments for headed mode.

    This fixture overrides the default pytest-playwright settings to:
    - Show browser window (headless=False)
    - Add slowmo for visual debugging
    - Set viewport size
    - Use Firefox browser
    """
    return {
        **browser_type_launch_args,
        "headless": False,  # Show browser window
        "slow_mo": 500,     # 500ms delay between actions (visible for debugging)
    }


@pytest.fixture(scope="session")
def browser_name(pytestconfig):
    """
    Force Firefox browser for all Playwright tests.
    """
    return "firefox"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Configure browser context arguments.

    Sets viewport size and other context-level settings.
    """
    return {
        **browser_context_args,
        "viewport": {
            "width": 1920,
            "height": 1080,
        },
        "ignore_https_errors": True,
    }


# Make pytest aware of the fixtures
__all__ = [
    "admin_token",
    "test_instructor",
    "test_players",
    "create_tournament",
    "tournament_in_draft",
    "tournament_with_instructor",
    "complete_tournament_setup",
    "browser_type_launch_args",
    "browser_context_args",
    "browser_name",
]
