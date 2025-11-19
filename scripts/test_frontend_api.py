"""
Frontend E2E API Tests (Cypress Alternative)
=============================================

Tests the Health Dashboard API endpoints that Cypress would test.
This is a fallback when Cypress has compatibility issues.

Author: Claude Code
Date: 2025-10-26
"""

import requests
import time
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin_password"


class FrontendAPITester:
    """Test Health Dashboard API endpoints"""

    def __init__(self):
        self.token = None
        self.test_results = []

    def log_test(self, test_name: str, success: bool, details: Dict[str, Any]):
        """Log test result"""
        result = {
            'test': test_name,
            'success': success,
            'details': details
        }
        self.test_results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} | {test_name}")
        for key, value in details.items():
            print(f"  {key}: {value}")

    # =========================================================================
    # TEST 1: Admin Login
    # =========================================================================

    def test_1_admin_login(self) -> bool:
        """Test 1: Admin can login and get access token"""
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD
                },
                timeout=10
            )

            success = (
                response.status_code == 200 and
                "access_token" in response.json()
            )

            if success:
                self.token = response.json()["access_token"]

            self.log_test(
                "Admin Login",
                success,
                {
                    'status_code': response.status_code,
                    'has_access_token': "access_token" in response.json(),
                    'token_type': response.json().get('token_type')
                }
            )
            return success

        except Exception as e:
            self.log_test("Admin Login", False, {'error': str(e)})
            return False

    # =========================================================================
    # TEST 2: Health Status Endpoint
    # =========================================================================

    def test_2_health_status(self) -> bool:
        """Test 2: Get health status"""
        try:
            response = requests.get(
                f"{BASE_URL}/health/status",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )

            data = response.json()
            success = (
                response.status_code == 200 and
                "status" in data and
                "last_check" in data
            )

            self.log_test(
                "Health Status Endpoint",
                success,
                {
                    'status_code': response.status_code,
                    'status': data.get('status'),
                    'last_check': data.get('last_check')
                }
            )
            return success

        except Exception as e:
            self.log_test("Health Status Endpoint", False, {'error': str(e)})
            return False

    # =========================================================================
    # TEST 3: Health Metrics Endpoint
    # =========================================================================

    def test_3_health_metrics(self) -> bool:
        """Test 3: Get health metrics"""
        try:
            response = requests.get(
                f"{BASE_URL}/health/metrics",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )

            data = response.json()
            success = (
                response.status_code == 200 and
                "total_users" in data and
                "consistency_rate" in data
            )

            self.log_test(
                "Health Metrics Endpoint",
                success,
                {
                    'status_code': response.status_code,
                    'total_users': data.get('total_users'),
                    'consistency_rate': data.get('consistency_rate'),
                    'consistent': data.get('consistent'),
                    'inconsistent': data.get('inconsistent')
                }
            )
            return success

        except Exception as e:
            self.log_test("Health Metrics Endpoint", False, {'error': str(e)})
            return False

    # =========================================================================
    # TEST 4: Health Violations Endpoint
    # =========================================================================

    def test_4_health_violations(self) -> bool:
        """Test 4: Get health violations"""
        try:
            response = requests.get(
                f"{BASE_URL}/health/violations",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )

            success = (
                response.status_code == 200 and
                isinstance(response.json(), list)
            )

            violations_count = len(response.json())

            self.log_test(
                "Health Violations Endpoint",
                success,
                {
                    'status_code': response.status_code,
                    'violations_count': violations_count,
                    'is_list': isinstance(response.json(), list)
                }
            )
            return success

        except Exception as e:
            self.log_test("Health Violations Endpoint", False, {'error': str(e)})
            return False

    # =========================================================================
    # TEST 5: Manual Health Check Trigger
    # =========================================================================

    def test_5_manual_health_check(self) -> bool:
        """Test 5: Trigger manual health check"""
        try:
            print("  ⏳ Running manual health check (may take 10-20 seconds)...")

            response = requests.post(
                f"{BASE_URL}/health/check-now",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30
            )

            data = response.json()
            success = (
                response.status_code == 200 and
                "total_checked" in data and
                "consistent" in data
            )

            self.log_test(
                "Manual Health Check Trigger",
                success,
                {
                    'status_code': response.status_code,
                    'total_checked': data.get('total_checked'),
                    'consistent': data.get('consistent'),
                    'inconsistent': data.get('inconsistent'),
                    'consistency_rate': data.get('consistency_rate')
                }
            )
            return success

        except Exception as e:
            self.log_test("Manual Health Check Trigger", False, {'error': str(e)})
            return False

    # =========================================================================
    # TEST 6: Auth Required (401 without token)
    # =========================================================================

    def test_6_auth_required(self) -> bool:
        """Test 6: Endpoints require authentication"""
        try:
            response = requests.get(
                f"{BASE_URL}/health/status",
                timeout=10
            )

            success = response.status_code in [401, 403]

            self.log_test(
                "Auth Required (401/403 without token)",
                success,
                {
                    'status_code': response.status_code,
                    'requires_auth': response.status_code in [401, 403]
                }
            )
            return success

        except Exception as e:
            self.log_test("Auth Required (401 without token)", False, {'error': str(e)})
            return False

    # =========================================================================
    # TEST 7: Response Times
    # =========================================================================

    def test_7_response_times(self) -> bool:
        """Test 7: API response times are acceptable"""
        try:
            endpoints = [
                ("/health/status", 100),  # <100ms
                ("/health/metrics", 100),  # <100ms
                ("/health/violations", 200)  # <200ms
            ]

            all_passed = True
            timings = {}

            for endpoint, max_ms in endpoints:
                start = time.time()
                response = requests.get(
                    f"{BASE_URL}{endpoint}",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10
                )
                duration_ms = (time.time() - start) * 1000

                passed = duration_ms < max_ms
                all_passed = all_passed and passed
                timings[endpoint] = {
                    'duration_ms': round(duration_ms, 2),
                    'max_ms': max_ms,
                    'passed': passed
                }

            self.log_test(
                "API Response Times",
                all_passed,
                timings
            )
            return all_passed

        except Exception as e:
            self.log_test("API Response Times", False, {'error': str(e)})
            return False

    # =========================================================================
    # Main Test Runner
    # =========================================================================

    def run_all_tests(self):
        """Run all API tests"""
        print("\n" + "="*70)
        print("🧪 FRONTEND E2E API TESTS (Cypress Alternative)")
        print("Health Dashboard API Endpoint Validation")
        print("="*70)

        tests = [
            self.test_1_admin_login,
            self.test_2_health_status,
            self.test_3_health_metrics,
            self.test_4_health_violations,
            self.test_5_manual_health_check,
            self.test_6_auth_required,
            self.test_7_response_times
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"\n❌ Test failed with exception: {str(e)}")
                failed += 1

        # Summary
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {len(tests)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/len(tests)*100):.1f}%")

        # Save results
        with open("logs/test_reports/frontend_api_tests.json", 'w') as f:
            json.dump({
                'total_tests': len(tests),
                'passed': passed,
                'failed': failed,
                'success_rate': round(passed/len(tests)*100, 2),
                'results': self.test_results
            }, f, indent=2)

        print(f"\n📝 Full report saved: logs/test_reports/frontend_api_tests.json")
        print("="*70 + "\n")

        return passed == len(tests)


def main():
    """Main test runner"""
    tester = FrontendAPITester()
    success = tester.run_all_tests()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
