#!/usr/bin/env python3
"""
Hook 2 Test: Exercise Grading → Competency Assessment

Tests the automatic competency assessment triggered when an instructor
grades a student's exercise submission.
"""

import requests
import json
from datetime import datetime
import bcrypt

# ============================================
# CONFIGURATION
# ============================================
BASE_URL = "http://localhost:8000/api/v1"

# Colors for terminal output
class Colors:
    HEADER = '\033[94m'
    OK = '\033[92m'
    FAIL = '\033[91m'
    WARN = '\033[93m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.END}\n")

def print_step(text):
    print(f"{Colors.HEADER}ℹ️  {text}{Colors.END}")

def print_success(text):
    print(f"{Colors.OK}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.END}")

def print_warn(text):
    print(f"{Colors.WARN}⚠️  {text}{Colors.END}")

# ============================================
# TEST FUNCTIONS
# ============================================

def create_test_users():
    """Create student and instructor test accounts"""
    from app.database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    timestamp = int(datetime.now().timestamp())

    try:
        # Create student
        student_email = f"hook2_student_{timestamp}@test.com"
        student_password = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode('utf-8')

        student_result = db.execute(text("""
            INSERT INTO users (email, password_hash, name, role, specialization, is_active, payment_verified)
            VALUES (:email, :password, 'Hook2 Student', 'STUDENT', 'PLAYER', true, true)
            RETURNING id, email
        """), {"email": student_email, "password": student_password}).fetchone()

        # Create instructor
        instructor_email = f"hook2_instructor_{timestamp}@test.com"
        instructor_password = bcrypt.hashpw(b"InstructorPass123!", bcrypt.gensalt()).decode('utf-8')

        instructor_result = db.execute(text("""
            INSERT INTO users (email, password_hash, name, role, is_active, payment_verified)
            VALUES (:email, :password, 'Hook2 Instructor', 'INSTRUCTOR', true, true)
            RETURNING id, email
        """), {"email": instructor_email, "password": instructor_password}).fetchone()

        db.commit()

        return {
            "student": {"id": student_result.id, "email": student_email, "password": "TestPass123!"},
            "instructor": {"id": instructor_result.id, "email": instructor_email, "password": "InstructorPass123!"}
        }

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def login(email, password):
    """Login and get access token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )

    if response.status_code != 200:
        print_error(f"Login failed: {response.status_code}")
        print(response.text)
        return None

    data = response.json()
    return data["access_token"]


def submit_exercise(student_token, exercise_id):
    """Submit an exercise as student"""
    response = requests.post(
        f"{BASE_URL}/curriculum/exercise/{exercise_id}/submit",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "submission_url": "https://test.com/ganball-assembly.mp4",
            "submission_text": "Completed Ganball assembly exercise",
            "submission_data": {
                "notes": "Assembly completed successfully",
                "timestamp": datetime.now().isoformat()
            }
        }
    )

    return response


def grade_exercise(instructor_token, submission_id, score):
    """Grade an exercise as instructor - TRIGGERS HOOK 2"""
    response = requests.post(
        f"{BASE_URL}/curriculum/exercise/submission/{submission_id}/grade",
        headers={"Authorization": f"Bearer {instructor_token}"},
        json={
            "score": score,
            "feedback": "Good work! Exercise demonstrates strong technical skills.",
            "status": "APPROVED"
        }
    )

    return response


def verify_hook2_effects(student_id):
    """Verify Hook 2 created competency assessments and updated scores"""
    from app.database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()

    try:
        # Check competency assessments
        assessments = db.execute(text("""
            SELECT COUNT(*) as count
            FROM competency_assessments
            WHERE user_id = :user_id AND assessment_type = 'EXERCISE'
        """), {"user_id": student_id}).fetchone()

        # Check competency scores
        scores = db.execute(text("""
            SELECT COUNT(*) as count
            FROM user_competency_scores
            WHERE user_id = :user_id
        """), {"user_id": student_id}).fetchone()

        # Check skill scores
        skills = db.execute(text("""
            SELECT COUNT(*) as count
            FROM user_skill_scores
            WHERE user_id = :user_id
        """), {"user_id": student_id}).fetchone()

        return {
            "assessments": assessments.count,
            "competency_scores": scores.count,
            "skill_scores": skills.count
        }

    finally:
        db.close()


# ============================================
# MAIN TEST
# ============================================

def main():
    print_header("HOOK 2 TEST: Exercise Grading → Competency Assessment")

    # Step 1: Create test users
    print_step("Step 1: Creating test users...")
    try:
        users = create_test_users()
        student = users["student"]
        instructor = users["instructor"]
        print_success(f"Student created: {student['email']} (ID: {student['id']})")
        print_success(f"Instructor created: {instructor['email']} (ID: {instructor['id']})")
    except Exception as e:
        print_error(f"Failed to create users: {e}")
        return False

    # Step 2: Login as student
    print_step("\nStep 2: Login as student...")
    student_token = login(student["email"], student["password"])
    if not student_token:
        return False
    print_success("Student login successful")

    # Step 3: Submit exercise
    print_step("\nStep 3: Submit exercise (Ganball Assembly)...")
    exercise_id = 1  # Ganball Assembly exercise
    submit_response = submit_exercise(student_token, exercise_id)

    if submit_response.status_code != 200:
        print_error(f"Exercise submission failed: {submit_response.status_code}")
        print(submit_response.text)
        return False

    submission_data = submit_response.json()
    submission_id = submission_data.get("submission_id") or submission_data.get("id")
    print_success(f"Exercise submitted (Submission ID: {submission_id})")

    # Step 4: Login as instructor
    print_step("\nStep 4: Login as instructor...")
    instructor_token = login(instructor["email"], instructor["password"])
    if not instructor_token:
        return False
    print_success("Instructor login successful")

    # Step 5: Grade exercise - TRIGGER HOOK 2
    print_step("\nStep 5: Grade exercise (TRIGGER HOOK 2)...")
    print_warn("⚡ This should trigger automatic competency assessment!")

    score = 85  # High score to test competency improvement
    grade_response = grade_exercise(instructor_token, submission_id, score)

    if grade_response.status_code != 200:
        print_error(f"Exercise grading failed: {grade_response.status_code}")
        print(grade_response.text)
        return False

    grade_data = grade_response.json()
    print_success(f"Exercise graded successfully!")
    print_success(f"   Score: {grade_data.get('score')}/100")
    print_success(f"   Status: {grade_data.get('grade_status')}")
    print_success(f"   XP Awarded: {grade_data.get('xp_awarded', 0)}")

    # Step 6: Verify Hook 2 effects
    print_step("\nStep 6: Verifying Hook 2 effects in database...")

    try:
        effects = verify_hook2_effects(student["id"])

        print_success("Hook 2 database effects:")
        print_success(f"   Competency Assessments (EXERCISE): {effects['assessments']}")
        print_success(f"   Competency Scores Updated: {effects['competency_scores']}")
        print_success(f"   Skill Scores Updated: {effects['skill_scores']}")

        if effects['assessments'] == 0:
            print_warn("No competency assessments created - Hook 2 may have failed")
            return False

    except Exception as e:
        print_error(f"Database verification failed: {e}")
        return False

    print_header("✅ HOOK 2 TEST COMPLETE!")
    print_success("All checks passed - Hook 2 is working correctly!")

    return True


if __name__ == "__main__":
    print("\n⚠️  Make sure the server is running on http://localhost:8000")
    print("Press Ctrl+C to cancel, or Enter to continue...")
    input()

    success = main()

    if success:
        print(f"\n{Colors.OK}{Colors.BOLD}🎉 HOOK 2 TEST PASSED!{Colors.END}\n")
        exit(0)
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}❌ HOOK 2 TEST FAILED!{Colors.END}\n")
        exit(1)
