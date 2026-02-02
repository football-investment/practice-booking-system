"""
Playwright E2E Frontend Tests Configuration

This file configures Playwright to run in HEADED mode with visible browser windows.
"""
import pytest
import requests


# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="session")
def admin_token():
    """Authenticate admin user and return JWT token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]
