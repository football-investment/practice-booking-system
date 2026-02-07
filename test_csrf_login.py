import requests

session = requests.Session()

# Step 1: Get CSRF token
print("Step 1: Getting CSRF token...")
csrf_response = session.get("http://localhost:8000/auth/csrf")
print(f"CSRF response status: {csrf_response.status_code}")
csrf_token = session.cookies.get("csrf_token")
print(f"CSRF token from cookie: {csrf_token}")

# Step 2: Login with CSRF token
print("\nStep 2: Logging in with CSRF token...")
headers = {}
if csrf_token:
    headers["X-CSRF-Token"] = csrf_token

login_response = session.post(
    "http://localhost:8000/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"},
    headers=headers
)
print(f"Login status: {login_response.status_code}")
if login_response.status_code == 200:
    token_data = login_response.json()
    token = token_data["access_token"]
    print(f"✅ Login successful!")
    print(f"   Access token: {token[:30]}...")
    print(f"   User ID: {token_data.get('user_id')}")

    # Step 3: Test tournament endpoint
    print("\nStep 3: Testing tournament 530...")
    headers_with_auth = {"Authorization": f"Bearer {token}"}
    tournament_response = session.get(
        "http://localhost:8000/api/v1/tournaments/530/summary",
        headers=headers_with_auth
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
