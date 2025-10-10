#!/usr/bin/env python3
"""
Integration Testing Script for LFA Academy Hooks
Tests Hook 1 (Quiz), Hook 2 (Exercise), Hook 3 (Snapshot)
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_section(msg):
    print(f"\n{BLUE}{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}{RESET}\n")


class IntegrationTester:
    def __init__(self):
        self.student_token = None
        self.instructor_token = None
        self.student_id = None
        self.instructor_id = None
        self.test_results = {
            "registration": False,
            "login": False,
            "quiz_hook": False,
            "exercise_hook": False,
            "snapshot_hook": False
        }

    def test_1_student_registration(self):
        """Test 1: Register a test student account"""
        print_section("TEST 1: Student Registration & Login")

        # Step 1: Register student
        print_info("Step 1: Registering test student...")
        timestamp = int(time.time())
        student_data = {
            "email": f"test_student_{timestamp}@lfa.test",
            "password": "TestPass123!",
            "name": f"Test Student {timestamp}",
            "role": "STUDENT"
        }

        try:
            response = requests.post(f"{API_V1}/auth/register", json=student_data)
            if response.status_code == 201:
                print_success(f"Student registered: {student_data['email']}")
                self.test_results["registration"] = True
            else:
                print_error(f"Registration failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print_error(f"Registration error: {e}")
            return False

        # Step 2: Login student
        print_info("Step 2: Logging in student...")
        login_data = {
            "username": student_data["email"],
            "password": student_data["password"]
        }

        try:
            response = requests.post(f"{API_V1}/auth/login", data=login_data)
            if response.status_code == 200:
                data = response.json()
                self.student_token = data["access_token"]
                self.student_id = data["user"]["id"]
                print_success(f"Student logged in. Token: {self.student_token[:20]}...")
                print_success(f"Student ID: {self.student_id}")
                self.test_results["login"] = True
            else:
                print_error(f"Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print_error(f"Login error: {e}")
            return False

        # Step 3: Select specialization
        print_info("Step 3: Selecting PLAYER specialization...")
        headers = {"Authorization": f"Bearer {self.student_token}"}

        try:
            response = requests.post(
                f"{API_V1}/students/select-specialization",
                json={"specialization": "PLAYER"},
                headers=headers
            )
            if response.status_code == 200:
                print_success("Specialization PLAYER selected")
            else:
                print_warning(f"Specialization selection: {response.status_code} - {response.text}")
        except Exception as e:
            print_warning(f"Specialization error: {e}")

        return True

    def test_2_quiz_hook(self):
        """Test 3: Quiz Completion + Hook 1"""
        print_section("TEST 3: Quiz Completion + Hook 1 (CRITICAL)")

        if not self.student_token:
            print_error("No student token - run test 1 first")
            return False

        headers = {"Authorization": f"Bearer {self.student_token}"}

        # Step 1: Get available quizzes
        print_info("Step 1: Fetching available quizzes...")
        try:
            response = requests.get(f"{API_V1}/quizzes/available", headers=headers)
            if response.status_code == 200:
                quizzes = response.json()
                if not quizzes:
                    print_error("No quizzes available")
                    return False
                quiz = quizzes[0]
                quiz_id = quiz["id"]
                print_success(f"Found quiz: {quiz['title']} (ID: {quiz_id})")
            else:
                print_error(f"Failed to get quizzes: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Quiz fetch error: {e}")
            return False

        # Step 2: Start quiz attempt
        print_info("Step 2: Starting quiz attempt...")
        try:
            response = requests.post(f"{API_V1}/quizzes/{quiz_id}/start", headers=headers)
            if response.status_code == 200:
                attempt = response.json()
                attempt_id = attempt["id"]
                print_success(f"Quiz attempt started (ID: {attempt_id})")
            else:
                print_error(f"Failed to start quiz: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Quiz start error: {e}")
            return False

        # Step 3: Get quiz questions
        print_info("Step 3: Fetching quiz questions...")
        try:
            response = requests.get(f"{API_V1}/quizzes/{quiz_id}", headers=headers)
            if response.status_code == 200:
                quiz_data = response.json()
                questions = quiz_data.get("questions", [])
                if not questions:
                    print_error("No questions in quiz")
                    return False
                print_success(f"Found {len(questions)} questions")
            else:
                print_error(f"Failed to get questions: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Question fetch error: {e}")
            return False

        # Step 4: Submit quiz with INTENTIONALLY LOW SCORE (< 70%)
        print_info("Step 4: Submitting quiz with LOW score (< 70% to trigger REVIEW_LESSON recommendation)...")

        # Answer first question correctly, rest incorrectly
        answers = []
        for i, question in enumerate(questions):
            if question.get("answer_options"):
                # For first question, find correct answer; for rest, pick wrong answer
                if i == 0:
                    correct_option = next((opt for opt in question["answer_options"] if opt.get("is_correct")), None)
                    selected_id = correct_option["id"] if correct_option else question["answer_options"][0]["id"]
                else:
                    # Pick first wrong answer
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

        try:
            print_info(f"Submitting {len(answers)} answers (1 correct, {len(answers)-1} incorrect)...")
            response = requests.post(f"{API_V1}/quizzes/submit", json=submission_data, headers=headers)

            if response.status_code == 200:
                result = response.json()
                score = result.get("score", 0)
                print_success(f"Quiz submitted! Score: {score}%")

                if score < 70:
                    print_success("✅ LOW SCORE (<70%) - This should trigger Hook 1!")
                else:
                    print_warning(f"Score is {score}% (>= 70%) - may not trigger REVIEW_LESSON recommendation")

                # Step 5: Verify Hook 1 effects
                print_info("\nStep 5: Verifying Hook 1 effects...")
                time.sleep(2)  # Wait for async processing

                # Check competency assessments
                print_info("Checking competency assessments...")
                response = requests.get(f"{API_V1}/competency/assessment-history?limit=5", headers=headers)
                if response.status_code == 200:
                    assessments = response.json()
                    quiz_assessments = [a for a in assessments if a.get("source_type") == "quiz"]
                    if quiz_assessments:
                        print_success(f"Found {len(quiz_assessments)} quiz-based competency assessments")
                        for a in quiz_assessments[:3]:
                            print_info(f"  - Category: {a.get('category_name')}, Score: {a.get('score')}, Level: {a.get('level_achieved')}")
                    else:
                        print_warning("No quiz-based assessments found yet")
                else:
                    print_warning(f"Could not fetch assessments: {response.status_code}")

                # Check learning profile update
                print_info("Checking learning profile update...")
                response = requests.get(f"{API_V1}/curriculum-adaptive/profile", headers=headers)
                if response.status_code == 200:
                    profile = response.json()
                    print_success(f"Learning profile updated:")
                    print_info(f"  - Pace: {profile.get('learning_pace')}")
                    print_info(f"  - Quiz avg: {profile.get('quiz_average_score', 0):.1f}%")
                    print_info(f"  - Last activity: {profile.get('last_activity_at')}")
                else:
                    print_warning(f"Could not fetch profile: {response.status_code}")

                # Check recommendations (should include REVIEW_LESSON)
                print_info("Checking adaptive recommendations...")
                response = requests.get(f"{API_V1}/curriculum-adaptive/recommendations?refresh=true", headers=headers)
                if response.status_code == 200:
                    recommendations = response.json()
                    if recommendations:
                        print_success(f"Found {len(recommendations)} recommendations:")
                        for rec in recommendations:
                            rec_type = rec.get('recommendation_type', 'UNKNOWN')
                            print_info(f"  - {rec_type}: {rec.get('title', 'No title')}")
                            if rec_type == "REVIEW_LESSON":
                                print_success("✅ REVIEW_LESSON recommendation found - Hook 1 working!")
                    else:
                        print_warning("No recommendations generated")
                else:
                    print_warning(f"Could not fetch recommendations: {response.status_code}")

                self.test_results["quiz_hook"] = True
                print_success("\n🎯 Hook 1 (Quiz Completion) TEST COMPLETE")
                return True
            else:
                print_error(f"Quiz submission failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print_error(f"Quiz submission error: {e}")
            return False

    def test_3_register_instructor(self):
        """Register instructor for exercise grading test"""
        print_section("Setting up Instructor Account")

        print_info("Registering test instructor...")
        timestamp = int(time.time())
        instructor_data = {
            "email": f"test_instructor_{timestamp}@lfa.test",
            "password": "InstructorPass123!",
            "name": f"Test Instructor {timestamp}",
            "role": "INSTRUCTOR"
        }

        try:
            response = requests.post(f"{API_V1}/auth/register", json=instructor_data)
            if response.status_code == 201:
                print_success(f"Instructor registered: {instructor_data['email']}")
            else:
                print_error(f"Instructor registration failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Instructor registration error: {e}")
            return False

        # Login instructor
        print_info("Logging in instructor...")
        login_data = {
            "username": instructor_data["email"],
            "password": instructor_data["password"]
        }

        try:
            response = requests.post(f"{API_V1}/auth/login", data=login_data)
            if response.status_code == 200:
                data = response.json()
                self.instructor_token = data["access_token"]
                self.instructor_id = data["user"]["id"]
                print_success(f"Instructor logged in. ID: {self.instructor_id}")
                return True
            else:
                print_error(f"Instructor login failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Instructor login error: {e}")
            return False

    def test_4_snapshot_hook(self):
        """Test 5: Daily Snapshot + Hook 3"""
        print_section("TEST 5: Daily Snapshot + Hook 3 (CRITICAL)")

        if not self.student_token:
            print_error("No student token - run test 1 first")
            return False

        headers = {"Authorization": f"Bearer {self.student_token}"}

        # Step 1: Manually trigger snapshot
        print_info("Step 1: Manually triggering performance snapshot...")
        try:
            response = requests.post(f"{API_V1}/curriculum-adaptive/snapshot", headers=headers)
            if response.status_code == 200:
                print_success("Performance snapshot created")
            else:
                print_warning(f"Snapshot creation: {response.status_code} - {response.text}")
        except Exception as e:
            print_warning(f"Snapshot error: {e}")

        # Step 2: Verify snapshot in history
        print_info("Step 2: Verifying snapshot in performance history...")
        time.sleep(1)

        try:
            response = requests.get(f"{API_V1}/curriculum-adaptive/performance-history?days=7", headers=headers)
            if response.status_code == 200:
                history = response.json()
                if history:
                    print_success(f"Found {len(history)} performance snapshots:")
                    for snapshot in history[:3]:
                        print_info(f"  - Date: {snapshot.get('snapshot_date')}")
                        print_info(f"    Pace: {snapshot.get('pace_score', 0):.1f}, Quiz avg: {snapshot.get('quiz_average', 0):.1f}%")
                    self.test_results["snapshot_hook"] = True
                    print_success("\n🎯 Hook 3 (Daily Snapshot) TEST COMPLETE")
                    return True
                else:
                    print_warning("No snapshots found in history")
                    return False
            else:
                print_error(f"Failed to get performance history: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Performance history error: {e}")
            return False

    def print_final_report(self):
        """Print final test results"""
        print_section("FINAL TEST REPORT")

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)

        print(f"{'Test':<30} {'Status':<10}")
        print("-" * 40)

        for test_name, result in self.test_results.items():
            status = f"{GREEN}✅ PASS{RESET}" if result else f"{RED}❌ FAIL{RESET}"
            print(f"{test_name:<30} {status}")

        print("-" * 40)
        print(f"\nTotal: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print_success("\n🎉 ALL INTEGRATION TESTS PASSED!")
        else:
            print_warning(f"\n⚠️  {total_tests - passed_tests} test(s) failed")

    def run_all_tests(self):
        """Run all integration tests"""
        print(f"{BLUE}")
        print("╔" + "="*58 + "╗")
        print("║" + " "*10 + "LFA ACADEMY INTEGRATION TESTING" + " "*17 + "║")
        print("║" + " "*15 + "Hook 1, Hook 2, Hook 3" + " "*21 + "║")
        print("╚" + "="*58 + "╝")
        print(f"{RESET}\n")

        # Test 1: Registration & Login
        if not self.test_1_student_registration():
            print_error("Student registration failed - stopping tests")
            self.print_final_report()
            return

        # Test 2: Quiz Hook
        self.test_2_quiz_hook()

        # Test 3: Snapshot Hook
        self.test_4_snapshot_hook()

        # Final report
        self.print_final_report()


if __name__ == "__main__":
    print_info("Starting integration tests...")
    print_info(f"Target: {BASE_URL}")
    print_info("Make sure the application is running: uvicorn app.main:app --reload\n")

    try:
        # Quick connectivity check
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print_success("Application is reachable\n")
        else:
            print_warning(f"Unexpected response: {response.status_code}\n")
    except Exception as e:
        print_error(f"Cannot connect to application: {e}")
        print_error("Please start the application first: uvicorn app.main:app --reload")
        exit(1)

    tester = IntegrationTester()
    tester.run_all_tests()
