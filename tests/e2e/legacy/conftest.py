"""
Legacy E2E tests - Collection disabled

These tests are outdated and have design issues:
- Execute DB queries at module level (before migrations)
- Don't use proper fixtures for setup/teardown
- Superseded by modern tests in tests_e2e/integration_critical/

To prevent pytest collection errors during smoke tests, we collect_ignore all files.
"""
import os

# Prevent pytest from collecting ANY test files in this directory
collect_ignore_glob = ["*.py"]

def pytest_collection_modifyitems(items):
    """Skip all tests in legacy directory"""
    pass
