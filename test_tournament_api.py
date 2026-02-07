import requests

# Test login
print("Testing login...")
login_response = requests.post(
    "http://localhost:8000/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)
print(f"Login status: {login_response.status_code}")
if login_response.status_code == 200:
    token_data = login_response.json()
    token = token_data["access_token"]
    print(f"✅ Login successful, token: {token[:20]}...")

    # Test tournament summary endpoint
    print("\nTesting tournament 530 summary...")
    headers = {"Authorization": f"Bearer {token}"}
    tournament_response = requests.get(
        "http://localhost:8000/api/v1/tournaments/530/summary",
        headers=headers
    )
    print(f"Tournament summary status: {tournament_response.status_code}")
    if tournament_response.status_code == 200:
        data = tournament_response.json()
        print(f"✅ Tournament data retrieved successfully")
        print(f"   Tournament status: {data.get('tournament_status')}")
        print(f"   Tournament name: {data.get('name')}")
    else:
        print(f"❌ Failed to get tournament: {tournament_response.text}")
else:
    print(f"❌ Login failed: {login_response.text}")
