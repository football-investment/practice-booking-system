"""
Test Data Fixtures Package

JSON-based test configuration system for E2E Playwright tests.

Usage:
    from fixtures.data_loader import TestDataLoader

    # In pytest fixture (conftest.py)
    @pytest.fixture(scope="session")
    def test_data():
        return TestDataLoader(fixture_name="tournament_test_data")

    # In tests
    def test_something(test_data):
        admin = test_data.get_admin()
        player = test_data.get_player(email="player@example.com")
        tournament = test_data.get_tournament(assignment_type="APPLICATION_BASED")
"""

from .data_loader import TestDataLoader

__all__ = ["TestDataLoader"]
