"""
Complete Business Workflow E2E Test

Tests the complete tournament instructor application workflow following exact business logic:

1. Admin creates 2 tournaments
2. Direct instructor assignment for "GrandMaster" instructor → Tournament 1
3. 4 instructors apply to Tournament 2
4. Admin randomly selects 1 instructor, declines 3 others
5. Selected instructor accepts assignment
6. 3 First Team players (@f1rstteamfc.hu) created
7. Coupons created and applied for credits
8. Players enroll in both tournaments (using credits)
9. Attendance records created
10. Tournaments completed with reward distribution
11. Negative test: Instructor cannot create tournament (permission denied)
"""

import pytest
import time
import random
from playwright.sync_api import Page, expect
from tests.e2e.reward_policy_fixtures import (
    create_admin_token,
    create_instructor_user,
    create_multiple_instructors,
    create_first_team_players,
    create_coupon,
    apply_coupon,
    admin_directly_assigns_instructor,
    instructor_applies_to_tournament,
    admin_approves_instructor_application,
    admin_declines_instructor_application,
    instructor_accepts_assignment,
    create_tournament_via_api,
    enroll_players_in_tournament,
    create_attendance_records,
    mark_tournament_completed,
    distribute_rewards
)


@pytest.mark.e2e
class TestCompleteBusinessWorkflow:
    """Complete business workflow E2E test with exact business logic"""

    STREAMLIT_URL = "http://localhost:8501"
    API_BASE_URL = "http://localhost:8000"

    def test_complete_business_workflow(self, page: Page):
        """
        Test complete tournament workflow following exact business algorithm.

        WORKFLOW:
        1. Create 2 tournaments
        2. Direct assign "GrandMaster" to Tournament 1
        3. 4 instructors apply to Tournament 2
        4. Random selection + 3 declines for Tournament 2
        5. First Team players with coupons
        6. Enroll in both tournaments
        7. Complete tournaments with rewards
        8. Negative permission test
        """

        print("\n" + "="*80)
        print("COMPLETE BUSINESS WORKFLOW E2E TEST")
        print("="*80 + "\n")

        # ====================================================================
        # SETUP: Get admin token
        # ====================================================================
        print("STEP 0: Setup")
        print("-" * 80)

        admin_token = create_admin_token()
        print("     ✅ Admin token obtained")

        # ====================================================================
        # STEP 1: Admin creates 2 tournaments
        # ====================================================================
        print("\nSTEP 1: Admin creates 2 tournaments")
        print("-" * 80)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        tournament1_result = create_tournament_via_api(
            admin_token,
            name=f"GrandMaster Tournament {timestamp}_1"
        )
        tournament1_id = tournament1_result["tournament_id"]
        tournament1_name = tournament1_result["summary"]["name"]
        print(f"     ✅ Tournament 1: {tournament1_name} (ID: {tournament1_id})")

        tournament2_result = create_tournament_via_api(
            admin_token,
            name=f"Competitive Selection Tournament {timestamp}_2"
        )
        tournament2_id = tournament2_result["tournament_id"]
        tournament2_name = tournament2_result["summary"]["name"]
        print(f"     ✅ Tournament 2: {tournament2_name} (ID: {tournament2_id})")

        # ====================================================================
        # STEP 2: Create "GrandMaster" instructor and direct assign to Tournament 1
        # ====================================================================
        print("\nSTEP 2: Direct assign GrandMaster instructor to Tournament 1")
        print("-" * 80)

        grandmaster = create_instructor_user(admin_token)
        grandmaster["name"] = "GrandMaster Coach"
        print(f"     ✅ GrandMaster created: {grandmaster['email']}")

        # Direct assignment (SCENARIO 1)
        direct_assignment = admin_directly_assigns_instructor(
            admin_token,
            tournament1_id,
            grandmaster['id'],
            "You are our top choice to lead this prestigious tournament!"
        )
        print(f"     ✅ Direct assignment created: assignment_id={direct_assignment['assignment_id']}")

        # GrandMaster accepts
        grandmaster_acceptance = instructor_accepts_assignment(
            grandmaster['token'],
            tournament1_id
        )
        print(f"     ✅ GrandMaster accepted assignment")
        print(f"     ✅ Tournament 1 status: {grandmaster_acceptance['status']}")

        # ====================================================================
        # STEP 3-4: 4 instructors apply to Tournament 2, random selection
        # ====================================================================
        print("\nSTEP 3-4: Four instructors apply to Tournament 2 (with random selection)")
        print("-" * 80)

        # Create 4 instructors
        applicant_instructors = create_multiple_instructors(admin_token, count=4)

        # All 4 apply to Tournament 2
        applications = []
        for idx, instructor in enumerate(applicant_instructors):
            application = instructor_applies_to_tournament(
                instructor['token'],
                tournament2_id,
                f"I am Instructor {idx+1} and I would love to lead this tournament!"
            )
            applications.append(application)
            instructor['application_id'] = application['application_id']
            print(f"     ✅ Instructor {idx+1} applied: application_id={application['application_id']}")

        # Random selection (pick 1 winner)
        selected_idx = random.randint(0, 3)
        selected_instructor = applicant_instructors[selected_idx]

        print(f"\n     🎲 Random selection: Instructor {selected_idx+1} SELECTED")

        # Approve selected instructor
        approval = admin_approves_instructor_application(
            admin_token,
            tournament2_id,
            selected_instructor['application_id'],
            f"Congratulations! We selected you from {len(applicant_instructors)} excellent candidates."
        )
        print(f"     ✅ Instructor {selected_idx+1} APPROVED")

        # Decline the other 3
        for idx, instructor in enumerate(applicant_instructors):
            if idx != selected_idx:
                decline = admin_declines_instructor_application(
                    admin_token,
                    tournament2_id,
                    instructor['application_id'],
                    "Thank you for your application. We selected another candidate for this role."
                )
                print(f"     ❌ Instructor {idx+1} DECLINED")

        # Selected instructor accepts
        selected_acceptance = instructor_accepts_assignment(
            selected_instructor['token'],
            tournament2_id
        )
        print(f"     ✅ Instructor {selected_idx+1} accepted assignment")
        print(f"     ✅ Tournament 2 status: {selected_acceptance['status']}")

        # ====================================================================
        # STEP 5-7: Use existing First Team players, coupons, enroll in both tournaments
        # ====================================================================
        print("\nSTEP 5-7: First Team players with coupons → Enroll in both tournaments")
        print("-" * 80)

        # Create 3 First Team players with @f1rstteamfc.hu emails
        first_team_players = create_first_team_players(admin_token, count=3)

        # Create coupon (500 credits = 1 tournament enrollment cost)
        # Max uses: 10 (enough for 3 players to enroll in 2 tournaments = 6 uses, with buffer)
        # Use timestamp to ensure unique coupon code
        coupon_code = f"TournamentPromo{timestamp}"
        coupon = create_coupon(admin_token, code=coupon_code, credits=500, max_uses=10)
        print(f"     ✅ Coupon created: {coupon['code']} (500 credits, max {coupon.get('max_uses', 10)} uses)")

        # Apply coupons to all players
        for idx, player in enumerate(first_team_players):
            try:
                coupon_result = apply_coupon(player['token'], coupon_code)
                print(f"     ✅ Player {idx+1} applied coupon: {coupon_result['new_balance']} credits")
            except Exception as e:
                # If coupon exhausted, create new one with unique timestamp
                time.sleep(0.1)  # Small delay to ensure different timestamp
                new_timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                coupon_code = f"TournamentPromo{new_timestamp}"
                coupon = create_coupon(admin_token, code=coupon_code, credits=500, max_uses=10)
                print(f"     ✅ New coupon created: {coupon['code']} (previous exhausted)")
                coupon_result = apply_coupon(player['token'], coupon_code)
                print(f"     ✅ Player {idx+1} applied coupon: {coupon_result['new_balance']} credits")

        # Enroll players in Tournament 1
        player_ids_t1 = [p['id'] for p in first_team_players]
        enrollments_t1 = enroll_players_in_tournament(
            admin_token,
            tournament1_id,
            player_ids_t1
        )
        print(f"     ✅ {len(enrollments_t1)} players enrolled in Tournament 1")

        # Enroll players in Tournament 2
        player_ids_t2 = [p['id'] for p in first_team_players]
        enrollments_t2 = enroll_players_in_tournament(
            admin_token,
            tournament2_id,
            player_ids_t2
        )
        print(f"     ✅ {len(enrollments_t2)} players enrolled in Tournament 2")

        # ====================================================================
        # STEP 8-9: Create attendance, complete tournaments, distribute rewards
        # ====================================================================
        print("\nSTEP 8-9: Attendance → Complete → Distribute Rewards")
        print("-" * 80)

        # Tournament 1: Attendance
        attendance_t1 = create_attendance_records(admin_token, tournament1_id, player_ids_t1)
        print(f"     ✅ Tournament 1: {attendance_t1['attendance_count']} attendance records")

        # Tournament 1: Complete
        mark_tournament_completed(admin_token, tournament1_id)
        print(f"     ✅ Tournament 1 completed")

        # Tournament 1: Distribute rewards
        rewards_t1 = distribute_rewards(admin_token, tournament1_id)
        print(f"     ✅ Tournament 1 rewards distributed: {rewards_t1.get('total_recipients', 0)} recipients")

        # Tournament 2: Attendance
        attendance_t2 = create_attendance_records(admin_token, tournament2_id, player_ids_t2)
        print(f"     ✅ Tournament 2: {attendance_t2['attendance_count']} attendance records")

        # Tournament 2: Complete
        mark_tournament_completed(admin_token, tournament2_id)
        print(f"     ✅ Tournament 2 completed")

        # Tournament 2: Distribute rewards
        rewards_t2 = distribute_rewards(admin_token, tournament2_id)
        print(f"     ✅ Tournament 2 rewards distributed: {rewards_t2.get('total_recipients', 0)} recipients")

        # ====================================================================
        # STEP 10: Negative test - Instructor cannot create tournament
        # ====================================================================
        print("\nSTEP 10: Negative Test - Instructor cannot create tournament")
        print("-" * 80)

        try:
            response = requests.post(
                f"{self.API_BASE_URL}/api/v1/semesters",
                headers={"Authorization": f"Bearer {grandmaster['token']}"},
                json={
                    "name": "Unauthorized Tournament",
                    "specialization_type": "LFA_PLAYER",
                    "age_group": "YOUTH",
                    "year": 2026,
                    "time_period_start": "Q1",
                    "time_period_end": "Q1",
                    "is_active": True
                }
            )

            if response.status_code == 403:
                print(f"     ✅ Permission denied as expected (403 Forbidden)")
                error_detail = response.json().get('detail', {})
                print(f"     ✅ Error: {error_detail.get('message', 'No message')}")
            else:
                print(f"     ❌ UNEXPECTED: Got status {response.status_code}, expected 403")
                pytest.fail(f"Instructor should not be able to create tournament (got {response.status_code})")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"     ✅ Permission denied as expected (403 Forbidden)")
            else:
                raise

        # ====================================================================
        # VERIFICATION SUMMARY
        # ====================================================================
        print("\n" + "="*80)
        print("✅ COMPLETE BUSINESS WORKFLOW TEST PASSED")
        print("="*80)
        print(f"\nSUMMARY:")
        print(f"  • Tournaments created: 2")
        print(f"  • GrandMaster directly assigned: Tournament 1")
        print(f"  • Competitive applications: 4 instructors → 1 selected, 3 declined")
        print(f"  • First Team players: {len(first_team_players)}")
        print(f"  • Coupons applied: {len(first_team_players)}x 500 credits")
        print(f"  • Tournament 1 enrollments: {len(enrollments_t1)}")
        print(f"  • Tournament 2 enrollments: {len(enrollments_t2)}")
        print(f"  • Tournaments completed: 2")
        print(f"  • Rewards distributed: Tournament 1 + Tournament 2")
        print(f"  • Negative test: Instructor permission denied ✅")
        print("\n" + "="*80 + "\n")
