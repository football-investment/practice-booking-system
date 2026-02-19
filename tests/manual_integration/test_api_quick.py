import requests
import json

API_BASE = "http://localhost:8000"

# Login
print("Logging in as grandmaster@lfa.com...")
login_resp = requests.post(
    f"{API_BASE}/api/v1/auth/login",
    json={"email": "grandmaster@lfa.com", "password": "grandmaster123"}
)

if login_resp.status_code == 200:
    token = login_resp.json()['access_token']
    print(f"✅ Logged in successfully\n")
    
    # Get session 209
    print("Fetching session 209...")
    session_resp = requests.get(
        f"{API_BASE}/api/v1/sessions/209",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if session_resp.status_code == 200:
        session = session_resp.json()
        print(f"✅ Session fetched:")
        print(f"   ID: {session.get('id')}")
        print(f"   Title: {session.get('title')}")
        print(f"   Credit Cost: {session.get('credit_cost')} ⭐")
        print(f"   Capacity: {session.get('capacity')}")
    else:
        print(f"❌ Failed to fetch session: {session_resp.status_code}")
        print(session_resp.text)
else:
    print(f"❌ Login failed: {login_resp.status_code}")
    print(login_resp.text)
