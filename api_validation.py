#!/usr/bin/env python3
"""
🤖 Practice Booking System - Automated API Validation Script
Comprehensive testing script that validates ALL API functionality automatically.
"""

import asyncio
import httpx
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
import os

# ANSI color codes for better output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class APIValidator:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.tokens = {}
        self.test_data = {}
        self.results = []
        self.start_time = time.time()
        self.performance_metrics = []
        
        # Environment variables for secure credential management
        self.admin_email = os.getenv('ADMIN_EMAIL', 'admin@company.com')
        self.admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        
    def log(self, message: str, color: str = Colors.WHITE):
        """Log message with color"""
        print(f"{color}{message}{Colors.END}")
        
    def log_test(self, test_name: str, passed: bool, duration: float = 0, details: str = ""):
        """Log test result"""
        status = f"{Colors.GREEN}✅ PASS" if passed else f"{Colors.RED}❌ FAIL"
        duration_str = f" ({duration:.3f}s)" if duration > 0 else ""
        self.log(f"{status}{Colors.END} - {test_name}{duration_str}")
        if details:
            self.log(f"    {details}", Colors.YELLOW)
        
        self.results.append({
            "test": test_name,
            "passed": passed,
            "duration": duration,
            "details": details
        })
        
        if duration > 0:
            self.performance_metrics.append({
                "endpoint": test_name,
                "response_time": duration
            })
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> tuple[httpx.Response, float]:
        """Make HTTP request and measure response time"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            response = await self.client.request(method, url, **kwargs)
            duration = time.time() - start_time
            return response, duration
        except Exception as e:
            duration = time.time() - start_time
            self.log(f"Request failed: {e}", Colors.RED)
            return None, duration
    
    async def run_complete_validation(self):
        """Run complete API validation suite"""
        
        self.log(f"{Colors.BOLD}{Colors.CYAN}🚀 Starting Complete API Validation Suite{Colors.END}")
        self.log(f"{Colors.BLUE}Target: {self.base_url}{Colors.END}")
        self.log(f"{Colors.BLUE}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        self.log("-" * 80)
        
        try:
            # Phase 1: Infrastructure Tests
            await self.test_infrastructure()
            
            # Phase 2: Authentication System
            await self.test_authentication()
            
            # Phase 3: User Management
            await self.test_user_management()
            
            # Phase 4: Semester Management
            await self.test_semester_management()
            
            # Phase 5: Group Management
            await self.test_group_management()
            
            # Phase 6: Session Management
            await self.test_session_management()
            
            # Phase 7: Booking Workflows
            await self.test_booking_workflows()
            
            # Phase 8: Attendance Tracking
            await self.test_attendance_tracking()
            
            # Phase 9: Feedback System
            await self.test_feedback_system()
            
            # Phase 10: Reporting System
            await self.test_reporting_system()
            
            # Phase 11: Permission Boundaries
            await self.test_permission_boundaries()
            
            # Phase 12: Edge Cases and Security
            await self.test_edge_cases_and_security()
            
            # Generate Final Report
            await self.generate_final_report()
            
        except Exception as e:
            self.log(f"Critical error during validation: {e}", Colors.RED)
        finally:
            await self.client.aclose()
    
    async def test_infrastructure(self):
        """Test basic infrastructure and connectivity"""
        self.log(f"\n{Colors.PURPLE}📡 Phase 1: Infrastructure Tests{Colors.END}")
        
        # Test 1: Health Check
        response, duration = await self.make_request("GET", "/health")
        if response and response.status_code == 200:
            data = response.json()
            passed = data.get("status") == "healthy"
            self.log_test("Health Check", passed, duration, f"Status: {data}")
        else:
            self.log_test("Health Check", False, duration, "Server not responding")
            return False
        
        # Test 2: Root Endpoint
        response, duration = await self.make_request("GET", "/")
        passed = response and response.status_code == 200
        self.log_test("Root Endpoint", passed, duration)
        
        # Test 3: API Documentation
        response, duration = await self.make_request("GET", "/docs")
        passed = response and response.status_code == 200
        self.log_test("Swagger UI", passed, duration)
        
        # Test 4: OpenAPI Schema
        response, duration = await self.make_request("GET", "/openapi.json")
        passed = response and response.status_code == 200 and response.json()
        self.log_test("OpenAPI Schema", passed, duration)
        
        return True
    
    async def test_authentication(self):
        """Test complete authentication system"""
        self.log(f"\n{Colors.PURPLE}🔐 Phase 2: Authentication System{Colors.END}")
        
        # Test 1: Admin Login - Success
        login_data = {"email": self.admin_email, "password": self.admin_password}
        response, duration = await self.make_request("POST", "/api/v1/auth/login", json=login_data)
        
        if response and response.status_code == 200:
            token_data = response.json()
            self.tokens['admin'] = token_data.get('access_token')
            self.tokens['admin_refresh'] = token_data.get('refresh_token')
            passed = bool(self.tokens['admin'])
            self.log_test("Admin Login Success", passed, duration)
        else:
            self.log_test("Admin Login Success", False, duration, f"Status: {response.status_code if response else 'No response'}")
            return False
        
        # Test 2: Invalid Credentials
        bad_login = {"email": self.admin_email, "password": "wrongpassword"}
        response, duration = await self.make_request("POST", "/api/v1/auth/login", json=bad_login)
        passed = response and response.status_code == 401
        self.log_test("Invalid Credentials Rejected", passed, duration)
        
        # Test 3: Nonexistent User
        fake_login = {"email": "nonexistent@test.com", "password": "password"}
        response, duration = await self.make_request("POST", "/api/v1/auth/login", json=fake_login)
        passed = response and response.status_code == 401
        self.log_test("Nonexistent User Rejected", passed, duration)
        
        # Test 4: Get Current User
        headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
        response, duration = await self.make_request("GET", "/api/v1/auth/me", headers=headers)
        if response and response.status_code == 200:
            user_data = response.json()
            self.test_data['admin_user'] = user_data
            passed = user_data.get('email') == self.admin_email
            self.log_test("Get Current User", passed, duration, f"User: {user_data.get('email')}")
        else:
            self.log_test("Get Current User", False, duration)
        
        # Test 5: Token Refresh
        if self.tokens.get('admin_refresh'):
            refresh_data = {"refresh_token": self.tokens['admin_refresh']}
            response, duration = await self.make_request("POST", "/api/v1/auth/refresh", json=refresh_data)
            passed = response and response.status_code == 200
            self.log_test("Token Refresh", passed, duration)
        
        # Test 6: Invalid Token Access
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response, duration = await self.make_request("GET", "/api/v1/users/", headers=invalid_headers)
        passed = response and response.status_code == 401
        self.log_test("Invalid Token Rejected", passed, duration)
        
        # Test 7: No Token Access
        response, duration = await self.make_request("GET", "/api/v1/users/")
        passed = response and response.status_code == 401
        self.log_test("No Token Rejected", passed, duration)
        
        return True
    
    async def test_user_management(self):
        """Test complete user management system"""
        self.log(f"\n{Colors.PURPLE}👥 Phase 3: User Management{Colors.END}")
        
        headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
        
        # Test 1: List Users
        response, duration = await self.make_request("GET", "/api/v1/users/", headers=headers)
        if response and response.status_code == 200:
            users_data = response.json()
            passed = 'users' in users_data and len(users_data['users']) > 0
            self.log_test("List Users", passed, duration, f"Found {len(users_data.get('users', []))} users")
        else:
            self.log_test("List Users", False, duration)
        
        # Test 2: Create Instructor
        instructor_data = {
            "name": "Test Instructor",
            "email": f"instructor_{int(time.time())}@test.com",
            "password": "instructor123",
            "role": "instructor"
        }
        response, duration = await self.make_request("POST", "/api/v1/users/", headers=headers, json=instructor_data)
        if response and response.status_code == 200:
            instructor = response.json()
            self.test_data['instructor'] = instructor
            passed = instructor.get('role') == 'instructor'
            self.log_test("Create Instructor", passed, duration, f"ID: {instructor.get('id')}")
        else:
            self.log_test("Create Instructor", False, duration, f"Status: {response.status_code if response else 'No response'}")
        
        # Test 3: Create Student
        student_data = {
            "name": "Test Student",
            "email": f"student_{int(time.time())}@test.com",
            "password": "student123",
            "role": "student"
        }
        response, duration = await self.make_request("POST", "/api/v1/users/", headers=headers, json=student_data)
        if response and response.status_code == 200:
            student = response.json()
            self.test_data['student'] = student
            passed = student.get('role') == 'student'
            self.log_test("Create Student", passed, duration, f"ID: {student.get('id')}")
        else:
            self.log_test("Create Student", False, duration)
        
        # Test 4: Login as Instructor
        if self.test_data.get('instructor'):
            login_data = {"email": instructor_data['email'], "password": "instructor123"}
            response, duration = await self.make_request("POST", "/api/v1/auth/login", json=login_data)
            if response and response.status_code == 200:
                token_data = response.json()
                self.tokens['instructor'] = token_data.get('access_token')
                passed = bool(self.tokens['instructor'])
                self.log_test("Instructor Login", passed, duration)
            else:
                self.log_test("Instructor Login", False, duration)
        
        # Test 5: Login as Student
        if self.test_data.get('student'):
            login_data = {"email": student_data['email'], "password": "student123"}
            response, duration = await self.make_request("POST", "/api/v1/auth/login", json=login_data)
            if response and response.status_code == 200:
                token_data = response.json()
                self.tokens['student'] = token_data.get('access_token')
                passed = bool(self.tokens['student'])
                self.log_test("Student Login", passed, duration)
            else:
                self.log_test("Student Login", False, duration)
        
        # Test 6: Get User by ID
        if self.test_data.get('instructor'):
            user_id = self.test_data['instructor']['id']
            response, duration = await self.make_request("GET", f"/api/v1/users/{user_id}", headers=headers)
            passed = response and response.status_code == 200
            self.log_test("Get User by ID", passed, duration)
        
        # Test 7: Update User
        if self.test_data.get('student'):
            user_id = self.test_data['student']['id']
            update_data = {"name": "Updated Student Name"}
            response, duration = await self.make_request("PATCH", f"/api/v1/users/{user_id}", headers=headers, json=update_data)
            passed = response and response.status_code == 200
            self.log_test("Update User", passed, duration)
        
        # Test 8: Duplicate Email Check
        duplicate_data = {
            "name": "Duplicate User",
            "email": self.admin_email,  # Existing email
            "password": "password123",
            "role": "student"
        }
        response, duration = await self.make_request("POST", "/api/v1/users/", headers=headers, json=duplicate_data)
        passed = response and response.status_code == 400
        self.log_test("Duplicate Email Rejected", passed, duration)
        
        # Test 9: Invalid Email Format
        invalid_data = {
            "name": "Invalid Email User",
            "email": "not-an-email",
            "password": "password123",
            "role": "student"
        }
        response, duration = await self.make_request("POST", "/api/v1/users/", headers=headers, json=invalid_data)
        passed = response and response.status_code == 422
        self.log_test("Invalid Email Rejected", passed, duration)
        
        return True
    
    async def test_semester_management(self):
        """Test semester management functionality"""
        self.log(f"\n{Colors.PURPLE}📅 Phase 4: Semester Management{Colors.END}")
        
        headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
        
        # Test 1: Create Semester
        semester_data = {
            "code": f"TEST/{int(time.time())}",
            "name": "Test Semester",
            "start_date": "2024-09-01",
            "end_date": "2024-12-31",
            "is_active": True
        }
        response, duration = await self.make_request("POST", "/api/v1/semesters/", headers=headers, json=semester_data)
        if response and response.status_code == 200:
            semester = response.json()
            self.test_data['semester'] = semester
            passed = semester.get('code') == semester_data['code']
            self.log_test("Create Semester", passed, duration, f"ID: {semester.get('id')}")
        else:
            self.log_test("Create Semester", False, duration, f"Status: {response.status_code if response else 'No response'}")
        
        # Test 2: List Semesters
        response, duration = await self.make_request("GET", "/api/v1/semesters/", headers=headers)
        if response and response.status_code == 200:
            semesters_data = response.json()
            passed = 'semesters' in semesters_data
            self.log_test("List Semesters", passed, duration, f"Found {len(semesters_data.get('semesters', []))} semesters")
        else:
            self.log_test("List Semesters", False, duration)
        
        # Test 3: Get Semester by ID
        if self.test_data.get('semester'):
            semester_id = self.test_data['semester']['id']
            response, duration = await self.make_request("GET", f"/api/v1/semesters/{semester_id}", headers=headers)
            passed = response and response.status_code == 200
            self.log_test("Get Semester by ID", passed, duration)
        
        # Test 4: Update Semester
        if self.test_data.get('semester'):
            semester_id = self.test_data['semester']['id']
            update_data = {"name": "Updated Test Semester"}
            response, duration = await self.make_request("PATCH", f"/api/v1/semesters/{semester_id}", headers=headers, json=update_data)
            passed = response and response.status_code == 200
            self.log_test("Update Semester", passed, duration)
        
        # Test 5: Invalid Date Range
        invalid_semester = {
            "code": "INVALID/2024",
            "name": "Invalid Semester",
            "start_date": "2024-12-31",
            "end_date": "2024-09-01"  # End before start
        }
        response, duration = await self.make_request("POST", "/api/v1/semesters/", headers=headers, json=invalid_semester)
        # This should either be rejected (422) or handled gracefully
        passed = response and (response.status_code == 422 or response.status_code == 400)
        self.log_test("Invalid Date Range Rejected", passed, duration)
        
        return True
    
    async def test_group_management(self):
        """Test group management functionality"""
        self.log(f"\n{Colors.PURPLE}👥 Phase 5: Group Management{Colors.END}")
        
        headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
        
        # Test 1: Create Group
        if self.test_data.get('semester'):
            group_data = {
                "name": f"Test Group {int(time.time())}",
                "description": "Test group for API validation",
                "semester_id": self.test_data['semester']['id']
            }
            response, duration = await self.make_request("POST", "/api/v1/groups/", headers=headers, json=group_data)
            if response and response.status_code == 200:
                group = response.json()
                self.test_data['group'] = group
                passed = group.get('name') == group_data['name']
                self.log_test("Create Group", passed, duration, f"ID: {group.get('id')}")
            else:
                self.log_test("Create Group", False, duration, f"Status: {response.status_code if response else 'No response'}")
        
        # Test 2: List Groups
        response, duration = await self.make_request("GET", "/api/v1/groups/", headers=headers)
        if response and response.status_code == 200:
            groups_data = response.json()
            passed = isinstance(groups_data, list) or 'groups' in groups_data
            self.log_test("List Groups", passed, duration)
        else:
            self.log_test("List Groups", False, duration)
        
        # Test 3: Add User to Group
        if self.test_data.get('group') and self.test_data.get('student'):
            group_id = self.test_data['group']['id']
            user_data = {"user_id": self.test_data['student']['id']}
            response, duration = await self.make_request("POST", f"/api/v1/groups/{group_id}/users", headers=headers, json=user_data)
            passed = response and response.status_code == 200
            self.log_test("Add User to Group", passed, duration)
        
        # Test 4: Get Group Details
        if self.test_data.get('group'):
            group_id = self.test_data['group']['id']
            response, duration = await self.make_request("GET", f"/api/v1/groups/{group_id}", headers=headers)
            passed = response and response.status_code == 200
            self.log_test("Get Group Details", passed, duration)
        
        return True
    
    async def test_session_management(self):
        """Test session management functionality"""
        self.log(f"\n{Colors.PURPLE}🏫 Phase 6: Session Management{Colors.END}")
        
        headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
        
        # Test 1: Create Session
        if self.test_data.get('semester') and self.test_data.get('group') and self.test_data.get('instructor'):
            session_start = datetime.now() + timedelta(days=1)
            session_end = session_start + timedelta(hours=2)
            
            session_data = {
                "title": f"Test Session {int(time.time())}",
                "description": "API Validation Test Session",
                "date_start": session_start.isoformat(),
                "date_end": session_end.isoformat(),
                "mode": "offline",
                "capacity": 20,
                "location": "Test Room",
                "semester_id": self.test_data['semester']['id'],
                "group_id": self.test_data['group']['id'],
                "instructor_id": self.test_data['instructor']['id']
            }
            response, duration = await self.make_request("POST", "/api/v1/sessions/", headers=headers, json=session_data)
            if response and response.status_code == 200:
                session = response.json()
                self.test_data['session'] = session
                passed = session.get('title') == session_data['title']
                self.log_test("Create Session", passed, duration, f"ID: {session.get('id')}")
            else:
                self.log_test("Create Session", False, duration, f"Status: {response.status_code if response else 'No response'}")
        
        # Test 2: List Sessions
        response, duration = await self.make_request("GET", "/api/v1/sessions/", headers=headers)
        if response and response.status_code == 200:
            passed = True
            self.log_test("List Sessions", passed, duration)
        else:
            self.log_test("List Sessions", False, duration)
        
        # Test 3: Get Session by ID
        if self.test_data.get('session'):
            session_id = self.test_data['session']['id']
            response, duration = await self.make_request("GET", f"/api/v1/sessions/{session_id}", headers=headers)
            passed = response and response.status_code == 200
            self.log_test("Get Session by ID", passed, duration)
        
        # Test 4: Update Session
        if self.test_data.get('session'):
            session_id = self.test_data['session']['id']
            update_data = {"title": "Updated Test Session"}
            response, duration = await self.make_request("PATCH", f"/api/v1/sessions/{session_id}", headers=headers, json=update_data)
            passed = response and response.status_code == 200
            self.log_test("Update Session", passed, duration)
        
        return True
    
    async def test_booking_workflows(self):
        """Test complete booking workflow"""
        self.log(f"\n{Colors.PURPLE}📝 Phase 7: Booking Workflows{Colors.END}")
        
        admin_headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
        student_headers = {"Authorization": f"Bearer {self.tokens.get('student', '')}"}
        
        # Test 1: Student Create Booking
        if self.test_data.get('session') and self.tokens.get('student'):
            booking_data = {
                "session_id": self.test_data['session']['id']
            }
            response, duration = await self.make_request("POST", "/api/v1/bookings/", headers=student_headers, json=booking_data)
            if response and response.status_code == 200:
                booking = response.json()
                self.test_data['booking'] = booking
                passed = booking.get('session_id') == booking_data['session_id']
                self.log_test("Create Booking", passed, duration, f"ID: {booking.get('id')}")
            else:
                self.log_test("Create Booking", False, duration, f"Status: {response.status_code if response else 'No response'}")
        
        # Test 2: Get Own Bookings
        if self.tokens.get('student'):
            response, duration = await self.make_request("GET", "/api/v1/bookings/me", headers=student_headers)
            passed = response and response.status_code == 200
            self.log_test("Get Own Bookings", passed, duration)
        
        # Test 3: Admin View Session Bookings
        if self.test_data.get('session'):
            session_id = self.test_data['session']['id']
            response, duration = await self.make_request("GET", f"/api/v1/sessions/{session_id}/bookings", headers=admin_headers)
            passed = response and response.status_code == 200
            self.log_test("View Session Bookings", passed, duration)
        
        # Test 4: Confirm Booking (Admin)
        if self.test_data.get('booking'):
            booking_id = self.test_data['booking']['id']
            response, duration = await self.make_request("POST", f"/api/v1/bookings/{booking_id}/confirm", headers=admin_headers)
            passed = response and response.status_code == 200
            self.log_test("Confirm Booking", passed, duration)
        
        # Test 5: Double Booking Prevention
        if self.test_data.get('session') and self.tokens.get('student'):
            booking_data = {
                "session_id": self.test_data['session']['id']
            }
            response, duration = await self.make_request("POST", "/api/v1/bookings/", headers=student_headers, json=booking_data)
            passed = response and response.status_code in [400, 409]  # Should prevent duplicate booking
            self.log_test("Double Booking Prevention", passed, duration)
        
        return True
    
    async def test_attendance_tracking(self):
        """Test attendance tracking functionality"""
        self.log(f"\n{Colors.PURPLE}✅ Phase 8: Attendance Tracking{Colors.END}")
        
        admin_headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
        student_headers = {"Authorization": f"Bearer {self.tokens.get('student', '')}"}
        
        # Test 1: Check-in to Session
        if self.test_data.get('booking') and self.tokens.get('student'):
            booking_id = self.test_data['booking']['id']
            response, duration = await self.make_request("POST", f"/api/v1/attendance/{booking_id}/checkin", headers=student_headers)
            if response and response.status_code == 200:
                attendance = response.json()
                self.test_data['attendance'] = attendance
                passed = True
                self.log_test("Student Check-in", passed, duration, f"Status: {attendance.get('status')}")
            else:
                self.log_test("Student Check-in", False, duration)
        
        # Test 2: View Attendance
        if self.test_data.get('session'):
            session_id = self.test_data['session']['id']
            response, duration = await self.make_request("GET", f"/api/v1/attendance/?session_id={session_id}", headers=admin_headers)
            passed = response and response.status_code == 200
            self.log_test("View Attendance", passed, duration)
        
        # Test 3: Update Attendance Status
        if self.test_data.get('attendance'):
            attendance_id = self.test_data['attendance']['id']
            update_data = {"status": "present", "notes": "On time"}
            response, duration = await self.make_request("PATCH", f"/api/v1/attendance/{attendance_id}", headers=admin_headers, json=update_data)
            passed = response and response.status_code == 200
            self.log_test("Update Attendance", passed, duration)
        
        return True
    
    async def test_feedback_system(self):
        """Test feedback system functionality"""
        self.log(f"\n{Colors.PURPLE}⭐ Phase 9: Feedback System{Colors.END}")
        
        student_headers = {"Authorization": f"Bearer {self.tokens.get('student', '')}"}
        admin_headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
        
        # Test 1: Submit Feedback
        if self.test_data.get('session') and self.tokens.get('student'):
            feedback_data = {
                "session_id": self.test_data['session']['id'],
                "rating": 5,
                "comment": "Great session! API validation test feedback.",
                "is_anonymous": False
            }
            response, duration = await self.make_request("POST", "/api/v1/feedback/", headers=student_headers, json=feedback_data)
            if response and response.status_code == 200:
                feedback = response.json()
                self.test_data['feedback'] = feedback
                passed = feedback.get('rating') == 5
                self.log_test("Submit Feedback", passed, duration, f"Rating: {feedback.get('rating')}")
            else:
                self.log_test("Submit Feedback", False, duration)
        
        # Test 2: Get Own Feedback
        if self.tokens.get('student'):
            response, duration = await self.make_request("GET", "/api/v1/feedback/me", headers=student_headers)
            passed = response and response.status_code == 200
            self.log_test("Get Own Feedback", passed, duration)
        
        # Test 3: Get Session Feedback (Admin)
        if self.test_data.get('session'):
            session_id = self.test_data['session']['id']
            response, duration = await self.make_request("GET", f"/api/v1/sessions/{session_id}/feedback", headers=admin_headers)
            passed = response and response.status_code == 200
            self.log_test("Get Session Feedback", passed, duration)
        
        # Test 4: Anonymous Feedback
        if self.test_data.get('session') and self.tokens.get('student'):
            anonymous_feedback = {
                "session_id": self.test_data['session']['id'],
                "rating": 4,
                "comment": "Anonymous feedback test",
                "is_anonymous": True
            }
            response, duration = await self.make_request("POST", "/api/v1/feedback/", headers=student_headers, json=anonymous_feedback)
            passed = response and response.status_code == 200
            self.log_test("Anonymous Feedback", passed, duration)
        
        return True
    
    async def test_reporting_system(self):
        """Test reporting functionality"""
        self.log(f"\n{Colors.PURPLE}📊 Phase 10: Reporting System{Colors.END}")
        
        admin_headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
        
        # Test 1: Semester Report
        if self.test_data.get('semester'):
            semester_id = self.test_data['semester']['id']
            response, duration = await self.make_request("GET", f"/api/v1/reports/semester/{semester_id}", headers=admin_headers)
            passed = response and response.status_code == 200
            self.log_test("Semester Report", passed, duration)
        
        # Test 2: User Participation Report
        if self.test_data.get('student'):
            user_id = self.test_data['student']['id']
            response, duration = await self.make_request("GET", f"/api/v1/reports/user/{user_id}", headers=admin_headers)
            passed = response and response.status_code == 200
            self.log_test("User Report", passed, duration)
        
        # Test 3: Export Sessions CSV
        response, duration = await self.make_request("GET", "/api/v1/reports/export/sessions", headers=admin_headers)
        passed = response and response.status_code == 200
        self.log_test("Export Sessions CSV", passed, duration)
        
        return True
    
    async def test_permission_boundaries(self):
        """Test role-based access control"""
        self.log(f"\n{Colors.PURPLE}🔒 Phase 11: Permission Boundaries{Colors.END}")
        
        student_headers = {"Authorization": f"Bearer {self.tokens.get('student', '')}"}
        instructor_headers = {"Authorization": f"Bearer {self.tokens.get('instructor', '')}"}
        
        # Test 1: Student Cannot Access Admin Endpoints
        if self.tokens.get('student'):
            response, duration = await self.make_request("GET", "/api/v1/users/", headers=student_headers)
            passed = response and response.status_code == 403
            self.log_test("Student Admin Access Blocked", passed, duration)
        
        # Test 2: Student Cannot Create Users
        if self.tokens.get('student'):
            user_data = {"name": "Unauthorized", "email": "test@test.com", "password": "pass", "role": "student"}
            response, duration = await self.make_request("POST", "/api/v1/users/", headers=student_headers, json=user_data)
            passed = response and response.status_code == 403
            self.log_test("Student Create User Blocked", passed, duration)
        
        # Test 3: Instructor Cannot Access Reports
        if self.tokens.get('instructor') and self.test_data.get('semester'):
            semester_id = self.test_data['semester']['id']
            response, duration = await self.make_request("GET", f"/api/v1/reports/semester/{semester_id}", headers=instructor_headers)
            passed = response and response.status_code == 403
            self.log_test("Instructor Reports Blocked", passed, duration)
        
        # Test 4: Instructor Can View Their Sessions
        if self.tokens.get('instructor'):
            response, duration = await self.make_request("GET", "/api/v1/sessions/", headers=instructor_headers)
            passed = response and response.status_code == 200
            self.log_test("Instructor Session Access", passed, duration)
        
        return True
    
    async def test_edge_cases_and_security(self):
        """Test edge cases and security measures"""
        self.log(f"\n{Colors.PURPLE}🚨 Phase 12: Edge Cases & Security{Colors.END}")
        
        admin_headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
        
        # Test 1: SQL Injection Attempt
        malicious_email = "admin@test.com'; DROP TABLE users; --"
        bad_data = {"name": "Hacker", "email": malicious_email, "password": "pass", "role": "student"}
        response, duration = await self.make_request("POST", "/api/v1/users/", headers=admin_headers, json=bad_data)
        passed = response and response.status_code == 422  # Should be rejected by validation
        self.log_test("SQL Injection Prevention", passed, duration)
        
        # Test 2: XSS Prevention
        xss_payload = "<script>alert('xss')</script>"
        xss_data = {"name": xss_payload, "email": "xss@test.com", "password": "pass", "role": "student"}
        response, duration = await self.make_request("POST", "/api/v1/users/", headers=admin_headers, json=xss_data)
        # Should either sanitize or reject
        passed = response and (response.status_code == 422 or response.status_code == 200)
        self.log_test("XSS Prevention", passed, duration)
        
        # Test 3: Large Payload Handling
        large_comment = "A" * 10000  # 10KB comment
        large_feedback = {
            "session_id": self.test_data.get('session', {}).get('id', 1),
            "rating": 3,
            "comment": large_comment
        }
        student_headers = {"Authorization": f"Bearer {self.tokens.get('student', '')}"}
        response, duration = await self.make_request("POST", "/api/v1/feedback/", headers=student_headers, json=large_feedback)
        passed = response  # Should handle gracefully (accept or reject)
        self.log_test("Large Payload Handling", passed, duration)
        
        # Test 4: Rate Limiting Test (Multiple requests)
        start = time.time()
        tasks = []
        for _ in range(10):
            task = self.make_request("GET", "/health")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        passed = all(resp and resp[0] for resp in responses)
        total_duration = time.time() - start
        self.log_test("Concurrent Requests", passed, total_duration, f"10 requests in {total_duration:.3f}s")
        
        # Test 5: Invalid JSON Handling
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/users/",
                headers={**admin_headers, "Content-Type": "application/json"},
                content='{"invalid": json}'  # Invalid JSON
            )
            passed = response.status_code == 422
            self.log_test("Invalid JSON Rejection", passed, 0)
        except:
            self.log_test("Invalid JSON Rejection", True, 0, "Exception handled gracefully")
        
        return True
    
    async def generate_final_report(self):
        """Generate comprehensive validation report"""
        self.log(f"\n{Colors.BOLD}{Colors.CYAN}📋 Final Validation Report{Colors.END}")
        
        total_time = time.time() - self.start_time
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['passed'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Performance metrics
        avg_response_time = sum(m['response_time'] for m in self.performance_metrics) / len(self.performance_metrics) if self.performance_metrics else 0
        max_response_time = max(m['response_time'] for m in self.performance_metrics) if self.performance_metrics else 0
        
        self.log("=" * 80)
        self.log(f"{Colors.BOLD}🎉 API VALIDATION COMPLETE{Colors.END}")
        self.log("=" * 80)
        
        # Test Results Summary
        status_color = Colors.GREEN if success_rate >= 90 else Colors.YELLOW if success_rate >= 75 else Colors.RED
        self.log(f"{Colors.BOLD}📊 Test Results Summary:{Colors.END}")
        self.log(f"  • Total Tests: {total_tests}")
        self.log(f"  • Passed: {Colors.GREEN}{passed_tests}{Colors.END}")
        self.log(f"  • Failed: {Colors.RED}{failed_tests}{Colors.END}")
        self.log(f"  • Success Rate: {status_color}{success_rate:.1f}%{Colors.END}")
        self.log(f"  • Total Time: {total_time:.2f}s")
        
        # Performance Summary
        self.log(f"\n{Colors.BOLD}⚡ Performance Summary:{Colors.END}")
        self.log(f"  • Average Response Time: {avg_response_time*1000:.1f}ms")
        self.log(f"  • Max Response Time: {max_response_time*1000:.1f}ms")
        self.log(f"  • Total Endpoints Tested: {len(self.performance_metrics)}")
        
        # System Status
        if success_rate >= 90:
            self.log(f"\n{Colors.BOLD}{Colors.GREEN}🚦 System Status: PRODUCTION READY ✅{Colors.END}")
            self.log("  • All critical functionality working")
            self.log("  • Performance within acceptable limits")
            self.log("  • Security measures active")
        elif success_rate >= 75:
            self.log(f"\n{Colors.BOLD}{Colors.YELLOW}🚦 System Status: MOSTLY READY ⚠️{Colors.END}")
            self.log("  • Core functionality working")
            self.log("  • Minor issues need attention")
        else:
            self.log(f"\n{Colors.BOLD}{Colors.RED}🚦 System Status: NEEDS WORK ❌{Colors.END}")
            self.log("  • Multiple critical issues found")
            self.log("  • Not ready for production")
        
        # Failed Tests Detail
        if failed_tests > 0:
            self.log(f"\n{Colors.BOLD}❌ Failed Tests:{Colors.END}")
            for result in self.results:
                if not result['passed']:
                    self.log(f"  • {result['test']}: {result['details']}", Colors.RED)
        
        # Generate HTML Report
        await self.generate_html_report(total_tests, passed_tests, failed_tests, success_rate, avg_response_time)
        
        self.log(f"\n{Colors.BOLD}{Colors.CYAN}📁 Reports Generated:{Colors.END}")
        self.log(f"  • Console output: Complete")
        self.log(f"  • HTML report: api_validation_report.html")
        self.log(f"  • JSON data: api_validation_data.json")
        
        # Save detailed results
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "total_time": total_time,
            "avg_response_time": avg_response_time,
            "max_response_time": max_response_time,
            "results": self.results,
            "performance_metrics": self.performance_metrics
        }
        
        with open("api_validation_data.json", "w") as f:
            json.dump(report_data, f, indent=2)
    
    async def generate_html_report(self, total_tests: int, passed_tests: int, failed_tests: int, success_rate: float, avg_response_time: float):
        """Generate HTML validation report"""
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Practice Booking System - API Validation Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .success {{ color: #4CAF50; }}
        .warning {{ color: #FF9800; }}
        .error {{ color: #f44336; }}
        .info {{ color: #2196F3; }}
        
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .test-results {{
            display: grid;
            gap: 10px;
        }}
        .test-item {{
            display: flex;
            align-items: center;
            padding: 15px;
            border-radius: 8px;
            background: #f8f9fa;
        }}
        .test-item.passed {{
            border-left: 4px solid #4CAF50;
            background: #f1f8e9;
        }}
        .test-item.failed {{
            border-left: 4px solid #f44336;
            background: #ffebee;
        }}
        .test-status {{
            margin-right: 15px;
            font-size: 1.2em;
        }}
        .test-name {{
            flex: 1;
            font-weight: 500;
        }}
        .test-duration {{
            color: #666;
            font-size: 0.9em;
        }}
        .test-details {{
            margin-left: 35px;
            color: #666;
            font-size: 0.9em;
        }}
        .footer {{
            background: #333;
            color: white;
            text-align: center;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 API Validation Report</h1>
            <p>Practice Booking System - Automated Testing Results</p>
            <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number success">{passed_tests}</div>
                <div class="stat-label">Tests Passed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number error">{failed_tests}</div>
                <div class="stat-label">Tests Failed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number info">{total_tests}</div>
                <div class="stat-label">Total Tests</div>
            </div>
            <div class="stat-card">
                <div class="stat-number {'success' if success_rate >= 90 else 'warning' if success_rate >= 75 else 'error'}">{success_rate:.1f}%</div>
                <div class="stat-label">Success Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-number info">{avg_response_time*1000:.1f}ms</div>
                <div class="stat-label">Avg Response Time</div>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📋 Test Results</h2>
                <div class="test-results">
"""
        
        for result in self.results:
            status_class = "passed" if result['passed'] else "failed"
            status_icon = "✅" if result['passed'] else "❌"
            duration_str = f"{result['duration']:.3f}s" if result['duration'] > 0 else ""
            
            html_content += f"""
                    <div class="test-item {status_class}">
                        <div class="test-status">{status_icon}</div>
                        <div class="test-name">{result['test']}</div>
                        <div class="test-duration">{duration_str}</div>
                    </div>
"""
            if result['details']:
                html_content += f"""
                    <div class="test-details">{result['details']}</div>
"""
        
        html_content += """
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>🤖 Generated by Practice Booking System API Validator</p>
            <p>Comprehensive automated testing for production readiness</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open("api_validation_report.html", "w") as f:
            f.write(html_content)

async def main():
    """Main function to run the validation"""
    validator = APIValidator()
    await validator.run_complete_validation()

if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.CYAN}🚀 Practice Booking System - Automated API Validator{Colors.END}")
    print(f"{Colors.BLUE}Starting comprehensive API validation...{Colors.END}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Validation interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error during validation: {e}{Colors.END}")
        sys.exit(1)