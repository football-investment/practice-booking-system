#!/usr/bin/env python3
"""
Simplified Integration Testing for Hooks 1, 2, 3
Uses existing database users instead of registration
"""
import requests
import time
from datetime import datetime
from sqlalchemy import create_engine, text

# Config
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"
DATABASE_URL = "postgresql://lfa_user:lfa2024@localhost/practice_booking_system"

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_section(title):
    print(f"\n{BLUE}{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}{RESET}\n")

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

# Test execution
print_section("LFA ACADEMY - HOOK INTEGRATION TEST")

# Step 1: Create test student directly in database
print_info("Step 1: Creating test student in database...")
engine = create_engine(DATABASE_URL)

timestamp = int(time.time())
test_email = f"hook_test_{timestamp}@test.com"
test_password = "HookTest123!"

# Hash password (bcrypt format)
from app.core.security import get_password_hash
password_hash = get_password_hash(test_password)

with engine.connect() as conn:
    # Insert user - minimal fields only
    result = conn.execute(text("""
        INSERT INTO users (name, email, password_hash, role, is_active, specialization, payment_verified, onboarding_completed)
        VALUES (:name, :email, :password_hash, 'STUDENT', true, 'PLAYER', true, true)
        RETURNING id
    """), {
        "name": f"Hook Test Student {timestamp}",
        "email": test_email,
        "password_hash": password_hash
    })
    student_id = result.fetchone()[0]
    conn.commit()
    print_success(f"Test student created: {test_email} (ID: {student_id})")

# Step 2: Login
print_info("Step 2: Logging in...")
login_data = {
    "email": test_email,
    "password": test_password
}

response = requests.post(f"{API_V1}/auth/login", json=login_data)
if response.status_code == 200:
    data = response.json()
    token = data["access_token"]
    print_success(f"Login successful. Token: {token[:30]}...")
else:
    print_error(f"Login failed: {response.status_code} - {response.text}")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

# Step 3: Get available quizzes
print_section("HOOK 1 TEST: Quiz Completion → Competency Assessment")
print_info("Step 3: Fetching available quizzes...")

response = requests.get(f"{API_V1}/quizzes/available", headers=headers)
if response.status_code != 200:
    print_error(f"Failed to get quizzes: {response.status_code}")
    exit(1)

quizzes = response.json()
if not quizzes:
    print_error("No quizzes available")
    exit(1)

quiz = quizzes[0]
quiz_id = quiz["id"]
print_success(f"Found quiz: {quiz['title']} (ID: {quiz_id})")

# Step 4: Start quiz
print_info("Step 4: Starting quiz attempt...")
response = requests.post(f"{API_V1}/quizzes/start", json={"quiz_id": quiz_id}, headers=headers)
if response.status_code != 200:
    print_error(f"Failed to start quiz: {response.status_code} - {response.text}")
    exit(1)

attempt = response.json()
attempt_id = attempt["id"]
print_success(f"Quiz attempt started (ID: {attempt_id})")

# Step 5: Get quiz questions
print_info("Step 5: Fetching quiz questions...")
response = requests.get(f"{API_V1}/quizzes/{quiz_id}", headers=headers)
if response.status_code != 200:
    print_error(f"Failed to get questions: {response.status_code}")
    exit(1)

quiz_data = response.json()
questions = quiz_data.get("questions", [])
if not questions:
    print_error("No questions in quiz")
    exit(1)

print_success(f"Found {len(questions)} questions")

# Step 6: Submit quiz with LOW score (answer only first question correctly)
print_info("Step 6: Submitting quiz with LOW score (<70%) to trigger Hook 1...")

answers = []
for i, question in enumerate(questions):
    if question.get("answer_options"):
        if i == 0:  # First question correct
            correct_option = next((opt for opt in question["answer_options"] if opt.get("is_correct")), None)
            selected_id = correct_option["id"] if correct_option else question["answer_options"][0]["id"]
        else:  # Rest incorrect
            wrong_option = next((opt for opt in question["answer_options"] if not opt.get("is_correct")), None)
            selected_id = wrong_option["id"] if wrong_option else question["answer_options"][0]["id"]

        answers.append({
            "question_id": question["id"],
            "selected_option_id": selected_id,
            "time_spent_seconds": 10
        })

submission_data = {
    "quiz_id": quiz_id,
    "attempt_id": attempt_id,
    "answers": answers,
    "time_taken_seconds": len(questions) * 10
}

response = requests.post(f"{API_V1}/quizzes/submit", json=submission_data, headers=headers)
if response.status_code != 200:
    print_error(f"Quiz submission failed: {response.status_code} - {response.text}")
    exit(1)

result = response.json()
score = result.get("score", 0)
print_success(f"Quiz submitted! Score: {score}%")

if score < 70:
    print_success("✅ LOW SCORE (<70%) - Hook 1 should trigger!")
else:
    print_error(f"Score is {score}% (>=70%) - may not trigger REVIEW_LESSON")

# Step 7: Verify Hook 1 effects in database
print_info("\nStep 7: Verifying Hook 1 effects in database...")
time.sleep(2)  # Wait for async processing

with engine.connect() as conn:
    # Check competency assessments
    result = conn.execute(text("""
        SELECT ca.id, cc.name as category, cs.name as skill, ca.score
        FROM competency_assessments ca
        JOIN competency_skills cs ON cs.id = ca.skill_id
        JOIN competency_categories cc ON cc.id = cs.category_id
        WHERE ca.user_id = :user_id AND ca.source_type = 'quiz'
        ORDER BY ca.assessed_at DESC
        LIMIT 5
    """), {"user_id": student_id})

    assessments = result.fetchall()
    if assessments:
        print_success(f"Found {len(assessments)} competency assessments from quiz:")
        for a in assessments:
            print_info(f"  - {a.category} > {a.skill}: {a.score}%")
    else:
        print_error("No competency assessments found - Hook 1 may not be working!")

    # Check learning profile
    result = conn.execute(text("""
        SELECT learning_pace, quiz_average_score, lessons_completed, last_activity_at
        FROM user_learning_profiles
        WHERE user_id = :user_id
    """), {"user_id": student_id})

    profile = result.fetchone()
    if profile:
        print_success("Learning profile updated:")
        print_info(f"  - Pace: {profile.learning_pace}")
        print_info(f"  - Quiz avg: {profile.quiz_average_score}%")
        print_info(f"  - Lessons completed: {profile.lessons_completed}")
    else:
        print_error("No learning profile found - Hook 1 may not be working!")

    # Check recommendations
    result = conn.execute(text("""
        SELECT recommendation_type, title, priority
        FROM adaptive_recommendations
        WHERE user_id = :user_id AND is_active = true
        ORDER BY created_at DESC
        LIMIT 3
    """), {"user_id": student_id})

    recommendations = result.fetchall()
    if recommendations:
        print_success(f"Found {len(recommendations)} active recommendations:")
        review_found = False
        for rec in recommendations:
            print_info(f"  - {rec.recommendation_type}: {rec.title} (Priority: {rec.priority})")
            if rec.recommendation_type == "REVIEW_LESSON":
                review_found = True

        if review_found:
            print_success("✅ REVIEW_LESSON recommendation found - Hook 1 is working!")
        else:
            print_error("No REVIEW_LESSON recommendation - expected for score < 70%")
    else:
        print_error("No recommendations found - Hook 1 may not be working!")

# Step 8: Test Hook 3 (Manual snapshot trigger)
print_section("HOOK 3 TEST: Daily Snapshot Creation")
print_info("Step 8: Manually triggering performance snapshot...")

response = requests.post(f"{API_V1}/curriculum-adaptive/snapshot", headers=headers)
if response.status_code == 200:
    print_success("Snapshot created successfully")
else:
    print_error(f"Snapshot creation failed: {response.status_code} - {response.text}")

# Step 9: Verify snapshot in database
print_info("Step 9: Verifying snapshot in database...")
time.sleep(1)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT snapshot_date, quiz_average, lessons_completed, total_xp
        FROM performance_snapshots
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT 1
    """), {"user_id": student_id})

    snapshot = result.fetchone()
    if snapshot:
        print_success("Performance snapshot found:")
        print_info(f"  - Date: {snapshot.snapshot_date}")
        print_info(f"  - Quiz avg: {snapshot.quiz_average}%")
        print_info(f"  - Lessons: {snapshot.lessons_completed}")
        print_info(f"  - XP: {snapshot.total_xp}")
        print_success("✅ Hook 3 is working!")
    else:
        print_error("No snapshot found - Hook 3 may not be working!")

# Final summary
print_section("TEST SUMMARY")
print_success("✅ Hook 1 (Quiz → Competency): TESTED")
print_success("✅ Hook 3 (Daily Snapshot): TESTED")
print_info("ℹ️  Hook 2 (Exercise → Competency): Requires instructor grading (skipped)")

print(f"\n{GREEN}🎉 Integration tests complete!{RESET}")
print(f"{BLUE}Test student ID: {student_id}{RESET}")
print(f"{BLUE}Test email: {test_email}{RESET}\n")
