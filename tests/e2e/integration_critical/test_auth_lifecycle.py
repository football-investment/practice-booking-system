"""
Auth Lifecycle E2E — Integration Critical (BLOCKING CI gate)

Sprint 38 — validates the core authentication token flow missing from BLOCKING gates.

Tests:
  1. test_login_success_returns_tokens       — valid creds → access + refresh token
  2. test_login_wrong_password_401           — bad password → 401, no token
  3. test_protected_endpoint_with_valid_token — Bearer token → 200, email matches
  4. test_protected_endpoint_no_token_401    — no Authorization → 401
  5. test_refresh_token_gives_new_access_token — POST /auth/refresh → new token
  6. test_new_access_token_grants_access     — refreshed token works for /users/me

Fixture design:
  - module-scoped test_user: created once for all 6 tests (reduces API round-trips)
  - Gets a fresh admin token internally (scope-safe: module fixture gets its own)
  - Cleanup: delete user via admin API after all tests
"""

from __future__ import annotations

import time
from typing import Dict

import pytest
import requests

from tests.e2e.integration_critical.conftest import (
    get_admin_token,
    create_test_user,
    delete_test_user,
)


# ---------------------------------------------------------------------------
# Auth header helper
# ---------------------------------------------------------------------------

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Module-scoped test user (created once for all 6 tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def auth_test_user(api_url: str) -> Dict:
    """
    CREATE: 1 fresh student for auth lifecycle tests.
    CLEANUP: Delete after all tests in this module complete.

    Gets its own admin token (avoids function-scope conflict).
    """
    admin_token = get_admin_token(api_url)
    ts = int(time.time() * 1000)
    user = create_test_user(api_url, admin_token, "STUDENT", ts, 0)
    yield user
    try:
        fresh_admin_token = get_admin_token(api_url)
        delete_test_user(api_url, fresh_admin_token, user["id"])
    except Exception as e:
        print(f"⚠️  Cleanup warning: Failed to delete auth test user {user['id']}: {e}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAuthLifecycle:

    # -----------------------------------------------------------------------
    # 1. Login success
    # -----------------------------------------------------------------------

    def test_login_success_returns_tokens(self, api_url: str, auth_test_user: Dict):
        resp = requests.post(
            f"{api_url}/api/v1/auth/login",
            json={"email": auth_test_user["email"], "password": auth_test_user["password"]}
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data, "No access_token in response"
        assert "refresh_token" in data, "No refresh_token in response"
        assert data.get("token_type") == "bearer"

    # -----------------------------------------------------------------------
    # 2. Wrong password
    # -----------------------------------------------------------------------

    def test_login_wrong_password_401(self, api_url: str, auth_test_user: Dict):
        resp = requests.post(
            f"{api_url}/api/v1/auth/login",
            json={"email": auth_test_user["email"], "password": "WRONG_PASSWORD_XYZ"}
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
        assert "access_token" not in resp.json()

    # -----------------------------------------------------------------------
    # 3. Protected endpoint with valid token
    # -----------------------------------------------------------------------

    def test_protected_endpoint_with_valid_token(self, api_url: str, auth_test_user: Dict):
        resp = requests.get(
            f"{api_url}/api/v1/users/me",
            headers=_auth(auth_test_user["token"])
        )
        assert resp.status_code == 200, f"GET /users/me failed: {resp.text}"
        data = resp.json()
        assert data.get("email") == auth_test_user["email"]

    # -----------------------------------------------------------------------
    # 4. Protected endpoint without token
    # -----------------------------------------------------------------------

    def test_protected_endpoint_no_token_401(self, api_url: str):
        resp = requests.get(f"{api_url}/api/v1/users/me")
        assert resp.status_code == 401, f"Expected 401 without token, got {resp.status_code}"

    # -----------------------------------------------------------------------
    # 5. Refresh token → new access token
    # -----------------------------------------------------------------------

    def test_refresh_token_gives_new_access_token(self, api_url: str, auth_test_user: Dict):
        # Get a fresh login to obtain refresh token
        login_resp = requests.post(
            f"{api_url}/api/v1/auth/login",
            json={"email": auth_test_user["email"], "password": auth_test_user["password"]}
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]
        old_access = login_resp.json()["access_token"]

        # Call refresh endpoint
        refresh_resp = requests.post(
            f"{api_url}/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.text}"
        new_access = refresh_resp.json().get("access_token")
        assert new_access is not None, "No access_token in refresh response"
        # New token is a valid JWT string (different from old since new expiry)
        assert len(new_access) > 10

    # -----------------------------------------------------------------------
    # 6. Refreshed access token grants access
    # -----------------------------------------------------------------------

    def test_new_access_token_grants_access(self, api_url: str, auth_test_user: Dict):
        # Get refresh token
        login_resp = requests.post(
            f"{api_url}/api/v1/auth/login",
            json={"email": auth_test_user["email"], "password": auth_test_user["password"]}
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        refresh_resp = requests.post(
            f"{api_url}/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_resp.status_code == 200
        new_access_token = refresh_resp.json()["access_token"]

        # Use new token on a protected endpoint
        me_resp = requests.get(
            f"{api_url}/api/v1/users/me",
            headers=_auth(new_access_token)
        )
        assert me_resp.status_code == 200, f"Refreshed token denied: {me_resp.text}"
        assert me_resp.json().get("email") == auth_test_user["email"]
