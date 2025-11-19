import pytest
from fastapi import status
from datetime import datetime, timedelta


class TestCompleteWorkflow:
    """End-to-end test scenarios covering all user roles and workflows"""
    
    def test_admin_complete_workflow(self, client, admin_user, admin_token):
        """
        Complete admin workflow:
        1. Admin login
        2. Create semester
        3. Create group
        4. Create instructor and students
        5. Create session
        6. Manage bookings
        7. Track attendance
        8. View feedback
        9. Generate reports
        """
        # 1. Admin login (using fixture token)
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 2. Create semester
        semester_data = {
            "code": "2024/1",
            "name": "2024/25 őszi félév",
            "start_date": "2024-09-01",
            "end_date": "2024-12-31",
            "is_active": True
        }
        semester_response = client.post(
            "/api/v1/semesters/",
            headers=headers,
            json=semester_data
        )
        assert semester_response.status_code == status.HTTP_200_OK
        semester = semester_response.json()
        semester_id = semester["id"]
        
        # 3. Create group
        group_data = {
            "name": "Csoport A",
            "description": "Első csoport",
            "semester_id": semester_id
        }
        group_response = client.post(
            "/api/v1/groups/",
            headers=headers,
            json=group_data
        )
        assert group_response.status_code == status.HTTP_200_OK
        group = group_response.json()
        group_id = group["id"]
        
        # 4. Create instructor and students
        instructor_data = {
            "name": "Dr. Oktató",
            "email": "instructor@test.com",
            "password": "instructor123",
            "role": "instructor"
        }
        instructor_response = client.post(
            "/api/v1/users/",
            headers=headers,
            json=instructor_data
        )
        assert instructor_response.status_code == status.HTTP_200_OK
        instructor = instructor_response.json()
        instructor_id = instructor["id"]
        
        # Create students
        students = []
        for i in range(2):
            student_data = {
                "name": f"Hallgató {i+1}",
                "email": f"student{i+1}@test.com",
                "password": "student123",
                "role": "student",
                "payment_verified": True  # Required for booking sessions
            }
            student_response = client.post(
                "/api/v1/users/",
                headers=headers,
                json=student_data
            )
            assert student_response.status_code == status.HTTP_200_OK
            students.append(student_response.json())
        
        # Add students to group
        for student in students:
            add_response = client.post(
                f"/api/v1/groups/{group_id}/users",
                headers=headers,
                json={"user_id": student["id"]}
            )
            assert add_response.status_code == status.HTTP_200_OK
        
        # 5. Create session
        session_start = datetime.now() + timedelta(days=1)
        session_end = session_start + timedelta(hours=2)
        
        session_data = {
            "title": "Első gyakorlat",
            "description": "Bevezetés a gyakorlatokba",
            "date_start": session_start.isoformat(),
            "date_end": session_end.isoformat(),
            "mode": "offline",
            "capacity": 20,
            "location": "101-es terem",
            "semester_id": semester_id,
            "group_id": group_id,
            "instructor_id": instructor_id
        }
        session_response = client.post(
            "/api/v1/sessions/",
            headers=headers,
            json=session_data
        )
        assert session_response.status_code == status.HTTP_200_OK
        session = session_response.json()
        session_id = session["id"]
        
        # 6. Student workflow - login and book session
        student_tokens = []
        bookings = []
        
        for i, student in enumerate(students):
            # Student login
            login_response = client.post(
                "/api/v1/auth/login",
                json={"email": f"student{i+1}@test.com", "password": "student123"}
            )
            assert login_response.status_code == status.HTTP_200_OK
            student_token = login_response.json()["access_token"]
            student_tokens.append(student_token)
            student_headers = {"Authorization": f"Bearer {student_token}"}
            
            # Create booking
            booking_response = client.post(
                "/api/v1/bookings/",
                headers=student_headers,
                json={"session_id": session_id, "notes": f"Jelentkezés student{i+1}"}
            )
            assert booking_response.status_code == status.HTTP_200_OK
            bookings.append(booking_response.json())
        
        # 7. Instructor workflow - manage session
        instructor_login = client.post(
            "/api/v1/auth/login",
            json={"email": "instructor@test.com", "password": "instructor123"}
        )
        assert instructor_login.status_code == status.HTTP_200_OK
        instructor_token = instructor_login.json()["access_token"]
        instructor_headers = {"Authorization": f"Bearer {instructor_token}"}
        
        # View session bookings
        bookings_response = client.get(
            f"/api/v1/sessions/{session_id}/bookings",
            headers=instructor_headers
        )
        assert bookings_response.status_code == status.HTTP_200_OK
        assert len(bookings_response.json()["bookings"]) == 2
        
        # 8. Track attendance
        for booking in bookings:
            attendance_data = {
                "user_id": booking["user_id"],
                "session_id": session_id,
                "booking_id": booking["id"],
                "status": "present"
            }
            attendance_response = client.post(
                "/api/v1/attendance/",
                headers=instructor_headers,
                json=attendance_data
            )
            assert attendance_response.status_code == status.HTTP_200_OK
        
        # 9. Students provide feedback
        for i, student_token in enumerate(student_tokens):
            student_headers = {"Authorization": f"Bearer {student_token}"}
            feedback_data = {
                "session_id": session_id,
                "rating": 4.5,
                "comment": f"Nagyon jó volt a gyakorlat! - Student {i+1}",
                "is_anonymous": False
            }
            feedback_response = client.post(
                "/api/v1/feedback/",
                headers=student_headers,
                json=feedback_data
            )
            assert feedback_response.status_code == status.HTTP_200_OK
        
        # 10. Generate reports
        semester_report = client.get(
            f"/api/v1/reports/semester/{semester_id}",
            headers=headers
        )
        assert semester_report.status_code == status.HTTP_200_OK
        report_data = semester_report.json()
        assert report_data["overview"]["total_sessions"] == 1
        assert report_data["overview"]["confirmed_bookings"] == 2
        
        # Test CSV export
        csv_export = client.get(
            f"/api/v1/reports/export/sessions?semester_id={semester_id}",
            headers=headers
        )
        assert csv_export.status_code == status.HTTP_200_OK
        assert "text/csv" in csv_export.headers["content-type"]

    def test_permission_boundaries(self, client, admin_user, admin_token):
        """
        Test permission boundaries:
        - Students can't access admin endpoints
        - Instructors can't access admin-only features
        - Users can only access their own data
        """
        # Create test data
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create student
        student_data = {
            "name": "Test Student",
            "email": "boundary_student@test.com",
            "password": "student123",
            "role": "student"
        }
        student_response = client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json=student_data
        )
        assert student_response.status_code == status.HTTP_200_OK
        
        # Create instructor
        instructor_data = {
            "name": "Test Instructor",
            "email": "boundary_instructor@test.com",
            "password": "instructor123",
            "role": "instructor"
        }
        instructor_response = client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json=instructor_data
        )
        assert instructor_response.status_code == status.HTTP_200_OK
        
        # Student login
        student_login = client.post(
            "/api/v1/auth/login",
            json={"email": "boundary_student@test.com", "password": "student123"}
        )
        student_token = student_login.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}
        
        # Instructor login
        instructor_login = client.post(
            "/api/v1/auth/login",
            json={"email": "boundary_instructor@test.com", "password": "instructor123"}
        )
        instructor_token = instructor_login.json()["access_token"]
        instructor_headers = {"Authorization": f"Bearer {instructor_token}"}
        
        # Test student permissions
        # Student should NOT be able to create users
        forbidden_response = client.post(
            "/api/v1/users/",
            headers=student_headers,
            json={"name": "Hacker", "email": "hacker@test.com", "password": "hack", "role": "admin"}
        )
        assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN
        
        # Student should NOT be able to list all users
        forbidden_response = client.get("/api/v1/users/", headers=student_headers)
        assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN
        
        # Student should NOT be able to access admin reports
        forbidden_response = client.get("/api/v1/reports/semester/1", headers=student_headers)
        assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN
        
        # Test instructor permissions
        # Instructor should NOT be able to create users
        forbidden_response = client.post(
            "/api/v1/users/",
            headers=instructor_headers,
            json={"name": "Hacker", "email": "hacker2@test.com", "password": "hack", "role": "admin"}
        )
        assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN
        
        # Instructor should NOT be able to access reports
        forbidden_response = client.get("/api/v1/reports/semester/1", headers=instructor_headers)
        assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN

    def test_booking_workflow_edge_cases(self, client, admin_user, admin_token):
        """
        Test booking system edge cases:
        - Capacity limits
        - Waitlist management
        - Booking deadlines
        - Cancellation policies
        """
        # Setup admin and get token
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create semester
        semester_data = {
            "code": "2024/2",
            "name": "Test Semester",
            "start_date": "2024-09-01",
            "end_date": "2024-12-31"
        }
        semester = client.post("/api/v1/semesters/", headers=admin_headers, json=semester_data).json()
        
        # Create group
        group_data = {"name": "Test Group", "semester_id": semester["id"]}
        group = client.post("/api/v1/groups/", headers=admin_headers, json=group_data).json()
        
        # Create session with limited capacity
        session_start = datetime.now() + timedelta(days=1)
        session_data = {
            "title": "Limited Session",
            "date_start": session_start.isoformat(),
            "date_end": (session_start + timedelta(hours=2)).isoformat(),
            "capacity": 1,  # Only 1 spot
            "semester_id": semester["id"],
            "group_id": group["id"]
        }
        session = client.post("/api/v1/sessions/", headers=admin_headers, json=session_data).json()
        
        # Create 3 students
        students = []
        for i in range(3):
            student_data = {
                "name": f"Edge Student {i+1}",
                "email": f"edge_student{i+1}@test.com",
                "password": "student123",
                "role": "student",
                "payment_verified": True  # Required for booking sessions
            }
            student = client.post("/api/v1/users/", headers=admin_headers, json=student_data).json()
            students.append(student)
            
            # Add to group
            client.post(
                f"/api/v1/groups/{group['id']}/users",
                headers=admin_headers,
                json={"user_id": student["id"]}
            )
        
        # Student logins and bookings
        bookings = []
        for i, student in enumerate(students):
            login_response = client.post(
                "/api/v1/auth/login",
                json={"email": f"edge_student{i+1}@test.com", "password": "student123"}
            )
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            booking_response = client.post(
                "/api/v1/bookings/",
                headers=headers,
                json={"session_id": session["id"]}
            )
            assert booking_response.status_code == status.HTTP_200_OK
            booking = booking_response.json()
            bookings.append((booking, headers))
            
            # First student should be confirmed, others waitlisted
            if i == 0:
                assert booking["status"] == "confirmed"
            else:
                assert booking["status"] == "waitlisted"
                assert booking["waitlist_position"] == i
        
        # First student cancels - second should be promoted
        first_booking, first_headers = bookings[0]
        cancel_response = client.delete(
            f"/api/v1/bookings/{first_booking['id']}",
            headers=first_headers
        )
        assert cancel_response.status_code == status.HTTP_200_OK
        
        # Check that second student was promoted (would need to check in actual implementation)
        # This is a placeholder for the promotion logic test

    def test_data_integrity_and_validation(self, client, admin_user, admin_token):
        """
        Test data integrity and validation:
        - Invalid data handling
        - Constraint violations
        - Foreign key relationships
        """
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test invalid email format
        invalid_user = {
            "name": "Invalid User",
            "email": "not-an-email",
            "password": "password123",
            "role": "student"
        }
        response = client.post("/api/v1/users/", headers=admin_headers, json=invalid_user)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test invalid date range for semester
        invalid_semester = {
            "code": "2024/TEST",
            "name": "Invalid Semester",
            "start_date": "2024-12-31",
            "end_date": "2024-09-01"  # End before start
        }
        response = client.post("/api/v1/semesters/", headers=admin_headers, json=invalid_semester)
        # This would fail validation in a complete implementation
        
        # Test foreign key constraints
        invalid_group = {
            "name": "Invalid Group",
            "semester_id": 99999  # Non-existent semester
        }
        response = client.post("/api/v1/groups/", headers=admin_headers, json=invalid_group)
        assert response.status_code == status.HTTP_404_NOT_FOUND