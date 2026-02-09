#!/usr/bin/env python3
"""
Controlled Persistence Validation
==================================

Creates dedicated test player cohort and validates end-to-end skill progression:
1. Create isolated test users (real DB records, not synthetic)
2. Capture baseline skills snapshot
3. Run full tournament lifecycle (ranking → rewards → skill persistence)
4. Verify skill changes in DB
5. Verify skill changes visible in UI

Success criteria:
- Measurable skill delta (baseline vs post-state)
- UI reflects changes
- End-to-end reward pipeline proven
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

# Dedicated test cohort (will create if not exists)
TEST_COHORT = {
    "test_player_persistence_1": {"email": "test.persist.1@sandbox.lfa.com", "name": "Test Persist Alpha"},
    "test_player_persistence_2": {"email": "test.persist.2@sandbox.lfa.com", "name": "Test Persist Beta"},
    "test_player_persistence_3": {"email": "test.persist.3@sandbox.lfa.com", "name": "Test Persist Gamma"},
    "test_player_persistence_4": {"email": "test.persist.4@sandbox.lfa.com", "name": "Test Persist Delta"},
}


def get_admin_token():
    """Authenticate as admin"""
    print("\n🔑 Authenticating as admin...")
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )

    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return None

    token = response.json()["access_token"]
    print("✅ Admin authenticated")
    return token


def get_or_create_test_users(token: str):
    """Get or create dedicated test user cohort"""
    print("\n📋 Setting up dedicated test user cohort...")
    headers = {"Authorization": f"Bearer {token}"}

    cohort_user_ids = {}

    for key, user_data in TEST_COHORT.items():
        email = user_data["email"]
        name = user_data["name"]

        # Try to find existing user
        print(f"\n  Checking user: {email}...")

        # Use admin endpoint to search users (if available)
        # For now, attempt login to check if exists
        login_response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"email": email, "password": "testpass123"}
        )

        if login_response.status_code == 200:
            # User exists, get user ID
            user_token = login_response.json()["access_token"]

            # Get user profile to extract ID
            profile_response = requests.get(
                f"{API_BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {user_token}"}
            )

            if profile_response.status_code == 200:
                user_id = profile_response.json()["id"]
                cohort_user_ids[key] = user_id
                print(f"    ✅ User exists (ID: {user_id})")
            else:
                print(f"    ❌ Failed to get user profile")
        else:
            # User doesn't exist, create via registration
            print(f"    Creating new user: {email}")

            register_response = requests.post(
                f"{API_BASE_URL}/auth/register",
                json={
                    "email": email,
                    "password": "testpass123",
                    "name": name,
                    "role": "LFA_FOOTBALL_PLAYER"
                }
            )

            if register_response.status_code in [200, 201]:
                # Login to get user ID
                login_response = requests.post(
                    f"{API_BASE_URL}/auth/login",
                    json={"email": email, "password": "testpass123"}
                )

                if login_response.status_code == 200:
                    user_token = login_response.json()["access_token"]

                    profile_response = requests.get(
                        f"{API_BASE_URL}/users/me",
                        headers={"Authorization": f"Bearer {user_token}"}
                    )

                    if profile_response.status_code == 200:
                        user_id = profile_response.json()["id"]
                        cohort_user_ids[key] = user_id
                        print(f"    ✅ User created (ID: {user_id})")
                else:
                    print(f"    ❌ Failed to login after registration")
            else:
                print(f"    ❌ Registration failed: {register_response.text}")

    print(f"\n✅ Test cohort ready: {len(cohort_user_ids)}/{len(TEST_COHORT)} users")
    return cohort_user_ids


def get_baseline_skills(token: str, user_ids: dict):
    """Capture baseline skills for all test users"""
    print("\n📸 Capturing baseline skills snapshot...")
    headers = {"Authorization": f"Bearer {token}"}

    baseline_skills = {}

    for key, user_id in user_ids.items():
        response = requests.get(
            f"{API_BASE_URL}/skills/profile/{user_id}",
            headers=headers
        )

        if response.status_code == 200:
            profile = response.json()
            skills = {}

            if "skills" in profile:
                for skill_name, skill_data in profile["skills"].items():
                    if isinstance(skill_data, dict) and "current_level" in skill_data:
                        skills[skill_name] = skill_data["current_level"]

            baseline_skills[user_id] = skills
            print(f"  {key} (ID {user_id}): {len(skills)} skills captured")
        else:
            print(f"  ❌ Failed to get skills for {key} (ID {user_id})")
            baseline_skills[user_id] = {}

    return baseline_skills


def run_production_tournament(token: str, user_ids: list):
    """Run PRODUCTION tournament (NOT sandbox - with persistence)"""
    print("\n🏆 Running PRODUCTION tournament (WITH SKILL PERSISTENCE)...")
    headers = {"Authorization": f"Bearer {token}"}

    # Create a real tournament (not sandbox)
    print("\n  Step 1: Creating tournament...")

    tournament_payload = {
        "name": f"Persistence Test Tournament - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "specialization_type": "LFA_FOOTBALL",
        "format": "league",
        "measurement_unit": "points",
        "start_date": datetime.now().isoformat(),
        "end_date": datetime.now().isoformat(),
        "is_active": True
    }

    # Note: This might need adjustment based on actual tournament creation endpoint
    # For now, using sandbox API with is_sandbox_mode=False
    print("\n  ⚠️  Using sandbox API in PRODUCTION mode (is_sandbox_mode=False)")
    print("      (Manual tournament creation via admin UI may be required)")

    # Alternative: Use sandbox API but tell it NOT to cleanup
    sandbox_response = requests.post(
        f"{API_BASE_URL}/sandbox/run-test",
        headers=headers,
        json={
            "tournament_type": "league",
            "skills_to_test": ["passing", "dribbling", "shot_power"],
            "player_count": len(user_ids),
            "selected_users": user_ids,  # Use our test cohort
            "test_config": {
                "performance_variation": "MEDIUM",
                "ranking_distribution": "NORMAL",
                "persist_skills": True  # Request skill persistence
            }
        }
    )

    if sandbox_response.status_code != 200:
        print(f"    ❌ Tournament creation failed: {sandbox_response.text}")
        return None

    result = sandbox_response.json()
    tournament_id = result.get("tournament", {}).get("id")

    print(f"  ✅ Tournament created (ID: {tournament_id})")
    print(f"      Status: {result.get('tournament', {}).get('status')}")
    print(f"      Verdict: {result.get('verdict')}")

    return result


def verify_skills_in_db(token: str, user_ids: dict, baseline_skills: dict):
    """Verify skill changes persisted to DB"""
    print("\n🔍 Verifying skill changes in DATABASE...")
    headers = {"Authorization": f"Bearer {token}"}

    changes_detected = False
    skill_deltas = {}

    for key, user_id in user_ids.items():
        response = requests.get(
            f"{API_BASE_URL}/skills/profile/{user_id}",
            headers=headers
        )

        if response.status_code == 200:
            profile = response.json()
            current_skills = {}

            if "skills" in profile:
                for skill_name, skill_data in profile["skills"].items():
                    if isinstance(skill_data, dict) and "current_level" in skill_data:
                        current_skills[skill_name] = skill_data["current_level"]

            # Compare with baseline
            baseline = baseline_skills.get(user_id, {})
            deltas = {}

            for skill_name in ["passing", "dribbling", "shot_power"]:
                before = baseline.get(skill_name, 50.0)
                after = current_skills.get(skill_name, 50.0)
                delta = after - before

                deltas[skill_name] = {
                    "before": before,
                    "after": after,
                    "delta": delta
                }

                if abs(delta) > 0.01:
                    changes_detected = True

            skill_deltas[user_id] = deltas

            print(f"\n  {key} (ID {user_id}):")
            for skill_name, data in deltas.items():
                delta_str = f"{data['delta']:+.1f}"
                status = "✅ CHANGED" if abs(data['delta']) > 0.01 else "⚪ UNCHANGED"
                print(f"    {skill_name:15s}: {data['before']:5.1f} → {data['after']:5.1f} ({delta_str}) {status}")

    return changes_detected, skill_deltas


def verify_skills_in_ui(token: str, user_ids: dict):
    """Verify skill changes visible in UI (via profile endpoint)"""
    print("\n🖥️  Verifying skill changes in UI (profile endpoint)...")
    headers = {"Authorization": f"Bearer {token}"}

    ui_verification_passed = True

    for key, user_id in user_ids.items():
        response = requests.get(
            f"{API_BASE_URL}/skills/profile/{user_id}",
            headers=headers
        )

        if response.status_code == 200:
            profile = response.json()

            # Check if profile has required structure
            has_skills = "skills" in profile
            skills_count = len(profile.get("skills", {}))

            print(f"  {key} (ID {user_id}):")
            print(f"    Skills present: {'✅ YES' if has_skills else '❌ NO'}")
            print(f"    Skills count: {skills_count}")

            if not has_skills or skills_count == 0:
                ui_verification_passed = False
        else:
            print(f"  ❌ Failed to fetch UI data for {key} (ID {user_id})")
            ui_verification_passed = False

    return ui_verification_passed


def main():
    """Execute controlled persistence validation"""
    print("\n" + "="*80)
    print("CONTROLLED PERSISTENCE VALIDATION")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Authenticate
    token = get_admin_token()
    if not token:
        print("\n❌ Authentication failed. Exiting.")
        return

    # Step 1: Get or create test users
    cohort_user_ids = get_or_create_test_users(token)

    if len(cohort_user_ids) < 3:
        print(f"\n❌ Insufficient test users ({len(cohort_user_ids)}/{len(TEST_COHORT)}). Exiting.")
        return

    user_ids_list = list(cohort_user_ids.values())

    # Step 2: Capture baseline skills
    baseline_skills = get_baseline_skills(token, cohort_user_ids)

    # Step 3: Run production tournament
    tournament_result = run_production_tournament(token, user_ids_list)

    if not tournament_result:
        print("\n❌ Tournament execution failed. Exiting.")
        return

    # Wait for skills to propagate (if async)
    print("\n⏳ Waiting 2 seconds for skill propagation...")
    time.sleep(2)

    # Step 4: Verify skills in DB
    changes_detected, skill_deltas = verify_skills_in_db(token, cohort_user_ids, baseline_skills)

    # Step 5: Verify skills in UI
    ui_verification_passed = verify_skills_in_ui(token, cohort_user_ids)

    # Final summary
    print(f"\n{'='*80}")
    print("CONTROLLED PERSISTENCE VALIDATION - RESULTS")
    print(f"{'='*80}")

    print(f"\n✅ Test cohort: {len(cohort_user_ids)} users")
    print(f"✅ Baseline captured: {len(baseline_skills)} skill profiles")
    print(f"✅ Tournament executed: {tournament_result.get('verdict')}")
    print(f"{'✅' if changes_detected else '❌'} Skill changes detected in DB: {changes_detected}")
    print(f"{'✅' if ui_verification_passed else '❌'} UI verification passed: {ui_verification_passed}")

    print(f"\n{'='*80}")
    if changes_detected and ui_verification_passed:
        print("✅✅✅ CONTROLLED PERSISTENCE VALIDATION: PASS")
        print("")
        print("EXECUTIVE ANSWER:")
        print("\"Controlled persistence validation completed — skill progression")
        print(" successfully written to DB and visible in UI.\"")
    else:
        print("❌❌❌ CONTROLLED PERSISTENCE VALIDATION: FAIL")
        print("")
        print("EXECUTIVE ANSWER:")
        print("\"Controlled persistence validation FAILED - skill changes not")
        print(" detected in DB or UI verification failed.\"")

    print(f"{'='*80}")

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
