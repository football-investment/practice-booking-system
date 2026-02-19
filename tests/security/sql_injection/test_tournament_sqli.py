"""
SQL Injection Security Tests - Tournament Endpoints

Tests tournament endpoints (/api/v1/tournaments/*) for SQL injection vulnerabilities.
This is a HIGH PRIORITY test suite as tournaments involve financial transactions,
user enrollments, and complex business logic.

Test Coverage:
- POST /api/v1/tournaments/ - Create tournament
- GET /api/v1/tournaments/available - List available tournaments
- POST /api/v1/tournaments/{id}/enroll - Enroll in tournament
- GET /api/v1/tournaments/{id}/summary - Get tournament summary
- PATCH /api/v1/tournaments/{id}/status - Update tournament status
- POST /api/v1/tournaments/{id}/instructor-applications - Apply as instructor
- DELETE /api/v1/tournaments/{id} - Delete tournament

Security Requirements:
1. Path parameters (tournament_id, application_id) must be validated
2. Query parameters (filters, search) must prevent SQL injection
3. JSON body fields must be sanitized
4. No SQL error messages should leak
5. Authorization must be enforced
6. Financial operations must be atomic and secure
"""

import pytest
import requests
from typing import List

from .payloads import SQLInjectionPayloads, is_vulnerable_response

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"


class TestTournamentSQLInjection:
    """SQL Injection tests for tournament endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.payloads = SQLInjectionPayloads()
        self.vulnerable_payloads = []

    # ========================================================================
    # GET /api/v1/tournaments/available - List Available Tournaments
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.CLASSIC[:10])
    def test_available_tournaments_filter_sqli(self, payload: str):
        """
        Test available tournaments with SQL injection in filter parameters

        Attack Vector: Query parameters for filtering
        Expected: Safe handling, no SQL injection
        """
        # Test various filter combinations
        filter_params = [
            {"age_group": payload},
            {"specialization_type": payload},
            {"location": payload},
        ]

        for params in filter_params:
            response = requests.get(
                f"{API_BASE}/tournaments/available",
                params=params
            )

            # Should NOT leak SQL errors
            is_vuln = is_vulnerable_response(response.text, response.status_code)
            if is_vuln:
                self.vulnerable_payloads.append(
                    ("GET /tournaments/available", payload, response.text)
                )

            assert not is_vuln, \
                f"SQL error leaked in available tournaments with params {params}"

    # ========================================================================
    # GET /api/v1/tournaments/{tournament_id}/summary - Tournament Summary
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.CLASSIC)
    def test_tournament_summary_path_sqli(self, payload: str):
        """
        Test tournament summary with SQL injection in path parameter

        Attack Vector: tournament_id path parameter
        Expected: 404 or 422, no SQL errors
        """
        response = requests.get(
            f"{API_BASE}/tournaments/{payload}/summary"
        )

        # Should NOT return 200 with injection
        assert response.status_code != 200, \
            f"Tournament summary succeeded with SQL injection: {payload}"

        # Should return proper error (405 = routing-level rejection, also safe)
        assert response.status_code in [401, 403, 404, 405, 422], \
            f"Unexpected status code {response.status_code} for payload: {payload}"

        # Should NOT leak SQL errors
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        if is_vuln:
            self.vulnerable_payloads.append(
                ("GET /tournaments/{id}/summary", payload, response.text)
            )

        assert not is_vuln, \
            f"SQL error leaked in tournament summary: {payload}"

    @pytest.mark.parametrize("negative_id", [-1, -999, -1000000])
    def test_tournament_negative_id(self, negative_id: int):
        """
        Test tournament endpoints with negative IDs

        Attack Vector: Negative IDs to bypass checks
        Expected: 404 Not Found or validation error
        """
        response = requests.get(f"{API_BASE}/tournaments/{negative_id}/summary")

        # Should NOT return 200
        assert response.status_code != 200, \
            f"Tournament summary succeeded with negative ID: {negative_id}"

    # ========================================================================
    # POST /api/v1/tournaments/ - Create Tournament
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.get_basic_payloads())
    def test_create_tournament_name_sqli(self, payload: str):
        """
        Test create tournament with SQL injection in name field

        Attack Vector: Tournament name field
        Expected: Validation error or safe storage
        """
        response = requests.post(
            f"{API_BASE}/tournaments/",
            json={
                "name": payload,
                "start_date": "2026-07-01",
                "end_date": "2026-07-15",
                "specialization_type": "LFA_FOOTBALL_PLAYER",
                "age_group": "AMATEUR",
                "enrollment_cost": 50,
                "reward_policy_name": "standard_league_tournament"
            }
        )

        # Should NOT leak SQL errors (might require auth)
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        if is_vuln:
            self.vulnerable_payloads.append(
                ("POST /tournaments/", payload, response.text)
            )

        assert not is_vuln, \
            f"SQL error leaked in create tournament name: {payload}"

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.get_basic_payloads())
    def test_create_tournament_location_sqli(self, payload: str):
        """
        Test create tournament with SQL injection in location fields

        Attack Vector: Location city, venue, address fields
        Expected: Validation error or safe storage
        """
        response = requests.post(
            f"{API_BASE}/tournaments/",
            json={
                "name": "Test Tournament",
                "start_date": "2026-07-01",
                "end_date": "2026-07-15",
                "specialization_type": "LFA_FOOTBALL_PLAYER",
                "age_group": "AMATEUR",
                "enrollment_cost": 50,
                "location_city": payload,
                "reward_policy_name": "standard_league_tournament"
            }
        )

        # Should NOT leak SQL errors
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        assert not is_vuln, \
            f"SQL error leaked in tournament location: {payload}"

    # ========================================================================
    # POST /api/v1/tournaments/{tournament_id}/enroll - Tournament Enrollment
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.CLASSIC[:10])
    def test_tournament_enroll_path_sqli(self, payload: str):
        """
        Test tournament enrollment with SQL injection in path

        Attack Vector: tournament_id path parameter
        Expected: 404 or 422, no SQL errors
        CRITICAL: This endpoint involves credit deduction - must be secure!
        """
        response = requests.post(
            f"{API_BASE}/tournaments/{payload}/enroll",
            json={}
        )

        # Should require auth and proper ID (405 = routing-level rejection)
        assert response.status_code in [401, 403, 404, 405, 422], \
            f"Enroll endpoint unexpected status: {response.status_code}"

        # CRITICAL: Should NOT leak SQL errors (involves financial transaction)
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        if is_vuln:
            self.vulnerable_payloads.append(
                ("POST /tournaments/{id}/enroll", payload, response.text)
            )

        assert not is_vuln, \
            f"SQL error leaked in tournament enroll: {payload}"

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.STACKED_QUERIES[:3])
    def test_tournament_enroll_stacked_queries(self, payload: str):
        """
        Test tournament enrollment with stacked queries

        Attack Vector: Stacked queries to manipulate credits or enrollment
        Expected: Single query execution only
        CRITICAL: Financial security - no stacked queries!
        """
        response = requests.post(
            f"{API_BASE}/tournaments/{payload}/enroll",
            json={}
        )

        # Should NOT execute stacked queries
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        if is_vuln:
            self.vulnerable_payloads.append(
                ("POST /tournaments/enroll STACKED", payload, response.text)
            )

        assert not is_vuln, \
            f"Stacked query vulnerability in tournament enroll: {payload}"

        # Should NOT leak database structure
        response_lower = response.text.lower()
        assert "credit_balance" not in response_lower or "update" not in response_lower, \
            "Credit manipulation syntax leaked in response"

    # ========================================================================
    # POST /api/v1/tournaments/{id}/instructor-applications - Apply as Instructor
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.CLASSIC[:5])
    def test_instructor_application_path_sqli(self, payload: str):
        """
        Test instructor application with SQL injection in path

        Attack Vector: tournament_id path parameter
        Expected: 404 or 422, no SQL errors
        """
        response = requests.post(
            f"{API_BASE}/tournaments/{payload}/instructor-applications",
            json={
                "application_message": "I would like to be the instructor"
            }
        )

        # Should require auth (405 = routing-level rejection)
        assert response.status_code in [401, 403, 404, 405, 422], \
            f"Instructor application unexpected status: {response.status_code}"

        # Should NOT leak SQL errors
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        assert not is_vuln, \
            f"SQL error leaked in instructor application: {payload}"

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.get_basic_payloads())
    def test_instructor_application_message_sqli(self, payload: str):
        """
        Test instructor application with SQL injection in message

        Attack Vector: Application message field
        Expected: Safe storage, no injection
        """
        response = requests.post(
            f"{API_BASE}/tournaments/999999/instructor-applications",
            json={
                "application_message": payload
            }
        )

        # Should NOT leak SQL errors
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        assert not is_vuln, \
            f"SQL error leaked in application message: {payload}"

    # ========================================================================
    # GET /api/v1/tournaments/{id}/instructor-applications - List Applications
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.UNION_BASED[:3])
    def test_list_applications_union_sqli(self, payload: str):
        """
        Test list instructor applications with UNION injection

        Attack Vector: UNION SELECT to extract application data
        Expected: No data extraction
        """
        response = requests.get(
            f"{API_BASE}/tournaments/{payload}/instructor-applications"
        )

        # Should NOT leak database structure
        response_lower = response.text.lower()
        assert "union" not in response_lower or "select" not in response_lower, \
            "UNION injection syntax leaked in applications list"

    # ========================================================================
    # PATCH /api/v1/tournaments/{id}/status - Update Tournament Status
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.CLASSIC[:5])
    def test_update_status_path_sqli(self, payload: str):
        """
        Test update tournament status with SQL injection in path

        Attack Vector: tournament_id path parameter
        Expected: 404 or 422, no SQL errors
        CRITICAL: Status changes affect tournament lifecycle!
        """
        response = requests.patch(
            f"{API_BASE}/tournaments/{payload}/status",
            json={
                "new_status": "ENROLLMENT_OPEN"
            }
        )

        # Should require admin auth (405 = routing-level rejection)
        assert response.status_code in [401, 403, 404, 405, 422], \
            f"Update status unexpected status: {response.status_code}"

        # CRITICAL: Should NOT leak SQL errors (affects tournament state)
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        if is_vuln:
            self.vulnerable_payloads.append(
                ("PATCH /tournaments/{id}/status", payload, response.text)
            )

        assert not is_vuln, \
            f"SQL error leaked in update status: {payload}"

    # ========================================================================
    # DELETE /api/v1/tournaments/{id} - Delete Tournament
    # ========================================================================

    @pytest.mark.parametrize("payload", SQLInjectionPayloads.STACKED_QUERIES)
    def test_delete_tournament_stacked_queries(self, payload: str):
        """
        Test delete tournament with stacked queries

        Attack Vector: Stacked queries to delete multiple tournaments
        Expected: Single query execution only
        CRITICAL: Should not allow cascading deletes via injection!
        """
        response = requests.delete(
            f"{API_BASE}/tournaments/{payload}"
        )

        # Should require admin auth (405 = routing-level rejection)
        assert response.status_code in [401, 403, 404, 405, 422], \
            f"Delete tournament unexpected status: {response.status_code}"

        # Should NOT execute stacked queries
        is_vuln = is_vulnerable_response(response.text, response.status_code)
        if is_vuln:
            self.vulnerable_payloads.append(
                ("DELETE /tournaments/{id}", payload, response.text)
            )

        assert not is_vuln, \
            f"Stacked query vulnerability in delete tournament: {payload}"

    # ========================================================================
    # Special Test: Integer Overflow in Tournament IDs
    # ========================================================================

    @pytest.mark.parametrize("large_id", [
        2147483647,  # Max int32
        2147483648,  # Max int32 + 1
        9999999999,  # Very large number
    ])
    def test_tournament_integer_overflow(self, large_id: int):
        """
        Test tournament endpoints with integer overflow values

        Attack Vector: Large integers to cause overflow
        Expected: 404 or proper error handling
        """
        endpoints = [
            f"/tournaments/{large_id}/summary",
            f"/tournaments/{large_id}/enroll",
            f"/tournaments/{large_id}/instructor-applications",
        ]

        for endpoint in endpoints:
            response = requests.get(f"{API_BASE}{endpoint}")

            # Should handle gracefully (not crash with 500)
            assert response.status_code != 500, \
                f"Server error with large ID on {endpoint}: {large_id}"

    # ========================================================================
    # Summary and Reporting
    # ========================================================================

    def teardown_method(self):
        """Print test summary after each test class"""
        if self.vulnerable_payloads:
            print("\n" + "="*70)
            print("⚠️  CRITICAL: VULNERABLE PAYLOADS IN TOURNAMENT ENDPOINTS")
            print("="*70)
            for endpoint, payload, response in self.vulnerable_payloads:
                print(f"\nEndpoint: {endpoint}")
                print(f"Payload: {payload}")
                print(f"Response: {response[:200]}...")
            print("="*70)
            print("⚠️  TOURNAMENTS INVOLVE FINANCIAL TRANSACTIONS - FIX IMMEDIATELY!")
            print("="*70)
