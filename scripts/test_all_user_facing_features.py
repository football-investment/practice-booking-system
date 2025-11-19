"""
COMPLETE USER-FACING BACKEND DIAGNOSTICS
=========================================

Tests ALL backend endpoints that users interact with through the UI.
This is a comprehensive diagnostic tool to ensure the backend is
ready for production deployment.

Author: Claude Code
Date: 2025-10-26
"""

import requests
import json
import time
from typing import Dict, Any, List
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin_password"


class UserFacingDiagnostics:
    """Complete diagnostics for all user-facing backend features"""

    def __init__(self):
        self.admin_token = None
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def log_test(self, category: str, test_name: str, success: bool, details: Dict[str, Any]):
        """Log test result"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
        else:
            self.failed_tests += 1

        result = {
            'category': category,
            'test': test_name,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.test_results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | [{category}] {test_name}")
        if not success or details:
            for key, value in details.items():
                print(f"     {key}: {value}")

    # =========================================================================
    # CATEGORY 1: AUTHENTICATION & USER MANAGEMENT
    # =========================================================================

    def test_admin_login(self) -> bool:
        """Test admin login"""
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                timeout=10
            )

            success = response.status_code == 200 and "access_token" in response.json()
            if success:
                self.admin_token = response.json()["access_token"]

            self.log_test(
                "AUTH",
                "Admin Login",
                success,
                {
                    'status_code': response.status_code,
                    'has_token': "access_token" in response.json() if response.status_code == 200 else False
                }
            )
            return success
        except Exception as e:
            self.log_test("AUTH", "Admin Login", False, {'error': str(e)})
            return False

    def test_token_refresh(self) -> bool:
        """Test JWT token refresh"""
        try:
            # First get refresh token
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                timeout=10
            )

            if response.status_code != 200:
                self.log_test("AUTH", "Token Refresh - Get Refresh Token", False, {'error': 'Login failed'})
                return False

            refresh_token = response.json().get("refresh_token")
            if not refresh_token:
                self.log_test("AUTH", "Token Refresh", False, {'error': 'No refresh token in response'})
                return False

            # Now refresh
            refresh_response = requests.post(
                f"{BASE_URL}/auth/refresh",
                json={"refresh_token": refresh_token},
                timeout=10
            )

            success = refresh_response.status_code == 200 and "access_token" in refresh_response.json()
            self.log_test(
                "AUTH",
                "Token Refresh",
                success,
                {
                    'status_code': refresh_response.status_code,
                    'has_new_token': "access_token" in refresh_response.json() if refresh_response.status_code == 200 else False
                }
            )
            return success
        except Exception as e:
            self.log_test("AUTH", "Token Refresh", False, {'error': str(e)})
            return False

    def test_user_profile(self) -> bool:
        """Test get current user profile"""
        try:
            response = requests.get(
                f"{BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )

            success = response.status_code == 200 and "email" in response.json()
            self.log_test(
                "AUTH",
                "Get User Profile",
                success,
                {
                    'status_code': response.status_code,
                    'email': response.json().get('email') if response.status_code == 200 else None
                }
            )
            return success
        except Exception as e:
            self.log_test("AUTH", "Get User Profile", False, {'error': str(e)})
            return False

    # =========================================================================
    # CATEGORY 2: HEALTH DASHBOARD (ADMIN UI)
    # =========================================================================

    def test_health_status(self) -> bool:
        """Test health status endpoint"""
        try:
            response = requests.get(
                f"{BASE_URL}/health/status",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )

            data = response.json()
            success = (
                response.status_code == 200 and
                "status" in data and
                "consistency_rate" in data
            )

            self.log_test(
                "HEALTH_DASHBOARD",
                "Get Health Status",
                success,
                {
                    'status_code': response.status_code,
                    'system_status': data.get('status'),
                    'consistency_rate': data.get('consistency_rate')
                }
            )
            return success
        except Exception as e:
            self.log_test("HEALTH_DASHBOARD", "Get Health Status", False, {'error': str(e)})
            return False

    def test_health_metrics(self) -> bool:
        """Test health metrics endpoint"""
        try:
            response = requests.get(
                f"{BASE_URL}/health/metrics",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )

            data = response.json()
            success = (
                response.status_code == 200 and
                "total_users" in data and
                "consistency_rate" in data and
                "consistent" in data and
                "inconsistent" in data
            )

            self.log_test(
                "HEALTH_DASHBOARD",
                "Get Health Metrics",
                success,
                {
                    'status_code': response.status_code,
                    'total_users': data.get('total_users'),
                    'consistency_rate': data.get('consistency_rate')
                }
            )
            return success
        except Exception as e:
            self.log_test("HEALTH_DASHBOARD", "Get Health Metrics", False, {'error': str(e)})
            return False

    def test_health_violations(self) -> bool:
        """Test health violations list"""
        try:
            response = requests.get(
                f"{BASE_URL}/health/violations",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )

            success = response.status_code == 200 and isinstance(response.json(), list)
            self.log_test(
                "HEALTH_DASHBOARD",
                "Get Violations List",
                success,
                {
                    'status_code': response.status_code,
                    'violations_count': len(response.json()) if success else 0,
                    'is_list': isinstance(response.json(), list) if response.status_code == 200 else False
                }
            )
            return success
        except Exception as e:
            self.log_test("HEALTH_DASHBOARD", "Get Violations List", False, {'error': str(e)})
            return False

    def test_manual_health_check(self) -> bool:
        """Test manual health check trigger"""
        try:
            print("     ⏳ Running manual health check (10-20 seconds)...")
            response = requests.post(
                f"{BASE_URL}/health/check-now",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=30
            )

            data = response.json()
            success = (
                response.status_code == 200 and
                "total_checked" in data and
                "consistent" in data
            )

            self.log_test(
                "HEALTH_DASHBOARD",
                "Manual Health Check Trigger",
                success,
                {
                    'status_code': response.status_code,
                    'total_checked': data.get('total_checked'),
                    'consistent': data.get('consistent'),
                    'inconsistent': data.get('inconsistent')
                }
            )
            return success
        except Exception as e:
            self.log_test("HEALTH_DASHBOARD", "Manual Health Check Trigger", False, {'error': str(e)})
            return False

    # =========================================================================
    # CATEGORY 3: PROGRESS & SPECIALIZATION (STUDENT/INSTRUCTOR UI)
    # =========================================================================

    def test_get_specializations(self) -> bool:
        """Test get all specializations"""
        try:
            response = requests.get(
                f"{BASE_URL}/specializations",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )

            success = response.status_code == 200 and isinstance(response.json(), list)
            self.log_test(
                "SPECIALIZATIONS",
                "Get All Specializations",
                success,
                {
                    'status_code': response.status_code,
                    'count': len(response.json()) if success else 0
                }
            )
            return success
        except Exception as e:
            self.log_test("SPECIALIZATIONS", "Get All Specializations", False, {'error': str(e)})
            return False

    def test_get_user_progress(self) -> bool:
        """Test get user progress"""
        try:
            # Get any user ID from database
            response = requests.get(
                f"{BASE_URL}/specializations/progress/me",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )

            success = response.status_code == 200
            self.log_test(
                "SPECIALIZATIONS",
                "Get User Progress",
                success,
                {
                    'status_code': response.status_code,
                    'has_progress': bool(response.json()) if success else False
                }
            )
            return success
        except Exception as e:
            self.log_test("SPECIALIZATIONS", "Get User Progress", False, {'error': str(e)})
            return False

    # =========================================================================
    # CATEGORY 4: LICENSES (STUDENT UI)
    # =========================================================================

    def test_get_user_licenses(self) -> bool:
        """Test get user licenses"""
        try:
            response = requests.get(
                f"{BASE_URL}/licenses/me",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )

            success = response.status_code == 200
            self.log_test(
                "LICENSES",
                "Get User Licenses",
                success,
                {
                    'status_code': response.status_code,
                    'has_licenses': bool(response.json()) if success else False
                }
            )
            return success
        except Exception as e:
            self.log_test("LICENSES", "Get User Licenses", False, {'error': str(e)})
            return False

    def test_get_license_metadata(self) -> bool:
        """Test get license metadata (for UI display)"""
        try:
            response = requests.get(
                f"{BASE_URL}/licenses/metadata/PLAYER",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )

            success = response.status_code == 200 and isinstance(response.json(), list)
            self.log_test(
                "LICENSES",
                "Get License Metadata",
                success,
                {
                    'status_code': response.status_code,
                    'levels_count': len(response.json()) if success else 0
                }
            )
            return success
        except Exception as e:
            self.log_test("LICENSES", "Get License Metadata", False, {'error': str(e)})
            return False

    # =========================================================================
    # CATEGORY 5: ADMIN DASHBOARD
    # =========================================================================

    def test_get_all_users(self) -> bool:
        """Test get all users (admin)"""
        try:
            response = requests.get(
                f"{BASE_URL}/users?skip=0&limit=10",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )

            data = response.json() if response.status_code == 200 else {}
            # Endpoint returns {users: [...], total: int, page: int, size: int}
            success = response.status_code == 200 and 'users' in data and isinstance(data.get('users'), list)
            self.log_test(
                "ADMIN_DASHBOARD",
                "Get All Users",
                success,
                {
                    'status_code': response.status_code,
                    'users_count': len(data.get('users', [])) if success else 0
                }
            )
            return success
        except Exception as e:
            self.log_test("ADMIN_DASHBOARD", "Get All Users", False, {'error': str(e)})
            return False

    def test_get_dashboard_stats(self) -> bool:
        """Test get dashboard statistics"""
        try:
            response = requests.get(
                f"{BASE_URL}/admin/stats",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )

            data = response.json()
            success = response.status_code == 200 and "total_users" in data
            self.log_test(
                "ADMIN_DASHBOARD",
                "Get Dashboard Stats",
                success,
                {
                    'status_code': response.status_code,
                    'total_users': data.get('total_users') if success else None
                }
            )
            return success
        except Exception as e:
            self.log_test("ADMIN_DASHBOARD", "Get Dashboard Stats", False, {'error': str(e)})
            return False

    # =========================================================================
    # CATEGORY 6: PERFORMANCE & RELIABILITY
    # =========================================================================

    def test_response_times(self) -> bool:
        """Test API response times"""
        try:
            endpoints = [
                ("/health/status", 100, "Health Status"),
                ("/health/metrics", 100, "Health Metrics"),
                ("/specializations", 200, "Specializations"),
                ("/licenses/me", 200, "User Licenses"),
            ]

            all_passed = True
            timings = {}

            for endpoint, max_ms, name in endpoints:
                start = time.time()
                response = requests.get(
                    f"{BASE_URL}{endpoint}",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    timeout=10
                )
                duration_ms = (time.time() - start) * 1000

                passed = duration_ms < max_ms and response.status_code == 200
                all_passed = all_passed and passed
                timings[name] = {
                    'duration_ms': round(duration_ms, 2),
                    'max_ms': max_ms,
                    'passed': passed,
                    'status_code': response.status_code
                }

            self.log_test(
                "PERFORMANCE",
                "API Response Times",
                all_passed,
                timings
            )
            return all_passed
        except Exception as e:
            self.log_test("PERFORMANCE", "API Response Times", False, {'error': str(e)})
            return False

    def test_concurrent_requests(self) -> bool:
        """Test handling concurrent requests"""
        try:
            import concurrent.futures

            def make_request():
                return requests.get(
                    f"{BASE_URL}/health/status",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    timeout=10
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                responses = [f.result() for f in concurrent.futures.as_completed(futures)]

            success_count = sum(1 for r in responses if r.status_code == 200)
            success = success_count == 10

            self.log_test(
                "PERFORMANCE",
                "Concurrent Requests (10)",
                success,
                {
                    'total_requests': 10,
                    'successful': success_count,
                    'failed': 10 - success_count
                }
            )
            return success
        except Exception as e:
            self.log_test("PERFORMANCE", "Concurrent Requests", False, {'error': str(e)})
            return False

    # =========================================================================
    # MAIN TEST RUNNER
    # =========================================================================

    def run_all_diagnostics(self):
        """Run all user-facing diagnostics"""
        print("\n" + "="*80)
        print("🔍 COMPLETE USER-FACING BACKEND DIAGNOSTICS")
        print("="*80)
        print(f"Backend: {BASE_URL}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")

        # Authentication
        print("\n📝 CATEGORY 1: AUTHENTICATION & USER MANAGEMENT")
        print("-" * 80)
        self.test_admin_login()
        if not self.admin_token:
            print("\n❌ CRITICAL: Admin login failed. Cannot continue tests.")
            return False

        self.test_token_refresh()
        self.test_user_profile()

        # Health Dashboard
        print("\n🏥 CATEGORY 2: HEALTH DASHBOARD (ADMIN UI)")
        print("-" * 80)
        self.test_health_status()
        self.test_health_metrics()
        self.test_health_violations()
        self.test_manual_health_check()

        # Specializations
        print("\n🎯 CATEGORY 3: PROGRESS & SPECIALIZATIONS")
        print("-" * 80)
        self.test_get_specializations()
        self.test_get_user_progress()

        # Licenses
        print("\n🏮 CATEGORY 4: LICENSES")
        print("-" * 80)
        self.test_get_user_licenses()
        self.test_get_license_metadata()

        # Admin Dashboard
        print("\n👨‍💼 CATEGORY 5: ADMIN DASHBOARD")
        print("-" * 80)
        self.test_get_all_users()
        self.test_get_dashboard_stats()

        # Performance
        print("\n⚡ CATEGORY 6: PERFORMANCE & RELIABILITY")
        print("-" * 80)
        self.test_response_times()
        self.test_concurrent_requests()

        # Summary
        print("\n" + "="*80)
        print("📊 DIAGNOSTIC SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%")

        # Save results
        report_file = "logs/test_reports/user_facing_diagnostics.json"
        import os
        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'backend_url': BASE_URL,
                'total_tests': self.total_tests,
                'passed': self.passed_tests,
                'failed': self.failed_tests,
                'success_rate': round(self.passed_tests/self.total_tests*100, 2),
                'results': self.test_results
            }, f, indent=2)

        print(f"\n📝 Full report: {report_file}")
        print("="*80 + "\n")

        return self.passed_tests == self.total_tests


def main():
    """Main entry point"""
    diagnostics = UserFacingDiagnostics()
    success = diagnostics.run_all_diagnostics()

    if success:
        print("✅ ALL USER-FACING FEATURES WORKING")
        exit(0)
    else:
        print("❌ SOME USER-FACING FEATURES FAILING")
        exit(1)


if __name__ == "__main__":
    main()
