"""
Create Additional Instructors for Tournament Tests

Creates 3 additional instructor users (besides Grandmaster):
1. Senior Instructor
2. Junior Instructor
3. Coach Instructor

These instructors can apply to APPLICATION_BASED tournaments.
"""

import requests
import sys
import psycopg2
from datetime import datetime

API_BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

# Instructor credentials
INSTRUCTORS = [
    {
        "email": "senior.instructor@lfa.com",
        "password": "SeniorInstructor2026!",
        "name": "Senior Instructor",
        "role": "instructor",
        "date_of_birth": "1980-03-15T00:00:00"
    },
    {
        "email": "junior.instructor@lfa.com",
        "password": "JuniorInstructor2026!",
        "name": "Junior Instructor",
        "role": "instructor",
        "date_of_birth": "1995-07-22T00:00:00"
    },
    {
        "email": "coach.instructor@lfa.com",
        "password": "CoachInstructor2026!",
        "name": "Coach Instructor",
        "role": "instructor",
        "date_of_birth": "1988-11-10T00:00:00"
    }
]


def get_admin_token():
    """Get admin authentication token."""
    print(f"\n🔑 Authenticating as admin...")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )

    if response.status_code != 200:
        print(f"❌ Admin login failed: {response.status_code} {response.text}")
        sys.exit(1)

    token = response.json()["access_token"]
    print(f"✅ Admin authenticated")
    return token


def create_instructor_via_api(token, instructor_data):
    """Create an instructor via admin API."""
    print(f"\n📝 Creating instructor: {instructor_data['email']}...")

    response = requests.post(
        f"{API_BASE_URL}/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json=instructor_data
    )

    if response.status_code == 400 and "already exists" in response.text:
        print(f"⚠️  User {instructor_data['email']} already exists. Skipping creation.")

        # Try to get user info by logging in
        login_response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": instructor_data["email"], "password": instructor_data["password"]}
        )

        if login_response.status_code == 200:
            user_token = login_response.json()["access_token"]
            profile_response = requests.get(
                f"{API_BASE_URL}/api/v1/users/me",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            if profile_response.status_code == 200:
                return profile_response.json()

        return None

    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create instructor: {response.status_code} {response.text}")
        return None

    user = response.json()
    print(f"✅ Instructor created: {user['email']} (id={user['id']})")
    return user


def add_lfa_coach_license(user_id, user_email):
    """Add LFA_COACH license to instructor via direct DB insert."""
    print(f"📝 Adding LFA_COACH license for {user_email}...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Check if license already exists
        cur.execute("""
            SELECT id FROM user_licenses
            WHERE user_id = %s AND specialization_type = 'LFA_COACH'
        """, (user_id,))
        existing = cur.fetchone()

        if existing:
            # Update existing license
            cur.execute("""
                UPDATE user_licenses
                SET is_active = true,
                    payment_verified = true,
                    onboarding_completed = true,
                    payment_verified_at = NOW(),
                    current_level = 5,
                    max_achieved_level = 5
                WHERE user_id = %s AND specialization_type = 'LFA_COACH'
            """, (user_id,))
            print(f"✅ LFA_COACH license updated (level 5)")
        else:
            # Insert new license
            cur.execute("""
                INSERT INTO user_licenses (
                    user_id, specialization_type, current_level, max_achieved_level,
                    started_at, is_active, payment_verified, onboarding_completed,
                    payment_verified_at, renewal_cost, credit_balance, credit_purchased
                )
                VALUES (%s, 'LFA_COACH', 5, 5, NOW(), true, true, true, NOW(), 0, 0, 0)
            """, (user_id,))
            print(f"✅ LFA_COACH license created (level 5)")

        # Give instructor 3000 credits
        cur.execute("""
            UPDATE users
            SET credit_balance = 3000
            WHERE id = %s
        """, (user_id,))
        print(f"✅ 3000 credits added to {user_email}")

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Failed to add license: {e}")
        return False

    return True


def main():
    print("="*80)
    print("CREATE ADDITIONAL INSTRUCTORS FOR TOURNAMENT TESTS")
    print("="*80)

    # Get admin token
    admin_token = get_admin_token()

    created_instructors = []

    # Create each instructor
    for instructor_data in INSTRUCTORS:
        user = create_instructor_via_api(admin_token, instructor_data)

        if user:
            # Add LFA_COACH license
            success = add_lfa_coach_license(user["id"], user["email"])

            if success:
                created_instructors.append({
                    "id": user["id"],
                    "email": user["email"],
                    "name": instructor_data["name"],
                    "password": instructor_data["password"]
                })

    # Summary
    print("\n" + "="*80)
    print("✅ INSTRUCTOR CREATION COMPLETE")
    print("="*80)

    print(f"\n📋 Created {len(created_instructors)} instructors:\n")

    for instructor in created_instructors:
        print(f"   {instructor['name']}:")
        print(f"      Email: {instructor['email']}")
        print(f"      Password: {instructor['password']}")
        print(f"      ID: {instructor['id']}")
        print()

    print("🎯 These instructors can now:")
    print("   - Apply to APPLICATION_BASED tournaments")
    print("   - Be selected for OPEN_ASSIGNMENT tournaments")
    print("   - Access Instructor Dashboard")
    print()


if __name__ == "__main__":
    main()
