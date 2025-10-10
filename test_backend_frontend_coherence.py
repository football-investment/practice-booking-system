#!/usr/bin/env python3
"""
Backend-Frontend Coherence Test Suite
Tests all student dashboard endpoints and validates data structures
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

# Test credentials
TEST_STUDENT = {
    "email": "student@test.com",
    "password": "password123"
}

class CoherenceTestRunner:
    def __init__(self):
        self.token = None
        self.results = []
        self.errors = []

    def log_test(self, name, passed, details="", error=None):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test": name,
            "passed": passed,
            "status": status,
            "details": details,
            "error": str(error) if error else None
        }
        self.results.append(result)
        print(f"{status} | {name}")
        if details:
            print(f"    {details}")
        if error:
            print(f"    ERROR: {error}")
        print()

    def test_authentication(self):
        """Test student authentication"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json=TEST_STUDENT,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.log_test(
                    "Student Authentication",
                    True,
                    f"Token obtained successfully"
                )
                return True
            else:
                self.log_test(
                    "Student Authentication",
                    False,
                    f"Status: {response.status_code}",
                    response.text
                )
                return False

        except Exception as e:
            self.log_test("Student Authentication", False, error=e)
            return False

    def get_headers(self):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}"}

    def test_semester_progress_endpoint(self):
        """Test /api/v1/students/dashboard/semester-progress"""
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/students/dashboard/semester-progress",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                progress = data.get("progress", {})

                # Validate structure
                required_fields = ["current_phase", "completion_percentage", "timeline"]
                missing = [f for f in required_fields if f not in progress]

                if missing:
                    self.log_test(
                        "Semester Progress Endpoint",
                        False,
                        f"Missing fields: {missing}",
                        "Incomplete data structure"
                    )
                else:
                    self.log_test(
                        "Semester Progress Endpoint",
                        True,
                        f"Phase: {progress['current_phase']}, Progress: {progress['completion_percentage']}%"
                    )
                    return data
            else:
                self.log_test(
                    "Semester Progress Endpoint",
                    False,
                    f"Status: {response.status_code}",
                    response.text
                )

        except Exception as e:
            self.log_test("Semester Progress Endpoint", False, error=e)

        return None

    def test_achievements_endpoint(self):
        """Test /api/v1/students/dashboard/achievements"""
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/students/dashboard/achievements",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                achievements = data.get("achievements", [])
                summary = data.get("summary", {})

                self.log_test(
                    "Achievements Endpoint",
                    True,
                    f"Found {len(achievements)} achievements, Total XP: {summary.get('total_xp', 0)}"
                )
                return data
            else:
                self.log_test(
                    "Achievements Endpoint",
                    False,
                    f"Status: {response.status_code}",
                    response.text
                )

        except Exception as e:
            self.log_test("Achievements Endpoint", False, error=e)

        return None

    def test_daily_challenge_endpoint(self):
        """Test /api/v1/students/dashboard/daily-challenge"""
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/students/dashboard/daily-challenge",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                challenge = data.get("daily_challenge")

                if challenge:
                    self.log_test(
                        "Daily Challenge Endpoint",
                        True,
                        f"Challenge: {challenge.get('challenge_type', 'N/A')}, Difficulty: {challenge.get('difficulty', 'N/A')}"
                    )
                else:
                    self.log_test(
                        "Daily Challenge Endpoint",
                        True,
                        "No active challenge today"
                    )
                return data
            else:
                self.log_test(
                    "Daily Challenge Endpoint",
                    False,
                    f"Status: {response.status_code}",
                    response.text
                )

        except Exception as e:
            self.log_test("Daily Challenge Endpoint", False, error=e)

        return None

    def test_sessions_endpoint(self):
        """Test /api/v1/sessions/ endpoint"""
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/sessions/",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                # Handle both array and object responses
                data = response.json()
                sessions = data if isinstance(data, list) else data.get("sessions", [])

                self.log_test(
                    "Sessions List Endpoint",
                    True,
                    f"Found {len(sessions)} sessions"
                )
                return sessions
            else:
                self.log_test(
                    "Sessions List Endpoint",
                    False,
                    f"Status: {response.status_code}",
                    response.text
                )

        except Exception as e:
            self.log_test("Sessions List Endpoint", False, error=e)

        return None

    def test_projects_endpoints(self):
        """Test project-related endpoints"""
        endpoints_to_test = [
            ("/api/v1/projects/", "Projects List"),
            ("/api/v1/projects/my/current", "My Current Project"),
            ("/api/v1/projects/my/summary", "My Projects Summary")
        ]

        results = {}

        for endpoint, name in endpoints_to_test:
            try:
                response = requests.get(
                    f"{BASE_URL}{endpoint}",
                    headers=self.get_headers(),
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    results[endpoint] = data

                    # Get count
                    if isinstance(data, dict):
                        if "projects" in data:
                            count = len(data["projects"])
                        elif "total" in data:
                            count = data["total"]
                        else:
                            count = "N/A"
                    elif isinstance(data, list):
                        count = len(data)
                    else:
                        count = "1" if data else "0"

                    self.log_test(
                        f"Projects Endpoint: {name}",
                        True,
                        f"Status: {response.status_code}, Count: {count}"
                    )
                elif response.status_code == 404:
                    self.log_test(
                        f"Projects Endpoint: {name}",
                        True,
                        f"No data found (404) - acceptable"
                    )
                else:
                    self.log_test(
                        f"Projects Endpoint: {name}",
                        False,
                        f"Status: {response.status_code}",
                        response.text
                    )

            except Exception as e:
                self.log_test(f"Projects Endpoint: {name}", False, error=e)

        return results

    def test_frontend_accessibility(self):
        """Test frontend accessibility"""
        try:
            response = requests.get(FRONTEND_URL, timeout=10)

            if response.status_code == 200:
                self.log_test(
                    "Frontend Server Accessibility",
                    True,
                    "Frontend is accessible"
                )
                return True
            else:
                self.log_test(
                    "Frontend Server Accessibility",
                    False,
                    f"Status: {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_test("Frontend Server Accessibility", False, error=e)
            return False

    def test_users_me_endpoint(self):
        """Test /api/v1/users/me endpoint"""
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/users/me",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "User Profile Endpoint",
                    True,
                    f"User: {data.get('name', 'N/A')}, Role: {data.get('role', 'N/A')}"
                )
                return data
            else:
                self.log_test(
                    "User Profile Endpoint",
                    False,
                    f"Status: {response.status_code}",
                    response.text
                )

        except Exception as e:
            self.log_test("User Profile Endpoint", False, error=e)

        return None

    def check_api_route_consistency(self):
        """Check for known API route mismatches"""
        issues = []

        # Known issue: frontend calls /api/v1/projects/my which doesn't exist
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/projects/my",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 422 or response.status_code == 404:
                issues.append({
                    "endpoint": "/api/v1/projects/my",
                    "issue": "Frontend calls this endpoint but it doesn't exist",
                    "fix": "Update apiService.js getMyProjects() to use /api/v1/projects/my/summary or /api/v1/projects/"
                })

        except Exception as e:
            pass

        if issues:
            self.log_test(
                "API Route Consistency Check",
                False,
                f"Found {len(issues)} route mismatches",
                json.dumps(issues, indent=2)
            )
            return issues
        else:
            self.log_test(
                "API Route Consistency Check",
                True,
                "All API routes are consistent"
            )
            return []

    def run_all_tests(self):
        """Run all coherence tests"""
        print("=" * 80)
        print("BACKEND-FRONTEND COHERENCE TEST SUITE")
        print("=" * 80)
        print()

        # Test 1: Frontend accessibility
        self.test_frontend_accessibility()

        # Test 2: Authentication
        if not self.test_authentication():
            print("\n❌ Authentication failed. Cannot proceed with API tests.")
            return self.generate_report()

        # Test 3: Dashboard endpoints
        self.test_semester_progress_endpoint()
        self.test_achievements_endpoint()
        self.test_daily_challenge_endpoint()
        self.test_sessions_endpoint()
        self.test_projects_endpoints()
        self.test_users_me_endpoint()

        # Test 4: Check for route mismatches
        route_issues = self.check_api_route_consistency()

        # Generate report
        return self.generate_report(route_issues)

    def generate_report(self, route_issues=None):
        """Generate final report"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        success_rate = (passed / total * 100) if total > 0 else 0

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {success_rate:.1f}%")

        if route_issues:
            print(f"\n⚠️  Route Mismatches Found: {len(route_issues)}")
            for issue in route_issues:
                print(f"  - {issue['endpoint']}: {issue['issue']}")
                print(f"    Fix: {issue['fix']}")

        # Save results to JSON
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": success_rate,
            "results": self.results,
            "route_issues": route_issues or []
        }

        filename = f"coherence_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n📄 Detailed results saved to: {filename}")

        return report_data

if __name__ == "__main__":
    runner = CoherenceTestRunner()
    report = runner.run_all_tests()
