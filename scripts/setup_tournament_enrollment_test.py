"""
Setup Tournament Enrollment E2E Test Environment
================================================

This script creates a complete test environment for tournament enrollment:
1. Resets existing test player (Péter)
2. Sets up complete player profile with 600 credits
3. Creates tournament via API
4. Creates instructor and assigns to tournament
5. Instructor accepts assignment
6. Opens enrollment for players

Usage:
    python scripts/setup_tournament_enrollment_test.py
"""

import requests
from datetime import datetime, date, timedelta
import sys
import random

    import subprocess

    # Update user profile
    import psycopg2
        import traceback
API_BASE = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

# Test player details
PLAYER_EMAIL = "pwt.p3t1k3@f1stteam.hu"
PLAYER_PASSWORD = "password123"
PLAYER_NAME = "Péter Pataki"
PLAYER_DOB = "2009-08-20"  # 16 years old
PLAYER_GENDER = "MALE"
CREDITS_TO_ADD = 600  # Tournament enrollment requires credits


def print_step(step: str):
    """Print formatted step"""
    print(f"\n{'='*80}")
    print(f"🔧 {step}")
    print('='*80)


def print_success(msg: str):
    """Print success message"""
    print(f"   ✅ {msg}")


def print_error(msg: str):
    """Print error message"""
    print(f"   ❌ {msg}")


def get_admin_token() -> str:
    """Get admin authentication token"""
    print_step("STEP 1: Admin Login")

    response = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )

    if response.status_code != 200:
        print_error(f"Admin login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)

    token = response.json()["access_token"]
    print_success(f"Admin logged in successfully")
    return token


def reset_player_via_db():
    """Reset player user via direct DB access"""
    print_step("STEP 2: Reset Player User (Database)")

    sql = """
    -- Reset user
    UPDATE users
    SET specialization = NULL,
        onboarding_completed = false,
        date_of_birth = NULL
    WHERE email = '{email}';

    -- Delete license
    DELETE FROM user_licenses
    WHERE user_id = (SELECT id FROM users WHERE email = '{email}');

    -- Delete semester enrollments
    DELETE FROM semester_enrollments
    WHERE user_id = (SELECT id FROM users WHERE email = '{email}');

    -- Verify
    SELECT id, email, specialization, onboarding_completed, date_of_birth
    FROM users WHERE email = '{email}';
    """.format(email=PLAYER_EMAIL)

    result = subprocess.run(
        ["psql", "-U", "postgres", "-h", "localhost", "-d", "lfa_intern_system", "-c", sql],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print_success(f"Player user reset: {PLAYER_EMAIL}")
        print(f"   {result.stdout.strip()}")
    else:
        print_error(f"Database reset failed: {result.stderr}")
        sys.exit(1)


def complete_onboarding() -> dict:
    """Complete player onboarding via database (no API endpoint exists)"""
    print_step("STEP 3: Complete Onboarding")

    print("   📝 Updating user profile...")
    sql = f"""
    UPDATE users
    SET
        date_of_birth = '{PLAYER_DOB}',
        specialization = 'LFA_FOOTBALL_PLAYER',
        onboarding_completed = true
    WHERE email = '{PLAYER_EMAIL}';

    SELECT id, email, name, date_of_birth, specialization, onboarding_completed
    FROM users WHERE email = '{PLAYER_EMAIL}';
    """

    result = subprocess.run(
        ["psql", "-U", "postgres", "-h", "localhost", "-d", "lfa_intern_system", "-c", sql],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print_error(f"User profile update failed: {result.stderr}")
        sys.exit(1)

    print_success(f"User profile updated")
    print(f"   {result.stdout.strip()}")

    # Create user license
    print("   💼 Creating user license...")
    sql = f"""
    -- Delete existing license if any
    DELETE FROM user_licenses WHERE user_id = (SELECT id FROM users WHERE email = '{PLAYER_EMAIL}');

    -- Insert new license
    INSERT INTO user_licenses (
        user_id,
        specialization_type,
        current_level,
        max_achieved_level,
        started_at,
        payment_verified,
        onboarding_completed,
        is_active,
        renewal_cost,
        credit_balance,
        credit_purchased,
        created_at,
        updated_at
    ) VALUES (
        (SELECT id FROM users WHERE email = '{PLAYER_EMAIL}'),
        'LFA_FOOTBALL_PLAYER',
        1,
        1,
        NOW(),
        true,
        true,
        true,
        0,
        {CREDITS_TO_ADD},
        {CREDITS_TO_ADD},
        NOW(),
        NOW()
    );

    SELECT ul.id, ul.user_id, ul.specialization_type, ul.current_level, ul.credit_balance, ul.is_active
    FROM user_licenses ul
    WHERE ul.user_id = (SELECT id FROM users WHERE email = '{PLAYER_EMAIL}');
    """

    result = subprocess.run(
        ["psql", "-U", "postgres", "-h", "localhost", "-d", "lfa_intern_system", "-c", sql],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print_error(f"License creation failed: {result.stderr}")
        sys.exit(1)

    print_success(f"License created")
    print(f"   {result.stdout.strip()}")

    print_success(f"Onboarding completed")
    print(f"   - Name: {PLAYER_NAME}")
    print(f"   - DOB: {PLAYER_DOB} (Age: {datetime.now().year - 2009})")
    print(f"   - Gender: {PLAYER_GENDER}")
    print(f"   - Specialization: LFA_FOOTBALL_PLAYER")
    print(f"   - Credits: {CREDITS_TO_ADD}")

    return {"user_data": {"email": PLAYER_EMAIL}}


def create_tournament(admin_token: str) -> dict:
    """Create tournament via API"""
    print_step("STEP 4: Create Tournament")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Try multiple dates to avoid conflicts
    for attempt in range(10):
        today = datetime.now().date()
        # Use NEAR future date (7-30 days) to fit in default date filter
        future_days = random.randint(7, 30)
        future_date = today + timedelta(days=future_days)

        tournament_data = {
            "date": future_date.isoformat(),
            "name": f"E2E Test Tournament {timestamp}",
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "age_group": "AMATEUR",
            "reward_policy_name": "default",
            "sessions": [
                {"time": "10:00", "title": "Morning Game", "duration_minutes": 90, "capacity": 20},
                {"time": "14:00", "title": "Afternoon Game", "duration_minutes": 90, "capacity": 20},
                {"time": "18:00", "title": "Evening Finals", "duration_minutes": 90, "capacity": 16}
            ],
            "campus_id": 1,
            "location_id": 1,
            "auto_book_students": False
        }

        print(f"   🎯 Attempt {attempt + 1}/10: Creating tournament for {future_date}...")

        response = requests.post(
            f"{API_BASE}/tournaments/generate",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=tournament_data
        )

        if response.status_code in [200, 201]:
            result = response.json()
            tournament_id = result.get("tournament_id")
            tournament_name = result.get("summary", {}).get("name")
            tournament_code = result.get("summary", {}).get("code")

            print_success(f"Tournament created!")
            print(f"   - ID: {tournament_id}")
            print(f"   - Name: {tournament_name}")
            print(f"   - Code: {tournament_code}")
            print(f"   - Date: {future_date}")

            return {
                "tournament_id": tournament_id,
                "tournament_name": tournament_name,
                "tournament_code": tournament_code,
                "date": future_date.isoformat()
            }
        elif response.status_code == 409:
            print(f"   ⚠️  Conflict on {future_date}, trying next date...")
            continue
        else:
            print_error(f"Tournament creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            if attempt == 9:
                sys.exit(1)

    print_error("Failed to create tournament after 10 attempts")
    sys.exit(1)


def create_instructor(admin_token: str) -> dict:
    """Create instructor user via API"""
    print_step("STEP 5: Create Instructor")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

    instructor_data = {
        "email": f"tournament_instructor_{timestamp}@test.com",
        "name": f"Tournament Instructor {timestamp}",
        "password": "InstructorPass123!",
        "role": "instructor",
        "date_of_birth": "1985-01-01T00:00:00",
        "specialization": "LFA_COACH"
    }

    response = requests.post(
        f"{API_BASE}/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=instructor_data
    )

    if response.status_code != 200:
        print_error(f"Instructor creation failed: {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)

    instructor = response.json()
    instructor_id = instructor["id"]
    instructor_email = instructor["email"]

    print_success(f"Instructor created")
    print(f"   - ID: {instructor_id}")
    print(f"   - Email: {instructor_email}")

    # Activate and create license via database
    print("   💼 Activating instructor and creating license...")

    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    cur = conn.cursor()

    # 1. Activate user
    cur.execute("UPDATE users SET is_active = true WHERE id = %s", (instructor_id,))

    # 2. Insert LFA_COACH license
    cur.execute(
        """
        INSERT INTO user_licenses (
            user_id, specialization_type, current_level, max_achieved_level,
            started_at, payment_verified, is_active, onboarding_completed,
            payment_verified_at, renewal_cost, credit_balance, credit_purchased
        )
        VALUES (%s, 'LFA_COACH', 1, 1, NOW(), true, true, true, NOW(), 0, 0, 0)
        RETURNING id
        """,
        (instructor_id,)
    )
    license_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    print_success(f"Instructor license created (ID: {license_id})")

    # Get instructor token
    login_response = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": instructor_email, "password": instructor_data["password"]}
    )

    if login_response.status_code != 200:
        print_error(f"Instructor login failed")
        sys.exit(1)

    instructor_token = login_response.json()["access_token"]

    return {
        "instructor_id": instructor_id,
        "instructor_email": instructor_email,
        "instructor_token": instructor_token
    }


def assign_and_accept_instructor(admin_token: str, tournament_id: int, instructor_data: dict) -> dict:
    """Assign instructor to tournament and accept assignment"""
    print_step("STEP 6: Assign and Accept Instructor")

    instructor_id = instructor_data["instructor_id"]
    instructor_token = instructor_data["instructor_token"]

    # Direct assign instructor via API
    print("   📝 Admin assigning instructor to tournament...")
    assign_response = requests.post(
        f"{API_BASE}/tournaments/{tournament_id}/direct-assign-instructor",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"instructor_id": instructor_id}
    )

    if assign_response.status_code != 200:
        print_error(f"Assignment failed: {assign_response.status_code}")
        print(f"   Response: {assign_response.text}")
        sys.exit(1)

    print_success(f"Instructor assigned to tournament")

    # Instructor accepts assignment
    print("   ✅ Instructor accepting assignment...")

    accept_response = requests.post(
        f"{API_BASE}/tournaments/{tournament_id}/instructor-assignment/accept",
        headers={"Authorization": f"Bearer {instructor_token}"}
    )

    if accept_response.status_code != 200:
        print_error(f"Accept failed: {accept_response.status_code}")
        print(f"   Response: {accept_response.text}")
        sys.exit(1)

    print_success(f"Instructor accepted assignment")

    # Verify status is INSTRUCTOR_CONFIRMED
    status_response = requests.get(
        f"{API_BASE}/semesters/{tournament_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if status_response.status_code == 200:
        current_status = status_response.json().get("tournament_status")
        print(f"   ℹ️  Tournament status: {current_status}")

        if current_status != "INSTRUCTOR_CONFIRMED":
            print_error(f"Expected INSTRUCTOR_CONFIRMED, got {current_status}")
            sys.exit(1)

    return {"status": "INSTRUCTOR_CONFIRMED"}


def open_enrollment(admin_token: str, tournament_id: int) -> dict:
    """Open enrollment for tournament (optional - can be done via UI test)"""
    print_step("STEP 7: Open Enrollment (Optional)")

    print("   ℹ️  Enrollment can be opened via:")
    print("      1. UI test (admin clicks 'Open Enrollment' button)")
    print("      2. API call (coming next...)")

    # TODO: Add API call to open enrollment if endpoint exists
    # For now, this will be done in the UI test

    print_success(f"Setup complete - Ready for UI enrollment test!")

    return {"ready": True}


def verify_setup(tournament_data: dict):
    """Verify complete setup"""
    print_step("STEP 8: Verify Setup")

    # Login as player
    login_response = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": PLAYER_EMAIL, "password": PLAYER_PASSWORD}
    )

    if login_response.status_code != 200:
        print_error(f"Verification login failed")
        return False

    player_token = login_response.json()["access_token"]

    # Get user info
    me_response = requests.get(
        f"{API_BASE}/users/me",
        headers={"Authorization": f"Bearer {player_token}"}
    )

    if me_response.status_code != 200:
        print_error(f"Failed to get user info")
        return False

    user = me_response.json()

    # Check all required fields
    checks = {
        "Email": user.get("email") == PLAYER_EMAIL,
        "Name": user.get("name") == PLAYER_NAME,
        "Date of Birth": user.get("date_of_birth") is not None,
        "Specialization": user.get("specialization") == "LFA_FOOTBALL_PLAYER",
        "Onboarding": user.get("onboarding_completed") == True,
    }

    all_passed = all(checks.values())

    for check, passed in checks.items():
        if passed:
            print_success(f"{check}: OK")
        else:
            print_error(f"{check}: FAILED")

    # Check license
    license_response = requests.get(
        f"{API_BASE}/licenses/me",
        headers={"Authorization": f"Bearer {player_token}"}
    )

    if license_response.status_code == 200:
        licenses = license_response.json()
        if licenses:
            license = licenses[0]
            balance = license.get("credit_balance", 0)
            print_success(f"License Credits: {balance}")
        else:
            print_error(f"No license found")
            all_passed = False

    # Print tournament info
    print("\n   🏆 Tournament Ready:")
    print(f"      - ID: {tournament_data['tournament_id']}")
    print(f"      - Name: {tournament_data['tournament_name']}")
    print(f"      - Code: {tournament_data['tournament_code']}")
    print(f"      - Date: {tournament_data['date']}")

    return all_passed


def main():
    """Main setup flow"""
    print("\n" + "="*80)
    print("🎭 TOURNAMENT ENROLLMENT E2E TEST SETUP")
    print("="*80)
    print(f"\nPlayer: {PLAYER_EMAIL}")
    print(f"Specialization: LFA_FOOTBALL_PLAYER")
    print(f"Credits: {CREDITS_TO_ADD}")

    try:
        # Step 1: Admin login
        admin_token = get_admin_token()

        # Step 2: Reset player
        reset_player_via_db()

        # Step 3: Complete onboarding
        player_data = complete_onboarding()

        # Step 4: Create tournament
        tournament_data = create_tournament(admin_token)

        # Step 5: Create instructor
        instructor_data = create_instructor(admin_token)

        # Step 6: Assign and accept instructor
        assignment_data = assign_and_accept_instructor(
            admin_token,
            tournament_data["tournament_id"],
            instructor_data
        )

        # Step 7: Open enrollment (optional - can be done in UI test)
        open_enrollment(admin_token, tournament_data["tournament_id"])

        # Step 8: Verify
        if verify_setup(tournament_data):
            print("\n" + "="*80)
            print("✅ SETUP COMPLETE - Ready for Tournament Enrollment E2E Test!")
            print("="*80)
            print(f"\n📋 Test Details:")
            print(f"   Player Email: {PLAYER_EMAIL}")
            print(f"   Player Password: {PLAYER_PASSWORD}")
            print(f"   Player Credits: {CREDITS_TO_ADD}")
            print(f"\n   Tournament ID: {tournament_data['tournament_id']}")
            print(f"   Tournament Code: {tournament_data['tournament_code']}")
            print(f"   Tournament Status: INSTRUCTOR_CONFIRMED")
            print(f"\n   Instructor Email: {instructor_data['instructor_email']}")
            print("\n🎯 Next Steps:")
            print("   1. Admin opens enrollment via UI (or API)")
            print("   2. Player can see and enroll in tournament")
            print("   3. Credits deducted on enrollment")
            print("="*80 + "\n")
            return 0
        else:
            print("\n" + "="*80)
            print("❌ SETUP INCOMPLETE - Some checks failed")
            print("="*80 + "\n")
            return 1

    except Exception as e:
        print_error(f"Setup failed: {str(e)}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
