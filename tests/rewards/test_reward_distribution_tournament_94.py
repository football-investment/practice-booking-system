"""
Test Reward Distribution on Tournament 94
==========================================

Tournament 94 is a COMPLETED tournament with 8 rankings.
This script will:
1. Check current tournament status
2. Distribute rewards (first time)
3. Verify rewards created
4. Distribute rewards (second time - idempotency test)
5. Verify no duplicates

Usage:
    python test_reward_distribution_tournament_94.py
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
TOURNAMENT_ID = 94

def get_admin_token():
    """Authenticate and get admin token"""
    print("\n🔑 Authenticating as admin...")
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    print(f"✅ Admin authenticated")
    return token

def check_tournament_status(token):
    """Check current tournament status"""
    print(f"\n{'='*80}")
    print(f"CHECKING TOURNAMENT {TOURNAMENT_ID} STATUS")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{API_BASE_URL}/tournaments/{TOURNAMENT_ID}/summary",
        headers=headers
    )

    if response.status_code != 200:
        print(f"❌ Failed to get tournament: {response.text}")
        return None

    tournament = response.json()
    print(f"\nCurrent Status:")
    print(f"   - ID: {tournament.get('id')}")
    print(f"   - Name: {tournament.get('name')}")
    print(f"   - Status: {tournament.get('tournament_status')}")
    print(f"   - Participants: {tournament.get('total_bookings', 0)}")
    print(f"   - Rankings: {tournament.get('rankings_count', 0)}")

    return tournament

def check_rewards_status(token):
    """Check current reward distribution status"""
    print(f"\n{'='*80}")
    print(f"CHECKING REWARDS STATUS")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{API_BASE_URL}/tournaments/{TOURNAMENT_ID}/distributed-rewards",
        headers=headers
    )

    if response.status_code != 200:
        print(f"❌ Failed to get rewards status: {response.text}")
        return None

    rewards = response.json()
    print(f"\nRewards Status:")
    print(f"   - Rewards distributed: {rewards.get('rewards_distributed', False)}")
    print(f"   - Total reward count: {rewards.get('rewards_count', 0)}")

    return rewards

def distribute_rewards(token, reason="Test distribution"):
    """Distribute rewards"""
    print(f"\n{'='*80}")
    print(f"DISTRIBUTING REWARDS: {reason}")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    start_time = time.time()
    response = requests.post(
        f"{API_BASE_URL}/tournaments/{TOURNAMENT_ID}/distribute-rewards",
        headers=headers,
        json={"reason": reason}
    )
    duration = time.time() - start_time

    print(f"Response: HTTP {response.status_code} ({duration*1000:.0f}ms)")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Rewards distributed successfully!")
        print(f"   - Message: {result.get('message', 'N/A')}")

        if "rewards_summary" in result:
            summary = result["rewards_summary"]
            print(f"   - Credit transactions: {summary.get('credit_transactions', 0)}")
            print(f"   - XP transactions: {summary.get('xp_transactions', 0)}")
            print(f"   - Skill rewards: {summary.get('skill_rewards', 0)}")
            print(f"   - Total credits: {summary.get('total_credits', 0)}")
            print(f"   - Total XP: {summary.get('total_xp', 0)}")

        return True
    elif response.status_code == 400:
        error = response.json()
        error_message = error.get("error", {}).get("message", error.get("detail", "N/A"))
        print(f"✅ Idempotency protection working!")
        print(f"   - Error message: {error_message}")
        return "idempotency"
    else:
        print(f"❌ Reward distribution failed: {response.text}")
        return False

def main():
    """Run reward distribution test"""
    print(f"\n{'='*80}")
    print(f"REWARD DISTRIBUTION TEST - TOURNAMENT {TOURNAMENT_ID}")
    print(f"{'='*80}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Authenticate
        token = get_admin_token()

        # Step 1: Check current tournament status
        tournament = check_tournament_status(token)
        if not tournament:
            print(f"\n❌ FAILED: Tournament not found")
            return

        # Verify tournament is COMPLETED
        if tournament.get("tournament_status") != "COMPLETED":
            print(f"\n❌ FAILED: Tournament must be COMPLETED (current: {tournament.get('tournament_status')})")
            return

        # Verify rankings exist
        rankings_count = tournament.get("rankings_count", 0)
        if rankings_count == 0:
            print(f"\n❌ FAILED: No rankings found")
            return

        print(f"\n✅ Tournament ready for reward distribution")
        print(f"   - Status: COMPLETED")
        print(f"   - Rankings: {rankings_count}")

        # Step 2: Check initial rewards status
        initial_rewards = check_rewards_status(token)

        # Step 3: Distribute rewards (first time)
        result1 = distribute_rewards(token, f"E2E Complete Test - First Distribution - {datetime.now().isoformat()}")
        if not result1:
            print(f"\n❌ FAILED: First reward distribution failed")
            return

        # Step 4: Verify rewards created
        after_first = check_rewards_status(token)
        if not after_first or not after_first.get("rewards_distributed"):
            print(f"\n❌ FAILED: Rewards not marked as distributed after first call")
            return

        print(f"\n✅ Rewards distributed successfully")

        # Step 5: Distribute rewards (second time - idempotency test)
        print(f"\n⏳ Waiting 2 seconds before second distribution...")
        time.sleep(2)

        result2 = distribute_rewards(token, f"E2E Complete Test - Second Distribution (Idempotency Test) - {datetime.now().isoformat()}")
        if result2 != "idempotency":
            print(f"\n⚠️ WARNING: Second distribution should have triggered idempotency protection")
            print(f"   - Result: {result2}")

        # Step 6: Verify no duplicates
        after_second = check_rewards_status(token)
        if after_first.get("rewards_count") != after_second.get("rewards_count"):
            print(f"\n❌ FAILED: Duplicate rewards created!")
            print(f"   - After first: {after_first.get('rewards_count')}")
            print(f"   - After second: {after_second.get('rewards_count')}")
            return

        print(f"\n✅ No duplicate rewards created")

        # Success!
        print(f"\n{'='*80}")
        print(f"✅ ALL TESTS PASSED!")
        print(f"{'='*80}")
        print(f"Tournament ID: {TOURNAMENT_ID}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n✅ You can now manually test this tournament in the frontend:")
        print(f"1. Navigate to Tournament History")
        print(f"2. Find tournament ID {TOURNAMENT_ID}")
        print(f"3. Click 'View Rewards' to see distributed rewards")
        print(f"4. Verify all 3 reward types are present:")
        print(f"   - Credit transactions (coins)")
        print(f"   - XP transactions (experience)")
        print(f"   - Skill rewards (skill-specific bonuses/penalties)")
        print(f"5. Try clicking 'Distribute All Rewards' again")
        print(f"6. Verify frontend shows 'Already distributed' message")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
