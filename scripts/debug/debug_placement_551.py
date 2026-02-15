import requests
import json

# Get auth token
print("Step 1: Getting auth token...")
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)
if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.text}")
    exit(1)

token_data = login_response.json()
token = token_data["access_token"]
print(f"✅ Login successful")

# Test tournament 551 leaderboard
print("\nStep 2: Testing tournament 551 leaderboard API...")
headers = {"Authorization": f"Bearer {token}"}
leaderboard_response = requests.get(
    "http://localhost:8000/api/v1/tournaments/551/leaderboard",
    headers=headers
)
print(f"Leaderboard response status: {leaderboard_response.status_code}")

if leaderboard_response.status_code == 200:
    data = leaderboard_response.json()
    print(f"\n✅ Leaderboard data retrieved!")
    print(f"   winner_count: {data.get('winner_count')}")
    print(f"   performance_rankings count: {len(data.get('performance_rankings', []))}")

    # Print first 3 performance rankings
    print(f"\nFirst 3 performance_rankings:")
    for i, pr in enumerate(data.get('performance_rankings', [])[:3], 1):
        print(f"  {i}. rank={pr.get('rank')}, user_id={pr.get('user_id')}, best_score={pr.get('best_score')}, final_value={pr.get('final_value')}")

    # Check if all ranks are 1
    ranks = [pr.get('rank') for pr in data.get('performance_rankings', [])]
    unique_ranks = set(ranks)
    print(f"\nUnique ranks in performance_rankings: {sorted(unique_ranks)}")
    if unique_ranks == {1}:
        print("❌ BUG CONFIRMED: All players have rank=1 (tied ranks)")
    else:
        print("✅ Ranks are properly distributed")
else:
    print(f"❌ Leaderboard request failed: {leaderboard_response.text}")
