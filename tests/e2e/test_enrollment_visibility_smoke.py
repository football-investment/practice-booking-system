"""
Enrollment Visibility Smoke Test

ISOLATED TEST - Does NOT reset database, works with existing state

Tests ONLY the enrollment visibility flow:
1. Tournament in READY_FOR_ENROLLMENT → Player CANNOT see
2. Admin transitions to ENROLLMENT_OPEN → Player CAN see
3. Player browse endpoint returns tournament

This test assumes:
- Database already has tournaments (use after_tournament_creation checkpoint)
- Player user exists (pwt.k1sqx1@f1stteam.hu)
- Admin user exists (admin@lfa.com)
"""

import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


def test_enrollment_visibility_smoke():
    """
    Smoke test: Verify tournament becomes visible to players after ENROLLMENT_OPEN
    """

    print("\n" + "="*80)
    print("🔬 SMOKE TEST: Tournament Enrollment Visibility")
    print("="*80 + "\n")

    # ========================================================================
    # STEP 1: Login as admin
    # ========================================================================
    print("1️⃣  Logging in as admin...")
    admin_response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": "admin@lfa.com", "password": "admin123"}
    )
    assert admin_response.status_code == 200, f"Admin login failed: {admin_response.text}"
    admin_token = admin_response.json()["access_token"]
    print("   ✅ Admin logged in")

    # ========================================================================
    # STEP 2: Get first tournament
    # ========================================================================
    print("\n2️⃣  Finding first tournament...")
    import psycopg2
    conn = psycopg2.connect(
        host="localhost",
        database="lfa_intern_system",
        user="postgres",
        password="postgres"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, tournament_status
        FROM semesters
        WHERE code LIKE 'TOURN-%'
        ORDER BY id ASC
        LIMIT 1
    """)
    tournament = cur.fetchone()
    assert tournament, "No tournaments found in database"

    tournament_id, tournament_name, current_status = tournament
    print(f"   📋 Tournament: {tournament_name}")
    print(f"   📊 Current status: {current_status}")
    print(f"   🆔 ID: {tournament_id}")

    # CRITICAL: Change tournament age_group to PRE (player is 11 years old)
    # The test player (pwt.k1sqx1@f1stteam.hu) is PRE category (age 11)
    # Tournament browse endpoint filters by age category
    print(f"   🔧 Updating tournament age_group to PRE (player is age 11)...")
    cur.execute("""
        UPDATE semesters
        SET age_group = 'PRE'
        WHERE id = %s
    """, (tournament_id,))
    conn.commit()
    print(f"   ✅ Age group updated to PRE")

    # ========================================================================
    # STEP 3: Login as player
    # ========================================================================
    print("\n3️⃣  Logging in as player...")
    player_response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": "pwt.k1sqx1@f1stteam.hu", "password": "password123"}
    )
    assert player_response.status_code == 200, f"Player login failed: {player_response.text}"
    player_token = player_response.json()["access_token"]
    print("   ✅ Player logged in")

    # ========================================================================
    # STEP 4: Verify player visibility based on current status
    # ========================================================================
    print(f"\n4️⃣  Checking player visibility (status: {current_status})...")
    browse_response = requests.get(
        f"{API_BASE_URL}/tournaments/available",
        headers={"Authorization": f"Bearer {player_token}"}
    )
    assert browse_response.status_code == 200, f"Browse failed: {browse_response.text}"

    tournaments = browse_response.json()
    tournament_ids = [t["tournament"]["id"] for t in tournaments]

    if current_status == "ENROLLMENT_OPEN":
        # Tournament already in ENROLLMENT_OPEN - player SHOULD see it
        assert tournament_id in tournament_ids, f"❌ Player SHOULD see tournament in ENROLLMENT_OPEN"
        print(f"   ✅ SUCCESS: Tournament already in ENROLLMENT_OPEN, player can see it!")
        print(f"   📊 Total visible tournaments: {len(tournaments)}")
        print("\n" + "="*80)
        print("✅ SMOKE TEST PASSED: Tournament visibility works correctly!")
        print("="*80 + "\n")
        # Close connections and exit early
        cur.close()
        conn.close()
        return

    elif current_status in ["SEEKING_INSTRUCTOR", "PENDING_INSTRUCTOR_ACCEPTANCE", "INSTRUCTOR_CONFIRMED", "READY_FOR_ENROLLMENT"]:
        assert tournament_id not in tournament_ids, f"❌ Player should NOT see tournament in {current_status}"
        print(f"   ✅ Correct: Player cannot see tournament (status: {current_status})")
    else:
        print(f"   ⚠️  Tournament is in unexpected status: {current_status}")

    # ========================================================================
    # STEP 5: Transition to READY_FOR_ENROLLMENT (if needed)
    # ========================================================================
    if current_status != "READY_FOR_ENROLLMENT":
        print(f"\n5️⃣  Transitioning {current_status} → READY_FOR_ENROLLMENT...")

        # May need multiple transitions depending on current state
        if current_status == "SEEKING_INSTRUCTOR":
            # Assign instructor first
            print("   📝 Assigning instructor...")
            assign_response = requests.post(
                f"{API_BASE_URL}/tournaments/{tournament_id}/direct-assign-instructor",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"instructor_id": 3}  # Grandmaster
            )
            assert assign_response.status_code == 200, f"Instructor assignment failed: {assign_response.text}"
            print("   ✅ Instructor assigned")

        # Now transition to READY_FOR_ENROLLMENT
        print("   📝 Transitioning to READY_FOR_ENROLLMENT...")
        ready_response = requests.patch(
            f"{API_BASE_URL}/tournaments/{tournament_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "new_status": "READY_FOR_ENROLLMENT",
                "reason": "Smoke test: preparing for enrollment"
            }
        )
        assert ready_response.status_code == 200, f"READY_FOR_ENROLLMENT transition failed: {ready_response.text}"
        print("   ✅ Status: READY_FOR_ENROLLMENT")
    else:
        print(f"\n5️⃣  Tournament already in READY_FOR_ENROLLMENT, skipping...")

    # ========================================================================
    # STEP 6: Verify player still CANNOT see (READY_FOR_ENROLLMENT)
    # ========================================================================
    print("\n6️⃣  Verifying player CANNOT see tournament (READY_FOR_ENROLLMENT)...")
    browse_response = requests.get(
        f"{API_BASE_URL}/tournaments/available",
        headers={"Authorization": f"Bearer {player_token}"}
    )
    assert browse_response.status_code == 200
    tournaments = browse_response.json()
    tournament_ids = [t["tournament"]["id"] for t in tournaments]
    assert tournament_id not in tournament_ids, "❌ Player should NOT see READY_FOR_ENROLLMENT tournament"
    print("   ✅ Correct: Player cannot see READY_FOR_ENROLLMENT tournament")

    # ========================================================================
    # STEP 7: Transition to ENROLLMENT_OPEN
    # ========================================================================
    print("\n7️⃣  Transitioning READY_FOR_ENROLLMENT → ENROLLMENT_OPEN...")
    open_response = requests.patch(
        f"{API_BASE_URL}/tournaments/{tournament_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "new_status": "ENROLLMENT_OPEN",
            "reason": "Smoke test: opening enrollment for players"
        }
    )
    assert open_response.status_code == 200, f"ENROLLMENT_OPEN transition failed: {open_response.text}"
    print("   ✅ Status: ENROLLMENT_OPEN")

    # ========================================================================
    # STEP 8: Verify player CAN NOW see tournament
    # ========================================================================
    print("\n8️⃣  Verifying player CAN NOW see tournament (ENROLLMENT_OPEN)...")
    browse_response = requests.get(
        f"{API_BASE_URL}/tournaments/available",
        headers={"Authorization": f"Bearer {player_token}"}
    )
    assert browse_response.status_code == 200, f"Browse failed: {browse_response.text}"

    tournaments = browse_response.json()
    tournament_ids = [t["tournament"]["id"] for t in tournaments]

    assert tournament_id in tournament_ids, f"❌ Player SHOULD see ENROLLMENT_OPEN tournament! Found: {tournament_ids}"
    print(f"   ✅ SUCCESS: Player can now see tournament!")
    print(f"   📊 Total visible tournaments: {len(tournaments)}")

    # ========================================================================
    # CLEANUP: Close connections
    # ========================================================================
    cur.close()
    conn.close()

    print("\n" + "="*80)
    print("✅ SMOKE TEST PASSED: Tournament visibility works correctly!")
    print("="*80 + "\n")
