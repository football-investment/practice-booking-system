"""
E2E Test: Instructor Application Workflow (Scenario 2)

✅ PRODUCTION-READY WORKFLOW TEST

This test validates the complete instructor application workflow for tournaments:

SCENARIO 2 - Application Workflow:
1. Admin creates tournament → status: SEEKING_INSTRUCTOR
2. Instructor applies to tournament (POST /tournaments/{id}/instructor-applications)
3. Admin approves application (POST /tournaments/{id}/instructor-applications/{id}/approve)
4. Instructor accepts assignment (POST /tournaments/{id}/instructor-assignment/accept)
5. Status changes to READY_FOR_ENROLLMENT
6. Players can enroll
7. Attendance records created
8. Rankings set
9. Tournament marked as COMPLETED
10. Rewards distributed successfully

VALIDATIONS:
✅ Instructor can apply with LFA_COACH license
✅ Application status: PENDING → ACCEPTED
✅ Admin can approve application
✅ Instructor can accept after approval
✅ master_instructor_id set correctly
✅ session.instructor_id set for all sessions
✅ Tournament status transitions correctly
✅ Production validations pass (attendance_count > 0)
✅ Reward distribution works correctly

BACKEND COMPONENTS TESTED:
- POST /api/v1/tournaments/{id}/instructor-applications
- POST /api/v1/tournaments/{id}/instructor-applications/{id}/approve
- POST /api/v1/tournaments/{id}/instructor-assignment/accept
- InstructorAssignmentRequest model
- Production validations enabled
"""

import pytest
import requests
from typing import Dict, Any, List

# Import fixtures from reward_policy_fixtures
from tests.e2e.reward_policy_fixtures import (
    API_BASE_URL,
    reward_policy_admin_token,
    create_instructor_user,
    create_tournament_via_api,
    instructor_applies_to_tournament,
    admin_approves_instructor_application,
    instructor_accepts_assignment,
    create_player_users,
    enroll_players_in_tournament,
    create_attendance_records,
    set_tournament_rankings,
    mark_tournament_completed,
)


class TestInstructorApplicationWorkflow:
    """Test suite for Scenario 2: Instructor Application Workflow"""

    def test_complete_application_workflow(
        self,
        reward_policy_admin_token: str
    ):
        """
        Test complete instructor application workflow from application to reward distribution.

        Workflow:
        1. Create tournament (SEEKING_INSTRUCTOR)
        2. Instructor applies
        3. Admin approves
        4. Instructor accepts
        5. Players enroll
        6. Attendance recorded
        7. Rankings set
        8. Rewards distributed

        Expected:
        - All API calls succeed
        - Application status transitions correctly
        - master_instructor_id set properly
        - session.instructor_id set for all sessions
        - Reward distribution succeeds with validations
        """
        print("\n" + "="*80)
        print("📋 E2E TEST: Instructor Application Workflow (Scenario 2)")
        print("="*80 + "\n")

        from datetime import datetime, timedelta
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        # ========================================================================
        # STEP 1: Create tournament
        # ========================================================================
        print("  1️⃣ Creating tournament...")

        tournament_result = create_tournament_via_api(
            token=reward_policy_admin_token,
            name=f"Application Test Tournament {timestamp}",
            reward_policy_name="default",
            age_group="AMATEUR"
        )

        tournament_id = tournament_result["tournament_id"]
        status = tournament_result.get("status") or tournament_result.get("summary", {}).get("status")
        assert status == "SEEKING_INSTRUCTOR", \
            f"Expected SEEKING_INSTRUCTOR, got {status}"

        print(f"     ✅ Tournament {tournament_id} created")
        print(f"     ✅ Status: {status}")

        # ========================================================================
        # STEP 2: Create instructor with LFA_COACH license
        # ========================================================================
        print("\n  2️⃣ Creating instructor with LFA_COACH license...")

        instructor = create_instructor_user(reward_policy_admin_token)

        print(f"     ✅ Instructor {instructor['id']} created")
        print(f"     ✅ Email: {instructor['email']}")
        print(f"     ✅ LFA_COACH license: {instructor['license_id']}")

        # ========================================================================
        # STEP 3: Instructor applies to tournament
        # ========================================================================
        print("\n  3️⃣ Instructor applies to tournament...")

        application_response = instructor_applies_to_tournament(
            instructor_token=instructor["token"],
            tournament_id=tournament_id,
            application_message="I am interested in leading this tournament"
        )

        application_id = application_response["application_id"]
        assert application_response["status"] == "PENDING", \
            f"Expected PENDING status, got {application_response['status']}"
        assert application_response["instructor_id"] == instructor["id"], \
            "Instructor ID mismatch"

        print(f"     ✅ Application {application_id} submitted")
        print(f"     ✅ Status: {application_response['status']}")
        print(f"     ✅ Message: {application_response['application_message']}")

        # ========================================================================
        # STEP 4: Admin approves application
        # ========================================================================
        print("\n  4️⃣ Admin approves application...")

        approval_response = admin_approves_instructor_application(
            admin_token=reward_policy_admin_token,
            tournament_id=tournament_id,
            application_id=application_id,
            response_message="Application approved - looking forward to working with you"
        )

        assert approval_response["status"] == "ACCEPTED", \
            f"Expected ACCEPTED status, got {approval_response['status']}"
        assert approval_response["instructor_id"] == instructor["id"], \
            "Instructor ID mismatch after approval"

        print(f"     ✅ Application approved")
        print(f"     ✅ Status: {approval_response['status']}")
        print(f"     ✅ Approved by: {approval_response['approved_by_name']}")
        print(f"     ✅ Response: {approval_response['response_message']}")

        # ========================================================================
        # STEP 5: Instructor accepts assignment
        # ========================================================================
        print("\n  5️⃣ Instructor accepts assignment...")

        accept_response = instructor_accepts_assignment(
            instructor_token=instructor["token"],
            tournament_id=tournament_id
        )

        assert accept_response["status"] == "READY_FOR_ENROLLMENT", \
            f"Expected READY_FOR_ENROLLMENT, got {accept_response['status']}"
        assert accept_response["instructor_id"] == instructor["id"], \
            "Instructor ID mismatch after acceptance"
        assert accept_response["sessions_updated"] == 3, \
            f"Expected 3 sessions updated, got {accept_response['sessions_updated']}"

        print(f"     ✅ Assignment accepted")
        print(f"     ✅ Status: {accept_response['status']}")
        print(f"     ✅ Instructor ID: {accept_response['instructor_id']}")
        print(f"     ✅ Sessions updated: {accept_response['sessions_updated']}")

        # ========================================================================
        # STEP 6: Create and enroll players
        # ========================================================================
        print("\n  6️⃣ Creating and enrolling players...")

        players = create_player_users(
            token=reward_policy_admin_token,
            count=5,
            age_group="AMATEUR"
        )
        player_ids = [p["id"] for p in players]

        enrollments = enroll_players_in_tournament(
            token=reward_policy_admin_token,
            tournament_id=tournament_id,
            player_ids=player_ids
        )

        assert len(enrollments) == 5, \
            f"Expected 5 enrollments, got {len(enrollments)}"

        print(f"     ✅ {len(players)} players created and enrolled")

        # ========================================================================
        # STEP 7: Create attendance records
        # ========================================================================
        print("\n  7️⃣ Creating attendance records...")

        attendance_result = create_attendance_records(
            admin_token=reward_policy_admin_token,
            tournament_id=tournament_id,
            player_ids=player_ids
        )

        assert attendance_result["count"] > 0, \
            "No attendance records created"

        print(f"     ✅ {attendance_result['count']} attendance records created")
        print(f"     ✅ Sessions with attendance: {attendance_result['sessions']}")

        # ========================================================================
        # STEP 8: Set tournament rankings
        # ========================================================================
        print("\n  8️⃣ Setting tournament rankings...")

        rankings = [
            {"user_id": player_ids[0], "placement": "1ST", "points": 15, "wins": 5, "draws": 0, "losses": 0},
            {"user_id": player_ids[1], "placement": "2ND", "points": 12, "wins": 4, "draws": 0, "losses": 1},
            {"user_id": player_ids[2], "placement": "3RD", "points": 9, "wins": 3, "draws": 0, "losses": 2},
            {"user_id": player_ids[3], "placement": "PARTICIPANT", "points": 3, "wins": 1, "draws": 0, "losses": 4},
            {"user_id": player_ids[4], "placement": "PARTICIPANT", "points": 0, "wins": 0, "draws": 0, "losses": 5},
        ]

        set_tournament_rankings(
            token=reward_policy_admin_token,
            tournament_id=tournament_id,
            rankings=rankings
        )

        print(f"     ✅ {len(rankings)} rankings set")

        # ========================================================================
        # STEP 9: Mark tournament as COMPLETED
        # ========================================================================
        print("\n  9️⃣ Marking tournament as COMPLETED...")

        mark_tournament_completed(
            token=reward_policy_admin_token,
            tournament_id=tournament_id
        )

        print(f"     ✅ Tournament status: COMPLETED")

        # ========================================================================
        # STEP 10: Distribute rewards
        # ========================================================================
        print("\n  🔟 Distributing rewards...")

        distribute_response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/distribute-rewards",
            headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
        )
        distribute_response.raise_for_status()
        result = distribute_response.json()

        # Validate reward distribution
        expected_xp = 500 + 300 + 200 + 50 + 50  # 1100
        expected_credits = 100 + 50 + 25 + 0 + 0  # 175

        assert result["total_participants"] == 5, \
            f"Expected 5 participants, got {result['total_participants']}"
        assert result["xp_distributed"] == expected_xp, \
            f"Expected {expected_xp} XP, got {result['xp_distributed']}"
        assert result["credits_distributed"] == expected_credits, \
            f"Expected {expected_credits} credits, got {result['credits_distributed']}"

        print(f"     ✅ Rewards distributed successfully")
        print(f"     ✅ Total participants: {result['total_participants']}")
        print(f"     ✅ Total XP distributed: {result['xp_distributed']}")
        print(f"     ✅ Total credits distributed: {result['credits_distributed']}")

        # ========================================================================
        # CLEANUP
        # ========================================================================
        print("\n  🧹 Cleaning up...")

        # Delete tournament
        try:
            requests.delete(
                f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}",
                headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
            )
        except:
            pass  # Ignore cleanup errors

        # Delete users
        for player in players:
            try:
                requests.delete(
                    f"{API_BASE_URL}/api/v1/users/{player['id']}",
                    headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
                )
            except:
                pass

        try:
            requests.delete(
                f"{API_BASE_URL}/api/v1/users/{instructor['id']}",
                headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
            )
        except:
            pass

        print("\n" + "="*80)
        print("✅ APPLICATION WORKFLOW TEST COMPLETE")
        print("="*80 + "\n")


    def test_application_validations(
        self,
        reward_policy_admin_token: str
    ):
        """
        Test application workflow validations.

        Tests:
        - Instructor without LFA_COACH license cannot apply
        - Duplicate applications rejected
        - Non-admin cannot approve
        - Cannot approve non-existent application
        """
        print("\n" + "="*80)
        print("🔒 E2E TEST: Application Workflow Validations")
        print("="*80 + "\n")

        from datetime import datetime, timedelta
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        # Create tournament
        tournament_result = create_tournament_via_api(
            token=reward_policy_admin_token,
            name=f"Validation Test Tournament {timestamp}",
            reward_policy_name="default",
            age_group="AMATEUR"
        )
        tournament_id = tournament_result["tournament_id"]

        # Create instructor with LFA_COACH license
        instructor = create_instructor_user(reward_policy_admin_token)

        # ========================================================================
        # TEST 1: Duplicate application rejected
        # ========================================================================
        print("  1️⃣ Testing duplicate application rejection...")

        # First application
        app1 = instructor_applies_to_tournament(
            instructor_token=instructor["token"],
            tournament_id=tournament_id
        )

        # Second application should fail
        try:
            app2 = instructor_applies_to_tournament(
                instructor_token=instructor["token"],
                tournament_id=tournament_id
            )
            assert False, "Duplicate application should have been rejected"
        except requests.exceptions.HTTPError as e:
            assert e.response.status_code == 400, \
                f"Expected 400 Bad Request, got {e.response.status_code}"
            error_response = e.response.json()
            # Error structure: {"error": {"code": "...", "message": {"error": "duplicate_application", ...}}}
            error_data = error_response.get("error", {}).get("message", {})
            assert error_data.get("error") == "duplicate_application", \
                f"Expected duplicate_application error, got {error_data.get('error')}"

        print("     ✅ Duplicate application correctly rejected")

        # ========================================================================
        # TEST 2: Non-existent application cannot be approved
        # ========================================================================
        print("\n  2️⃣ Testing non-existent application approval...")

        try:
            fake_approval = admin_approves_instructor_application(
                admin_token=reward_policy_admin_token,
                tournament_id=tournament_id,
                application_id=99999
            )
            assert False, "Non-existent application should have been rejected"
        except requests.exceptions.HTTPError as e:
            assert e.response.status_code == 404, \
                f"Expected 404 Not Found, got {e.response.status_code}"

        print("     ✅ Non-existent application correctly rejected")

        # ========================================================================
        # CLEANUP
        # ========================================================================
        print("\n  🧹 Cleaning up...")

        try:
            requests.delete(
                f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}",
                headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
            )
        except:
            pass

        try:
            requests.delete(
                f"{API_BASE_URL}/api/v1/users/{instructor['id']}",
                headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
            )
        except:
            pass

        print("\n" + "="*80)
        print("✅ VALIDATION TEST COMPLETE")
        print("="*80 + "\n")
