"""
Test reward distribution with skill_rewards persistence
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Login as admin
print("🔐 Logging in as admin...")
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login/form",
    data={"username": "admin@lfa.com", "password": "admin123"}
)
print(f"Login status: {login_response.status_code}")

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.text}")
    exit(1)

token = login_response.json()["access_token"]
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Distribute rewards
print("\n💰 Distributing rewards for tournament 222...")
distribute_response = requests.post(
    f"{BASE_URL}/api/v1/tournaments/222/distribute-rewards",
    headers=headers,
    json={"reason": "Test skill_rewards persistence"}
)

print(f"Distribution status: {distribute_response.status_code}")

if distribute_response.status_code == 200:
    result = distribute_response.json()
    print(f"✅ Success!")
    print(f"   - Rewards distributed: {result['rewards_distributed']}")
    print(f"   - Total credits: {result['total_credits_awarded']}")
    print(f"   - Total XP: {result['total_xp_awarded']}")
    print(f"   - Status: {result['status']}")
else:
    print(f"❌ Failed: {distribute_response.text}")
    exit(1)

# Get distributed rewards (to see skill_points_awarded)
print("\n🎯 Fetching distributed rewards...")
rewards_response = requests.get(
    f"{BASE_URL}/api/v1/tournaments/222/distributed-rewards",
    headers=headers
)

if rewards_response.status_code == 200:
    rewards_data = rewards_response.json()
    print(f"✅ Rewards fetched successfully")
    print(f"   - Total rewards: {rewards_data['rewards_count']}")

    # Show first 3 players with skill points
    print("\n📊 Sample rewards (top 3):")
    for i, reward in enumerate(rewards_data['rewards'][:3], 1):
        skill_points = reward.get('skill_points_awarded', {})
        print(f"   {i}. {reward['player_name']} (Rank #{reward['rank']})")
        print(f"      - Credits: {reward['credits']}, XP: {reward['xp']}")
        print(f"      - Skill points: {skill_points}")
else:
    print(f"❌ Failed to fetch rewards: {rewards_response.text}")

print("\n✅ Test complete!")
