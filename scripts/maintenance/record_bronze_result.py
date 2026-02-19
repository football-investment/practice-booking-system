"""
Script to record bronze match result for tournament 38.

Bronze Match (Session 210): Lamine Yamal (14) vs Martin Ødegaard (16)
Result: Lamine Yamal wins 9-7
"""

import requests
import json

# Login
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "grandmaster@lfa.com", "password": "LFA_2025!"}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
print("✅ Login successful")

# Submit bronze match results
# Lamine Yamal (14) wins 9-7 against Martin Ødegaard (16)
bronze_result = {
    "results": [
        {"user_id": 14, "score": 9, "opponent_score": 7},  # Lamine Yamal WINS
        {"user_id": 16, "score": 7, "opponent_score": 9}   # Martin Ødegaard loses
    ],
    "notes": "Bronze Medal Match - 3rd Place"
}

print(f"\n📤 Submitting bronze match results...")
print(json.dumps(bronze_result, indent=2))

result_response = requests.post(
    "http://localhost:8000/api/v1/tournaments/38/sessions/210/submit-results",
    headers={"Authorization": f"Bearer {token}"},
    json=bronze_result
)

if result_response.status_code in [200, 201]:
    print(f"\n✅ Bronze match results recorded successfully!")
    print(json.dumps(result_response.json(), indent=2))
else:
    print(f"\n❌ Failed to record results: {result_response.status_code}")
    print(result_response.text)
