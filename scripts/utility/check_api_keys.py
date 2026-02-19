import requests
import json

API_BASE = "http://localhost:8000"

# Login
login_resp = requests.post(
    f"{API_BASE}/api/v1/auth/login",
    json={"email": "grandmaster@lfa.com", "password": "grandmaster2024"}
)

token = login_resp.json()['access_token']

# Get session 209
session_resp = requests.get(
    f"{API_BASE}/api/v1/sessions/209",
    headers={"Authorization": f"Bearer {token}"}
)

session_data = session_resp.json()

print("FULL SESSION 209 DATA:")
print("=" * 70)
print(json.dumps(session_data, indent=2))
print("=" * 70)
print(f"\nKEYS IN RESPONSE: {list(session_data.keys())}")
print(f"\n'credit_cost' in keys? {'credit_cost' in session_data}")
print(f"Value of session_data.get('credit_cost'): {session_data.get('credit_cost')}")
