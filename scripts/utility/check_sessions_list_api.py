import requests
import json

API_BASE = "http://localhost:8000"

# Login
login_resp = requests.post(
    f"{API_BASE}/api/v1/auth/login",
    json={"email": "grandmaster@lfa.com", "password": "grandmaster2024"}
)

token = login_resp.json()['access_token']

# Get sessions list for semester 167 (THIS IS WHAT THE DASHBOARD USES!)
sessions_resp = requests.get(
    f"{API_BASE}/api/v1/sessions?semester_id=167",
    headers={"Authorization": f"Bearer {token}"}
)

sessions_data = sessions_resp.json()

print("SESSIONS LIST API RESPONSE:")
print("=" * 70)

if isinstance(sessions_data, dict) and 'sessions' in sessions_data:
    sessions = sessions_data['sessions']
    print(f"Found {len(sessions)} sessions\n")
    
    for s in sessions:
        print(f"ID: {s.get('id')}")
        print(f"Title: {s.get('title')}")
        print(f"💳 credit_cost: {s.get('credit_cost')} ⭐⭐⭐")
        print(f"Keys: {list(s.keys())[:10]}")
        print("-" * 70)
else:
    print("Unexpected format:")
    print(json.dumps(sessions_data, indent=2)[:500])
    
print("=" * 70)
