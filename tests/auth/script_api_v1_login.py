import requests

# Test API v1 login (should NOT require CSRF)
print("Testing /api/v1/auth/login (should be CSRF-exempt)...")
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)
print(f"Login status: {login_response.status_code}")
if login_response.status_code == 200:
    token_data = login_response.json()
    token = token_data["access_token"]
    print(f"✅ Login successful!")
    print(f"   Access token: {token[:30]}...")
    print(f"   User ID: {token_data.get('user_id')}")

    # Test tournament endpoint
    print("\nTesting tournament 530...")
    headers = {"Authorization": f"Bearer {token}"}
    tournament_response = requests.get(
        "http://localhost:8000/api/v1/tournaments/530/summary",
        headers=headers
    )
    print(f"Tournament response status: {tournament_response.status_code}")
    if tournament_response.status_code == 200:
        data = tournament_response.json()
        print(f"✅ Tournament data retrieved!")
        print(f"   Status: {data.get('tournament_status')}")
        print(f"   Name: {data.get('name')}")
    else:
        print(f"❌ Tournament request failed: {tournament_response.text}")
else:
    print(f"❌ Login failed: {login_response.text}")
