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

# Test tournament 606 leaderboard
print("\nStep 2: Testing tournament 606 leaderboard API...")
headers = {"Authorization": f"Bearer {token}"}
leaderboard_response = requests.get(
    "http://localhost:8000/api/v1/tournaments/606/leaderboard",
    headers=headers
)
print(f"Leaderboard response status: {leaderboard_response.status_code}")

if leaderboard_response.status_code == 200:
    data = leaderboard_response.json()
    print(f"\n✅ Leaderboard data retrieved!")
    print(f"   winner_count: {data.get('winner_count')}")
    print(f"   performance_rankings count: {len(data.get('performance_rankings', []))}")

    # Print all performance rankings
    print(f"\nAll performance_rankings:")
    for i, pr in enumerate(data.get('performance_rankings', []), 1):
        print(f"  {i}. rank={pr.get('rank')}, user_id={pr.get('user_id')}, best_score={pr.get('best_score')}, final_value={pr.get('final_value')}")

    # Check if ranks are correct
    ranks = [pr.get('rank') for pr in data.get('performance_rankings', [])]
    unique_ranks = set(ranks)
    print(f"\nUnique ranks in performance_rankings: {sorted(unique_ranks)}")
    if unique_ranks == {1}:
        print("❌ BUG STILL EXISTS: All players have rank=1 (tied ranks)")
    elif sorted(ranks) == list(range(1, 9)):
        print("✅ Ranks are properly distributed (1-8)")
    else:
        print(f"⚠️  Unexpected rank distribution: {ranks}")
else:
    print(f"❌ Leaderboard request failed: {leaderboard_response.text}")
