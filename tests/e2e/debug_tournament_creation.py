"""Quick debug script to test tournament creation endpoint"""
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Login as admin
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)

print(f"Login status: {login_response.status_code}")

if login_response.status_code != 200:
    print(f"Login failed: {login_response.text}")
    exit(1)

token = login_response.json()["access_token"]
print(f"Got token: {token[:20]}...")

# 2. Create tournament
tournament_data = {
    "name": "Debug Test Tournament",
    "specialization_type": "LFA_FOOTBALL_PLAYER",
    "age_group": "YOUTH",
    "start_date": "2026-01-10",
    "end_date": "2026-01-17",
    "description": "Debug test"
}

create_response = requests.post(
    f"{BASE_URL}/api/v1/tournaments",
    headers={"Authorization": f"Bearer {token}"},
    json=tournament_data
)

print(f"\nTournament creation status: {create_response.status_code}")
print(f"Response: {json.dumps(create_response.json(), indent=2)}")
