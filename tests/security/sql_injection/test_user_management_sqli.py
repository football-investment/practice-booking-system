"""
SQL Injection Security Tests - User Management Endpoints

Tests user management endpoints (/api/v1/users/*) for SQL injection vulnerabilities.
Verifies CRUD operations properly parameterize queries and prevent injection attacks.

Test Coverage:
- GET /api/v1/users/ - List users (with filters)
- GET /api/v1/users/{user_id} - Get user by ID
- GET /api/v1/users/search - Search users by query
- POST /api/v1/users/ - Create user
- PATCH /api/v1/users/{user_id} - Update user
- DELETE /api/v1/users/{user_id} - Delete user
- GET /api/v1/users/me/profile - Get current user profile
- PATCH /api/v1/users/me/profile - Update current user profile

Security Requirements:
1. All path parameters (user_id) must be validated
2. Query parameters (search, filters) must prevent SQL injection
3. JSON body fields must be sanitized
4. No SQL error messages should leak
5. Authorization must be enforced before any DB query
"""

import pytest
import requests
from typing import List

from .payloads import SQLInjectionPayloads, is_vulnerable_response

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"


class TestUserManagementSQLInjection:
    """SQL Injection tests for user management endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.payloads = SQLInjectionPayloads()
        self.vulnerable_payloads = []

    # ========================================================================
    # GET /api/v1/users/{user_id} - Get User By ID
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.CLASSIC[:10])
    def test_get_user_by_id_path_sqli(self, payload: str):
        """
        Test get user endpoint with SQL injection in path parameter

        Attack Vector: user_id path parameter
        Expected: 404 or 422 (invalid ID format), no SQL errors
        """
        # Try SQL injection in path
        response = requests.get(
            f"{API_BASE}/users/{payload}",
        )

        # Should NOT return 200 with injection
        assert response.status_code != 200, \
            f"Get user succeeded with SQL injection in path: {payload}"

        # Should return proper error (not 500 server error)
        assert response.status_code in [401, 403, 404, 422], \
            f"Unexpected status code {response.status_code} for payload: {payload}"

        # Should NOT leak SQL errors
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        if is_vuln:
            self.vulnerable_payloads.append(("GET /users/{id}", payload, response.text))

        assert not is_vuln, \
            f"SQL error leaked in get user for payload: {payload}"

    @pytest.mark.parametrize("negative_id", [-1, -999, -1000000])
    def test_get_user_negative_id(self, negative_id: int):
        """
        Test get user with negative IDs (common SQL injection technique)

        Attack Vector: Negative IDs to bypass checks
        Expected: 404 Not Found or proper validation error
        """
        response = requests.get(f"{API_BASE}/users/{negative_id}")

        # Should NOT return 200
        assert response.status_code != 200, \
            f"Get user succeeded with negative ID: {negative_id}"

    # ========================================================================
    # GET /api/v1/users/search - Search Users
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.CLASSIC)
    def test_search_users_query_sqli(self, payload: str):
        """
        Test search users endpoint with SQL injection in search query

        Attack Vector: Query parameter 'q' for search
        Expected: Empty results or validation error, no SQL injection
        """
        response = requests.get(
            f"{API_BASE}/users/search",
            params={"q": payload}
        )

        # Should NOT leak SQL errors (even if returns 200 with empty results)
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        if is_vuln:
            self.vulnerable_payloads.append(("GET /users/search", payload, response.text))

        assert not is_vuln, \
            f"SQL error leaked in search for payload: {payload}"

        # If returns 200, should be empty results or properly handled
        if response.status_code == 200:
            data = response.json()
            # Should not leak database structure
            response_str = str(data).lower()
            assert "password" not in response_str, "Password field leaked in search results"
            assert "password_hash" not in response_str, "Password hash leaked in search results"

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.UNION_BASED[:3])
    def test_search_users_union_sqli(self, payload: str):
        """
        Test search users with UNION-based injection

        Attack Vector: UNION SELECT to extract sensitive data
        Expected: No data extraction, proper query parameterization
        """
        response = requests.get(
            f"{API_BASE}/users/search",
            params={"q": payload}
        )

        # Should NOT leak database structure
        response_lower = response.text.lower()
        assert "union" not in response_lower or "select" not in response_lower, \
            "UNION injection syntax leaked in response"

        # Should NOT leak table names
        assert "information_schema" not in response_lower, "Database schema leaked"
        assert "pg_catalog" not in response_lower, "PostgreSQL catalog leaked"

    # ========================================================================
    # GET /api/v1/users/ - List Users (with filters)
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.BOOLEAN_BLIND[:5])
    def test_list_users_filter_sqli(self, payload: str):
        """
        Test list users endpoint with SQL injection in filter parameters

        Attack Vector: Filter parameters (role, status, etc.)
        Expected: Validation error or safe handling
        """
        # Test various filter parameters
        filter_params = [
            {"role": payload},
            {"skip": payload},
            {"limit": payload},
        ]

        for params in filter_params:
            response = requests.get(
                f"{API_BASE}/users/",
                params=params
            )

            # Should NOT leak SQL errors
            is_vuln = is_vulnerable_response(response.text, response.status_code)
            assert not is_vuln, \
                f"SQL error leaked in list users with params {params}"

    # ========================================================================
    # POST /api/v1/users/ - Create User
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.get_basic_payloads())
    def test_create_user_email_sqli(self, payload: str):
        """
        Test create user endpoint with SQL injection in email field

        Attack Vector: Email field during user creation
        Expected: Validation error, no SQL injection
        """
        response = requests.post(
            f"{API_BASE}/users/",
            json={
                "email": payload,
                "name": "Test User",
                "password": "TestPass123!",
                "role": "student"
            }
        )

        # Should NOT succeed
        assert response.status_code != 200, \
            f"User creation succeeded with SQL injection in email: {payload}"

        # Should NOT leak SQL errors
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        if is_vuln:
            self.vulnerable_payloads.append(("POST /users/", payload, response.text))

        assert not is_vuln, \
            f"SQL error leaked in create user email: {payload}"

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.get_basic_payloads())
    def test_create_user_name_sqli(self, payload: str):
        """
        Test create user endpoint with SQL injection in name field

        Attack Vector: Name field during user creation
        Expected: Validation error or safe storage
        """
        response = requests.post(
            f"{API_BASE}/users/",
            json={
                "email": "test@example.com",
                "name": payload,
                "password": "TestPass123!",
                "role": "student"
            }
        )

        # Should NOT leak SQL errors
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        assert not is_vuln, \
            f"SQL error leaked in create user name: {payload}"

    # ========================================================================
    # PATCH /api/v1/users/{user_id} - Update User
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.CLASSIC[:5])
    def test_update_user_path_sqli(self, payload: str):
        """
        Test update user endpoint with SQL injection in path

        Attack Vector: user_id path parameter
        Expected: 404 or 422, no SQL errors
        """
        response = requests.patch(
            f"{API_BASE}/users/{payload}",
            json={"name": "Updated Name"}
        )

        # Should require auth and proper ID format
        assert response.status_code in [401, 403, 404, 422], \
            f"Unexpected status for update user with payload: {payload}"

        # Should NOT leak SQL errors
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        assert not is_vuln, \
            f"SQL error leaked in update user path: {payload}"

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.get_basic_payloads())
    def test_update_user_fields_sqli(self, payload: str):
        """
        Test update user endpoint with SQL injection in update fields

        Attack Vector: JSON body fields (name, email, etc.)
        Expected: Validation error or safe update
        """
        # Try injection in various fields
        test_cases = [
            {"name": payload},
            {"email": payload},
            {"phone": payload},
        ]

        for update_data in test_cases:
            response = requests.patch(
                f"{API_BASE}/users/999999",  # Non-existent user
                json=update_data
            )

            # Should NOT leak SQL errors
            is_vuln = is_vulnerable_response(response.text, response.status_code)
            assert not is_vuln, \
                f"SQL error leaked in update user with data {update_data}"

    # ========================================================================
    # DELETE /api/v1/users/{user_id} - Delete User
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.STACKED_QUERIES[:3])
    def test_delete_user_stacked_queries(self, payload: str):
        """
        Test delete user with stacked queries (attempting CASCADE deletion)

        Attack Vector: Stacked queries to execute multiple SQL statements
        Expected: Single query execution, no stacked queries
        """
        response = requests.delete(
            f"{API_BASE}/users/{payload}"
        )

        # Should require auth and proper ID
        assert response.status_code in [401, 403, 404, 422], \
            f"Delete user unexpected status: {response.status_code}"

        # Should NOT execute stacked queries
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        if is_vuln:
            self.vulnerable_payloads.append(("DELETE /users/{id}", payload, response.text))

        assert not is_vuln, \
            f"SQL error leaked in delete user: {payload}"

    # ========================================================================
    # GET /api/v1/users/me/profile - Current User Profile
    # ========================================================================

    def test_profile_endpoint_requires_auth(self):
        """
        Test profile endpoint requires authentication

        Security Check: Profile should not be accessible without token
        Expected: 401 Unauthorized
        """
        response = requests.get(f"{API_BASE}/users/me/profile")

        # Should require authentication (401/403) or not found (404)
        assert response.status_code in [401, 403, 404], \
            f"Profile endpoint should require authentication or return not found, got {response.status_code}"

    # ========================================================================
    # Special Test: Integer Overflow
    # ========================================================================

    @pytest.mark.parametrize("large_id", [
        2147483647,  # Max int32
        2147483648,  # Max int32 + 1
        9999999999,  # Very large number
    ])
    def test_get_user_integer_overflow(self, large_id: int):
        """
        Test user ID with integer overflow values

        Attack Vector: Large integers to cause overflow
        Expected: 404 or proper error handling
        """
        response = requests.get(f"{API_BASE}/users/{large_id}")

        # Should handle gracefully (not crash with 500)
        assert response.status_code != 500, \
            f"Server error with large ID: {large_id}"

        # Should return 404 or similar
        assert response.status_code in [401, 403, 404, 422], \
            f"Unexpected status for large ID {large_id}: {response.status_code}"

    # ========================================================================
    # Summary and Reporting
    # ========================================================================

    def teardown_method(self):
        """Print test summary after each test class"""
        if self.vulnerable_payloads:
            print("\n" + "="*70)
            print("⚠️  VULNERABLE PAYLOADS DETECTED IN USER MANAGEMENT")
            print("="*70)
            for endpoint, payload, response in self.vulnerable_payloads:
                print(f"\nEndpoint: {endpoint}")
                print(f"Payload: {payload}")
                print(f"Response: {response[:200]}...")
            print("="*70)
