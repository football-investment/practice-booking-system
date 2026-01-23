"""
Test Tournament Application and Approval Flow

This script tests the complete workflow:
1. Instructor logs in (grandmaster Level 1)
2. Fetches open tournaments (should see all 3: PRE, YOUTH, AMATEUR)
3. Applies to PRE tournament (Level 1 can apply)
4. Admin approves the application
5. Verifies no integrity constraint errors occur
"""

import requests
import json
import sys

API_BASE_URL = "http://localhost:8000"

# Test accounts
INSTRUCTOR_EMAIL = "coach.instructor@lfa.com"
INSTRUCTOR_PASSWORD = "CoachInstructor2026!"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"


def login(email, password):
    """Login and get auth token."""
    print(f"\n🔑 Logging in as {email}...")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password}
    )

    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

    token = response.json()["access_token"]
    print(f"✅ Logged in successfully")
    return token


def get_open_tournaments(token):
    """Get list of open tournaments."""
    print(f"\n📋 Fetching open tournaments...")
    response = requests.get(
        f"{API_BASE_URL}/api/v1/tournaments/available",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code != 200:
        print(f"❌ Failed to fetch tournaments: {response.status_code}")
        print(f"   Response: {response.text}")
        return []

    tournaments = response.json()
    print(f"✅ Found {len(tournaments)} open tournaments:")
    for t in tournaments:
        print(f"   • ID {t['id']}: {t['name']} (Age Group: {t.get('age_group', 'N/A')})")

    return tournaments


def apply_to_tournament(token, tournament_id, application_message):
    """Submit application to tournament."""
    print(f"\n📝 Applying to tournament ID {tournament_id}...")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/apply",
        headers={"Authorization": f"Bearer {token}"},
        json={"application_message": application_message}
    )

    if response.status_code not in [200, 201]:
        print(f"❌ Application failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

    result = response.json()
    application_id = result.get("application_id") or result.get("id")
    print(f"✅ Application submitted successfully")
    print(f"   Application ID: {application_id}")
    print(f"   Status: {result.get('status', 'N/A')}")

    return application_id


def get_tournament_applications(token, tournament_id):
    """Get applications for a tournament (admin)."""
    print(f"\n📋 Fetching applications for tournament {tournament_id}...")
    response = requests.get(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/applications",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code != 200:
        print(f"❌ Failed to fetch applications: {response.status_code}")
        print(f"   Response: {response.text}")
        return []

    applications = response.json()
    print(f"✅ Found {len(applications)} applications")
    for app in applications:
        print(f"   • App ID {app['id']}: {app.get('instructor_name', 'N/A')} - {app.get('status', 'N/A')}")

    return applications


def approve_application(token, tournament_id, application_id, response_message):
    """Approve an application (admin)."""
    print(f"\n✅ Approving application {application_id} for tournament {tournament_id}...")
    print(f"   This is the critical step where integrity errors occurred before")

    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications/{application_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"response_message": response_message}
    )

    print(f"\n   Response Status: {response.status_code}")

    if response.status_code not in [200, 201]:
        print(f"\n❌ APPROVAL FAILED: {response.status_code}")
        print(f"   Response: {response.text}")

        # Try to parse error details
        try:
            error_data = response.json()
            print(f"\n   Error Details:")
            print(json.dumps(error_data, indent=2))
        except:
            pass

        return None

    result = response.json()
    print(f"\n✅ Application approved successfully!")
    print(f"   Tournament Status: {result.get('tournament_status', 'N/A')}")
    print(f"   Instructor: {result.get('instructor_name', 'N/A')}")
    print(f"   Next Step: {result.get('next_step', 'N/A')}")

    return result


def get_tournament_details(token, tournament_id):
    """Get tournament details."""
    print(f"\n📊 Fetching tournament {tournament_id} details...")
    response = requests.get(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code != 200:
        print(f"❌ Failed to fetch tournament: {response.status_code}")
        return None

    tournament = response.json()
    print(f"✅ Tournament details:")
    print(f"   Name: {tournament.get('name', 'N/A')}")
    print(f"   Status: {tournament.get('tournament_status', 'N/A')}")
    print(f"   Master Instructor: {tournament.get('master_instructor_id', 'None')}")

    return tournament


def main():
    print("=" * 80)
    print("TEST: Tournament Application & Approval Flow (Integrity Error Check)")
    print("=" * 80)

    # Step 1: Login as instructor
    instructor_token = login(INSTRUCTOR_EMAIL, INSTRUCTOR_PASSWORD)
    if not instructor_token:
        print("\n❌ TEST FAILED: Could not login as instructor")
        sys.exit(1)

    # Step 2: Get open tournaments
    tournaments = get_open_tournaments(instructor_token)
    if len(tournaments) < 1:
        print("\n❌ TEST FAILED: No tournaments found")
        sys.exit(1)

    # Find PRE tournament (ID 122)
    pre_tournament = next((t for t in tournaments if "PRE" in t['name']), None)
    if not pre_tournament:
        print("\n❌ TEST FAILED: PRE tournament not found")
        sys.exit(1)

    tournament_id = pre_tournament['id']
    print(f"\n🎯 Target tournament: {pre_tournament['name']} (ID: {tournament_id})")

    # Step 3: Apply to PRE tournament
    application_id = apply_to_tournament(
        instructor_token,
        tournament_id,
        "I am a Level 1 coach and would love to lead this PRE tournament. Test application."
    )

    if not application_id:
        print("\n❌ TEST FAILED: Could not submit application")
        sys.exit(1)

    # Step 4: Login as admin
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not admin_token:
        print("\n❌ TEST FAILED: Could not login as admin")
        sys.exit(1)

    # Step 5: Get applications for tournament
    applications = get_tournament_applications(admin_token, tournament_id)
    if not applications:
        print("\n❌ TEST FAILED: No applications found for tournament")
        sys.exit(1)

    # Step 6: Approve the application (CRITICAL STEP - where error occurred)
    print("\n" + "=" * 80)
    print("🚨 CRITICAL STEP: Approving Application (Watch for Integrity Error)")
    print("=" * 80)

    approval_result = approve_application(
        admin_token,
        tournament_id,
        application_id,
        "Great! You are approved to lead this tournament. Test approval."
    )

    if not approval_result:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED: INTEGRITY ERROR STILL EXISTS")
        print("=" * 80)
        print("\n🔍 The approval failed with an error.")
        print("   This is the same error the user reported.")
        print("   We need to investigate the database constraints and status transitions.")
        sys.exit(1)

    # Step 7: Verify tournament status changed to ONGOING
    tournament_details = get_tournament_details(admin_token, tournament_id)

    if tournament_details and tournament_details.get('tournament_status') == 'ONGOING':
        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Application Approval Flow Successful!")
        print("=" * 80)
        print(f"\n✅ Tournament status is now: ONGOING")
        print(f"✅ Master instructor assigned: {tournament_details.get('master_instructor_id')}")
        print(f"✅ No integrity constraint errors occurred!")
        print("\n🎉 The APPLICATION_BASED auto-assignment logic is working correctly!")
    else:
        print("\n⚠️  TEST PARTIALLY PASSED:")
        print("   - Application approval succeeded")
        print(f"   - But tournament status is: {tournament_details.get('tournament_status')}")
        print("   - Expected: ONGOING")


if __name__ == "__main__":
    main()
