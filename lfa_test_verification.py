#!/usr/bin/env python3
"""
🧪 LFA Test Environment Verification Script
Comprehensive testing for futballista accounts and cross-semester functionality
"""

import sys
import os
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional

# Add app to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class LFATestVerifier:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_users = {
            # Players 
            "messi": {"email": "messi@lfa.com", "type": "ACTIVE_PLAYER"},
            "ronaldo": {"email": "ronaldo@lfa.com", "type": "LEGEND_PLAYER"},
            "neymar": {"email": "neymar@lfa.com", "type": "CREATIVE_PLAYER"},
            "mbappe": {"email": "mbappe@lfa.com", "type": "CROSS_PLAYER"},  # Special cross-semester access
            
            # Instructors
            "guardiola": {"email": "guardiola@lfa.com", "type": "TACTICAL_INSTRUCTOR"},
            "ancelotti": {"email": "ancelotti@lfa.com", "type": "TECHNICAL_INSTRUCTOR"},
            "klopp": {"email": "klopp@lfa.com", "type": "FITNESS_INSTRUCTOR"},
            
            # Admins
            "maradona": {"email": "maradona@lfa.com", "type": "SYSTEM_ADMIN"},
            "pele": {"email": "pele@lfa.com", "type": "ANALYTICS_ADMIN"}
        }
        self.tokens = {}
        self.password = "FootballMaster2025!"
        
    def print_header(self, title: str):
        """Print formatted test section header"""
        print("\n" + "=" * 60)
        print(f"🧪 {title}")
        print("=" * 60)
    
    def print_test(self, description: str, result: bool, details: str = ""):
        """Print formatted test result"""
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {description}")
        if details:
            print(f"     {details}")
    
    def login_all_users(self) -> bool:
        """🔐 Test login for all futballista accounts"""
        self.print_header("Authentication Tests")
        
        success_count = 0
        total_users = len(self.test_users)
        
        for name, user_info in self.test_users.items():
            try:
                response = requests.post(f"{self.base_url}/api/v1/auth/login", json={
                    "email": user_info["email"],
                    "password": self.password
                })
                
                if response.status_code == 200:
                    data = response.json()
                    self.tokens[name] = data["access_token"]
                    success_count += 1
                    self.print_test(
                        f"{name.title()} Login",
                        True,
                        f"{user_info['type']} - Token received"
                    )
                else:
                    self.print_test(
                        f"{name.title()} Login",
                        False,
                        f"HTTP {response.status_code}: {response.text}"
                    )
                    
            except Exception as e:
                self.print_test(
                    f"{name.title()} Login",
                    False,
                    f"Connection error: {e}"
                )
        
        overall_success = success_count == total_users
        self.print_test(
            f"Overall Authentication",
            overall_success,
            f"{success_count}/{total_users} successful logins"
        )
        
        return overall_success
    
    def test_session_access(self) -> bool:
        """⚽ Test session access patterns for different users"""
        self.print_header("Session Access Tests")
        
        test_results = []
        
        for name, token in self.tokens.items():
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get(f"{self.base_url}/api/v1/sessions/", headers=headers)
                
                if response.status_code == 200:
                    sessions = response.json()
                    session_count = len(sessions)
                    
                    # Special validation for Mbappé (cross-semester access)
                    if name == "mbappe":
                        # Mbappé should see MORE sessions (cross-semester access)
                        expected_min = 5  # Should see sessions from multiple semesters
                        success = session_count >= expected_min
                        details = f"Cross-semester access: {session_count} sessions (min {expected_min})"
                        
                        # Test explicit cross-semester parameter
                        cross_response = requests.get(
                            f"{self.base_url}/api/v1/sessions/?cross_semester=true", 
                            headers=headers
                        )
                        if cross_response.status_code == 200:
                            cross_sessions = cross_response.json()
                            details += f", cross_param: {len(cross_sessions)} sessions"
                    else:
                        # Regular users should see limited sessions
                        success = session_count >= 0  # Basic functionality test
                        details = f"Regular access: {session_count} sessions"
                    
                    self.print_test(
                        f"{name.title()} Session Access",
                        success,
                        details
                    )
                    test_results.append(success)
                else:
                    self.print_test(
                        f"{name.title()} Session Access",
                        False,
                        f"HTTP {response.status_code}"
                    )
                    test_results.append(False)
                    
            except Exception as e:
                self.print_test(
                    f"{name.title()} Session Access",
                    False,
                    f"Error: {e}"
                )
                test_results.append(False)
        
        overall_success = all(test_results)
        self.print_test(
            "Overall Session Access",
            overall_success,
            f"{sum(test_results)}/{len(test_results)} users successful"
        )
        
        return overall_success
    
    def test_project_restrictions(self) -> bool:
        """📚 Test project enrollment restrictions (critical requirement)"""
        self.print_header("Project Enrollment Restriction Tests")
        
        # Get available projects
        try:
            response = requests.get(f"{self.base_url}/api/v1/projects/")
            if response.status_code != 200:
                self.print_test("Project List Fetch", False, f"HTTP {response.status_code}")
                return False
                
            projects = response.json()
            if not projects:
                self.print_test("Project Availability", False, "No projects found")
                return False
            
            # Find test projects
            live_project = None
            cross_project = None
            
            for project in projects:
                if "Barcelona" in project.get("title", "") or "Real Madrid" in project.get("title", ""):
                    live_project = project
                elif "Cross-Semester" in project.get("title", ""):
                    cross_project = project
            
            test_results = []
            
            # Test 1: Students should be able to enroll in their own semester projects
            if live_project:
                for player_name in ["messi", "ronaldo", "neymar", "mbappe"]:
                    if player_name in self.tokens:
                        success = self._test_project_enrollment(
                            player_name, 
                            live_project["id"], 
                            should_succeed=True,
                            test_name="Own Semester Project"
                        )
                        test_results.append(success)
            
            # Test 2: Students should NOT be able to enroll in cross-semester projects
            if cross_project:
                for player_name in ["messi", "ronaldo", "neymar", "mbappe"]:
                    if player_name in self.tokens:
                        success = self._test_project_enrollment(
                            player_name, 
                            cross_project["id"], 
                            should_succeed=False,
                            test_name="Cross-Semester Project (Should Fail)"
                        )
                        test_results.append(success)
            
            overall_success = all(test_results) if test_results else False
            self.print_test(
                "Overall Project Restrictions",
                overall_success,
                f"{sum(test_results)}/{len(test_results)} tests passed"
            )
            
            return overall_success
                        
        except Exception as e:
            self.print_test("Project Restriction Tests", False, f"Error: {e}")
            return False
    
    def _test_project_enrollment(self, player_name: str, project_id: int, should_succeed: bool, test_name: str) -> bool:
        """Helper method to test project enrollment"""
        try:
            headers = {"Authorization": f"Bearer {self.tokens[player_name]}"}
            response = requests.post(
                f"{self.base_url}/api/v1/projects/{project_id}/enroll",
                headers=headers
            )
            
            if should_succeed:
                # Should succeed (200) or already enrolled (409)
                success = response.status_code in [200, 201, 409]
                details = f"Expected success: HTTP {response.status_code}"
                if response.status_code == 409:
                    details += " (already enrolled)"
            else:
                # Should fail with 403 (forbidden)
                success = response.status_code == 403
                details = f"Expected 403 Forbidden: HTTP {response.status_code}"
                if response.status_code == 403:
                    # Check if it's specifically a cross-semester error
                    try:
                        error_detail = response.json().get("detail", "")
                        if "Cross-semester" in error_detail:
                            details += " (Cross-semester blocked ✓)"
                    except:
                        pass
            
            self.print_test(
                f"{player_name.title()} - {test_name}",
                success,
                details
            )
            
            return success
            
        except Exception as e:
            self.print_test(
                f"{player_name.title()} - {test_name}",
                False,
                f"Error: {e}"
            )
            return False
    
    def test_realistic_content(self) -> bool:
        """⚽ Test that realistic football content is present"""
        self.print_header("Realistic Football Content Tests")
        
        test_results = []
        
        # Test session content
        try:
            if "messi" in self.tokens:
                headers = {"Authorization": f"Bearer {self.tokens['messi']}"}
                response = requests.get(f"{self.base_url}/api/v1/sessions/", headers=headers)
                
                if response.status_code == 200:
                    sessions = response.json()
                    football_sessions = [
                        s for s in sessions 
                        if any(term in s.get("title", "").lower() for term in [
                            "taktikai", "labdabirtoklás", "kondicionálás", "mérkőzés", "guardiola", "ancelotti", "klopp"
                        ])
                    ]
                    
                    success = len(football_sessions) >= 3
                    self.print_test(
                        "Football Sessions Content",
                        success,
                        f"{len(football_sessions)} football-themed sessions found"
                    )
                    test_results.append(success)
                else:
                    test_results.append(False)
                    
        except Exception as e:
            self.print_test("Football Sessions Content", False, f"Error: {e}")
            test_results.append(False)
        
        # Test project content
        try:
            response = requests.get(f"{self.base_url}/api/v1/projects/")
            
            if response.status_code == 200:
                projects = response.json()
                football_projects = [
                    p for p in projects 
                    if any(term in p.get("title", "").lower() for term in [
                        "barcelona", "real madrid", "liverpool", "academy", "cantera"
                    ])
                ]
                
                success = len(football_projects) >= 3
                self.print_test(
                    "Football Projects Content",
                    success,
                    f"{len(football_projects)} football-themed projects found"
                )
                test_results.append(success)
            else:
                test_results.append(False)
                
        except Exception as e:
            self.print_test("Football Projects Content", False, f"Error: {e}")
            test_results.append(False)
        
        overall_success = all(test_results)
        return overall_success
    
    def run_comprehensive_test(self) -> bool:
        """🚀 Run all LFA tests and generate comprehensive report"""
        print("🧪 LFA Test Environment Comprehensive Verification")
        print(f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 API Base URL: {self.base_url}")
        print(f"👥 Testing {len(self.test_users)} futballista accounts")
        
        # Run all test suites
        auth_success = self.login_all_users()
        session_success = self.test_session_access() if auth_success else False
        project_success = self.test_project_restrictions() if auth_success else False
        content_success = self.test_realistic_content() if auth_success else False
        
        # Generate summary
        self.print_header("Test Summary")
        
        all_tests = [
            ("Authentication", auth_success),
            ("Session Access", session_success),
            ("Project Restrictions", project_success),
            ("Football Content", content_success)
        ]
        
        passed_tests = sum(1 for _, success in all_tests if success)
        total_tests = len(all_tests)
        
        for test_name, success in all_tests:
            self.print_test(test_name, success, "")
        
        overall_success = all(success for _, success in all_tests)
        
        print("\n" + "=" * 60)
        if overall_success:
            print("🎉 ALL TESTS PASSED - LFA Environment Ready for Live Testing!")
            print("✅ All 9 futballista accounts functional")
            print("🌐 Cross-semester access working for Mbappé")
            print("🚫 Project enrollment restrictions properly enforced")
            print("⚽ Realistic football content verified")
        else:
            print("⚠️  SOME TESTS FAILED - Review issues above")
            print(f"📊 Test Results: {passed_tests}/{total_tests} passed")
        
        print("=" * 60)
        
        return overall_success

if __name__ == "__main__":
    print("🚀 Starting LFA Test Environment Verification...")
    
    # Check if API is running
    try:
        requests.get("http://localhost:8000/docs", timeout=5)
        print("✅ API server is running")
    except:
        print("❌ API server not running. Start the backend first!")
        print("   Command: uvicorn app.main:app --reload")
        sys.exit(1)
    
    # Run comprehensive tests
    verifier = LFATestVerifier()
    success = verifier.run_comprehensive_test()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)